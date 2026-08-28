#!/usr/bin/env python3
"""Generate the first photograph-scaled FEBio shirt-on-torso equilibrium model.

The model is intentionally a verification case, not a calibrated movement
simulation.  A closed shirt shell is split into front and back element domains
with shared nodes at the side seams. It starts just outside a fixed rigid
elliptical torso, while an in-plane prestrain represents garment negative
ease. A very small external follower pressure regularizes initial contact.
This is a contact-verification model, not calibrated garment mechanics.
"""

from __future__ import annotations

import argparse
import json
import math
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CASE = "garment_contact_equilibrium"

# Millimetre geometry. The 1080-mm shirt circumference is twice the
# photograph-estimated 540-mm flat chest width.
SHIRT_LENGTH = 650.0
SHIRT_RX = 189.63
SHIRT_RY = 166.62
TORSO_RX = 188.0
TORSO_RY = 165.0
SHELL_THICKNESS = 1.6
IN_PLANE_PRESTRAIN = 0.9975
FIT_PRESSURE_MPA = 0.00002
N_THETA = 64
N_Z = 26


def add_text(parent: ET.Element, tag: str, value: object, **attrs: str) -> ET.Element:
    child = ET.SubElement(parent, tag, attrs)
    child.text = str(value)
    return child


def node_id(
    theta_index: int, z_index: int, offset: int = 0, n_theta: int = N_THETA
) -> int:
    return offset + z_index * n_theta + theta_index + 1


def add_cylindrical_nodes(
    nodes: ET.Element,
    *,
    rx: float,
    ry: float,
    offset: int,
    name: str,
    length: float = SHIRT_LENGTH,
    z_offset: float = 0.0,
    n_theta: int = N_THETA,
    n_z: int = N_Z,
) -> None:
    block = ET.SubElement(nodes, "Nodes", name=name)
    for k in range(n_z + 1):
        z = z_offset + length * k / n_z
        for j in range(n_theta):
            theta = 2.0 * math.pi * j / n_theta
            node = ET.SubElement(
                block, "node", id=str(node_id(j, k, offset, n_theta))
            )
            node.text = f"{rx * math.cos(theta):.9g},{ry * math.sin(theta):.9g},{z:.9g}"


def add_shell_part(
    mesh: ET.Element,
    *,
    name: str,
    offset: int,
    element_start: int,
    sectors: range,
    n_theta: int = N_THETA,
    n_z: int = N_Z,
) -> tuple[int, list[tuple[int, tuple[int, int, int, int]]]]:
    part = ET.SubElement(mesh, "Elements", type="quad4", name=name)
    eid = element_start
    facets: list[tuple[int, tuple[int, int, int, int]]] = []
    for k in range(n_z):
        for j in sectors:
            jp = (j + 1) % n_theta
            conn = (
                node_id(j, k, offset, n_theta),
                node_id(jp, k, offset, n_theta),
                node_id(jp, k + 1, offset, n_theta),
                node_id(j, k + 1, offset, n_theta),
            )
            elem = ET.SubElement(part, "elem", id=str(eid))
            elem.text = ",".join(map(str, conn))
            facets.append((eid, conn))
            eid += 1
    return eid, facets


def add_surface(
    mesh: ET.Element,
    name: str,
    facets: list[tuple[int, tuple[int, ...]]],
    *,
    reverse: bool = False,
) -> None:
    surface = ET.SubElement(mesh, "Surface", name=name)
    for lid, (_, conn) in enumerate(facets, 1):
        face = ET.SubElement(surface, "quad4", id=str(lid))
        oriented = (conn[0], conn[3], conn[2], conn[1]) if reverse else conn
        face.text = ",".join(map(str, oriented))


