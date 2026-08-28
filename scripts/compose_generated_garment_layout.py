#!/usr/bin/env python3
"""Overlay the canonical sensor layout on a clean generated T-shirt base."""

from __future__ import annotations

import json
import os
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/private/tmp/matplotlib-generated-layout")
os.environ.setdefault("MPLBACKEND", "Agg")

import matplotlib.image as mpimg
import matplotlib.pyplot as plt
from matplotlib import transforms
from matplotlib.patches import Rectangle


ROOT = Path(__file__).resolve().parents[1]

BLUE = "#3F7198"
BLUE_FILL = "#A9C9E2"
LAVENDER = "#756A9B"
LAVENDER_FILL = "#C7B7DC"
CORAL = "#A45751"
CORAL_FILL = "#E9AAA4"
SLATE = "#5C6670"


def add_sensor(ax, x: float, y: float, angle: float, label: str,
               offset: tuple[float, float], length: float) -> None:
    """Add a nominal 80-by-15 mm sensor assembly scaled to the shirt."""
    height = length * 15.0 / 80.0
    rotation = transforms.Affine2D().rotate_deg_around(x, y, -angle) + ax.transData
    ax.add_patch(Rectangle((x - length / 2, y - height / 2), length, height,
                           transform=rotation, facecolor=LAVENDER_FILL,
                           edgecolor=LAVENDER, linewidth=1.0, zorder=4))
    conductive_length = 0.76 * length
    conductive_height = 0.54 * height
    ax.add_patch(Rectangle((x - conductive_length / 2, y - conductive_height / 2),
                           conductive_length, conductive_height, transform=rotation,
                           facecolor=SLATE, edgecolor="none", zorder=5))
    pad_width = 0.12 * length
    pad_height = 0.78 * height
    for pad_x in (x - 0.43 * length, x + 0.31 * length):
        ax.add_patch(Rectangle((pad_x, y - pad_height / 2), pad_width, pad_height,
                               transform=rotation, facecolor=CORAL_FILL,
                               edgecolor=CORAL, linewidth=0.75, zorder=6))
    ax.annotate(label, xy=(x, y), xytext=(x + offset[0], y + offset[1]),
                ha="center", va="center", color=BLUE, fontsize=10.2, weight="bold",
                arrowprops={"arrowstyle": "-", "color": BLUE_FILL, "lw": 0.8}, zorder=7)


def main() -> None:
    base_path = ROOT / "figures" / "garment_layout_base_generated.png"
    layout = json.loads((ROOT / "references" / "garment_layout_normalized.json").read_text())
    image = mpimg.imread(base_path)
    height_px, width_px = image.shape[:2]

    # Image-space mappings derived from the generated front/back torso bounds.
    mappings = {
        "front": {"center_x": 424.5, "panel_width": 495.0, "shoulder_y": 45.0, "hem_y": 835.0},
        "back": {"center_x": 1354.0, "panel_width": 488.0, "shoulder_y": 45.0, "hem_y": 835.0},
    }
    offsets = {
        1: (-3, -31), 2: (3, -31), 3: (-35, 0), 4: (0, -30),
        5: (-24, -28), 6: (24, -28), 7: (-34, 0), 8: (-35, 0),
        9: (-7, -30), 10: (7, -30),
    }

    plt.rcParams.update({"font.family": "sans-serif", "font.size": 9.4})
    fig = plt.figure(figsize=(9.0, 5.25), facecolor="white")
    ax = fig.add_axes([0.015, 0.105, 0.97, 0.875])
    ax.imshow(image)
    ax.set_xlim(0, width_px)
    ax.set_ylim(height_px, 0)
    ax.axis("off")

    for sensor in layout["sensors"]:
        mapping = mappings[sensor["panel"]]
        x = mapping["center_x"] + sensor["x"] * mapping["panel_width"]
        usable_height = mapping["hem_y"] - mapping["shoulder_y"]
        y = mapping["hem_y"] - sensor["y"] * usable_height
        sensor_length_px = mapping["panel_width"] * 80.0 / 540.0
        add_sensor(ax, x, y, sensor["angle_deg"], f"S{sensor['sensor']}",
                   offsets[sensor["sensor"]], sensor_length_px)

    ax.text(72, 58, "a  Front", color=SLATE, fontsize=11.2, weight="bold")
    ax.text(1000, 58, "b  Back", color=SLATE, fontsize=11.2, weight="bold")
    ax.text(760, 58, "7 sensors", ha="right", color=SLATE, fontsize=8.5)
    ax.text(1710, 58, "3 sensors", ha="right", color=SLATE, fontsize=8.5)

    legend_y = 0.035
    fig.text(0.31, legend_y, "Sensor assembly:", ha="right", va="center",
             fontsize=8.2, color=SLATE)
    components = [
        (0.33, LAVENDER_FILL, LAVENDER, "TPU backing"),
        (0.49, SLATE, SLATE, "conductive gauge"),
        (0.67, CORAL_FILL, CORAL, "terminal pad"),
    ]
    for x, fill, edge, label in components:
        patch = Rectangle((x, legend_y - 0.008), 0.024, 0.016, transform=fig.transFigure,
                          facecolor=fill, edgecolor=edge, linewidth=0.7, clip_on=False)
        fig.add_artist(patch)
        fig.text(x + 0.030, legend_y, label, ha="left", va="center",
                 fontsize=8.0, color=SLATE)

    for suffix, kwargs in (("png", {"dpi": 450}), ("jpg", {"dpi": 450, "pil_kwargs": {"quality": 95}})):
        output = ROOT / "figures" / f"garment_layout_normalized.{suffix}"
        fig.savefig(output, bbox_inches="tight", facecolor="white", **kwargs)
        print(f"Wrote {output}")
    plt.close(fig)


if __name__ == "__main__":
    main()
