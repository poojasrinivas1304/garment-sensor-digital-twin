#!/usr/bin/env python3
"""Extract gauge strain and a provisional piezoresistive response from FEBio output."""

from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
from xml.etree import ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
def parse_last_state(path: Path) -> dict[int, tuple[float, float, float]]:
    """Parse the final conductive-gauge coordinate block from a FEBio log."""
    lines = path.read_text(errors="replace").splitlines()
    starts = [
        i
        for i, line in enumerate(lines)
        if line.strip() == "Data = conductive_gauge_coordinates"
    ]
    if not starts:
        raise RuntimeError(f"No converged FEBio data records found in {path}")
    start = starts[-1]
    coordinates: dict[int, tuple[float, float, float]] = {}
    for line in lines[start + 1 :]:
        if (line.startswith("Data Record") or line.startswith("====")) and coordinates:
            break
        row = next(csv.reader([line]))
        if len(row) != 4:
            continue
        try:
            node_id = int(row[0].strip())
            coordinates[node_id] = tuple(float(value) for value in row[1:4])
        except ValueError:
            continue
    if not coordinates:
        raise RuntimeError(f"The final FEBio record in {path} contains no node coordinates")
    return coordinates


def mean_point(
    coordinates: dict[int, tuple[float, float, float]], ids: list[int]
) -> tuple[float, float, float]:
    missing = [node_id for node_id in ids if node_id not in coordinates]
    if missing:
        raise RuntimeError(f"Missing electrode nodes in solver output: {missing}")
    return tuple(
        sum(coordinates[node_id][axis] for node_id in ids) / len(ids)
        for axis in range(3)
    )


def initial_node_coordinates(path: Path) -> dict[int, tuple[float, float, float]]:
    """Read reference coordinates directly from the generated FEBio input."""
    root = ET.parse(path).getroot()
    coordinates: dict[int, tuple[float, float, float]] = {}
    for node in root.findall(".//Mesh/Nodes/node"):
        coordinates[int(node.attrib["id"])] = tuple(
            float(value) for value in (node.text or "").split(",")
        )
    if not coordinates:
        raise RuntimeError(f"No reference nodes found in {path}")
    return coordinates


def centroid_path_length(
    reference: dict[int, tuple[float, float, float]],
    current: dict[int, tuple[float, float, float]],
    ids: list[int],
) -> tuple[float, float, int]:
    """Return reference/current lengths of the gauge cross-section centroid path."""
    groups: dict[float, list[int]] = {}
    for node_id in ids:
        groups.setdefault(round(reference[node_id][0], 8), []).append(node_id)
    ordered = sorted(groups.items())

    def centroid(coords: dict[int, tuple[float, float, float]], members: list[int]):
        return tuple(
            sum(coords[node_id][axis] for node_id in members) / len(members)
            for axis in range(3)
        )

    reference_points = [centroid(reference, members) for _, members in ordered]
    current_points = [centroid(current, members) for _, members in ordered]

    def polyline(points: list[tuple[float, float, float]]) -> float:
        return sum(
            math.sqrt(sum((b[axis] - a[axis]) ** 2 for axis in range(3)))
            for a, b in zip(points, points[1:])
        )

    return polyline(reference_points), polyline(current_points), len(ordered)


