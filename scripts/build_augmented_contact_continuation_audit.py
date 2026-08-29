#!/usr/bin/env python3
"""Assemble accepted and interrupted contact-continuation evidence."""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PAIRS = (
    (
        "augmented_mu0_frictionless",
        True,
        0.0,
        "contact_sensitivity_baseline_reference",
        "contact_sensitivity_baseline_movement025",
    ),
    (
        "penalty_mu0p1_archived",
        False,
        0.1,
        "garment_friction_n2f_mu0p1_reference",
        "garment_friction_n2f_mu0p1_kt0p1_025",
    ),
)


def summary(case: str) -> dict:
    return json.loads((ROOT / "results" / f"{case}_movement_summary.json").read_text())


def main() -> None:
    with (ROOT / "results" / "garment_kinematic_screen.csv").open() as stream:
        free = {
            int(row["sensor"]): 0.25 * float(row["projected_sensor_axis_strain"])
            for row in csv.DictReader(stream)
            if row["posture"] == "both_arms_raise"
        }
    rows: list[dict[str, object]] = []
    statuses: list[dict[str, object]] = []
    for name, augmented, mu, reference_case, movement_case in PAIRS:
        reference = summary(reference_case)
        movement = summary(movement_case)
        rmap = {item["sensor"]: item for item in reference["sensor_strains"]}
        mmap = {item["sensor"]: item for item in movement["sensor_strains"]}
        statuses.append(
            {
                "variant": name,
                "reference_case": reference_case,
                "movement_case": movement_case,
                "normal_termination": True,
                "accepted_as_result": True,
            }
        )
        for sensor in range(1, 11):
            delta = (
                mmap[sensor]["projected_sensor_axis_green_strain"]
                - rmap[sensor]["projected_sensor_axis_green_strain"]
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
                    "active_contact_fraction": movement["contact"]["active_facet_fraction"],
                    "reference_case": reference_case,
                    "movement_case": movement_case,
                }
            )

    interrupted_case = "continuation_augmented_mu0p1_reference"
    log_path = ROOT / "results" / f"{interrupted_case}.log"
    log_text = log_path.read_text(errors="replace")
    step_starts = [
        (int(step), float(value))
        for step, value in re.findall(
            r"beginning time step (\d+)\s*:\s*([0-9.eE+-]+)", log_text
        )
    ]
    stalled_step = max((step for step, _ in step_starts), default=0)
    accepted_times = [value for step, value in step_starts if step < stalled_step]
    attempted_times = [float(value) for value in re.findall(r"Nonlinear solution status: time=\s*([0-9.eE+-]+)", log_text)]
    statuses.append(
        {
            "variant": "augmented_mu0p1_interrupted",
            "case": interrupted_case,
            "normal_termination": False,
            "accepted_as_result": False,
            "audit_action": (
                "interrupted after the third repeated automatic step retry at the same "
                "fit-stage stagnation boundary"
            ),
            "last_accepted_time": max(accepted_times) if accepted_times else None,
            "maximum_attempted_time": max(attempted_times) if attempted_times else None,
            "automatic_step_retries_observed": log_text.count("AUTO STEPPER: retry"),
            "negative_jacobian_trial_messages": log_text.count("negative jacobians detected"),
            "interpretation": "numerical trial only; no movement or physical response inferred",
        }
    )

    output = {
        "strategy": (
            "fitted reference followed by a separate matched 25% movement solve; movement "
            "load curve holds arm motion at zero until normalized time 0.5"
        ),
        "statuses": statuses,
        "rows": rows,
        "finding": (
            "augmented Lagrangian completed for the frictionless facet-on-facet pair; "
            "the new augmented node-on-facet mu=0.1 fitted reference stagnated and was "
            "interrupted after three repeated step cuts"
        ),
        "high_friction_mu0p3_not_attempted_reason": (
            "the lower nonzero-friction augmented reference did not produce an accepted fitted state"
        ),
        "interpretation_limit": (
            "normal termination is numerical evidence only; it does not validate friction, "
            "contact pressure or garment-body mechanics"
        ),
    }
    json_path = ROOT / "results" / "augmented_contact_continuation.json"
    csv_path = ROOT / "results" / "augmented_contact_continuation.csv"
    json_path.write_text(json.dumps(output, indent=2) + "\n")
    with csv_path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(json.dumps({key: value for key, value in output.items() if key != "rows"}, indent=2))
    print(f"Wrote {json_path}")
    print(f"Wrote {csv_path}")


if __name__ == "__main__":
    main()
