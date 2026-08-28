#!/usr/bin/env python3
"""Drive resolved sensor coupons with contact-aware arm-raise strain tensors."""

from __future__ import annotations

import csv
import json
import math
import subprocess
from pathlib import Path

import numpy as np

from generate_coupon import ROOT, generate
from postprocess_coupon import process


FEBIO = Path("/Applications/FEBioStudio/FEBioStudio.app/Contents/MacOS/febio4")
SENSORS = (3, 8, 9, 10)
BASELINE = ROOT / "results" / "garment_fit_torso_expand_060mm_manual_movement_summary.json"
MOVEMENT = ROOT / "results" / "garment_both_arms_raise_100_movement_summary.json"
CONTACT_FREE = ROOT / "results" / "garment_kinematic_screen.csv"


def rotate_tensor(
    exx: float, eyy: float, exy: float, angle_deg: float
) -> tuple[float, float, float]:
    """Rotate a symmetric 2-D tensor into the sensor-aligned basis."""
    theta = math.radians(angle_deg)
    c, s = math.cos(theta), math.sin(theta)
    local_xx = exx * c * c + eyy * s * s + 2.0 * exy * s * c
    local_yy = exx * s * s + eyy * c * c - 2.0 * exy * s * c
    local_xy = (eyy - exx) * s * c + exy * (c * c - s * s)
    return local_xx, local_yy, local_xy


def pure_stretch_from_green(
    exx: float, eyy: float, exy: float
) -> tuple[float, float, float, np.ndarray]:
    """Return a symmetric displacement gradient whose Green tensor is E."""
    green = np.asarray([[exx, exy], [exy, eyy]], dtype=float)
    right_cauchy_green = np.eye(2) + 2.0 * green
    eigenvalues, eigenvectors = np.linalg.eigh(right_cauchy_green)
    if float(eigenvalues.min()) <= 0.0:
        raise ValueError(f"non-positive right Cauchy--Green eigenvalue: {eigenvalues}")
    stretch = eigenvectors @ np.diag(np.sqrt(eigenvalues)) @ eigenvectors.T
    displacement_gradient = stretch - np.eye(2)
    return (
        float(displacement_gradient[0, 0]),
        float(displacement_gradient[1, 1]),
        float(displacement_gradient[0, 1]),
        stretch,
    )


def complete(case_name: str) -> bool:
    log = ROOT / "results" / f"{case_name}.log"
    return log.exists() and "N O R M A L   T E R M I N A T I O N" in log.read_text(
        errors="replace"
    )


def run_case(
    case_name: str,
    remote_xx: float,
    remote_yy: float,
    remote_xy: float,
    time_steps: int = 30,
    maximum_time_step: float = 0.05,
) -> dict:
    if not complete(case_name):
        generate(
            case_name=case_name,
            mesh_level="local_medium",
            material_case="textile_fiber_balanced",
            taper_length_mm=5.0,
            tip_thickness_fraction=0.25,
            remote_exx=remote_xx,
            remote_eyy=remote_yy,
            remote_gamma_xy=2.0 * remote_xy,
            time_steps=time_steps,
            maximum_time_step=maximum_time_step,
        )
        completed = subprocess.run(
            [str(FEBIO), "-i", str(ROOT / "model" / f"{case_name}.feb")],
            cwd=ROOT,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.STDOUT,
            check=False,
        )
        if completed.returncode != 0 or not complete(case_name):
            raise RuntimeError(f"FEBio failed for {case_name}: {completed.returncode}")
    result = process(case_name)
    log_text = (ROOT / "results" / f"{case_name}.log").read_text(errors="replace")
    result["negative_jacobian_messages"] = log_text.count("negative jacobians detected")
    return result


