# Document 9: CAD RLVE For Structural Household Mechanical Parts

Date: 2026-04-25

## Core Realization

Current AI is not reliably bad at "imagining 3D objects."

It is bad at:

- making valid CAD,
- making the right geometric edit at the right time,
- preserving design intent,
- keeping features clean and editable,
- avoiding broken booleans and non-manifold geometry,
- producing parts that survive physical checks.

That is exactly why a CAD-focused RLVE environment is interesting.

The product should not be:

> Generate a cool-looking mesh.

The product should be:

> Train an agent to create and revise parametric CAD code until the part is valid, editable, manufacturable, and structurally correct.

This is a stronger and more general version of MechForge. MechForge becomes the first structural benchmark suite inside a larger CAD-agent training environment.

## Name

Working names:

- **CADForge**
- **MechForge CAD**
- **OpenCAD Gym**
- **ParametricCAD RLVE**
- **FeatureForge**

Best current framing:

> **CADForge: an RLVE environment where agents learn reliable parametric CAD creation and editing for functional mechanical parts.**

## Why Code-CAD Is The Right Medium

The agent should write or edit code-CAD, not arbitrary meshes.

Good backend candidates:

- OpenSCAD-style constructive solid geometry,
- CadQuery,
- build123d,
- a constrained internal DSL that compiles to CadQuery/OpenSCAD/STEP/STL.

The user said "OpenCADD"; if this means OpenSCAD or a similar code-CAD tool, the important idea is the same:

> CAD should be represented as executable, inspectable, deterministic code.

That gives the environment objective checks:

- Did the code run?
- Did the model build?
- Did operations apply in the right order?
- Is the feature tree clean?
- Are dimensions parameterized?
- Can a downstream edit change the part without breaking it?
- Does export work?
- Is the final geometry watertight and manifold?

This is much better for RLVE than asking the model to emit a raw mesh.

## Target Domain

Start with structural household and mechanical parts:

- wall hook,
- shelf bracket,
- cantilever support,
- chair seat support,
- stool leg joint,
- phone stand,
- desk clamp,
- handle,
- hinge plate,
- simple enclosure mount,
- motor mount,
- cable guide,
- pegboard fixture,
- plant hanger,
- small appliance bracket.

These are ideal because they are:

- easy to understand visually,
- mechanically meaningful,
- structurally verifiable,
- small enough to simulate quickly,
- familiar enough that judges understand failures,
- broad enough to expose many CAD operations.

## Agent Task

The agent receives a physical design brief:

```text
Design a wall hook that mounts with two screws, fits inside an 80 mm x 60 mm x 45 mm envelope,
holds a 5 kg load with safety factor above 2, is printable without support where possible,
and has rounded edges for safe household use.
```

The agent must produce code-CAD:

```python
part = create_base_plate(width=60, height=80, thickness=6)
part = add_mounting_holes(part, spacing=48, diameter=5)
part = add_hook_arm(part, length=42, thickness=8, root_fillet=6)
part = add_tip_lip(part, height=8, radius=4)
part = add_ribs(part, count=2, thickness=4)
part = fillet_edges(part, radius=2)
```

Then the environment builds, validates, simulates, and scores the result.

## Action Space

Use incremental tool calls rather than one giant CAD program.

Sketch and feature tools:

```json
{"tool": "create_sketch", "plane": "XY", "id": "base_profile"}
{"tool": "add_rectangle", "sketch": "base_profile", "width_mm": 60, "height_mm": 80}
{"tool": "constrain_symmetric", "sketch": "base_profile", "axis": "Y"}
{"tool": "extrude", "sketch": "base_profile", "distance_mm": 6, "id": "base_plate"}
{"tool": "add_hole", "target": "base_plate", "center_mm": [0, 24], "diameter_mm": 5}
{"tool": "add_hole", "target": "base_plate", "center_mm": [0, -24], "diameter_mm": 5}
{"tool": "add_hook_arm", "length_mm": 42, "thickness_mm": 8, "angle_deg": 12}
{"tool": "add_rib", "from": "base_plate", "to": "hook_arm", "thickness_mm": 4}
{"tool": "fillet", "target": "root_edges", "radius_mm": 5}
```

