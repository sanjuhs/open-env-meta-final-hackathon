from __future__ import annotations

from typing import Any

from .cadquery_builder import build_cadquery_artifact
from .models import Design, Feature, Hole, ToolAction
from .solver3d import solve_3d_linear_elasticity


def _feature_family(design: Design) -> str:
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
    if feature_types & {"generic_panel", "support_tube", "curved_tube", "flat_foot", "armrest", "headrest"}:
        return "freeform_object"
    return "bracket"


def _design_bounds(design: Design) -> dict[str, float]:
    xs = [0.0, design.base_length_mm, design.load_point_x_mm]
    ys = [-design.base_width_mm / 2, design.base_width_mm / 2, design.load_point_y_mm]
    zs = [0.0, design.base_thickness_mm]
    for feature in design.features:
        xs.extend([feature.x, feature.x2])
        ys.extend([feature.y, feature.y2])
        zs.extend([feature.height, feature.radius])
    return {
        "min_x": round(min(xs), 3),
        "max_x": round(max(xs), 3),
        "min_y": round(min(ys), 3),
        "max_y": round(max(ys), 3),
        "min_z": 0.0,
        "max_z": round(max(zs), 3),
    }


def design_family_template(family: str) -> Design:
    if family.startswith("blank_"):
        design = design_family_template(family.removeprefix("blank_"))
        design.title = "Blank " + design.title
        design.rationale = "Initialized as a blank family envelope; later tool calls add visible CAD features."
        design.features = []
        return design

    if family == "wall_hook":
        return Design(
            title="Wall-mounted J hook for 120 N hanging load",
            rationale="A compact wall plate carries two mounting bolts while a thick J-shaped hook tube carries the hanging load at its curled tip.",
            material="aluminum_6061",
            load_newtons=120,
            load_point_x_mm=62,
            load_point_y_mm=0,
            base_length_mm=74,
            base_width_mm=54,
            base_thickness_mm=6,
            fixed_holes=[Hole(x=10, y=-15, radius=3), Hole(x=10, y=15, radius=3)],
            features=[
                Feature(type="hook_curve", x=12, y=0, x2=68, y2=0, width=8, height=34, radius=10, note="round J hook tube"),
                Feature(type="boss", x=62, y=0, height=1, radius=4, note="hook lip/load contact proxy"),
            ],
            expected_failure_mode="Bending at hook root and mounting-hole bearing stress.",
            action_plan=["Create wall mounting plate", "Extrude curved hook tube", "Thicken root boss", "Run FEA proxy", "Commit hook geometry"],
        )

    if family == "torque_clamp":
        return Design(
            title="Split clamp fixture for 120 Nm shaft torque",
            rationale="Two jaws wrap a shaft proxy while a fixed root resists torque through a compact shear path.",
            material="aluminum_6061",
            load_newtons=120,
            load_point_x_mm=68,
            load_point_y_mm=0,
            base_length_mm=92,
            base_width_mm=58,
            base_thickness_mm=8,
            fixed_holes=[Hole(x=12, y=-18, radius=3), Hole(x=12, y=18, radius=3)],
            features=[
                Feature(type="clamp_jaw", x=34, y=-18, x2=78, y2=-18, width=10, height=18, radius=9, note="lower clamp jaw"),
                Feature(type="clamp_jaw", x=34, y=18, x2=78, y2=18, width=10, height=18, radius=9, note="upper clamp jaw"),
                Feature(type="boss", x=66, y=0, height=12, radius=12, note="shaft torque proxy"),
            ],
            expected_failure_mode="Jaw bending and root shear under torque proxy load.",
            action_plan=["Create split clamp jaws", "Place shaft proxy", "Add fixed root holes", "Run torque proxy FEA", "Commit clamp"],
        )

    if family == "motor_stator":
        return Design(
            title="12-slot axial motor stator concept",
            rationale="A circular stator ring with twelve teeth gives a recognizable motor design that can later connect to electromagnetic and thermal solvers.",
            material="steel_1018",
            load_newtons=80,
            load_point_x_mm=52,
            load_point_y_mm=0,
            base_length_mm=96,
            base_width_mm=96,
            base_thickness_mm=8,
            fixed_holes=[],
            features=[
                Feature(type="stator_ring", x=48, y=0, width=14, height=8, radius=34, note="lamination ring"),
                Feature(type="stator_tooth", x=48, y=0, width=9, height=18, radius=12, note="12 radial teeth"),
                Feature(type="boss", x=48, y=0, height=8, radius=6, note="center shaft/load proxy"),
            ],
            expected_failure_mode="Thermal expansion and tooth/root stress are future solver targets.",
            action_plan=["Create stator ring", "Add radial teeth", "Add center shaft proxy", "Run structural proxy", "Commit stator"],
        )

    if family == "chair":
        return Design(
            title="Simple full chair with backrest",
            rationale="A rectangular seat panel, four splayed legs, crossbars, and a backrest give a simple recognizable chair for load and deflection tests.",
            material="aluminum_6061",
            load_newtons=700,
            load_point_x_mm=45,
            load_point_y_mm=0,
            base_length_mm=90,
            base_width_mm=70,
            base_thickness_mm=6,
            fixed_holes=[],
            features=[
                Feature(type="seat_panel", x=45, y=0, width=90, height=6, radius=0, note="seat panel"),
                Feature(type="chair_leg", x=14, y=-24, x2=6, y2=-32, width=6, height=55, radius=0, note="front left leg"),
                Feature(type="chair_leg", x=76, y=-24, x2=84, y2=-32, width=6, height=55, radius=0, note="front right leg"),
                Feature(type="chair_leg", x=14, y=24, x2=6, y2=32, width=6, height=55, radius=0, note="rear left leg"),
                Feature(type="chair_leg", x=76, y=24, x2=84, y2=32, width=6, height=55, radius=0, note="rear right leg"),
                Feature(type="chair_back", x=45, y=31, width=84, height=44, radius=0, note="upright backrest panel"),
                Feature(type="chair_crossbar", x=45, y=-30, width=84, height=4, radius=0, note="front leg crossbar"),
            ],
            expected_failure_mode="Leg buckling and seat deflection under distributed downward load.",
            action_plan=["Create seat", "Add four legs", "Add backrest", "Apply distributed load proxy", "Run structural proxy", "Commit chair"],
        )

    if family == "table":
        return Design(
            title="Small freeform table",
            rationale="A tabletop plus individually added legs and stretchers forms a table from primitive CAD features.",
            material="aluminum_6061",
            load_newtons=500,
            load_point_x_mm=50,
            load_point_y_mm=0,
            base_length_mm=100,
            base_width_mm=70,
            base_thickness_mm=6,
            fixed_holes=[],
            features=[
                Feature(type="tabletop", x=50, y=0, width=100, height=6, radius=4, note="small tabletop panel"),
                Feature(type="table_leg", x=12, y=-28, width=6, height=48, radius=3, note="table leg"),
                Feature(type="table_leg", x=88, y=-28, width=6, height=48, radius=3, note="table leg"),
                Feature(type="table_leg", x=12, y=28, width=6, height=48, radius=3, note="table leg"),
                Feature(type="table_leg", x=88, y=28, width=6, height=48, radius=3, note="table leg"),
            ],
            expected_failure_mode="Tabletop bending and leg buckling under downward load.",
            action_plan=["Create tabletop", "Add requested legs", "Add stretchers", "Apply distributed load proxy", "Run structural proxy"],
        )

    if family == "freeform_object":
        return Design(
            title="Freeform primitive CAD object",
            rationale="A blank primitive grammar object; the agent composes panels, tubes, curves, feet, and decorative elements from the prompt.",
            material="aluminum_6061",
            load_newtons=120,
            load_point_x_mm=50,
            load_point_y_mm=0,
            base_length_mm=100,
            base_width_mm=70,
            base_thickness_mm=6,
            fixed_holes=[],
            features=[],
            expected_failure_mode="Depends on primitive layout and load path.",
            action_plan=["Compose primitive CAD features", "Apply load", "Run FEA", "Iterate"],
        )

    return Design(
        title=f"{family.replace('_', ' ').title()}",
        rationale="Initialized from a ribbed cantilever design family template.",
        fixed_holes=[Hole(x=12, y=-13, radius=3), Hole(x=12, y=13, radius=3)],
        features=[
            Feature(type="boss", x=90, y=0, height=7, radius=6, note="default load boss"),
        ],
    )


