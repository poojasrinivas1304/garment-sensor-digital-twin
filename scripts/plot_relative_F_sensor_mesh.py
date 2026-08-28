#!/usr/bin/env python3
"""Plot relative-F resolved-sensor mesh sensitivity."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    data = json.loads((ROOT / "results" / "relative_F_sensor_mesh.json").read_text())
    rows = data["rows"]
    meshes = ("local_coarse", "local_medium", "local_fine")
    styles = {
        ("full_garment_no_contact", 3): ("#2c7fb8", "o", "S3, no contact"),
        ("full_garment_contact", 3): ("#d95f43", "s", "S3, contact"),
        ("full_garment_no_contact", 9): ("#41ab5d", "^", "S9, no contact"),
        ("full_garment_contact", 9): ("#756bb1", "D", "S9, contact"),
    }
    fig, axes = plt.subplots(1, 2, figsize=(9.4, 4.0), constrained_layout=True)
    for (model, sensor), (color, marker, label) in styles.items():
        selected = {
            row["mesh"]: row
            for row in rows
            if row["garment_model"] == model and row["sensor"] == sensor
        }
        x = [selected[m]["element_count"] for m in meshes]
        endpoint = [selected[m]["endpoint_gauge_percent"] for m in meshes]
        path = [selected[m]["path_gauge_percent"] for m in meshes]
        axes[0].plot(x, endpoint, color=color, marker=marker, label=label)
        axes[1].plot(x, path, color=color, marker=marker, label=label)
    for i, (ax, title) in enumerate(zip(axes, ("Endpoint-centroid gauge", "Centroid-path gauge"))):
        ax.axhline(0.0, color="black", lw=0.8)
        ax.set_xscale("log")
        ax.set_xlabel("Resolved sensor elements (log scale)")
        ax.set_ylabel("Conductive-gauge strain (%)")
        ax.set_title(f"{'ab'[i]}  {title}", loc="left", fontweight="bold")
        ax.grid(color="#dddddd", lw=0.6)
    axes[0].legend(frameon=False, fontsize=8)
    output = ROOT / "figures" / "relative_F_sensor_mesh.png"
    compile_output = ROOT / "overleaf" / "compile_figures" / "relative_F_sensor_mesh.jpg"
    fig.savefig(output, dpi=300, bbox_inches="tight")
    fig.savefig(compile_output, dpi=240, bbox_inches="tight")
    print(output)
    print(compile_output)


if __name__ == "__main__":
    main()
