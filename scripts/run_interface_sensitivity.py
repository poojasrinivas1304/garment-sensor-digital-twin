#!/usr/bin/env python3
"""Run a bounded perfect-bond/compliant-interphase sensitivity study."""

from __future__ import annotations

import csv
import json
import subprocess
from pathlib import Path

from generate_coupon import generate


ROOT = Path(__file__).resolve().parents[1]
FEBIO = Path("/Applications/FEBioStudio/FEBioStudio.app/Contents/MacOS/febio4")
INTERFACE_THICKNESS_MM = 0.05
CASES = (
    ("interface_perfect_bond_local_medium", 0.0, None, 0.0),
    ("interface_E0p01_local_medium", INTERFACE_THICKNESS_MM, 0.01, 0.0),
    ("interface_E0p1_local_medium", INTERFACE_THICKNESS_MM, 0.10, 0.0),
    ("interface_E1_local_medium", INTERFACE_THICKNESS_MM, 1.00, 0.0),
    ("interface_E0p1_debond5_local_medium", INTERFACE_THICKNESS_MM, 0.10, 5.0),
)


def normally_terminated(log_path: Path) -> bool:
    return log_path.exists() and "N O R M A L   T E R M I N A T I O N" in log_path.read_text(
        errors="replace"
    )


def main() -> None:
    rows: list[dict[str, object]] = []
    for case, thickness, modulus, debond_length in CASES:
        kwargs = dict(
            case_name=case,
            mesh_level="local_medium",
            material_case="literature_nominal",
            coupon_strain=0.30,
            taper_length_mm=5.0,
            tip_thickness_fraction=0.25,
            interface_thickness_mm=thickness,
            interface_debond_length_mm=debond_length,
        )
        if modulus is not None:
            kwargs["interface_E_MPa"] = modulus
        generate(**kwargs)

        log_path = ROOT / "results" / f"{case}.log"
        if not normally_terminated(log_path):
            subprocess.run(
                [str(FEBIO), "-i", str(ROOT / "model" / f"{case}.feb")],
                cwd=ROOT,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.STDOUT,
                check=True,
            )
        subprocess.run(
            ["python3", str(ROOT / "scripts" / "postprocess_coupon.py"), "--case", case],
            cwd=ROOT,
            stdout=subprocess.DEVNULL,
            check=True,
        )
        summary = json.loads((ROOT / "results" / f"{case}_summary.json").read_text())
        rows.append(
            {
                "case": case,
                "bond_model": (
                    "perfect shared-node"
                    if thickness == 0.0
                    else "finite compliant interphase with initialized end debond"
                    if debond_length > 0.0
                    else "finite compliant interphase"
                ),
                "interface_thickness_mm": thickness,
                "interface_E_MPa": modulus,
                "interface_nu": None if thickness == 0.0 else 0.30,
                "initialized_unbonded_length_each_end_mm": debond_length,
                "endpoint_strain_percent": 100.0 * summary["conductive_gauge_endpoint_engineering_strain"],
                "path_strain_percent": 100.0 * summary["conductive_gauge_centroid_path_engineering_strain"],
                "endpoint_transfer_percent": 100.0 * summary["strain_transfer_ratio"],
                "normal_termination": normally_terminated(log_path),
                "element_count": summary["element_count"],
            }
        )

    perfect = float(rows[0]["endpoint_transfer_percent"])
    for row in rows:
        value = float(row["endpoint_transfer_percent"])
        row["endpoint_transfer_change_vs_perfect_percent"] = 100.0 * (value - perfect) / perfect

    json_path = ROOT / "results" / "interface_sensitivity.json"
    csv_path = ROOT / "results" / "interface_sensitivity.csv"
    json_path.write_text(json.dumps(rows, indent=2) + "\n")
    with csv_path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(json.dumps(rows, indent=2))
    print(f"Wrote {json_path}")
    print(f"Wrote {csv_path}")


if __name__ == "__main__":
    main()
