#!/usr/bin/env python3
"""Report reference-configuration edge aspect ratios for the taper meshes."""

from __future__ import annotations

import json
import math
from pathlib import Path
from xml.etree import ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
CASES = ("local_coarse", "local_medium", "local_fine")
HEX_EDGES = (
    (0, 1), (1, 2), (2, 3), (3, 0),
    (4, 5), (5, 6), (6, 7), (7, 4),
    (0, 4), (1, 5), (2, 6), (3, 7),
)


def percentile(values: list[float], q: float) -> float:
    ordered = sorted(values)
    position = q * (len(ordered) - 1)
    low = math.floor(position)
    high = math.ceil(position)
    if low == high:
        return ordered[low]
    weight = position - low
    return ordered[low] * (1.0 - weight) + ordered[high] * weight


def audit(path: Path) -> dict[str, object]:
    root = ET.parse(path).getroot()
    nodes = {
        int(node.attrib["id"]): tuple(float(v) for v in node.text.split(","))
        for node in root.findall(".//Mesh/Nodes/node")
    }
    rows: list[dict[str, object]] = []
    for domain in root.findall(".//Mesh/Elements"):
        name = domain.attrib["name"]
        for element in domain.findall("elem"):
            xyz = [nodes[int(i)] for i in element.text.split(",")]
            lengths = [math.dist(xyz[i], xyz[j]) for i, j in HEX_EDGES]
            centroid_x = sum(point[0] for point in xyz) / 8.0
            rows.append(
                {
                    "domain": name,
                    "centroid_x_mm": centroid_x,
                    "edge_aspect_ratio": max(lengths) / min(lengths),
                }
            )
    taper = [
        row for row in rows
        if row["domain"] != "nylon_substrate"
        and (20.0 <= row["centroid_x_mm"] <= 30.0
             or 90.0 <= row["centroid_x_mm"] <= 100.0)
    ]
    return {
        "file": path.name,
        "element_count": len(rows),
        "taper_element_count": len(taper),
        "all_edge_aspect_ratio_median": percentile(
            [row["edge_aspect_ratio"] for row in rows], 0.5
        ),
        "all_edge_aspect_ratio_95th": percentile(
            [row["edge_aspect_ratio"] for row in rows], 0.95
        ),
        "all_edge_aspect_ratio_maximum": max(
            row["edge_aspect_ratio"] for row in rows
        ),
        "taper_edge_aspect_ratio_median": percentile(
            [row["edge_aspect_ratio"] for row in taper], 0.5
        ),
        "taper_edge_aspect_ratio_95th": percentile(
            [row["edge_aspect_ratio"] for row in taper], 0.95
        ),
        "taper_edge_aspect_ratio_maximum": max(
            row["edge_aspect_ratio"] for row in taper
        ),
    }


def main() -> None:
    results = [
        audit(ROOT / "model" / f"taper_mesh_10mm_tip25pct_{case}.feb")
        for case in CASES
    ]
    output = ROOT / "results" / "taper_mesh_quality.json"
    output.write_text(json.dumps(results, indent=2) + "\n")
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
