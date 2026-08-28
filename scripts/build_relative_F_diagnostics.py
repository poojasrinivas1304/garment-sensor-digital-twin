#!/usr/bin/env python3
"""Report admissibility and polar-decomposition diagnostics for transferred F."""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
PAIRS = {
    "full garment, no contact": (
        "matched_no_contact_0p6_reference",
        "matched_no_contact_0p6_movement025",
    ),
    "full garment, contact": (
        "garment_fit_torso_expand_060mm_manual",
        "garment_both_arms_raise_025",
    ),
}
SENSORS = (3, 8, 9, 10)
MIRROR = {3: 8, 8: 3, 9: 10, 10: 9}


def load_rows(case: str) -> dict[int, dict]:
    path = ROOT / "results" / f"{case}_movement_summary.json"
    data = json.loads(path.read_text())
    return {int(row["sensor"]): row for row in data["sensor_strains"]}


def rotation_degrees(f: np.ndarray) -> float:
    u, _, vt = np.linalg.svd(f)
    r = u @ vt
    if np.linalg.det(r) < 0.0:
        u[:, -1] *= -1.0
        r = u @ vt
    cosine = np.clip((np.trace(r) - 1.0) / 2.0, -1.0, 1.0)
    return math.degrees(math.acos(float(cosine)))


def main() -> None:
    rows: list[dict] = []
    for state, (fit_case, move_case) in PAIRS.items():
        fitted = load_rows(fit_case)
        moved = load_rows(move_case)
        state_values: dict[int, float] = {}
        state_matrices: dict[int, tuple[np.ndarray, np.ndarray, np.ndarray]] = {}
        for sensor in SENSORS:
            f_fit = np.asarray(
                fitted[sensor]["deformation_gradient_sensor_basis"], dtype=float
            )
            f_move = np.asarray(
                moved[sensor]["deformation_gradient_sensor_basis"], dtype=float
            )
            f_rel = f_move @ np.linalg.inv(f_fit)
            e_rel = 0.5 * (f_rel.T @ f_rel - np.eye(3))
            state_values[sensor] = 100.0 * float(e_rel[0, 0])
            state_matrices[sensor] = (f_fit, f_move, f_rel)
        for sensor in (3, 9):
            f_fit, f_move, f_rel = state_matrices[sensor]
            stretches = np.sort(np.linalg.svd(f_rel, compute_uv=False))[::-1]
            rows.append(
                {
                    "state": state,
                    "sensor": f"S{sensor}",
                    "det_F_fit": float(np.linalg.det(f_fit)),
                    "det_F_move": float(np.linalg.det(f_move)),
                    "det_F_rel": float(np.linalg.det(f_rel)),
                    "principal_stretch_1": float(stretches[0]),
                    "principal_stretch_2": float(stretches[1]),
                    "principal_stretch_3": float(stretches[2]),
                    "polar_rotation_deg": rotation_degrees(f_rel),
                    "relative_axis_green_percent": state_values[sensor],
                    "mirror_pair_absolute_difference_percentage_points": abs(
                        state_values[sensor] - state_values[MIRROR[sensor]]
                    ),
                }
            )

    csv_path = ROOT / "results" / "relative_F_diagnostics.csv"
    with csv_path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    json_path = ROOT / "results" / "relative_F_diagnostics.json"
    json_path.write_text(
        json.dumps(
            {
                "definition": "F_rel = F_move @ inverse(F_fit)",
                "rotation": "proper orthogonal factor from an SVD polar decomposition",
                "principal_stretches": "singular values of F_rel in descending order",
                "rows": rows,
            },
            indent=2,
        )
        + "\n"
    )
    print(f"Wrote {csv_path}")
    print(f"Wrote {json_path}")


if __name__ == "__main__":
    main()
