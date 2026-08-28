#!/usr/bin/env python3
"""Run matched no-contact and garment-shell mesh controls at 25% movement."""

from __future__ import annotations

import csv
import json
import math
import subprocess
import sys
from pathlib import Path

import numpy as np

from generate_garment_contact import build_model


ROOT = Path(__file__).resolve().parents[1]
FEBIO = Path("/Applications/FEBioStudio/FEBioStudio.app/Contents/MacOS/febio4")


def complete(case: str) -> bool:
    path = ROOT / "results" / f"{case}.log"
    return path.exists() and "N O R M A L   T E R M I N A T I O N" in path.read_text(
        errors="replace"
    )


def write_model(case: str, *, movement: bool, contact: bool, n_theta: int, n_z: int) -> None:
    time_steps = 40 if movement else 20
    tree, metadata = build_model(
        case=case,
        time_steps=time_steps,
        augmented_contact=False,
        contact_tolerance=0.1,
        contact_maxaug=5,
        penalty_scale=0.001,
        torso_expansion_mm=0.6,
        initial_clearance_mm=0.5,
        garment_E_MPa=0.8,
        auto_penalty=False,
        movement="both_arms_raise" if movement else None,
        movement_stage_fraction=0.5,
        movement_scale=0.25,
        contact_enabled=contact,
        n_theta=n_theta,
        n_z=n_z,
    )
    model_path = ROOT / "model" / f"{case}.feb"
    metadata_path = ROOT / "model" / f"{case}_metadata.json"
    tree.write(model_path, encoding="utf-8", xml_declaration=True)
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n")


def run_and_process(case: str, *, movement: bool, contact: bool, n_theta: int, n_z: int) -> None:
    if not complete(case):
        write_model(
            case, movement=movement, contact=contact, n_theta=n_theta, n_z=n_z
        )
        result = subprocess.run(
            [str(FEBIO), "-i", str(ROOT / "model" / f"{case}.feb")],
            cwd=ROOT,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.STDOUT,
            check=False,
        )
        if result.returncode != 0 or not complete(case):
            raise RuntimeError(f"FEBio failed for {case} (return code {result.returncode})")
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "postprocess_garment_movement.py"),
            "--case",
            case,
            "--no-figure",
        ],
        cwd=ROOT,
        check=True,
        stdout=subprocess.DEVNULL,
    )


def load_summary(case: str) -> dict:
    return json.loads(
        (ROOT / "results" / f"{case}_movement_summary.json").read_text()
    )


def rows_by_sensor(summary: dict) -> dict[int, dict]:
    return {int(row["sensor"]): row for row in summary["sensor_strains"]}


def relative_rows(reference: dict, movement: dict) -> list[dict]:
    reference_rows = rows_by_sensor(reference)
    movement_rows = rows_by_sensor(movement)
    output = []
    for sensor in range(1, 11):
        base = reference_rows[sensor]
        moved = movement_rows[sensor]
        f_fit = np.asarray(base["deformation_gradient_sensor_basis"], dtype=float)
        f_move = np.asarray(moved["deformation_gradient_sensor_basis"], dtype=float)
        f_rel = f_move @ np.linalg.inv(f_fit)
        e_rel = 0.5 * (f_rel.T @ f_rel - np.eye(3))
        subtraction = (
            float(moved["projected_sensor_axis_green_strain"])
            - float(base["projected_sensor_axis_green_strain"])
        )
        output.append(
            {
                "sensor": sensor,
                "panel": moved["panel"],
                "sensor_angle_deg": float(moved["sensor_angle_deg"]),
                "green_subtraction_sensor_axis": subtraction,
                "relative_F_sensor_axis_green": float(e_rel[0, 0]),
                "relative_F_sensor_transverse_green": float(e_rel[1, 1]),
                "relative_F_sensor_shear_green": float(e_rel[0, 1]),
                "relative_deformation_gradient_sensor_basis": f_rel.tolist(),
                "det_relative_deformation_gradient": float(np.linalg.det(f_rel)),
                "movement_local_gap_mm": moved["local_contact_gap_mm"],
                "movement_local_pressure_kPa": moved["local_contact_pressure_kPa"],
                "movement_local_contact_active": moved["local_contact_active"],
            }
        )
    return output


def analytical_rows() -> dict[int, float]:
    with (ROOT / "results" / "garment_kinematic_screen.csv").open() as handle:
        return {
            int(row["sensor"]): 0.25 * float(row["projected_sensor_axis_strain"])
            for row in csv.DictReader(handle)
            if row["posture"] == "both_arms_raise"
        }


