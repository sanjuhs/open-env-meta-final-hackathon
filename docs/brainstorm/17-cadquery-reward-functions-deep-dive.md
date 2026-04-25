# CadQuery Reward Functions Deep Dive

This document explains the reward code in `experiment-2-cadforge/python_tools/cadquery_env.py`.

## Total Reward

The evaluator produces component scores in `[0, 1]`, except build failures, which return total reward `-1`.

Fast mode is for dense RL feedback:

```text
total = 0.22 * build
      + 0.17 * topology
      + 0.12 * contact
      + 0.25 * semantic_parts
      + 0.10 * reference_similarity
      + 0.10 * editability
      + 0.04 * efficiency
```

Full mode is for reports, teacher traces, and benchmark artifacts:

```text
total = 0.18 * build
      + 0.17 * topology
      + 0.10 * contact
      + 0.15 * semantic_parts
      + 0.15 * reference_similarity
      + 0.10 * silhouette
      + 0.10 * editability
      + 0.05 * efficiency
```

Fast mode deliberately weights task semantics higher and reference lower because, without renders/point clouds, bbox-only reference scoring is easier to game.

## Build Reward

Build is a hard gate.

If the CadQuery code does not execute, does not create/export `fixture`, or fails STL export:

```text
total = -1
build = 0
all other components = 0
```

The evaluator now includes a concise Python/CadQuery error in `notes`, for example:

```text
Build error: NameError: name 'headrest_height_from_ground' is not defined
```

This is crucial for Qwen because most early failures are invalid code, not bad geometry.

## Task Semantics Reward

Function: `semantic_reward(code, mesh, task_spec)`

This has three parts:

```text
semantic = 0.35 * code_score
         + 0.45 * geometry_score
         + 0.20 * assembly_score
```

### Code Score

Each task has `semantic_hints` in `cad_tasks.json`.

Example table hints:

```json
["tabletop", "six_leg", "leg", "crossbar", "stretcher", "support", "load_500n"]
```

The reward checks whether each hint appears in the code, allowing underscore-insensitive matches:

```python
hint in lowered_code
hint_without_underscores in lowered_code_without_underscores
```

This rewards explicit, editable part intent. It does not require a fixed function name like `add_seat()`. The model can invent its own structure, but it gets credit when the code makes the intended parts legible.

### Geometry Score

If the task has `bbox_mm`, the evaluator compares the normalized shape ratios:

```text
target = [x, y, z] / z
actual = candidate_bbox / candidate_height
geometry_score = 1 - mean(relative_ratio_error)
```

This prevents a model from getting high semantic score by merely writing keywords in comments while building a totally wrong envelope.

For the original Markus chair path without a task spec, it uses chair-specific geometry signals:

- chair-like width/height and depth/height ratios
- lower base spread
- meaningful upper-height geometry

### Assembly Score

The reward counts helper functions:

```python
functions = number of `def name(...):`
assembly_score = min(1, functions / 6)
```

This encourages decomposed CAD: helper functions for legs, arms, bosses, teeth, ribs, etc. It does not force exact part names.

## Editability Reward

Function: `editability_reward(code)`

This rewards code that another agent can revise over many steps.

```text
editability = 0.35 * function_score
            + 0.20 * named_dimension_score
            + 0.25 * reusable_return_score
            + 0.20 * final_object_score
```

### Function Score

```python
functions = count_regex(r"^\s*def\s+\w+\s*\(")
function_score = min(1, functions / 6)
```

Why: long-horizon CAD editing works better when the model can edit `make_leg()`, `make_backrest()`, `make_stator_tooth()`, or `make_mounting_hole_pattern()` instead of rewriting one giant union chain.

### Named Dimension Score

```python
named_values = count_regex(r"^\s*[a-zA-Z_][a-zA-Z0-9_]*\s*=\s*[-+]?\d")
named_dimension_score = min(1, named_values / 8)
```

This rewards parameters like:

```python
seat_width = 520
leg_height = 680
bolt_radius = 4
```

Why: dimensions make future edits local and stable. A repair agent can increase `back_height` or move `caster_radius` without hunting through anonymous numbers.

### Reusable Return Score

```python
reusable_returns = count_regex(r"^\s*return\s+")
reusable_return_score = min(1, reusable_returns / max(1, functions))
```

This rewards helper functions that return shapes instead of mutating unclear globals.

Good:

```python
def make_leg(x, y):
    return cq.Workplane("XY").box(35, 35, leg_height).translate((x, y, leg_height / 2))
```

Less editable:

```python
leg = cq.Workplane("XY").box(35, 35, 680)
```

### Final Object Score

```python
has_final_object = "fixture" in code or "result" in code or "chair" in code or "show_object" in code
```

This gives `0.20` when the model clearly exposes an exportable final object. In practice, `fixture` is the important convention because the runner exports `fixture`.

## Topology Reward

Function: `topology_reward(topology_metrics(mesh))`

It checks:

- component count
- watertightness
- boundary edge ratio
- non-manifold edge ratio
- degenerate face ratio
- sane face count

Markus and many CAD assemblies are allowed to have multiple components, so this does not require a single monolithic body. For future tasks that explicitly require one connected watertight object, we should add a stricter task-level option.

## Contact/Gaps Reward

Function: `contact_metrics(mesh)`

The mesh is split into components. Tiny fragments are ignored. For each meaningful component, the evaluator finds the nearest component bounding-box gap and normalizes it by object height.

The score decays with:

- higher mean gap
- higher max gap
- count of large separated components

This catches:

- floating backrests
- disconnected caster assemblies
- floating table legs
- load bosses not attached to arms
- detached wall plates or brackets

Small assembly gaps are tolerated because real CAD assemblies may have separate touching solids or visual separation.

## Reference Similarity

If a GLB reference exists, the evaluator compares the candidate against:

- generated/reference GLB
- optional ideal CadQuery reference

The per-reference score is:

```text
reference_one = 0.25 * bbox
              + 0.35 * chamfer
              + 0.40 * silhouette
```

If both ideal CadQuery and GLB exist:

```text
reference_similarity = 0.60 * ideal_score + 0.40 * glb_score
```

If no GLB exists yet for a generated task, reference and silhouette are neutral `0.50`, and the report explicitly says the task-specific GLB is missing.

## Silhouette Reward

Full mode renders masks from:

- front
- back
- left
- right
- top
- isometric

It computes mask IoU against reference silhouettes. This is cheap enough for reports and teacher traces and catches overall shape mistakes that bbox alone cannot catch.

## Known Limitations

1. Code semantic hints can be gamed by comments. Geometry and reference scores reduce this, but we should later ignore comments or parse identifiers only.
2. Editability currently checks simple regexes. It rewards structure, not true AST-level quality.
3. No finite-element simulation is running yet. Load/safety-factor phrases are currently semantic intent, not verified stress analysis.
4. Generic tasks without GLBs use neutral reference scores until generated references are preprocessed.
5. Single-body/watertight requirements need task-specific stricter topology settings.

## Near-Term Improvements

- Parse Python AST for identifiers and assignments instead of raw regex.
- Add per-task reward profiles, for example `single_body_required`, `min_holes`, `radial_symmetry_required`, `leg_count`.
- Add image/GLB generated references for all 24 tasks.
- Add cheap analytic checks for hole count, radial teeth count, and support/leg count.
- Add optional FEA proxy rewards for load-bearing prompts.
