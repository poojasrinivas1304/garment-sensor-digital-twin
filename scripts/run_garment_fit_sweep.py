#!/usr/bin/env python3
"""Run independent one-step garment-fit cases without overwriting verified data."""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FEBIO = Path("/Applications/FEBioStudio/FEBioStudio.app/Contents/MacOS/febio4")
PRESTRAINS = (0.9975, 0.9970, 0.9965, 0.9960, 0.9950, 0.9925, 0.9900)
OUTPUT = ROOT / "results" / "garment_fit_sweep.json"


def case_name(value: float) -> str:
    contraction_bp = round((1.0 - value) * 10000)
    return f"garment_fit_{contraction_bp:04d}bp"


def main() -> None:
    records = []
    for prestrain in PRESTRAINS:
        case = case_name(prestrain)
        model = ROOT / "model" / f"{case}.feb"
        subprocess.run(
            [
                "python3",
                str(ROOT / "scripts" / "generate_garment_contact.py"),
                "--case",
                case,
                "--prestrain",
                str(prestrain),
            ],
            cwd=ROOT,
            check=True,
            stdout=subprocess.DEVNULL,
        )
        try:
            completed = subprocess.run(
                [str(FEBIO), "-i", str(model.relative_to(ROOT))],
                cwd=ROOT,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.STDOUT,
                timeout=60,
                check=False,
            )
            exit_code = completed.returncode
            timed_out = False
        except subprocess.TimeoutExpired:
            exit_code = 124
            timed_out = True

        log_path = ROOT / "results" / f"{case}.log"
        log_text = log_path.read_text(errors="replace") if log_path.exists() else ""
        normal = "N O R M A L   T E R M I N A T I O N" in log_text
        negative_jacobians = [
            int(value)
            for value in re.findall(r"(\d+) negative jacobians detected", log_text)
        ]
        record = {
            "case": case,
            "prestrain_gradient": prestrain,
            "nominal_contraction_percent": (1.0 - prestrain) * 100.0,
            "exit_code": exit_code,
            "timed_out": timed_out,
            "normal_termination": normal,
            "maximum_reported_negative_jacobians": max(negative_jacobians, default=0),
        }
        if normal:
            subprocess.run(
                [
                    "python3",
                    str(ROOT / "scripts" / "postprocess_garment_contact.py"),
                    "--case",
                    case,
                    "--no-figure",
                ],
                cwd=ROOT,
                check=True,
                stdout=subprocess.DEVNULL,
            )
            summary = json.loads(
                (ROOT / "results" / f"{case}_summary.json").read_text()
            )
            record.update(summary["contact"])
            record["maximum_nodal_displacement_mm"] = summary["kinematics"][
                "maximum_nodal_displacement_mm"
            ]
        records.append(record)
        print(
            f"{case}: normal={normal}, exit={exit_code}, "
            f"active={record.get('active_facets', 0)}"
        )

    payload = {
        "description": "Independent one-step contraction sweep from the same reference mesh",
        "acceptance": {
            "normal_termination": True,
            "maximum_absolute_active_gap_mm": 0.01,
            "maximum_reported_negative_jacobians": 0,
        },
        "cases": records,
    }
    OUTPUT.write_text(json.dumps(payload, indent=2) + "\n")
    print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    main()
