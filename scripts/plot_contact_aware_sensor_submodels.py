#!/usr/bin/env python3
"""Plot resolved contact-free and contact-aware arm-raise sensor submodels."""

from __future__ import annotations

import json
import os
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/private/tmp/matplotlib-contact-sensor")
os.environ.setdefault("MPLBACKEND", "Agg")

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import TwoSlopeNorm


ROOT = Path(__file__).resolve().parents[1]
SENSORS = (3, 8, 9, 10)
MODELS = ("contact_free", "contact_aware")
COLORS = {"contact_free": "#7A7A7A", "contact_aware": "#0072B2"}


def main() -> None:
    data = json.loads(
        (ROOT / "results" / "contact_aware_sensor_submodels.json").read_text()
    )
    lookup = {(row["model"], int(row["sensor"])): row for row in data["rows"]}
    labels = [f"S{sensor}" for sensor in SENSORS]
    x = np.arange(len(SENSORS), dtype=float)
    width = 0.34

    tensor_rows = []
    tensor_labels = []
    for model in MODELS:
        for sensor in SENSORS:
            row = lookup[(model, sensor)]
            tensor_rows.append(
                [
                    100.0 * row["target_local_xx"],
                    100.0 * row["target_local_yy"],
                    200.0 * row["target_local_xy_tensor"],
                ]
            )
            tensor_labels.append(
                f"{model.replace('_', ' ')} S{sensor}"
            )
    tensor = np.asarray(tensor_rows)

    fig, axes = plt.subplots(2, 2, figsize=(12.8, 8.6), constrained_layout=True)
    ax = axes[0, 0]
    norm = TwoSlopeNorm(vmin=float(tensor.min()), vcenter=0.0, vmax=float(tensor.max()))
    image = ax.imshow(tensor, aspect="auto", cmap="RdBu_r", norm=norm)
    ax.set_xticks(np.arange(3), [r"$E_{ss}$", r"$E_{nn}$", r"$2E_{sn}$"])
    ax.set_yticks(np.arange(len(tensor_labels)), tensor_labels, fontsize=8)
    for i in range(tensor.shape[0]):
        for j in range(tensor.shape[1]):
            ax.text(j, i, f"{tensor[i, j]:+.2f}", ha="center", va="center", fontsize=7)
    ax.set_title("(a) Sensor-aligned input tensor (%)")
    fig.colorbar(image, ax=ax, label="strain component (%)", shrink=0.82)

    ax = axes[0, 1]
    bar_width = 0.18
    series = [
        ("contact_free", "conductive_gauge_endpoint_engineering_strain", "endpoint", ""),
        ("contact_free", "conductive_gauge_centroid_path_engineering_strain", "path", "//"),
        ("contact_aware", "conductive_gauge_endpoint_engineering_strain", "endpoint", ""),
        ("contact_aware", "conductive_gauge_centroid_path_engineering_strain", "path", "//"),
    ]
    for index, (model, field, measure, hatch) in enumerate(series):
        values = [100.0 * lookup[(model, s)][field] for s in SENSORS]
        ax.bar(
            x + (index - 1.5) * bar_width,
            values,
            bar_width,
            label=f"{model.replace('_', ' ')}: {measure}",
            color=COLORS[model],
            hatch=hatch,
            edgecolor="black",
            linewidth=0.45,
        )
    ax.axhline(0.0, color="black", lw=0.8)
    ax.set_xticks(x, labels)
    ax.set_ylabel("conductive-gauge strain (%)")
    ax.set_title("(b) Resolved mechanical gauge response")
    ax.legend(frameon=False)

    ax = axes[1, 0]
    retained_by_measure = {}
    for index, (field, measure, hatch) in enumerate(
        [
            ("conductive_gauge_endpoint_engineering_strain", "endpoint", ""),
            ("conductive_gauge_centroid_path_engineering_strain", "path", "//"),
        ]
    ):
        free = np.asarray([abs(lookup[("contact_free", s)][field]) for s in SENSORS])
        aware = np.asarray([abs(lookup[("contact_aware", s)][field]) for s in SENSORS])
        retained = 100.0 * aware / free
        retained_by_measure[measure] = retained
        ax.bar(
            x + (index - 0.5) * width,
            retained,
            width,
            label=measure,
            color="#009E73" if measure == "endpoint" else "#E69F00",
            hatch=hatch,
            edgecolor="black",
            linewidth=0.45,
        )
    ax.set_ylim(
        0.0,
        max(40.0, max(float(v.max()) for v in retained_by_measure.values()) + 8.0),
    )
    ax.set_xticks(x, labels)
    ax.set_ylabel("retained gauge-strain magnitude (%)")
    ax.set_title("(c) Contact-aware signal relative to contact-free")
    ax.legend(frameon=False)

    ax = axes[1, 1]
    for model, marker in (("contact_free", "o"), ("contact_aware", "s")):
        endpoint = np.asarray(
            [100.0 * lookup[(model, s)]["conductive_gauge_endpoint_engineering_strain"] for s in SENSORS]
        )
        path = np.asarray(
            [100.0 * lookup[(model, s)]["conductive_gauge_centroid_path_engineering_strain"] for s in SENSORS]
        )
        ax.scatter(endpoint, path, s=58, marker=marker, color=COLORS[model], label=model.replace("_", " "))
        for xv, yv, sensor in zip(endpoint, path, SENSORS):
            offset = (4, 4) if sensor in (3, 9) else (4, -10)
            ax.annotate(
                f"S{sensor}",
                (xv, yv),
                xytext=offset,
                textcoords="offset points",
                fontsize=7,
            )
    limits = [-0.06, 0.18]
    ax.plot(limits, limits, color="black", ls="--", lw=0.8, label="equal measures")
    ax.axhline(0.0, color="black", lw=0.5)
    ax.axvline(0.0, color="black", lw=0.5)
    ax.set_xlim(limits)
    ax.set_ylim(limits)
    ax.set_xlabel("endpoint-centroid strain (%)")
    ax.set_ylabel("centroid-path strain (%)")
    ax.set_title("(d) Gauge-definition sensitivity")
    ax.legend(frameon=False)

    fig.suptitle(
        "Contact-aware garment mechanics propagated to resolved conductive-TPU sensors",
        fontsize=14,
    )
    output = ROOT / "figures" / "contact_aware_sensor_submodels.png"
    fig.savefig(output, dpi=300)
    plt.close(fig)
    print(f"Wrote {output}")


if __name__ == "__main__":
    main()
