#!/usr/bin/env python3
"""Audit the converged garment-contact verification model."""

from __future__ import annotations

import argparse
import json
import math
import os
import re
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/private/tmp/matplotlib-garment-contact")
os.environ.setdefault("MPLBACKEND", "Agg")

import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CASE = "garment_contact_equilibrium"

N_THETA = 64
N_Z = 26
SHIRT_RX = 189.63
SHIRT_RY = 166.62
TORSO_RX = 188.0
TORSO_RY = 165.0
SHIRT_LENGTH = 650.0


def read_last_record(
    lines: list[str], marker: str, count: int, log_path: Path
) -> np.ndarray:
    starts = [i for i, line in enumerate(lines) if line.strip() == f"Data = {marker}"]
    if not starts:
        raise RuntimeError(f"Record {marker!r} is absent from {log_path}")
    rows: list[list[float]] = []
    for line in lines[starts[-1] + 1 :]:
        fields = line.strip().split(",")
        if len(fields) < 2 or not fields[0].isdigit():
            if rows:
                break
            continue
        rows.append([float(value) for value in fields[1:]])
        if len(rows) == count:
            break
    if len(rows) != count:
        raise RuntimeError(f"Expected {count} rows for {marker}, found {len(rows)}")
    return np.asarray(rows)


def initial_shirt_coordinates(
    rx: float,
    ry: float,
    n_theta: int = N_THETA,
    n_z: int = N_Z,
    shirt_length: float = SHIRT_LENGTH,
) -> np.ndarray:
    coords = []
    for k in range(n_z + 1):
        z = shirt_length * k / n_z
        for j in range(n_theta):
            theta = 2.0 * math.pi * j / n_theta
            coords.append(
                [rx * math.cos(theta), ry * math.sin(theta), z]
            )
    return np.asarray(coords)


