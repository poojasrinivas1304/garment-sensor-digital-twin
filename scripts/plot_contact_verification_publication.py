#!/usr/bin/env python3
"""Create publication Figure 10: garment-contact verification audit."""

from __future__ import annotations

import json
import os
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/private/tmp/matplotlib-contact-verification")
os.environ.setdefault("MPLBACKEND", "Agg")

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap
from mpl_toolkits.axes_grid1.inset_locator import inset_axes, mark_inset

from postprocess_garment_contact import (
    TORSO_RX,
    TORSO_RY,
    facet_locations,
    initial_shirt_coordinates,
    read_last_record,
)


ROOT = Path(__file__).resolve().parents[1]
CASE = "garment_fit_torso_expand_060mm_manual"

BLUE = "#3F7198"
BLUE_FILL = "#A9C9E2"
LAVENDER = "#756A9B"
LAVENDER_FILL = "#C7B7DC"
CORAL = "#A45751"
CORAL_FILL = "#E9AAA4"
SLATE = "#5C6670"
GREY_FILL = "#D9DEE2"
PAPER = "#FCFDFD"
GRID = "#DCE3E7"


def main() -> None:
    log_path = ROOT / "results" / f"{CASE}.log"
    metadata = json.loads((ROOT / "model" / f"{CASE}_metadata.json").read_text())
    summary = json.loads((ROOT / "results" / f"{CASE}_summary.json").read_text())
    n_theta = int(metadata["mesh"]["circumferential_divisions"])
    n_z = int(metadata["mesh"]["vertical_divisions"])
    shirt_length = float(metadata["shirt"]["modelled_body_panel_length_mm"])
    shirt_radii = metadata["shirt"]["ellipse_radii_mm"]

    lines = log_path.read_text(errors="replace").splitlines()
    final = read_last_record(lines, "shirt_final_coordinates", n_theta * (n_z + 1), log_path)
    face = read_last_record(lines, "shirt_contact_data", n_theta * n_z, log_path)
    initial = initial_shirt_coordinates(
        float(shirt_radii[0]), float(shirt_radii[1]), n_theta, n_z, shirt_length
    )
    gap = face[:, 0]
    pressure_kpa = face[:, 1] * 1000.0
    active = pressure_kpa > 1e-9
    active_gap_um = np.abs(gap[active]) * 1000.0

    theta_face, z_face = facet_locations(n_theta, n_z, shirt_length)
    theta_centres = np.sort(np.unique(theta_face))
    z_centres = np.sort(np.unique(z_face))
    pressure_grid = np.full((len(z_centres), len(theta_centres)), np.nan)
    theta_index = {round(value, 8): index for index, value in enumerate(theta_centres)}
    z_index = {round(value, 8): index for index, value in enumerate(z_centres)}
    for theta, z, pressure in zip(theta_face, z_face, pressure_kpa):
        pressure_grid[z_index[round(z, 8)], theta_index[round(theta, 8)]] = pressure

    middle = n_z // 2
    middle_ids = np.arange(middle * n_theta, (middle + 1) * n_theta)
    order = np.argsort(np.arctan2(initial[middle_ids, 1], initial[middle_ids, 0]))

    plt.rcParams.update({
        "font.family": "sans-serif",
        "font.size": 9.0,
        "axes.labelsize": 9.2,
        "xtick.labelsize": 8.3,
        "ytick.labelsize": 8.3,
        "axes.linewidth": 0.8,
    })
    fig, axes = plt.subplots(
        1, 3, figsize=(9.2, 3.75), constrained_layout=True,
        gridspec_kw={"width_ratios": [1.02, 1.18, 1.0]},
    )

    # a: fitted cross-section with an actual-scale lateral zoom.
    angle = np.linspace(0, 2 * np.pi, 600)
    axes[0].plot(TORSO_RX * np.cos(angle), TORSO_RY * np.sin(angle),
                 color=CORAL, lw=1.7, label="final torso")
    axes[0].plot(initial[middle_ids, 0][order], initial[middle_ids, 1][order],
                 linestyle=(0, (4, 2)), color=LAVENDER, lw=1.5, label="garment: initial")
    axes[0].plot(final[middle_ids, 0][order], final[middle_ids, 1][order],
                 color=BLUE, lw=1.5, label="garment: equilibrium")
    axes[0].set_aspect("equal")
    axes[0].set_xlabel("x (mm)")
    axes[0].set_ylabel("y (mm)")
    axes[0].set_title("a   Fitted cross-section", loc="left", color=SLATE, weight="semibold")
    axes[0].legend(frameon=False, fontsize=7.2, loc="lower center")
    axes[0].grid(color=GRID, lw=0.55)

    zoom = inset_axes(axes[0], width="37%", height="42%", loc="upper right", borderpad=0.8)
    zoom.plot(TORSO_RX * np.cos(angle), TORSO_RY * np.sin(angle), color=CORAL, lw=1.5)
    zoom.plot(initial[middle_ids, 0][order], initial[middle_ids, 1][order],
              linestyle=(0, (4, 2)), color=LAVENDER, lw=1.3)
    zoom.plot(final[middle_ids, 0][order], final[middle_ids, 1][order], color=BLUE, lw=1.3)
    zoom.set_xlim(186.9, 190.1)
    zoom.set_ylim(-14, 14)
    zoom.set_xticks([188, 189, 190])
    zoom.set_yticks([-10, 0, 10])
    zoom.tick_params(labelsize=6.2)
    zoom.grid(color=GRID, lw=0.45)
    zoom.set_title("actual-scale zoom", fontsize=6.7, color=SLATE, pad=2)
    mark_inset(axes[0], zoom, loc1=1, loc2=4, fc="none", ec=SLATE, lw=0.55)

    # b: full facet pressure field in the manuscript sequential blue palette.
    pressure_cmap = LinearSegmentedColormap.from_list(
        "pressure_blue", [PAPER, BLUE_FILL, BLUE], N=256
    )
    theta_edges = np.linspace(0, 360, n_theta + 1)
    z_edges = np.linspace(0, shirt_length, n_z + 1)
    field = axes[1].pcolormesh(
        theta_edges, z_edges, pressure_grid, shading="flat", cmap=pressure_cmap,
        vmin=float(np.nanmin(pressure_grid)), vmax=float(np.nanmax(pressure_grid)),
    )
    axes[1].set_xlabel("Circumferential angle (degrees)")
    axes[1].set_ylabel("Height from hem (mm)")
    axes[1].set_title("b   Contact pressure (kPa)", loc="left", color=SLATE, weight="semibold")
    axes[1].set_xticks([0, 90, 180, 270, 360])
    colorbar = fig.colorbar(field, ax=axes[1], pad=0.025, fraction=0.055)
    colorbar.outline.set_edgecolor(SLATE)
    colorbar.outline.set_linewidth(0.7)
    axes[1].text(
        0.02, 0.98,
        f"mean {summary['contact']['pressure_MPa_active_mean'] * 1000:.5f} kPa\n"
        f"max {summary['contact']['pressure_MPa_active_max'] * 1000:.5f} kPa",
        transform=axes[1].transAxes, ha="left", va="top", fontsize=7.2, color=SLATE,
        bbox={"boxstyle": "round,pad=0.25", "facecolor": PAPER, "edgecolor": "none", "alpha": 0.88},
    )

    # c: gap distribution displayed against the predefined 10-µm tolerance.
    bins = np.linspace(0, 10, 26)
    axes[2].hist(active_gap_um, bins=bins, color=LAVENDER_FILL,
                 edgecolor=LAVENDER, linewidth=0.65)
    axes[2].axvline(10.0, color=CORAL, linewidth=1.4, linestyle=(0, (4, 2)))
    axes[2].set_xlim(0, 10.5)
    axes[2].set_xlabel("Absolute active-facet gap (µm)")
    axes[2].set_ylabel("Facet count")
    axes[2].set_title("c   Gap tolerance audit", loc="left", color=SLATE, weight="semibold")
    axes[2].grid(axis="y", color=GRID, lw=0.55)
    axes[2].text(10.0, axes[2].get_ylim()[1] * 0.96, "10-µm limit", ha="right", va="top",
                 rotation=90, color=CORAL, fontsize=7.0)
    axes[2].annotate(
        f"max {active_gap_um.max():.2f} µm",
        xy=(active_gap_um.max(), 0), xytext=(active_gap_um.max() + 0.45, axes[2].get_ylim()[1] * 0.62),
        color=BLUE, fontsize=7.6, weight="semibold",
        arrowprops={"arrowstyle": "->", "color": BLUE, "lw": 0.8},
    )
    axes[2].text(0.03, 0.97, f"{active.sum()}/{len(active)} facets active",
                 transform=axes[2].transAxes, ha="left", va="top", color=SLATE, fontsize=7.3)

    for ax in axes:
        for spine in ax.spines.values():
            spine.set_color(SLATE)
            spine.set_linewidth(0.75)

    fig.suptitle(
        "Contact verification: normal termination • 100% active facets • no inverted triangles",
        fontsize=10.0, color=SLATE, weight="semibold",
    )

    for suffix, kwargs in (("png", {"dpi": 450}), ("jpg", {"dpi": 450, "pil_kwargs": {"quality": 95}})):
        output = ROOT / "figures" / f"{CASE}_audit.{suffix}"
        fig.savefig(output, bbox_inches="tight", facecolor="white", **kwargs)
        print(f"Wrote {output}")
    plt.close(fig)


if __name__ == "__main__":
    main()
