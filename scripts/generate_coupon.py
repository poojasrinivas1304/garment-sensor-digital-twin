#!/usr/bin/env python3
"""Generate a conforming FEBio 4 solid model of the TPU-on-textile coupon."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from xml.etree import ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
MODEL_DIR = ROOT / "model"
RESULTS_DIR = ROOT / "results"

MESH_SPECS = {
    "coarse": {"dx": 10.0, "dy": 5.0, "z_counts": (2, 1, 1)},
    "medium": {"dx": 5.0, "dy": 2.5, "z_counts": (4, 2, 2)},
    "fine": {"dx": 2.5, "dy": 1.25, "z_counts": (6, 3, 3)},
    "extra_fine": {"dx": 1.25, "dy": 0.625, "z_counts": (8, 4, 4)},
    "local_coarse": {
        "dx": 10.0, "dy": 5.0, "edge_dx": 2.5, "edge_dy": 1.25,
        "z_counts": (4, 2, 2), "local": True,
    },
    "local_medium": {
        "dx": 5.0, "dy": 2.5, "edge_dx": 1.25, "edge_dy": 0.625,
        "z_counts": (6, 3, 3), "local": True,
    },
    "local_fine": {
        "dx": 2.5, "dy": 1.25, "edge_dx": 0.625, "edge_dy": 0.3125,
        "z_counts": (8, 4, 4), "local": True,
    },
}

MATERIAL_CASES = {
    "provisional": {
        "nylon": {"E_MPa": 5.0, "nu": 0.45},
        "backing_tpu": {"E_MPa": 8.0, "nu": 0.45},
        "conductive_tpu": {"E_MPa": 15.0, "nu": 0.45},
    },
    "literature_nominal": {
        "nylon": {"E_MPa": 0.24, "nu": 0.35},
        "backing_tpu": {"E_MPa": 48.4, "nu": 0.45},
        "conductive_tpu": {"E_MPa": 45.0, "nu": 0.45},
    },
    "textile_nu_low": {
        "nylon": {"E_MPa": 0.24, "nu": 0.20},
        "backing_tpu": {"E_MPa": 48.4, "nu": 0.45},
        "conductive_tpu": {"E_MPa": 45.0, "nu": 0.45},
    },
    "textile_nu_high": {
        "nylon": {"E_MPa": 0.24, "nu": 0.45},
        "backing_tpu": {"E_MPa": 48.4, "nu": 0.45},
        "conductive_tpu": {"E_MPa": 45.0, "nu": 0.45},
    },
    "tpu_nu_low": {
        "nylon": {"E_MPa": 0.24, "nu": 0.35},
        "backing_tpu": {"E_MPa": 48.4, "nu": 0.40},
        "conductive_tpu": {"E_MPa": 45.0, "nu": 0.40},
    },
    "tpu_nu_high": {
        "nylon": {"E_MPa": 0.24, "nu": 0.35},
        "backing_tpu": {"E_MPa": 48.4, "nu": 0.48},
        "conductive_tpu": {"E_MPa": 45.0, "nu": 0.48},
    },
    "nylon_low": {
        "nylon": {"E_MPa": 0.10, "nu": 0.35},
        "backing_tpu": {"E_MPa": 48.4, "nu": 0.45},
        "conductive_tpu": {"E_MPa": 45.0, "nu": 0.45},
    },
    "nylon_high": {
        "nylon": {"E_MPa": 5.0, "nu": 0.35},
        "backing_tpu": {"E_MPa": 48.4, "nu": 0.45},
        "conductive_tpu": {"E_MPa": 45.0, "nu": 0.45},
    },
    "backing_low": {
        "nylon": {"E_MPa": 0.24, "nu": 0.35},
        "backing_tpu": {"E_MPa": 31.4, "nu": 0.45},
        "conductive_tpu": {"E_MPa": 45.0, "nu": 0.45},
    },
    "backing_high": {
        "nylon": {"E_MPa": 0.24, "nu": 0.35},
        "backing_tpu": {"E_MPa": 67.0, "nu": 0.45},
        "conductive_tpu": {"E_MPa": 45.0, "nu": 0.45},
    },
    "conductive_low": {
        "nylon": {"E_MPa": 0.24, "nu": 0.35},
        "backing_tpu": {"E_MPa": 48.4, "nu": 0.45},
        "conductive_tpu": {"E_MPa": 12.0, "nu": 0.45},
    },
    "conductive_high": {
        "nylon": {"E_MPa": 0.24, "nu": 0.35},
        "backing_tpu": {"E_MPa": 48.4, "nu": 0.45},
        "conductive_tpu": {"E_MPa": 90.0, "nu": 0.45},
    },
    "textile_fiber_balanced": {
        "nylon": {
            "type": "two_fiber_textile", "matrix_c1_MPa": 0.01,
            "bulk_modulus_MPa": 2.4, "fiber_x_c5_MPa": 0.20,
            "fiber_y_c5_MPa": 0.20, "fiber_c4": 8.0,
            "fiber_transition_stretch": 1.05,
        },
        "backing_tpu": {"E_MPa": 48.4, "nu": 0.45},
        "conductive_tpu": {"E_MPa": 45.0, "nu": 0.45},
    },
    "textile_fiber_bulk_low": {
        "nylon": {
            "type": "two_fiber_textile", "matrix_c1_MPa": 0.01,
            "bulk_modulus_MPa": 1.2, "fiber_x_c5_MPa": 0.20,
            "fiber_y_c5_MPa": 0.20, "fiber_c4": 8.0,
            "fiber_transition_stretch": 1.05,
        },
        "backing_tpu": {"E_MPa": 48.4, "nu": 0.45},
        "conductive_tpu": {"E_MPa": 45.0, "nu": 0.45},
    },
    "textile_fiber_bulk_high": {
        "nylon": {
            "type": "two_fiber_textile", "matrix_c1_MPa": 0.01,
            "bulk_modulus_MPa": 4.8, "fiber_x_c5_MPa": 0.20,
            "fiber_y_c5_MPa": 0.20, "fiber_c4": 8.0,
            "fiber_transition_stretch": 1.05,
        },
        "backing_tpu": {"E_MPa": 48.4, "nu": 0.45},
        "conductive_tpu": {"E_MPa": 45.0, "nu": 0.45},
    },
    "textile_fiber_c4_low": {
        "nylon": {
            "type": "two_fiber_textile", "matrix_c1_MPa": 0.01,
            "bulk_modulus_MPa": 2.4, "fiber_x_c5_MPa": 0.20,
            "fiber_y_c5_MPa": 0.20, "fiber_c4": 4.0,
            "fiber_transition_stretch": 1.05,
        },
        "backing_tpu": {"E_MPa": 48.4, "nu": 0.45},
        "conductive_tpu": {"E_MPa": 45.0, "nu": 0.45},
    },
    "textile_fiber_c4_high": {
        "nylon": {
            "type": "two_fiber_textile", "matrix_c1_MPa": 0.01,
            "bulk_modulus_MPa": 2.4, "fiber_x_c5_MPa": 0.20,
            "fiber_y_c5_MPa": 0.20, "fiber_c4": 12.0,
            "fiber_transition_stretch": 1.05,
        },
        "backing_tpu": {"E_MPa": 48.4, "nu": 0.45},
        "conductive_tpu": {"E_MPa": 45.0, "nu": 0.45},
    },
    "textile_fiber_transition_low": {
        "nylon": {
            "type": "two_fiber_textile", "matrix_c1_MPa": 0.01,
            "bulk_modulus_MPa": 2.4, "fiber_x_c5_MPa": 0.20,
            "fiber_y_c5_MPa": 0.20, "fiber_c4": 8.0,
            "fiber_transition_stretch": 1.02,
        },
        "backing_tpu": {"E_MPa": 48.4, "nu": 0.45},
        "conductive_tpu": {"E_MPa": 45.0, "nu": 0.45},
    },
    "textile_fiber_transition_high": {
        "nylon": {
            "type": "two_fiber_textile", "matrix_c1_MPa": 0.01,
            "bulk_modulus_MPa": 2.4, "fiber_x_c5_MPa": 0.20,
            "fiber_y_c5_MPa": 0.20, "fiber_c4": 8.0,
            "fiber_transition_stretch": 1.08,
        },
        "backing_tpu": {"E_MPa": 48.4, "nu": 0.45},
        "conductive_tpu": {"E_MPa": 45.0, "nu": 0.45},
    },
    "textile_fiber_x3": {
        "nylon": {
            "type": "two_fiber_textile", "matrix_c1_MPa": 0.01,
            "bulk_modulus_MPa": 2.4, "fiber_x_c5_MPa": 0.30,
            "fiber_y_c5_MPa": 0.10, "fiber_c4": 8.0,
            "fiber_transition_stretch": 1.05,
        },
        "backing_tpu": {"E_MPa": 48.4, "nu": 0.45},
        "conductive_tpu": {"E_MPa": 45.0, "nu": 0.45},
    },
    "textile_fiber_y3": {
        "nylon": {
            "type": "two_fiber_textile", "matrix_c1_MPa": 0.01,
            "bulk_modulus_MPa": 2.4, "fiber_x_c5_MPa": 0.10,
            "fiber_y_c5_MPa": 0.30, "fiber_c4": 8.0,
            "fiber_transition_stretch": 1.05,
        },
        "backing_tpu": {"E_MPa": 48.4, "nu": 0.45},
        "conductive_tpu": {"E_MPa": 45.0, "nu": 0.45},
    },
}

MATERIAL_IDENTITIES = {
    "nylon": {
        "product": "Zoofly men's quick-dry athletic T-shirt, white, size XL",
        "asin": "B0D63CXLBR",
        "composition": "polyester according to product records; physical care label unavailable",
        "status": "product identified; legacy internal key 'nylon' retained for result compatibility; constitutive curves and physical composition label unavailable",
    },
    "backing_tpu": {
        "product": "Luocute white flexible TPU filament, 1.75 mm, Shore 95A",
        "asin": "B0D5MMNBRY",
        "status": "product identified; constitutive curve unavailable",
    },
    "conductive_tpu": {
        "product": "Graphene 3D Lab conductive flexible TPU filament, 1.75 mm, Shore 90A",
        "manufacturer_volume_resistivity_upper_bound_ohm_cm": 1.25,
        "status": "product identified; printed resistance-strain curve unavailable",
    },
}


def segmented_axis(breakpoints: list[float], target_spacing: float) -> list[float]:
    values = [breakpoints[0]]
    for start, stop in zip(breakpoints, breakpoints[1:]):
        count = max(1, math.ceil((stop - start) / target_spacing))
        values.extend(start + (stop - start) * i / count for i in range(1, count + 1))
    return [round(value, 8) for value in values]


def layered_axis(breakpoints: list[float], counts: tuple[int, ...]) -> list[float]:
    values = [breakpoints[0]]
    for start, stop, count in zip(breakpoints, breakpoints[1:], counts):
        values.extend(start + (stop - start) * i / count for i in range(1, count + 1))
    return [round(value, 8) for value in values]


def locally_refined_axis(
    start: float,
    stop: float,
    patch_start: float,
    patch_stop: float,
    window: float,
    base_spacing: float,
    edge_spacing: float,
) -> list[float]:
    """Create a conforming axis with compact refinement around patch edges."""
    breakpoints = sorted(
        {
            start,
            max(start, patch_start - window),
            patch_start,
            min(stop, patch_start + window),
            max(start, patch_stop - window),
            patch_stop,
            min(stop, patch_stop + window),
            stop,
        }
    )
    values = [breakpoints[0]]
    for left, right in zip(breakpoints, breakpoints[1:]):
        midpoint = 0.5 * (left + right)
        near_edge = (
            abs(midpoint - patch_start) <= window
            or abs(midpoint - patch_stop) <= window
        )
        spacing = edge_spacing if near_edge else base_spacing
        count = max(1, math.ceil((right - left) / spacing))
        values.extend(left + (right - left) * i / count for i in range(1, count + 1))
    return [round(value, 8) for value in values]


class MeshBuilder:
    def __init__(self) -> None:
        self.nodes: dict[tuple[float, float, float], int] = {}
        self.elements: dict[str, list[tuple[int, ...]]] = {
            "nylon_substrate": [],
            "interface_layer": [],
            "tpu_backing": [],
            "conductive_tpu": [],
        }

    def node(self, x: float, y: float, z: float) -> int:
        key = (round(x, 8), round(y, 8), round(z, 8))
        if key not in self.nodes:
            self.nodes[key] = len(self.nodes) + 1
        return self.nodes[key]

    def add_block(self, name: str, xs: list[float], ys: list[float], zs: list[float]) -> None:
        for k in range(len(zs) - 1):
            for j in range(len(ys) - 1):
                for i in range(len(xs) - 1):
                    x0, x1 = xs[i], xs[i + 1]
                    y0, y1 = ys[j], ys[j + 1]
                    z0, z1 = zs[k], zs[k + 1]
                    element = (
                        self.node(x0, y0, z0),
                        self.node(x1, y0, z0),
                        self.node(x1, y1, z0),
                        self.node(x0, y1, z0),
                        self.node(x0, y0, z1),
                        self.node(x1, y0, z1),
                        self.node(x1, y1, z1),
                        self.node(x0, y1, z1),
                    )
                    self.elements[name].append(element)

    def add_tapered_layer(
        self,
        name: str,
        xs: list[float],
        ys: list[float],
        layer_count: int,
        bottom_at_x,
        top_at_x,
    ) -> None:
        """Add a structured hex layer bounded by x-dependent z surfaces."""
        for k in range(layer_count):
            f0 = k / layer_count
            f1 = (k + 1) / layer_count
            for j in range(len(ys) - 1):
                for i in range(len(xs) - 1):
                    x0, x1 = xs[i], xs[i + 1]
                    y0, y1 = ys[j], ys[j + 1]
                    z00 = bottom_at_x(x0) + f0 * (top_at_x(x0) - bottom_at_x(x0))
                    z01 = bottom_at_x(x1) + f0 * (top_at_x(x1) - bottom_at_x(x1))
                    z10 = bottom_at_x(x0) + f1 * (top_at_x(x0) - bottom_at_x(x0))
                    z11 = bottom_at_x(x1) + f1 * (top_at_x(x1) - bottom_at_x(x1))
                    element = (
                        self.node(x0, y0, z00),
                        self.node(x1, y0, z01),
                        self.node(x1, y1, z01),
                        self.node(x0, y1, z00),
                        self.node(x0, y0, z10),
                        self.node(x1, y0, z11),
                        self.node(x1, y1, z11),
                        self.node(x0, y1, z10),
                    )
                    self.elements[name].append(element)


def add_text(parent: ET.Element, tag: str, value: str, **attrs: str) -> ET.Element:
    child = ET.SubElement(parent, tag, attrs)
    child.text = value
    return child


def generate(
    case_name: str = "coupon_baseline",
    mesh_level: str = "coarse",
    material_case: str = "provisional",
    sensor_length_mm: float = 80.0,
    sensor_width_mm: float = 15.0,
    backing_thickness_mm: float = 0.4,
    conductive_thickness_mm: float = 0.6,
    interface_thickness_mm: float = 0.0,
    interface_E_MPa: float = 0.10,
    interface_nu: float = 0.30,
    interface_debond_length_mm: float = 0.0,
    coupon_strain: float = 0.30,
    taper_length_mm: float = 0.0,
    tip_thickness_fraction: float = 0.25,
    loading_angle_deg: float | None = None,
    remote_transverse_ratio: float = 0.30,
    remote_exx: float | None = None,
    remote_eyy: float | None = None,
    remote_gamma_xy: float | None = None,
    remote_deformation_gradient: list[list[float]] | None = None,
    time_steps: int = 30,
    maximum_time_step: float = 0.05,
) -> None:
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    spec = MESH_SPECS[mesh_level]
    materials_for_case = MATERIAL_CASES[material_case]
    coupon_length_mm = 120.0
    coupon_width_mm = 40.0
    textile_thickness_mm = 1.6
    if not 0.0 < sensor_length_mm < coupon_length_mm:
        raise ValueError("sensor length must lie between zero and coupon length")
    if not 0.0 < sensor_width_mm < coupon_width_mm:
        raise ValueError("sensor width must lie between zero and coupon width")
    if backing_thickness_mm <= 0.0 or conductive_thickness_mm <= 0.0:
        raise ValueError("layer thicknesses must be positive")
    if interface_thickness_mm < 0.0:
        raise ValueError("interface thickness must be nonnegative")
    if interface_thickness_mm > 0.0 and interface_E_MPa <= 0.0:
        raise ValueError("interface modulus must be positive when an interface is used")
    if not -1.0 < interface_nu < 0.5:
        raise ValueError("interface Poisson ratio must lie in (-1, 0.5)")
    if interface_debond_length_mm < 0.0 or interface_debond_length_mm >= sensor_length_mm / 2.0:
        raise ValueError("interface debond length must be nonnegative and less than half the sensor length")
    if interface_debond_length_mm > 0.0 and interface_thickness_mm == 0.0:
        raise ValueError("an interface thickness is required for an initialized debond")
    if not 0.0 < coupon_strain <= 0.50:
        raise ValueError("coupon strain must be in (0, 0.50]")
    if taper_length_mm < 0.0 or taper_length_mm >= sensor_length_mm / 2.0:
        raise ValueError("taper length must be nonnegative and less than half the sensor length")
    if not 0.0 < tip_thickness_fraction <= 1.0:
        raise ValueError("tip thickness fraction must be in (0, 1]")
    if not 0.0 <= remote_transverse_ratio < 1.0:
        raise ValueError("remote transverse contraction ratio must be in [0, 1)")
    explicit_remote_values = (remote_exx, remote_eyy, remote_gamma_xy)
    if any(value is not None for value in explicit_remote_values) and not all(
        value is not None for value in explicit_remote_values
    ):
        raise ValueError("remote_exx, remote_eyy and remote_gamma_xy must be supplied together")
    if loading_angle_deg is not None and remote_exx is not None:
        raise ValueError("use either loading_angle_deg or an explicit remote strain tensor")
    if remote_deformation_gradient is not None:
        if loading_angle_deg is not None or any(
            value is not None for value in explicit_remote_values
        ):
            raise ValueError(
                "remote_deformation_gradient is mutually exclusive with strain inputs"
            )
        if len(remote_deformation_gradient) != 3 or any(
            len(row) != 3 for row in remote_deformation_gradient
        ):
            raise ValueError("remote_deformation_gradient must be a 3 by 3 matrix")
    if time_steps <= 0:
        raise ValueError("time_steps must be positive")
    if not 0.0 < maximum_time_step <= 1.0:
        raise ValueError("maximum_time_step must lie in (0, 1]")
    affine_mode = (
        loading_angle_deg is not None
        or remote_exx is not None
        or remote_deformation_gradient is not None
    )

    patch_x0 = (coupon_length_mm - sensor_length_mm) / 2.0
    patch_x1 = patch_x0 + sensor_length_mm
    patch_y0 = (coupon_width_mm - sensor_width_mm) / 2.0
    patch_y1 = patch_y0 + sensor_width_mm
    if spec.get("local"):
        xs = locally_refined_axis(
            0.0, coupon_length_mm, patch_x0, patch_x1, 5.0,
            spec["dx"], spec["edge_dx"],
        )
        ys = locally_refined_axis(
            0.0, coupon_width_mm, patch_y0, patch_y1, 2.5,
            spec["dy"], spec["edge_dy"],
        )
    else:
        x_breakpoints = [0.0, patch_x0, patch_x1, coupon_length_mm]
        if taper_length_mm > 0.0:
            x_breakpoints.extend([patch_x0 + taper_length_mm, patch_x1 - taper_length_mm])
        xs = segmented_axis(sorted(set(x_breakpoints)), spec["dx"])
        ys = segmented_axis([0.0, patch_y0, patch_y1, coupon_width_mm], spec["dy"])
    if taper_length_mm > 0.0:
        xs = sorted(set(xs + [patch_x0 + taper_length_mm, patch_x1 - taper_length_mm]))
    if interface_debond_length_mm > 0.0:
        xs = sorted(set(xs + [
            patch_x0 + interface_debond_length_mm,
            patch_x1 - interface_debond_length_mm,
        ]))
    patch_xs = [value for value in xs if patch_x0 <= value <= patch_x1]
    patch_ys = [value for value in ys if patch_y0 <= value <= patch_y1]
    interface_xs = [
        value for value in patch_xs
        if patch_x0 + interface_debond_length_mm
        <= value
        <= patch_x1 - interface_debond_length_mm
    ]
    substrate_zs = layered_axis([0.0, 1.6], (spec["z_counts"][0],))
    interface_top = textile_thickness_mm + interface_thickness_mm
    backing_top = interface_top + backing_thickness_mm
    conductive_top = backing_top + conductive_thickness_mm
    interface_zs = layered_axis(
        [textile_thickness_mm, interface_top], (1,)
    ) if interface_thickness_mm > 0.0 else []
    backing_zs = layered_axis(
        [interface_top, backing_top], (spec["z_counts"][1],)
    )
    sensor_zs = layered_axis(
        [backing_top, conductive_top], (spec["z_counts"][2],)
    )

    mesh = MeshBuilder()
    mesh.add_block("nylon_substrate", xs, ys, substrate_zs)
    if taper_length_mm == 0.0:
        if interface_thickness_mm > 0.0:
            mesh.add_block("interface_layer", interface_xs, patch_ys, interface_zs)
        mesh.add_block("tpu_backing", patch_xs, patch_ys, backing_zs)
        mesh.add_block("conductive_tpu", patch_xs, patch_ys, sensor_zs)
    else:
        def scale_at_x(x: float) -> float:
            distance = min(x - patch_x0, patch_x1 - x)
            ramp = min(1.0, max(0.0, distance / taper_length_mm))
            return tip_thickness_fraction + (1.0 - tip_thickness_fraction) * ramp

        interface_surface = lambda x: textile_thickness_mm + scale_at_x(x) * interface_thickness_mm
        backing_bottom = interface_surface
        backing_surface = lambda x: interface_surface(x) + scale_at_x(x) * backing_thickness_mm
        conductive_surface = lambda x: textile_thickness_mm + scale_at_x(x) * (
            interface_thickness_mm + backing_thickness_mm + conductive_thickness_mm
        )
        if interface_thickness_mm > 0.0:
            mesh.add_tapered_layer(
                "interface_layer", interface_xs, patch_ys, 1,
                lambda x: textile_thickness_mm, interface_surface,
            )
        mesh.add_tapered_layer(
            "tpu_backing", patch_xs, patch_ys, spec["z_counts"][1],
            backing_bottom, backing_surface,
        )
        mesh.add_tapered_layer(
            "conductive_tpu", patch_xs, patch_ys, spec["z_counts"][2],
            backing_surface, conductive_surface,
        )

    root = ET.Element("febio_spec", version="4.0")
    ET.SubElement(root, "Module", type="solid")

    control = ET.SubElement(root, "Control")
    add_text(control, "analysis", "STATIC")
    add_text(control, "time_steps", str(time_steps))
    add_text(control, "step_size", f"{1.0 / time_steps:.12g}")
    add_text(control, "plot_level", "PLOT_MUST_POINTS")
    solver = ET.SubElement(control, "solver", type="solid")
    add_text(solver, "max_refs", "25")
    add_text(solver, "diverge_reform", "1")
    add_text(solver, "reform_each_time_step", "1")
    add_text(solver, "dtol", "0.001")
    add_text(solver, "etol", "0.01")
    add_text(solver, "rtol", "0")
    time_stepper = ET.SubElement(control, "time_stepper")
    add_text(time_stepper, "dtmin", "0.0001")
    add_text(time_stepper, "dtmax", f"{maximum_time_step:.12g}")
    add_text(time_stepper, "max_retries", "12")
    add_text(time_stepper, "opt_iter", "10")

    materials = ET.SubElement(root, "Material")
    for mid, name, props in [
        (1, "nylon", materials_for_case["nylon"]),
        (2, "backing_tpu", materials_for_case["backing_tpu"]),
        (3, "conductive_tpu", materials_for_case["conductive_tpu"]),
    ]:
        if props.get("type") == "two_fiber_textile":
            material = ET.SubElement(
                materials, "material", id=str(mid), name=name,
                type="uncoupled solid mixture",
            )
            add_text(material, "k", f"{props['bulk_modulus_MPa']:g}")
            matrix = ET.SubElement(material, "solid", type="Mooney-Rivlin")
            add_text(matrix, "c1", f"{props['matrix_c1_MPa']:g}")
            add_text(matrix, "c2", "0")
            for direction, c5 in [
                ("1,0,0", props["fiber_x_c5_MPa"]),
                ("0,1,0", props["fiber_y_c5_MPa"]),
            ]:
                fiber = ET.SubElement(
                    material, "solid", type="uncoupled fiber-exp-linear"
                )
                add_text(fiber, "c3", "0")
                add_text(fiber, "c4", f"{props['fiber_c4']:g}")
                add_text(fiber, "c5", f"{c5:g}")
                add_text(
                    fiber, "lambda", f"{props['fiber_transition_stretch']:g}"
                )
                add_text(fiber, "fiber", direction, type="vector")
        else:
            material = ET.SubElement(
                materials, "material", id=str(mid), name=name, type="neo-Hookean"
            )
            add_text(material, "E", f"{props['E_MPa']:g}")
            add_text(material, "v", f"{props['nu']:g}")
    if interface_thickness_mm > 0.0:
        interface_material = ET.SubElement(
            materials, "material", id="4", name="compliant_interface", type="neo-Hookean"
        )
        add_text(interface_material, "E", f"{interface_E_MPa:g}")
        add_text(interface_material, "v", f"{interface_nu:g}")

    mesh_xml = ET.SubElement(root, "Mesh")
    nodes_xml = ET.SubElement(mesh_xml, "Nodes", name="coupon_nodes")
    for xyz, node_id in sorted(mesh.nodes.items(), key=lambda item: item[1]):
        add_text(nodes_xml, "node", ",".join(f"{v:.8g}" for v in xyz), id=str(node_id))

    element_id = 1
    for domain_name, domain_elements in mesh.elements.items():
        if not domain_elements:
            continue
        elements_xml = ET.SubElement(mesh_xml, "Elements", type="hex8", name=domain_name)
        for element in domain_elements:
            add_text(elements_xml, "elem", ",".join(map(str, element)), id=str(element_id))
            element_id += 1

    left_nodes = [
        nid for (x, _, z), nid in mesh.nodes.items()
        if x == 0.0 and z <= textile_thickness_mm
    ]
    right_nodes = [
        nid for (x, _, z), nid in mesh.nodes.items()
        if x == coupon_length_mm and z <= textile_thickness_mm
    ]
    affine_boundary_nodes = [
        nid for (x, y, z), nid in mesh.nodes.items()
        if z <= textile_thickness_mm
        and (x == 0.0 or x == coupon_length_mm or y == 0.0 or y == coupon_width_mm)
    ]
    gauge_nodes = sorted({
        nid for element in mesh.elements["conductive_tpu"] for nid in element
    })
    node_coordinates = {nid: xyz for xyz, nid in mesh.nodes.items()}
    gauge_left = [
        nid for nid in gauge_nodes if node_coordinates[nid][0] == patch_x0
    ]
    gauge_right = [
        nid for nid in gauge_nodes if node_coordinates[nid][0] == patch_x1
    ]

    standard_node_sets = [("conductive_gauge_nodes", gauge_nodes)]
    if not affine_mode:
        standard_node_sets.extend([("fixed_end", left_nodes), ("loaded_end", right_nodes)])
    for name, values in standard_node_sets:
        node_set = ET.SubElement(mesh_xml, "NodeSet", name=name)
        node_set.text = ",".join(str(nid) for nid in sorted(values))
    if affine_mode:
        for nid in sorted(affine_boundary_nodes):
            node_set = ET.SubElement(mesh_xml, "NodeSet", name=f"affine_node_{nid}")
            node_set.text = str(nid)

    domains = ET.SubElement(root, "MeshDomains")
    ET.SubElement(domains, "SolidDomain", name="nylon_substrate", mat="nylon")
    if interface_thickness_mm > 0.0:
        ET.SubElement(domains, "SolidDomain", name="interface_layer", mat="compliant_interface")
    ET.SubElement(domains, "SolidDomain", name="tpu_backing", mat="backing_tpu")
    ET.SubElement(domains, "SolidDomain", name="conductive_tpu", mat="conductive_tpu")

    boundary = ET.SubElement(root, "Boundary")
    prescribed_displacement_mm = coupon_strain * coupon_length_mm
    remote_strain_tensor = None
    if not affine_mode:
        fixed = ET.SubElement(boundary, "bc", name="clamped_left", type="zero displacement", node_set="fixed_end")
        add_text(fixed, "x_dof", "1")
        add_text(fixed, "y_dof", "1")
        add_text(fixed, "z_dof", "1")
        loaded = ET.SubElement(
            boundary,
            "bc",
            name="thirty_percent_extension",
            type="prescribed displacement",
            node_set="loaded_end",
        )
        add_text(loaded, "dof", "x")
        add_text(loaded, "value", f"{prescribed_displacement_mm:g}", lc="1")
        add_text(loaded, "relative", "0")
    else:
        if remote_deformation_gradient is not None:
            deformation_gradient = [
                [float(value) for value in row]
                for row in remote_deformation_gradient
            ]
            displacement_gradient = [
                [
                    deformation_gradient[i][j] - (1.0 if i == j else 0.0)
                    for j in range(3)
                ]
                for i in range(3)
            ]
            remote_strain_tensor = {
                "input_type": "full_relative_deformation_gradient",
                "deformation_gradient": deformation_gradient,
            }
            prescribed_displacement_mm = max(
                abs(value) for row in displacement_gradient for value in row
            ) * coupon_length_mm
            center = (
                coupon_length_mm / 2.0,
                coupon_width_mm / 2.0,
                textile_thickness_mm / 2.0,
            )
            for nid in sorted(affine_boundary_nodes):
                xyz = node_coordinates[nid]
                relative = [xyz[i] - center[i] for i in range(3)]
                displacement = [
                    sum(displacement_gradient[i][j] * relative[j] for j in range(3))
                    for i in range(3)
                ]
                for dof, value in zip(("x", "y", "z"), displacement):
                    bc = ET.SubElement(
                        boundary,
                        "bc",
                        name=f"affine_{dof}_{nid}",
                        type="prescribed displacement",
                        node_set=f"affine_node_{nid}",
                    )
                    add_text(bc, "dof", dof)
                    add_text(bc, "value", f"{value:.12g}", lc="1")
                    add_text(bc, "relative", "0")
        elif remote_exx is not None:
            exx = remote_exx
            eyy = remote_eyy
            exy = 0.5 * remote_gamma_xy
        else:
            theta = math.radians(loading_angle_deg)
            c, s = math.cos(theta), math.sin(theta)
            transverse_strain = -remote_transverse_ratio * coupon_strain
            exx = coupon_strain * c * c + transverse_strain * s * s
            eyy = coupon_strain * s * s + transverse_strain * c * c
            exy = (coupon_strain - transverse_strain) * s * c
        if remote_deformation_gradient is None:
            remote_strain_tensor = {
                "exx": exx,
                "eyy": eyy,
                "exy_tensor": exy,
                "gamma_xy_engineering": 2.0 * exy,
            }
            trace_half = 0.5 * (exx + eyy)
            radius = math.sqrt((0.5 * (exx - eyy)) ** 2 + exy**2)
            reference_strain = max(abs(trace_half + radius), abs(trace_half - radius))
            prescribed_displacement_mm = reference_strain * coupon_length_mm
            x_center = coupon_length_mm / 2.0
            y_center = coupon_width_mm / 2.0
            for nid in sorted(affine_boundary_nodes):
                x, y, _ = node_coordinates[nid]
                ux = exx * (x - x_center) + exy * (y - y_center)
                uy = exy * (x - x_center) + eyy * (y - y_center)
                for dof, value in (("x", ux), ("y", uy)):
                    bc = ET.SubElement(
                        boundary,
                        "bc",
                        name=f"affine_{dof}_{nid}",
                        type="prescribed displacement",
                        node_set=f"affine_node_{nid}",
                    )
                    add_text(bc, "dof", dof)
                    add_text(bc, "value", f"{value:.12g}", lc="1")
                    add_text(bc, "relative", "0")
            anchor_coordinates = [(0.0, 0.0, 0.0), (coupon_length_mm, 0.0, 0.0), (0.0, coupon_width_mm, 0.0)]
            for index, xyz in enumerate(anchor_coordinates, start=1):
                nid = mesh.nodes[xyz]
                anchor = ET.SubElement(
                    boundary,
                    "bc",
                    name=f"out_of_plane_anchor_{index}",
                    type="zero displacement",
                    node_set=f"affine_node_{nid}",
                )
                add_text(anchor, "z_dof", "1")

    load_data = ET.SubElement(root, "LoadData")
    load_controller = ET.SubElement(load_data, "load_controller", id="1", type="loadcurve")
    add_text(load_controller, "interpolate", "LINEAR")
    points = ET.SubElement(load_controller, "points")
    add_text(points, "point", "0,0")
    add_text(points, "point", "1,1")

    output = ET.SubElement(root, "Output")
    plotfile = ET.SubElement(output, "plotfile", type="febio", file=f"results/{case_name}.xplt")
    ET.SubElement(plotfile, "var", type="displacement")
    ET.SubElement(plotfile, "var", type="Lagrange strain")
    ET.SubElement(plotfile, "var", type="stress")
    logfile = ET.SubElement(output, "logfile", file=f"results/{case_name}.log")
    ET.SubElement(
        logfile,
        "node_data",
        data="x;y;z",
        name="conductive_gauge_coordinates",
        node_set="conductive_gauge_nodes",
        delim=",",
    )

    tree = ET.ElementTree(root)
    ET.indent(tree, space="  ")
    model_path = MODEL_DIR / f"{case_name}.feb"
    tree.write(model_path, encoding="utf-8", xml_declaration=True)

    metadata = {
        "units": {"length": "mm", "stress": "MPa"},
        "case_name": case_name,
        "mesh_level": mesh_level,
        "material_case": material_case,
        "target_in_plane_spacing_mm": {"x": spec["dx"], "y": spec["dy"]},
        "patch_edge_spacing_mm": {
            "x": spec.get("edge_dx"),
            "y": spec.get("edge_dy"),
        },
        "through_thickness_element_counts": {
            "nylon": spec["z_counts"][0],
            "interface_layer": 1 if interface_thickness_mm > 0.0 else 0,
            "backing_tpu": spec["z_counts"][1],
            "conductive_tpu": spec["z_counts"][2],
        },
        "nominal_coupon_length_mm": coupon_length_mm,
        "nominal_coupon_width_mm": coupon_width_mm,
        "textile_thickness_mm": textile_thickness_mm,
        "prescribed_displacement_mm": prescribed_displacement_mm,
        "nominal_coupon_strain": coupon_strain,
        "initial_gauge_length_mm": sensor_length_mm,
        "sensor_width_mm": sensor_width_mm,
        "backing_thickness_mm": backing_thickness_mm,
        "conductive_thickness_mm": conductive_thickness_mm,
        "interface": {
            "type": "finite neo-Hookean interphase" if interface_thickness_mm > 0.0 else "perfect shared-node bond",
            "thickness_mm": interface_thickness_mm,
            "E_MPa": interface_E_MPa if interface_thickness_mm > 0.0 else None,
            "nu": interface_nu if interface_thickness_mm > 0.0 else None,
            "status": "uncalibrated compliance sensitivity" if interface_thickness_mm > 0.0 else "ideal upper-transfer assumption",
            "initialized_unbonded_length_each_end_mm": interface_debond_length_mm,
            "damage_evolution": "not modelled",
        },
        "taper_length_mm": taper_length_mm,
        "tip_thickness_fraction": tip_thickness_fraction,
        "loading_angle_deg": loading_angle_deg,
        "remote_transverse_ratio": remote_transverse_ratio,
        "remote_strain_tensor": remote_strain_tensor,
        "time_steps": time_steps,
        "maximum_time_step": maximum_time_step,
        "conductive_gauge_node_ids": gauge_nodes,
        "gauge_left_node_ids": sorted(gauge_left),
        "gauge_right_node_ids": sorted(gauge_right),
        "node_count": len(mesh.nodes),
        "element_count": sum(len(v) for v in mesh.elements.values()),
        "element_count_by_domain": {k: len(v) for k, v in mesh.elements.items()},
        "materials": materials_for_case,
        "material_identities": MATERIAL_IDENTITIES,
    }
    (MODEL_DIR / f"{case_name}_metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
    print(f"Wrote {model_path}")
    print(f"Nodes: {metadata['node_count']}; elements: {metadata['element_count']}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", default="coupon_baseline")
    parser.add_argument("--mesh", choices=sorted(MESH_SPECS), default="coarse")
    parser.add_argument("--material-case", choices=sorted(MATERIAL_CASES), default="provisional")
    parser.add_argument("--sensor-length", type=float, default=80.0)
    parser.add_argument("--sensor-width", type=float, default=15.0)
    parser.add_argument("--backing-thickness", type=float, default=0.4)
    parser.add_argument("--conductive-thickness", type=float, default=0.6)
    parser.add_argument("--interface-thickness", type=float, default=0.0)
    parser.add_argument("--interface-E", type=float, default=0.10)
    parser.add_argument("--interface-nu", type=float, default=0.30)
    parser.add_argument("--interface-debond-length", type=float, default=0.0)
    parser.add_argument("--coupon-strain", type=float, default=0.30)
    parser.add_argument("--taper-length", type=float, default=0.0)
    parser.add_argument("--tip-thickness-fraction", type=float, default=0.25)
    parser.add_argument("--loading-angle", type=float)
    parser.add_argument("--remote-transverse-ratio", type=float, default=0.30)
    parser.add_argument("--remote-exx", type=float)
    parser.add_argument("--remote-eyy", type=float)
    parser.add_argument("--remote-gamma-xy", type=float)
    args = parser.parse_args()
    generate(
        case_name=args.case,
        mesh_level=args.mesh,
        material_case=args.material_case,
        sensor_length_mm=args.sensor_length,
        sensor_width_mm=args.sensor_width,
        backing_thickness_mm=args.backing_thickness,
        conductive_thickness_mm=args.conductive_thickness,
        interface_thickness_mm=args.interface_thickness,
        interface_E_MPa=args.interface_E,
        interface_nu=args.interface_nu,
        interface_debond_length_mm=args.interface_debond_length,
        coupon_strain=args.coupon_strain,
        taper_length_mm=args.taper_length,
        tip_thickness_fraction=args.tip_thickness_fraction,
        loading_angle_deg=args.loading_angle,
        remote_transverse_ratio=args.remote_transverse_ratio,
        remote_exx=args.remote_exx,
        remote_eyy=args.remote_eyy,
        remote_gamma_xy=args.remote_gamma_xy,
    )
