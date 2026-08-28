#!/usr/bin/env python3
"""Plot the matched reduced/no-contact/contact comparison and shell-mesh audit."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    data = json.loads((ROOT / "results" / "matched_garment_controls.json").read_text())
    records = {record["label"]: record for record in data["records"]}
    current_no = records["full garment without contact, current mesh"]
    current_yes = records["full garment with contact, current mesh"]
    sensors = np.arange(1, 11)

    def strain(record):
        return np.asarray([100.0 * row["relative_F_sensor_axis_green"] for row in record["rows"]])

    reduced = np.asarray(
        [100.0 * row["reduced_analytical_sensor_axis_green"] for row in current_no["rows"]]
    )

    fig, axes = plt.subplots(1, 3, figsize=(13.2, 4.25), constrained_layout=True)
    width = 0.25
    axes[0].bar(sensors - width, reduced, width, label="Reduced analytical", color="#c7c7c7")
    axes[0].bar(sensors, strain(current_no), width, label="Full garment, no contact", color="#3b82b4")
    axes[0].bar(sensors + width, strain(current_yes), width, label="Full garment, contact", color="#d95f43")
    axes[0].axhline(0, color="black", lw=0.8)
    axes[0].set_xticks(sensors)
    axes[0].set_xlabel("Sensor")
    axes[0].set_ylabel("Relative sensor-axis Green strain (%)")
    axes[0].set_title("a  Matched current-mesh comparison", loc="left", fontweight="bold")
    axes[0].legend(frameon=False, fontsize=8)

    levels = ["coarse mesh", "current mesh", "fine mesh"]
    elements = [
        records[f"full garment without contact, {level}"]["mesh"]["shirt_shell_elements"]
        for level in levels
    ]
    for contact, marker, color, label in [
        (False, "o", "#3b82b4", "No contact"),
        (True, "s", "#d95f43", "Contact"),
    ]:
        vals3, vals9 = [], []
        for level in levels:
            rec = records[f"full garment {'with' if contact else 'without'} contact, {level}"]
            rows = {row["sensor"]: row for row in rec["rows"]}
            vals3.append(100.0 * rows[3]["relative_F_sensor_axis_green"])
            vals9.append(100.0 * rows[9]["relative_F_sensor_axis_green"])
        axes[1].plot(elements, vals3, marker=marker, color=color, ls="-", label=f"S3, {label}")
        axes[1].plot(elements, vals9, marker=marker, color=color, ls="--", label=f"S9, {label}")
    axes[1].axhline(0, color="black", lw=0.8)
    axes[1].set_xlabel("Garment shell facets")
    axes[1].set_ylabel("Relative sensor-axis Green strain (%)")
    axes[1].set_title("b  Shell-mesh audit", loc="left", fontweight="bold")
    axes[1].legend(frameon=False, fontsize=8, ncol=2)

    contact_records = [records[f"full garment with contact, {level}"] for level in levels]
    coverage = [100.0 * rec["movement_contact_coverage"] for rec in contact_records]
    gaps3 = [next(row for row in rec["rows"] if row["sensor"] == 3)["movement_local_gap_mm"] for rec in contact_records]
    ax2 = axes[2]
    ax2.plot(elements, coverage, "o-", color="#6a51a3", label="Active coverage")
    ax2.set_xlabel("Garment shell facets")
    ax2.set_ylabel("Active contact facets (%)", color="#6a51a3")
    ax2.tick_params(axis="y", colors="#6a51a3")
    ax2b = ax2.twinx()
    ax2b.plot(elements, gaps3, "s--", color="#238b45", label="S3 local signed gap")
    ax2b.set_ylabel("S3 signed gap (mm)", color="#238b45")
    ax2b.tick_params(axis="y", colors="#238b45")
    ax2.set_title("c  Contact discretization outputs", loc="left", fontweight="bold")

    for ax in axes:
        ax.grid(axis="y", color="#dddddd", lw=0.6)
    output = ROOT / "figures" / "matched_garment_controls.png"
    fig.savefig(output, dpi=300, bbox_inches="tight")
    compile_output = ROOT / "overleaf" / "compile_figures" / "matched_garment_controls.jpg"
    fig.savefig(compile_output, dpi=240, bbox_inches="tight")
    print(output)
    print(compile_output)


if __name__ == "__main__":
    main()
