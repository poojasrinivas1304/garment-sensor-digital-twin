#!/usr/bin/env python3
"""Create publication Figure 8: canonical ten-sensor garment layout."""

from __future__ import annotations

import json
import os
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/private/tmp/matplotlib-garment-layout")
os.environ.setdefault("MPLBACKEND", "Agg")

import matplotlib.pyplot as plt
import numpy as np
from matplotlib import transforms
from matplotlib.path import Path as MplPath
from matplotlib.patches import PathPatch, Rectangle


ROOT = Path(__file__).resolve().parents[1]
SHIRT_LENGTH_MM = 720.0
CHEST_WIDTH_MM = 540.0

BLUE = "#3F7198"
BLUE_FILL = "#A9C9E2"
LAVENDER = "#756A9B"
LAVENDER_FILL = "#C7B7DC"
CORAL = "#A45751"
CORAL_FILL = "#E9AAA4"
SLATE = "#5C6670"
GREY_FILL = "#D9DEE2"
SHIRT_FILL = "#F7F5F9"
GRID = "#DCE3E7"


def panel_path(panel: str) -> MplPath:
    """Smooth, symmetric flat-shirt silhouette in millimetres."""
    neck_y = 646.0 if panel == "front" else 682.0
    neck_outer_y = 670.0 if panel == "front" else 692.0
    neck_mid_y = 653.0 if panel == "front" else 684.0
    vertices = [
        (-250, 0),
        (250, 0),
        # Right torso: a gentle outward taper toward the armhole.
        (258, 155), (264, 350), (270, 500),
        # Sleeve lower edge and cuff.
        (317, 510), (344, 520), (354, 535),
        (366, 554), (376, 580), (382, 606),
        # Sleeve upper edge into the shoulder.
        (327, 628), (286, 644), (250, 658),
        (230, 682), (210, 700), (187, 710),
        (150, 716), (125, 721), (104, 725),
        # Right half of the neckline.
        (96, 702), (82, 683 if panel == "front" else 695), (62, neck_outer_y),
        (42, neck_mid_y), (20, neck_y), (0, neck_y),
        # Left half of the neckline.
        (-20, neck_y), (-42, neck_mid_y), (-62, neck_outer_y),
        (-82, 683 if panel == "front" else 695), (-96, 702), (-104, 725),
        # Left shoulder and sleeve.
        (-125, 721), (-150, 716), (-187, 710),
        (-210, 700), (-230, 682), (-250, 658),
        (-286, 644), (-327, 628), (-382, 606),
        (-376, 580), (-366, 554), (-354, 535),
        (-344, 520), (-317, 510), (-270, 500),
        # Left torso and closure.
        (-264, 350), (-258, 155), (-250, 0),
        (-250, 0),
    ]
    codes = [
        MplPath.MOVETO,
        MplPath.LINETO,
        MplPath.CURVE4, MplPath.CURVE4, MplPath.CURVE4,
        MplPath.CURVE4, MplPath.CURVE4, MplPath.CURVE4,
        MplPath.CURVE4, MplPath.CURVE4, MplPath.CURVE4,
        MplPath.CURVE4, MplPath.CURVE4, MplPath.CURVE4,
        MplPath.CURVE4, MplPath.CURVE4, MplPath.CURVE4,
        MplPath.CURVE4, MplPath.CURVE4, MplPath.CURVE4,
        MplPath.CURVE4, MplPath.CURVE4, MplPath.CURVE4,
        MplPath.CURVE4, MplPath.CURVE4, MplPath.CURVE4,
        MplPath.CURVE4, MplPath.CURVE4, MplPath.CURVE4,
        MplPath.CURVE4, MplPath.CURVE4, MplPath.CURVE4,
        MplPath.CURVE4, MplPath.CURVE4, MplPath.CURVE4,
        MplPath.CURVE4, MplPath.CURVE4, MplPath.CURVE4,
        MplPath.CURVE4, MplPath.CURVE4, MplPath.CURVE4,
        MplPath.CURVE4, MplPath.CURVE4, MplPath.CURVE4,
        MplPath.CURVE4, MplPath.CURVE4, MplPath.CURVE4,
        MplPath.CURVE4, MplPath.CURVE4, MplPath.CURVE4,
        MplPath.CLOSEPOLY,
    ]
    return MplPath(vertices, codes)


def add_sensor(ax, x: float, y: float, angle: float, label: str, offset: tuple[float, float]) -> None:
    """Draw a backing, conductive strip and two terminal pads about a centre."""
    rotation = transforms.Affine2D().rotate_deg_around(x, y, angle) + ax.transData
    ax.add_patch(Rectangle((x - 43, y - 9.5), 86, 19, transform=rotation,
                           facecolor=LAVENDER_FILL, edgecolor=LAVENDER, linewidth=0.75, zorder=3))
    ax.add_patch(Rectangle((x - 32, y - 5.5), 64, 11, transform=rotation,
                           facecolor=SLATE, edgecolor="none", zorder=4))
    for pad_x in (x - 39, x + 29):
        ax.add_patch(Rectangle((pad_x, y - 7.5), 10, 15, transform=rotation,
                               facecolor=CORAL_FILL, edgecolor=CORAL, linewidth=0.55, zorder=5))
    ax.annotate(label, xy=(x, y), xytext=(x + offset[0], y + offset[1]),
                ha="center", va="center", color=BLUE, weight="bold", fontsize=9.2,
                arrowprops={"arrowstyle": "-", "color": BLUE_FILL, "lw": 0.7}, zorder=6)


