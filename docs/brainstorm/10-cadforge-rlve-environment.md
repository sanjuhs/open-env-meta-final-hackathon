# Document 10: CADForge RLVE Environment

Date: 2026-04-25

## Thesis

CADForge should be an RLVE environment for training agents to create and revise constructive solid geometry code.

The strongest medium is code-CAD:

- OpenSCAD-style CSG,
- CadQuery/build123d feature scripts,
- or a constrained AST/DSL that compiles to OpenSCAD/CadQuery.

The important move is to treat CAD code as an interactive, verifiable environment, not a one-shot file format.

> CADForge is a REPL for mechanical geometry. The agent proposes a small CAD action, the environment builds and verifies the resulting object, then returns geometry, manufacturability, editability, and structural rewards.

This directly fits the hackathon themes:

- **Long-horizon planning:** 300+ small CAD/tool actions to reach a valid final object.
- **World modeling:** the agent must maintain a mental model of the evolving geometry and consequences of each operation.
- **Self-improvement:** adaptive curricula can generate harder CAD briefs and edit tests.
- **Wild card:** reliable CAD creation is an underexplored and high-value frontier for LLM training.

## Why This Is Better Than Raw CAD Text

Do not train the agent to emit raw OpenSCAD text character by character.

That wastes most of the learning signal on syntax:

- semicolons,
- braces,
- parameter order,
- missing parentheses,
- malformed module calls.

Instead, constrain the action space to AST operations. The policy chooses valid grammar moves:

```json
{"action": "add_primitive", "type": "cube", "size_mm": [80, 40, 6]}
{"action": "apply_transform", "type": "translate", "vector_mm": [0, 0, 6]}
{"action": "apply_boolean", "type": "union", "children": ["base", "rib_1"]}
{"action": "apply_boolean", "type": "difference", "target": "base", "tool": "mount_hole_1"}
```

Then the environment renders or compiles that AST into OpenSCAD/CadQuery.

This gives:

- syntactic validity by construction,
- clean action traces,
- easier reward attribution,
- interpretable failure modes,
- curriculum control over which operations are unlocked.

## Environment Loop

The RL step loop should look like:

```text
reset(task_seed)
  -> returns design brief, target constraints, allowed grammar/actions

step(action)
  -> updates CSG AST / feature tree
  -> optionally compiles the current CAD
  -> validates syntax, topology, editability, manufacturability, structure
  -> returns observation, reward, done, artifacts

done
  -> when agent commits design, exceeds step budget, or creates unrecoverable invalid geometry
```

The environment is effectively a CAD REPL:

```text
agent action
-> AST update
-> generated OpenSCAD/CadQuery
-> headless CAD build
-> STL/STEP export
-> trimesh/solid validation
-> simple structural check
-> reward + warnings
```

## Action Space

Start with a small grammar.

Primitive actions:

```json
{"tool": "add_cube", "id": "seat", "size_mm": [420, 380, 35]}
{"tool": "add_cylinder", "id": "leg_1", "height_mm": 450, "radius_mm": 18}
{"tool": "add_sphere", "id": "edge_round_proxy", "radius_mm": 12}
```

Transform actions:

```json
{"tool": "translate", "target": "leg_1", "vector_mm": [-170, -140, -225]}
{"tool": "rotate", "target": "back_leg_1", "axis": "x", "degrees": -8}
{"tool": "scale", "target": "rib_1", "factor": [1, 1, 1.2]}
```

Boolean actions:

```json
{"tool": "union", "id": "chair_frame", "children": ["seat", "leg_1", "leg_2", "leg_3", "leg_4"]}
{"tool": "difference", "target": "seat", "tool": "lightening_cutout_1"}
{"tool": "intersection", "id": "trimmed_backrest", "children": ["backrest", "envelope_box"]}
```

Feature actions:

```json
{"tool": "add_mount_hole", "target": "wall_plate", "diameter_mm": 5, "center_mm": [0, 24, 0]}
{"tool": "add_fillet", "target": "load_path_edges", "radius_mm": 4}
{"tool": "add_rib", "from": "seat", "to": "leg_1", "thickness_mm": 8}
{"tool": "add_crossbar", "between": ["leg_1", "leg_2"], "radius_mm": 10}
```

