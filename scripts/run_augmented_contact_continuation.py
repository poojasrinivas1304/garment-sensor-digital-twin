#!/usr/bin/env python3
"""Audit staged fit-to-motion contact with penalty and augmented enforcement."""

from __future__ import annotations

import csv
import json
import subprocess
import time
from pathlib import Path

from generate_garment_contact import build_model


ROOT = Path(__file__).resolve().parents[1]
FEBIO = Path("/Applications/FEBioStudio/FEBioStudio.app/Contents/MacOS/febio4")
VARIANTS = (
    ("augmented_mu0p1", True, 0.1),
    ("augmented_mu0p3", True, 0.3),
)


def normal_termination(case: str) -> bool:
    path = ROOT / "results" / f"{case}.log"
    return path.exists() and "N O R M A L   T E R M I N A T I O N" in path.read_text(
        errors="replace"
    )


def generate_case(case: str, *, movement: bool, augmented: bool, mu: float) -> None:
    tree, metadata = build_model(
        case=case,
        time_steps=40 if movement else 20,
        augmented_contact=augmented,
        contact_tolerance=0.25,
        contact_maxaug=3,
        penalty_scale=0.001,
        torso_expansion_mm=0.6,
        initial_clearance_mm=0.5,
        garment_E_MPa=0.8,
        auto_penalty=False,
        friction_coefficient=mu,
        segment_updates=4,
        tangential_stiffness_multiplier=0.1,
        friction_formulation="node-on-facet",
        friction_penalty=1.0,
        movement="both_arms_raise" if movement else None,
        movement_stage_fraction=0.5,
        movement_scale=0.25,
    )
    metadata["continuation_audit"] = {
        "fit_stage": "torso expansion reaches its final value by normalized time 0.5",
        "motion_stage": "arm-raise displacement is zero through time 0.5 and ramps thereafter",
        "comparison_role": "matched penalty/augmented enforcement at mu=0.1",
    }
    tree.write(ROOT / "model" / f"{case}.feb", encoding="utf-8", xml_declaration=True)
    (ROOT / "model" / f"{case}_metadata.json").write_text(
        json.dumps(metadata, indent=2) + "\n"
    )


def solve(case: str) -> dict[str, object]:
    started = time.perf_counter()
    return_code = 0
    if not normal_termination(case):
        completed = subprocess.run(
            [str(FEBIO), "-i", str(ROOT / "model" / f"{case}.feb")],
            cwd=ROOT,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.STDOUT,
            check=False,
        )
        return_code = completed.returncode
    elapsed = time.perf_counter() - started
    log_path = ROOT / "results" / f"{case}.log"
    text = log_path.read_text(errors="replace") if log_path.exists() else ""
    status: dict[str, object] = {
        "case": case,
        "normal_termination": normal_termination(case),
        "return_code": return_code,
        "wall_time_seconds": elapsed,
        "negative_jacobian_trial_messages": text.count("negative jacobians detected"),
    }
    if status["normal_termination"]:
        subprocess.run(
            [
                "python3",
                str(ROOT / "scripts" / "postprocess_garment_movement.py"),
                "--case",
                case,
                "--no-figure",
            ],
            cwd=ROOT,
            stdout=subprocess.DEVNULL,
            check=True,
        )
        status["summary"] = json.loads(
            (ROOT / "results" / f"{case}_movement_summary.json").read_text()
        )
    return status


