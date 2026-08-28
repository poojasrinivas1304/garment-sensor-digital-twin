#!/usr/bin/env python3
"""Build a formulation-matched friction comparison from completed N2F cases."""

from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PAIRS = (
    (0.0, "garment_friction_n2f_mu0_reference", "garment_friction_n2f_mu0_025"),
    (0.1, "garment_friction_n2f_mu0p1_reference", "garment_friction_n2f_mu0p1_kt0p1_025"),
)
FAILED_HIGH_FRICTION_CASES = (
    "garment_friction_n2f_mu0p3_kt0p1_025",
    "garment_friction_n2f_mu0p3_fp0p1_kt0p01_025",
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
    for coefficient, reference_case, movement_case in PAIRS:
        reference = summary(reference_case)
        movement = summary(movement_case)
        rmap = {x["sensor"]: x for x in reference["sensor_strains"]}
        mmap = {x["sensor"]: x for x in movement["sensor_strains"]}
        for sensor in range(1, 11):
            delta = (
                mmap[sensor]["projected_sensor_axis_green_strain"]
                - rmap[sensor]["projected_sensor_axis_green_strain"]
            )
            rows.append(
                {
                    "friction_coefficient": coefficient,
                    "sensor": sensor,
                    "movement_induced_strain_percent": 100.0 * delta,
                    "contact_free_scaled_strain_percent": 100.0 * free[sensor],
                    "sign_reversal_vs_contact_free": delta * free[sensor] < 0.0,
                    "active_contact_fraction": movement["contact"]["active_facet_fraction"],
                    "reference_case": reference_case,
                    "movement_case": movement_case,
                }
            )
    output = {
        "comparison": "formulation-matched sliding-node-on-facet, manual normal penalty 0.001, penalty-only enforcement, four segment updates, 25% movement",
        "rows": rows,
        "s3_s8_reversal_persisted_at_mu_0_and_0p1": all(
            bool(row["sign_reversal_vs_contact_free"])
            for row in rows if row["sensor"] in (3, 8)
        ),
        "failed_high_friction_trials_not_used_as_results": [
            {
                "case": case,
                "normal_termination": "N O R M A L   T E R M I N A T I O N" in (
                    ROOT / "results" / f"{case}.log"
                ).read_text(errors="replace"),
            }
            for case in FAILED_HIGH_FRICTION_CASES
        ],
    }
    json_path = ROOT / "results" / "friction_sensitivity.json"
    csv_path = ROOT / "results" / "friction_sensitivity.csv"
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