Validation and simulation actions:

```json
{"tool": "compile_cad"}
{"tool": "check_connected_components"}
{"tool": "check_watertight"}
{"tool": "check_manifold"}
{"tool": "check_editability"}
{"tool": "run_structural_check"}
{"tool": "commit_design"}
```

## Verifiable REPL Implementation

Use Python as the bridge.

MVP stack:

```text
Gymnasium/OpenEnv API
-> Python CSG AST
-> SolidPython or direct OpenSCAD text emitter
-> OpenSCAD CLI headless compile
-> STL output
-> trimesh validation
-> reward
```

Headless compile:

```bash
openscad -o temp.stl generated_script.scad
```

For speed:

- compile every N actions during long episodes,
- compile immediately after high-risk boolean/edit operations,
- run multiple environments in parallel,
- write temporary files to a RAM disk when available,
- cache compiled subtrees if the AST supports stable node IDs.

## Reward Function

The reward should combine code validity, geometry coherence, editability, manufacturability, and structural performance.

```text
R_total =
  + w_build         * build_success
  + w_connected     * single_connected_component
  + w_manifold      * watertight_manifold_mesh
  + w_contact       * required_parts_touch_and_align
  + w_editable      * editability_tests_passed
  + w_constraints   * task_constraints_satisfied
  + w_structure     * safety_factor_score
  + w_efficiency    * mass_efficiency
  - w_nodes         * ast_node_count
  - w_invalid       * invalid_operation_count
  - w_floating      * disconnected_component_count
```

Suggested first weights:

```text
build_success:              0.20
single_connected_component: 0.20
watertight_manifold_mesh:   0.20
part_contact_alignment:     0.10
editability_tests_passed:   0.10
constraints_satisfied:      0.05
structural_safety:          0.10
mass_efficiency:            0.025
manufacturability:          0.025
```

Big penalties:

```text
syntax_or_compile_error:    -1.00 and terminate
floating_parts:             -0.60 to -1.00 and terminate on final commit
non_manifold_mesh:          -0.50
self_intersection:          -0.50
unjoined_touching_failure:   -0.35
edge_misalignment:          -0.25
zero_thickness_geometry:    -0.20
failed_required_edit:       -0.20
unsafe_final_design:        -0.30
```

The first principle:

> A pretty shape that does not compile, is not watertight, or contains floating parts should receive a near-zero score.

For CADForge, topology is not a secondary check. It is the gate that decides whether the object is even a valid candidate.

## Floating Parts And Coherence

This is a major reward term.

After the CAD compiles to STL, load it with `trimesh`:

```python
mesh = trimesh.load("generated.stl")
components = mesh.split()
floating_count = max(0, len(components) - 1)
```

If `len(components) > 1`, the part contains disconnected/floating geometry.

Policy:

- small intermediate penalty while exploring,
- large penalty after compile checkpoints,
- immediate episode termination if the final committed design has floating parts.

The reward should strongly prefer one physically coherent object.

For multi-part everyday objects such as chairs, tables, hooks, clamps, and trusses, "close enough visually" is not enough. The environment should verify that load-bearing parts actually touch or overlap:

- legs must contact or penetrate the underside of the seat enough to form a union,
- crossbars must touch both legs they claim to connect,
- backrests must connect to the seat or rear legs,
- hook arms must connect to the mounting plate,
- truss members must meet at nodes,
- holes/cutouts must pass through the intended parent solid, not float in empty space.

This needs edge/contact and alignment checks:

- bounding-box contact tests between named features,
- nearest-surface distance between intended mating faces,
- shared-node or overlap checks after boolean union,
- non-manifold edge count,
- boundary/open edge count,
- connected-component count,
- semantic contact graph pass/fail.

The contact graph can be part of the observation:

```json
{
  "contact_graph": {
    "seat": ["front_left_leg", "front_right_leg", "rear_left_leg", "rear_right_leg", "backrest"],
    "front_crossbar": ["front_left_leg", "front_right_leg"],
    "rear_crossbar": ["rear_left_leg", "rear_right_leg"]
  },
  "missing_contacts": [],
  "floating_features": []
}
```

