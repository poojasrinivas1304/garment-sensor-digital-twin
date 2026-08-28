#!/usr/bin/env python3
"""Plot the vertical relative-strain field causing the S3/S8 reversal."""

from __future__ import annotations

import json
import math
import os
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/private/tmp/matplotlib-garment-reversal")
os.environ.setdefault("MPLBACKEND", "Agg")

import matplotlib.pyplot as plt
import numpy as np

from postprocess_garment_contact import initial_shirt_coordinates, read_last_record
from postprocess_garment_movement import local_surface_kinematics, sensor_theta


ROOT = Path(__file__).resolve().parents[1]
LAYOUT = json.loads((ROOT / "references" / "garment_layout_normalized.json").read_text())
PAIRS = {
    "Full garment, no contact": (
        "matched_no_contact_0p6_reference",
        "matched_no_contact_0p6_movement025",
    ),
    "Full garment, contact": (
        "garment_fit_torso_expand_060mm_manual",
        "garment_both_arms_raise_025",
    ),
}


def metadata(case: str) -> dict:
    return json.loads((ROOT / "model" / f"{case}_metadata.json").read_text())


def final_coordinates(case: str, n_nodes: int) -> np.ndarray:
    path = ROOT / "results" / f"{case}.log"
    return read_last_record(
        path.read_text(errors="replace").splitlines(),
        "shirt_final_coordinates",
        n_nodes,
        path,
    )


def relative_vertical_field(reference_case: str, movement_case: str):
    meta = metadata(movement_case)
    n_theta = int(meta["mesh"]["circumferential_divisions"])
    n_z = int(meta["mesh"]["vertical_divisions"])
    length = float(meta["shirt"]["modelled_body_panel_length_mm"])
    radii = meta["shirt"]["ellipse_radii_mm"]
    initial = initial_shirt_coordinates(
        float(radii[0]), float(radii[1]), n_theta, n_z, length
    )
    n_nodes = n_theta * (n_z + 1)
    fitted = final_coordinates(reference_case, n_nodes)
    moved = final_coordinates(movement_case, n_nodes)
    values = np.zeros((n_z, n_theta))
    for k in range(n_z):
        y = (k + 0.5) / n_z
        for j in range(n_theta):
            theta = 2.0 * math.pi * (j + 0.5) / n_theta
            f_fit = local_surface_kinematics(
                initial, fitted, theta, y, n_theta, n_z
            )[-1]
            f_move = local_surface_kinematics(
                initial, moved, theta, y, n_theta, n_z
            )[-1]
            f_rel = f_move @ np.linalg.inv(f_fit)
            e_rel = 0.5 * (f_rel.T @ f_rel - np.eye(3))
            values[k, j] = 100.0 * float(e_rel[1, 1])
    return values, length


def main() -> None:
    fields = []
    length = 0.0
    for title, pair in PAIRS.items():
        field, length = relative_vertical_field(*pair)
        fields.append((title, field))
    difference = fields[1][1] - fields[0][1]
    vmax = max(float(np.max(np.abs(field))) for _, field in fields)
    vmax = max(vmax, 0.8)
    fig, axes = plt.subplots(1, 3, figsize=(13.6, 4.2), constrained_layout=True)
    extent = (0.0, 360.0, 0.0, length)
    images = []
    for ax, (title, field) in zip(axes[:2], fields):
        images.append(
            ax.imshow(
                field,
                origin="lower",
                aspect="auto",
                extent=extent,
                cmap="RdBu_r",
                vmin=-vmax,
                vmax=vmax,
                interpolation="nearest",
            )
        )
        ax.set_title(title)
    dmax = max(float(np.max(np.abs(difference))), 0.3)
    im_diff = axes[2].imshow(
        difference,
        origin="lower",
        aspect="auto",
        extent=extent,
        cmap="RdBu_r",
        vmin=-dmax,
        vmax=dmax,
        interpolation="nearest",
    )
    axes[2].set_title("Contact increment")
    for ax in axes:
        ax.set_xlabel("Circumferential angle (degrees)")
        ax.set_xlim(0.0, 360.0)
        ax.set_xticks((0, 90, 180, 270, 360))
    axes[0].set_ylabel("Height from hem (mm)")
    for sensor in LAYOUT["sensors"]:
        if int(sensor["sensor"]) not in (3, 8):
            continue
        theta = math.degrees(
            sensor_theta(sensor["panel"], float(sensor["x"]))
        ) % 360.0
        y = float(sensor["y"]) * length
        for ax in axes:
            ax.plot(theta, y, marker="o", ms=6, mfc="white", mec="black", mew=0.9)
            ax.text(theta + 4.0, y + 9.0, f"S{sensor['sensor']}", fontsize=8)
    cb1 = fig.colorbar(images[0], ax=axes[:2], shrink=0.90, pad=0.02)
    cb1.set_label("Movement-induced vertical Green strain (%)")
    cb2 = fig.colorbar(im_diff, ax=axes[2], shrink=0.90, pad=0.02)
    cb2.set_label("Contact minus no-contact (percentage points)")
    for label, ax in zip("abc", axes):
        ax.text(-0.12, 1.04, label, transform=ax.transAxes, fontsize=14, fontweight="bold")
    output = ROOT / "figures" / "full_garment_reversal_field.png"
    fig.savefig(output, dpi=300, bbox_inches="tight")
    compile_output = ROOT / "overleaf" / "compile_figures" / "full_garment_reversal_field.jpg"
    fig.savefig(compile_output, dpi=220, bbox_inches="tight")
    print(f"Wrote {output}")
    print(f"Wrote {compile_output}")


if __name__ == "__main__":
    main()
