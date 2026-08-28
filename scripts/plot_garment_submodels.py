#!/usr/bin/env python3
"""Plot garment kinematic strain against resolved full-field gauge strain."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    data = json.loads((ROOT / "results" / "garment_submodels.json").read_text())
    rows = data["rows"]
    x = np.array([100 * row["kinematic_projected_sensor_axis_strain"] for row in rows])
    y = np.array([100 * row["fullfield_mean_gauge_strain"] for row in rows])
    labels = [
        "left arm raise (S3)", "mirrored twists (S9/S10)", "",
        "both arms raise (S3)", "forward bend (S8)", "sitting (S5)",
    ]
    colors = ["#3182bd", "#756bb1", "#756bb1", "#31a354", "#e6550d", "#636363"]
    offsets = [(-5, -25), (10, 8), (0, 0), (10, 5), (10, 5), (10, 5)]

    fig, ax = plt.subplots(figsize=(7.4, 5.0), constrained_layout=True)
    for x_value, y_value, label, color, offset in zip(x, y, labels, colors, offsets):
        ax.scatter(x_value, y_value, s=58, color=color, zorder=3)
        if label:
            ax.annotate(label, (x_value, y_value), xytext=offset,
                        textcoords="offset points", fontsize=8)
    line_x = np.linspace(0, 1.08 * max(x), 100)
    ax.plot(line_x, 100 * data["zero_intercept_slope"] * line_x / 100,
            color="0.25", linewidth=1.2, linestyle="--",
            label=f"Zero-intercept slope = {100 * data['zero_intercept_slope']:.2f}%")
    ax.set_xlim(left=0)
    ax.set_ylim(bottom=0)
    ax.set_xlabel("Local sensor-axis strain from garment kinematics (%)")
    ax.set_ylabel("Full-field conductive-gauge strain (%)")
    ax.set_title("Multiscale garment-to-sensor transfer")
    ax.legend(frameon=False, loc="upper left")
    fig.savefig(ROOT / "figures" / "garment_submodel_transfer.png", dpi=300)
    plt.close(fig)
    print("Wrote garment submodel transfer figure")


if __name__ == "__main__":
    main()