If the contact graph fails, the episode should continue only if the agent still has repair budget. A final committed design with missing required contacts should fail hard.

## Mesh And Solid Quality

The "tight mesh" requirement means:

> The CAD-generated solid exports to a closed, watertight, manifold, simulation-ready mesh.

Checks:

- `mesh.is_watertight`,
- one connected component,
- no zero-area faces,
- no duplicate faces,
- no inverted normals,
- no obvious self-intersections,
- minimum wall thickness,
- minimum feature size,
- acceptable triangle aspect ratios,
- volume above a small threshold,
- bounding box inside the task envelope.

These checks are objective and judge-friendly.

For browser-side MVP rendering, the same checks can be computed directly on the generated mesh:

- count connected components from triangle/vertex adjacency,
- count boundary edges,
- count non-manifold edges,
- mark watertight only if every edge has exactly two incident faces,
- expose the failure as a reward penalty and UI metric.

This is not a mock reward. It is a real topology check on the actual rendered mesh, even if the renderer initially supports only a constrained OpenSCAD subset.

## Reference Model Reward

A second reward channel can compare the generated CAD mesh against a reference object.

For the chair benchmark, the first reference asset is:

```text
3d-models/ikea_markus_office_chair.glb
```

This should not replace topology rewards. It should sit after them:

```text
if not build_success or not watertight or floating_parts > 0:
  reward = near_zero
else:
  reward = topology_reward + structural_reward + reference_similarity_reward
```

Reference similarity can use:

- normalized bounding-box dimensions,
- oriented bounding-box alignment,
- voxel IoU,
- Chamfer distance between sampled surface points,
- silhouette overlap from canonical views,
- part-presence classifiers for seat/legs/back/arms/headrest,
- center-of-mass and support-polygon checks.

For chairs:

- CAD output should have a seat-like horizontal surface,
- support structures should reach the floor,
- backrest should rise behind the seat,
- optional armrests/headrest should align with the reference,
- dimensions should fit a plausible chair envelope.

This gives the model a shape target without letting it cheat by creating a raw mesh. The final artifact still needs to be editable SCAD/CAD code.

## Prompt-To-Reference-To-CAD Pipeline

The general everyday-object pipeline:

```text
input prompt
-> generate or retrieve reference image
-> generate/retrieve watertight reference mesh or GLB
-> normalize reference mesh scale/orientation
-> agent creates SCAD/CAD through constrained actions
-> compile/render candidate mesh
-> reject if uncompiled, non-watertight, or floating
-> compare candidate mesh to reference mesh
-> run object-specific structural/contact checks
-> return reward and repair hints
```

Possible reference sources:

- curated GLB files for common objects,
- image-to-3D systems such as Tripo-style services,
- generated image followed by image-to-3D,
- public model libraries when licensing permits,
- procedural target generators for simple brackets, hooks, tables, and trusses.

Reward order matters:

1. **Compile validity**: code must parse and render.
2. **Topology validity**: one watertight connected component.
3. **Semantic contact graph**: required parts touch and align.
4. **Reference similarity**: looks like the target/reference.
5. **Structural validity**: load path and safety checks.
6. **Editability**: parameters survive changes.

This attacks a core AI CAD weakness:

> Models can generate objects that look plausible in one view but are topologically broken, uneditable, disconnected, or mechanically meaningless.

CADForge should train against exactly those failures.

## Editability Tests

This is where CADForge becomes much stronger than ordinary shape generation.

After a final design is produced, mutate the design brief:

- make the chair seat 10% wider,
- increase chair load from 700 N to 900 N,
- move screw spacing from 48 mm to 56 mm,
- increase hook tip load by 20%,
- change material from PLA to PETG,
- require all fillets above 3 mm,
- shrink the envelope,
- switch from FDM printing to CNC constraints.

The environment recompiles after the mutation.

Reward the agent only if the design survives without a full rewrite. This encourages:

- named parameters,
- stable feature IDs,
- constrained sketches,
- reusable modules,
- clean boolean ordering,
- avoiding brittle one-off coordinates.

## First Benchmark: Chairs

A chair is a surprisingly good first benchmark if the grammar is constrained.

Why:

