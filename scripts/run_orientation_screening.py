#!/usr/bin/env python3
"""Reduced-order orientation screen based on planar strain-rosette mechanics."""

from __future__ import annotations

import csv
import itertools
import json
import math
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
CANDIDATE_ANGLES_DEG = tuple(range(-75, 91, 15))
CANONICAL_STATES = {
    "horizontal_extension": {"exx": 0.30, "eyy": -0.09, "gamma_xy": 0.00},
    "vertical_extension": {"exx": -0.09, "eyy": 0.30, "gamma_xy": 0.00},
    "positive_shear": {"exx": 0.08, "eyy": 0.04, "gamma_xy": 0.20},
    "negative_shear": {"exx": 0.08, "eyy": 0.04, "gamma_xy": -0.20},
    "biaxial_extension": {"exx": 0.18, "eyy": 0.12, "gamma_xy": 0.00},
}


def orientation_row(angle_deg: float) -> np.ndarray:
    theta = math.radians(angle_deg)
    c, s = math.cos(theta), math.sin(theta)
    return np.array([c * c, s * s, s * c])


def main() -> None:
    taper_summary = json.loads(
        (ROOT / "results" / "taper_5mm_local_medium_summary.json").read_text()
    )
    transfer = float(taper_summary["strain_transfer_ratio"])

    rows = []
    for angle in CANDIDATE_ANGLES_DEG:
        projection = orientation_row(angle)
        for state_name, state in CANONICAL_STATES.items():
            tensor_vector = np.array([state["exx"], state["eyy"], state["gamma_xy"]])
            projected_textile_strain = float(projection @ tensor_vector)
            finite_directional_engineering_strain = math.sqrt(
                1.0 + 2.0 * projected_textile_strain
            ) - 1.0
            rows.append(
                {
                    "angle_deg": angle,
                    "strain_state": state_name,
                    **state,
                    "projected_textile_strain": projected_textile_strain,
                    "screening_transfer_ratio": transfer,
                    "predicted_mean_gauge_strain": transfer * projected_textile_strain,
                    "finite_directional_engineering_strain": finite_directional_engineering_strain,
                    "predicted_endpoint_strain_finite_directional": (
                        transfer * finite_directional_engineering_strain
                    ),
                }
            )

    subsets = []
    for count in (3, 4, 5):
        for angles in itertools.combinations(CANDIDATE_ANGLES_DEG, count):
            matrix = np.vstack([orientation_row(angle) for angle in angles])
            singular_values = np.linalg.svd(matrix, compute_uv=False)
            if singular_values[-1] < 1e-12:
                continue
            condition_number = float(singular_values[0] / singular_values[-1])
            information = matrix.T @ matrix
            subsets.append(
                {
                    "sensor_count": count,
                    "angles_deg": list(angles),
                    "condition_number": condition_number,
                    "determinant_information_matrix": float(np.linalg.det(information)),
                }
            )
    subsets.sort(
        key=lambda item: (
            item["sensor_count"],
            -item["determinant_information_matrix"],
            item["condition_number"],
        )
    )
    best_by_count = {
        str(count): max(
            (item for item in subsets if item["sensor_count"] == count),
            key=lambda item: (
                item["determinant_information_matrix"],
                -item["condition_number"],
            ),
        )
        for count in (3, 4, 5)
    }

    results = ROOT / "results"
    with (results / "orientation_screening.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    output = {
        "method": "first-order observation matrix for identifiability; response heatmap uses exact directional engineering stretch from canonical tensors interpreted as Green strain, multiplied by the 5 mm taper screening transfer ratio",
        "candidate_angles_deg": list(CANDIDATE_ANGLES_DEG),
        "transfer_ratio": transfer,
        "canonical_states": CANONICAL_STATES,
        "best_subsets_by_sensor_count": best_by_count,
        "top_ten_three_sensor_subsets_by_information": [
            item for item in subsets if item["sensor_count"] == 3
        ][:10],
        "limitations": [
            "not a rotated full-field FEBio model",
            "assumes angle-independent scalar strain-transfer ratio",
            "canonical strain states are basis cases, not measured garment movements",
        ],
    }
    (results / "orientation_screening.json").write_text(json.dumps(output, indent=2) + "\n")
    print(json.dumps(best_by_count, indent=2))


if __name__ == "__main__":
    main()
