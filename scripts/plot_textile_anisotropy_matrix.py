#!/usr/bin/env python3
"""Create the publication Figure 7 textile-anisotropy response matrix."""

from __future__ import annotations

import csv
import os
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/private/tmp/matplotlib-contact-sensor")
os.environ.setdefault("MPLBACKEND", "Agg")

import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, Rectangle


ROOT = Path(__file__).resolve().parents[1]

BLUE = "#3F7198"
BLUE_FILL = "#A9C9E2"
LAVENDER = "#756A9B"
CORAL = "#A45751"
CORAL_FILL = "#E9AAA4"
SLATE = "#5C6670"
GREY_FILL = "#D9DEE2"
GRID = "#E7EBEE"
PAPER = "#FCFDFD"


def main() -> None:
    rows = list(csv.DictReader((ROOT / "results" / "textile_anisotropy.csv").open()))

    def get(case: str, angle: float, field: str) -> float:
        return float(next(
            row[field] for row in rows
            if row["material_case"] == case
            and float(row["loading_angle_deg"]) == angle
        ))

    cases = ["textile_fiber_balanced", "textile_fiber_x3", "textile_fiber_y3"]
    case_titles = ["Balanced", "x-fiber dominant", "y-fiber dominant"]
    ratios = ["1:1 stiffness", "3:1 stiffness", "1:3 stiffness"]
    angles = [0.0, 60.0]
    row_titles = ["Aligned", "Diagonal"]
    fills = [GREY_FILL, BLUE_FILL, CORAL_FILL]
    edges = [SLATE, BLUE, CORAL]

    transfer = {
        (case, angle): 100 * get(case, angle, "strain_transfer_vs_major_strain")
        for case in cases for angle in angles
    }
    changes = {
        (case, angle): get(case, angle, "change_vs_balanced_percent")
        for case in cases for angle in angles
    }

    plt.rcParams.update({
        "font.family": "sans-serif",
        "font.size": 9.2,
        "axes.linewidth": 0.8,
    })
    fig, ax = plt.subplots(figsize=(8.2, 5.0), constrained_layout=True)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    ax.text(0.5, 0.975, "Directional textile stiffness controls strain transfer",
            ha="center", va="top", fontsize=12, weight="semibold", color=SLATE)
    ax.text(0.015, 0.885, "a", weight="bold", fontsize=11, color=SLATE)
    ax.text(0.045, 0.885, "Simulated strain transfer", weight="semibold", color=SLATE)

    left = 0.22
    col_w = 0.245
    gap = 0.012
    centers = [left + col_w / 2 + i * (col_w + gap) for i in range(3)]
    row_bottoms = [0.58, 0.365]
    cell_h = 0.16

    # Column headers and compact fiber-direction schematics.
    for index, (cx, title, ratio, edge) in enumerate(zip(centers, case_titles, ratios, edges)):
        ax.text(cx, 0.895, title, ha="center", va="bottom", weight="semibold", color=SLATE)
        ax.text(cx, 0.858, ratio, ha="center", va="top", fontsize=7.8, color=SLATE)
        icon_y = 0.795
        if index == 0:
            for offset in (-0.018, 0.0, 0.018):
                ax.plot([cx - 0.036, cx + 0.036], [icon_y + offset, icon_y + offset], color=edge, lw=1.5)
                ax.plot([cx + offset, cx + offset], [icon_y - 0.032, icon_y + 0.032], color=edge, lw=1.5)
        elif index == 1:
            for offset in (-0.018, 0.0, 0.018):
                ax.plot([cx - 0.042, cx + 0.042], [icon_y + offset, icon_y + offset], color=edge, lw=2.2)
            for offset in (-0.020, 0.020):
                ax.plot([cx + offset, cx + offset], [icon_y - 0.032, icon_y + 0.032], color=edge, lw=0.8, alpha=0.7)
        else:
            for offset in (-0.018, 0.0, 0.018):
                ax.plot([cx + offset, cx + offset], [icon_y - 0.038, icon_y + 0.038], color=edge, lw=2.2)
            for offset in (-0.018, 0.018):
                ax.plot([cx - 0.040, cx + 0.040], [icon_y + offset, icon_y + offset], color=edge, lw=0.8, alpha=0.7)

    # Row schematics and six response cells.
    for row_index, (angle, title, y0) in enumerate(zip(angles, row_titles, row_bottoms)):
        sensor_x, sensor_y = 0.07, y0 + cell_h / 2
        ax.add_patch(Rectangle((sensor_x, sensor_y - 0.014), 0.055, 0.028,
                               facecolor=GREY_FILL, edgecolor=SLATE, linewidth=0.9))
        if angle == 0:
            ax.add_patch(FancyArrowPatch((0.035, sensor_y), (sensor_x - 0.005, sensor_y),
                                         arrowstyle="-|>", mutation_scale=8, color=SLATE, lw=0.9))
            ax.add_patch(FancyArrowPatch((sensor_x + 0.060, sensor_y), (0.165, sensor_y),
                                         arrowstyle="-|>", mutation_scale=8, color=SLATE, lw=0.9))
        else:
            ax.add_patch(FancyArrowPatch((0.052, sensor_y - 0.045), (sensor_x - 0.002, sensor_y - 0.005),
                                         arrowstyle="-|>", mutation_scale=8, color=SLATE, lw=0.9))
            ax.add_patch(FancyArrowPatch((sensor_x + 0.057, sensor_y + 0.005), (0.145, sensor_y + 0.055),
                                         arrowstyle="-|>", mutation_scale=8, color=SLATE, lw=0.9))
        ax.text(0.02, sensor_y + 0.032, title, va="center", weight="semibold", color=SLATE)
        ax.text(0.02, sensor_y + 0.004, f"{int(angle)}° loading", va="center", fontsize=7.8, color=SLATE)

        for col_index, (case, fill, edge) in enumerate(zip(cases, fills, edges)):
            x0 = left + col_index * (col_w + gap)
            alpha = 0.73 if case != cases[0] and abs(changes[(case, angle)]) < 25 else 0.93
            ax.add_patch(Rectangle((x0, y0), col_w, cell_h, facecolor=fill,
                                   edgecolor=PAPER, linewidth=1.4, alpha=alpha))
            result = transfer[(case, angle)]
            result_text = f"{result:.3f}%" if angle == 60 else f"{result:.2f}%"
            ax.text(x0 + col_w / 2, y0 + 0.098, result_text, ha="center", va="center",
                    fontsize=12, weight="semibold", color=edge)
            if case == cases[0]:
                delta = "reference"
            else:
                delta = f"{changes[(case, angle)]:+.0f}% vs balanced"
            ax.text(x0 + col_w / 2, y0 + 0.047, delta, ha="center", va="center",
                    fontsize=8.1, color=edge)

    # Matrix frame and subtle dividers.
    matrix_top = row_bottoms[0] + cell_h
    matrix_bottom = row_bottoms[1]
    matrix_right = left + 3 * col_w + 2 * gap
    ax.add_patch(Rectangle((left, matrix_bottom), matrix_right - left, matrix_top - matrix_bottom,
                           fill=False, edgecolor=SLATE, linewidth=0.65))
    ax.plot([left, matrix_right], [0.55, 0.55], color=GRID, lw=0.8)
    ax.text(matrix_right, 0.335, "Cell colour: change from balanced", ha="right", va="top",
            fontsize=7.7, color=SLATE)
    legend_x = matrix_right - 0.29
    for x, fill, label in zip(
        [legend_x, legend_x + 0.09, legend_x + 0.18],
        [CORAL_FILL, GREY_FILL, BLUE_FILL],
        ["decrease", "reference", "increase"],
    ):
        ax.add_patch(Rectangle((x, 0.305), 0.012, 0.014, facecolor=fill, edgecolor="none"))
        ax.text(x + 0.017, 0.312, label, va="center", fontsize=7.2, color=SLATE)

    # Panel b: response contrast between x- and y-dominant cases.
    ax.plot([0.015, 0.985], [0.265, 0.265], color=GRID, lw=0.9)
    ax.text(0.015, 0.235, "b", weight="bold", fontsize=11, color=SLATE)
    ax.text(0.045, 0.235, "x/y response contrast", weight="semibold", color=SLATE)
    ax.text(0.245, 0.235, "maximum divided by minimum transfer", fontsize=7.8, color=SLATE)

    contrast_y = [0.17, 0.095]
    for angle, title, y in zip(angles, row_titles, contrast_y):
        y_val = transfer[(cases[2], angle)]
        b_val = transfer[(cases[0], angle)]
        x_val = transfer[(cases[1], angle)]
        position = (b_val - y_val) / (x_val - y_val)
        x_start, x_end = 0.20, 0.79
        ax.plot([x_start, x_end], [y, y], color=LAVENDER, lw=1.7)
        ax.scatter([x_start, x_start + position * (x_end - x_start), x_end], [y, y, y],
                   s=[42, 36, 42], c=[CORAL, SLATE, BLUE], edgecolors=PAPER, linewidths=0.6, zorder=4)
        ax.text(0.02, y, f"{title}  {int(angle)}°", va="center", weight="semibold", color=SLATE)
        decimals = 3 if angle == 60 else 2
        ax.text(x_start, y - 0.035, f"y: {y_val:.{decimals}f}%", ha="center", fontsize=7.4, color=CORAL)
        ax.text(x_start + position * (x_end - x_start), y - 0.035,
                f"balanced: {b_val:.{decimals}f}%", ha="center", fontsize=7.4, color=SLATE)
        ax.text(x_end, y - 0.035, f"x: {x_val:.{decimals}f}%", ha="center", fontsize=7.4, color=BLUE)
        ax.text(0.91, y, f"{x_val / y_val:.2f}×", ha="center", va="center",
                fontsize=11, weight="semibold", color=SLATE)

    ax.text(0.985, 0.018, "Illustrative directional-stiffness ratios; materials mechanically uncalibrated.",
            ha="right", va="bottom", fontsize=7.5, color=SLATE, style="italic")

    for suffix, kwargs in (("png", {"dpi": 450}), ("jpg", {"dpi": 450, "pil_kwargs": {"quality": 95}})):
        output = ROOT / "figures" / f"textile_anisotropy.{suffix}"
        fig.savefig(output, bbox_inches="tight", facecolor="white", **kwargs)
        print(f"Wrote {output}")
    plt.close(fig)


if __name__ == "__main__":
    main()