def build_model(
    *,
    case: str = CASE,
    prestrain_value: float = IN_PLANE_PRESTRAIN,
    time_steps: int = 1,
    augmented_contact: bool = True,
    contact_tolerance: float = 0.25,
    contact_maxaug: int = 3,
    penalty_scale: float = 0.5,
    staged_loading: bool = False,
    contact_stage_fraction: float = 0.2,
    geometric_overlap_mm: float = 0.0,
    torso_expansion_mm: float = 0.0,
    initial_clearance_mm: float = 0.5,
    torso_rx_mm: float = TORSO_RX,
    torso_ry_mm: float = TORSO_RY,
    garment_E_MPa: float = 0.8,
    auto_penalty: bool = True,
    friction_coefficient: float = 0.0,
    segment_updates: int = 0,
    tangential_stiffness_multiplier: float = 1.0,
    friction_formulation: str = "elastic",
    friction_penalty: float = 1.0,
    movement: str | None = None,
    movement_stage_fraction: float = 0.5,
    movement_scale: float = 1.0,
    contact_enabled: bool = True,
    n_theta: int = N_THETA,
    n_z: int = N_Z,
) -> tuple[ET.ElementTree, dict[str, object]]:
    direct_overlap_fit = geometric_overlap_mm > 0.0
    expanding_torso_fit = torso_expansion_mm > 0.0
    geometric_fit = direct_overlap_fit or expanding_torso_fit
    movement_active = movement == "both_arms_raise"
    if n_theta < 16 or n_theta % 4 != 0:
        raise ValueError("n_theta must be a multiple of four and at least 16")
    if n_z < 8:
        raise ValueError("n_z must be at least 8")
    if movement is not None and not movement_active:
        raise ValueError(f"unsupported movement: {movement}")
    if movement_active and not expanding_torso_fit:
        raise ValueError("movement requires the radially expanding torso fit")
    torso_axial_extension = 50.0 if movement_active else 0.0
    torso_model_length = SHIRT_LENGTH + 2.0 * torso_axial_extension
    if expanding_torso_fit:
        torso_rx_initial = torso_rx_mm - torso_expansion_mm
        torso_ry_initial = torso_ry_mm - torso_expansion_mm
        shirt_rx = torso_rx_initial + initial_clearance_mm
        shirt_ry = torso_ry_initial + initial_clearance_mm
    else:
        torso_rx_initial = torso_rx_mm
        torso_ry_initial = torso_ry_mm
        shirt_rx = torso_rx_mm - geometric_overlap_mm if direct_overlap_fit else SHIRT_RX
        shirt_ry = torso_ry_mm - geometric_overlap_mm if direct_overlap_fit else SHIRT_RY
    root = ET.Element("febio_spec", version="4.0")
    ET.SubElement(root, "Module", type="solid")

    control = ET.SubElement(root, "Control")
    add_text(control, "analysis", "STATIC")
    # Apply the target contraction over one or more pseudo-time increments.
    add_text(control, "time_steps", time_steps)
    add_text(control, "step_size", 1.0 / time_steps)
    add_text(control, "plot_level", "PLOT_MUST_POINTS")
    solver = ET.SubElement(control, "solver", type="solid")
    add_text(solver, "max_refs", 35)
    add_text(solver, "diverge_reform", 1)
    add_text(solver, "reform_each_time_step", 1)
    add_text(solver, "symmetric_stiffness", 0)
    add_text(solver, "dtol", 0.02)
    add_text(solver, "etol", 0.0001)
    add_text(solver, "rtol", 0.001)
    time_stepper = ET.SubElement(control, "time_stepper")
    add_text(time_stepper, "dtmin", 1e-5)
    add_text(time_stepper, "dtmax", 1.0 / time_steps)
    add_text(time_stepper, "max_retries", 15)
    add_text(time_stepper, "opt_iter", 10)

    materials = ET.SubElement(root, "Material")
    shirt = ET.SubElement(
        materials,
        "material",
        id="1",
        name="textile_provisional",
        type="neo-Hookean" if geometric_fit else "prestrain elastic",
    )
    elastic = shirt if geometric_fit else ET.SubElement(shirt, "elastic", type="neo-Hookean")
    add_text(elastic, "E", garment_E_MPa)
    add_text(elastic, "v", 0.30)
    if not geometric_fit:
        prestrain = ET.SubElement(shirt, "prestrain", type="prestrain gradient")
        add_text(prestrain, "ramp", 1.0, lc="1")
        add_text(
            prestrain,
            "F0",
            f"{prestrain_value},0,0,0,{prestrain_value},0,0,0,1",
        )
    torso = ET.SubElement(
        materials, "material", id="2", name="torso_fixed", type="neo-Hookean"
    )
    torso_E = 0.8 if expanding_torso_fit else 1000.0
    add_text(torso, "E", torso_E)
    add_text(torso, "v", 0.30)

    mesh = ET.SubElement(root, "Mesh")
    shirt_node_count = n_theta * (n_z + 1)
    add_cylindrical_nodes(
        mesh, rx=shirt_rx, ry=shirt_ry, offset=0, name="shirt_nodes",
        n_theta=n_theta, n_z=n_z,
    )
    add_cylindrical_nodes(
        mesh,
        rx=torso_rx_initial,
        ry=torso_ry_initial,
        offset=shirt_node_count,
        name="torso_nodes",
        length=torso_model_length,
        z_offset=-torso_axial_extension,
        n_theta=n_theta,
        n_z=n_z,
    )

    # Front is the negative-y half and back is the positive-y half. The shared
    # theta=0 and theta=pi node columns are the two side seams.
    eid, back_facets = add_shell_part(
        mesh,
        name="shirt_back",
        offset=0,
        element_start=1,
        sectors=range(0, n_theta // 2),
        n_theta=n_theta,
        n_z=n_z,
    )
    eid, front_facets = add_shell_part(
        mesh,
        name="shirt_front",
        offset=0,
        element_start=eid,
        sectors=range(n_theta // 2, n_theta),
        n_theta=n_theta,
        n_z=n_z,
    )
    eid, torso_facets = add_shell_part(
        mesh,
        name="torso_surface_elements",
        offset=shirt_node_count,
        element_start=eid,
        sectors=range(n_theta),
        n_theta=n_theta,
        n_z=n_z,
    )
    shirt_facets = back_facets + front_facets

    top_nodes = [node_id(j, n_z, n_theta=n_theta) for j in range(n_theta)]
    add_text(mesh, "NodeSet", ",".join(map(str, top_nodes)), name="shirt_top_ring")
    if movement_active:
        for j in range(n_theta):
            add_text(
                mesh,
                "NodeSet",
                str(node_id(j, n_z, n_theta=n_theta)),
                name=f"shirt_top_node_{j}",
            )
    add_text(mesh, "NodeSet", str(node_id(0, n_z, n_theta=n_theta)), name="shirt_anchor_y")
    add_text(mesh, "NodeSet", str(node_id(n_theta // 4, n_z, n_theta=n_theta)), name="shirt_anchor_x")
    add_text(
        mesh,
        "NodeSet",
        ",".join(map(str, range(1, shirt_node_count + 1))),
        name="shirt_all_nodes",
    )
    add_text(
        mesh,
        "NodeSet",
        ",".join(
            map(
                str,
                range(
                    shirt_node_count + 1,
                    2 * shirt_node_count + 1,
                ),
            )
        ),
        name="torso_all_nodes",
    )
    if expanding_torso_fit:
        for j in range(n_theta):
            column = [
                node_id(j, k, shirt_node_count, n_theta) for k in range(n_z + 1)
            ]
            add_text(
                mesh,
                "NodeSet",
                ",".join(map(str, column)),
                name=f"torso_column_{j}",
            )
    shirt_element_ids = [eid_ for eid_, _ in shirt_facets]
    add_text(mesh, "ElementSet", ",".join(map(str, shirt_element_ids)), name="shirt_all")
    # An outside garment searches inward toward the torso. In the geometric
    # negative-ease case the reference shirt lies just inside the torso, so
    # its outward face must be used while contact expands it to the body.
    add_surface(
        mesh,
        "shirt_on_torso_primary",
        shirt_facets,
        reverse=not direct_overlap_fit,
    )
    add_surface(mesh, "shirt_on_torso_secondary", torso_facets)
    add_surface(mesh, "shirt_pressure_surface", shirt_facets)
    pair = ET.SubElement(mesh, "SurfacePair", name="shirt_torso_pair")
    add_text(pair, "primary", "shirt_on_torso_primary")
    add_text(pair, "secondary", "shirt_on_torso_secondary")

    domains = ET.SubElement(root, "MeshDomains")
    for name in ("shirt_front", "shirt_back"):
        domain = ET.SubElement(
            domains,
            "ShellDomain",
            name=name,
            mat="textile_provisional",
            type="elastic-shell",
        )
        add_text(domain, "shell_thickness", SHELL_THICKNESS)
    torso_domain = ET.SubElement(
        domains,
        "ShellDomain",
        name="torso_surface_elements",
        mat="torso_fixed",
        type="elastic-shell",
    )
    add_text(torso_domain, "shell_thickness", 1.0)

    boundary = ET.SubElement(root, "Boundary")
    if not movement_active:
        top_bc = ET.SubElement(
            boundary, "bc", name="support_top_vertical", type="zero displacement", node_set="shirt_top_ring"
        )
        add_text(top_bc, "z_dof", 1)
    else:
        for j in range(n_theta):
            theta = 2.0 * math.pi * j / n_theta
            x_normalized = (shirt_rx * math.cos(theta)) / (2.0 * shirt_rx)
            u_normalized = 0.025 * x_normalized
            shoulder_weight = 0.55 + 1.8 * x_normalized**2
            v_normalized = 0.060 * shoulder_weight
            movement_values = (
                ("x", movement_scale * 540.0 * u_normalized),
                ("z", movement_scale * SHIRT_LENGTH * v_normalized),
            )
            for dof, value in movement_values:
                prescribed = ET.SubElement(
                    boundary,
                    "bc",
                    name=f"both_arms_raise_{dof}_{j}",
                    type="prescribed displacement",
                    node_set=f"shirt_top_node_{j}",
                )
                add_text(prescribed, "dof", dof)
                add_text(prescribed, "value", f"{value:.12g}", lc="2")
    anchor_y = ET.SubElement(
        boundary, "bc", name="remove_y_translation", type="zero displacement", node_set="shirt_anchor_y"
    )
    add_text(anchor_y, "y_dof", 1)
    anchor_x = ET.SubElement(
        boundary, "bc", name="remove_x_translation", type="zero displacement", node_set="shirt_anchor_x"
    )
    add_text(anchor_x, "x_dof", 1)
    torso_bc = ET.SubElement(
        boundary,
        "bc",
        name="fixed_torso_axial" if expanding_torso_fit else "fixed_torso",
        type="zero displacement",
        node_set="torso_all_nodes",
    )
    for dof in (("z_dof",) if expanding_torso_fit else ("x_dof", "y_dof", "z_dof")):
        add_text(torso_bc, dof, 1)
    if expanding_torso_fit:
        for j in range(n_theta):
            theta = 2.0 * math.pi * j / n_theta
            for dof, value in (
                ("x", torso_expansion_mm * math.cos(theta)),
                ("y", torso_expansion_mm * math.sin(theta)),
            ):
                prescribed = ET.SubElement(
                    boundary,
                    "bc",
                    name=f"expand_torso_{dof}_{j}",
                    type="prescribed displacement",
                    node_set=f"torso_column_{j}",
                )
                add_text(prescribed, "dof", dof)
                add_text(prescribed, "value", f"{value:.12g}", lc="1")

    contact_type = (
        "sliding-node-on-facet"
        if friction_formulation == "node-on-facet"
        else "sliding-elastic"
        if friction_coefficient > 0.0
        else "sliding-facet-on-facet"
    )
    if contact_enabled:
        contact = ET.SubElement(root, "Contact")
        sliding = ET.SubElement(
            contact,
            "contact",
            name="shirt_on_torso",
            type=contact_type,
            surface_pair="shirt_torso_pair",
        )
        add_text(sliding, "auto_penalty", int(auto_penalty))
        add_text(sliding, "penalty", penalty_scale)
        add_text(sliding, "two_pass", 0)
        add_text(sliding, "laugon", int(augmented_contact))
        if augmented_contact:
            add_text(sliding, "tolerance", contact_tolerance)
            add_text(sliding, "gaptol", 0.01)
            add_text(sliding, "minaug", 1)
            add_text(sliding, "maxaug", contact_maxaug)
        add_text(sliding, "search_radius", 20.0)
        add_text(sliding, "search_tol", 0.1)
        if friction_coefficient > 0.0:
            add_text(sliding, "fric_coeff", friction_coefficient)
            if friction_formulation == "node-on-facet":
                add_text(sliding, "fric_penalty", friction_penalty)
                add_text(sliding, "ktmult", tangential_stiffness_multiplier)
        if segment_updates > 0:
            add_text(sliding, "seg_up", segment_updates)

    if not geometric_fit:
        loads = ET.SubElement(root, "Loads")
        pressure = ET.SubElement(
            loads,
            "surface_load",
            name="fit_pressure_surrogate",
            type="pressure",
            surface="shirt_pressure_surface",
        )
        add_text(
            pressure,
            "pressure",
            FIT_PRESSURE_MPA,
            **({"lc": "2"} if staged_loading else {}),
        )
        add_text(pressure, "symmetric_stiffness", 0)

        load_data = ET.SubElement(root, "LoadData")
        load_controller = ET.SubElement(
            load_data, "load_controller", id="1", type="loadcurve"
        )
        add_text(load_controller, "interpolate", "LINEAR")
        points = ET.SubElement(load_controller, "points")
        add_text(points, "pt", "0,0")
        if staged_loading:
            add_text(points, "pt", f"{contact_stage_fraction},0")
        add_text(points, "pt", "1,1")
        if staged_loading:
            pressure_controller = ET.SubElement(
                load_data, "load_controller", id="2", type="loadcurve"
            )
            add_text(pressure_controller, "interpolate", "LINEAR")
            pressure_points = ET.SubElement(pressure_controller, "points")
            add_text(pressure_points, "pt", "0,0")
            add_text(pressure_points, "pt", f"{contact_stage_fraction},1")
            add_text(pressure_points, "pt", "1,1")
    elif expanding_torso_fit:
        load_data = ET.SubElement(root, "LoadData")
        load_controller = ET.SubElement(
            load_data, "load_controller", id="1", type="loadcurve"
        )
        add_text(load_controller, "interpolate", "LINEAR")
        points = ET.SubElement(load_controller, "points")
        add_text(points, "pt", "0,0")
        if movement_active:
            add_text(points, "pt", f"{movement_stage_fraction},1")
        add_text(points, "pt", "1,1")
        if movement_active:
            movement_controller = ET.SubElement(
                load_data, "load_controller", id="2", type="loadcurve"
            )
            add_text(movement_controller, "interpolate", "LINEAR")
            movement_points = ET.SubElement(movement_controller, "points")
            add_text(movement_points, "pt", "0,0")
            add_text(movement_points, "pt", f"{movement_stage_fraction},0")
            add_text(movement_points, "pt", "1,1")

    output = ET.SubElement(root, "Output")
    plotfile = ET.SubElement(
        output, "plotfile", type="febio", file=f"results/{case}.xplt"
    )
    plot_variables = ["displacement", "stress", "Lagrange strain", "shell thickness"]
    if contact_enabled:
        plot_variables.extend(["contact gap", "contact pressure"])
    for variable in plot_variables:
        ET.SubElement(plotfile, "var", type=variable)
    logfile = ET.SubElement(output, "logfile", file=f"results/{case}.log")
    ET.SubElement(
        logfile,
        "node_data",
        data="x;y;z",
        name="shirt_final_coordinates",
        node_set="shirt_all_nodes",
        delim=",",
    )
    if contact_enabled:
        ET.SubElement(
            logfile,
            "face_data",
            data="contact gap;contact pressure",
            name="shirt_contact_data",
            surface="shirt_on_torso_primary",
            delim=",",
        )

    ET.indent(root, space="  ")
    metadata = {
        "case": case,
        "status": (
            "radially expanded torso fitted-contact verification; not calibrated garment mechanics"
            if expanding_torso_fit
            else "prestrained fitted-contact verification; not calibrated garment mechanics"
        ),
        "units": "mm, MPa, N",
        "shirt": {
            "photograph_scaled_flat_chest_width_mm": 540.0,
            "modelled_body_panel_length_mm": SHIRT_LENGTH,
            "ellipse_radii_mm": [shirt_rx, shirt_ry],
            "shell_thickness_mm": SHELL_THICKNESS,
            "material": {
                "type": "neo-Hookean geometric fit" if geometric_fit else "prestrain elastic / neo-Hookean",
                "E_MPa": garment_E_MPa,
                "v": 0.30,
                "in_plane_prestrain_gradient": None if geometric_fit else prestrain_value,
            },
            "front_and_back_domains_share_side_seam_nodes": True,
        },
        "torso": {
            "type": (
                "prescribed radially expanding elliptical shell"
                if expanding_torso_fit
                else "fully fixed high-stiffness elliptical shell"
            ),
            "ellipse_radii_mm": [torso_rx_mm, torso_ry_mm],
            "initial_ellipse_radii_mm": [torso_rx_initial, torso_ry_initial],
            "prescribed_radial_expansion_mm": torso_expansion_mm,
            "axial_range_mm": [
                -torso_axial_extension,
                SHIRT_LENGTH + torso_axial_extension,
            ],
            "material": {"type": "neo-Hookean", "E_MPa": torso_E, "v": 0.30},
        },
        "mesh": {
            "circumferential_divisions": n_theta,
            "vertical_divisions": n_z,
            "shirt_shell_elements": len(shirt_facets),
            "torso_fixed_shell_elements": len(torso_facets),
        },
        "contact": {
            "enabled": contact_enabled,
            "type": contact_type,
            "shirt_is_primary": True,
            "fixed_high_stiffness_torso_is_secondary": True,
            "shirt_bottom_surface_used": False,
            "primary_surface_connectivity_reversed_to_inward_face": not direct_overlap_fit,
            "friction_coefficient": friction_coefficient,
            "friction_note": (
                f"{contact_type} frictional formulation"
                if friction_coefficient > 0.0
                else f"frictionless {contact_type} formulation"
            ),
            "negative_ease_representation": (
                "prescribed radial torso expansion"
                if expanding_torso_fit
                else "in-plane prestrain gradient"
            ),
            "regularizing_external_fit_pressure_MPa": (
                None if geometric_fit else FIT_PRESSURE_MPA
            ),
            "geometric_overlap_mm": geometric_overlap_mm,
            "initial_clearance_mm": (
                initial_clearance_mm if expanding_torso_fit else None
            ),
            "augmented_lagrangian": augmented_contact,
            "augmentation_tolerance": (
                contact_tolerance if augmented_contact else None
            ),
            "maximum_augmentations": contact_maxaug if augmented_contact else 0,
            "penalty_scale": penalty_scale,
            "automatic_penalty_scaling": auto_penalty,
            "segment_updates_per_time_step": segment_updates,
            "tangential_stiffness_multiplier": (
                tangential_stiffness_multiplier if friction_coefficient > 0.0 else None
            ),
            "friction_formulation": friction_formulation,
            "friction_penalty": (
                friction_penalty
                if friction_coefficient > 0.0 and friction_formulation == "node-on-facet"
                else None
            ),
        },
        "control": {
            "time_steps": time_steps,
            "step_size": 1.0 / time_steps,
            "staged_loading": staged_loading,
            "contact_stage_fraction": (
                contact_stage_fraction if staged_loading else None
            ),
            "movement": movement,
            "movement_stage_fraction": (
                movement_stage_fraction if movement_active else None
            ),
            "movement_scale": movement_scale if movement_active else None,
            "movement_boundary": (
                "upper garment ring driven by compatible both-arms-raise field"
                if movement_active else None
            ),
        },
    }
    return ET.ElementTree(root), metadata


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", default=CASE)
    parser.add_argument("--prestrain", type=float, default=IN_PLANE_PRESTRAIN)
    parser.add_argument("--time-steps", type=int, default=1)
    parser.add_argument("--penalty-only", action="store_true")
    parser.add_argument("--contact-tolerance", type=float, default=0.25)
    parser.add_argument("--contact-maxaug", type=int, default=3)
    parser.add_argument("--penalty-scale", type=float, default=0.5)
    parser.add_argument("--staged-loading", action="store_true")
    parser.add_argument("--contact-stage-fraction", type=float, default=0.2)
    parser.add_argument("--geometric-overlap-mm", type=float, default=0.0)
    parser.add_argument("--torso-expansion-mm", type=float, default=0.0)
    parser.add_argument("--initial-clearance-mm", type=float, default=0.5)
    parser.add_argument("--torso-rx-mm", type=float, default=TORSO_RX)
    parser.add_argument("--torso-ry-mm", type=float, default=TORSO_RY)
    parser.add_argument("--garment-E-MPa", type=float, default=0.8)
    parser.add_argument("--manual-penalty", action="store_true")
    parser.add_argument("--friction-coefficient", type=float, default=0.0)
    parser.add_argument("--segment-updates", type=int, default=0)
    parser.add_argument("--tangential-stiffness-multiplier", type=float, default=1.0)
    parser.add_argument("--friction-formulation", choices=("elastic", "node-on-facet"), default="elastic")
    parser.add_argument("--friction-penalty", type=float, default=1.0)
    parser.add_argument("--movement", choices=["both_arms_raise"])
    parser.add_argument("--movement-stage-fraction", type=float, default=0.5)
    parser.add_argument("--movement-scale", type=float, default=1.0)
    parser.add_argument("--no-contact", action="store_true")
    parser.add_argument("--n-theta", type=int, default=N_THETA)
    parser.add_argument("--n-z", type=int, default=N_Z)
    args = parser.parse_args()
    if not 0.9 <= args.prestrain <= 1.01:
        parser.error("--prestrain must be between 0.9 and 1.01")
    if args.time_steps < 1:
        parser.error("--time-steps must be positive")
    if not 0.0 < args.contact_stage_fraction < 1.0:
        parser.error("--contact-stage-fraction must lie between zero and one")
    if args.torso_rx_mm <= 0.0 or args.torso_ry_mm <= 0.0:
        parser.error("torso radii must be positive")
    if not 0.0 <= args.geometric_overlap_mm < min(args.torso_rx_mm, args.torso_ry_mm):
        parser.error("--geometric-overlap-mm must be nonnegative and smaller than the torso radii")
    if not 0.0 <= args.torso_expansion_mm < min(args.torso_rx_mm, args.torso_ry_mm):
        parser.error("--torso-expansion-mm must be nonnegative and smaller than the torso radii")
    if args.geometric_overlap_mm > 0.0 and args.torso_expansion_mm > 0.0:
        parser.error("choose either direct geometric overlap or torso expansion, not both")
    if not 0.0 < args.initial_clearance_mm:
        parser.error("--initial-clearance-mm must be positive")
    if not 0.0 < args.garment_E_MPa:
        parser.error("--garment-E-MPa must be positive")
    if not 0.0 <= args.friction_coefficient <= 1.0:
        parser.error("--friction-coefficient must lie in [0, 1]")
    if args.segment_updates < 0:
        parser.error("--segment-updates must be non-negative")
    if not 0.0 < args.tangential_stiffness_multiplier <= 1.0:
        parser.error("--tangential-stiffness-multiplier must lie in (0, 1]")
    if args.friction_penalty <= 0.0:
        parser.error("--friction-penalty must be positive")
    if not 0.0 < args.movement_stage_fraction < 1.0:
        parser.error("--movement-stage-fraction must lie between zero and one")
    if not 0.0 < args.movement_scale <= 1.0:
        parser.error("--movement-scale must lie in (0, 1]")

    tree, metadata = build_model(
        case=args.case,
        prestrain_value=args.prestrain,
        time_steps=args.time_steps,
        augmented_contact=not args.penalty_only,
        contact_tolerance=args.contact_tolerance,
        contact_maxaug=args.contact_maxaug,
        penalty_scale=args.penalty_scale,
        staged_loading=args.staged_loading,
        contact_stage_fraction=args.contact_stage_fraction,
        geometric_overlap_mm=args.geometric_overlap_mm,
        torso_expansion_mm=args.torso_expansion_mm,
        initial_clearance_mm=args.initial_clearance_mm,
        torso_rx_mm=args.torso_rx_mm,
        torso_ry_mm=args.torso_ry_mm,
        garment_E_MPa=args.garment_E_MPa,
        auto_penalty=not args.manual_penalty,
        friction_coefficient=args.friction_coefficient,
        segment_updates=args.segment_updates,
        tangential_stiffness_multiplier=args.tangential_stiffness_multiplier,
        friction_formulation=args.friction_formulation,
        friction_penalty=args.friction_penalty,
        movement=args.movement,
        movement_stage_fraction=args.movement_stage_fraction,
        movement_scale=args.movement_scale,
        contact_enabled=not args.no_contact,
        n_theta=args.n_theta,
        n_z=args.n_z,
    )
    model_path = ROOT / "model" / f"{args.case}.feb"
    metadata_path = ROOT / "model" / f"{args.case}_metadata.json"
    tree.write(model_path, encoding="utf-8", xml_declaration=True)
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n")
    print(f"Wrote {model_path}")
    print(f"Wrote {metadata_path}")


if __name__ == "__main__":
    main()
