#!/usr/bin/env python3
"""Screen textile compressibility and nonlinear-fibre shape parameters."""

from __future__ import annotations

import csv
import json
import subprocess
from pathlib import Path

from generate_coupon import MATERIAL_CASES, ROOT, generate
from postprocess_coupon import process


FEBIO = Path("/Applications/FEBioStudio/FEBioStudio.app/Contents/MacOS/febio4")
ISOTROPIC_CASES = (
    "textile_nu_low", "literature_nominal", "textile_nu_high",
    "tpu_nu_low", "tpu_nu_high",
)
FIBRE_CASES = (
    "textile_fiber_bulk_low",
    "textile_fiber_balanced",
    "textile_fiber_bulk_high",
    "textile_fiber_c4_low",
    "textile_fiber_c4_high",
    "textile_fiber_transition_low",
    "textile_fiber_transition_high",
)


def complete(case: str) -> bool:
    path = ROOT / "results" / f"{case}.log"
    return path.exists() and "N O R M A L   T E R M I N A T I O N" in path.read_text(
        errors="replace"
    )


def solve(case: str) -> dict:
    if not complete(case):
        completed = subprocess.run(
            [str(FEBIO), "-i", str(ROOT / "model" / f"{case}.feb")],
            cwd=ROOT,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.STDOUT,
            check=False,
        )
        if completed.returncode != 0 or not complete(case):
            raise RuntimeError(f"FEBio failed for {case}: {completed.returncode}")
    return process(case)


def main() -> None:
    rows: list[dict[str, object]] = []
    for material_case in ISOTROPIC_CASES:
        case = f"compressibility_{material_case}_medium"
        generate(case_name=case, mesh_level="medium", material_case=material_case)
        result = solve(case)
        props = MATERIAL_CASES[material_case]["nylon"]
        is_tpu_case = material_case.startswith("tpu_nu_")
        varied_nu = (
            MATERIAL_CASES[material_case]["backing_tpu"]["nu"]
            if is_tpu_case else props["nu"]
        )
        rows.append(
            {
                "family": (
                    "isotropic_tpu_poisson_ratio"
                    if is_tpu_case else "isotropic_textile_poisson_ratio"
                ),
                "material_case": material_case,
                "loading_angle_deg": 0.0,
                "parameter_name": "tpu_nu" if is_tpu_case else "textile_nu",
                "parameter_value": varied_nu,
                "endpoint_strain_percent": 100.0 * result["conductive_gauge_endpoint_engineering_strain"],
                "endpoint_transfer_percent": 100.0 * result["strain_transfer_ratio"],
                "normal_termination": complete(case),
                "case": case,
            }
        )

    for material_case in FIBRE_CASES:
        props = MATERIAL_CASES[material_case]["nylon"]
        if "bulk_" in material_case:
            parameter_name, parameter_value = "bulk_modulus_MPa", props["bulk_modulus_MPa"]
        elif "c4_" in material_case:
            parameter_name, parameter_value = "fiber_c4", props["fiber_c4"]
        elif "transition_" in material_case:
            parameter_name, parameter_value = "fiber_transition_stretch", props["fiber_transition_stretch"]
        else:
            parameter_name, parameter_value = "balanced_nominal", 1.0
        for angle in (0.0, 60.0):
            label = material_case.removeprefix("textile_fiber_")
            case = f"shape_{label}_angle_{angle:g}_local_medium"
            generate(
                case_name=case,
                mesh_level="local_medium",
                material_case=material_case,
                taper_length_mm=5.0,
                tip_thickness_fraction=0.25,
                loading_angle_deg=angle,
                remote_transverse_ratio=0.30,
            )
            result = solve(case)
            rows.append(
                {
                    "family": "two_fibre_shape_or_compressibility",
                    "material_case": material_case,
                    "loading_angle_deg": angle,
                    "parameter_name": parameter_name,
                    "parameter_value": parameter_value,
                    "endpoint_strain_percent": 100.0 * result["conductive_gauge_endpoint_engineering_strain"],
                    "endpoint_transfer_percent": 100.0 * result["strain_transfer_ratio"],
                    "normal_termination": complete(case),
                    "case": case,
                }
            )

    output = {
        "status": "provisional constitutive-shape sensitivity; parameter brackets are not calibrated product properties",
        "all_normal_termination": all(bool(row["normal_termination"]) for row in rows),
        "rows": rows,
    }
    json_path = ROOT / "results" / "constitutive_shape_sensitivity.json"
    csv_path = ROOT / "results" / "constitutive_shape_sensitivity.csv"
    json_path.write_text(json.dumps(output, indent=2) + "\n")
    with csv_path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(json.dumps({k: v for k, v in output.items() if k != "rows"}, indent=2))
    print(f"Wrote {json_path}")
    print(f"Wrote {csv_path}")


if __name__ == "__main__":
    main()
