#!/usr/bin/env python3
"""Compare homogeneous-F and spatial nodal-displacement sensor transfers.

The spatial map is fitted to the relative displacement of the garment shell
nodes over the 120 x 40 mm solid-submodel footprint centred on each sensor.
It is deliberately reported as a smooth least-squares boundary field rather
than an exact shell-to-solid tie because the shell and solid meshes are not
conforming.
"""

from __future__ import annotations

import csv
import json
import math
import subprocess
from pathlib import Path

import numpy as np

from generate_coupon import ROOT, generate
from postprocess_coupon import process
from postprocess_garment_contact import initial_shirt_coordinates, read_last_record
from postprocess_garment_movement import sensor_theta


FEBIO = Path("/Applications/FEBioStudio/FEBioStudio.app/Contents/MacOS/febio4")
LAYOUT = ROOT / "references" / "garment_layout_normalized.json"
SENSORS = (3, 9)
PAIRS = {
    "full_garment_no_contact": (
        "matched_no_contact_0p6_reference",
        "matched_no_contact_0p6_movement025",
    ),
    "full_garment_contact": (
        "garment_fit_torso_expand_060mm_manual",
        "garment_both_arms_raise_025",
    ),
}
COUPON_HALF_LENGTH_MM = 60.0
COUPON_HALF_WIDTH_MM = 20.0


def complete(case: str) -> bool:
    log = ROOT / "results" / f"{case}.log"
    return log.exists() and "N O R M A L   T E R M I N A T I O N" in log.read_text(
        errors="replace"
    )


def garment_state(case: str) -> tuple[np.ndarray, np.ndarray, dict]:
    metadata = json.loads((ROOT / "model" / f"{case}_metadata.json").read_text())
    n_theta = int(metadata["mesh"]["circumferential_divisions"])
    n_z = int(metadata["mesh"]["vertical_divisions"])
    length = float(metadata["shirt"]["modelled_body_panel_length_mm"])
    rx, ry = [float(value) for value in metadata["shirt"]["ellipse_radii_mm"]]
    initial = initial_shirt_coordinates(rx, ry, n_theta, n_z, length)
    log_path = ROOT / "results" / f"{case}.log"
    final = read_last_record(
        log_path.read_text(errors="replace").splitlines(),
        "shirt_final_coordinates",
        n_theta * (n_z + 1),
        log_path,
    )
    return initial, final, metadata


def interpolate_shell(
    coordinates: np.ndarray,
    theta: float,
    z_mm: float,
    n_theta: int,
    n_z: int,
    length_mm: float,
) -> np.ndarray:
    circumferential = (theta % (2.0 * math.pi)) * n_theta / (2.0 * math.pi)
    j = int(math.floor(circumferential)) % n_theta
    a = circumferential - math.floor(circumferential)
    jp = (j + 1) % n_theta
    vertical = min(float(n_z), max(0.0, z_mm * n_z / length_mm))
    k = min(n_z - 1, int(math.floor(vertical)))
    b = vertical - k
    ids = (
        k * n_theta + j,
        k * n_theta + jp,
        (k + 1) * n_theta + jp,
        (k + 1) * n_theta + j,
    )
    return (
        (1.0 - a) * (1.0 - b) * coordinates[ids[0]]
        + a * (1.0 - b) * coordinates[ids[1]]
        + a * b * coordinates[ids[2]]
        + (1.0 - a) * b * coordinates[ids[3]]
    )


def local_basis(
    fitted: np.ndarray,
    theta: float,
    z_mm: float,
    n_theta: int,
    n_z: int,
    length_mm: float,
    angle_deg: float,
) -> np.ndarray:
    dtheta = 0.25 * 2.0 * math.pi / n_theta
    dz = 0.25 * length_mm / n_z
    tangent_theta = interpolate_shell(
        fitted, theta + dtheta, z_mm, n_theta, n_z, length_mm
    ) - interpolate_shell(fitted, theta - dtheta, z_mm, n_theta, n_z, length_mm)
    tangent_z = interpolate_shell(
        fitted, theta, z_mm + dz, n_theta, n_z, length_mm
    ) - interpolate_shell(fitted, theta, z_mm - dz, n_theta, n_z, length_mm)
    e_theta = tangent_theta / np.linalg.norm(tangent_theta)
    e_z = tangent_z - float(np.dot(tangent_z, e_theta)) * e_theta
    e_z /= np.linalg.norm(e_z)
    e_n = np.cross(e_theta, e_z)
    garment_basis = np.column_stack((e_theta, e_z, e_n))
    angle = math.radians(angle_deg)
    c, s = math.cos(angle), math.sin(angle)
    sensor_rotation = np.asarray(
        [[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]]
    )
    return garment_basis @ sensor_rotation


