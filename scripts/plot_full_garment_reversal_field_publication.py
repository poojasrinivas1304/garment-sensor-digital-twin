#!/usr/bin/env python3
"""Create a publication-style full-garment strain-field comparison."""

from __future__ import annotations

import math
import os

os.environ.setdefault("MPLCONFIGDIR", "/private/tmp/matplotlib-garment-reversal-publication")
os.environ.setdefault("MPLBACKEND", "Agg")

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap

from plot_full_garment_reversal_field import LAYOUT, PAIRS, ROOT, relative_vertical_field
from postprocess_garment_movement import sensor_theta


BLUE = "#3F7198"
BLUE_FILL = "#A9C9E2"
CORAL = "#A45751"
CORAL_FILL = "#E9AAA4"
SLATE = "#5C6670"
PAPER = "#FCFDFD"


def main() -> None:
    fields = []
    length = 0.0
    for title, pair in PAIRS.items():
        field, length = relative_vertical_field(*pair)
        fields.append((title, field))
    difference = fields[1][1] - fields[0][1]
    vmax = max(max(float(np.max(np.abs(field))) for _, field in fields), 0.8)
    dmax = max(float(np.max(np.abs(difference))), 0.3)

    strain_cmap = LinearSegmentedColormap.from_list(
        "manuscript_diverging",
        [BLUE, BLUE_FILL, PAPER, CORAL_FILL, CORAL],
        N=256,
    )
    plt.rcParams.update({
        "font.family": "sans-serif",
        "font.size": 8.5,
        "axes.labelsize": 9.0,
        "xtick.labelsize": 7.8,
        "ytick.labelsize": 7.8,
        "axes.linewidth": 0.75,
    })

    fig, axes = plt.subplots(1, 3, figsize=(9.25, 3.45), constrained_layout=True,
                             sharey=True)
    extent = (0.0, 360.0, 0.0, length)
    titles = (
        "a   Full garment · no contact",
        "b   Full garment · contact",
        "c   Contact increment",
    )
    images = []
    for ax, title, (_, field) in zip(axes[:2], titles[:2], fields):
        image = ax.imshow(
            field, origin="lower", aspect="auto", extent=extent,
            cmap=strain_cmap, vmin=-vmax, vmax=vmax, interpolation="nearest",
        )
        images.append(image)
        ax.contour(
            np.linspace(0, 360, field.shape[1]),
            np.linspace(0, length, field.shape[0]),
            field, levels=[0], colors=[SLATE], linewidths=0.42, alpha=0.58,
        )
        ax.set_title(title, loc="left", fontsize=9.2, color=SLATE, weight="semibold")

    im_diff = axes[2].imshow(
        difference, origin="lower", aspect="auto", extent=extent,
        cmap=strain_cmap, vmin=-dmax, vmax=dmax, interpolation="nearest",
    )
    axes[2].contour(
        np.linspace(0, 360, difference.shape[1]),
        np.linspace(0, length, difference.shape[0]),
        difference, levels=[0], colors=[SLATE], linewidths=0.42, alpha=0.58,
    )
    axes[2].set_title(titles[2], loc="left", fontsize=9.2, color=SLATE,
                      weight="semibold")

    for ax in axes:
        ax.set_xlabel("Circumferential angle (degrees)")
        ax.set_xlim(0.0, 360.0)
        ax.set_xticks((0, 90, 180, 270, 360))
        for spine in ax.spines.values():
            spine.set_color(SLATE)
            spine.set_linewidth(0.72)
    axes[0].set_ylabel("Height from hem (mm)")

    for sensor in LAYOUT["sensors"]:
        if int(sensor["sensor"]) not in (3, 8):
            continue
        theta = math.degrees(sensor_theta(sensor["panel"], float(sensor["x"]))) % 360.0
        y = float(sensor["y"]) * length
        for ax in axes:
            ax.scatter(theta, y, s=25, facecolor=PAPER, edgecolor=SLATE,
                       linewidth=0.75, zorder=4)
            ax.text(theta + 5.0, y + 10.0, f"S{sensor['sensor']}", fontsize=7.0,
                    color=SLATE, weight="semibold", zorder=5)

    shared_cb = fig.colorbar(images[0], ax=axes[:2], orientation="horizontal",
                             fraction=0.055, pad=0.13, aspect=34)
    shared_cb.set_label("Movement-induced vertical Green strain (%)", color=SLATE,
                        labelpad=3)
    shared_cb.outline.set_edgecolor(SLATE)
    shared_cb.outline.set_linewidth(0.65)
    diff_cb = fig.colorbar(im_diff, ax=axes[2], orientation="horizontal",
                           fraction=0.055, pad=0.13, aspect=17)
    diff_cb.set_label("Contact − no-contact (percentage points)", color=SLATE,
                      labelpad=3)
    diff_cb.outline.set_edgecolor(SLATE)
    diff_cb.outline.set_linewidth(0.65)

    for suffix, kwargs in (("png", {"dpi": 450}), ("jpg", {"dpi": 450, "pil_kwargs": {"quality": 95}})):
        output = ROOT / "figures" / f"full_garment_reversal_field_publication.{suffix}"
        fig.savefig(output, bbox_inches="tight", facecolor="white", **kwargs)
        print(f"Wrote {output}")
    plt.close(fig)


if __name__ == "__main__":
    main()
