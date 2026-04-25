from __future__ import annotations

from dataclasses import dataclass

from .models import Design


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


@dataclass
class Mesh:
    nodes: list[dict]
    tets: list[list[int]]
    length: float
    width: float
    height: float


def point_in_feature_volume(point: dict, design: Design) -> bool:
    x, y, z = point["x"], point["y"], point["z"]
    length = design.base_length_mm
    half_width = design.base_width_mm / 2
    thickness = design.base_thickness_mm
    solid = 0 <= x <= length and -half_width <= y <= half_width and 0 <= z <= thickness

    if solid and z <= thickness:
        for hole in design.fixed_holes:
            if ((x - hole.x) ** 2 + (y - hole.y) ** 2) ** 0.5 < hole.radius:
                solid = False
        for feature in design.features:
            if feature.type == "lightening_hole" and ((x - feature.x) ** 2 + (y - feature.y) ** 2) ** 0.5 < feature.radius:
                solid = False

    for feature in design.features:
        if feature.type == "boss":
            radius = clamp(feature.radius, 1, 20)
            height = clamp(feature.height, 1, 40)
            if ((x - feature.x) ** 2 + (y - feature.y) ** 2) ** 0.5 <= radius and thickness <= z <= thickness + height:
                solid = True

        if feature.type == "rib":
            ax, ay, bx, by = feature.x, feature.y, feature.x2, feature.y2
            vx, vy = bx - ax, by - ay
            length_sq = max(vx * vx + vy * vy, 1)
            t = clamp(((x - ax) * vx + (y - ay) * vy) / length_sq, 0, 1)
            px, py = ax + t * vx, ay + t * vy
            rib_height = clamp(feature.height, 1, 60)
            if ((x - px) ** 2 + (y - py) ** 2) ** 0.5 <= max(feature.width, 1) / 2 and thickness <= z <= thickness + rib_height:
                solid = True

    return solid


def build_structured_tet_mesh(design: Design, nx: int = 7, ny: int = 5, nz: int = 5) -> Mesh:
    length = clamp(design.base_length_mm, 30, 240)
    width = clamp(design.base_width_mm, 10, 120)
    thickness = clamp(design.base_thickness_mm, 1, 30)
    max_feature_height = max(
        [feature.height for feature in design.features if feature.type in {"rib", "boss"}] or [0]
    )
    height = max(thickness + max_feature_height, thickness * 2)
    nodes: list[dict] = []
    node_id: dict[tuple[int, int, int], int] = {}
    tets: list[list[int]] = []

    def grid_point(i: int, j: int, k: int) -> dict:
        return {
            "x": length * i / nx,
            "y": -width / 2 + width * j / ny,
            "z": height * k / nz,
        }

    def add_node(i: int, j: int, k: int) -> int:
        key = (i, j, k)
        if key in node_id:
            return node_id[key]
        idx = len(nodes)
        nodes.append({"id": idx, **grid_point(i, j, k)})
        node_id[key] = idx
        return idx

    tet_pattern = [
        [0, 1, 3, 7],
        [0, 3, 2, 7],
        [0, 2, 6, 7],
        [0, 6, 4, 7],
        [0, 4, 5, 7],
        [0, 5, 1, 7],
    ]

    for i in range(nx):
        for j in range(ny):
            for k in range(nz):
                p0 = grid_point(i, j, k)
                p1 = grid_point(i + 1, j + 1, k + 1)
                center = {"x": (p0["x"] + p1["x"]) / 2, "y": (p0["y"] + p1["y"]) / 2, "z": (p0["z"] + p1["z"]) / 2}
                if not point_in_feature_volume(center, design):
                    continue
                corners = [
                    add_node(i, j, k),
                    add_node(i + 1, j, k),
                    add_node(i, j + 1, k),
                    add_node(i + 1, j + 1, k),
                    add_node(i, j, k + 1),
                    add_node(i + 1, j, k + 1),
                    add_node(i, j + 1, k + 1),
                    add_node(i + 1, j + 1, k + 1),
                ]
                for tet in tet_pattern:
                    tets.append([corners[idx] for idx in tet])

    return Mesh(nodes=nodes, tets=tets, length=length, width=width, height=height)

