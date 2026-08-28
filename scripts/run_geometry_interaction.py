#!/usr/bin/env python3
"""Run a limited 2x2 length-by-width interaction screen."""

from __future__ import annotations

import csv
import json
import subprocess
from pathlib import Path

from generate_coupon import ROOT, generate
from postprocess_coupon import process


FEBIO = Path("/Applications/FEBioStudio/FEBioStudio.app/Contents/MacOS/febio4")
LEVELS = ((60.0, 10.0), (60.0, 20.0), (100.0, 10.0), (100.0, 20.0))


def token(value: float) -> str:
    return f"{value:g}".replace(".", "p")


def main() -> None:
    rows: list[dict[str, object]] = []
    for length, width in LEVELS:
        case = f"geometry_interaction_L{token(length)}_W{token(width)}"
        generate(
            case_name=case,
            mesh_level="coarse",
            material_case="literature_nominal",
            sensor_length_mm=length,
            sensor_width_mm=width,
            backing_thickness_mm=0.4,
            conductive_thickness_mm=0.6,
            coupon_strain=0.30,
        )
        completed = subprocess.run(
            [str(FEBIO), "-i", str(ROOT / "model" / f"{case}.feb")],
            cwd=ROOT,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.STDOUT,
            check=False,
        )
        if completed.returncode != 0:
            raise RuntimeError(f"FEBio failed for {case}: {completed.returncode}")
        summary = process(case)
        rows.append(
            {
                "case": case,
                "sensor_length_mm": length,
                "sensor_width_mm": width,
                "endpoint_strain_percent": 100.0 * summary["conductive_gauge_endpoint_engineering_strain"],
                "endpoint_transfer_percent": 100.0 * summary["strain_transfer_ratio"],
                "normal_termination": "N O R M A L   T E R M I N A T I O N" in (
                    ROOT / "results" / f"{case}.log"
                ).read_text(errors="replace"),
                "element_count": summary["element_count"],
            }
        )

    lookup = {
        (float(row["sensor_length_mm"]), float(row["sensor_width_mm"])):
        float(row["endpoint_transfer_percent"])
        for row in rows
    }
    difference_in_differences = (
        lookup[(100.0, 20.0)] - lookup[(100.0, 10.0)]
        - lookup[(60.0, 20.0)] + lookup[(60.0, 10.0)]
    )
    interaction_coefficient = difference_in_differences / 4.0
    output = {
        "design": "2x2 length-by-width interaction screen on the coarse global screening mesh",
        "rows": rows,
        "difference_in_differences_percentage_points": difference_in_differences,
        "coded_interaction_coefficient_percentage_points": interaction_coefficient,
        "all_normal_termination": all(bool(row["normal_termination"]) for row in rows),
    }
    json_path = ROOT / "results" / "geometry_interaction.json"
    csv_path = ROOT / "results" / "geometry_interaction.csv"
    json_path.write_text(json.dumps(output, indent=2) + "\n")
    with csv_path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(json.dumps(output, indent=2))
    print(f"Wrote {json_path}")
    print(f"Wrote {csv_path}")


if __name__ == "__main__":
    main()
