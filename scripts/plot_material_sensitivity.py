#!/usr/bin/env python3
"""Plot the completed isotropic material-property sensitivity screen."""

from __future__ import annotations

import csv
import os
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/private/tmp/matplotlib-contact-sensor")
os.environ.setdefault("MPLBACKEND", "Agg")

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.ticker import FixedLocator, FuncFormatter, NullFormatter


ROOT = Path(__file__).resolve().parents[1]

BLUE = "#3F7198"
BLUE_FILL = "#A9C9E2"
GOLD = "#9A7125"
GOLD_FILL = "#F2D69A"
CORAL = "#A45751"
CORAL_FILL = "#E9AAA4"
NOMINAL = "#C46B4E"
SLATE = "#5C6670"


def main() -> None:
    rows = list(csv.DictReader((ROOT / "results" / "material_sensitivity.csv").open()))
    lookup = {row["material_case"]: row for row in rows}
    nominal_value = 100.0 * float(lookup["literature_nominal"]["strain_transfer_ratio"])
    panels = [
        {
            "title": "Textile modulus",
            "cases": ["nylon_low", "literature_nominal", "nylon_high"],
            "x": [0.10, 0.24, 5.0],
            "color": BLUE,
            "fill": BLUE_FILL,
        },
        {
            "title": "Backing modulus",
            "cases": ["backing_low", "literature_nominal", "backing_high"],
            "x": [31.4, 48.4, 67.0],
            "color": GOLD,
            "fill": GOLD_FILL,
        },
        {
            "title": "Conductive modulus",
            "cases": ["conductive_low", "literature_nominal", "conductive_high"],
            "x": [12.0, 45.0, 90.0],
            "color": CORAL,
            "fill": CORAL_FILL,
        },
    ]

    plt.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.size": 9.5,
            "axes.labelsize": 10,
            "axes.titlesize": 10,
            "xtick.labelsize": 8.5,
            "ytick.labelsize": 9,
            "axes.linewidth": 0.8,
        }
    )
    fig, axes = plt.subplots(1, 3, figsize=(8.2, 3.65), sharey=True, constrained_layout=True)
    for panel_index, (ax, panel) in enumerate(zip(axes, panels)):
        x = np.asarray(panel["x"], dtype=float)
        values = np.asarray(
            [100.0 * float(lookup[case]["strain_transfer_ratio"]) for case in panel["cases"]]
        )
        ax.set_facecolor("#FCFDFD")
        ax.plot(x, values, color=panel["color"], linewidth=2.15, zorder=2)
        ax.scatter(x[[0, 2]], values[[0, 2]], s=58, facecolor=panel["fill"], edgecolor=panel["color"],
                   linewidth=1.3, zorder=3)
        ax.scatter([x[1]], [values[1]], s=82, marker="D", facecolor="#FFF7E8", edgecolor=NOMINAL,
                   linewidth=1.6, zorder=4)
        for point_index, (xi, yi) in enumerate(zip(x, values)):
            offset = (0, 9) if point_index != 1 else (0, -18)
            ax.annotate(f"{yi:.2f}%", (xi, yi), xytext=offset, textcoords="offset points", ha="center",
                        fontsize=8.1, color=panel["color"] if point_index != 1 else NOMINAL)

        span = values.max() / values.min()
        ax.text(
            0.05,
            0.94,
            f"screened span: {span:.1f}×",
            transform=ax.transAxes,
            ha="left",
            va="top",
            fontsize=7.9,
            color=panel["color"],
            weight="semibold",
            bbox={"boxstyle": "round,pad=0.25", "facecolor": panel["fill"], "edgecolor": "none", "alpha": 0.46},
        )
        ax.set_title(panel["title"], color=SLATE, weight="semibold", pad=8)
        ax.set_xlabel("Elastic modulus (MPa)")
        ax.set_xscale("log")
        ax.set_xticks(x, [f"{value:g}" for value in x])
        ax.xaxis.set_minor_formatter(NullFormatter())
        ax.set_yscale("log")
        ax.set_ylim(0.75, 55)
        ax.yaxis.set_major_locator(FixedLocator([1, 2, 5, 10, 20, 50]))
        ax.yaxis.set_major_formatter(FuncFormatter(lambda value, _: f"{value:g}"))
        ax.grid(axis="y", which="major", color="#DCE3E7", linewidth=0.7)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["left"].set_color(SLATE)
        ax.spines["bottom"].set_color(SLATE)
        ax.text(-0.10, 1.03, chr(ord("a") + panel_index), transform=ax.transAxes, va="bottom",
                weight="bold", fontsize=11)
    axes[0].set_ylabel("Endpoint strain transfer (%)\n(log scale)")
    fig.legend(
        handles=[
            plt.Line2D([0], [0], marker="D", linestyle="none", markerfacecolor="#FFF7E8",
                       markeredgecolor=NOMINAL, label=f"Common nominal case ({nominal_value:.2f}%)")
        ],
        loc="lower center",
        bbox_to_anchor=(0.5, -0.055),
        frameon=False,
        fontsize=8.5,
    )
    for suffix, kwargs in (("png", {"dpi": 450}), ("jpg", {"dpi": 450, "pil_kwargs": {"quality": 95}})):
        output = ROOT / "figures" / f"material_sensitivity.{suffix}"
        fig.savefig(output, bbox_inches="tight", facecolor="white", **kwargs)
        print(f"Wrote {output}")
    plt.close(fig)


if __name__ == "__main__":
    main()
