#!/usr/bin/env python3
"""Plot the local-medium taper-length screening result."""

from __future__ import annotations

import csv
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import Polygon, Rectangle


ROOT = Path(__file__).resolve().parents[1]

BLUE_FILL = "#A9C9E2"
BLUE = "#3F7198"
TEAL_FILL = "#9FD3C7"
TEAL = "#347E73"
CORAL_FILL = "#F3C2B8"
CORAL = "#C46B4E"
SLATE = "#5C6670"


def draw_taper_schematic(ax) -> None:
    """Draw an explanatory side view; dimensions are schematic, not to scale."""
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 7.2)
    ax.axis("off")

    # Textile substrate and abrupt printed stack.
    ax.add_patch(Rectangle((0.7, 5.0), 8.6, 0.28, facecolor="#E8ECEF", edgecolor=SLATE, lw=0.8))
    ax.add_patch(Rectangle((1.7, 5.28), 6.6, 0.85, facecolor=BLUE_FILL, edgecolor=BLUE, lw=1.2))
    ax.text(0.7, 6.65, "Abrupt reference", color=SLATE, weight="semibold", fontsize=9.5)
    ax.text(5.0, 5.70, "printed stack", ha="center", va="center", color=BLUE, fontsize=8.5)

    # Symmetric thickness taper with a 25% terminal thickness.
    ax.add_patch(Rectangle((0.7, 1.25), 8.6, 0.28, facecolor="#E8ECEF", edgecolor=SLATE, lw=0.8))
    tapered = Polygon(
        [(1.0, 1.53), (3.0, 1.53), (7.0, 1.53), (9.0, 1.53), (9.0, 1.74), (7.0, 2.38), (3.0, 2.38), (1.0, 1.74)],
        closed=True,
        facecolor=TEAL_FILL,
        edgecolor=TEAL,
        lw=1.2,
    )
    ax.add_patch(tapered)
    ax.text(0.7, 3.15, "Symmetric end taper", color=SLATE, weight="semibold", fontsize=9.5)
    ax.annotate("", xy=(1.0, 0.73), xytext=(3.0, 0.73), arrowprops={"arrowstyle": "<->", "color": TEAL, "lw": 1.1})
    ax.annotate("", xy=(7.0, 0.73), xytext=(9.0, 0.73), arrowprops={"arrowstyle": "<->", "color": TEAL, "lw": 1.1})
    ax.text(2.0, 0.38, r"$L_{\rm taper}$", ha="center", color=TEAL, fontsize=9)
    ax.text(8.0, 0.38, r"$L_{\rm taper}$", ha="center", color=TEAL, fontsize=9)
    ax.annotate(
        r"$t_{\rm tip}=0.25t_0$",
        xy=(9.0, 1.67),
        xytext=(7.25, 3.15),
        color=CORAL,
        fontsize=8.7,
        arrowprops={"arrowstyle": "->", "color": CORAL, "lw": 1.0},
    )
    ax.text(5.0, 0.02, "Side view · schematic, not to scale", ha="center", color="#7B858C", fontsize=7.8)


def main() -> None:
    rows = list(csv.DictReader((ROOT / "results" / "taper_screening.csv").open()))
    x = [float(row["taper_length_mm"]) for row in rows]
    y = [100.0 * float(row["strain_transfer_ratio"]) for row in rows]
    figure_dir = ROOT / "figures"
    figure_dir.mkdir(exist_ok=True)
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
    fig, (schematic, ax) = plt.subplots(
        1,
        2,
        figsize=(8.2, 3.65),
        gridspec_kw={"width_ratios": [1.0, 1.55]},
        constrained_layout=True,
    )
    draw_taper_schematic(schematic)
    ax.set_facecolor("#FCFDFD")
    ax.plot(x, y, color=BLUE, linewidth=2.25, zorder=2)
    ax.scatter(x, y, s=48, facecolor=BLUE_FILL, edgecolor=BLUE, linewidth=1.2, zorder=3)
    ax.scatter([x[0]], [y[0]], s=68, marker="s", facecolor="#EDF0F2", edgecolor=SLATE, linewidth=1.4, zorder=4)
    ax.scatter([x[2]], [y[2]], s=92, marker="D", facecolor="#FFF7E8", edgecolor=CORAL, linewidth=1.7, zorder=5)
    ax.scatter([x[3]], [y[3]], s=78, marker="o", facecolor=TEAL_FILL, edgecolor=TEAL, linewidth=1.6, zorder=5)

    for xi, yi in zip(x, y):
        ax.text(xi, yi + 0.065, f"{yi:.2f}%", ha="center", va="bottom", fontsize=8.3, color=SLATE)

    improvement_5 = 100.0 * (y[2] - y[0]) / y[0]
    improvement_10 = 100.0 * (y[3] - y[0]) / y[0]
    incremental = 100.0 * (y[3] - y[2]) / y[2]
    ax.annotate(
        f"Selected 5-mm geometry\n+{improvement_5:.1f}% vs abrupt",
        xy=(x[2], y[2]),
        xytext=(5.0, 2.70),
        ha="center",
        va="center",
        color=CORAL,
        fontsize=8.1,
        bbox={"boxstyle": "round,pad=0.28", "facecolor": CORAL_FILL, "edgecolor": "none", "alpha": 0.38},
        arrowprops={"arrowstyle": "->", "color": CORAL, "lw": 1.0, "shrinkB": 4},
    )
    ax.annotate(
        f"10-mm case (largest tested)\n+{improvement_10:.1f}% vs abrupt",
        xy=(x[3], y[3]),
        xytext=(9.15, 3.08),
        ha="right",
        va="center",
        color=TEAL,
        fontsize=8.1,
        bbox={"boxstyle": "round,pad=0.28", "facecolor": TEAL_FILL, "edgecolor": "none", "alpha": 0.38},
        arrowprops={"arrowstyle": "->", "color": TEAL, "lw": 1.0, "shrinkB": 4},
    )
    ax.text(
        0.96,
        0.08,
        f"5 → 10 mm: +{incremental:.1f}%",
        transform=ax.transAxes,
        ha="right",
        va="bottom",
        fontsize=8.3,
        color=BLUE,
        bbox={"boxstyle": "round,pad=0.25", "facecolor": BLUE_FILL, "edgecolor": "none", "alpha": 0.50},
    )
    ax.set_xlabel("End-taper length (mm)")
    ax.set_ylabel("Strain transfer (%)")
    ax.set_xticks(x)
    ax.set_ylim(2.30, 3.75)
    ax.axhline(y[0], color=SLATE, lw=0.9, ls=(0, (3, 3)), alpha=0.65, zorder=1)
    ax.grid(axis="y", color="#DCE3E7", linewidth=0.7)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(SLATE)
    ax.spines["bottom"].set_color(SLATE)
    schematic.text(-0.04, 1.02, "a", transform=schematic.transAxes, va="bottom", weight="bold", fontsize=11)
    ax.text(-0.04, 1.02, "b", transform=ax.transAxes, va="bottom", weight="bold", fontsize=11)

    for suffix, kwargs in (("png", {"dpi": 450}), ("jpg", {"dpi": 450, "pil_kwargs": {"quality": 95}})):
        output = figure_dir / f"taper_screening.{suffix}"
        fig.savefig(output, bbox_inches="tight", facecolor="white", **kwargs)
        print(f"Wrote {output}")


if __name__ == "__main__":
    main()