def spatial_polynomial(reference_case: str, movement_case: str, sensor: dict) -> dict:
    _, fitted, metadata_fit = garment_state(reference_case)
    _, moved, metadata_move = garment_state(movement_case)
    if metadata_fit["mesh"] != metadata_move["mesh"]:
        raise ValueError("reference and movement garment meshes differ")
    n_theta = int(metadata_fit["mesh"]["circumferential_divisions"])
    n_z = int(metadata_fit["mesh"]["vertical_divisions"])
    length = float(metadata_fit["shirt"]["modelled_body_panel_length_mm"])
    rx, ry = [float(value) for value in metadata_fit["shirt"]["ellipse_radii_mm"]]
    theta0 = sensor_theta(sensor["panel"], float(sensor["x"]))
    z0 = float(sensor["y"]) * length
    angle = math.radians(float(sensor["angle_deg"]))
    c, s = math.cos(angle), math.sin(angle)
    arc_radius = math.sqrt((rx * math.sin(theta0)) ** 2 + (ry * math.cos(theta0)) ** 2)
    basis = local_basis(
        fitted, theta0, z0, n_theta, n_z, length, float(sensor["angle_deg"])
    )
    fitted_center = interpolate_shell(fitted, theta0, z0, n_theta, n_z, length)
    moved_center = interpolate_shell(moved, theta0, z0, n_theta, n_z, length)
    center_increment = moved_center - fitted_center

    samples = []
    targets = []
    for x_mm in np.linspace(-COUPON_HALF_LENGTH_MM, COUPON_HALF_LENGTH_MM, 9):
        for y_mm in np.linspace(-COUPON_HALF_WIDTH_MM, COUPON_HALF_WIDTH_MM, 7):
            circumferential_mm = x_mm * c - y_mm * s
            vertical_mm = x_mm * s + y_mm * c
            theta = theta0 + circumferential_mm / arc_radius
            z_mm = z0 + vertical_mm
            fitted_point = interpolate_shell(fitted, theta, z_mm, n_theta, n_z, length)
            moved_point = interpolate_shell(moved, theta, z_mm, n_theta, n_z, length)
            local_increment = basis.T @ (
                (moved_point - fitted_point) - center_increment
            )
            xn = x_mm / COUPON_HALF_LENGTH_MM
            yn = y_mm / COUPON_HALF_WIDTH_MM
            samples.append([xn, yn, xn * yn, xn * xn, yn * yn])
            targets.append(local_increment)
    design = np.asarray(samples)
    target = np.asarray(targets)
    coefficients = np.linalg.lstsq(design, target, rcond=None)[0].T
    predicted = design @ coefficients.T
    residual = predicted - target
    return {
        "coordinate_scales_mm": [COUPON_HALF_LENGTH_MM, COUPON_HALF_WIDTH_MM],
        "term_order": ["x", "y", "x_y", "x_squared", "y_squared"],
        "coefficients": coefficients.tolist(),
        "fit_source": {
            "reference_case": reference_case,
            "movement_case": movement_case,
            "sensor": int(sensor["sensor"]),
            "sample_count": int(design.shape[0]),
            "shell_interpolation": "periodic bilinear interpolation of four shell nodes",
            "mapping": "relative nodal displacement fitted in the fitted-state sensor basis",
            "rms_residual_mm": float(np.sqrt(np.mean(residual**2))),
            "maximum_vector_residual_mm": float(
                np.linalg.norm(residual, axis=1).max()
            ),
            "maximum_sample_vector_increment_mm": float(
                np.linalg.norm(target, axis=1).max()
            ),
        },
    }


