#!/usr/bin/env python3
"""Generate, solve, and compare three systematic coupon mesh levels."""

from __future__ import annotations

import csv
import argparse
import json
import math
import subprocess
import time
from pathlib import Path

from generate_coupon import generate
from postprocess_coupon import process


ROOT = Path(__file__).resolve().parents[1]
FEBIO = Path("/Applications/FEBioStudio/FEBioStudio.app/Contents/MacOS/febio4")
LEVELS = ("coarse", "medium", "fine")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reuse-existing", action="store_true")
    args = parser.parse_args()
    rows: list[dict[str, float | int | str]] = []
    for level in LEVELS:
        case_name = f"coupon_mesh_{level}"
        log_path = ROOT / "results" / f"{case_name}.log"
        metadata_path = ROOT / "model" / f"{case_name}_metadata.json"
        can_reuse = (
            args.reuse_existing
            and log_path.exists()
            and metadata_path.exists()
            and "N O R M A L   T E R M I N A T I O N" in log_path.read_text(errors="replace")
        )
        if can_reuse:
            elapsed = 0.0
        else:
            generate(case_name=case_name, mesh_level=level, material_case="provisional")
            started = time.perf_counter()
            completed = subprocess.run(
                [str(FEBIO), "-i", f"model/{case_name}.feb"],
                cwd=ROOT,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.STDOUT,
                check=False,
            )
            elapsed = time.perf_counter() - started
            if completed.returncode != 0:
                raise RuntimeError(f"FEBio failed for {case_name} with code {completed.returncode}")
        summary = process(case_name)
        summary["wall_time_seconds"] = round(elapsed, 4)
        rows.append(summary)
        print(
            f"{level}: {summary['element_count']} elements, "
            f"gauge strain={summary['mean_conductive_gauge_strain']:.8f}, "
            f"time={elapsed:.2f} s"
        )

    fine_value = float(rows[-1]["mean_conductive_gauge_strain"])
    for row in rows:
        value = float(row["mean_conductive_gauge_strain"])
        row["relative_error_vs_fine_percent"] = abs(value - fine_value) / abs(fine_value) * 100.0

    json_path = ROOT / "results" / "mesh_convergence.json"
    csv_path = ROOT / "results" / "mesh_convergence.csv"
    metrics_path = ROOT / "results" / "mesh_convergence_metrics.json"
    json_path.write_text(json.dumps(rows, indent=2) + "\n")
    fieldnames = [
        "mesh_level",
        "node_count",
        "element_count",
        "wall_time_seconds",
        "mean_conductive_gauge_strain",
        "strain_transfer_ratio",
        "predicted_delta_R_over_R0",
        "relative_error_vs_fine_percent",
    ]
    with csv_path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

    coarse, medium, fine = [float(row["mean_conductive_gauge_strain"]) for row in rows]
    refinement_ratio = 2.0
    difference_ratio = abs((coarse - medium) / (medium - fine))
    apparent_order = math.log(difference_ratio) / math.log(refinement_ratio)
    denominator = refinement_ratio**apparent_order - 1.0
    extrapolated = fine + (fine - medium) / denominator
    fine_gci_percent = (
        1.25 * abs((fine - medium) / fine) / abs(denominator) * 100.0
    )
    metrics = {
        "refinement_ratio": refinement_ratio,
        "apparent_order": apparent_order,
        "richardson_extrapolated_gauge_strain": extrapolated,
        "fine_grid_convergence_index_percent": fine_gci_percent,
        "status": "not paper-ready" if fine_gci_percent > 2.0 else "acceptable screening convergence",
        "recommended_action": "Use local refinement at the two printed-patch ends and repeat until GCI is below 2%.",
    }
    metrics_path.write_text(json.dumps(metrics, indent=2) + "\n")
    print(f"Wrote {csv_path}")
    print(f"Wrote {json_path}")
    print(f"Wrote {metrics_path}")


if __name__ == "__main__":
    main()