def main() -> None:
    layout = json.loads((ROOT / "references" / "garment_layout_normalized.json").read_text())
    label_offsets = {
        1: (-4, 34), 2: (4, 34), 3: (-38, 0), 4: (0, 32),
        5: (-26, 30), 6: (26, 30), 7: (-36, 0), 8: (-38, 0),
        9: (-8, 32), 10: (8, 32),
    }

    plt.rcParams.update({
        "font.family": "sans-serif",
        "font.size": 9.2,
        "axes.linewidth": 0.8,
    })
    fig, axes = plt.subplots(1, 2, figsize=(8.2, 5.35), constrained_layout=True)

    for panel_index, (ax, panel) in enumerate(zip(axes, ["front", "back"])):
        ax.add_patch(PathPatch(panel_path(panel), facecolor=SHIRT_FILL,
                              edgecolor=SLATE, linewidth=1.15, zorder=1))
        # Quiet seam cues help the silhouette read as a garment rather than a plate.
        ax.plot([-242, 242], [14, 14], color=GRID, lw=0.75, zorder=2)
        ax.plot([-350, -275], [532, 510], color=GRID, lw=0.75, zorder=2)
        ax.plot([275, 350], [510, 532], color=GRID, lw=0.75, zorder=2)
        ax.plot([0, 0], [10, 635], color=GRID, lw=0.8, linestyle=(0, (3, 3)), zorder=2)
        ax.text(-420, 742, chr(ord("a") + panel_index), weight="bold", fontsize=11, color=SLATE)
        ax.text(-382, 742, panel.capitalize(), weight="semibold", fontsize=11, color=SLATE)
        count = 0
        for sensor in layout["sensors"]:
            if sensor["panel"] != panel:
                continue
            count += 1
            x = sensor["x"] * CHEST_WIDTH_MM
            y = sensor["y"] * SHIRT_LENGTH_MM
            add_sensor(ax, x, y, sensor["angle_deg"], f"S{sensor['sensor']}",
                       label_offsets[sensor["sensor"]])

        ax.text(382, 742, f"{count} sensors", ha="right", va="center", fontsize=8.0, color=SLATE)
        ax.set_xlim(-445, 445)
        ax.set_ylim(-62, 770)
        ax.set_aspect("equal")
        ax.axis("off")

    # Photograph-derived dimensional estimates shown only on the front panel.
    front = axes[0]
    front.annotate("", xy=(-414, 0), xytext=(-414, SHIRT_LENGTH_MM),
                   arrowprops={"arrowstyle": "<->", "color": LAVENDER, "lw": 1.0})
    front.text(-432, SHIRT_LENGTH_MM / 2, r"$\approx 720 \pm 10$ mm",
               rotation=90, ha="center", va="center", color=LAVENDER, fontsize=8.2)
    front.annotate("", xy=(-CHEST_WIDTH_MM / 2, 465), xytext=(CHEST_WIDTH_MM / 2, 465),
                   arrowprops={"arrowstyle": "<->", "color": LAVENDER, "lw": 1.0})
    front.text(0, 448, r"$\approx 540 \pm 30$ mm", ha="center", va="top",
               color=LAVENDER, fontsize=8.2)

    fig.suptitle("Canonical ten-sensor simulation layout", fontsize=12.2,
                 weight="semibold", color=SLATE, y=1.02)
    fig.text(0.5, 0.985,
             "Positions and orientations digitized from the adopted design schematic; outline scaled from photographs",
             ha="center", va="top", fontsize=8.0, color=SLATE)

    # Shared component legend.
    legend_y = 0.018
    fig.text(0.36, legend_y, "Sensor assembly:", ha="right", va="center", fontsize=8.0, color=SLATE)
    components = [
        (0.38, LAVENDER_FILL, LAVENDER, "TPU backing"),
        (0.52, SLATE, SLATE, "conductive gauge"),
        (0.69, CORAL_FILL, CORAL, "terminal pad"),
    ]
    for x, fill, edge, label in components:
        patch = Rectangle((x, legend_y - 0.008), 0.022, 0.016, transform=fig.transFigure,
                          facecolor=fill, edgecolor=edge, linewidth=0.65, clip_on=False)
        fig.add_artist(patch)
        fig.text(x + 0.028, legend_y, label, ha="left", va="center", fontsize=7.7, color=SLATE)

    for suffix, kwargs in (("png", {"dpi": 450}), ("jpg", {"dpi": 450, "pil_kwargs": {"quality": 95}})):
        output = ROOT / "figures" / f"garment_layout_normalized.{suffix}"
        fig.savefig(output, bbox_inches="tight", facecolor="white", **kwargs)
        print(f"Wrote {output}")
    plt.close(fig)


if __name__ == "__main__":
    main()