Validation tools:

```json
{"tool": "build_cad"}
{"tool": "check_feature_tree"}
{"tool": "check_constraints"}
{"tool": "check_manifold"}
{"tool": "check_watertight"}
{"tool": "check_min_wall_thickness", "min_mm": 2.5}
{"tool": "check_overhangs", "process": "fdm_3d_printing", "max_angle_deg": 45}
{"tool": "export_artifacts", "formats": ["step", "stl", "json", "png"]}
```

Simulation tools:

```json
{"tool": "set_material", "material": "pla"}
{"tool": "set_fixed_region", "region": "mounting_hole_faces"}
{"tool": "set_force", "region": "hook_tip", "vector_n": [0, 0, -50]}
{"tool": "mesh_geometry", "target_size_mm": 3}
{"tool": "run_structural_check", "physics": "linear_elasticity"}
{"tool": "inspect_hotspots", "field": "von_mises_stress"}
```

Revision tools:

```json
{"tool": "increase_parameter", "name": "root_fillet_mm", "delta": 1}
{"tool": "move_feature", "feature": "mount_hole_1", "delta_mm": [0, 4, 0]}
{"tool": "add_support_rib", "region": "hook_root", "thickness_mm": 3}
{"tool": "reduce_mass", "strategy": "lightening_holes_low_stress_regions"}
{"tool": "commit_design"}
```

## Reward Design

Reward should be multi-layered. The early curriculum rewards basic CAD validity; later stages reward engineering quality.

Suggested reward:

```text
valid_code_execution:        0.10
cad_build_success:           0.15
clean_feature_tree:          0.10
editability_test_passed:     0.10
manifold_watertight_mesh:    0.10
constraint_satisfaction:     0.10
manufacturability:           0.10
structural_safety:           0.15
mass_efficiency:             0.05
revision_efficiency:         0.05
```

Penalties:

```text
syntax_error:                -0.20
failed_boolean_operation:    -0.15
non_manifold_geometry:       -0.15
self_intersection:           -0.15
unparameterized_magic_values: -0.05
uneditable_feature_chain:    -0.10
unsafe_stress_or_deflection: -0.20
invalid_final_export:        -0.20
```

The important thing:

> The agent is not rewarded for a pretty model. It is rewarded for reliable CAD behavior.

## Editability Tests

This is the key differentiator.

After the agent submits a part, the environment should mutate requirements and test whether the CAD remains editable:

- increase load by 20%,
- change screw spacing,
- change material,
- change envelope,
- increase minimum wall thickness,
- require a larger fillet,
- move mounting holes,
- change manufacturing process from FDM to CNC or vice versa.

Example:

```json
{
  "edit_test": "change_mount_hole_spacing",
  "old_spacing_mm": 48,
  "new_spacing_mm": 56,
  "expected": "model_rebuilds_without_manual_rewrite"
}
```

This catches fake CAD solutions that only work once.

The trained behavior we want:

- define named parameters,
- reference parameters consistently,
- avoid brittle coordinate hacks,
- keep sketches constrained,
- isolate features cleanly,
- choose operations that survive downstream edits.

This is where AI currently fails badly, which makes it a strong RLVE target.

## Geometry Quality Checks

The environment should check:

- watertight mesh,
- no holes or gaps,
- manifold edges,
- no self-intersections,
- no zero-thickness faces,
- no tiny sliver faces,
- no duplicate coincident geometry,
- acceptable triangle quality for exported mesh,
- consistent normals,
- minimum feature size,
- minimum wall thickness,
- proper contact/union between features.

For code-CAD, this can be done after export:

```text
CAD code -> solid model -> STEP/STL -> mesh/solid validation -> reward
```

The "tight mesh" requirement should not mean the agent directly optimizes mesh triangles first. It should mean:

> The CAD-generated solid exports to a clean, watertight, simulation-ready mesh.

## Structural Verification

For MechForge, start with fast structural checks:

- cantilever beam approximation,
- plate/rib stress proxies,
- simple linear elasticity,
- later tetrahedral FEA.

Each part gets a load template:

