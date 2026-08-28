#!/usr/bin/env python3
"""Create publication Figure 9 with the manuscript diverging palette."""

from __future__ import annotations

import csv
import os
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/private/tmp/matplotlib-kinematic-signatures")
os.environ.setdefault("MPLBACKEND", "Agg")

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm


ROOT = Path(__file__).resolve().parents[1]

BLUE = "#3F7198"
BLUE_FILL = "#A9C9E2"
CORAL = "#A45751"
CORAL_FILL = "#E9AAA4"
SLATE = "#5C6670"
PAPER = "#FCFDFD"
GRID = "#E2E7EA"


def main() -> None:
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
    norm = TwoSlopeNorm(vmin=-limit, vcenter=0.0, vmax=limit)
    cmap = LinearSegmentedColormap.from_list(
        "manuscript_diverging",
        [CORAL, CORAL_FILL, PAPER, BLUE_FILL, BLUE],
        N=256,
    )

    plt.rcParams.update({
        "font.family": "sans-serif",
        "font.size": 9.3,
        "axes.labelsize": 9.8,
        "xtick.labelsize": 9.0,
        "ytick.labelsize": 9.0,
        "axes.linewidth": 0.8,
    })
    fig, ax = plt.subplots(figsize=(9.0, 4.8), constrained_layout=True)
    image = ax.imshow(matrix, cmap=cmap, norm=norm, aspect="auto", interpolation="nearest")
    ax.set_xticks(range(10), [f"S{i}" for i in sensors])
    ax.set_yticks(range(len(postures)), [p.replace("_", " ") for p in postures])
    ax.set_xlabel("Sensor in canonical layout")
    ax.set_ylabel("Compatible normalized displacement field")
    ax.set_title("Projected sensor-axis strain signatures", color=SLATE,
                 weight="semibold", pad=20)

    # Quiet structural separation between front (S1--S7) and back (S8--S10).
    ax.axvline(6.5, color=SLATE, linewidth=1.15)
    ax.text(3.0, -0.78, "Front sensors", ha="center", va="bottom",
            color=SLATE, fontsize=8.0, weight="semibold", clip_on=False)
    ax.text(8.0, -0.78, "Back sensors", ha="center", va="bottom",
            color=SLATE, fontsize=8.0, weight="semibold", clip_on=False)

    for row_index in range(matrix.shape[0]):
        for column_index in range(matrix.shape[1]):
            value = matrix[row_index, column_index]
            ax.text(
                column_index,
                row_index,
                f"{value:.1f}",
                ha="center",
                va="center",
                fontsize=7.7,
                color="white" if abs(value) > 0.62 * limit else SLATE,
                weight="semibold" if abs(value) > 0.62 * limit else "normal",
            )

    # Thin white cell boundaries improve legibility without creating a heavy grid.
    ax.set_xticks(np.arange(-0.5, 10, 1), minor=True)
    ax.set_yticks(np.arange(-0.5, len(postures), 1), minor=True)
    ax.grid(which="minor", color="white", linewidth=0.75)
    ax.tick_params(which="minor", bottom=False, left=False)
    for spine in ax.spines.values():
        spine.set_color(SLATE)
        spine.set_linewidth(0.8)

    colorbar = fig.colorbar(image, ax=ax, pad=0.035, fraction=0.038)
    colorbar.set_label("Projected sensor-axis strain (%)")
    colorbar.outline.set_edgecolor(SLATE)
    colorbar.outline.set_linewidth(0.75)
    colorbar.ax.axhline(0, color=SLATE, linewidth=0.75)

    for suffix, kwargs in (("png", {"dpi": 450}), ("jpg", {"dpi": 450, "pil_kwargs": {"quality": 95}})):
        output = ROOT / "figures" / f"garment_kinematic_signatures.{suffix}"
        fig.savefig(output, bbox_inches="tight", facecolor="white", **kwargs)
        print(f"Wrote {output}")
    plt.close(fig)


if __name__ == "__main__":
    main()
