#!/usr/bin/env python3
"""Plot contact-aware bilateral-arm-raise amplitude continuation."""

from __future__ import annotations

import csv
import json
import os
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/private/tmp/matplotlib-garment-movement")
os.environ.setdefault("MPLBACKEND", "Agg")

import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
CASES = (
    (0.0, "garment_fit_torso_expand_060mm_manual"),
    (0.25, "garment_both_arms_raise_025_extended"),
    (0.50, "garment_both_arms_raise_050"),
    (1.00, "garment_both_arms_raise_100"),
)


def read_summary(case: str) -> dict:
    path = ROOT / "results" / f"{case}_movement_summary.json"
    return json.loads(path.read_text())


def main() -> None:
    summaries = [(amplitude, read_summary(case)) for amplitude, case in CASES]
    baseline = {
        row["sensor"]: row["projected_sensor_axis_green_strain"]
        for row in summaries[0][1]["sensor_strains"]
    }
    rows = []
    matrix = []
    for amplitude, summary in summaries:
        delta_values = []
        for sensor in summary["sensor_strains"]:
            delta = sensor["projected_sensor_axis_green_strain"] - baseline[sensor["sensor"]]
            delta_values.append(100.0 * delta)
            rows.append(
                {
                    "amplitude_fraction": amplitude,
                    "case": summary["case"],
                    "sensor": sensor["sensor"],
                    "panel": sensor["panel"],
                    "total_projected_green_strain_percent": 100.0 * sensor["projected_sensor_axis_green_strain"],
                    "movement_induced_green_strain_percent": 100.0 * delta,
                    "active_contact_fraction": summary["contact"]["active_facet_fraction"],
                    "active_gap_95th_percentile_mm": summary["contact"]["absolute_active_gap_mm_95th_percentile"],
                    "active_gap_maximum_mm": summary["contact"]["maximum_absolute_active_gap_mm"],
                }
            )
        matrix.append(delta_values)

    results = ROOT / "results"
    with (results / "garment_both_arms_raise_continuation.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    amplitudes = np.asarray([item[0] for item in summaries])
    matrix_array = np.asarray(matrix)
    coverage = np.asarray([item[1]["contact"]["active_facet_fraction"] for item in summaries])
    gap95 = np.asarray([
        item[1]["contact"]["absolute_active_gap_mm_95th_percentile"] for item in summaries
    ])
    gapmax = np.asarray([
        item[1]["contact"]["maximum_absolute_active_gap_mm"] for item in summaries
    ])
    min_area = np.asarray([
        item[1]["mesh_quality"]["minimum_signed_triangle_area_ratio"] for item in summaries
    ])
    pair_errors = {}
    for pair in ((1, 2), (3, 8), (9, 10)):
        pair_errors[f"S{pair[0]}_S{pair[1]}"] = [
            float(abs(values[pair[0] - 1] - values[pair[1] - 1]))
            for values in matrix_array
        ]
    with (results / "garment_kinematic_screen.csv").open() as handle:
        contact_free_rows = [
            row for row in csv.DictReader(handle) if row["posture"] == "both_arms_raise"
        ]
    contact_free_rows.sort(key=lambda row: int(row["sensor"]))
    contact_free_percent = np.asarray(
        [100.0 * float(row["projected_sensor_axis_strain"]) for row in contact_free_rows]
    )
    contact_aware_percent = matrix_array[-1]
    sign_reversals = [
        index + 1 for index, (free, aware) in enumerate(zip(contact_free_percent, contact_aware_percent))
        if free * aware < 0.0
    ]
    comparison_r = float(np.corrcoef(contact_free_percent, contact_aware_percent)[0, 1])
    output = {
        "status": "contact-aware upper-boundary perturbation amplitude continuation inspired by bilateral arm raising; illustrative, not calibrated human motion",
        "cases": [item[1]["case"] for item in summaries],
        "amplitude_fractions": amplitudes.tolist(),
        "contact_coverage_fractions": coverage.tolist(),
        "active_gap_95th_percentile_mm": gap95.tolist(),
        "active_gap_maximum_mm": gapmax.tolist(),
        "minimum_signed_triangle_area_ratio": min_area.tolist(),
        "movement_induced_sensor_strain_percent": matrix_array.tolist(),
        "mirrored_pair_absolute_error_percentage_points": pair_errors,
        "maximum_mirrored_pair_error_percentage_points": float(
            max(max(values) for values in pair_errors.values())
        ),
        "contact_free_full_amplitude_sensor_strain_percent": contact_free_percent.tolist(),
        "contact_aware_full_amplitude_movement_induced_strain_percent": contact_aware_percent.tolist(),
        "sign_reversal_sensors": sign_reversals,
        "contact_free_vs_contact_aware_pearson_r": comparison_r,
    }
    (results / "garment_both_arms_raise_continuation.json").write_text(
        json.dumps(output, indent=2) + "\n"
    )

    fig, axes = plt.subplots(2, 2, figsize=(12.5, 8.0), constrained_layout=True)
    limit = float(np.abs(matrix_array).max())
    image = axes[0, 0].imshow(
        matrix_array,
        aspect="auto",
        cmap="RdBu_r",
        vmin=-limit,
        vmax=limit,
    )
    axes[0, 0].set_xticks(np.arange(10), [f"S{i}" for i in range(1, 11)])
    axes[0, 0].set_yticks(np.arange(len(amplitudes)), [f"{100*a:.0f}%" for a in amplitudes])
    axes[0, 0].set_xlabel("sensor")
    axes[0, 0].set_ylabel("movement amplitude")
    axes[0, 0].set_title("(a) Movement-induced sensor-axis strain (%)")
    for row_index in range(matrix_array.shape[0]):
        for column_index in range(matrix_array.shape[1]):
            value = matrix_array[row_index, column_index]
            axes[0, 0].text(
                column_index,
                row_index,
                f"{value:.2f}",
                ha="center",
                va="center",
                fontsize=6.5,
                color="white" if abs(value) > 0.55 * limit else "black",
            )
    fig.colorbar(image, ax=axes[0, 0], shrink=0.85, label="percentage points")

    axes[0, 1].plot(100 * amplitudes, 100 * coverage, "o-", color="#0072B2", lw=2)
    axes[0, 1].set_xlabel("movement amplitude (%)")
    axes[0, 1].set_ylabel("active contact facets (%)")
    axes[0, 1].set_ylim(0, 105)
    axes[0, 1].set_title("(b) Contact redistribution")
    axes[0, 1].grid(alpha=0.25)

    sensor_ids = np.arange(1, 11)
    width = 0.38
    axes[1, 0].bar(
        sensor_ids - width / 2,
        contact_free_percent,
        width,
        label="contact-free kinematic field",
        color="#E69F00",
        edgecolor="black",
        linewidth=0.5,
        hatch="//",
    )
    axes[1, 0].bar(
        sensor_ids + width / 2,
        contact_aware_percent,
        width,
        label="contact-aware garment FE",
        color="#0072B2",
        edgecolor="black",
        linewidth=0.5,
        hatch="..",
    )
    axes[1, 0].axhline(0, color="black", lw=0.8)
    axes[1, 0].set_xticks(sensor_ids)
    axes[1, 0].set_xlabel("sensor")
    axes[1, 0].set_ylabel("projected sensor-axis strain (%)")
    axes[1, 0].set_title(f"(c) Contact changes seven signal signs ($r={comparison_r:.2f}$)")
    axes[1, 0].legend(frameon=False, fontsize=8)
    axes[1, 0].grid(axis="y", alpha=0.25)

    axes[1, 1].plot(100 * amplitudes, gap95, "o-", label="95th percentile")
    axes[1, 1].plot(100 * amplitudes, gapmax, "s--", label="maximum")
    axes[1, 1].axhline(0.01, color="#D55E00", ls=":", label="0.01 mm reference")
    axes[1, 1].set_xlabel("movement amplitude (%)")
    axes[1, 1].set_ylabel("absolute active-facet gap (mm)")
    axes[1, 1].set_title("(d) Contact-gap audit")
    axes[1, 1].legend(frameon=False)
    axes[1, 1].grid(alpha=0.25)

    fig.suptitle("Contact-aware upper-boundary perturbation continuation")
    figure_path = ROOT / "figures" / "garment_both_arms_raise_continuation.png"
    fig.savefig(figure_path, dpi=300)
    plt.close(fig)
    print(json.dumps(output, indent=2))
    print(f"Wrote {figure_path}")


if __name__ == "__main__":
    main()
