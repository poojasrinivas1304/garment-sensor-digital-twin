#!/usr/bin/env python3
"""Screen balanced and 3:1 warp/weft finite-strain textile surrogates."""

from __future__ import annotations

import csv
import json
import subprocess
from pathlib import Path

from generate_coupon import MATERIAL_CASES, ROOT, generate
from postprocess_coupon import process


FEBIO = Path("/Applications/FEBioStudio/FEBioStudio.app/Contents/MacOS/febio4")
MATERIALS = (
    "textile_fiber_balanced",
    "textile_fiber_x3",
    "textile_fiber_y3",
)
ANGLES = (0.0, 60.0)


def case_name(material_case: str, angle: float, mesh: str) -> str:
    label = material_case.removeprefix("textile_fiber_")
    return f"anisotropy_{label}_angle_{angle:g}_{mesh}"


def complete(name: str) -> bool:
    log_path = ROOT / "results" / f"{name}.log"
    return log_path.exists() and "N O R M A L   T E R M I N A T I O N" in log_path.read_text(errors="replace")


def run_case(material_case: str, angle: float, mesh: str) -> dict:
    name = case_name(material_case, angle, mesh)
    if not complete(name):
        generate(
            case_name=name,
            mesh_level=mesh,
            material_case=material_case,
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
        if completed.returncode != 0 or not complete(name):
            raise RuntimeError(f"FEBio failed for {name}: {completed.returncode}")
    result = process(name)
    textile = MATERIAL_CASES[material_case]["nylon"]
    return {
        "case_name": name,
        "material_case": material_case,
        "loading_angle_deg": angle,
        "fiber_x_c5_MPa": textile["fiber_x_c5_MPa"],
        "fiber_y_c5_MPa": textile["fiber_y_c5_MPa"],
        "fiber_stiffness_ratio_x_over_y": (
            textile["fiber_x_c5_MPa"] / textile["fiber_y_c5_MPa"]
        ),
        "mean_conductive_gauge_strain": result["mean_conductive_gauge_strain"],
        "strain_transfer_vs_major_strain": result["strain_transfer_ratio"],
        "element_count": result["element_count"],
    }


def main() -> None:
    # A coarse dry run catches constitutive/XML errors before production cases.
    run_case("textile_fiber_balanced", 0.0, "local_coarse")
    rows = []
    for material_case in MATERIALS:
        for angle in ANGLES:
            row = run_case(material_case, angle, "local_medium")
            rows.append(row)
            print(
                f"{material_case}, {angle:+g} deg: "
                f"gauge strain={100 * row['mean_conductive_gauge_strain']:.6f}%"
            )

    balanced = {
        row["loading_angle_deg"]: row for row in rows
        if row["material_case"] == "textile_fiber_balanced"
    }
    for row in rows:
        reference = balanced[row["loading_angle_deg"]]["mean_conductive_gauge_strain"]
        row["change_vs_balanced_percent"] = 100.0 * (
            row["mean_conductive_gauge_strain"] - reference
        ) / abs(reference)

    output = ROOT / "results"
    with (output / "textile_anisotropy.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    (output / "textile_anisotropy.json").write_text(
        json.dumps(
            {
                "rows": rows,
                "status": "illustrative constitutive sensitivity, not calibrated textile properties",
                "model": "uncoupled hyperelastic matrix plus orthogonal tension-only exponential-linear fibers",
            },
            indent=2,
        ) + "\n"
    )


if __name__ == "__main__":
    main()
