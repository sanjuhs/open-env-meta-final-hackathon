from __future__ import annotations

import math
import re
import time
from pathlib import Path
from typing import Any

from .models import Design


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")[:64] or "design"


def _family(design: Design) -> str:
    feature_types = {feature.type for feature in design.features}
    if "tabletop" in feature_types:
        return "table"
    if "stator_ring" in feature_types:
        return "motor_stator"
    if "seat_panel" in feature_types:
        return "chair"
    if "clamp_jaw" in feature_types:
        return "torque_clamp"
    if "hook_curve" in feature_types:
        return "wall_hook"
    if feature_types & {"generic_panel", "support_tube", "curved_tube", "flat_foot", "armrest", "headrest", "table_leg"}:
        return "freeform_object"
    return "bracket"


def _box(cq: Any, x: float, y: float, z: float, cx: float, cy: float, cz: float):
    return cq.Workplane("XY").box(x, y, z).translate((cx, cy, cz))


def _cylinder_x(cq: Any, radius: float, length: float, cx: float, cy: float, cz: float):
    return cq.Workplane("YZ").circle(radius).extrude(length).translate((cx - length / 2, cy, cz))


def _cylinder_y(cq: Any, radius: float, length: float, cx: float, cy: float, cz: float):
    return cq.Workplane("XZ").circle(radius).extrude(length).translate((cx, cy - length / 2, cz))


def _cylinder_z(cq: Any, radius: float, height: float, cx: float, cy: float, cz: float):
    return cq.Workplane("XY").circle(radius).extrude(height).translate((cx, cy, cz - height / 2))


def _merge(parts: list[Any]):
    body = parts[0]
    for part in parts[1:]:
        body = body.union(part)
    return body


def _box_between_xy(cq: Any, x1: float, y1: float, x2: float, y2: float, width: float, height: float, z: float):
    length = max(math.hypot(x2 - x1, y2 - y1), 1)
    part = _box(cq, length, max(width, 1), max(height, 1), (x1 + x2) / 2, (y1 + y2) / 2, z)
    return part.rotate(((x1 + x2) / 2, (y1 + y2) / 2, z), ((x1 + x2) / 2, (y1 + y2) / 2, z + 1), math.degrees(math.atan2(y2 - y1, x2 - x1)))


def _primitive_part(cq: Any, design: Design, feature: Any, ops: list[dict[str, Any]]):
    if feature.type in {"tabletop", "generic_panel"}:
        depth = max(design.base_width_mm, 18)
        z = 52 if feature.type == "tabletop" else max(feature.height, 4) / 2
        ops.append({"op": "box_extrude", "part": feature.type, "center_xy_mm": [feature.x, feature.y], "size_mm": [max(feature.width, 24), depth, max(feature.height, 4)]})
        return _box(cq, max(feature.width, 24), depth, max(feature.height, 4), feature.x or design.base_length_mm / 2, feature.y, z)
    if feature.type == "table_leg":
        height = max(feature.height, 24)
        radius = max(feature.radius, feature.width / 2, 2.4)
        ops.append({"op": "cylinder_extrude", "part": "table_leg", "center_xy_mm": [feature.x, feature.y], "height_mm": height, "radius_mm": radius})
        return _cylinder_z(cq, radius, height, feature.x, feature.y, height / 2)
    if feature.type == "support_tube":
        z = max(feature.height, 8)
        ops.append({"op": "box_between", "part": "support_tube", "from_xy_mm": [feature.x, feature.y], "to_xy_mm": [feature.x2, feature.y2]})
        return _box_between_xy(cq, feature.x, feature.y, feature.x2, feature.y2, max(feature.width, feature.radius * 2, 3), max(feature.radius * 2, 3), z)
    if feature.type == "curved_tube":
        z = max(feature.height, 18)
        ops.append({"op": "segmented_curve_proxy", "part": "curved_tube", "from_xy_mm": [feature.x, feature.y], "to_xy_mm": [feature.x2, feature.y2]})
        return _box_between_xy(cq, feature.x, feature.y, feature.x2, feature.y2, max(feature.width, feature.radius * 2, 3), max(feature.radius * 2, 3), z)
    if feature.type == "flat_foot":
        ops.append({"op": "box_extrude", "part": "flat_foot", "center_xy_mm": [feature.x, feature.y]})
        return _box(cq, max(feature.width, 16), max(feature.radius * 2.4, 8), max(feature.height, 2.5), feature.x, feature.y, max(feature.height, 2.5) / 2)
    return None


