#!/usr/bin/env python3
"""Plot orientation signatures for canonical planar garment strain states."""

from __future__ import annotations

import csv
import os
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/private/tmp/matplotlib-contact-sensor")
os.environ.setdefault("MPLBACKEND", "Agg")

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm


ROOT = Path(__file__).resolve().parents[1]

BLUE = "#3F7198"
BLUE_FILL = "#A9C9E2"
TEAL = "#347E73"
TEAL_FILL = "#9FD3C7"
CORAL = "#A45751"
CORAL_FILL = "#E9AAA4"
SLATE = "#5C6670"


STATE_LABELS = {
    "horizontal_extension": "Horizontal extension",
    "vertical_extension": "Vertical extension",
    "positive_shear": "Positive shear (+γ)",
    "negative_shear": "Negative shear (−γ)",
    "biaxial_extension": "Biaxial extension",
}


def main() -> None:
    rows = list(csv.DictReader((ROOT / "results" / "orientation_screening.csv").open()))
    angles = sorted({int(row["angle_deg"]) for row in rows})
    states = list(dict.fromkeys(row["strain_state"] for row in rows))
    matrix = np.array(
        [
            [
                100.0 * float(next(
                    row["predicted_endpoint_strain_finite_directional"]
                    for row in rows
                    if int(row["angle_deg"]) == angle and row["strain_state"] == state
                ))
                for angle in angles
            ]
            for state in states
        ]
    )
    plt.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.size": 9.5,
            "axes.labelsize": 10,
            "xtick.labelsize": 8.5,
            "ytick.labelsize": 9,
            "axes.linewidth": 0.8,
        }
    )
    fig, (ax, contrast_ax) = plt.subplots(
        2,
        1,
        figsize=(8.2, 5.7),
        gridspec_kw={"height_ratios": [1.9, 1.0]},
        constrained_layout=True,
    )
    limit = float(np.max(np.abs(matrix)))
    pastel_diverging = LinearSegmentedColormap.from_list(
        "pastel_strain",
        [CORAL, CORAL_FILL, "#FBFAF7", TEAL_FILL, BLUE],
        N=256,
    )
    norm = TwoSlopeNorm(vmin=-limit, vcenter=0.0, vmax=limit)
    image = ax.imshow(matrix, cmap=pastel_diverging, norm=norm, aspect="auto")
    ax.set_xticks(range(len(angles)), [f"{angle}°" for angle in angles])
    ax.set_yticks(range(len(states)), [STATE_LABELS[state] for state in states])
    ax.tick_params(length=0)
    ax.set_xlabel("Sensor orientation, θ")
    ax.set_xticks(np.arange(-0.5, len(angles), 1), minor=True)
    ax.set_yticks(np.arange(-0.5, len(states), 1), minor=True)
    ax.grid(which="minor", color="white", linewidth=1.4)
    ax.tick_params(which="minor", bottom=False, left=False)
    for row_index in range(matrix.shape[0]):
        for column_index in range(matrix.shape[1]):
            value = matrix[row_index, column_index]
            color = "white" if abs(value) > 0.62 * limit else "#344047"
            ax.text(
                column_index,
                row_index,
                f"{value:+.2f}",
                ha="center",
                va="center",
                fontsize=7.1,
                color=color,
                fontweight="semibold" if abs(value) > 0.60 * limit else "normal",
            )
    colorbar = fig.colorbar(image, ax=ax, pad=0.012, fraction=0.035)
    colorbar.set_label("Predicted endpoint strain (%)")
    colorbar.outline.set_edgecolor("#AAB3B8")
    ax.text(-0.055, 1.03, "a", transform=ax.transAxes, va="bottom", weight="bold", fontsize=11)
    ax.text(
        1.0,
        1.03,
        "Finite directional-stretch endpoint screen",
        transform=ax.transAxes,
        ha="right",
        va="bottom",
        color=SLATE,
        fontsize=8.5,
        weight="semibold",
    )

    # Panel b: the differential response is the observable that distinguishes
    # the signs of otherwise matched shear states.
    positive = matrix[states.index("positive_shear")]
    negative = matrix[states.index("negative_shear")]
    shear_contrast = positive - negative
    contrast_ax.set_facecolor("#FCFDFD")
    contrast_ax.axhline(0.0, color=SLATE, linewidth=0.9, zorder=1)
    contrast_ax.fill_between(
        angles,
        shear_contrast,
        0,
        where=shear_contrast >= 0,
        color=TEAL_FILL,
        alpha=0.58,
        interpolate=True,
    )
    contrast_ax.fill_between(
        angles,
        shear_contrast,
        0,
        where=shear_contrast < 0,
        color=CORAL_FILL,
        alpha=0.58,
        interpolate=True,
    )
    contrast_ax.plot(angles, shear_contrast, color=SLATE, linewidth=1.8, marker="o",
                     markerfacecolor="white", markeredgecolor=SLATE, markersize=4.5, zorder=3)
    diagonal_indices = [angles.index(-45), angles.index(45)]
    contrast_ax.scatter(
        [angles[i] for i in diagonal_indices],
        [shear_contrast[i] for i in diagonal_indices],
        s=66,
        marker="D",
        facecolor=[CORAL_FILL, TEAL_FILL],
        edgecolor=[CORAL, TEAL],
        linewidth=1.4,
        zorder=4,
    )
    contrast_ax.annotate(
        f"−45°: {shear_contrast[diagonal_indices[0]]:+.2f}%",
        xy=(-45, shear_contrast[diagonal_indices[0]]),
        xytext=(-68, -0.42),
        color=CORAL,
        fontsize=8.1,
        arrowprops={"arrowstyle": "->", "color": CORAL, "lw": 0.9},
    )
    contrast_ax.annotate(
        f"+45°: {shear_contrast[diagonal_indices[1]]:+.2f}%",
        xy=(45, shear_contrast[diagonal_indices[1]]),
        xytext=(18, 0.45),
        color=TEAL,
        fontsize=8.1,
        arrowprops={"arrowstyle": "->", "color": TEAL, "lw": 0.9},
    )
    contrast_ax.text(
        0,
        0.075,
        "Axial sensors (0°, 90°):\nno shear-sign contrast",
        ha="center",
        va="bottom",
        fontsize=7.8,
        color=SLATE,
        bbox={"boxstyle": "round,pad=0.25", "facecolor": "#EDF0F2", "edgecolor": "none"},
    )
    contrast_ax.set_xticks(angles, [f"{angle}°" for angle in angles])
    contrast_ax.set_xlabel("Sensor orientation, θ")
    contrast_ax.set_ylabel("Shear-sign contrast\n(+γ minus −γ) (%)")
    contrast_ax.set_ylim(-0.72, 0.72)
    contrast_ax.grid(axis="y", color="#DCE3E7", linewidth=0.7)
    contrast_ax.spines["top"].set_visible(False)
    contrast_ax.spines["right"].set_visible(False)
    contrast_ax.spines["left"].set_color(SLATE)
    contrast_ax.spines["bottom"].set_color(SLATE)
    contrast_ax.text(-0.055, 1.03, "b", transform=contrast_ax.transAxes, va="bottom", weight="bold", fontsize=11)

    for suffix, kwargs in (("png", {"dpi": 450}), ("jpg", {"dpi": 450, "pil_kwargs": {"quality": 95}})):
        output = ROOT / "figures" / f"orientation_screening.{suffix}"
        fig.savefig(output, bbox_inches="tight", facecolor="white", **kwargs)
        print(f"Wrote {output}")


if __name__ == "__main__":
    main()