| Part | Boundary condition | Load |
|---|---|---|
| Wall hook | screw holes fixed | downward load at hook tip |
| Shelf bracket | wall plate fixed | distributed shelf load |
| Chair support | feet fixed | downward seat load |
| Phone stand | base contact fixed | device weight and tipping check |
| Clamp | screw pad contact | clamping force and jaw bending |
| Motor mount | bolt holes fixed | radial/axial force and torque |

The environment returns feedback:

```json
{
  "build": "success",
  "geometry": {
    "watertight": true,
    "manifold": true,
    "min_wall_thickness_mm": 3.2,
    "self_intersections": 0
  },
  "feature_tree": {
    "named_parameters": 12,
    "editable": true,
    "failed_edit_tests": []
  },
  "structural": {
    "max_stress_mpa": 31.4,
    "max_displacement_mm": 1.8,
    "safety_factor": 2.4,
    "hotspots": ["hook_root"]
  },
  "reward": 0.86
}
```

## Curriculum

Stage 1: Valid code-CAD

- simple plates,
- holes,
- extrusions,
- fillets,
- no physical simulation yet.

Stage 2: Editable parametric parts

- change dimensions,
- move holes,
- alter thickness,
- regenerate cleanly.

Stage 3: Manufacturable household parts

- wall hook,
- phone stand,
- shelf bracket,
- clamp,
- hinge plate.

Stage 4: Structural MechForge

- loads,
- fixed regions,
- stress proxy,
- displacement proxy,
- safety factor,
- mass efficiency.

Stage 5: Multi-step engineering revision

- inspect hotspots,
- add ribs,
- change fillets,
- move holes,
- reduce mass,
- rerun checks,
- commit design.

Stage 6: Higher-fidelity CAD and FEA

- STEP export,
- tetrahedral meshing,
- linear elasticity,
- thermal add-on,
- multi-load cases.

## Why This Is Reliable

This environment has unusually objective feedback.

The verifier does not need to understand aesthetics or taste. It can simply check:

- code runs,
- CAD builds,
- geometry is closed,
- edits survive,
- features are named,
- constraints are satisfied,
- physical load cases pass,
- artifacts export.

That gives a clean training signal.

It also directly targets a frontier-model weakness:

> Models can often write one plausible CAD script, but they are unreliable at iterative geometric repair and robust parametric editing.

That gap is where RLVE can show measurable improvement.

## 24-Hour MVP

Build the MVP around one or two part families:

1. Wall hook.
2. Shelf bracket or motor mount.

Minimum viable loop:

```text
prompt
-> agent emits constrained CAD JSON or code-CAD
-> environment builds part
-> exports STL
-> validates watertight/manifold geometry
-> runs simple structural score
-> applies one editability mutation
-> returns reward
```

Artifacts:

- CAD code,
- design JSON,
- STL,
- PNG render,
- validation report,
- reward breakdown,
- trace of actions.

The demo story:

> At first, the agent creates CAD that looks plausible but breaks under edits or produces bad geometry. After training, it learns to create clean, editable, watertight parametric parts that survive structural checks.

## Relationship To MechForge

MechForge should become the structural subset of CADForge.

Old framing:

> Train an agent to design lightweight brackets/mounts under load.

New framing:

> Train an agent to create reliable parametric CAD for functional mechanical parts, with MechForge structural checks as the first reward suite.

This is better because it solves the deeper problem.

Structural optimization is valuable, but CAD reliability is the bottleneck. If an agent cannot make clean editable CAD, it cannot become a useful engineering agent.

## Rating

Score: **9/10**

Why:

- Very strong pain point.
- Easy to explain.
- Objective rewards.
- Strong long-horizon action space.
- Clear frontier-model weakness.
- Good bridge between CAD, simulation, manufacturability, and agent training.
- More generally useful than a pure mesh-generation environment.

Main risk:

- Real CAD kernels can be annoying to package and debug.
- The MVP should avoid arbitrary free-form CAD at first.
- Start with a constrained DSL and only later expose full OpenSCAD/CadQuery code.

Best near-term choice:

> Build a constrained code-CAD environment for wall hooks and brackets, validate clean geometry and editability, then add structural MechForge rewards.

