#!/usr/bin/env python3
"""Solve and summarize patch-edge-refined mesh families."""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import time
from pathlib import Path

from generate_coupon import ROOT, generate
from postprocess_coupon import process


FEBIO = Path("/Applications/FEBioStudio/FEBioStudio.app/Contents/MacOS/febio4")
LEVELS = ("local_coarse", "local_medium", "local_fine")


def solve(level: str) -> dict:
    case_name = level.replace("local_", "local_mesh_")
    log_path = ROOT / "results" / f"{case_name}.log"
    complete = (
        log_path.exists()
        and "N O R M A L   T E R M I N A T I O N"
        in log_path.read_text(errors="replace")
    )
    elapsed = 0.0
    if not complete:
        generate(
            case_name=case_name,
            mesh_level=level,
            material_case="literature_nominal",
        )
        started = time.perf_counter()
        completed = subprocess.run(
            [str(FEBIO), "-i", str(ROOT / "model" / f"{case_name}.feb")],
            cwd=ROOT,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.STDOUT,
            check=False,
        )
        elapsed = time.perf_counter() - started
        if completed.returncode != 0:
            raise RuntimeError(f"FEBio failed for {case_name}: {completed.returncode}")
    summary = process(case_name)
    summary["wall_time_seconds"] = elapsed
    print(
        f"{level}: {summary['element_count']} elements, "
        f"transfer={100 * summary['strain_transfer_ratio']:.5f}%, "
        f"time={elapsed:.1f}s"
    )
    return summary


def summarize() -> None:
    rows = []
    for level in LEVELS:
        case_name = level.replace("local_", "local_mesh_")
        summary_path = ROOT / "results" / f"{case_name}_summary.json"
        if not summary_path.exists():
            raise RuntimeError(f"Missing completed summary: {summary_path}")
        rows.append(json.loads(summary_path.read_text()))

    fine = float(rows[-1]["mean_conductive_gauge_strain"])
    for row in rows:
        value = float(row["mean_conductive_gauge_strain"])
        row["relative_error_vs_local_fine_percent"] = 100.0 * abs(value - fine) / abs(fine)
    medium_fine_difference = 100.0 * abs(
        float(rows[1]["mean_conductive_gauge_strain"]) - fine
    ) / abs(fine)
    metrics = {
        "medium_fine_difference_percent": medium_fine_difference,
        "screening_target_percent": 2.0,
        "status": "acceptable" if medium_fine_difference < 2.0 else "refine further",
        "note": "Nonuniform local meshes are compared directly; a formal constant-ratio GCI is not claimed.",
    }
    results = ROOT / "results"
    (results / "local_mesh_convergence.json").write_text(json.dumps(rows, indent=2) + "\n")
    (results / "local_mesh_convergence_metrics.json").write_text(
        json.dumps(metrics, indent=2) + "\n"
    )
    with (results / "local_mesh_convergence.csv").open("w", newline="") as handle:
        fields = [
            "mesh_level", "node_count", "element_count",
            "mean_conductive_gauge_strain", "strain_transfer_ratio",
            "relative_error_vs_local_fine_percent",
        ]
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    print(json.dumps(metrics, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--level", choices=LEVELS)
    parser.add_argument("--summarize", action="store_true")
    args = parser.parse_args()
    if args.level:
        solve(args.level)
    if args.summarize:
        summarize()
    if not args.level and not args.summarize:
        for level in LEVELS:
            solve(level)
        summarize()


if __name__ == "__main__":
    main()
