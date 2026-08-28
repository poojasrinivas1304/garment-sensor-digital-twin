#!/usr/bin/env python3
"""Create a compact publication redesign of the fitted-contact audit."""

from __future__ import annotations

import json
import os
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/private/tmp/matplotlib-contact-verification-v2")
os.environ.setdefault("MPLBACKEND", "Agg")

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap
from mpl_toolkits.axes_grid1.inset_locator import inset_axes

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

    def signed_radial_offset(points: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        x = points[middle_ids, 0]
        y = points[middle_ids, 1]
        theta = np.mod(np.arctan2(y / TORSO_RY, x / TORSO_RX), 2 * np.pi)
        torso_x = TORSO_RX * np.cos(theta)
        torso_y = TORSO_RY * np.sin(theta)
        offset_um = (np.hypot(x, y) - np.hypot(torso_x, torso_y)) * 1000.0
        order = np.argsort(theta)
        return np.degrees(theta[order]), offset_um[order]

    theta_initial, offset_initial = signed_radial_offset(initial)
    theta_final, offset_final = signed_radial_offset(final)
    theta_initial = np.r_[theta_initial, 360.0]
    offset_initial = np.r_[offset_initial, offset_initial[0]]
    theta_final = np.r_[theta_final, 360.0]
    offset_final = np.r_[offset_final, offset_final[0]]

    plt.rcParams.update({
        "font.family": "sans-serif",
        "font.size": 8.6,
        "axes.labelsize": 9.0,
        "xtick.labelsize": 7.8,
        "ytick.labelsize": 7.8,
        "axes.linewidth": 0.75,
    })
    fig, axes = plt.subplots(
        1, 3, figsize=(9.0, 3.15), constrained_layout=True,
        gridspec_kw={"width_ratios": [1.08, 1.0, 1.0]},
    )

    # a: fitting is communicated directly as the signed surface offset.
    axes[0].axhline(0, color=CORAL, lw=1.0, zorder=1)
    axes[0].fill_between(theta_initial, offset_initial, 0, color=LAVENDER_FILL, alpha=0.28)
    axes[0].plot(theta_initial, offset_initial, color=LAVENDER, lw=1.6,
                 linestyle=(0, (4, 2)), label="initial")
    axes[0].plot(theta_final, offset_final, color=BLUE, lw=1.8, label="equilibrium")
    axes[0].set_xlim(0, 360)
    axes[0].set_ylim(-112, 10)
    axes[0].set_xticks([0, 90, 180, 270, 360])
    axes[0].set_xlabel("Circumferential angle (degrees)")
    axes[0].set_ylabel("Signed garment–torso offset (µm)")
    axes[0].set_title("a   Contact establishment", loc="left", color=SLATE, weight="semibold")
    axes[0].text(354, 3.5, "torso surface", color=CORAL, fontsize=7.0,
                 ha="right", va="bottom")
    axes[0].annotate(
        "relaxed to near-zero gap",
        xy=(183, np.interp(183, theta_final, offset_final)), xytext=(338, -36),
        ha="right", color=BLUE, fontsize=7.1,
        arrowprops={"arrowstyle": "->", "color": BLUE, "lw": 0.8},
    )
    axes[0].legend(frameon=False, ncol=2, loc="lower center", fontsize=7.0,
                   bbox_to_anchor=(0.5, 0.01))

    # b: retain the manuscript's unwrapped facet-pressure map.
    pressure_cmap = LinearSegmentedColormap.from_list(
        "pressure_blue", [PAPER, BLUE_FILL, BLUE], N=256
    )
    theta_edges = np.linspace(0, 360, n_theta + 1)
    z_edges = np.linspace(0, shirt_length, n_z + 1)
    field = axes[1].pcolormesh(
        theta_edges, z_edges, pressure_grid, shading="flat", cmap=pressure_cmap,
        vmin=float(np.nanmin(pressure_grid)), vmax=float(np.nanmax(pressure_grid)),
    )
    axes[1].set_xlim(0, 360)
    axes[1].set_xticks([0, 90, 180, 270, 360])
    axes[1].set_xlabel("Circumferential angle (degrees)")
    axes[1].set_ylabel("Height from hem (mm)")
    axes[1].set_title("b   Contact pressure (kPa)", loc="left", color=SLATE,
                      weight="semibold")
    colorbar = fig.colorbar(field, ax=axes[1], pad=0.025, fraction=0.052)
    colorbar.outline.set_edgecolor(SLATE)
    colorbar.outline.set_linewidth(0.65)
    axes[1].text(
        0.03, 0.96,
        f"mean {summary['contact']['pressure_MPa_active_mean'] * 1000:.5f} kPa\n"
        f"max {summary['contact']['pressure_MPa_active_max'] * 1000:.5f} kPa",
        transform=axes[1].transAxes, ha="left", va="top", fontsize=7.1, color=SLATE,
    )
    axes[1].text(0.97, 0.04, f"{active.sum()}/{len(active)} facets active",
                 transform=axes[1].transAxes, ha="right", va="bottom",
                 fontsize=7.0, color=SLATE, weight="semibold")

    # c: preserve the distribution detail and show the tolerance on a compact inset scale.
    lo = np.floor(active_gap_um.min() * 10) / 10 - 0.1
    hi = np.ceil(active_gap_um.max() * 10) / 10 + 0.1
    bins = np.linspace(lo, hi, 18)
    axes[2].hist(active_gap_um, bins=bins, color=LAVENDER_FILL,
                 edgecolor=LAVENDER, linewidth=0.65)
    axes[2].set_xlim(lo, hi)
    axes[2].set_xlabel("Absolute active-facet gap (µm)")
    axes[2].set_ylabel("Facet count")
    axes[2].set_title("c   Gap distribution", loc="left", color=SLATE, weight="semibold")
    axes[2].text(
        0.97, 0.72, f"maximum {active_gap_um.max():.2f} µm",
        transform=axes[2].transAxes, ha="right", va="top",
        fontsize=7.1, color=BLUE, weight="semibold",
    )

    gauge = inset_axes(axes[2], width="58%", height="12%", loc="upper right", borderpad=1.55)
    gauge.set_xlim(0, 10.4)
    gauge.set_ylim(-1, 1)
    gauge.hlines(0, 0, 10, color=GRID, lw=4.2, zorder=1)
    gauge.hlines(0, 0, active_gap_um.max(), color=BLUE_FILL, lw=4.2, zorder=2)
    gauge.scatter([active_gap_um.max()], [0], s=23, color=BLUE, zorder=3,
                  edgecolor=PAPER, linewidth=0.55)
    gauge.vlines(10, -0.65, 0.65, color=CORAL, lw=1.5)
    gauge.text(10, 0.64, "limit 10 µm", ha="right", va="bottom",
               fontsize=6.2, color=CORAL)
    gauge.set_axis_off()

    for ax in axes:
        ax.grid(axis="y", color=GRID, lw=0.5, zorder=0)
        for spine in ax.spines.values():
            spine.set_color(SLATE)
            spine.set_linewidth(0.72)
    axes[1].grid(False)

    for suffix, kwargs in (("png", {"dpi": 450}), ("jpg", {"dpi": 450, "pil_kwargs": {"quality": 95}})):
        output = ROOT / "figures" / f"{CASE}_audit_v2.{suffix}"
        fig.savefig(output, bbox_inches="tight", facecolor="white", **kwargs)
        print(f"Wrote {output}")
    plt.close(fig)


if __name__ == "__main__":
    main()
