#!/usr/bin/env python3
"""Run selected affine full-field loading directions on the tapered coupon."""

from __future__ import annotations

import csv
import json
import subprocess
from pathlib import Path

from generate_coupon import ROOT, generate
from postprocess_coupon import process


FEBIO = Path("/Applications/FEBioStudio/FEBioStudio.app/Contents/MacOS/febio4")
ANGLES = (0.0, 60.0, -60.0)


def case_name(angle: float) -> str:
    token = f"{abs(angle):g}".replace(".", "p")
    sign = "minus" if angle < 0 else "plus"
    return f"fullfield_angle_{sign}_{token}_local_medium"


def complete(name: str) -> bool:
    log_path = ROOT / "results" / f"{name}.log"
    return log_path.exists() and "N O R M A L   T E R M I N A T I O N" in log_path.read_text(errors="replace")


def main() -> None:
    rows = []
    for angle in ANGLES:
        name = case_name(angle)
        if not complete(name):
            generate(
                case_name=name,
                mesh_level="local_medium",
                material_case="literature_nominal",
                taper_length_mm=5.0,
                tip_thickness_fraction=0.25,
                loading_angle_deg=angle,
                remote_transverse_ratio=0.30,
            )
            completed = subprocess.run(
                [str(FEBIO), "-i", str(ROOT / "model" / f"{name}.feb")],
                cwd=ROOT,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.STDOUT,
                check=False,
            )
            if completed.returncode != 0:
                raise RuntimeError(f"FEBio failed for {name}: {completed.returncode}")
        summary = process(name)
        metadata = json.loads((ROOT / "model" / f"{name}_metadata.json").read_text())
        rows.append(
            {
                "case_name": name,
                "loading_angle_deg": angle,
                **metadata["remote_strain_tensor"],
                "mean_conductive_gauge_strain": summary["mean_conductive_gauge_strain"],
                "conductive_gauge_endpoint_engineering_strain": summary[
                    "conductive_gauge_endpoint_engineering_strain"
                ],
                "conductive_gauge_centroid_path_engineering_strain": summary[
                    "conductive_gauge_centroid_path_engineering_strain"
                ],
                "strain_transfer_vs_major_strain": summary["strain_transfer_ratio"],
                "element_count": summary["element_count"],
            }
        )
        print(f"{angle:+g} deg: gauge strain={100 * summary['mean_conductive_gauge_strain']:.6f}%")

    aligned_transfer = rows[0]["mean_conductive_gauge_strain"] / rows[0]["exx"]
    aligned_path_transfer = (
        rows[0]["conductive_gauge_centroid_path_engineering_strain"] / rows[0]["exx"]
    )
    for row in rows:
        prediction = aligned_transfer * row["exx"]
        row["aligned_scalar_transfer"] = aligned_transfer
        row["aligned_path_scalar_transfer"] = aligned_path_transfer
        row["reduced_order_predicted_gauge_strain"] = prediction
        row["reduced_order_predicted_path_strain"] = aligned_path_transfer * row["exx"]
        row["fullfield_minus_reduced_gauge_strain"] = (
            row["mean_conductive_gauge_strain"] - prediction
        )

    results = ROOT / "results"
    with (results / "fullfield_orientation.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    plus = next(row for row in rows if row["loading_angle_deg"] == 60.0)
    minus = next(row for row in rows if row["loading_angle_deg"] == -60.0)
    summary_output = {
        "rows": rows,
        "plus_minus_60_symmetry_error_percent": 100.0 * abs(
            plus["mean_conductive_gauge_strain"] - minus["mean_conductive_gauge_strain"]
        ) / abs(0.5 * (plus["mean_conductive_gauge_strain"] + minus["mean_conductive_gauge_strain"])),
        "interpretation": "selected full-field check of the reduced-order orientation screen; material remains isotropic",
        "gauge_definition_audit": "endpoint-centroid and centroid-path engineering strains are reported; a sign claim is robust only if both agree",
    }
    (results / "fullfield_orientation.json").write_text(
        json.dumps(summary_output, indent=2) + "\n"
    )


if __name__ == "__main__":
    main()
