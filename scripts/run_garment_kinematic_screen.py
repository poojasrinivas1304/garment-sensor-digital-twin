#!/usr/bin/env python3
"""Screen the Figure-2 sensor layout under compatible normalized garment motions.

This is a kinematic pre-screen, not a body-contact or calibrated cloth model.
Each strain field is obtained by differentiating a continuous displacement field.
"""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
LAYOUT = ROOT / "references" / "garment_layout_normalized.json"
POSTURES = (
    "standing_straight",
    "left_arm_raise",
    "right_arm_raise",
    "left_shoulder_touch_twist",
    "right_shoulder_touch_twist",
    "both_arms_raise",
    "forward_bend",
    "sitting",
)


def anatomical_x(panel: str, side: str) -> float:
    """Return image-coordinate shoulder location for anatomical side."""
    if panel == "front":
        return 0.34 if side == "left" else -0.34
    return -0.34 if side == "left" else 0.34


def displacement(posture: str, panel: str, x: float, y: float) -> tuple[float, float]:
    """Illustrative dimensionless in-plane displacement field."""
    if posture == "standing_straight":
        return 0.0, 0.0

    if posture in {"left_arm_raise", "right_arm_raise"}:
        side = posture.split("_")[0]
        x0 = anatomical_x(panel, side)
        side_sign = 1.0 if x0 > 0 else -1.0
        weight = math.exp(-((x - x0) / 0.34) ** 2) * y**2
        return 0.018 * side_sign * weight, 0.065 * weight

    if posture in {"left_shoulder_touch_twist", "right_shoulder_touch_twist"}:
        side = posture.split("_")[0]
        x0 = anatomical_x(panel, side)
        twist_sign = 1.0 if side == "left" else -1.0
        panel_sign = 1.0 if panel == "front" else -1.0
        local = math.exp(-((x - x0) / 0.42) ** 2) * y**2
        u = twist_sign * panel_sign * 0.055 * y + 0.012 * np.sign(x0) * local
        v = twist_sign * panel_sign * 0.030 * x * y + 0.035 * local
        return float(u), float(v)

    if posture == "both_arms_raise":
        shoulder_weight = 0.55 + 1.8 * x**2
        return 0.025 * x * y, 0.060 * y**2 * shoulder_weight

    if posture == "forward_bend":
        if panel == "back":
            return 0.030 * x * y, 0.080 * y
        return -0.010 * x * y, -0.030 * y

    if posture == "sitting":
        lower = math.exp(-(y / 0.38) ** 2)
        panel_sign = 1.0 if panel == "front" else 0.75
        return panel_sign * 0.050 * x * lower, -panel_sign * 0.045 * y * lower

    raise ValueError(posture)


def strain_tensor(posture: str, panel: str, x: float, y: float) -> tuple[float, float, float]:
    h = 1e-5
    ux_plus, vx_plus = displacement(posture, panel, x + h, y)
    ux_minus, vx_minus = displacement(posture, panel, x - h, y)
    uy_plus, vy_plus = displacement(posture, panel, x, y + h)
    uy_minus, vy_minus = displacement(posture, panel, x, y - h)
    du_dx = (ux_plus - ux_minus) / (2 * h)
    du_dy = (uy_plus - uy_minus) / (2 * h)
    dv_dx = (vx_plus - vx_minus) / (2 * h)
    dv_dy = (vy_plus - vy_minus) / (2 * h)
    return du_dx, dv_dy, du_dy + dv_dx


def projected_strain(exx: float, eyy: float, gamma_xy: float, angle_deg: float) -> float:
    theta = math.radians(angle_deg)
    c, s = math.cos(theta), math.sin(theta)
    return exx * c * c + eyy * s * s + gamma_xy * s * c


def main() -> None:
    layout = json.loads(LAYOUT.read_text())
    rows = []
    for posture in POSTURES:
        for sensor in layout["sensors"]:
            exx, eyy, gamma = strain_tensor(
                posture, sensor["panel"], sensor["x"], sensor["y"]
            )
            tensor = np.array([[exx, 0.5 * gamma], [0.5 * gamma, eyy]])
            eigenvalues, eigenvectors = np.linalg.eigh(tensor)
            major_index = int(np.argmax(eigenvalues))
            vector = eigenvectors[:, major_index]
            major_angle = math.degrees(math.atan2(vector[1], vector[0]))
            gauge_projection = projected_strain(exx, eyy, gamma, sensor["angle_deg"])
            rows.append(
                {
                    "posture": posture,
                    "sensor": sensor["sensor"],
                    "panel": sensor["panel"],
                    "sensor_angle_deg": sensor["angle_deg"],
                    "exx": exx,
                    "eyy": eyy,
                    "gamma_xy_engineering": gamma,
                    "major_principal_strain": eigenvalues[major_index],
                    "minor_principal_strain": eigenvalues[1 - major_index],
                    "major_principal_angle_deg": major_angle,
                    "projected_sensor_axis_strain": gauge_projection,
                }
            )

    results = ROOT / "results"
    with (results / "garment_kinematic_screen.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    rankings = {}
    for posture in POSTURES[1:]:
        candidates = [row for row in rows if row["posture"] == posture]
        candidates.sort(key=lambda row: abs(row["projected_sensor_axis_strain"]), reverse=True)
        rankings[posture] = [
            {
                "sensor": row["sensor"],
                "panel": row["panel"],
                "projected_sensor_axis_strain": row["projected_sensor_axis_strain"],
            }
            for row in candidates
        ]
    (results / "garment_kinematic_screen.json").write_text(
        json.dumps(
            {
                "status": "normalized compatible-displacement kinematic screen; not calibrated garment mechanics",
                "layout_source": "manuscript Figure 2",
                "mapping_conflict": layout["mapping_conflict"],
                "rankings": rankings,
            },
            indent=2,
        ) + "\n"
    )
    for posture, ranking in rankings.items():
        top = ", ".join(f"S{item['sensor']}" for item in ranking[:3])
        print(f"{posture}: {top}")


if __name__ == "__main__":
    main()