def facet_locations(
    n_theta: int = N_THETA,
    n_z: int = N_Z,
    shirt_length: float = SHIRT_LENGTH,
) -> tuple[np.ndarray, np.ndarray]:
    theta = []
    z = []
    for sectors in (range(0, n_theta // 2), range(n_theta // 2, n_theta)):
        for k in range(n_z):
            for j in sectors:
                theta.append((j + 0.5) * 360.0 / n_theta)
                z.append((k + 0.5) * shirt_length / n_z)
    return np.asarray(theta), np.asarray(z)


def signed_triangle_area_ratios(
    initial: np.ndarray,
    final: np.ndarray,
    n_theta: int = N_THETA,
    n_z: int = N_Z,
) -> np.ndarray:
    ratios: list[float] = []
    for k in range(n_z):
        for j in range(n_theta):
            jp = (j + 1) % n_theta
            ids = (
                k * n_theta + j,
                k * n_theta + jp,
                (k + 1) * n_theta + jp,
                (k + 1) * n_theta + j,
            )
            for a, b, c in ((ids[0], ids[1], ids[2]), (ids[0], ids[2], ids[3])):
                normal_0 = np.cross(initial[b] - initial[a], initial[c] - initial[a])
                normal_f = np.cross(final[b] - final[a], final[c] - final[a])
                ratios.append(float(np.dot(normal_f, normal_0) / np.dot(normal_0, normal_0)))
    return np.asarray(ratios)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", default=DEFAULT_CASE)
    parser.add_argument("--no-figure", action="store_true")
    args = parser.parse_args()
    log_path = ROOT / "results" / f"{args.case}.log"
    summary_path = ROOT / "results" / f"{args.case}_summary.json"
    figure_path = ROOT / "figures" / f"{args.case}_audit.png"
    metadata_path = ROOT / "model" / f"{args.case}_metadata.json"
    metadata = json.loads(metadata_path.read_text()) if metadata_path.exists() else {}
    shirt_radii = metadata.get("shirt", {}).get(
        "ellipse_radii_mm", [SHIRT_RX, SHIRT_RY]
    )
    n_theta = int(metadata.get("mesh", {}).get("circumferential_divisions", N_THETA))
    n_z = int(metadata.get("mesh", {}).get("vertical_divisions", N_Z))
    shirt_length = float(
        metadata.get("shirt", {}).get("modelled_body_panel_length_mm", SHIRT_LENGTH)
    )

    lines = log_path.read_text(errors="replace").splitlines()
    final = read_last_record(
        lines, "shirt_final_coordinates", n_theta * (n_z + 1), log_path
    )
    face = read_last_record(
        lines, "shirt_contact_data", n_theta * n_z, log_path
    )
    initial = initial_shirt_coordinates(
        float(shirt_radii[0]), float(shirt_radii[1]), n_theta, n_z, shirt_length
    )
    gap = face[:, 0]
    pressure = face[:, 1]
    active = pressure > 1e-12
    displacement = np.linalg.norm(final - initial, axis=1)
    ellipse_metric = (final[:, 0] / TORSO_RX) ** 2 + (
        final[:, 1] / TORSO_RY
    ) ** 2
    area_ratios = signed_triangle_area_ratios(initial, final, n_theta, n_z)
    negative_jacobian_counts = [
        int(match.group(1))
        for line in lines
        if (match := re.search(r"(\d+) negative jacobians detected", line))
    ]

    active_gap = gap[active]
    active_pressure = pressure[active]
    pressure_gap_zero_intercept_slope = (
        float(np.dot(active_gap, active_pressure) / np.dot(active_gap, active_gap))
        if active.any() and float(np.dot(active_gap, active_gap)) > 0.0
        else 0.0
    )
    normal_termination = any("N O R M A L   T E R M I N A T I O N" in line for line in lines)
    summary = {
        "case": args.case,
        "febio_normal_termination": normal_termination,
        "mesh": {
            "shirt_nodes": int(final.shape[0]),
            "shirt_contact_facets": int(face.shape[0]),
        },
        "kinematics": {
            "maximum_nodal_displacement_mm": float(displacement.max()),
            "mean_nodal_displacement_mm": float(displacement.mean()),
            "final_z_range_mm": [float(final[:, 2].min()), float(final[:, 2].max())],
            "torso_ellipse_metric_range_at_shirt_midsurface": [
                float(ellipse_metric.min()),
                float(ellipse_metric.max()),
            ],
            "final_surface_inverted_triangles": int((area_ratios <= 0.0).sum()),
            "minimum_signed_triangle_area_ratio": float(area_ratios.min()),
        },
        "solver_path": {
            "rejected_negative_jacobian_trials": len(negative_jacobian_counts),
            "maximum_negative_jacobians_in_rejected_trial": (
                max(negative_jacobian_counts) if negative_jacobian_counts else 0
            ),
        },
        "contact": {
            "sampling": "FEBio face_data on each primary garment contact facet at the accepted final state",
            "active_definition": "reported contact pressure > 1e-12 MPa",
            "active_facets": int(active.sum()),
            "active_facet_fraction": float(active.mean()),
            "pressure_MPa_active_mean": (
                float(active_pressure.mean()) if active.any() else 0.0
            ),
            "pressure_MPa_active_max": (
                float(active_pressure.max()) if active.any() else 0.0
            ),
            "gap_mm_all_range": [float(gap.min()), float(gap.max())],
            "gap_mm_active_range": (
                [float(active_gap.min()), float(active_gap.max())]
                if active.any()
                else [0.0, 0.0]
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
            "pressure_gap_zero_intercept_slope_MPa_per_mm": pressure_gap_zero_intercept_slope,
            "pressure_gap_pearson_r": (
                float(np.corrcoef(active_gap, active_pressure)[0, 1])
                if active.sum() > 1 and float(np.std(active_gap)) > 0.0
                and float(np.std(active_pressure)) > 0.0 else 0.0
            ),
        },
        "interpretation": (
            "Verification only: geometry, constitutive constants, contact parameters, and fit "
            "remain provisional and must not be presented as experimentally calibrated."
        ),
    }
    summary_path.write_text(json.dumps(summary, indent=2) + "\n")

    if not args.no_figure:
        theta_face, z_face = facet_locations(n_theta, n_z, shirt_length)
        middle = n_z // 2
        middle_ids = np.arange(middle * n_theta, (middle + 1) * n_theta)
        order = np.argsort(
            np.arctan2(initial[middle_ids, 1], initial[middle_ids, 0])
        )

        fig, axes = plt.subplots(1, 3, figsize=(13.2, 4.2), constrained_layout=True)
        angle = np.linspace(0, 2 * np.pi, 400)
        axes[0].plot(
            TORSO_RX * np.cos(angle),
            TORSO_RY * np.sin(angle),
            "k-",
            lw=2,
            label="torso",
        )
        axes[0].plot(
            initial[middle_ids, 0][order],
            initial[middle_ids, 1][order],
            "--",
            color="#8c8c8c",
            lw=1.5,
            label="shirt: initial",
        )
        axes[0].plot(
            final[middle_ids, 0][order],
            final[middle_ids, 1][order],
            color="#0072B2",
            lw=1.8,
            label="shirt: equilibrium",
        )
        axes[0].set_aspect("equal")
        axes[0].set_xlabel("x (mm)")
        axes[0].set_ylabel("y (mm)")
        axes[0].set_title("(a) Mid-torso equilibrium")
        axes[0].legend(frameon=False, fontsize=8)

        scatter = axes[1].scatter(
            theta_face,
            z_face,
            c=pressure * 1000.0,
            s=13,
            cmap="viridis",
            vmin=0,
        )
        axes[1].set_xlabel("circumferential angle (degrees)")
        axes[1].set_ylabel("height from hem (mm)")
        axes[1].set_title("(b) Contact pressure (kPa)")
        # The panel title already carries the pressure unit; omitting a second
        # rotated label prevents collision with panel (c) at journal width.
        fig.colorbar(scatter, ax=axes[1], shrink=0.85)

        absolute_gap_um = np.abs(active_gap) * 1000.0
        axes[2].hist(absolute_gap_um, bins=20, color="#D55E00", alpha=0.85)
        axes[2].set_xlabel("absolute active-facet gap (µm)")
        axes[2].set_ylabel("facet count")
        axes[2].set_title("(c) Active-contact gap audit")

        fig.suptitle(
            f"Garment contact verification: {active.sum()}/{len(active)} active facets; "
            f"max pressure {active_pressure.max() * 1000:.3g} kPa"
        )
        fig.savefig(figure_path, dpi=300)
        plt.close(fig)
    print(json.dumps(summary, indent=2))
    print(f"Wrote {summary_path}")
    if not args.no_figure:
        print(f"Wrote {figure_path}")


if __name__ == "__main__":
    main()
