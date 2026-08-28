#!/usr/bin/env python3
"""Export model-source parameters and a case manifest for peer review."""

from __future__ import annotations

import csv
import importlib.metadata
import json
import math
import platform
import re
import sys
from pathlib import Path

from generate_coupon import MATERIAL_CASES, ROOT


RESULTS = ROOT / "results"
MODEL = ROOT / "model"

# These exploratory cases misread the legacy ``060mm`` case label as 60 mm
# rather than 0.60 mm. They are retained locally for audit provenance but are
# invalid and must never enter the submission manifest or reported analyses.
INVALID_EXPLORATORY_PREFIXES = (
    "matched_no_contact_reference",
    "matched_no_contact_movement025",
    "garment_mesh_coarse_",
    "garment_mesh_coarse56_",
    "garment_mesh_fine72_",
    "garment_mesh_fine80_",
    "relativeF_full_garment_",
)


def write_csv(path: Path, rows: list[dict]) -> None:
    fieldnames = sorted({key for row in rows for key in row})
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def constitutive_parameters() -> list[dict]:
    rows = []
    for case_name, domains in MATERIAL_CASES.items():
        for domain, props in domains.items():
            row = {
                "material_case": case_name,
                "domain": domain,
                "density": "not used (quasi-static analysis)",
            }
            if props.get("type") == "two_fiber_textile":
                row.update(
                    {
                        "law": "uncoupled solid mixture: Mooney-Rivlin matrix + two uncoupled exp-linear fibres",
                        "matrix_c1_MPa": props["matrix_c1_MPa"],
                        "matrix_c2_MPa": 0.0,
                        "bulk_modulus_MPa": props["bulk_modulus_MPa"],
                        "fiber_x_direction": "(1,0,0)",
                        "fiber_y_direction": "(0,1,0)",
                        "fiber_dispersion": "none; perfectly aligned families",
                        "fiber_c3_MPa": 0.0,
                        "fiber_c4": props["fiber_c4"],
                        "fiber_x_c5_MPa": props["fiber_x_c5_MPa"],
                        "fiber_y_c5_MPa": props["fiber_y_c5_MPa"],
                        "fiber_transition_stretch": props[
                            "fiber_transition_stretch"
                        ],
                        "compressibility": "finite bulk penalty k",
                    }
                )
            else:
                young = float(props["E_MPa"])
                poisson = float(props["nu"])
                row.update(
                    {
                        "law": "compressible neo-Hookean",
                        "young_modulus_MPa": young,
                        "poisson_ratio": poisson,
                        "shear_modulus_MPa": young / (2.0 * (1.0 + poisson)),
                        "bulk_modulus_MPa": young / (3.0 * (1.0 - 2.0 * poisson)),
                        "compressibility": "compressible; derived from E and nu",
                    }
                )
            rows.append(row)
    return rows


def case_manifest() -> list[dict]:
    rows = []
    for metadata_path in sorted(MODEL.glob("*_metadata.json")):
        try:
            metadata = json.loads(metadata_path.read_text())
        except json.JSONDecodeError:
            continue
        case_name = metadata_path.name.removesuffix("_metadata.json")
        if case_name.startswith(INVALID_EXPLORATORY_PREFIXES):
            continue
        # A legacy generic ``mesh_metadata.json`` survives from an early
        # geometry-only export, but its FEBio input no longer exists. Submission
        # manifests must contain only cases that map to an inspectable input.
        model_path = MODEL / f"{case_name}.feb"
        if not model_path.exists():
            continue
        log_path = RESULTS / f"{case_name}.log"
        normal_termination = False
        negative_counts: list[int] = []
        if log_path.exists():
            with log_path.open(errors="replace") as log_handle:
                for line in log_handle:
                    if "N O R M A L   T E R M I N A T I O N" in line:
                        normal_termination = True
                    if "negative jacobians detected" in line:
                        match = re.search(r"(\d+) negative jacobians detected", line)
                        if match:
                            negative_counts.append(int(match.group(1)))
        summary_candidates = (
            RESULTS / f"{case_name}_summary.json",
            RESULTS / f"{case_name}_movement_summary.json",
        )
        summary_path = next((path for path in summary_candidates if path.exists()), None)
        rows.append(
            {
                "case_name": case_name,
                "model_file": f"model/{case_name}.feb",
                "metadata_file": f"model/{metadata_path.name}",
                "log_file": f"results/{case_name}.log" if log_path.exists() else "",
                "summary_file": (
                    f"results/{summary_path.name}" if summary_path is not None else ""
                ),
                "mesh_level": metadata.get("mesh_level", "garment surface"),
                "material_case": metadata.get("material_case", "garment case"),
                "node_count": metadata.get("node_count", ""),
                "element_count": metadata.get("element_count", ""),
                "normal_termination": normal_termination,
                "negative_jacobian_trial_messages": len(negative_counts),
                "maximum_trial_negative_jacobians": (
                    max(negative_counts) if negative_counts else 0
                ),
                "time_steps": metadata.get("time_steps", ""),
                "maximum_time_step": metadata.get("maximum_time_step", ""),
                "taper_length_mm": metadata.get("taper_length_mm", ""),
                "sensor_length_mm": metadata.get("initial_gauge_length_mm", ""),
                "sensor_width_mm": metadata.get("sensor_width_mm", ""),
                "backing_thickness_mm": metadata.get("backing_thickness_mm", ""),
                "conductive_thickness_mm": metadata.get(
                    "conductive_thickness_mm", ""
                ),
                "movement": metadata.get("control", {}).get("movement", ""),
            }
        )
    return rows


