#!/usr/bin/env python3
"""Run legacy one-at-a-time mechanical material sensitivity cases."""

from __future__ import annotations

import csv
import json
import subprocess
import time
from pathlib import Path

from generate_coupon import MATERIAL_CASES, generate
from postprocess_coupon import process


ROOT = Path(__file__).resolve().parents[1]
FEBIO = Path("/Applications/FEBioStudio/FEBioStudio.app/Contents/MacOS/febio4")
CASES = (
    "literature_nominal",
    "nylon_low",
    "nylon_high",
    "backing_low",
    "backing_high",
    "conductive_low",
    "conductive_high",
)


def main() -> None:
    rows: list[dict[str, float | int | str]] = []
    for material_case in CASES:
        case_name = f"material_{material_case}"
        generate(case_name=case_name, mesh_level="medium", material_case=material_case)
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
        properties = MATERIAL_CASES[material_case]
        row = {
            **summary,
            "wall_time_seconds": round(elapsed, 4),
            "nylon_E_MPa": properties["nylon"]["E_MPa"],
            "backing_E_MPa": properties["backing_tpu"]["E_MPa"],
            "conductive_E_MPa": properties["conductive_tpu"]["E_MPa"],
        }
        rows.append(row)
        print(
            f"{material_case}: gauge strain={summary['mean_conductive_gauge_strain']:.8f}, "
            f"transfer={summary['strain_transfer_ratio']:.4f}, time={elapsed:.2f} s"
        )

    nominal = float(rows[0]["mean_conductive_gauge_strain"])
    for row in rows:
        value = float(row["mean_conductive_gauge_strain"])
        row["change_from_nominal_percent"] = (value - nominal) / nominal * 100.0

    json_path = ROOT / "results" / "material_sensitivity.json"
    csv_path = ROOT / "results" / "material_sensitivity.csv"
    json_path.write_text(json.dumps(rows, indent=2) + "\n")
    fieldnames = [
        "material_case",
        "nylon_E_MPa",
        "backing_E_MPa",
        "conductive_E_MPa",
        "mean_conductive_gauge_strain",
        "strain_transfer_ratio",
        "change_from_nominal_percent",
        "wall_time_seconds",
    ]
    with csv_path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {csv_path}")
    print(f"Wrote {json_path}")


if __name__ == "__main__":
    main()