def movement_rows() -> dict[int, dict]:
    baseline = json.loads(BASELINE.read_text())
    movement = json.loads(MOVEMENT.read_text())
    baseline_by_sensor = {int(row["sensor"]): row for row in baseline["sensor_strains"]}
    movement_by_sensor = {int(row["sensor"]): row for row in movement["sensor_strains"]}
    rows: dict[int, dict] = {}
    for sensor in SENSORS:
        base = baseline_by_sensor[sensor]
        full = movement_by_sensor[sensor]
        delta_tt = float(full["green_strain_circumferential"]) - float(
            base["green_strain_circumferential"]
        )
        delta_zz = float(full["green_strain_vertical"]) - float(
            base["green_strain_vertical"]
        )
        delta_tz = float(full["green_shear_tensor_component"]) - float(
            base["green_shear_tensor_component"]
        )
        local_xx, local_yy, local_xy = rotate_tensor(
            delta_tt, delta_zz, delta_tz, float(full["sensor_angle_deg"])
        )
        rows[sensor] = {
            "panel": full["panel"],
            "sensor_angle_deg": float(full["sensor_angle_deg"]),
            "global_tensor": [delta_tt, delta_zz, delta_tz],
            "local_tensor": [local_xx, local_yy, local_xy],
        }
    return rows


def contact_free_rows() -> dict[int, dict]:
    with CONTACT_FREE.open() as handle:
        source = [
            row
            for row in csv.DictReader(handle)
            if row["posture"] == "both_arms_raise" and int(row["sensor"]) in SENSORS
        ]
    rows: dict[int, dict] = {}
    for row in source:
        sensor = int(row["sensor"])
        global_xx = float(row["exx"])
        global_yy = float(row["eyy"])
        global_xy = 0.5 * float(row["gamma_xy_engineering"])
        local_xx, local_yy, local_xy = rotate_tensor(
            global_xx, global_yy, global_xy, float(row["sensor_angle_deg"])
        )
        rows[sensor] = {
            "panel": row["panel"],
            "sensor_angle_deg": float(row["sensor_angle_deg"]),
            "global_tensor": [global_xx, global_yy, global_xy],
            "local_tensor": [local_xx, local_yy, local_xy],
        }
    return rows