def _build_stator(cq: Any, design: Design, ops: list[dict[str, Any]]):
    ring = next((item for item in design.features if item.type == "stator_ring"), None)
    tooth = next((item for item in design.features if item.type == "stator_tooth"), None)
    cx = ring.x if ring else design.base_length_mm / 2
    cy = ring.y if ring else 0
    outer = ring.radius + ring.width if ring else 46
    inner = max((tooth.radius if tooth else 18), 12)
    height = max(ring.height if ring else design.base_thickness_mm, 4)

    body = cq.Workplane("XY").circle(outer).circle(inner).extrude(height)
    ops.append({"op": "sketch_annulus", "outer_radius_mm": outer, "inner_radius_mm": inner, "height_mm": height})
    tooth_count = 12
    for idx in range(tooth_count):
        angle = 360 * idx / tooth_count
        length = max((tooth.height if tooth else 18), 8)
        width = max((tooth.width if tooth else 8), 3)
        radial = inner + length / 2
        local = cq.Workplane("XY").box(length, width, height).translate((radial, 0, height / 2))
        local = local.rotate((0, 0, 0), (0, 0, 1), angle).translate((cx, cy, 0))
        body = body.union(local)
        ops.append({"op": "union_radial_tooth", "index": idx + 1, "angle_deg": angle, "length_mm": length, "width_mm": width})
    body = body.translate((cx, cy, 0))
    ops.append({"op": "export_ready_body", "family": "motor_stator", "note": "flat annular stator, not a torus placeholder"})
    return body


def _build_chair(cq: Any, design: Design, ops: list[dict[str, Any]]):
    parts = []
    seat_z = 48
    parts.append(_box(cq, design.base_length_mm, design.base_width_mm, design.base_thickness_mm, design.base_length_mm / 2, 0, seat_z))
    ops.append({"op": "box_extrude", "part": "seat_panel", "size_mm": [design.base_length_mm, design.base_width_mm, design.base_thickness_mm]})
    for leg in [item for item in design.features if item.type == "chair_leg"]:
        height = max(leg.height, 35)
        parts.append(_box(cq, max(leg.width, 4), max(leg.width, 4), height, leg.x, leg.y, height / 2))
        ops.append({"op": "extrude_leg", "part": leg.note, "top_xy_mm": [leg.x, leg.y], "height_mm": height})
    parts.append(_box(cq, design.base_length_mm, 5, 42, design.base_length_mm / 2, design.base_width_mm / 2 - 3, seat_z + 22))
    parts.append(_box(cq, 5, 5, 54, 10, design.base_width_mm / 2 - 3, seat_z + 25))
    parts.append(_box(cq, 5, 5, 54, design.base_length_mm - 10, design.base_width_mm / 2 - 3, seat_z + 25))
    ops.append({"op": "add_backrest", "parts": ["back_panel", "left_back_post", "right_back_post"]})
    decorative = [item for item in design.features if item.type == "decorative_curve"]
    if decorative:
        back_y = design.base_width_mm / 2 + 0.5
        cx = design.base_length_mm / 2
        cz = seat_z + 38
        if any("flower" in item.note.lower() or "petal" in item.note.lower() for item in decorative):
            parts.append(_cylinder_y(cq, 3.2, 1.8, cx, back_y, cz))
            for idx in range(6):
                angle = math.tau * idx / 6
                px = cx + math.cos(angle) * 10
                pz = cz + math.sin(angle) * 10
                parts.append(_cylinder_y(cq, 5.5, 1.6, px, back_y, pz))
                ops.append({"op": "union_flower_petal_disc", "index": idx + 1, "center_xz_mm": [round(px, 3), round(pz, 3)]})
            parts.append(_cylinder_y(cq, 1.6, 1.6, cx - 2, back_y, seat_z + 18))
            ops.append({"op": "add_backrest_flower_pattern", "note": "decorative raised petal discs on backrest"})
        else:
            for idx, item in enumerate(decorative, start=1):
                parts.append(_cylinder_y(cq, max(item.radius, 2), 1.4, item.x or cx, back_y, seat_z + 24 + idx * 8))
                ops.append({"op": "union_decorative_curve_proxy", "index": idx, "note": item.note})
    for item in [feature for feature in design.features if feature.type in {"armrest", "headrest", "flat_foot", "support_tube", "curved_tube"}]:
        primitive = _primitive_part(cq, design, item, ops)
        if primitive is not None:
            parts.append(primitive)
    ops.append({"op": "export_ready_body", "family": "chair"})
    return _merge(parts)