def process(case_name: str = "coupon_baseline") -> dict[str, float | str]:
    meta_path = ROOT / "model" / f"{case_name}_metadata.json"
    coord_path = ROOT / "results" / f"{case_name}.log"
    summary_path = ROOT / "results" / f"{case_name}_summary.json"
    metadata = json.loads(meta_path.read_text())
    coordinates = parse_last_state(coord_path)
    reference_coordinates = initial_node_coordinates(
        ROOT / "model" / f"{case_name}.feb"
    )
    left_point = mean_point(coordinates, metadata["gauge_left_node_ids"])
    right_point = mean_point(coordinates, metadata["gauge_right_node_ids"])
    initial_length = metadata["initial_gauge_length_mm"]
    final_length = math.sqrt(
        sum((right_point[axis] - left_point[axis]) ** 2 for axis in range(3))
    )
    gauge_strain = (final_length - initial_length) / initial_length
    path_reference_length, path_current_length, path_section_count = centroid_path_length(
        reference_coordinates,
        coordinates,
        sorted(set(metadata["gauge_left_node_ids"] + metadata["gauge_right_node_ids"]))
        if "conductive_gauge_node_ids" not in metadata
        else metadata["conductive_gauge_node_ids"],
    )
    # Older metadata files did not retain all gauge-node ids. Recover them from
    # the conductive-gauge coordinate record when needed.
    if path_section_count <= 2:
        path_reference_length, path_current_length, path_section_count = centroid_path_length(
            reference_coordinates, coordinates, sorted(coordinates)
        )
    path_strain = (
        path_current_length - path_reference_length
    ) / path_reference_length
    coupon_strain = metadata["prescribed_displacement_mm"] / metadata["nominal_coupon_length_mm"]
    transfer = gauge_strain / coupon_strain

    # Provisional electrical law: incompressible geometric resistance change
    # multiplied by an exponential bulk-resistivity term. beta is deliberately
    # exposed and must later be calibrated from independent literature data.
    beta = 4.0
    resistance_ratio = (1.0 + gauge_strain) ** 2 * math.exp(beta * gauge_strain)
    delta_r_over_r0 = resistance_ratio - 1.0

    # The identified conductive filament is advertised with bulk volume
    # resistivity <1.25 ohm-cm.  This gives only an ideal homogeneous-part
    # resistance bound; printed roads, raster orientation and electrodes are
    # excluded, so it must not be used as a calibrated sensor baseline.
    rho_upper_ohm_cm = 1.25
    gauge_length_cm = initial_length / 10.0
    gauge_area_cm2 = (
        metadata["sensor_width_mm"] / 10.0
        * metadata["conductive_thickness_mm"] / 10.0
    )
    taper_length_cm = metadata.get("taper_length_mm", 0.0) / 10.0
    tip_fraction = metadata.get("tip_thickness_fraction", 1.0)
    if taper_length_cm > 0.0 and tip_fraction < 1.0:
        uniform_length_cm = gauge_length_cm - 2.0 * taper_length_cm
        equivalent_taper_length_cm = (
            taper_length_cm * math.log(1.0 / tip_fraction) / (1.0 - tip_fraction)
        )
        resistance_equivalent_length_cm = uniform_length_cm + 2.0 * equivalent_taper_length_cm
    else:
        resistance_equivalent_length_cm = gauge_length_cm
    ideal_bulk_r0_upper_ohm = (
        rho_upper_ohm_cm * resistance_equivalent_length_cm / gauge_area_cm2
    )

    summary = {
        "final_gauge_length_mm": final_length,
        "reference_endpoint_centroid_distance_mm": initial_length,
        "current_endpoint_centroid_distance_mm": final_length,
        "conductive_gauge_endpoint_engineering_strain": gauge_strain,
        "conductive_gauge_endpoint_green_strain": 0.5
        * ((final_length / initial_length) ** 2 - 1.0),
        "reference_centroid_path_length_mm": path_reference_length,
        "current_centroid_path_length_mm": path_current_length,
        "conductive_gauge_centroid_path_engineering_strain": path_strain,
        "conductive_gauge_centroid_path_green_strain": 0.5
        * ((path_current_length / path_reference_length) ** 2 - 1.0),
        "centroid_path_cross_section_count": path_section_count,
        "nominal_coupon_strain": coupon_strain,
        "mean_conductive_gauge_strain": gauge_strain,
        "strain_transfer_ratio": transfer,
        "provisional_piezoresistive_beta": beta,
        "predicted_delta_R_over_R0": delta_r_over_r0,
        "manufacturer_bulk_R0_upper_bound_ohm": ideal_bulk_r0_upper_ohm,
        "warning": "The legacy mean_conductive_gauge_strain key is the endpoint-centroid engineering strain, not a volume average. Mechanical constants and electrical beta are provisional. The bulk-resistivity-derived R0 bound excludes printing anisotropy, interfaces, electrodes and contact resistance.",
    }
    summary.update(
        {
            "case_name": case_name,
            "mesh_level": metadata["mesh_level"],
            "material_case": metadata.get("material_case", "provisional"),
            "node_count": metadata["node_count"],
            "element_count": metadata["element_count"],
        }
    )
    summary_path.write_text(json.dumps(summary, indent=2) + "\n")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", default="coupon_baseline")
    args = parser.parse_args()
    print(json.dumps(process(args.case), indent=2))


if __name__ == "__main__":
    main()
