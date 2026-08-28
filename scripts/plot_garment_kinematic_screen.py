#!/usr/bin/env python3
"""Plot normalized sensor geometry and posture-by-sensor kinematic signatures."""

from __future__ import annotations

import csv
import json
import math
import os
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/private/tmp/matplotlib-garment-movement")
os.environ.setdefault("MPLBACKEND", "Agg")

import matplotlib.pyplot as plt
from matplotlib.patches import Polygon, Rectangle
import numpy as np


ROOT = Path(__file__).resolve().parents[1]


SHIRT_LENGTH_MM = 720.0
CHEST_WIDTH_MM = 540.0


def panel_outline() -> np.ndarray:
    """Photograph-scaled, deliberately simplified flat T-shirt outline (mm)."""
    return np.array([
        [-255, 0], [255, 0], [270, 500], [360, 525], [380, 600],
        [255, 650], [210, 700], [100, 720], [75, 690], [-75, 690],
        [-100, 720], [-210, 700], [-255, 650], [-380, 600],
        [-360, 525], [-270, 500],
    ])


def main() -> None:
    layout = json.loads((ROOT / "references" / "garment_layout_normalized.json").read_text())
    fig, axes = plt.subplots(1, 2, figsize=(7.4, 5.2), constrained_layout=True)
    for ax, panel in zip(axes, ["front", "back"]):
        ax.add_patch(Polygon(panel_outline(), closed=True, facecolor="#f7f7f7", edgecolor="0.25"))
        for sensor in layout["sensors"]:
            if sensor["panel"] != panel:
                continue
            x_mm = sensor["x"] * CHEST_WIDTH_MM
            y_mm = sensor["y"] * SHIRT_LENGTH_MM
            width, height = 80.0, 15.0
            rect = Rectangle(
                (x_mm - width / 2, y_mm - height / 2), width, height,
                angle=sensor["angle_deg"], rotation_point="center",
                facecolor="#252525", edgecolor="none",
            )
            ax.add_patch(rect)
            ax.text(x_mm, y_mm + 28, f"S{sensor['sensor']}",
                    ha="center", va="center", color="#cb181d", weight="bold")
        if panel == "front":
            ax.annotate("", xy=(-410, 0), xytext=(-410, SHIRT_LENGTH_MM),
                        arrowprops={"arrowstyle": "<->", "color": "0.3"})
            ax.text(-423, SHIRT_LENGTH_MM / 2, r"$\approx$720 mm",
                    rotation=90, ha="center", va="center", color="0.25")
            ax.annotate("", xy=(-CHEST_WIDTH_MM / 2, 485),
                        xytext=(CHEST_WIDTH_MM / 2, 485),
                        arrowprops={"arrowstyle": "<->", "color": "0.3"})
            ax.text(0, 468, r"$\approx$540 mm", ha="center", va="top", color="0.25")
        ax.set(xlim=(-440, 440), ylim=(-25, 760), aspect="equal", title=panel.capitalize())
        ax.axis("off")
    fig.suptitle("Photograph-scaled shirt outline with canonical ten-sensor layout")
    fig.savefig(ROOT / "figures" / "garment_layout_normalized.png", dpi=300)
    plt.close(fig)

    rows = list(csv.DictReader((ROOT / "results" / "garment_kinematic_screen.csv").open()))
    postures = list(dict.fromkeys(row["posture"] for row in rows))[1:]
    sensors = list(range(1, 11))
    matrix = np.array([
        [100.0 * float(next(
            row["projected_sensor_axis_strain"] for row in rows
            if row["posture"] == posture and int(row["sensor"]) == sensor
        )) for sensor in sensors]
        for posture in postures
    ])
    limit = float(np.max(np.abs(matrix)))
    fig, ax = plt.subplots(figsize=(9.0, 4.8), constrained_layout=True)
    image = ax.imshow(matrix, cmap="RdBu_r", vmin=-limit, vmax=limit, aspect="auto")
    ax.set_xticks(range(10), [f"S{i}" for i in sensors])
    ax.set_yticks(range(len(postures)), [p.replace("_", " ") for p in postures])
    for row_index in range(matrix.shape[0]):
        for column_index in range(matrix.shape[1]):
            value = matrix[row_index, column_index]
            ax.text(
                column_index,
                row_index,
                f"{value:.1f}",
                ha="center",
                va="center",
                fontsize=6.5,
                color="white" if abs(value) > 0.55 * limit else "black",
            )
    ax.set_xlabel("Sensor in canonical layout")
    ax.set_title("Projected local strain from compatible kinematic fields")
    fig.colorbar(image, ax=ax, label="Projected sensor-axis strain (%)")
    fig.savefig(ROOT / "figures" / "garment_kinematic_signatures.png", dpi=300)
    plt.close(fig)
    print("Wrote normalized layout and kinematic signature figures")


if __name__ == "__main__":
    main()