def _build_table(cq: Any, design: Design, ops: list[dict[str, Any]]):
    parts = []
    for feature in design.features:
        primitive = _primitive_part(cq, design, feature, ops)
        if primitive is not None:
            parts.append(primitive)
    if not parts:
        parts.append(_box(cq, design.base_length_mm, design.base_width_mm, design.base_thickness_mm, design.base_length_mm / 2, 0, 52))
        ops.append({"op": "box_extrude", "part": "fallback_tabletop"})
    ops.append({"op": "export_ready_body", "family": "table"})
    return _merge(parts)


def _build_freeform(cq: Any, design: Design, ops: list[dict[str, Any]]):
    parts = []
    for feature in design.features:
        primitive = _primitive_part(cq, design, feature, ops)
        if primitive is not None:
            parts.append(primitive)
    if not parts:
        parts.append(_box(cq, design.base_length_mm, design.base_width_mm, design.base_thickness_mm, design.base_length_mm / 2, 0, design.base_thickness_mm / 2))
        ops.append({"op": "box_extrude", "part": "fallback_freeform_panel"})
    ops.append({"op": "export_ready_body", "family": "freeform_object"})
    return _merge(parts)


def _build_clamp(cq: Any, design: Design, ops: list[dict[str, Any]]):
    parts = [
        _box(cq, 16, design.base_width_mm, 28, 8, 0, 14),
        _cylinder_x(cq, 11, 58, 58, 0, 22),
    ]
    ops.append({"op": "box_extrude", "part": "fixed_root", "size_mm": [16, design.base_width_mm, 28]})
    ops.append({"op": "cylinder_extrude", "part": "shaft_bore_proxy", "axis": "x", "radius_mm": 11, "length_mm": 58})
    for y in [-18, 18]:
        parts.append(_box(cq, 54, 10, 15, 53, y, 22))
        ops.append({"op": "box_extrude", "part": "split_clamp_jaw", "center_y_mm": y, "size_mm": [54, 10, 15]})
    parts.append(_cylinder_x(cq, 14, 12, 82, 0, 22))
    ops.append({"op": "add_end_collar", "radius_mm": 14, "note": "visual collar for torque/load application"})
    ops.append({"op": "export_ready_body", "family": "torque_clamp"})
    return _merge(parts)


