#!/usr/bin/env python3
"""Plot the selected full-field check and textile anisotropy sensitivity."""

from __future__ import annotations

import csv
import os
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/private/tmp/matplotlib-contact-sensor")
os.environ.setdefault("MPLBACKEND", "Agg")

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Rectangle


ROOT = Path(__file__).resolve().parents[1]

BLUE = "#3F7198"
BLUE_FILL = "#A9C9E2"
LAVENDER = "#756A9B"
LAVENDER_FILL = "#C7B7DC"
CORAL = "#A45751"
CORAL_FILL = "#E9AAA4"
SLATE = "#5C6670"
GREY_FILL = "#D9DEE2"


def main() -> None:
    full = list(csv.DictReader((ROOT / "results" / "fullfield_orientation.csv").open()))
    full.sort(key=lambda row: float(row["loading_angle_deg"]))
    angles = [int(float(row["loading_angle_deg"])) for row in full]
    endpoint_values = [
        100 * float(row["conductive_gauge_endpoint_engineering_strain"])
        for row in full
    ]
    path_values = [
        100 * float(row["conductive_gauge_centroid_path_engineering_strain"])
        for row in full
    ]
    reduced_values = [100 * float(row["reduced_order_predicted_gauge_strain"]) for row in full]

    plt.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.size": 9.5,
            "axes.labelsize": 10,
            "xtick.labelsize": 9,
            "ytick.labelsize": 9,
            "axes.linewidth": 0.8,
        }
    )
    fig, (ax, detail) = plt.subplots(
        1,
        2,
        figsize=(8.2, 3.9),
        gridspec_kw={"width_ratios": [1.25, 1.0]},
        constrained_layout=True,
    )
    x = np.arange(len(angles))
    width = 0.23
    series = [
        (reduced_values, -width, "Scalar projection", GREY_FILL, SLATE),
        (endpoint_values, 0.0, "Full field: endpoint", BLUE_FILL, BLUE),
        (path_values, width, "Full field: path", LAVENDER_FILL, LAVENDER),
    ]
    ax.set_facecolor("#FCFDFD")
    for values, offset, label, fill, edge in series:
        bars = ax.bar(x + offset, values, width, label=label, color=fill, edgecolor=edge, linewidth=1.0, zorder=2)
        for index, (bar, value) in enumerate(zip(bars, values)):
            if abs(value) > 0.10:
                ax.text(bar.get_x() + bar.get_width() / 2, value + 0.035, f"{value:.2f}%",
                        ha="center", va="bottom", fontsize=7.8, color=edge)
    ax.axhline(0, color=SLATE, linewidth=0.85)
    ax.set_xticks(x, [f"{angle:+d}°" for angle in angles])
    ax.set_xlabel("Major-strain direction relative to sensor axis")
    ax.set_ylabel("Conductive-gauge strain (%)")
    ax.set_ylim(-0.10, 1.42)
    ax.grid(axis="y", color="#DCE3E7", linewidth=0.7)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(SLATE)
    ax.spines["bottom"].set_color(SLATE)
    ax.legend(frameon=False, fontsize=8.1, loc="upper left")
    ax.text(-0.07, 1.03, "a", transform=ax.transAxes, va="bottom", weight="bold", fontsize=11)
    # Mark the narrow range expanded in panel b without changing the scale of panel a.
    for center in (0.0, 2.0):
        zoom_box = Rectangle((center - 0.48, -0.035), 0.96, 0.105, facecolor="#FFF7E8", edgecolor=CORAL,
                             linewidth=1.0, linestyle=(0, (3, 2)), alpha=0.70)
        ax.add_patch(zoom_box)
    ax.text(-0.47, 0.085, "near-transverse; magnified in b", fontsize=7.3, color=CORAL, va="bottom")

    # Panel b: exact magnification of the two ±60° cases.
    detail.set_facecolor("#FCFDFD")
    transverse_indices = [i for i, angle in enumerate(angles) if abs(angle) == 60]
    tx = np.arange(len(transverse_indices))
    for values, offset, label, fill, edge in series:
        selected = [values[i] for i in transverse_indices]
        bars = detail.bar(tx + offset, selected, width, color=fill, edgecolor=edge, linewidth=1.0, zorder=2)
        for bar, value in zip(bars, selected):
            detail.text(
                bar.get_x() + bar.get_width() / 2,
                value + (0.0035 if value >= 0 else -0.0045),
                f"{value:+.3f}%",
                ha="center",
                va="bottom" if value >= 0 else "top",
                fontsize=7.6,
                color=edge,
            )
    detail.axhline(0, color=SLATE, linewidth=0.85)
    detail.set_xticks(tx, [f"{angles[i]:+d}°" for i in transverse_indices])
    detail.set_xlabel("Near-transverse loading direction")
    detail.set_ylabel("Conductive-gauge strain (%)")
    detail.set_ylim(-0.027, 0.064)
    detail.grid(axis="y", color="#DCE3E7", linewidth=0.7)
    detail.spines["top"].set_visible(False)
    detail.spines["right"].set_visible(False)
    detail.spines["left"].set_color(SLATE)
    detail.spines["bottom"].set_color(SLATE)
    detail.text(-0.10, 1.03, "b", transform=detail.transAxes, va="bottom", weight="bold", fontsize=11)
    detail.text(
        0.5,
        1.02,
        "Gauge-definition sign disagreement",
        transform=detail.transAxes,
        ha="center",
        va="bottom",
        fontsize=8.2,
        color=CORAL,
        weight="semibold",
        bbox={"boxstyle": "round,pad=0.25", "facecolor": CORAL_FILL, "edgecolor": "none", "alpha": 0.40},
    )
    for suffix, kwargs in (("png", {"dpi": 450}), ("jpg", {"dpi": 450, "pil_kwargs": {"quality": 95}})):
        output = ROOT / "figures" / f"fullfield_orientation.{suffix}"
        fig.savefig(output, bbox_inches="tight", facecolor="white", **kwargs)
        print(f"Wrote {output}")
    plt.close(fig)

    rows = list(csv.DictReader((ROOT / "results" / "textile_anisotropy.csv").open()))
    cases = ["textile_fiber_balanced", "textile_fiber_x3", "textile_fiber_y3"]
    labels = ["Balanced", "x-fiber 3:1", "y-fiber 3:1"]
    fills = [GREY_FILL, BLUE_FILL, CORAL_FILL]
    edges = [SLATE, BLUE, CORAL]
    angle_values = [0.0, 60.0]

    def value(case: str, angle: float, field: str) -> float:
        return float(next(
            row[field] for row in rows
            if row["material_case"] == case
            and float(row["loading_angle_deg"]) == angle
        ))

    # Use separate absolute-response axes because the 60-degree response is more
    # than an order of magnitude below the aligned response.  A shared scale would
    # make the diagonal-loading sensitivity visually disappear.
    fig = plt.figure(figsize=(8.2, 5.0), constrained_layout=True)
    grid = fig.add_gridspec(2, 2, height_ratios=[1.0, 1.12])
    absolute_axes = [fig.add_subplot(grid[0, 0]), fig.add_subplot(grid[0, 1])]
    positions = np.arange(len(cases))
    for ax, angle in zip(absolute_axes, angle_values):
        transfer = [100 * value(case, angle, "strain_transfer_vs_major_strain") for case in cases]
        bars = ax.bar(
            positions,
            transfer,
            width=0.64,
            color=fills,
            edgecolor=edges,
            linewidth=1.1,
            zorder=2,
        )
        for bar, result, edge in zip(bars, transfer, edges):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                result + max(transfer) * 0.035,
                f"{result:.3f}%" if angle else f"{result:.2f}%",
                ha="center",
                va="bottom",
                fontsize=8.2,
                color=edge,
                weight="semibold",
            )
        ax.set_xticks(positions, labels)
        ax.tick_params(axis="x", labelrotation=0)
        ax.set_ylim(0, max(transfer) * 1.23)
        ax.set_title(
            "Aligned loading (0°)" if angle == 0 else "Diagonal loading (60°)",
            fontsize=10,
            weight="semibold",
            color=SLATE,
            pad=7,
        )
        ax.set_facecolor("#FCFDFD")
        ax.grid(axis="y", color="#DCE3E7", linewidth=0.7, zorder=0)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["left"].set_color(SLATE)
        ax.spines["bottom"].set_color(SLATE)
    absolute_axes[0].set_ylabel("Strain transfer (%)")
    absolute_axes[0].text(-0.13, 1.05, "a", transform=absolute_axes[0].transAxes,
                          weight="bold", fontsize=11)
    absolute_axes[1].text(
        0.98,
        0.92,
        "Separate ordinate\nfor visibility",
        transform=absolute_axes[1].transAxes,
        ha="right",
        va="top",
        fontsize=7.5,
        color=SLATE,
    )

    # Diverging summary makes the directional effect relative to the balanced
    # textile explicit while retaining the exact simulated values above.
    change_ax = fig.add_subplot(grid[1, :])
    change_ax.set_facecolor("#FCFDFD")
    y0 = np.array([1.0, 0.0])
    offsets = [-0.13, 0.13]
    for case, label, edge, offset in zip(cases[1:], labels[1:], edges[1:], offsets):
        changes = [value(case, angle, "change_vs_balanced_percent") for angle in angle_values]
        change_ax.plot(changes, y0 + offset, color=edge, linewidth=1.2, alpha=0.65, zorder=2)
        change_ax.scatter(
            changes,
            y0 + offset,
            s=72,
            facecolor=BLUE_FILL if case == cases[1] else CORAL_FILL,
            edgecolor=edge,
            linewidth=1.3,
            label=label,
            zorder=3,
        )
        for x_value, y_value in zip(changes, y0 + offset):
            change_ax.text(
                x_value + (3.0 if x_value >= 0 else -3.0),
                y_value,
                f"{x_value:+.0f}%",
                ha="left" if x_value >= 0 else "right",
                va="center",
                fontsize=8.4,
                color=edge,
                weight="semibold",
            )
    change_ax.axvline(0, color=SLATE, linewidth=0.9, zorder=1)
    change_ax.set_xlim(-84, 84)
    change_ax.set_ylim(-0.42, 1.42)
    change_ax.set_yticks(y0, ["0° aligned", "60° diagonal"])
    change_ax.set_xlabel("Change in strain transfer relative to balanced textile (%)")
    change_ax.grid(axis="x", color="#DCE3E7", linewidth=0.7, zorder=0)
    change_ax.spines["top"].set_visible(False)
    change_ax.spines["right"].set_visible(False)
    change_ax.spines["left"].set_visible(False)
    change_ax.spines["bottom"].set_color(SLATE)
    change_ax.legend(frameon=False, ncol=2, loc="upper center", fontsize=8.2)
    change_ax.text(-0.06, 1.04, "b", transform=change_ax.transAxes,
                   weight="bold", fontsize=11)
    change_ax.text(
        0.99,
        0.03,
        "Illustrative stiffness ratios; materials uncalibrated",
        transform=change_ax.transAxes,
        ha="right",
        va="bottom",
        fontsize=7.7,
        color=SLATE,
        style="italic",
    )

    for suffix, kwargs in (("png", {"dpi": 450}), ("jpg", {"dpi": 450, "pil_kwargs": {"quality": 95}})):
        output = ROOT / "figures" / f"textile_anisotropy.{suffix}"
        fig.savefig(output, bbox_inches="tight", facecolor="white", **kwargs)
        print(f"Wrote {output}")
    plt.close(fig)

    print("Wrote full-field orientation and textile-anisotropy figures")


if __name__ == "__main__":
    main()
