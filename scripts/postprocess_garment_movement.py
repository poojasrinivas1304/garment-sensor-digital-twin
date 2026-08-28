#!/usr/bin/env python3
"""Audit garment contact and extract sensor strains for a movement case."""

from __future__ import annotations

import argparse
import json
import math
import os
import re
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/private/tmp/matplotlib-garment-movement")
os.environ.setdefault("MPLBACKEND", "Agg")

import matplotlib.pyplot as plt
import numpy as np

from postprocess_garment_contact import (
    N_THETA,
    N_Z,
    SHIRT_LENGTH,
    facet_locations,
    initial_shirt_coordinates,
    read_last_record,
    signed_triangle_area_ratios,
)


ROOT = Path(__file__).resolve().parents[1]
LAYOUT = ROOT / "references" / "garment_layout_normalized.json"


def sensor_theta(panel: str, x: float) -> float:
    if panel == "front":
        return math.pi * (x + 1.5)
    return math.pi * (x + 0.5)


def local_surface_kinematics(
    initial: np.ndarray,
    final: np.ndarray,
    theta: float,
    y_normalized: float,
    n_theta: int = N_THETA,
    n_z: int = N_Z,
) -> tuple[float, float, float, int, int, np.ndarray]:
    """Return surface Green strain and a director-completed local F.

    The two shell tangents are mapped exactly. Unit reference and current
    normals complete the surface map through the thickness; this preserves
    the local rotation, in-plane stretch and shear while assuming unit
    director stretch.
    """
    j = int(math.floor((theta % (2.0 * math.pi)) * n_theta / (2.0 * math.pi)))
    k = min(n_z - 1, max(0, int(math.floor(y_normalized * n_z))))
    jp = (j + 1) % n_theta
    ids = np.asarray(
        [
            k * n_theta + j,
            k * n_theta + jp,
            (k + 1) * n_theta + jp,
            (k + 1) * n_theta + j,
        ]
    )

    def directions(coords: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        circumferential = 0.5 * (
            (coords[ids[1]] - coords[ids[0]])
            + (coords[ids[2]] - coords[ids[3]])
        )
        vertical = 0.5 * (
            (coords[ids[3]] - coords[ids[0]])
            + (coords[ids[2]] - coords[ids[1]])
        )
        return circumferential, vertical

    a_theta, a_z = directions(initial)
    g_theta, g_z = directions(final)
    reference_normal = np.cross(a_theta, a_z)
    reference_normal /= np.linalg.norm(reference_normal)
    current_normal = np.cross(g_theta, g_z)
    current_normal /= np.linalg.norm(current_normal)
    reference_map = np.column_stack((a_theta, a_z, reference_normal))
    current_map = np.column_stack((g_theta, g_z, current_normal))
    deformation_gradient_global = current_map @ np.linalg.inv(reference_map)

    basis_theta = a_theta / np.linalg.norm(a_theta)
    basis_z = a_z - float(np.dot(a_z, basis_theta)) * basis_theta
    basis_z /= np.linalg.norm(basis_z)
    basis_normal = np.cross(basis_theta, basis_z)
    local_basis = np.column_stack((basis_theta, basis_z, basis_normal))
    deformation_gradient_local = (
        local_basis.T @ deformation_gradient_global @ local_basis
    )
    green = 0.5 * (
        deformation_gradient_local.T @ deformation_gradient_local - np.eye(3)
    )
    return (
        float(green[0, 0]),
        float(green[1, 1]),
        float(green[0, 1]),
        j,
        k,
        deformation_gradient_local,
    )


def rotate_deformation_gradient(
    deformation_gradient: np.ndarray, angle_deg: float
) -> np.ndarray:
    """Express a garment-basis deformation gradient in the sensor basis."""
    angle = math.radians(angle_deg)
    c, s = math.cos(angle), math.sin(angle)
    rotation = np.asarray([[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]])
    return rotation.T @ deformation_gradient @ rotation


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", required=True)
    parser.add_argument("--no-figure", action="store_true")
    args = parser.parse_args()

    log_path = ROOT / "results" / f"{args.case}.log"
    metadata_path = ROOT / "model" / f"{args.case}_metadata.json"
    summary_path = ROOT / "results" / f"{args.case}_movement_summary.json"
    figure_path = ROOT / "figures" / f"{args.case}_movement_audit.png"
    lines = log_path.read_text(errors="replace").splitlines()
    metadata = json.loads(metadata_path.read_text())
    shirt_radii = metadata["shirt"]["ellipse_radii_mm"]
    n_theta = int(metadata.get("mesh", {}).get("circumferential_divisions", N_THETA))
    n_z = int(metadata.get("mesh", {}).get("vertical_divisions", N_Z))
    shirt_length = float(
        metadata.get("shirt", {}).get("modelled_body_panel_length_mm", SHIRT_LENGTH)
    )
    initial = initial_shirt_coordinates(
        float(shirt_radii[0]), float(shirt_radii[1]), n_theta, n_z, shirt_length
    )
    final = read_last_record(
        lines, "shirt_final_coordinates", n_theta * (n_z + 1), log_path
    )
    contact_enabled = bool(metadata.get("contact", {}).get("enabled", True))
    if contact_enabled:
        face = read_last_record(lines, "shirt_contact_data", n_theta * n_z, log_path)
        gap = face[:, 0]
        pressure = face[:, 1]
    else:
        gap = np.full(n_theta * n_z, np.nan)
        pressure = np.zeros(n_theta * n_z)
    active = pressure > 1e-12
    area_ratios = signed_triangle_area_ratios(initial, final, n_theta, n_z)

    layout = json.loads(LAYOUT.read_text())
    sensor_rows = []
    for sensor in layout["sensors"]:
        theta = sensor_theta(sensor["panel"], float(sensor["x"]))
        e_tt, e_zz, e_tz, j, k, deformation_gradient = local_surface_kinematics(
            initial, final, theta, float(sensor["y"]), n_theta, n_z
        )
        angle = math.radians(float(sensor["angle_deg"]))
        c, s = math.cos(angle), math.sin(angle)
        projected = e_tt * c * c + e_zz * s * s + 2.0 * e_tz * s * c
        sensor_gradient = rotate_deformation_gradient(
            deformation_gradient, float(sensor["angle_deg"])
        )
        if j < n_theta // 2:
            facet_index = k * (n_theta // 2) + j
        else:
            facet_index = (
                n_z * (n_theta // 2)
                + k * (n_theta // 2)
                + (j - n_theta // 2)
            )
        sensor_rows.append(
            {
                "sensor": int(sensor["sensor"]),
                "panel": sensor["panel"],
                "theta_deg": math.degrees(theta) % 360.0,
                "height_mm": float(sensor["y"]) * shirt_length,
                "sensor_angle_deg": float(sensor["angle_deg"]),
                "element_theta_index": j,
                "element_z_index": k,
                "green_strain_circumferential": e_tt,
                "green_strain_vertical": e_zz,
                "green_shear_tensor_component": e_tz,
                "projected_sensor_axis_green_strain": projected,
                "deformation_gradient_garment_basis": deformation_gradient.tolist(),
                "deformation_gradient_sensor_basis": sensor_gradient.tolist(),
                "director_completion": "unit reference normal mapped to unit current normal",
                "local_contact_gap_mm": (
                    float(gap[facet_index]) if contact_enabled else None
                ),
                "local_contact_pressure_kPa": (
                    float(pressure[facet_index] * 1000.0) if contact_enabled else None
                ),
                "local_contact_active": (
                    bool(active[facet_index]) if contact_enabled else False
                ),
            }
        )

    negative_counts = [
        int(match.group(1))
        for line in lines
        if (match := re.search(r"(\d+) negative jacobians detected", line))
    ]
    displacement = final - initial
    active_gap = gap[active]
    active_pressure = pressure[active]
    pressure_gap_zero_intercept_slope = (
        float(np.dot(active_gap, active_pressure) / np.dot(active_gap, active_gap))
        if active.any() and float(np.dot(active_gap, active_gap)) > 0.0
        else 0.0
    )
    pressure_gap_correlation = (
        float(np.corrcoef(active_gap, active_pressure)[0, 1])
        if active.sum() > 1 and float(np.std(active_gap)) > 0.0
        and float(np.std(active_pressure)) > 0.0
        else 0.0
    )
    movement_name = metadata.get("control", {}).get("movement")
    summary = {
        "case": args.case,
        "status": (
            "illustrative boundary-driven bilateral-arm-raise movement; not calibrated human motion"
            if movement_name else
            "fitted-contact reference state used for movement-strain subtraction"
        ),
        "febio_normal_termination": any(
            "N O R M A L   T E R M I N A T I O N" in line for line in lines
        ),
        "movement": metadata["control"],
        "mesh_quality": {
            "final_surface_inverted_triangles": int((area_ratios <= 0.0).sum()),
            "minimum_signed_triangle_area_ratio": float(area_ratios.min()),
        },
        "solver_path": {
            "rejected_negative_jacobian_trials": len(negative_counts),
            "maximum_negative_jacobians_in_rejected_trial": (
                max(negative_counts) if negative_counts else 0
            ),
        },
        "contact": {
            "enabled": contact_enabled,
            "sampling": "FEBio face_data on each primary garment contact facet at the accepted final state",
            "active_definition": "reported contact pressure > 1e-12 MPa",
            "active_facets": int(active.sum()),
            "active_facet_fraction": float(active.mean()),
            "pressure_kPa_active_mean": (
                float(active_pressure.mean() * 1000.0) if active.any() else 0.0
            ),
            "pressure_kPa_active_max": (
                float(active_pressure.max() * 1000.0) if active.any() else 0.0
            ),
            "maximum_absolute_active_gap_mm": (
                float(np.abs(active_gap).max()) if active.any() else 0.0
            ),
            "signed_active_gap_mm_range": (
                [float(active_gap.min()), float(active_gap.max())]
                if active.any() else [0.0, 0.0]
            ),
            "active_facets_with_negative_gap": int((active_gap < 0.0).sum()),
            "active_facets_with_positive_gap": int((active_gap > 0.0).sum()),
            "absolute_active_gap_mm_median": (
                float(np.quantile(np.abs(active_gap), 0.50)) if active.any() else 0.0
            ),
            "absolute_active_gap_mm_95th_percentile": (
                float(np.quantile(np.abs(active_gap), 0.95)) if active.any() else 0.0
            ),
            "active_facets_above_0p01_mm_gap": (
                int((np.abs(active_gap) > 0.01).sum()) if active.any() else 0
            ),
            "pressure_gap_zero_intercept_slope_MPa_per_mm": pressure_gap_zero_intercept_slope,
            "pressure_gap_pearson_r": pressure_gap_correlation,
        },
        "kinematics": {
            "maximum_displacement_mm": float(np.linalg.norm(displacement, axis=1).max()),
            "maximum_vertical_displacement_mm": float(displacement[:, 2].max()),
            "minimum_vertical_displacement_mm": float(displacement[:, 2].min()),
        },
        "sensor_strains": sensor_rows,
    }
    summary_path.write_text(json.dumps(summary, indent=2) + "\n")

    if not args.no_figure:
        theta_face, z_face = facet_locations(n_theta, n_z, shirt_length)
        theta_nodes = np.tile(np.arange(n_theta) * 360.0 / n_theta, n_z + 1)
        z_nodes = np.repeat(np.arange(n_z + 1) * shirt_length / n_z, n_theta)
        fig, axes = plt.subplots(1, 3, figsize=(14.2, 4.5), constrained_layout=True)

        strains = np.asarray(
            [row["projected_sensor_axis_green_strain"] for row in sensor_rows]
        ) * 100.0
        colors = ["#0072B2" if row["panel"] == "front" else "#D55E00" for row in sensor_rows]
        axes[0].bar(np.arange(1, 11), strains, color=colors)
        axes[0].axhline(0.0, color="black", lw=0.8)
        axes[0].set_xticks(np.arange(1, 11))
        axes[0].set_xlabel("sensor")
        axes[0].set_ylabel("projected Green strain (%)")
        axes[0].set_title("(a) Sensor-axis garment strain")

        pressure_scatter = axes[1].scatter(
            theta_face, z_face, c=pressure * 1000.0, s=12, cmap="viridis", vmin=0
        )
        axes[1].set_xlabel("circumferential angle (degrees)")
        axes[1].set_ylabel("height from hem (mm)")
        axes[1].set_title("(b) Contact pressure (kPa)")
        fig.colorbar(pressure_scatter, ax=axes[1], shrink=0.85)

        vertical_scatter = axes[2].scatter(
            theta_nodes,
            z_nodes,
            c=displacement[:, 2],
            s=9,
            cmap="coolwarm",
        )
        for row in sensor_rows:
            axes[2].text(
                row["theta_deg"], row["height_mm"], f"S{row['sensor']}",
                fontsize=7, ha="center", va="center", color="black"
            )
        axes[2].set_xlabel("circumferential angle (degrees)")
        axes[2].set_ylabel("height from hem (mm)")
        axes[2].set_title("(c) Vertical displacement (mm)")
        fig.colorbar(vertical_scatter, ax=axes[2], shrink=0.85)
        fig.suptitle(
            f"Bilateral-arm-raise audit: {active.sum()}/{len(active)} active facets; "
            f"max |sensor strain| {np.abs(strains).max():.3g}%"
        )
        fig.savefig(figure_path, dpi=300)
        plt.close(fig)

    print(json.dumps(summary, indent=2))
    print(f"Wrote {summary_path}")
    if not args.no_figure:
        print(f"Wrote {figure_path}")


if __name__ == "__main__":
    main()
