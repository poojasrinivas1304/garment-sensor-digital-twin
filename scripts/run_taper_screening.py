#!/usr/bin/env python3
"""Screen printable thickness-taper lengths on the local-medium mesh."""

from __future__ import annotations

import csv
import json
import subprocess
from pathlib import Path

from generate_coupon import ROOT, generate
from postprocess_coupon import process


FEBIO = Path("/Applications/FEBioStudio/FEBioStudio.app/Contents/MacOS/febio4")
TAPER_CASES = {
    0.0: "local_mesh_medium",
    2.5: "taper_2p5mm_local_medium",
    5.0: "taper_5mm_local_medium",
    10.0: "taper_10mm_local_medium",
}
TIP_FRACTION = 0.25


def completed_log(case_name: str) -> bool:
    path = ROOT / "results" / f"{case_name}.log"
    return path.exists() and "N O R M A L   T E R M I N A T I O N" in path.read_text(errors="replace")


def main() -> None:
    rows = []
    for taper_length, case_name in TAPER_CASES.items():
        if not completed_log(case_name):
            generate(
                case_name=case_name,
                mesh_level="local_medium",
                material_case="literature_nominal",
                taper_length_mm=taper_length,
                tip_thickness_fraction=TIP_FRACTION,
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
                "taper_length_mm": taper_length,
                "tip_thickness_fraction": TIP_FRACTION if taper_length else 1.0,
                "mean_conductive_gauge_strain": summary["mean_conductive_gauge_strain"],
                "strain_transfer_ratio": summary["strain_transfer_ratio"],
                "predicted_delta_R_over_R0": summary["predicted_delta_R_over_R0"],
                "element_count": summary["element_count"],
            }
        )
        print(f"{taper_length:g} mm: transfer={100 * summary['strain_transfer_ratio']:.5f}%")

    results = ROOT / "results"
    (results / "taper_screening.json").write_text(json.dumps(rows, indent=2) + "\n")
    with (results / "taper_screening.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    main()