def run_case(case: str, polynomial: dict) -> dict:
    if not complete(case):
        generate(
            case_name=case,
            mesh_level="local_medium",
            material_case="textile_fiber_balanced",
            taper_length_mm=5.0,
            tip_thickness_fraction=0.25,
            remote_displacement_polynomial=polynomial,
            time_steps=20,
            maximum_time_step=0.05,
        )
        completed = subprocess.run(
            [str(FEBIO), "-i", str(ROOT / "model" / f"{case}.feb")],
            cwd=ROOT,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.STDOUT,
            check=False,
        )
        if completed.returncode != 0 or not complete(case):
            raise RuntimeError(f"FEBio failed for {case} ({completed.returncode})")
    result = process(case)
    log_text = (ROOT / "results" / f"{case}.log").read_text(errors="replace")
    result["negative_jacobian_messages"] = log_text.count(
        "negative jacobians detected"
    )
    return result


def main() -> None:
    layout = json.loads(LAYOUT.read_text())
    sensors = {
        int(item["sensor"]): item
        for item in layout["sensors"]
        if int(item["sensor"]) in SENSORS
    }
    homogeneous = json.loads((ROOT / "results" / "relative_F_sensor_mesh.json").read_text())
    homogeneous_rows = {
        (row["garment_model"], int(row["sensor"])): row
        for row in homogeneous["rows"]
        if row["mesh"] == "local_medium"
    }
    rows = []
    fields = {}
    for model, (reference_case, movement_case) in PAIRS.items():
        for sensor_number in SENSORS:
            polynomial = spatial_polynomial(
                reference_case, movement_case, sensors[sensor_number]
            )
            fields[f"{model}_s{sensor_number}"] = polynomial
            case = f"spatial_map1p0_{model}_s{sensor_number}_local_medium"
            print(f"Running {case}", flush=True)
            result = run_case(case, polynomial)
            baseline = homogeneous_rows[(model, sensor_number)]
            endpoint = 100.0 * float(result["mean_conductive_gauge_strain"])
            path = 100.0 * float(
                result["conductive_gauge_centroid_path_engineering_strain"]
            )
            rows.append(
                {
                    "case_name": case,
                    "garment_model": model,
                    "sensor": sensor_number,
                    "mesh": "local_medium",
                    "spatial_endpoint_percent": endpoint,
                    "homogeneous_endpoint_percent": baseline["endpoint_gauge_percent"],
                    "spatial_path_percent": path,
                    "homogeneous_path_percent": baseline["path_gauge_percent"],
                    "endpoint_sign_preserved_vs_homogeneous": bool(
                        np.sign(endpoint) == np.sign(baseline["endpoint_gauge_percent"])
                    ),
                    "path_sign_preserved_vs_homogeneous": bool(
                        np.sign(path) == np.sign(baseline["path_gauge_percent"])
                    ),
                    "endpoint_change_percent_of_homogeneous": 100.0
                    * (endpoint - baseline["endpoint_gauge_percent"])
                    / max(abs(float(baseline["endpoint_gauge_percent"])), 1e-15),
                    "path_change_percent_of_homogeneous": 100.0
                    * (path - baseline["path_gauge_percent"])
                    / max(abs(float(baseline["path_gauge_percent"])), 1e-15),
                    "mapping_rms_residual_mm": polynomial["fit_source"]["rms_residual_mm"],
                    "mapping_maximum_residual_mm": polynomial["fit_source"]["maximum_vector_residual_mm"],
                    "normal_termination": complete(case),
                    "negative_jacobian_messages": int(result["negative_jacobian_messages"]),
                }
            )
    summary = {
        "status": "spatial nodal-displacement-derived boundary comparison; uncalibrated mechanical analysis",
        "method": "periodic bilinear shell-node interpolation followed by a continuous quadratic least-squares boundary map",
        "rows": rows,
        "all_endpoint_signs_preserved_vs_homogeneous": all(
            row["endpoint_sign_preserved_vs_homogeneous"] for row in rows
        ),
        "all_path_signs_preserved_vs_homogeneous": all(
            row["path_sign_preserved_vs_homogeneous"] for row in rows
        ),
        "boundary_fields": fields,
    }
    json_path = ROOT / "results" / "spatial_boundary_transfer.json"
    csv_path = ROOT / "results" / "spatial_boundary_transfer.csv"
    json_path.write_text(json.dumps(summary, indent=2) + "\n")
    with csv_path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(json.dumps({key: value for key, value in summary.items() if key != "boundary_fields"}, indent=2))
    print(f"Wrote {json_path}")
    print(f"Wrote {csv_path}")


if __name__ == "__main__":
    main()