def _build_hook(cq: Any, design: Design, ops: list[dict[str, Any]]):
    wall_h = max(design.base_width_mm, 50)
    parts = [_box(cq, 8, 26, wall_h, 4, 0, wall_h / 2)]
    ops.append({"op": "box_extrude", "part": "wall_plate", "size_mm": [8, 26, wall_h]})
    tube = 4
    root_z = wall_h * 0.58
    points = [(8, root_z), (32, root_z), (52, root_z - 8), (58, root_z - 28), (44, root_z - 38), (35, root_z - 24)]
    for idx, ((x1, z1), (x2, z2)) in enumerate(zip(points, points[1:]), start=1):
        length = math.hypot(x2 - x1, z2 - z1)
        angle = math.degrees(math.atan2(z2 - z1, x2 - x1))
        segment = _cylinder_x(cq, tube, length, (x1 + x2) / 2, 0, (z1 + z2) / 2)
        segment = segment.rotate(((x1 + x2) / 2, 0, (z1 + z2) / 2), ((x1 + x2) / 2, 1, (z1 + z2) / 2), -angle)
        parts.append(segment)
        ops.append({"op": "sweep_hook_segment", "index": idx, "from_xz_mm": [x1, z1], "to_xz_mm": [x2, z2], "tube_radius_mm": tube})
    ops.append({"op": "export_ready_body", "family": "wall_hook"})
    return _merge(parts)


def _build_bracket(cq: Any, design: Design, ops: list[dict[str, Any]]):
    body = _box(cq, design.base_length_mm, design.base_width_mm, design.base_thickness_mm, design.base_length_mm / 2, 0, design.base_thickness_mm / 2)
    ops.append({"op": "box_extrude", "part": "base_plate", "size_mm": [design.base_length_mm, design.base_width_mm, design.base_thickness_mm]})
    for feature in design.features:
        if feature.type == "rib":
            length = max(math.hypot(feature.x2 - feature.x, feature.y2 - feature.y), 1)
            rib = _box(cq, length, max(feature.width, 1), max(feature.height, 1), (feature.x + feature.x2) / 2, (feature.y + feature.y2) / 2, design.base_thickness_mm + max(feature.height, 1) / 2)
            rib = rib.rotate((feature.x, feature.y, design.base_thickness_mm), (feature.x, feature.y, design.base_thickness_mm + 1), math.degrees(math.atan2(feature.y2 - feature.y, feature.x2 - feature.x)))
            body = body.union(rib)
            ops.append({"op": "union_rib", "from_xy_mm": [feature.x, feature.y], "to_xy_mm": [feature.x2, feature.y2]})
        if feature.type == "boss":
            body = body.union(_cylinder_z(cq, max(feature.radius, 1), max(feature.height, 1), feature.x, feature.y, design.base_thickness_mm + max(feature.height, 1) / 2))
            ops.append({"op": "union_boss", "center_xy_mm": [feature.x, feature.y], "radius_mm": feature.radius})
    ops.append({"op": "export_ready_body", "family": "bracket"})
    return body


def build_cadquery_artifact(design: Design, output_root: str | Path = "runs") -> dict[str, Any]:
    """Build an actual CadQuery body and export manufacturable artifacts."""

    operations: list[dict[str, Any]] = []
    family = _family(design)
    output_dir = Path(output_root) / f"{int(time.time() * 1000)}_{_slug(design.title)}"
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        import cadquery as cq

        builders = {
            "motor_stator": _build_stator,
            "chair": _build_chair,
            "table": _build_table,
            "freeform_object": _build_freeform,
            "torque_clamp": _build_clamp,
            "wall_hook": _build_hook,
            "bracket": _build_bracket,
        }
        body = builders[family](cq, design, operations)
        step_path = output_dir / "design.step"
        stl_path = output_dir / "design.stl"
        cq.exporters.export(body, str(step_path))
        cq.exporters.export(body, str(stl_path))
        return {
            "valid": True,
            "family": family,
            "engine": "cadquery",
            "operations": operations,
            "step_path": str(step_path),
            "stl_path": str(stl_path),
        }
    except Exception as exc:  # pragma: no cover - keeps agent loop alive if CAD kernel fails.
        operations.append({"op": "cadquery_error", "error": str(exc)})
        return {
            "valid": False,
            "family": family,
            "engine": "cadquery",
            "operations": operations,
            "error": str(exc),
        }