def apply_action(design: Design | None, action: ToolAction, prompt: str = "") -> tuple[Design | None, dict[str, Any]]:
    """Apply one agent tool action to the parametric design state."""

    if action.tool == "create_design_family":
        family = action.params.get("family", "ribbed_cantilever_bracket")
        design = design_family_template(str(family))
        prompt_text = prompt.lower()
        if "chair" in str(family) and (
            "curv" in prompt_text
            or "round" in prompt_text
            or "organic" in prompt_text
            or "sweep" in prompt_text
            or "arched" in prompt_text
            or "bent" in prompt_text
            or " flowing" in prompt_text
            or prompt_text.strip().startswith("flow ")
        ):
            design.title = "Blank curvy full chair with arched backrest"
            design.rationale = "Initialized as a curvy chair envelope; later tools add rounded seat, splayed tubular legs, curved crossbars, and an arched backrest."
        return design, {"valid": True, "message": f"Created design family {family}."}

    if design is None:
        return design, {"valid": False, "error": f"Tool {action.tool} requires an active design."}

    if action.tool == "set_material":
        design.material = action.params.get("material", design.material)
        return design, {"valid": True, "changed_parameters": ["material"]}

    if action.tool == "set_envelope":
        for key, attr in [("length_mm", "base_length_mm"), ("width_mm", "base_width_mm"), ("thickness_mm", "base_thickness_mm")]:
            if key in action.params:
                setattr(design, attr, float(action.params[key]))
        return design, {"valid": True, "changed_parameters": ["base_length_mm", "base_width_mm", "base_thickness_mm"]}

    if action.tool == "set_load":
        vector = action.params.get("vector_n", [0, 0, -design.load_newtons])
        point = action.params.get("point_mm") or action.params.get("point") or [design.load_point_x_mm, design.load_point_y_mm, design.base_thickness_mm]
        design.load_newtons = abs(float(vector[2] if len(vector) > 2 else vector[-1]))
        design.load_point_x_mm = float(point[0])
        design.load_point_y_mm = float(point[1])
        return design, {"valid": True, "changed_parameters": ["load_newtons", "load_point_x_mm", "load_point_y_mm"]}

    if action.tool == "add_mount_hole":
        center = action.params.get("center", [action.params.get("x", 12), action.params.get("y", 0)])
        design.fixed_holes.append(Hole(x=float(center[0]), y=float(center[1]), radius=float(action.params.get("radius_mm", action.params.get("radius", 3)))))
        return design, {"valid": True, "changed_parameters": ["fixed_holes"]}

    if action.tool == "add_rib":
        start = action.params.get("start", [action.params.get("x", 10), action.params.get("y", 0), 0])
        end = action.params.get("end", [action.params.get("x2", 90), action.params.get("y2", 0), 10])
        design.features.append(
            Feature(
                type="rib",
                x=float(start[0]),
                y=float(start[1]),
                x2=float(end[0]),
                y2=float(end[1]),
                width=float(action.params.get("width_mm", action.params.get("width", 4))),
                height=float(action.params.get("height_mm", action.params.get("height", max(end[2] if len(end) > 2 else 12, 1)))),
                note=str(action.params.get("id", "agent rib")),
            )
        )
        return design, {"valid": True, "changed_parameters": ["features"]}

    if action.tool == "add_lightening_hole":
        center = action.params.get("center", [action.params.get("x", 50), action.params.get("y", 0), 0])
        design.features.append(
            Feature(
                type="lightening_hole",
                x=float(center[0]),
                y=float(center[1]),
                radius=float(action.params.get("radius_mm", action.params.get("radius", 4))),
                note=str(action.params.get("id", "agent lightening hole")),
            )
        )
        return design, {"valid": True, "changed_parameters": ["features"]}

    if action.tool == "add_feature":
        params = dict(action.params)
        feature_type = str(params.pop("type"))
        design.features.append(
            Feature(
                type=feature_type,  # type: ignore[arg-type]
                x=float(params.get("x", 0)),
                y=float(params.get("y", 0)),
                x2=float(params.get("x2", 0)),
                y2=float(params.get("y2", 0)),
                width=float(params.get("width", params.get("width_mm", 0))),
                height=float(params.get("height", params.get("height_mm", 0))),
                radius=float(params.get("radius", params.get("radius_mm", 0))),
                note=str(params.get("note", params.get("id", feature_type))),
            )
        )
        return design, {"valid": True, "changed_parameters": ["features"], "added_feature": feature_type}

    if action.tool == "observe_design":
        return design, {
            "valid": True,
            "observation": {
                "family": _feature_family(design),
                "feature_count": len(design.features),
                "fixed_hole_count": len(design.fixed_holes),
                "bounds_mm": _design_bounds(design),
                "load_point_mm": [design.load_point_x_mm, design.load_point_y_mm, design.base_thickness_mm],
                "material": design.material,
            },
        }

    if action.tool == "measure_clearance":
        bounds = _design_bounds(design)
        return design, {
            "valid": True,
            "measurement": {
                "bounds_mm": bounds,
                "envelope_length_mm": round(bounds["max_x"] - bounds["min_x"], 3),
                "envelope_width_mm": round(bounds["max_y"] - bounds["min_y"], 3),
                "feature_count": len(design.features),
                "load_is_inside_nominal_envelope": 0 <= design.load_point_x_mm <= design.base_length_mm
                and -design.base_width_mm / 2 <= design.load_point_y_mm <= design.base_width_mm / 2,
            },
        }

    if action.tool == "check_constraints":
        family = _feature_family(design)
        missing: list[str] = []
        if family == "chair":
            for required in ["seat_panel", "chair_leg", "chair_back"]:
                if not any(feature.type == required for feature in design.features):
                    missing.append(required)
            if sum(1 for feature in design.features if feature.type == "chair_leg") < 4:
                missing.append("four_chair_legs")
        if family == "torque_clamp" and sum(1 for feature in design.features if feature.type == "clamp_jaw") < 2:
            missing.append("two_split_clamp_jaws")
        if family == "motor_stator" and not any(feature.type == "stator_tooth" for feature in design.features):
            missing.append("radial_stator_teeth")
        return design, {"valid": True, "family": family, "constraint_status": "pass" if not missing else "needs_repair", "missing": missing}

    if action.tool == "visual_snapshot":
        return design, {
            "valid": True,
            "snapshot": {
                "view": action.params.get("view", "isometric"),
                "camera": action.params.get("camera", "auto"),
                "note": "Renderer should inspect this view for identity, load contact, and disconnected geometry.",
                "family": _feature_family(design),
                "bounds_mm": _design_bounds(design),
            },
        }

    if action.tool == "critique_geometry":
        family = _feature_family(design)
        notes = []
        if family == "torque_clamp":
            notes.append("Blue cylinder is shaft/load proxy; green arcs and jaws should visibly wrap it with a small split gap.")
        if family == "chair":
            notes.append("Seat, four legs, crossbars, and backrest should be visible from isometric and side views.")
        if family == "motor_stator":
            notes.append("Stator should read as a flat toothed annulus with visible center bore and radial slots.")
        if family == "wall_hook":
            notes.append("Hook tip must be the load contact; load arrow should terminate on the curved hook.")
        return design, {"valid": True, "critique": notes or ["Generic bracket load path should remain connected."]}

    if action.tool == "run_fea":
        return design, {"valid": True, "simulation": solve_3d_linear_elasticity(design, prompt)}

    if action.tool == "export_cadquery":
        return design, build_cadquery_artifact(design)

    if action.tool == "commit_design":
        return design, {"valid": True, "committed": True, "simulation": solve_3d_linear_elasticity(design, prompt)}

    return design, {"valid": False, "error": f"Unknown tool: {action.tool}"}


def run_actions(actions: list[ToolAction], prompt: str = "", initial_design: Design | None = None) -> dict[str, Any]:
    design: Design | None = initial_design
    trace = []
    last_result: dict[str, Any] = {}
    for idx, action in enumerate(actions, start=1):
        design, result = apply_action(design, action, prompt)
        last_result = result
        trace.append({"step": idx, "action": action.model_dump(), "result": result, "design": design.model_dump() if design else None})
        if result.get("committed"):
            break
    return {"design": design.model_dump() if design else None, "last_result": last_result, "trace": trace}
