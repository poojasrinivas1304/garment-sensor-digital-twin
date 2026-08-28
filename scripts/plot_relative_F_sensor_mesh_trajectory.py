#!/usr/bin/env python3
"""Alternative Figure 13: mesh trajectories on a shared strain axis."""

from __future__ import annotations

import json
import os
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/private/tmp/matplotlib-relative-f-trajectory")
os.environ.setdefault("MPLBACKEND", "Agg")

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D


ROOT = Path(__file__).resolve().parents[1]
BLUE = "#3F7198"
CORAL = "#A45751"
SLATE = "#5C6670"
GRID = "#DCE3E7"
PAPER = "#FCFDFD"


def main() -> None:
    rows = json.loads((ROOT / "results" / "relative_F_sensor_mesh.json").read_text())["rows"]
    meshes = ("local_coarse", "local_medium", "local_fine")
    marker_by_mesh = {"local_coarse": "o", "local_medium": "s", "local_fine": "D"}
    row_specs = (
        ("full_garment_no_contact", 3, "S3 · no contact", BLUE),
        ("full_garment_contact", 3, "S3 · contact", CORAL),
        ("full_garment_no_contact", 9, "S9 · no contact", BLUE),
        ("full_garment_contact", 9, "S9 · contact", CORAL),
    )
    y_positions = np.array([3.2, 2.2, 0.8, -0.2])

    plt.rcParams.update({
        "font.family": "sans-serif",
        "font.size": 8.6,
        "axes.labelsize": 9.1,
        "xtick.labelsize": 8.0,
        "ytick.labelsize": 8.0,
        "axes.linewidth": 0.75,
    })
    fig, axes = plt.subplots(1, 2, figsize=(9.0, 3.45), constrained_layout=True,
                             sharex=True, sharey=True)
    measures = (
        ("endpoint_gauge_percent", "a   Endpoint-centroid measure"),
        ("path_gauge_percent", "b   Centroid-path measure"),
    )

    for ax, (field, title) in zip(axes, measures):
        ax.axvspan(-0.021, 0, color=BLUE, alpha=0.035, lw=0)
        ax.axvspan(0, 0.007, color=CORAL, alpha=0.035, lw=0)
        ax.axvline(0, color=SLATE, lw=0.9)
        ax.axhline(1.5, color=GRID, lw=0.75)
        for y, (model, sensor, label, color) in zip(y_positions, row_specs):
            selected = {
                row["mesh"]: row for row in rows
                if row["garment_model"] == model and row["sensor"] == sensor
            }
            values = np.asarray([selected[mesh][field] for mesh in meshes])
            ax.plot(values, np.full(3, y), color=color, lw=1.45, zorder=2)
            # Direction of refinement, coarse to fine.
            ax.annotate(
                "", xy=(values[-1], y), xytext=(values[0], y),
                arrowprops={"arrowstyle": "->", "color": color, "lw": 1.45,
                            "shrinkA": 5, "shrinkB": 5}, zorder=2,
            )
            for value, mesh in zip(values, meshes):
                ax.scatter(
                    value, y, s=36, marker=marker_by_mesh[mesh],
                    facecolor=PAPER if mesh == "local_coarse" else color,
                    edgecolor=color, linewidth=1.0, zorder=3,
                )
        ax.set_yticks(y_positions, [spec[2] for spec in row_specs])
        ax.set_xlim(-0.021, 0.007)
        ax.set_ylim(-0.75, 3.75)
        ax.set_xlabel("Conductive-gauge strain (%)")
        ax.set_title(title, loc="left", fontsize=9.3, color=SLATE, weight="semibold")
        ax.grid(axis="x", color=GRID, lw=0.55, zorder=0)
        ax.text(
            0.5, 0.97, "same sign on all three tested meshes",
            transform=ax.transAxes, ha="center", va="top", fontsize=7.0,
            color=SLATE,
        )
        for spine in ax.spines.values():
            spine.set_color(SLATE)
            spine.set_linewidth(0.72)

    mesh_handles = [
        Line2D([0], [0], marker="o", color="none", markerfacecolor=PAPER,
               markeredgecolor=SLATE, markersize=5.2, label="coarse · 1,328"),
        Line2D([0], [0], marker="s", color="none", markerfacecolor=SLATE,
               markeredgecolor=SLATE, markersize=5.2, label="current · 7,632"),
        Line2D([0], [0], marker="D", color="none", markerfacecolor=SLATE,
               markeredgecolor=SLATE, markersize=5.2, label="fine · 40,704"),
    ]
    axes[1].legend(handles=mesh_handles, frameon=False, ncol=3,
                   loc="lower center", bbox_to_anchor=(0.5, 0.015), fontsize=6.8)

    for suffix, kwargs in (("png", {"dpi": 450}), ("jpg", {"dpi": 450, "pil_kwargs": {"quality": 95}})):
        output = ROOT / "figures" / f"relative_F_sensor_mesh_trajectory.{suffix}"
        fig.savefig(output, bbox_inches="tight", facecolor="white", **kwargs)
        print(f"Wrote {output}")
    plt.close(fig)


if __name__ == "__main__":
    main()