def geometry_screen_complete() -> list[dict]:
    source = json.loads((RESULTS / "geometry_screening.json").read_text())
    rows = []
    for row in source:
        case_name = row["case_name"]
        metadata = json.loads((MODEL / f"{case_name}_metadata.json").read_text())
        log = (RESULTS / f"{case_name}.log").read_text(errors="replace")
        warnings = re.findall(r"\*\s+(\d+) negative jacobians detected", log)
        rows.append(
            {
                **row,
                "material_case": metadata["material_case"],
                "mesh_level": metadata["mesh_level"],
                "node_count": metadata["node_count"],
                "normal_termination": "N O R M A L   T E R M I N A T I O N" in log,
                "negative_jacobian_trial_messages": len(warnings),
            }
        )
    return rows


def baseline_configurations() -> list[dict]:
    cases = [
        ("geometry_sensor_length_80", "global coarse OFAT geometry-screen baseline"),
        ("geometry_verify_baseline_medium", "global medium geometry verification"),
        ("local_mesh_coarse", "locally refined abrupt reference"),
        ("local_mesh_medium", "production locally refined abrupt reference"),
        ("taper_5mm_local_medium", "5 mm taper screening case"),
        ("taper_10mm_local_medium", "10 mm taper screening case"),
    ]
    rows = []
    for case_name, role in cases:
        metadata = json.loads((MODEL / f"{case_name}_metadata.json").read_text())
        summary = json.loads((RESULTS / f"{case_name}_summary.json").read_text())
        log = (RESULTS / f"{case_name}.log").read_text(errors="replace")
        rows.append(
            {
                "case_name": case_name,
                "role": role,
                "mesh_level": metadata["mesh_level"],
                "material_case": metadata["material_case"],
                "element_count": metadata["element_count"],
                "taper_length_mm": metadata.get("taper_length_mm", 0.0),
                "tip_thickness_fraction": metadata.get(
                    "tip_thickness_fraction", 1.0
                ),
                "conductive_gauge_end_to_end_strain_percent": 100.0
                * summary["mean_conductive_gauge_strain"],
                "transfer_ratio_percent": 100.0 * summary["strain_transfer_ratio"],
                "normal_termination": "N O R M A L   T E R M I N A T I O N" in log,
            }
        )
    return rows


def software_versions() -> dict:
    versions = {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "febio": "4.13.0",
    }
    for package in ("numpy", "matplotlib"):
        try:
            versions[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            versions[package] = "not installed in this interpreter"
    return versions


def main() -> None:
    write_csv(RESULTS / "constitutive_parameters.csv", constitutive_parameters())
    write_csv(RESULTS / "case_manifest.csv", case_manifest())
    write_csv(RESULTS / "geometry_screening_complete.csv", geometry_screen_complete())
    write_csv(RESULTS / "baseline_configurations.csv", baseline_configurations())
    (RESULTS / "software_versions.json").write_text(
        json.dumps(software_versions(), indent=2) + "\n"
    )
    print("Wrote constitutive parameters, case manifest, geometry table, baselines and versions")


if __name__ == "__main__":
    main()