def main() -> None:
    contact_aware = movement_rows()
    contact_free = contact_free_rows()
    output_rows = []

    for model_name, tensor_rows in (
        ("contact_free", contact_free),
        ("contact_aware", contact_aware),
    ):
        for sensor in SENSORS:
            source = tensor_rows[sensor]
            target_xx, target_yy, target_xy = source["local_tensor"]
            # Interpret both input tensor families as Green strain and construct
            # the same rotation-free finite deformation.  The contact-free field
            # originated from infinitesimal kinematics, so this is a controlled
            # finite-strain embedding rather than a recovered deformation history.
            remote_xx, remote_yy, remote_xy, stretch = pure_stretch_from_green(
                target_xx, target_yy, target_xy
            )
            realized_green = 0.5 * (stretch.T @ stretch - np.eye(2))

            refined_compression = model_name == "contact_aware" and sensor in (3, 8)
            suffix = "_refinedstep" if refined_compression else ""
            if model_name == "contact_free":
                suffix = "_finitegreen"
            case_name = (
                f"arm_raise_sensor_{model_name}_s{sensor}_local_medium{suffix}"
            )
            result = run_case(
                case_name,
                remote_xx,
                remote_yy,
                remote_xy,
                time_steps=60 if refined_compression else 30,
                maximum_time_step=0.02 if refined_compression else 0.05,
            )
            gauge = float(result["mean_conductive_gauge_strain"])
            path_gauge = float(
                result["conductive_gauge_centroid_path_engineering_strain"]
            )
            output_rows.append(
                {
                    "case_name": case_name,
                    "model": model_name,
                    "sensor": sensor,
                    "panel": source["panel"],
                    "sensor_angle_deg": source["sensor_angle_deg"],
                    "target_local_xx": target_xx,
                    "target_local_yy": target_yy,
                    "target_local_xy_tensor": target_xy,
                    "applied_displacement_gradient_xx": remote_xx,
                    "applied_displacement_gradient_yy": remote_yy,
                    "applied_displacement_gradient_xy": remote_xy,
                    "realized_farfield_green_xx": float(realized_green[0, 0]),
                    "realized_farfield_green_yy": float(realized_green[1, 1]),
                    "realized_farfield_green_xy_tensor": float(realized_green[0, 1]),
                    "mean_conductive_gauge_strain": gauge,
                    "conductive_gauge_endpoint_engineering_strain": gauge,
                    "conductive_gauge_centroid_path_engineering_strain": path_gauge,
                    "effective_axial_transfer_ratio": (
                        gauge / target_xx if abs(target_xx) > 1e-12 else None
                    ),
                    "path_effective_axial_transfer_ratio": (
                        path_gauge / target_xx if abs(target_xx) > 1e-12 else None
                    ),
                    "predicted_delta_R_over_R0_provisional": float(
                        result["predicted_delta_R_over_R0"]
                    ),
                    "element_count": int(result["element_count"]),
                    "febio_normal_termination": complete(case_name),
                    "negative_jacobian_messages": int(
                        result["negative_jacobian_messages"]
                    ),
                }
            )
            print(
                f"{model_name}, S{sensor}: input={100 * target_xx:+.4f}%, "
                f"gauge={100 * gauge:+.5f}%"
            )

    results_dir = ROOT / "results"
    csv_path = results_dir / "contact_aware_sensor_submodels.csv"
    with csv_path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(output_rows[0]))
        writer.writeheader()
        writer.writerows(output_rows)

    by_model_sensor = {
        (row["model"], int(row["sensor"])): row for row in output_rows
    }
    endpoint_sign_reversals = [
        sensor
        for sensor in SENSORS
        if math.copysign(1.0, by_model_sensor[("contact_free", sensor)]["mean_conductive_gauge_strain"])
        != math.copysign(1.0, by_model_sensor[("contact_aware", sensor)]["mean_conductive_gauge_strain"])
    ]
    path_sign_reversals = [
        sensor
        for sensor in SENSORS
        if math.copysign(
            1.0,
            by_model_sensor[("contact_free", sensor)][
                "conductive_gauge_centroid_path_engineering_strain"
            ],
        )
        != math.copysign(
            1.0,
            by_model_sensor[("contact_aware", sensor)][
                "conductive_gauge_centroid_path_engineering_strain"
            ],
        )
    ]
    symmetry = {}
    for left, right in ((3, 8), (9, 10)):
        for model_name in ("contact_free", "contact_aware"):
            a = by_model_sensor[(model_name, left)]["mean_conductive_gauge_strain"]
            b = by_model_sensor[(model_name, right)]["mean_conductive_gauge_strain"]
            denominator = max(abs(0.5 * (a + b)), 1e-15)
            symmetry[f"{model_name}_s{left}_s{right}_relative_error_percent"] = (
                100.0 * abs(a - b) / denominator
            )

    summary = {
        "status": "resolved mechanical sensor coupons driven by illustrative arm-raise fields; material and electrical laws are not calibrated",
        "rows": output_rows,
        "resolved_endpoint_gauge_sign_reversal_sensors": endpoint_sign_reversals,
        "resolved_endpoint_gauge_sign_reversal_count": len(endpoint_sign_reversals),
        "resolved_path_gauge_sign_reversal_sensors": path_sign_reversals,
        "resolved_path_gauge_sign_reversal_count": len(path_sign_reversals),
        "resolved_gauge_sign_reversal_sensors": endpoint_sign_reversals,
        "resolved_gauge_sign_reversal_count": len(endpoint_sign_reversals),
        "symmetry_checks": symmetry,
        "warnings": [
            "Contact-aware inputs are differences of fitted and full-amplitude surface Green tensors; relative deformation gradients were unavailable.",
            "Both input tensor families use the same pure-stretch finite-strain embedding; contact-free tensors originated from an infinitesimal displacement field.",
            "The beta=4 resistance law is illustrative and must not be interpreted as a calibrated electrical prediction.",
        ],
    }
    json_path = results_dir / "contact_aware_sensor_submodels.json"
    json_path.write_text(json.dumps(summary, indent=2) + "\n")
    print(f"Wrote {csv_path}")
    print(f"Wrote {json_path}")


if __name__ == "__main__":
    main()
