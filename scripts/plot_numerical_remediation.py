#!/usr/bin/env python3
"""Plot spatial transfer, controlled mesh and contact-continuation audits."""

from __future__ import annotations

import json
import os
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/private/tmp/matplotlib-remediation")
os.environ.setdefault("MPLBACKEND", "Agg")

import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
BLUE = "#3F7198"
BLUE_FILL = "#A9C9E2"
TEAL = "#347E73"
TEAL_FILL = "#9FD3C7"
CORAL = "#A45751"
CORAL_FILL = "#E9AAA4"
LAVENDER = "#756A9B"
LAVENDER_FILL = "#C7B7DC"
SLATE = "#5C6670"
GRID = "#DCE3E7"


def main() -> None:
    spatial = json.loads((ROOT / "results" / "spatial_boundary_transfer.json").read_text())
    mesh = json.loads((ROOT / "results" / "quality_mesh_convergence.json").read_text())
    contact = json.loads((ROOT / "results" / "augmented_contact_continuation.json").read_text())

    plt.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.size": 8.4,
            "axes.labelsize": 8.8,
            "xtick.labelsize": 7.7,
            "ytick.labelsize": 7.7,
            "axes.linewidth": 0.72,
        }
    )
    fig, axes = plt.subplots(1, 3, figsize=(10.2, 3.55), constrained_layout=True)

    # a: paired endpoint magnitudes emphasize that sign survived while S9
    # no-contact magnitude did not.
    ax = axes[0]
    labels = ["No contact\nS3", "No contact\nS9", "Contact\nS3", "Contact\nS9"]
    y = np.arange(4)
    rows = spatial["rows"]
    homogeneous = np.asarray([row["homogeneous_endpoint_percent"] for row in rows])
    mapped = np.asarray([row["spatial_endpoint_percent"] for row in rows])
    for i, (left, right) in enumerate(zip(homogeneous, mapped)):
        ax.plot([left, right], [i, i], color=GRID, lw=2.2, zorder=1)
    ax.scatter(homogeneous, y, s=37, color=BLUE_FILL, edgecolor=BLUE, linewidth=1.0,
               label="Homogeneous $F_{rel}$", zorder=3)
    ax.scatter(mapped, y, s=39, marker="D", color=TEAL_FILL, edgecolor=TEAL, linewidth=1.0,
               label="Spatial map", zorder=3)
    ax.axvline(0, color=SLATE, lw=0.8)
    ax.set_yticks(y, labels)
    ax.invert_yaxis()
    ax.set_xlabel("Endpoint-centroid strain (%)")
    ax.set_title("a   Spatial boundary transfer", loc="left", color=SLATE, weight="semibold")
    ax.grid(axis="x", color=GRID, lw=0.55)
    ax.legend(frameon=False, fontsize=7.0, loc="lower right")

    # b: controlled in-plane taper refinement.
    ax = axes[1]
    mesh_rows = mesh["rows"]
    spacing = np.asarray([row["target_taper_in_plane_spacing_mm"] for row in mesh_rows])
    endpoint = 100.0 * np.asarray([row["endpoint_strain"] for row in mesh_rows])
    path = 100.0 * np.asarray([row["path_strain"] for row in mesh_rows])
    ax.plot(spacing, endpoint, "o-", color=BLUE, markerfacecolor=BLUE_FILL,
            markeredgecolor=BLUE, lw=1.8, ms=5.6, label="Endpoint centroid")
    ax.plot(spacing, path, "s--", color=LAVENDER, markerfacecolor=LAVENDER_FILL,
            markeredgecolor=LAVENDER, lw=1.7, ms=5.3, label="Centroid path")
    for x, value in zip(spacing, endpoint):
        ax.annotate(f"{value:.3f}", (x, value), xytext=(0, -12),
                    textcoords="offset points", ha="center", fontsize=6.9, color=BLUE)
    ax.set_xlim(1.08, 0.42)
    ax.set_xlabel("Target taper spacing (mm; finer →)")
    ax.set_ylabel("Conductive-gauge strain (%)")
    ax.set_title("b   Regularized in-plane mesh", loc="left", color=SLATE, weight="semibold")
    ax.grid(axis="y", color=GRID, lw=0.55)
    ax.legend(frameon=False, fontsize=7.0, loc="lower left")
    ax.text(0.98, 0.98, "GCI: 14.1% / 4.19%\nnot converged", transform=ax.transAxes,
            ha="right", va="top", fontsize=7.0, color=SLATE)

    # c: only normally terminated matched pairs become bars; failed trials are
    # shown as a labelled boundary, never converted into a physical value.
    ax = axes[2]
    contact_rows = contact["rows"]
    variants = [
        name for name in ("augmented_mu0_frictionless", "penalty_mu0p1_archived")
        if any(row["variant"] == name for row in contact_rows)
    ]
    display = {
        "augmented_mu0_frictionless": "Augmented\n$\\mu=0$",
        "penalty_mu0p1_archived": "Penalty\n$\\mu=0.1$",
    }
    xpos = np.arange(len(variants))
    width = 0.34
    for offset, sensor, color, fill, label in (
        (-width / 2, 3, CORAL, CORAL_FILL, "S3"),
        (width / 2, 9, TEAL, TEAL_FILL, "S9"),
    ):
        values = [
            next(row["movement_induced_strain_percent"] for row in contact_rows
                 if row["variant"] == variant and row["sensor"] == sensor)
            for variant in variants
        ]
        ax.bar(xpos + offset, values, width, color=fill, edgecolor=color,
               linewidth=1.0, label=label)
    ax.axhline(0, color=SLATE, lw=0.8)
    ax.set_xticks(xpos, [display[name] for name in variants])
    ax.set_ylabel("Movement-induced strain (%)")
    ax.set_title("c   Contact continuation", loc="left", color=SLATE, weight="semibold")
    ax.grid(axis="y", color=GRID, lw=0.55)
    ax.legend(frameon=False, fontsize=7.0, ncol=2, loc="lower right")
    if not any(row["variant"] == "augmented_mu0p1" for row in contact_rows):
        ax.text(0.50, 0.97, "Augmented $\\mu=0.1$:\nfit-stage stagnation", transform=ax.transAxes,
                ha="center", va="top", fontsize=7.0, color=CORAL)

    for ax in axes:
        ax.set_facecolor("#FCFDFD")
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["left"].set_color(SLATE)
        ax.spines["bottom"].set_color(SLATE)

    for suffix, kwargs in (
        ("png", {"dpi": 450}),
        ("jpg", {"dpi": 450, "pil_kwargs": {"quality": 95}}),
    ):
        path = ROOT / "figures" / f"numerical_remediation.{suffix}"
        fig.savefig(path, bbox_inches="tight", facecolor="white", **kwargs)
        print(f"Wrote {path}")
        if suffix == "jpg":
            compile_path = ROOT / "overleaf" / "compile_figures" / path.name
            fig.savefig(compile_path, bbox_inches="tight", facecolor="white", **kwargs)
            print(f"Wrote {compile_path}")
    plt.close(fig)


if __name__ == "__main__":
    main()