def case_record(
    label: str, reference_case: str, movement_case: str, *, contact: bool
) -> dict:
    reference = load_summary(reference_case)
    movement = load_summary(movement_case)
    rows = relative_rows(reference, movement)
    return {
        "label": label,
        "reference_case": reference_case,
        "movement_case": movement_case,
        "contact_enabled": contact,
        "mesh": json.loads(
            (ROOT / "model" / f"{movement_case}_metadata.json").read_text()
        )["mesh"],
        "normal_termination": bool(
            reference["febio_normal_termination"]
            and movement["febio_normal_termination"]
        ),
        "movement_contact_coverage": movement["contact"]["active_facet_fraction"],
        "movement_minimum_signed_area_ratio": movement["mesh_quality"][
            "minimum_signed_triangle_area_ratio"
        ],
        "rows": rows,
    }


def main() -> None:
    # Reprocess the existing matched nominal contact pair with deformation-gradient output.
    existing = (
        ("garment_fit_torso_expand_060mm_manual", False),
        ("garment_both_arms_raise_025", True),
    )
    for case, movement in existing:
        run_and_process(
            case, movement=movement, contact=True, n_theta=64, n_z=26
        )

    requested = [
        ("matched_no_contact_0p6_reference", False, False, 64, 26),
        ("matched_no_contact_0p6_movement025", True, False, 64, 26),
        ("matched_no_contact_0p6_coarse56_reference", False, False, 56, 23),
        ("matched_no_contact_0p6_coarse56_movement025", True, False, 56, 23),
        ("matched_no_contact_0p6_fine72_reference", False, False, 72, 30),
        ("matched_no_contact_0p6_fine72_movement025", True, False, 72, 30),
        ("garment_mesh_0p6_coarse56_reference", False, True, 56, 23),
        ("garment_mesh_0p6_coarse56_movement025", True, True, 56, 23),
        ("garment_mesh_0p6_fine72_reference", False, True, 72, 30),
        ("garment_mesh_0p6_fine72_movement025", True, True, 72, 30),
    ]
    for case, movement, contact, n_theta, n_z in requested:
        print(f"Running {case}", flush=True)
        run_and_process(
            case,
            movement=movement,
            contact=contact,
            n_theta=n_theta,
            n_z=n_z,
        )

    records = [
        case_record(
            "full garment without contact, coarse mesh",
            "matched_no_contact_0p6_coarse56_reference",
            "matched_no_contact_0p6_coarse56_movement025",
            contact=False,
        ),
        case_record(
            "full garment without contact, current mesh",
            "matched_no_contact_0p6_reference",
            "matched_no_contact_0p6_movement025",
            contact=False,
        ),
        case_record(
            "full garment without contact, fine mesh",
            "matched_no_contact_0p6_fine72_reference",
            "matched_no_contact_0p6_fine72_movement025",
            contact=False,
        ),
        case_record(
            "full garment with contact, coarse mesh",
            "garment_mesh_0p6_coarse56_reference",
            "garment_mesh_0p6_coarse56_movement025",
            contact=True,
        ),
        case_record(
            "full garment with contact, current mesh",
            "garment_fit_torso_expand_060mm_manual",
            "garment_both_arms_raise_025",
            contact=True,
        ),
        case_record(
            "full garment with contact, fine mesh",
            "garment_mesh_0p6_fine72_reference",
            "garment_mesh_0p6_fine72_movement025",
            contact=True,
        ),
    ]
    reduced = analytical_rows()
    for record in records:
        for row in record["rows"]:
            row["reduced_analytical_sensor_axis_green"] = reduced[row["sensor"]]
            row["sign_vs_reduced_relative_F"] = (
                math.copysign(1.0, row["relative_F_sensor_axis_green"])
                != math.copysign(1.0, reduced[row["sensor"]])
            )

    output = {
        "status": "matched 25% full-garment controls and three-level shell-mesh audit",
        "comparison_rule": (
            "all full-garment pairs use identical reference shell, material, seams, "
            "constraints and upper-ring field; only the contact-enabled flag changes "
            "in the matched current-mesh control"
        ),
        "reduced_analytical_scale": 0.25,
        "records": records,
    }
    json_path = ROOT / "results" / "matched_garment_controls.json"
    json_path.write_text(json.dumps(output, indent=2) + "\n")

    csv_rows = []
    for record in records:
        for row in record["rows"]:
            csv_rows.append(
                {
                    "case": record["label"],
                    "n_theta": record["mesh"]["circumferential_divisions"],
                    "n_z": record["mesh"]["vertical_divisions"],
                    "shirt_elements": record["mesh"]["shirt_shell_elements"],
                    "contact_coverage": record["movement_contact_coverage"],
                    "minimum_signed_area_ratio": record[
                        "movement_minimum_signed_area_ratio"
                    ],
                    **{k: v for k, v in row.items() if not isinstance(v, list)},
                }
            )
    csv_path = ROOT / "results" / "matched_garment_controls.csv"
    with csv_path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(csv_rows[0]))
        writer.writeheader()
        writer.writerows(csv_rows)
    print(f"Wrote {json_path}")
    print(f"Wrote {csv_path}")


if __name__ == "__main__":
    main()
