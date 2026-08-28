#!/usr/bin/env python3
"""Run representative garment-derived strain tensors through full-field coupons."""

from __future__ import annotations

import csv
import json
import math
import subprocess
from pathlib import Path

from generate_coupon import ROOT, generate
from postprocess_coupon import process


FEBIO = Path("/Applications/FEBioStudio/FEBioStudio.app/Contents/MacOS/febio4")
REPRESENTATIVES = (
    ("left_arm_raise", 3),
    ("left_shoulder_touch_twist", 9),
    ("right_shoulder_touch_twist", 10),
    ("both_arms_raise", 3),
    ("forward_bend", 8),
    ("sitting", 5),
)
SELECTION_RATIONALE = {
    "left_arm_raise_s3": "unilateral upper-front response with combined axial and shear loading",
    "left_shoulder_touch_twist_s9": "negative-shear member of a mirrored back-sensor pair",
    "right_shoulder_touch_twist_s10": "positive-shear symmetry partner used for verification",
    "both_arms_raise_s3": "bilateral upper-front axial-dominant loading and contact-free comparator",
    "forward_bend_s8": "largest selected axial strain and back-panel coverage",
    "sitting_s5": "lowest selected axial strain with mixed lower-front loading",
}


def rotate_to_sensor(row: dict) -> tuple[float, float, float]:
    exx = float(row["exx"])
    eyy = float(row["eyy"])
    gamma = float(row["gamma_xy_engineering"])
    theta = math.radians(float(row["sensor_angle_deg"]))
    c, s = math.cos(theta), math.sin(theta)
    local_exx = exx * c * c + eyy * s * s + gamma * s * c
    local_eyy = exx * s * s + eyy * c * c - gamma * s * c
    local_gamma = 2.0 * (eyy - exx) * s * c + gamma * (c * c - s * s)
    return local_exx, local_eyy, local_gamma


def complete(name: str) -> bool:
    path = ROOT / "results" / f"{name}.log"
    return path.exists() and "N O R M A L   T E R M I N A T I O N" in path.read_text(errors="replace")


def main() -> None:
    source_rows = list(csv.DictReader((ROOT / "results" / "garment_kinematic_screen.csv").open()))
    rows = []
    for posture, sensor in REPRESENTATIVES:
        source = next(
            row for row in source_rows
            if row["posture"] == posture and int(row["sensor"]) == sensor
        )
        exx, eyy, gamma = rotate_to_sensor(source)
        name = f"garment_submodel_{posture}_s{sensor}_local_medium"
        if not complete(name):
            generate(
                case_name=name,
                mesh_level="local_medium",
                material_case="textile_fiber_balanced",
                taper_length_mm=5.0,
                tip_thickness_fraction=0.25,
                remote_exx=exx,
                remote_eyy=eyy,
                remote_gamma_xy=gamma,
            )
            completed = subprocess.run(
                [str(FEBIO), "-i", str(ROOT / "model" / f"{name}.feb")],
                cwd=ROOT,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.STDOUT,
                check=False,
            )
            if completed.returncode != 0 or not complete(name):
                raise RuntimeError(f"FEBio failed for {name}: {completed.returncode}")
        result = process(name)
        projected = float(source["projected_sensor_axis_strain"])
        rows.append(
            {
                "case_name": name,
                "posture": posture,
                "sensor": sensor,
                "panel": source["panel"],
                "local_exx": exx,
                "local_eyy": eyy,
                "local_gamma_xy_engineering": gamma,
                "kinematic_projected_sensor_axis_strain": projected,
                "fullfield_mean_gauge_strain": result["mean_conductive_gauge_strain"],
                "fullfield_endpoint_gauge_strain": result[
                    "conductive_gauge_endpoint_engineering_strain"
                ],
                "fullfield_path_gauge_strain": result[
                    "conductive_gauge_centroid_path_engineering_strain"
                ],
                "selection_rationale": SELECTION_RATIONALE[f"{posture}_s{sensor}"],
                "effective_transfer_ratio": (
                    result["mean_conductive_gauge_strain"] / projected
                    if abs(projected) > 1e-12 else None
                ),
                "element_count": result["element_count"],
            }
        )
        print(
            f"{posture}, S{sensor}: local={100 * projected:.4f}%, "
            f"gauge={100 * result['mean_conductive_gauge_strain']:.5f}%"
        )

    output = ROOT / "results"
    with (output / "garment_submodels.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    x_values = [row["kinematic_projected_sensor_axis_strain"] for row in rows]
    y_values = [row["fullfield_mean_gauge_strain"] for row in rows]
    slope = sum(x * y for x, y in zip(x_values, y_values)) / sum(x * x for x in x_values)
    x_mean = sum(x_values) / len(x_values)
    y_mean = sum(y_values) / len(y_values)
    correlation = sum(
        (x - x_mean) * (y - y_mean) for x, y in zip(x_values, y_values)
    ) / math.sqrt(
        sum((x - x_mean) ** 2 for x in x_values)
        * sum((y - y_mean) ** 2 for y in y_values)
    )
    unconstrained_slope = sum(
        (x - x_mean) * (y - y_mean) for x, y in zip(x_values, y_values)
    ) / sum((x - x_mean) ** 2 for x in x_values)
    unconstrained_intercept = y_mean - unconstrained_slope * x_mean
    unconstrained_predictions = [
        unconstrained_intercept + unconstrained_slope * x for x in x_values
    ]
    residuals = [y - predicted for y, predicted in zip(y_values, unconstrained_predictions)]
    residual_sum_squares = sum(value * value for value in residuals)
    total_sum_squares = sum((y - y_mean) ** 2 for y in y_values)
    left_twist = next(row for row in rows if row["posture"] == "left_shoulder_touch_twist")
    right_twist = next(row for row in rows if row["posture"] == "right_shoulder_touch_twist")
    mirrored_error = 100.0 * abs(
        left_twist["fullfield_mean_gauge_strain"] - right_twist["fullfield_mean_gauge_strain"]
    ) / abs(0.5 * (
        left_twist["fullfield_mean_gauge_strain"] + right_twist["fullfield_mean_gauge_strain"]
    ))
    (output / "garment_submodels.json").write_text(
        json.dumps(
            {
                "rows": rows,
                "status": "full-field local coupons driven by illustrative normalized garment kinematics",
                "material_status": "balanced two-fiber textile sensitivity model; not calibrated",
                "zero_intercept_slope": slope,
                "zero_intercept_rationale": "zero imposed local strain should produce zero mechanical gauge strain in this deterministic model",
                "unconstrained_intercept": unconstrained_intercept,
                "unconstrained_slope": unconstrained_slope,
                "unconstrained_r_squared": 1.0 - residual_sum_squares / total_sum_squares,
                "unconstrained_rmse": math.sqrt(residual_sum_squares / len(residuals)),
                "unconstrained_max_absolute_residual": max(abs(value) for value in residuals),
                "pearson_r": correlation,
                "deterministic_case_count": len(rows),
                "independent_loading_count_note": "six solved cases, including one mirrored twist pair used as a symmetry check",
                "effective_transfer_ratio_range": [
                    min(row["effective_transfer_ratio"] for row in rows),
                    max(row["effective_transfer_ratio"] for row in rows),
                ],
                "mirrored_twist_symmetry_error_percent": mirrored_error,
            },
            indent=2,
        ) + "\n"
    )


if __name__ == "__main__":
    main()
