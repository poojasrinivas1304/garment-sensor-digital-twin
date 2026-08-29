#!/usr/bin/env python3
"""Run a controlled solid-mesh sequence for a regularized printed taper."""

from __future__ import annotations

import csv
import json
import math
import subprocess
import time
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np

from generate_coupon import MESH_SPECS, ROOT, generate
from postprocess_coupon import process


FEBIO = Path("/Applications/FEBioStudio/FEBioStudio.app/Contents/MacOS/febio4")
LEVELS = ("audit_coarse", "audit_medium", "audit_fine")
EDGE_PAIRS = (
    (0, 1), (1, 2), (2, 3), (3, 0),
    (4, 5), (5, 6), (6, 7), (7, 4),
    (0, 4), (1, 5), (2, 6), (3, 7),
)


def complete(case: str) -> bool:
    path = ROOT / "results" / f"{case}.log"
    return path.exists() and "N O R M A L   T E R M I N A T I O N" in path.read_text(
        errors="replace"
    )


def printed_edge_ratios(model_path: Path) -> dict[str, float]:
    root = ET.parse(model_path).getroot()
    nodes = {
        int(node.attrib["id"]): np.fromstring(node.text or "", sep=",")
        for block in root.findall("./Mesh/Nodes")
        for node in block.findall("node")
    }
    ratios = []
    minimum_edges = []
    maximum_edges = []
    taper_ratios = []
    element_count = 0
    printed_blocks = [
        block
        for block in root.findall("./Mesh/Elements")
        if block.attrib.get("name") in {"tpu_backing", "conductive_tpu"}
    ]
    printed_node_ids = {
        int(value)
        for block in printed_blocks
        for element in block.findall("elem")
        for value in (element.text or "").split(",")
    }
    printed_x_min = min(nodes[node_id][0] for node_id in printed_node_ids)
    printed_x_max = max(nodes[node_id][0] for node_id in printed_node_ids)
    for block in root.findall("./Mesh/Elements"):
        if block.attrib.get("name") not in {"tpu_backing", "conductive_tpu"}:
            continue
        for element in block.findall("elem"):
            ids = [int(value) for value in (element.text or "").split(",")]
            coordinates = [nodes[node_id] for node_id in ids]
            lengths = [
                float(np.linalg.norm(coordinates[a] - coordinates[b]))
                for a, b in EDGE_PAIRS
            ]
            minimum = min(lengths)
            maximum = max(lengths)
            ratios.append(maximum / minimum)
            centroid_x = float(np.mean([point[0] for point in coordinates]))
            # This audit uses 10-mm tapers at both printed-gauge terminals.
            if (
                centroid_x <= printed_x_min + 10.0
                or centroid_x >= printed_x_max - 10.0
            ):
                taper_ratios.append(maximum / minimum)
            minimum_edges.append(minimum)
            maximum_edges.append(maximum)
            element_count += 1
    return {
        "printed_element_count": element_count,
        "maximum_printed_edge_length_ratio": max(ratios),
        "printed_edge_length_ratio_95th_percentile": float(np.quantile(ratios, 0.95)),
        "maximum_taper_region_edge_length_ratio": max(taper_ratios),
        "taper_region_edge_length_ratio_95th_percentile": float(
            np.quantile(taper_ratios, 0.95)
        ),
        "minimum_printed_edge_length_mm": min(minimum_edges),
        "maximum_printed_edge_length_mm": max(maximum_edges),
    }


def observed_order(
    coarse: float,
    medium: float,
    fine: float,
    r_coarse_medium: float,
    r_medium_fine: float,
) -> float | None:
    denominator = medium - fine
    if denominator == 0.0:
        return None
    ratio = (coarse - medium) / denominator
    if ratio <= 0.0:
        return None
    low, high = 1e-5, 12.0
    for _ in range(120):
        trial = 0.5 * (low + high)
        predicted = (
            r_medium_fine**trial
            * (r_coarse_medium**trial - 1.0)
            / (r_medium_fine**trial - 1.0)
        )
        if predicted > ratio:
            high = trial
        else:
            low = trial
    return 0.5 * (low + high)


