#!/usr/bin/env python3
"""Run an audited three-level local-mesh study for a regularized taper."""

from __future__ import annotations

import argparse
import csv
import json
import math
import subprocess
import time
from pathlib import Path

from generate_coupon import ROOT, generate
from postprocess_coupon import process


FEBIO = Path("/Applications/FEBioStudio/FEBioStudio.app/Contents/MacOS/febio4")
LEVELS = ("local_coarse", "local_medium", "local_fine")


def token(value: float) -> str:
    return f"{value:g}".replace(".", "p")


def case_name(level: str, taper_mm: float, tip_fraction: float) -> str:
    return (
        f"taper_mesh_{token(taper_mm)}mm_tip{token(100 * tip_fraction)}pct_"
        f"{level}"
    )


def normal_termination(name: str) -> bool:
    path = ROOT / "results" / f"{name}.log"
    return path.exists() and "N O R M A L   T E R M I N A T I O N" in path.read_text(
        errors="replace"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--taper-mm", type=float, default=10.0)
    parser.add_argument("--tip-fraction", type=float, default=0.25)
    args = parser.parse_args()
    rows = []
    for level in LEVELS:
        name = case_name(level, args.taper_mm, args.tip_fraction)
        if not normal_termination(name):
            generate(
                case_name=name,
                mesh_level=level,
                material_case="literature_nominal",
                taper_length_mm=args.taper_mm,
                tip_thickness_fraction=args.tip_fraction,
                time_steps=60,
                maximum_time_step=0.02,
            )
            started = time.perf_counter()
            completed = subprocess.run(
                [str(FEBIO), "-i", str(ROOT / "model" / f"{name}.feb")],
                cwd=ROOT,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.STDOUT,
                check=False,
            )
            elapsed = time.perf_counter() - started
            return_code = completed.returncode
        else:
            elapsed = 0.0
            return_code = 0
        log_path = ROOT / "results" / f"{name}.log"
        log_text = log_path.read_text(errors="replace") if log_path.exists() else ""
        row = {
            "case_name": name,
            "mesh_level": level,
            "taper_length_mm": args.taper_mm,
            "tip_thickness_fraction": args.tip_fraction,
            "normal_termination": normal_termination(name),
            "return_code": return_code,
            "wall_time_seconds": elapsed,
            "negative_jacobian_trial_messages": log_text.count(
                "negative jacobians detected"
            ),
        }
        if row["normal_termination"]:
            summary = process(name)
            row.update(
                {
                    "node_count": int(summary["node_count"]),
                    "element_count": int(summary["element_count"]),
                    "endpoint_strain": float(
                        summary["conductive_gauge_endpoint_engineering_strain"]
                    ),
                    "path_strain": float(
                        summary["conductive_gauge_centroid_path_engineering_strain"]
                    ),
                    "endpoint_transfer_ratio": float(summary["strain_transfer_ratio"]),
                }
            )
        rows.append(row)
        print(json.dumps(row, indent=2))

    completed_rows = [row for row in rows if row["normal_termination"]]
    metrics = {"status": "incomplete three-level study"}
    if len(completed_rows) == 3:
        fine = completed_rows[-1]
        for row in completed_rows:
            row["endpoint_difference_vs_fine_percent"] = 100.0 * abs(
                row["endpoint_strain"] - fine["endpoint_strain"]
            ) / abs(fine["endpoint_strain"])
            row["path_difference_vs_fine_percent"] = 100.0 * abs(
                row["path_strain"] - fine["path_strain"]
            ) / abs(fine["path_strain"])
        r21 = (completed_rows[2]["element_count"] / completed_rows[1]["element_count"]) ** (1.0 / 3.0)
        r32 = (completed_rows[1]["element_count"] / completed_rows[0]["element_count"]) ** (1.0 / 3.0)

        def observed_order(coarse: float, medium: float, fine_value: float) -> float:
            ratio = (coarse - medium) / (medium - fine_value)
            low, high = 1e-6, 10.0
            for _ in range(100):
                trial = 0.5 * (low + high)
                predicted = r21**trial * (r32**trial - 1.0) / (r21**trial - 1.0)
                if predicted > ratio:
                    high = trial
                else:
                    low = trial
            return 0.5 * (low + high)

        metrics = {
            "status": "three normal terminations; monotonic but not mesh-independent",
            "effective_spacing_ratio_medium_to_fine": r21,
            "effective_spacing_ratio_coarse_to_medium": r32,
            "effective_spacing_definition": "h proportional to element_count^(-1/3); only indicative for nonuniform anisotropic local meshes",
        }
        for field, label in (("endpoint_strain", "endpoint"), ("path_strain", "path")):
            coarse, medium, fine_value = [row[field] for row in completed_rows]
            order = observed_order(coarse, medium, fine_value)
            gci_fine = 1.25 * abs((fine_value - medium) / fine_value) / (r21**order - 1.0)
            extrapolated = fine_value + (fine_value - medium) / (r21**order - 1.0)
            metrics[f"{label}_observed_order_indicative"] = order
            metrics[f"{label}_fine_grid_GCI_percent_indicative"] = 100.0 * gci_fine
            metrics[f"{label}_richardson_extrapolated_strain_indicative"] = extrapolated

    stem = (
        f"taper_mesh_convergence_{token(args.taper_mm)}mm_"
        f"tip{token(100 * args.tip_fraction)}pct"
    )
    output_json = ROOT / "results" / f"{stem}.json"
    output_csv = ROOT / "results" / f"{stem}.csv"
    output_json.write_text(json.dumps({"rows": rows, "metrics": metrics}, indent=2) + "\n")
    fields = sorted({key for row in rows for key in row})
    with output_csv.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {output_json}")
    print(f"Wrote {output_csv}")


if __name__ == "__main__":
    main()
