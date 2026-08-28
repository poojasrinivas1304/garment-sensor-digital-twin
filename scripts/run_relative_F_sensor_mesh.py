#!/usr/bin/env python3
"""Drive principal sensor submodels with matched relative deformation gradients."""

from __future__ import annotations

import csv
import json
import subprocess
from pathlib import Path

import numpy as np

from generate_coupon import ROOT, generate
from postprocess_coupon import process


FEBIO = Path("/Applications/FEBioStudio/FEBioStudio.app/Contents/MacOS/febio4")
MESHES = ("local_coarse", "local_medium", "local_fine")
SENSORS = (3, 9)
PAIRS = {
    "full_garment_no_contact": (
        "matched_no_contact_0p6_reference",
        "matched_no_contact_0p6_movement025",
    ),
    "full_garment_contact": (
        "garment_fit_torso_expand_060mm_manual",
        "garment_both_arms_raise_025",
    ),
}


def complete(case: str) -> bool:
    log = ROOT / "results" / f"{case}.log"
    return log.exists() and "N O R M A L   T E R M I N A T I O N" in log.read_text(
        errors="replace"
    )


def summary(case: str) -> dict:
    return json.loads(
        (ROOT / "results" / f"{case}_movement_summary.json").read_text()
    )


def sensor_rows(case: str) -> dict[int, dict]:
    return {int(row["sensor"]): row for row in summary(case)["sensor_strains"]}


def relative_gradient(reference_case: str, movement_case: str, sensor: int) -> np.ndarray:
    reference = sensor_rows(reference_case)[sensor]
    movement = sensor_rows(movement_case)[sensor]
    f_fit = np.asarray(reference["deformation_gradient_sensor_basis"], dtype=float)
    f_move = np.asarray(movement["deformation_gradient_sensor_basis"], dtype=float)
    return f_move @ np.linalg.inv(f_fit)


def run_case(case: str, mesh: str, deformation_gradient: np.ndarray) -> dict:
    if not complete(case):
        generate(
            case_name=case,
            mesh_level=mesh,
            material_case="textile_fiber_balanced",
            taper_length_mm=5.0,
            tip_thickness_fraction=0.25,
            remote_deformation_gradient=deformation_gradient.tolist(),
            time_steps=10,
            maximum_time_step=0.1,
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
    values = process(case)
    text = (ROOT / "results" / f"{case}.log").read_text(errors="replace")
    values["negative_jacobian_messages"] = text.count("negative jacobians detected")
    return values


def main() -> None:
    rows = []
    for model, (reference_case, movement_case) in PAIRS.items():
        for sensor in SENSORS:
            f_rel = relative_gradient(reference_case, movement_case, sensor)
            e_rel = 0.5 * (f_rel.T @ f_rel - np.eye(3))
            for mesh in MESHES:
                # The versioned prefix prevents legacy 60-mm exploratory cases from
                # being mistaken for the corrected 0.6-mm fitted-state transfer.
                case = f"relativeF0p6_{model}_s{sensor}_{mesh}"
                print(f"Running {case}", flush=True)
                result = run_case(case, mesh, f_rel)
                rows.append(
                    {
                        "case_name": case,
                        "garment_model": model,
                        "sensor": sensor,
                        "mesh": mesh,
                        "input_relative_F_sensor_axis_green_percent": 100.0
                        * float(e_rel[0, 0]),
                        "input_relative_F_transverse_green_percent": 100.0
                        * float(e_rel[1, 1]),
                        "input_relative_F_shear_green_percent": 100.0
                        * float(e_rel[0, 1]),
                        "input_det_F": float(np.linalg.det(f_rel)),
                        "endpoint_gauge_percent": 100.0
                        * float(result["mean_conductive_gauge_strain"]),
                        "path_gauge_percent": 100.0
                        * float(
                            result[
                                "conductive_gauge_centroid_path_engineering_strain"
                            ]
                        ),
                        "element_count": int(result["element_count"]),
                        "node_count": int(result["node_count"]),
                        "normal_termination": complete(case),
                        "negative_jacobian_messages": int(
                            result["negative_jacobian_messages"]
                        ),
                    }
                )

    by_key = {
        (row["garment_model"], row["sensor"], row["mesh"]): row for row in rows
    }
    convergence = []
    for model in PAIRS:
        for sensor in SENSORS:
            coarse = by_key[(model, sensor, "local_coarse")]
            medium = by_key[(model, sensor, "local_medium")]
            fine = by_key[(model, sensor, "local_fine")]
            convergence.append(
                {
                    "garment_model": model,
                    "sensor": sensor,
                    "endpoint_sign_stable": len(
                        {
                            np.sign(coarse["endpoint_gauge_percent"]),
                            np.sign(medium["endpoint_gauge_percent"]),
                            np.sign(fine["endpoint_gauge_percent"]),
                        }
                    )
                    == 1,
                    "path_sign_stable": len(
                        {
                            np.sign(coarse["path_gauge_percent"]),
                            np.sign(medium["path_gauge_percent"]),
                            np.sign(fine["path_gauge_percent"]),
                        }
                    )
                    == 1,
                    "medium_to_fine_endpoint_relative_percent": 100.0
                    * abs(
                        fine["endpoint_gauge_percent"]
                        - medium["endpoint_gauge_percent"]
                    )
                    / max(abs(fine["endpoint_gauge_percent"]), 1e-15),
                    "medium_to_fine_path_relative_percent": 100.0
                    * abs(
                        fine["path_gauge_percent"] - medium["path_gauge_percent"]
                    )
                    / max(abs(fine["path_gauge_percent"]), 1e-15),
                }
            )

    csv_path = ROOT / "results" / "relative_F_sensor_mesh.csv"
    with csv_path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    json_path = ROOT / "results" / "relative_F_sensor_mesh.json"
    json_path.write_text(
        json.dumps(
            {
                "status": (
                    "matched fitted-to-movement relative-deformation-gradient transfer; "
                    "shell director completed with unit normal stretch"
                ),
                "rows": rows,
                "convergence": convergence,
            },
            indent=2,
        )
        + "\n"
    )
    print(f"Wrote {csv_path}")
    print(f"Wrote {json_path}")


if __name__ == "__main__":
    main()
