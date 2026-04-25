from __future__ import annotations

import math
from typing import Any

import numpy as np

from .load_manager import infer_load_case
from .mesh import build_structured_tet_mesh
from .models import MATERIALS, Design, Material


def isotropic_elasticity_matrix(material: Material) -> np.ndarray:
    e = material.young_mpa
    nu = material.poisson
    lam = e * nu / ((1 + nu) * (1 - 2 * nu))
    mu = e / (2 * (1 + nu))
    return np.array(
        [
            [lam + 2 * mu, lam, lam, 0, 0, 0],
            [lam, lam + 2 * mu, lam, 0, 0, 0],
            [lam, lam, lam + 2 * mu, 0, 0, 0],
            [0, 0, 0, mu, 0, 0],
            [0, 0, 0, 0, mu, 0],
            [0, 0, 0, 0, 0, mu],
        ],
        dtype=float,
    )


def tet_stiffness(points: np.ndarray, material: Material) -> tuple[np.ndarray, np.ndarray, float] | None:
    m = np.column_stack([np.ones(4), points])
    det = float(np.linalg.det(m))
    volume = abs(det) / 6
    if volume < 1e-9:
        return None
    inv = np.linalg.inv(m)
    b, c, d = inv[1, :], inv[2, :], inv[3, :]
    bmat = np.zeros((6, 12), dtype=float)
    for i in range(4):
        col = 3 * i
        bmat[0, col] = b[i]
        bmat[1, col + 1] = c[i]
        bmat[2, col + 2] = d[i]
        bmat[3, col] = c[i]
        bmat[3, col + 1] = b[i]
        bmat[4, col + 1] = d[i]
        bmat[4, col + 2] = c[i]
        bmat[5, col] = d[i]
        bmat[5, col + 2] = b[i]
    dmat = isotropic_elasticity_matrix(material)
    return bmat.T @ dmat @ bmat * volume, bmat, volume


def von_mises(stress: np.ndarray) -> float:
    sx, sy, sz, txy, tyz, txz = stress
    return float(math.sqrt(0.5 * ((sx - sy) ** 2 + (sy - sz) ** 2 + (sz - sx) ** 2) + 3 * (txy**2 + tyz**2 + txz**2)))


def estimate_mass_g(design: Design) -> float:
    material = MATERIALS[design.material]
    volume = design.base_length_mm * design.base_width_mm * design.base_thickness_mm
    for hole in design.fixed_holes:
        volume -= math.pi * hole.radius**2 * design.base_thickness_mm
    for feature in design.features:
        if feature.type == "lightening_hole":
            volume -= math.pi * feature.radius**2 * design.base_thickness_mm
        elif feature.type == "boss":
            volume += math.pi * max(feature.radius, 1) ** 2 * max(feature.height, 1)
        elif feature.type == "rib":
            length = math.hypot(feature.x2 - feature.x, feature.y2 - feature.y)
            volume += length * max(feature.width, 1) * max(feature.height, 1) * 0.85
    return round(max(volume, 1) * material.density_g_cm3 / 1000, 2)


