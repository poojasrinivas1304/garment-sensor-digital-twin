#!/usr/bin/env python3
"""Plot the first-pass coupon geometry screening study."""

from __future__ import annotations

import csv
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D


ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "results" / "geometry_screening.csv"
FIGURE_DIR = ROOT / "figures"

LABELS = {
    "sensor_length_mm": "Sensor length (mm)",
    "sensor_width_mm": "Sensor width (mm)",
    "backing_thickness_mm": "Backing thickness (mm)",
    "conductive_thickness_mm": "Conductive thickness (mm)",
}

# Manuscript palette: muted fills with darker strokes for print accessibility.
COLORS = {
    "sensor_length_mm": ("#A9C9E2", "#3F7198"),
    "sensor_width_mm": ("#9FD3C7", "#347E73"),
    "backing_thickness_mm": ("#F2D69A", "#9A7125"),
    "conductive_thickness_mm": ("#E9AAA4", "#A45751"),
}
NOMINAL = {
    "sensor_length_mm": 80.0,
    "sensor_width_mm": 15.0,
    "backing_thickness_mm": 0.4,
    "conductive_thickness_mm": 0.6,
}


def main() -> None:
    rows = list(csv.DictReader(CSV_PATH.open()))
    FIGURE_DIR.mkdir(exist_ok=True)
    plt.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.size": 9.5,
            "axes.labelsize": 10,
            "axes.titlesize": 10.5,
            "xtick.labelsize": 9,
            "ytick.labelsize": 9,
            "axes.linewidth": 0.8,
        }
    )
    fig, axes = plt.subplots(
        2,
        2,
        figsize=(8.2, 6.25),
        sharey=True,
        constrained_layout=True,
    )
    nominal_transfer = None
    for panel, (parameter, label) in enumerate(LABELS.items()):
        ax = axes.flat[panel]
        subset = sorted(
            (
                float(row["parameter_value"]),
                100.0 * float(row["strain_transfer_ratio"]),
            )
            for row in rows
            if row["varied_parameter"] == parameter
        )
        x, y = zip(*subset)
        fill, stroke = COLORS[parameter]
        ax.set_facecolor("#FCFDFD")
        ax.plot(x, y, color=stroke, linewidth=2.25, zorder=2)
        ax.scatter(
            x,
            y,
            s=42,
            facecolor=fill,
            edgecolor=stroke,
            linewidth=1.2,
            zorder=3,
        )

        nominal_index = min(range(len(x)), key=lambda i: abs(x[i] - NOMINAL[parameter]))
        nominal_transfer = y[nominal_index]
        ax.scatter(
            [x[nominal_index]],
            [y[nominal_index]],
            s=78,
            marker="D",
            facecolor="#FFF7E8",
            edgecolor="#C46B4E",
            linewidth=1.6,
            zorder=4,
        )

        change = 100.0 * (y[-1] - y[0]) / y[0]
        ax.text(
            0.96,
            0.92,
            rf"$\Delta_{{\mathrm{{range}}}}={change:+.0f}\%$",
            transform=ax.transAxes,
            ha="right",
            va="top",
            color=stroke,
            fontweight="semibold",
            bbox={
                "boxstyle": "round,pad=0.25",
                "facecolor": fill,
                "edgecolor": "none",
                "alpha": 0.48,
            },
        )
        ax.set_xlabel(label)
        if panel % 2 == 0:
            ax.set_ylabel("Strain transfer (%)")
        ax.set_ylim(1.5, 7.15)
        ax.grid(axis="y", color="#DCE3E7", linewidth=0.7)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["left"].set_color("#5C6670")
        ax.spines["bottom"].set_color("#5C6670")
        ax.text(
            -0.04,
            1.02,
            chr(ord("a") + panel),
            transform=ax.transAxes,
            va="bottom",
            ha="left",
            fontweight="bold",
            fontsize=11,
        )

    # The same baseline case occurs once in every OFAT sweep.
    for ax in axes.flat:
        ax.axhline(
            nominal_transfer,
            color="#C46B4E",
            linewidth=0.9,
            linestyle=(0, (3, 3)),
            alpha=0.72,
            zorder=1,
        )

    fig.legend(
        handles=[
            Line2D(
                [0],
                [0],
                marker="D",
                linestyle="--",
                color="#C46B4E",
                markerfacecolor="#FFF7E8",
                markeredgecolor="#C46B4E",
                label=f"Nominal design ({nominal_transfer:.2f}% transfer)",
            )
        ],
        loc="lower center",
        bbox_to_anchor=(0.5, -0.045),
        frameon=False,
        fontsize=9,
    )

    for suffix, kwargs in (("png", {"dpi": 450}), ("jpg", {"dpi": 450, "pil_kwargs": {"quality": 95}})):
        output = FIGURE_DIR / f"geometry_screening.{suffix}"
        fig.savefig(output, bbox_inches="tight", facecolor="white", **kwargs)
        print(f"Wrote {output}")


if __name__ == "__main__":
    main()
