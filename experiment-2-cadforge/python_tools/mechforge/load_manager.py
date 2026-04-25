from __future__ import annotations

import re
from typing import Any

from .models import Design


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def infer_load_case(prompt: str, design: Design) -> dict[str, Any]:
    """Resolve natural-language load details to simulation boundary data.

    The LLM can propose load location through the design fields. This manager
    resolves that proposal into a concrete point/region and records assumptions.
    If the prompt explicitly says torque, cyclic, impact, chair, motor, or fixture,
    those details alter the load case.
    """

    text = (prompt or "").lower()
    load_x = clamp(abs(design.load_point_x_mm), 5, design.base_length_mm)
    load_y = clamp(design.load_point_y_mm, -design.base_width_mm / 2, design.base_width_mm / 2)
    nearest_boss = min(
        [feature for feature in design.features if feature.type == "boss"],
        key=lambda feature: (feature.x - load_x) ** 2 + (feature.y - load_y) ** 2,
        default=None,
    )
    load_z = design.base_thickness_mm
    load_region_hint = "tip_boss"
    if nearest_boss is not None:
        load_x = nearest_boss.x
        load_y = nearest_boss.y
        load_z = design.base_thickness_mm + max(nearest_boss.height, 1)
        load_region_hint = "top_of_nearest_load_boss"
    factor = 3.0 if "impact" in text else 1.5 if ("cyclic" in text or "fatigue" in text) else 1.0

    torque_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:n\s*[-*]?\s*m|nm|newton\s*meter)", text)
    if torque_match:
        torque_nm = float(torque_match.group(1))
        equivalent_force = torque_nm * 1000 / max(load_x, 1)
        return {
            "type": "torque_as_force_couple_proxy",
            "effective_load_n": equivalent_force * factor,
            "nominal_load_n": equivalent_force,
            "factor": factor,
            "load_point": [load_x, load_y, load_z],
            "vector_n": [0, 0, -round(equivalent_force * factor, 4)],
            "fixed_region": "left_face",
            "load_region": "shaft_proxy_or_" + load_region_hint,
            "note": f"{torque_nm} Nm converted to equivalent force at {load_x:.1f} mm lever arm.",
        }

    if "chair" in text or "seat" in text:
        load_type = "distributed_downward_proxy"
        load_region = "seat_surface_proxy"
    elif "motor" in text:
        load_type = "motor_mount_tip_or_boss_load"
        load_region = "motor_boss_or_tip"
    else:
        load_type = "cantilever_tip_load"
        load_region = load_region_hint

    return {
        "type": load_type,
        "effective_load_n": abs(design.load_newtons) * factor,
        "nominal_load_n": abs(design.load_newtons),
        "factor": factor,
        "load_point": [load_x, load_y, load_z],
        "vector_n": [0, 0, -round(abs(design.load_newtons) * factor, 4)],
        "fixed_region": "left_face",
        "load_region": load_region,
        "note": "Defaulted to fixed left face and downward load at the model-proposed tip/load point.",
    }