def solve_3d_linear_elasticity(design: Design, prompt: str = "") -> dict[str, Any]:
    material = MATERIALS[design.material]
    load_case = infer_load_case(prompt, design)
    mesh = build_structured_tet_mesh(design)
    if len(mesh.nodes) < 8 or len(mesh.tets) < 6:
        raise ValueError("3D mesh has too few solid elements.")

    dof_count = len(mesh.nodes) * 3
    stiffness = np.zeros((dof_count, dof_count), dtype=float)
    force = np.zeros(dof_count, dtype=float)
    element_cache: list[dict[str, Any]] = []

    node_points = np.array([[node["x"], node["y"], node["z"]] for node in mesh.nodes], dtype=float)
    for tet in mesh.tets:
        points = node_points[np.array(tet)]
        result = tet_stiffness(points, material)
        if result is None:
            continue
        ke, bmat, volume = result
        dofs = np.array([dof for node_id in tet for dof in (node_id * 3, node_id * 3 + 1, node_id * 3 + 2)])
        stiffness[np.ix_(dofs, dofs)] += ke
        element_cache.append({"tet": tet, "bmat": bmat, "volume": volume})

    load_x, load_y, load_z = load_case["load_point"]
    candidates = sorted(
        [
            (
                node["id"],
                math.sqrt(
                    ((node["x"] - load_x) / max(mesh.length, 1)) ** 2
                    + ((node["y"] - load_y) / max(mesh.width, 1)) ** 2
                    + ((node["z"] - load_z) / max(mesh.height, 1)) ** 2
                ),
            )
            for node in mesh.nodes
        ],
        key=lambda item: item[1],
    )[:6]
    for node_id, _ in candidates:
        force[node_id * 3 + 2] -= load_case["effective_load_n"] / len(candidates)

    fixed_nodes = [node["id"] for node in mesh.nodes if node["x"] <= mesh.length * 0.001]
    fixed_dofs = {dof for node_id in fixed_nodes for dof in (node_id * 3, node_id * 3 + 1, node_id * 3 + 2)}
    free_dofs = np.array([idx for idx in range(dof_count) if idx not in fixed_dofs])
    displacement = np.zeros(dof_count, dtype=float)
    displacement[free_dofs] = np.linalg.solve(stiffness[np.ix_(free_dofs, free_dofs)], force[free_dofs])

    dmat = isotropic_elasticity_matrix(material)
    element_results = []
    max_vm = 0.0
    max_strain = 0.0
    for item in element_cache:
        tet = item["tet"]
        dofs = np.array([dof for node_id in tet for dof in (node_id * 3, node_id * 3 + 1, node_id * 3 + 2)])
        strain = item["bmat"] @ displacement[dofs]
        stress = dmat @ strain
        vm = von_mises(stress)
        strain_mag = float(np.linalg.norm(strain))
        max_vm = max(max_vm, vm)
        max_strain = max(max_strain, strain_mag)
        centroid = node_points[np.array(tet)].mean(axis=0)
        element_results.append(
            {
                "centroid": {"x": round(float(centroid[0]), 3), "y": round(float(centroid[1]), 3), "z": round(float(centroid[2]), 3)},
                "von_mises_mpa": round(vm, 3),
                "strain_microstrain": round(strain_mag * 1_000_000, 1),
                "utilization": round(max(0.0, min(1.0, vm / material.yield_mpa)), 3),
            }
        )

    displacements = []
    for node in mesh.nodes:
        ux, uy, uz = displacement[node["id"] * 3 : node["id"] * 3 + 3]
        displacements.append(
            {
                "id": node["id"],
                "x": round(node["x"], 3),
                "y": round(node["y"], 3),
                "z": round(node["z"], 3),
                "ux_mm": round(float(ux), 6),
                "uy_mm": round(float(uy), 6),
                "uz_mm": round(float(uz), 6),
                "magnitude_mm": round(float(np.linalg.norm([ux, uy, uz])), 6),
            }
        )

    loaded_node_ids = [node_id for node_id, _ in candidates]
    tip_deflection = float(np.mean([abs(displacement[node_id * 3 + 2]) for node_id in loaded_node_ids]))
    mass_g = estimate_mass_g(design)
    safety_factor = material.yield_mpa / max(max_vm, 1e-6)
    thermal_rise = 0.0
    score = max(0.0, min(1.0, 0.38 * min(1.0, max(0.0, (safety_factor - 0.8) / 2.2)) + 0.28 * min(1.0, max(0.0, 1 - tip_deflection / 8)) + 0.2 * min(1.0, max(0.0, 1 - mass_g / 90)) + 0.14))

    hotspots = sorted(element_results, key=lambda item: item["utilization"], reverse=True)[:5]
    return {
        "method": "Python 3D linear tetrahedral elasticity",
        "nodes": mesh.nodes,
        "tets": mesh.tets,
        "element_results": element_results,
        "displacements": displacements,
        "max_stress_mpa": round(max_vm, 2),
        "max_strain_microstrain": round(max_strain * 1_000_000, 1),
        "tip_deflection_mm": round(tip_deflection, 3),
        "max_displacement_mm": round(max(item["magnitude_mm"] for item in displacements), 3),
        "safety_factor": round(safety_factor, 2),
        "mass_g": mass_g,
        "thermal_delta_c_proxy": thermal_rise,
        "manufacturability": 1.0,
        "score": round(score, 3),
        "force_vector_n": load_case["vector_n"],
        "load_case": load_case,
        "stress_regions": [
            {
                "label": "3D tetra element",
                "x": item["centroid"]["x"],
                "y": item["centroid"]["y"],
                "z": item["centroid"]["z"],
                "severity": item["utilization"],
            }
            for item in hotspots
        ],
        "verdict": "promising" if score > 0.72 and safety_factor >= 1.8 else "needs iteration",
        "caveat": "Coarse 3D linear tetrahedral FEA for rapid iteration. Use Gmsh + scikit-fem/FEniCSx for production certification.",
    }

