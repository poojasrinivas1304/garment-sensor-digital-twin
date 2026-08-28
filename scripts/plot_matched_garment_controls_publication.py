#!/usr/bin/env python3
"""Create a publication-style redesign of the matched garment controls."""

from __future__ import annotations

import json
import os
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/private/tmp/matplotlib-matched-controls")
os.environ.setdefault("MPLBACKEND", "Agg")

import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[1]

BLUE = "#3F7198"
BLUE_FILL = "#A9C9E2"
LAVENDER = "#756A9B"
LAVENDER_FILL = "#C7B7DC"
CORAL = "#A45751"
CORAL_FILL = "#E9AAA4"
SLATE = "#5C6670"
GREY = "#AEB6BC"
GREY_FILL = "#D9DEE2"
GRID = "#DCE3E7"


def main() -> None:
    data = json.loads((ROOT / "results" / "matched_garment_controls.json").read_text())
    records = {record["label"]: record for record in data["records"]}
    current_no = records["full garment without contact, current mesh"]
    current_yes = records["full garment with contact, current mesh"]
    sensors = np.arange(1, 11)

    def strain(record):
        return np.asarray([100.0 * row["relative_F_sensor_axis_green"] for row in record["rows"]])

    reduced = np.asarray([
        100.0 * row["reduced_analytical_sensor_axis_green"] for row in current_no["rows"]
    ])

    levels = ["coarse mesh", "current mesh", "fine mesh"]
    elements = np.asarray([
        records[f"full garment without contact, {level}"]["mesh"]["shirt_shell_elements"]
        for level in levels
    ])

    plt.rcParams.update({
        "font.family": "sans-serif",
        "font.size": 8.5,
        "axes.labelsize": 9.0,
        "xtick.labelsize": 7.8,
        "ytick.labelsize": 7.8,
        "axes.linewidth": 0.75,
    })

    fig = plt.figure(figsize=(9.2, 3.55), constrained_layout=True)
    outer = fig.add_gridspec(1, 3, width_ratios=[1.18, 1.0, 0.88])
    ax_a = fig.add_subplot(outer[0, 0])
    ax_b = fig.add_subplot(outer[0, 1])
    right = outer[0, 2].subgridspec(2, 1, hspace=0.10)
    ax_c1 = fig.add_subplot(right[0, 0])
    ax_c2 = fig.add_subplot(right[1, 0], sharex=ax_c1)

    # a: matched current-mesh comparison.
    width = 0.23
    for sensor in (3, 8):
        ax_a.axvspan(sensor - 0.48, sensor + 0.48, color=CORAL_FILL, alpha=0.16, lw=0)
    ax_a.bar(sensors - width, reduced, width, label="Reduced analytical",
             color=GREY_FILL, edgecolor=GREY, linewidth=0.45)
    ax_a.bar(sensors, strain(current_no), width, label="Full garment: no contact",
             color=BLUE_FILL, edgecolor=BLUE, linewidth=0.55)
    ax_a.bar(sensors + width, strain(current_yes), width, label="Full garment: contact",
             color=CORAL_FILL, edgecolor=CORAL, linewidth=0.55)
    ax_a.axhline(0, color=SLATE, lw=0.85)
    ax_a.set_xticks(sensors, [f"S{i}" for i in sensors])
    ax_a.set_ylabel("Relative sensor-axis Green strain (%)")
    ax_a.set_title("a   Matched 25% garment response", loc="left", color=SLATE,
                   weight="semibold", fontsize=9.2)
    ax_a.text(3, 1.20, "sign reversal", ha="center", va="bottom",
              color=CORAL, fontsize=6.9, weight="semibold")
    ax_a.text(8, 1.20, "sign reversal", ha="center", va="bottom",
              color=CORAL, fontsize=6.9, weight="semibold")
    ax_a.legend(frameon=False, fontsize=6.7, loc="upper center", ncol=3,
                bbox_to_anchor=(0.5, -0.14), borderaxespad=0)
    ax_a.set_ylim(-0.66, 1.34)

    # b: shell-mesh audit; colour encodes contact state and line style encodes sensor.
    series = []
    for contact, color, state in ((False, BLUE, "No contact"), (True, CORAL, "Contact")):
        for sensor, marker, linestyle in ((3, "o", "-"), (9, "s", (0, (4, 2)))):
            values = []
            for level in levels:
                rec = records[f"full garment {'with' if contact else 'without'} contact, {level}"]
                row = next(item for item in rec["rows"] if item["sensor"] == sensor)
                values.append(100.0 * row["relative_F_sensor_axis_green"])
            line, = ax_b.plot(elements, values, marker=marker, ms=4.2, lw=1.35,
                              linestyle=linestyle, color=color,
                              label=f"S{sensor} · {state}")
            series.append(line)
    ax_b.axhline(0, color=SLATE, lw=0.85)
    ax_b.set_xticks(elements, ["coarse", "current", "fine"])
    ax_b.set_ylabel("Relative sensor-axis Green strain (%)")
    ax_b.set_title("b   Sign stability across shell meshes", loc="left", color=SLATE,
                   weight="semibold", fontsize=9.2)
    ax_b.legend(handles=series, frameon=False, fontsize=6.5, ncol=2,
                loc="center", bbox_to_anchor=(0.54, 0.57))

    # c: stacked axes avoid the previous dual-axis ambiguity.
    contact_records = [records[f"full garment with contact, {level}"] for level in levels]
    coverage = np.asarray([100.0 * rec["movement_contact_coverage"] for rec in contact_records])
    gaps3 = np.asarray([
        next(row for row in rec["rows"] if row["sensor"] == 3)["movement_local_gap_mm"]
        for rec in contact_records
    ])
    ax_c1.plot(elements, coverage, "o-", color=LAVENDER, lw=1.5, ms=4.2)
    ax_c1.fill_between(elements, coverage.min() - 0.15, coverage,
                       color=LAVENDER_FILL, alpha=0.45)
    ax_c1.set_ylabel("Active facets (%)", color=LAVENDER)
    ax_c1.tick_params(axis="y", colors=LAVENDER)
    ax_c1.tick_params(axis="x", labelbottom=False)
    ax_c1.set_title("c   Contact discretization", loc="left", color=SLATE,
                    weight="semibold", fontsize=9.2)
    for x, y in zip(elements, coverage):
        ax_c1.text(x, y + 0.05, f"{y:.1f}", ha="center", va="bottom",
                   fontsize=6.6, color=LAVENDER)

    ax_c2.plot(elements, gaps3, "s-", color=CORAL, lw=1.5, ms=4.2)
    ax_c2.fill_between(elements, gaps3.min() - 0.00004, gaps3,
                       color=CORAL_FILL, alpha=0.45)
    ax_c2.set_ylabel("S3 signed gap (mm)", color=CORAL)
    ax_c2.tick_params(axis="y", colors=CORAL)
    ax_c2.set_xticks(elements, ["coarse", "current", "fine"])
    ax_c2.set_xlabel("Garment shell mesh")
    for x, y in zip(elements, gaps3):
        ax_c2.text(x, y + 0.000012, f"{y:.4f}", ha="center", va="bottom",
                   fontsize=6.4, color=CORAL)

    for ax in (ax_a, ax_b, ax_c1, ax_c2):
        ax.grid(axis="y", color=GRID, lw=0.5, zorder=0)
        for spine in ax.spines.values():
            spine.set_color(SLATE)
            spine.set_linewidth(0.72)

    for suffix, kwargs in (("png", {"dpi": 450}), ("jpg", {"dpi": 450, "pil_kwargs": {"quality": 95}})):
        output = ROOT / "figures" / f"matched_garment_controls_publication.{suffix}"
        fig.savefig(output, bbox_inches="tight", facecolor="white", **kwargs)
        print(f"Wrote {output}")
    plt.close(fig)


if __name__ == "__main__":
    main()