- everyone understands what a chair should contain,
- it requires multiple connected components to become one coherent assembly,
- it exposes floating-part failures clearly,
- it has real load-bearing structure,
- it needs symmetry, legs, bracing, seat, and backrest,
- it can support long-horizon 100-300 step episodes.

Start simple:

```text
Build a four-legged chair that supports a 700 N seated load.
It must include a seat panel, four legs, lower crossbars, and a backrest.
All parts must be connected into one watertight/manifold solid.
Keep the bounding box under 500 mm x 500 mm x 900 mm.
```

Then increase difficulty:

- ergonomic curved chair,
- armrests,
- headrest,
- 1000 N seat load plus 100 N backrest load,
- lightweighting,
- printability constraints,
- edit test: widen seat and raise load.

Other early benchmark tasks:

- wall hook,
- shelf bracket,
- table,
- truss,
- clamp,
- motor mount.

## Training Path

Do not start with full free-form CAD.

Curriculum:

1. **2D primitives:** square, circle, translate, union.
2. **2D booleans:** difference and intersection.
3. **2.5D extrusion:** plate with holes.
4. **Simple 3D CSG:** cube/cylinder compositions.
5. **Connectivity tasks:** all parts must touch or union.
6. **Household parts:** hook, bracket, table, chair.
7. **Structural tasks:** loads, fixed regions, stress proxies.
8. **Editability tasks:** mutate dimensions and rebuild.
9. **Long-horizon tasks:** 300-step chair/bracket/truss episodes.

This makes the learning curve visible:

```text
random/untrained agent:
  compiles sometimes, often disconnected, weak structure

trained agent:
  valid AST, connected geometry, cleaner feature tree, passes structural checks
```

## Model And Algorithm Notes

For the hackathon, the minimum is not a perfect RL algorithm. The key is showing improvement.

Practical options:

- collect successful traces from a scripted expert,
- train/fine-tune an LLM with TRL/Unsloth on action traces,
- evaluate before/after in the environment,
- optionally run PPO or GRPO over tool-action rewards.

For a deeper version:

- PPO works well for discrete grammar actions,
- GRPO may be attractive for LLM tool-action policies,
- state encoder can combine text brief, AST history, and geometry metrics,
- later geometry encoders can use voxel grids, PointNet, or compact mesh summaries.

Do not overbuild the neural architecture for the MVP. The environment and reward quality matter more.

## Experiment 2 Scope

Experiment 2 should be the CADForge prototype:

```text
Experiment 1:
  prompt -> structured mechanical design -> Three.js render -> coarse FEA

Experiment 2:
  prompt -> multi-step CSG/CAD actions -> CAD validity checks -> connected/watertight reward -> structural household part score
```

The browser should show:

- design prompt,
- system prompt,
- CSG action trace,
- generated pseudo-OpenSCAD/code-CAD,
- geometry validation metrics,
- structural/checkpoint reward,
- 3D viewer,
- before/after or untrained/trained comparison.

The initial fun demo:

> Ask the agent to build a chair. Watch it add seat, legs, crossbars, backrest, fillets/ribs, run validation, detect floating parts, connect them, and commit a valid CAD-like object.

## Judging Story

Problem:

> LLMs can describe parts but are unreliable at building valid, editable CAD.

Environment:

> CADForge turns CAD creation into a long-horizon verifiable tool environment. The agent edits a CSG/feature tree, compiles it, receives topology/manufacturability/structure feedback, and revises until the design passes.

Training:

> We fine-tune or RL-train on CAD action traces and reward feedback. The model learns to use fewer invalid operations, avoid floating parts, create connected watertight solids, and satisfy structural constraints.

Evidence:

- reward curves,
- valid build rate,
- connected component count,
- watertight rate,
- editability pass rate,
- structural safety pass rate,
- before/after rendered parts.

Why it matters:

> Reliable CAD agents would unlock practical engineering workflows. The hard part is not drawing a shape; it is making geometry that builds, edits, exports, and survives physical constraints.

## Score

Score: **9/10**

This direction is strong because it is novel, verifiable, visual, long-horizon, and directly aimed at a known frontier-model weakness.

The best MVP path is:

> Build chairs/hooks/brackets through constrained CSG actions, validate with OpenSCAD/trimesh-style checks, and add MechForge structural rewards as the next layer.
