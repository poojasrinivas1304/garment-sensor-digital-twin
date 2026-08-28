#!/usr/bin/env python3
"""Run matched-reference OFAT garment-contact sensitivity cases at 25% movement."""

from __future__ import annotations

import csv
import json
import subprocess
from pathlib import Path

from generate_garment_contact import build_model


ROOT = Path(__file__).resolve().parents[1]
FEBIO = Path("/Applications/FEBioStudio/FEBioStudio.app/Contents/MacOS/febio4")
VARIANTS = (
    ("baseline", 0.001, 0.8, 0.5, 5, 188.0, 165.0),
    ("penalty_low", 0.0005, 0.8, 0.5, 5, 188.0, 165.0),
    ("penalty_high", 0.002, 0.8, 0.5, 5, 188.0, 165.0),
    ("garment_E_low", 0.001, 0.4, 0.5, 5, 188.0, 165.0),
    ("garment_E_high", 0.001, 1.6, 0.5, 5, 188.0, 165.0),
    ("garment_E_extended_low", 0.001, 0.1, 0.5, 5, 188.0, 165.0),
    ("garment_E_extended_midlow", 0.001, 0.2, 0.5, 5, 188.0, 165.0),
    ("garment_E_extended_high", 0.001, 5.0, 0.5, 5, 188.0, 165.0),
    ("clearance_low", 0.001, 0.8, 0.4, 5, 188.0, 165.0),
    ("clearance_high", 0.001, 0.8, 0.6, 5, 188.0, 165.0),
    ("augmentations_low", 0.001, 0.8, 0.5, 3, 188.0, 165.0),
    ("augmentations_high", 0.001, 0.8, 0.5, 8, 188.0, 165.0),
    ("torso_radii_low", 0.001, 0.8, 0.5, 5, 183.0, 160.0),
    ("torso_radii_high", 0.001, 0.8, 0.5, 5, 193.0, 170.0),
)


def terminated(log_path: Path) -> bool:
    return log_path.exists() and "N O R M A L   T E R M I N A T I O N" in log_path.read_text(
        errors="replace"
    )


def failed(log_path: Path) -> bool:
    return log_path.exists() and "E R R O R   T E R M I N A T I O N" in log_path.read_text(
        errors="replace"
    )


def write_case(case: str, *, movement: bool, penalty: float, garment_E: float,
               clearance: float, maxaug: int, torso_rx: float, torso_ry: float) -> None:
    tree, metadata = build_model(
        case=case,
        time_steps=40 if movement else 20,
        augmented_contact=True,
        contact_tolerance=0.1,
        contact_maxaug=maxaug,
        penalty_scale=penalty,
        torso_expansion_mm=0.6,
        initial_clearance_mm=clearance,
        garment_E_MPa=garment_E,
        torso_rx_mm=torso_rx,
        torso_ry_mm=torso_ry,
        auto_penalty=False,
        movement="both_arms_raise" if movement else None,
        movement_stage_fraction=0.5,
        movement_scale=0.25,
    )
    model_path = ROOT / "model" / f"{case}.feb"
    metadata_path = ROOT / "model" / f"{case}_metadata.json"
    tree.write(model_path, encoding="utf-8", xml_declaration=True)
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n")


def solve_and_postprocess(case: str) -> dict | None:
    log_path = ROOT / "results" / f"{case}.log"
    if failed(log_path):
        return None
    if not terminated(log_path):
        completed = subprocess.run(
            [str(FEBIO), "-i", str(ROOT / "model" / f"{case}.feb")],
            cwd=ROOT,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.STDOUT,
            check=False,
        )
        if completed.returncode != 0 or not terminated(log_path):
            return None
    subprocess.run(
        ["python3", str(ROOT / "scripts" / "postprocess_garment_movement.py"),
         "--case", case, "--no-figure"],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        check=True,
    )
    return json.loads((ROOT / "results" / f"{case}_movement_summary.json").read_text())