def main() -> None:
    with (ROOT / "results" / "garment_kinematic_screen.csv").open() as stream:
        free = {
            int(row["sensor"]): 0.25 * float(row["projected_sensor_axis_strain"])
            for row in csv.DictReader(stream)
            if row["posture"] == "both_arms_raise"
        }

    statuses: list[dict[str, object]] = []
    rows: list[dict[str, object]] = []

    def append_pair(
        name: str,
        augmented: bool,
        mu: float,
        reference_case: str,
        movement_case: str,
        reference_summary: dict,
        movement_summary: dict,
    ) -> None:
        reference_sensors = {
            item["sensor"]: item for item in reference_summary["sensor_strains"]
        }
        movement_sensors = {
            item["sensor"]: item for item in movement_summary["sensor_strains"]
        }
        for sensor in range(1, 11):
            delta = (
                movement_sensors[sensor]["projected_sensor_axis_green_strain"]
                - reference_sensors[sensor]["projected_sensor_axis_green_strain"]
            )
            rows.append(
                {
                    "variant": name,
                    "augmented_lagrangian": augmented,
                    "friction_coefficient": mu,
                    "sensor": sensor,
                    "movement_induced_strain_percent": 100.0 * delta,
                    "contact_free_scaled_strain_percent": 100.0 * free[sensor],
                    "sign_reversal_vs_contact_free": delta * free[sensor] < 0.0,
                    "active_contact_fraction": movement_summary["contact"]["active_facet_fraction"],
                    "reference_case": reference_case,
                    "movement_case": movement_case,
                }
            )

    # Reuse the already completed, formulation-matched penalty-only pair as
    # the comparator; the new solves change only enforcement to augmented
    # Lagrangian (and separately test mu=0.3).
    archived_reference = "garment_friction_n2f_mu0p1_reference"
    archived_movement = "garment_friction_n2f_mu0p1_kt0p1_025"
    append_pair(
        "penalty_mu0p1_archived",
        False,
        0.1,
        archived_reference,
        archived_movement,
        json.loads((ROOT / "results" / f"{archived_reference}_movement_summary.json").read_text()),
        json.loads((ROOT / "results" / f"{archived_movement}_movement_summary.json").read_text()),
    )
    for name, augmented, mu in VARIANTS:
        reference_case = f"continuation_{name}_reference"
        movement_case = f"continuation_{name}_movement025"
        generate_case(reference_case, movement=False, augmented=augmented, mu=mu)
        generate_case(movement_case, movement=True, augmented=augmented, mu=mu)
        reference = solve(reference_case)
        movement = solve(movement_case) if reference["normal_termination"] else {
            "case": movement_case,
            "normal_termination": False,
            "not_run_reason": "matched reference did not terminate normally",
        }
        statuses.extend([reference, movement])
        if not (reference["normal_termination"] and movement["normal_termination"]):
            print(json.dumps({"variant": name, "reference": reference, "movement": movement}, default=str), flush=True)
            continue
        append_pair(
            name,
            augmented,
            mu,
            reference_case,
            movement_case,
            reference["summary"],
            movement["summary"],
        )
        print(json.dumps({"variant": name, "completed": True}, indent=2), flush=True)

    matched = {
        row["variant"]: row
        for row in rows
        if row["sensor"] in (3, 8)
    }
    output = {
        "strategy": (
            "two-stage continuation: torso fit to t=0.5, followed by 25% arm-raise motion; "
            "manual normal penalty, four segment updates, node-on-facet friction"
        ),
        "statuses": statuses,
        "rows": rows,
        "completed_variants": sorted({str(row["variant"]) for row in rows}),
        "matched_mu0p1_penalty_and_augmented_completed": (
            "penalty_mu0p1_archived" in matched and "augmented_mu0p1" in matched
        ),
        "interpretation_limit": (
            "normal termination is a numerical robustness observation, not validation of the "
            "contact law or friction coefficient"
        ),
    }
    json_path = ROOT / "results" / "augmented_contact_continuation.json"
    csv_path = ROOT / "results" / "augmented_contact_continuation.csv"
    json_path.write_text(json.dumps(output, indent=2) + "\n")
    if rows:
        with csv_path.open("w", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
    print(json.dumps({key: value for key, value in output.items() if key not in {"rows", "statuses"}}, indent=2))
    print(f"Wrote {json_path}")
    if rows:
        print(f"Wrote {csv_path}")


if __name__ == "__main__":
    main()
