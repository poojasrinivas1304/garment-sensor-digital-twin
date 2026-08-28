#!/usr/bin/env python3
"""Repeat selected geometry-screening cases on the medium mesh."""

from __future__ import annotations

import csv
import json
import subprocess
from pathlib import Path

from generate_coupon import ROOT, generate
from postprocess_coupon import process
from run_geometry_screening import BASELINE, FEBIO


SELECTED = [
    ("baseline", {}),
    ("length_40", {"sensor_length_mm": 40.0}),
    ("length_100", {"sensor_length_mm": 100.0}),
    ("width_5", {"sensor_width_mm": 5.0}),
    ("width_20", {"sensor_width_mm": 20.0}),
    ("backing_0p2", {"backing_thickness_mm": 0.2}),
    ("backing_0p8", {"backing_thickness_mm": 0.8}),
    ("conductive_0p2", {"conductive_thickness_mm": 0.2}),
    ("conductive_0p8", {"conductive_thickness_mm": 0.8}),
]


def main() -> None:
    rows = []
    for label, changes in SELECTED:
        geometry = {**BASELINE, **changes}
        case_name = f"geometry_verify_{label}_medium"
        try:
            summary = process(case_name)
            print(f"Reused completed {case_name}")
        except (FileNotFoundError, RuntimeError):
            generate(
                case_name=case_name,
                mesh_level="medium",
                material_case="literature_nominal",
                **geometry,
            )
            completed = subprocess.run(
                [str(FEBIO), "-i", str(ROOT / "model" / f"{case_name}.feb")],
                cwd=ROOT,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.STDOUT,
                check=False,
            )
            if completed.returncode != 0:
                raise RuntimeError(f"FEBio failed for {case_name}: {completed.returncode}")
            summary = process(case_name)
        rows.append(
            {
                "case_name": case_name,
                "design": label,
                **geometry,
                "mean_conductive_gauge_strain": summary["mean_conductive_gauge_strain"],
                "strain_transfer_ratio": summary["strain_transfer_ratio"],
                "element_count": summary["element_count"],
            }
        )

    output_json = ROOT / "results" / "geometry_medium_verification.json"
    output_csv = ROOT / "results" / "geometry_medium_verification.csv"
    output_json.write_text(json.dumps(rows, indent=2) + "\n")
    with output_csv.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {output_csv}")
    print(f"Wrote {output_json}")


if __name__ == "__main__":
    main()