def main() -> None:
    with (ROOT / "results" / "garment_kinematic_screen.csv").open() as stream:
        free_rows = [
            row for row in csv.DictReader(stream) if row["posture"] == "both_arms_raise"
        ]
    contact_free = {
        int(row["sensor"]): 0.25 * float(row["projected_sensor_axis_strain"])
        for row in free_rows
    }

    rows: list[dict[str, object]] = []
    variant_status: list[dict[str, object]] = []
    for name, penalty, garment_E, clearance, maxaug, torso_rx, torso_ry in VARIANTS:
        reference_case = f"contact_sensitivity_{name}_reference"
        movement_case = f"contact_sensitivity_{name}_movement025"
        write_case(reference_case, movement=False, penalty=penalty, garment_E=garment_E,
                   clearance=clearance, maxaug=maxaug, torso_rx=torso_rx, torso_ry=torso_ry)
        write_case(movement_case, movement=True, penalty=penalty, garment_E=garment_E,
                   clearance=clearance, maxaug=maxaug, torso_rx=torso_rx, torso_ry=torso_ry)
        reference = solve_and_postprocess(reference_case)
        if reference is None:
            variant_status.append(
                {
                    "variant": name,
                    "status": "excluded: reference did not terminate normally",
                    "reference_case": reference_case,
                    "movement_case": "not run",
                }
            )
            continue
        movement = solve_and_postprocess(movement_case)
        if movement is None:
            variant_status.append(
                {
                    "variant": name,
                    "status": "excluded: movement case did not terminate normally",
                    "reference_case": reference_case,
                    "movement_case": movement_case,
                }
            )
            continue
        variant_status.append(
            {
                "variant": name,
                "status": "included: both cases terminated normally",
                "reference_case": reference_case,
                "movement_case": movement_case,
            }
        )
        reference_sensor = {x["sensor"]: x for x in reference["sensor_strains"]}
        movement_sensor = {x["sensor"]: x for x in movement["sensor_strains"]}
        for sensor in range(1, 11):
            delta = (
                movement_sensor[sensor]["projected_sensor_axis_green_strain"]
                - reference_sensor[sensor]["projected_sensor_axis_green_strain"]
            )
            free = contact_free[sensor]
            rows.append(
                {
                    "variant": name,
                    "sensor": sensor,
                    "penalty_scale": penalty,
                    "garment_E_MPa": garment_E,
                    "initial_clearance_mm": clearance,
                    "final_nominal_interference_mm": 0.6 - clearance,
                    "maximum_augmentations": maxaug,
                    "torso_rx_mm": torso_rx,
                    "torso_ry_mm": torso_ry,
                    "movement_induced_strain_percent": 100.0 * delta,
                    "contact_free_scaled_strain_percent": 100.0 * free,
                    "sign_reversal_vs_contact_free": delta * free < 0.0,
                    "movement_active_contact_fraction": movement["contact"]["active_facet_fraction"],
                    "reference_normal_termination": reference["febio_normal_termination"],
                    "movement_normal_termination": movement["febio_normal_termination"],
                }
            )

    s3s8 = [row for row in rows if row["sensor"] in (3, 8)]
    summary = {
        "design": "one-factor-at-a-time around the baseline; matched fitted reference subtracted for each variant",
        "movement_amplitude_fraction": 0.25,
        "attempted_variant_count": len(VARIANTS),
        "completed_variant_count": len({row["variant"] for row in rows}),
        "all_attempted_variants_included": len({row["variant"] for row in rows}) == len(VARIANTS),
        "variant_status": variant_status,
        "s3_s8_reversal_persisted_in_all_variants": all(
            row["sign_reversal_vs_contact_free"] for row in s3s8
        ),
        "s3_s8_movement_induced_strain_percent_range": [
            min(float(row["movement_induced_strain_percent"]) for row in s3s8),
            max(float(row["movement_induced_strain_percent"]) for row in s3s8),
        ],
        "rows": rows,
    }
    json_path = ROOT / "results" / "garment_contact_sensitivity.json"
    csv_path = ROOT / "results" / "garment_contact_sensitivity.csv"
    json_path.write_text(json.dumps(summary, indent=2) + "\n")
    with csv_path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(json.dumps({k: v for k, v in summary.items() if k != "rows"}, indent=2))
    print(f"Wrote {json_path}")
    print(f"Wrote {csv_path}")


if __name__ == "__main__":
    main()