def main() -> None:
    rows = []
    for level in LEVELS:
        case = f"controlled10pct_mesh_taper10mm_tip50pct_{level}"
        if not complete(case):
            generate(
                case_name=case,
                mesh_level=level,
                material_case="literature_nominal",
                coupon_strain=0.10,
                taper_length_mm=10.0,
                tip_thickness_fraction=0.50,
                time_steps=60,
                maximum_time_step=0.02,
            )
            started = time.perf_counter()
            completed = subprocess.run(
                [str(FEBIO), "-i", str(ROOT / "model" / f"{case}.feb")],
                cwd=ROOT,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.STDOUT,
                check=False,
            )
            elapsed = time.perf_counter() - started
            return_code = completed.returncode
        else:
            elapsed = 0.0
            return_code = 0
        log_path = ROOT / "results" / f"{case}.log"
        log_text = log_path.read_text(errors="replace") if log_path.exists() else ""
        row = {
            "case_name": case,
            "mesh_level": level,
            "target_taper_in_plane_spacing_mm": MESH_SPECS[level]["edge_dx"],
            "normal_termination": complete(case),
            "return_code": return_code,
            "wall_time_seconds": elapsed,
            "negative_jacobian_trial_messages": log_text.count(
                "negative jacobians detected"
            ),
            **printed_edge_ratios(ROOT / "model" / f"{case}.feb"),
        }
        if row["normal_termination"]:
            result = process(case)
            row.update(
                {
                    "node_count": int(result["node_count"]),
                    "element_count": int(result["element_count"]),
                    "endpoint_strain": float(
                        result["conductive_gauge_endpoint_engineering_strain"]
                    ),
                    "path_strain": float(
                        result["conductive_gauge_centroid_path_engineering_strain"]
                    ),
                    "endpoint_transfer_ratio": float(result["strain_transfer_ratio"]),
                }
            )
        rows.append(row)
        print(json.dumps(row, indent=2), flush=True)

    metrics: dict[str, object] = {
        "status": "incomplete controlled mesh sequence",
        "geometry_note": (
            "10% coupon extension, 10-mm taper and 50% terminal thickness; this "
            "regularized in-plane audit retains one element through each printed "
            "layer and does not establish full 3D convergence or convergence of the "
            "manuscript's 30%-extension, 25%-tip cases"
        ),
    }
    completed_rows = [row for row in rows if row["normal_termination"]]
    if len(completed_rows) == 3:
        coarse, medium, fine = completed_rows
        h = [
            float(row["target_taper_in_plane_spacing_mm"])
            for row in completed_rows
        ]
        r_cm = h[0] / h[1]
        r_mf = h[1] / h[2]
        metrics.update(
            {
                "status": "three normal terminations in a controlled regularized sequence",
                "effective_spacing_ratio_coarse_to_medium": r_cm,
                "effective_spacing_ratio_medium_to_fine": r_mf,
                "effective_spacing_definition": (
                    "h is the target in-plane spacing within the terminal taper; "
                    "printed-layer through-thickness counts are fixed"
                ),
            }
        )
        for field, label in (("endpoint_strain", "endpoint"), ("path_strain", "path")):
            values = [float(row[field]) for row in completed_rows]
            for row, value in zip(completed_rows, values):
                row[f"{label}_difference_vs_fine_percent"] = 100.0 * abs(
                    value - values[-1]
                ) / max(abs(values[-1]), 1e-15)
            order = observed_order(values[0], values[1], values[2], r_cm, r_mf)
            metrics[f"{label}_monotonic_sequence"] = bool(
                (values[0] - values[1]) * (values[1] - values[2]) > 0.0
            )
            metrics[f"{label}_medium_to_fine_relative_percent"] = 100.0 * abs(
                values[2] - values[1]
            ) / max(abs(values[2]), 1e-15)
            metrics[f"{label}_observed_order_indicative"] = order
            if order is not None:
                gci = 1.25 * abs((values[2] - values[1]) / values[2]) / (
                    r_mf**order - 1.0
                )
                metrics[f"{label}_fine_grid_GCI_percent_indicative"] = 100.0 * gci
                metrics[f"{label}_richardson_extrapolated_strain_indicative"] = (
                    values[2] + (values[2] - values[1]) / (r_mf**order - 1.0)
                )
    output = {"rows": rows, "metrics": metrics}
    json_path = ROOT / "results" / "quality_mesh_convergence.json"
    csv_path = ROOT / "results" / "quality_mesh_convergence.csv"
    json_path.write_text(json.dumps(output, indent=2) + "\n")
    fields = sorted({key for row in rows for key in row})
    with csv_path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    print(json.dumps(metrics, indent=2))
    print(f"Wrote {json_path}")
    print(f"Wrote {csv_path}")


if __name__ == "__main__":
    main()
