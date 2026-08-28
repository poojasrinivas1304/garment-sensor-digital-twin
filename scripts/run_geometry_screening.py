#!/usr/bin/env python3
"""Run a one-factor-at-a-time screening study for coupon geometry."""

from __future__ import annotations

import csv
import json
import subprocess
from pathlib import Path

from generate_coupon import ROOT, generate
from postprocess_coupon import process


FEBIO = Path("/Applications/FEBioStudio/FEBioStudio.app/Contents/MacOS/febio4")
BASELINE = {
    "sensor_length_mm": 80.0,
    "sensor_width_mm": 15.0,
    "backing_thickness_mm": 0.4,
    "conductive_thickness_mm": 0.6,
    "coupon_strain": 0.30,
}
LEVELS = {
    "sensor_length_mm": [40.0, 60.0, 80.0, 100.0],
    "sensor_width_mm": [5.0, 10.0, 15.0, 20.0],
    "backing_thickness_mm": [0.2, 0.4, 0.6, 0.8],
    "conductive_thickness_mm": [0.2, 0.4, 0.6, 0.8],
}


def token(value: float) -> str:
    return f"{value:g}".replace(".", "p")


def cases() -> list[tuple[str, str, float, dict[str, float]]]:
    output: list[tuple[str, str, float, dict[str, float]]] = []
    for parameter, values in LEVELS.items():
        for value in values:
            geometry = dict(BASELINE)
            geometry[parameter] = value
            name = f"geometry_{parameter.removesuffix('_mm')}_{token(value)}"
            output.append((name, parameter, value, geometry))
    return output


def main() -> None:
    if not FEBIO.exists():
        raise FileNotFoundError(f"FEBio executable not found at {FEBIO}")

    rows = []
    for case_name, parameter, value, geometry in cases():
        generate(
            case_name=case_name,
            mesh_level="coarse",
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
                "varied_parameter": parameter,
                "parameter_value": value,
                **geometry,
                "mean_conductive_gauge_strain": summary["mean_conductive_gauge_strain"],
                "strain_transfer_ratio": summary["strain_transfer_ratio"],
                "predicted_delta_R_over_R0": summary["predicted_delta_R_over_R0"],
                "element_count": summary["element_count"],
            }
        )

    results_dir = ROOT / "results"
    json_path = results_dir / "geometry_screening.json"
    csv_path = results_dir / "geometry_screening.csv"
    json_path.write_text(json.dumps(rows, indent=2) + "\n")
    with csv_path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {csv_path}")
    print(f"Wrote {json_path}")


if __name__ == "__main__":
    main()
