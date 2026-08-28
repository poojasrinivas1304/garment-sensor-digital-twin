#!/usr/bin/env python3
"""Plot the three-level regularized-taper mesh audit."""

from __future__ import annotations

import json
import os
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/private/tmp/matplotlib-contact-sensor")
os.environ.setdefault("MPLBACKEND", "Agg")

import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[1]

BLUE_FILL = "#A9C9E2"
BLUE = "#3F7198"
LAVENDER_FILL = "#C7B7DC"
LAVENDER = "#756A9B"
CORAL_FILL = "#F3C2B8"
CORAL = "#C46B4E"
SLATE = "#5C6670"


def main() -> None:
    data = json.loads(
        (ROOT / "results" / "taper_mesh_convergence_10mm_tip25pct.json").read_text()
    )
    rows = data["rows"]
    elements = [row["element_count"] for row in rows]
    endpoint = [100.0 * row["endpoint_strain"] for row in rows]
    path = [100.0 * row["path_strain"] for row in rows]
    metrics = data["metrics"]

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
    fig, (ax, audit) = plt.subplots(
        1,
        2,
        figsize=(8.2, 3.8),
        gridspec_kw={"width_ratios": [1.55, 1.0]},
        constrained_layout=True,
    )

    # Panel a: the two gauge definitions approach the fine mesh monotonically,
    # but the remaining changes are not small enough for an independence claim.
    ax.set_facecolor("#FCFDFD")
    ax.plot(elements, endpoint, "o-", color=BLUE, markerfacecolor=BLUE_FILL, markeredgecolor=BLUE,
            markeredgewidth=1.2, linewidth=2.15, markersize=7, label="Endpoint centroid")
    ax.plot(elements, path, "s--", color=LAVENDER, markerfacecolor=LAVENDER_FILL, markeredgecolor=LAVENDER,
            markeredgewidth=1.2, linewidth=2.0, markersize=6.5, label="Centroid path")
    for i, (x, y_end, y_path) in enumerate(zip(elements, endpoint, path)):
        end_offset = 9 if y_end >= y_path else -16
        path_offset = -15 if y_end >= y_path else 9
        ax.annotate(f"{y_end:.3f}%", (x, y_end), xytext=(0, end_offset), ha="center", textcoords="offset points",
                    fontsize=8.1, color=BLUE)
        ax.annotate(f"{y_path:.3f}%", (x, y_path), xytext=(0, path_offset), ha="center", textcoords="offset points",
                    fontsize=8.1, color=LAVENDER)
        ax.axvline(x, color="#E8ECEF", lw=0.7, zorder=0)
    ax.set_xscale("log")
    ax.set_xticks(elements, ["1,488\ncoarse", "7,632\nmedium", "40,704\nfine"])
    ax.set_xlabel("Hexahedral elements (log scale)")
    ax.set_ylabel("Conductive-gauge strain (%)")
    ax.set_ylim(0.94, 1.17)
    ax.grid(axis="y", color="#DCE3E7", linewidth=0.7)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(SLATE)
    ax.spines["bottom"].set_color(SLATE)
    ax.legend(frameon=False, loc="upper right", fontsize=8.5)
    ax.text(-0.055, 1.02, "a", transform=ax.transAxes, va="bottom", weight="bold", fontsize=11)
    ax.text(0.02, 0.04, "Monotonic refinement", transform=ax.transAxes, color=SLATE, fontsize=8.3,
            bbox={"boxstyle": "round,pad=0.25", "facecolor": "#EDF0F2", "edgecolor": "none"})

    # Panel b: separate numerical-change metrics from the strain trajectories.
    audit.set_facecolor("#FCFDFD")
    categories = ["Medium → fine\nchange", "Fine-grid GCI\n(indicative)"]
    endpoint_metrics = [
        rows[1]["endpoint_difference_vs_fine_percent"],
        metrics["endpoint_fine_grid_GCI_percent_indicative"],
    ]
    path_metrics = [
        rows[1]["path_difference_vs_fine_percent"],
        metrics["path_fine_grid_GCI_percent_indicative"],
    ]
    ypos = np.arange(len(categories))
    height = 0.28
    audit.barh(ypos + height / 2, endpoint_metrics, height, color=BLUE_FILL, edgecolor=BLUE, linewidth=1.0,
               label="Endpoint centroid")
    audit.barh(ypos - height / 2, path_metrics, height, color=LAVENDER_FILL, edgecolor=LAVENDER, linewidth=1.0,
               label="Centroid path")
    for values, offset, color in ((endpoint_metrics, height / 2, BLUE), (path_metrics, -height / 2, LAVENDER)):
        for yi, value in zip(ypos, values):
            audit.text(value + 0.45, yi + offset, f"{value:.2f}%", va="center", color=color, fontsize=8.2,
                       fontweight="semibold")
    audit.set_yticks(ypos, categories)
    audit.set_ylim(-0.55, 1.95)
    audit.set_xlim(0, 22.5)
    audit.set_xlabel("Difference or uncertainty (%)")
    audit.grid(axis="x", color="#DCE3E7", linewidth=0.7)
    audit.spines["top"].set_visible(False)
    audit.spines["right"].set_visible(False)
    audit.spines["left"].set_visible(False)
    audit.spines["bottom"].set_color(SLATE)
    audit.tick_params(axis="y", length=0)
    audit.text(-0.08, 1.02, "b", transform=audit.transAxes, va="bottom", weight="bold", fontsize=11)
    audit.text(
        0.5,
        1.73,
        "Observed order (indicative)",
        transform=audit.transData,
        color=SLATE,
        fontsize=8.2,
        weight="semibold",
    )
    audit.text(0.5, 1.53, f"endpoint  p = {metrics['endpoint_observed_order_indicative']:.2f}",
               transform=audit.transData, color=BLUE, fontsize=8.2)
    audit.text(11.2, 1.53, f"path  p = {metrics['path_observed_order_indicative']:.2f}",
               transform=audit.transData, color=LAVENDER, fontsize=8.2)
    audit.text(
        0.50,
        -0.20,
        "Monotonic does not establish mesh independence",
        transform=audit.transAxes,
        ha="center",
        color=SLATE,
        fontsize=8.3,
        weight="semibold",
    )

    for suffix, kwargs in (("png", {"dpi": 450}), ("jpg", {"dpi": 450, "pil_kwargs": {"quality": 95}})):
        output = ROOT / "figures" / f"taper_mesh_convergence.{suffix}"
        fig.savefig(output, bbox_inches="tight", facecolor="white", **kwargs)
        print(f"Wrote {output}")
    plt.close(fig)


if __name__ == "__main__":
    main()
