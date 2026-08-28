#!/usr/bin/env python3
"""Create a publication-style resolved-sensor mesh audit."""

from __future__ import annotations

import json
import os
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/private/tmp/matplotlib-relative-f-mesh-publication")
os.environ.setdefault("MPLBACKEND", "Agg")

import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[1]

BLUE = "#3F7198"
BLUE_FILL = "#A9C9E2"
CORAL = "#A45751"
CORAL_FILL = "#E9AAA4"
SLATE = "#5C6670"
GRID = "#DCE3E7"


def main() -> None:
    data = json.loads((ROOT / "results" / "relative_F_sensor_mesh.json").read_text())
    rows = data["rows"]
    meshes = ("local_coarse", "local_medium", "local_fine")
    x = np.arange(3)

    # Colour encodes garment state; marker and line style encode sensor.
    styles = {
        ("full_garment_no_contact", 3): (BLUE, "o", "-", "S3 · no contact"),
        ("full_garment_contact", 3): (CORAL, "o", "-", "S3 · contact"),
        ("full_garment_no_contact", 9): (BLUE, "s", (0, (4, 2)), "S9 · no contact"),
        ("full_garment_contact", 9): (CORAL, "s", (0, (4, 2)), "S9 · contact"),
    }

    plt.rcParams.update({
        "font.family": "sans-serif",
        "font.size": 8.6,
        "axes.labelsize": 9.1,
        "xtick.labelsize": 8.0,
        "ytick.labelsize": 8.0,
        "axes.linewidth": 0.75,
    })
    fig, axes = plt.subplots(1, 2, figsize=(9.0, 3.55), constrained_layout=True,
                             sharex=True, sharey=True)

    handles = []
    for (model, sensor), (color, marker, linestyle, label) in styles.items():
        selected = {
            row["mesh"]: row for row in rows
            if row["garment_model"] == model and row["sensor"] == sensor
        }
        endpoint = [selected[mesh]["endpoint_gauge_percent"] for mesh in meshes]
        path = [selected[mesh]["path_gauge_percent"] for mesh in meshes]
        for ax, values in zip(axes, (endpoint, path)):
            line, = ax.plot(
                x, values, color=color, marker=marker, linestyle=linestyle,
                lw=1.55, ms=5.0, markerfacecolor=color,
                markeredgecolor="white", markeredgewidth=0.55, label=label,
            )
        handles.append(line)

    titles = (
        "a   Endpoint-centroid measure",
        "b   Centroid-path measure",
    )
    tick_labels = ("coarse\n1,328", "current\n7,632", "fine\n40,704")
    for ax, title in zip(axes, titles):
        ax.axhline(0.0, color=SLATE, lw=0.9)
        ax.set_xticks(x, tick_labels)
        ax.set_xlabel("Resolved sensor mesh (elements)")
        ax.set_title(title, loc="left", fontsize=9.3, color=SLATE, weight="semibold")
        ax.grid(axis="y", color=GRID, lw=0.55, zorder=0)
        ax.text(
            0.04, 0.96, "same sign on all three tested meshes",
            transform=ax.transAxes, ha="left", va="top", fontsize=7.0,
            color=SLATE,
        )
        for spine in ax.spines.values():
            spine.set_color(SLATE)
            spine.set_linewidth(0.72)
    axes[0].set_ylabel("Conductive-gauge strain (%)")
    axes[0].set_ylim(-0.0212, 0.0072)

    axes[1].legend(handles=handles, labels=[h.get_label() for h in handles],
                   frameon=False, ncol=2, loc="lower center",
                   bbox_to_anchor=(0.5, 0.035), fontsize=7.1)

    for suffix, kwargs in (("png", {"dpi": 450}), ("jpg", {"dpi": 450, "pil_kwargs": {"quality": 95}})):
        output = ROOT / "figures" / f"relative_F_sensor_mesh_publication.{suffix}"
        fig.savefig(output, bbox_inches="tight", facecolor="white", **kwargs)
        print(f"Wrote {output}")
    plt.close(fig)


if __name__ == "__main__":
    main()
