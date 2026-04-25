# Brainstorm 13: CadQuery Markus Chair GRPO/RLVE Hackathon Plan

Date: 2026-04-25

## One-line pitch

CADForge is a reinforcement-learning environment where language models learn to create and revise real parametric CadQuery models by acting through CAD tools, observing rendered geometry, and optimizing verifiable rewards for topology, editability, and similarity to a reference object.

The flagship benchmark is a Markus-style office chair reconstructed as editable CadQuery code from a reference GLB.

## Hackathon thesis

Most models can write plausible CAD-looking Python once. They fail when they must maintain a persistent 3D world model across many revisions:

- parts float,
- booleans fail,
- dimensions drift,
- edits break the model,
- screenshots look plausible but topology is invalid,
- the model cannot reliably repair geometry from tool feedback.

CADForge turns this into a trainable environment:

```text
prompt
-> model proposes CadQuery code or edit action
-> backend executes CadQuery
-> environment exports STL/mesh/screenshots
-> reward functions score topology, similarity, editability, and tool efficiency
-> model revises for up to 300 actions
-> GRPO trains a small model to need fewer revision steps
```

The objective is not just "generate a chair." The objective is:

> Train a tiny Qwen model to become a better CadQuery CAD agent that produces valid, editable, reference-aligned geometry with fewer tool calls.

## Theme alignment

### Theme 2: Long-horizon planning

The environment supports up to 300 actions per episode:

- generate initial CadQuery,
- render,
- inspect topology,
- inspect screenshots,
- compare to GLB reference,
- edit dimensions,
- add missing parts,
- repair disconnected components,
- rerender,
- commit final design.

The reward is delayed and multi-part. A model must plan the full assembly, not just write a single pretty script.

### Theme 3.1: Professional world modeling

This is a realistic engineering workflow:

- Python CadQuery execution,
- STL export,
- mesh validation,
- reference GLB normalization,
- point-cloud and silhouette comparison,
- persistent CAD state,
- artifact logs,
- render snapshots,
- code diffs,
- editability checks.

The agent must model a partially observable 3D world using tool feedback. It cannot solve the task by text pattern matching alone.

### Theme 4: Self-improvement

The environment can generate adaptive tasks:

- make the chair taller,
- make armrests thicker,
- widen the five-star base,
- repair floating parts,
- reduce revision count,
- preserve editability under parameter changes.

Curriculum generation can escalate from simple blocks to full chairs. The model improves by repeatedly encountering its own CAD failure modes.

### Theme 1: Multi-agent interactions, optional extension

If time permits, split the workflow into specialist roles:

- Designer agent proposes CadQuery.
- Critic agent interprets screenshots and reward reports.
- Repair agent edits only broken geometry.
- Verifier agent decides whether to commit.

This is not required for the MVP, but it is a clean demo extension.

## What to build first

Build the CadQuery-only Markus environment before training.

Do not start with full RL. First make the environment stable, because GRPO only matters if the reward is trustworthy.

Priority order:

1. Reference preprocessing pipeline.
2. CadQuery candidate execution pipeline.
3. Reward functions with visible breakdowns.
4. GPT-5.4/GPT-5.5 multi-step benchmark traces.
5. Small Qwen GRPO run.
6. Before/after report and demo.

## Reference pipeline

Input:

```text
3d-models/ikea_markus_office_chair.glb
```

Steps:

1. Load the GLB with `trimesh`.
2. Convert scene nodes into one mesh.
3. Normalize orientation so:
   - Z is up,
   - seat/back height is vertical,
   - chair front faces negative Y or a fixed canonical direction.
4. Normalize origin:
   - center X/Y at zero,
   - floor/base touches Z = 0,
   - scale height to a canonical chair height, for example 1000 mm.
5. Save normalized artifacts:
   - `reference_normalized.glb`,
   - `reference_normalized.stl`,
   - `reference_point_cloud.npy`,
   - `reference_voxels.npz`,
   - `reference_silhouettes/*.png`,
   - `reference_metrics.json`.

Reference metrics:

```json
{
  "bbox_mm": {"x": 620, "y": 650, "z": 1000},
  "seat_height_ratio": 0.45,
  "back_height_ratio": 0.55,
  "base_radius_ratio": 0.32,
  "views": ["front", "back", "left", "right", "top", "isometric"],
  "semantic_hints": ["seat", "tall_backrest", "armrests", "central_column", "five_star_base"]
}
```

## Candidate pipeline

Input:

```text
task prompt + current CadQuery code + last verifier report + screenshot summaries
```

Candidate execution:

1. Write CadQuery code.
2. Run in a sandboxed Python subprocess.
3. Export STL.
4. Load STL with `trimesh`.
5. Normalize candidate to the same coordinate frame as the reference.
6. Render six fixed views plus an isometric.
7. Compute reward components.
8. Save artifacts.

Artifacts per attempt:

```text
runs/<episode_id>/<step_id>/
  candidate.py
  candidate.stl
  candidate_normalized.stl
  renders/isometric.png
  renders/front.png
  renders/back.png
  renders/left.png
  renders/right.png
  renders/top.png
  reward.json
  verifier_report.md
```

## Agent action space

For the demo UI and GPT benchmark, allow free-form CadQuery edits.

For GRPO training, use a stricter action format so a small Qwen model can learn without forcing hand-authored chair-part tools:

```json
{
  "thought": "The backrest is too short and disconnected from the seat.",
  "tool": "apply_patch",
  "patch": "*** Begin Patch\n*** Update File: candidate.py\n@@\n-back_height = 520\n+back_height = 680\n*** End Patch"
}
```

Initial allowed tools:

```text
write_initial_cadquery
apply_patch
replace_file
render_candidate
inspect_reward
inspect_screenshots
commit_design
```

The important rule is that the model edits CadQuery like a developer edits code in a REPL. It can add functions, refactor parameters, split subassemblies, create helpers, and compose objects however it wants. The environment should not expose narrow tools such as `add_part seat` or `add_backrest` as the main action space, because that bakes our solution into the policy. Semantic part names are reward probes, not required action names.

Optional later tools can stay code-native:

```text
run_static_code_check
show_code_diff
revert_last_patch
ask_verifier_for_top_failure
export_artifacts
parameter_edit
```

The long-horizon version should count every tool call as an action and cap the episode at 300 actions.

## Reward design

The reward must be multi-signal. A single "looks like chair" score is too easy to hack.

Use two reward speeds:

- `fast`: dense RL feedback after ordinary edit/tool steps. It scores build success, topology, bounding-box similarity, code/semantic structure, and editability without writing screenshots or running point-cloud/silhouette comparison.
- `full`: checkpoint/final scoring. It saves render artifacts and computes silhouette IoU plus Chamfer-style point-cloud similarity against both the ideal CadQuery reference and the GLB reference.

The training loop should use `fast` for most rollout steps and `full` on `commit_design`, every N revisions, and benchmark/report runs.

Final score:

```text
R_total =
    0.20 * R_build
  + 0.20 * R_topology
  + 0.15 * R_semantic_parts
  + 0.15 * R_reference_similarity
  + 0.10 * R_silhouette
  + 0.10 * R_editability
  + 0.05 * R_efficiency
  + 0.05 * R_process
  - penalties
```

Use gates before adding soft similarity rewards:

```text
if code_does_not_run: R_total = -1.0 and terminate
if no_mesh_or_empty_mesh: R_total = -1.0 and terminate
if final_design_has_many_components: cap R_total at 0.20
if final_design_is_not_chair_like: cap R_total at 0.35
```

### R_build

Checks whether CadQuery code is executable and exports geometry.

Signals:

- imports only allowed modules,
- defines a final `result` or discoverable CadQuery object,
- CadQuery build succeeds,
- STL export succeeds,
- mesh loads in `trimesh`,
- bounding box is finite and nonzero.

Suggested scoring:

```text
cadquery_import_ok:      +0.15
script_exec_ok:          +0.25
solid_found:             +0.20
stl_export_ok:           +0.20
mesh_load_ok:            +0.20
```

### R_topology

Topology dominates because disconnected pretty geometry is not useful CAD.

Signals:

- connected component count,
- watertight mesh,
- manifold edges,
- boundary edges,
- non-manifold edges,
- degenerate faces,
- reasonable face count,
- no huge accidental slabs.

Suggested scoring:

```text
single_connected_component: +0.35
watertight:                  +0.25
no_non_manifold_edges:        +0.15
low_boundary_edges:           +0.10
no_degenerate_faces:          +0.10
reasonable_complexity:        +0.05
```

Penalties:

```text
extra_connected_component:     -0.15 each
boundary_edge_ratio_high:      -0.10 to -0.30
non_manifold_edges_present:    -0.20
degenerate_faces_present:      -0.10
```

### R_semantic_parts

The Markus chair is not just any tall object. It needs recognizable functional parts.

Required part hints:

- seat,
- tall backrest,
- upper/headrest-like section,
- left armrest,
- right armrest,
- central support column,
- five-star base or at least 5 radial spokes,
- caster proxies or feet.

Detection can start from named variables and bounding boxes, then become geometric:

```text
seat exists:                         +0.10
backrest taller than seat:            +0.15
backrest touches seat/rear supports:  +0.15
two armrests exist:                   +0.15
armrests connect to seat/back:        +0.10
central column exists:                +0.10
base has 5 radial spokes:             +0.15
base contacts column:                 +0.10
```

This reward should inspect both code and geometry. Code names are helpful but not sufficient.

### R_reference_similarity

Use normalized candidate and normalized GLB reference.

Signals:

- bounding-box ratio similarity,
- point-cloud Chamfer distance,
- voxel IoU,
- rough mass distribution by height,
- principal-axis alignment.

Suggested scoring:

```text
bbox_ratio_score:        0.25
chamfer_score:           0.30
voxel_iou_score:         0.25
height_distribution:     0.10
principal_axes_score:    0.10
```

Important: this reward should not overpower topology. A broken mesh that happens to occupy similar pixels should not win.

### R_silhouette

Render candidate and reference with the same camera settings:

- front,
- back,
- left,
- right,
- top,
- isometric.

Compute binary mask IoU or distance transform similarity.

Suggested scoring:

```text
front_iou:      0.20
side_iou:       0.25
back_iou:       0.15
top_iou:        0.15
isometric_iou:  0.25
```

This is the judge-friendly reward because it maps to visible screenshots.

### R_editability

This is the product differentiator. The environment should mutate the code and check whether it still builds.

Edit tests:

- increase backrest height by 10 percent,
- widen seat by 10 percent,
- thicken armrests,
- increase base radius,
- change column height,
- change global scale.

Signals:

```text
named_parameters_present:       +0.20
all_major_dimensions_parameterized: +0.25
edit_backrest_height_rebuilds:  +0.15
edit_seat_width_rebuilds:       +0.15
edit_base_radius_rebuilds:      +0.15
no_hardcoded_uneditable_blob:    +0.10
```

This blocks the model from generating a one-off decorative mesh-like CadQuery script.

### R_efficiency

The goal is fewer revision steps.

Signals:

- number of tool calls,
- number of failed renders,
- number of compile failures,
- token count,
- code size.

Suggested scoring:

```text
R_efficiency = max(0, 1 - tool_calls / max_tool_calls)
```

Penalties:

```text
compile_failure:      -0.05 each
render_failure:       -0.05 each
unproductive_edit:    -0.03 each
excessive_code_size:  -0.05
```

This is where the "trained model needs fewer revisions" claim becomes measurable.

### R_process

Reward the agent for using the workflow correctly:

- renders before committing,
- reads reward report before editing,
- repairs the biggest failure first,
- does not repeat the same failed edit,
- commits only after passing minimum topology gates.

Example:

```text
rendered_before_commit:            +0.20
used_verifier_feedback_in_edit:     +0.25
fixed_previous_top_failure:         +0.25
no_repeated_failed_patch:           +0.15
commit_after_threshold:             +0.15
```

## Anti-reward-hacking checks

Block or penalize:

- reading reference reward files directly,
- hardcoding saved mesh artifacts,
- importing network or filesystem tools outside the run directory,
- writing files outside the episode directory,
- returning a prebuilt STL instead of CadQuery,
- creating one giant slab that fills the silhouette,
- naming variables `seat` and `backrest` without matching geometry,
- disabling or bypassing verifier code,
- excessive triangle count to game silhouette overlap.

CadQuery execution should run in a subprocess with:

- timeout,
- allowed imports,
- isolated working directory,
- max file size,
- max mesh triangles,
- no network,
- no access to hidden reference internals.

## GPT-5.4/GPT-5.5 benchmark

Purpose:

Show that even strong frontier models improve through tool use, and collect teacher traces for the small model.

Benchmark setup:

- Tasks: 5 to 10 Markus-chair variants.
- Models: GPT-5.4 and GPT-5.5 if available in the local/API stack.
- Budget: 1, 3, 5, 10, and 20 tool-call attempts.
- Each attempt saves code, STL, screenshots, reward breakdown, and critique.

Tasks:

1. Baseline Markus-like chair.
2. Taller backrest.
3. Thicker armrests.
4. Wider five-star base.
5. Repair a provided broken chair with floating parts.
6. Make the chair editable under global scale changes.
7. Improve silhouette match against the GLB.

Report file:

```text
experiment-2-cadforge/reports/gpt-cadquery-benchmark.md
```

Report structure:

```markdown
# GPT CadQuery Tool-Use Benchmark

## Summary Table
| Task | Model | Attempts | Best Reward | Build | Topology | Similarity | Editability | Notes |

## Task 1: Baseline Markus Chair
### Attempt 1
- Code: ...
- Reward: ...
- Failure: ...
- Screenshots: ...
### Attempt N
- Improvement: ...

## Cross-task Findings
- What improved with more tool calls
- What did not improve
- Repeated failure modes
- Best teacher traces for SFT or GRPO warm start
```

This is the "evidence" part judges will care about.

## GRPO training plan

Use GRPO/RLVR, not classic human-preference RLHF, for the core result.

Why:

- rewards are verifiable,
- no reward model needed,
- multiple sampled candidates per prompt can be ranked by the verifier,
- the hackathon guide explicitly favors verifier-first GRPO-style tasks.

Model target:

```text
Qwen small instruct model, ideally 0.5B to 1.5B for overnight feasibility.
```

Training stages:

### Stage 0: Formatting warm start

Small SFT dataset from:

- hand-written valid CadQuery templates,
- GPT teacher traces,
- environment tool-call transcripts.

Goal:

Teach the small model to emit the correct action JSON and basic CadQuery structure.

### Stage 1: Easy GRPO

Tasks:

- create one box,
- create seat plus backrest,
- create connected chair silhouette from boxes/cylinders,
- pass build/topology rewards.

Reward focus:

- valid code,
- connected mesh,
- named parameters.

### Stage 2: Markus semantic GRPO

Tasks:

- full Markus-like chair,
- add armrests,
- add five-star base,
- repair disconnected base/back/arms.

Reward focus:

- semantic part score,
- topology,
- silhouette.

### Stage 3: Revision efficiency GRPO

Tasks:

- start from flawed candidates,
- repair within 5 to 20 tool calls,
- minimize failed renders and repeated edits.

Reward focus:

- fewer tool calls,
- fixed prior failure,
- final reward delta.

## Overnight RunPod plan

Only start raw compute after the environment can run 100 local episodes without crashing.

Minimum preflight:

```text
python scripts/run_cadquery_env_smoke.py --episodes 20
python scripts/run_reward_regression.py
python scripts/run_gpt_benchmark.py --tasks 2 --attempts 2
```

When to rent RunPod:

1. Reward code is stable.
2. Artifacts save correctly.
3. No reward file leakage.
4. Qwen can produce valid action JSON at least sometimes.
5. Local mini-GRPO or dry-run completes.

Suggested overnight jobs:

```text
Job A: GPT teacher benchmark
- 5 to 10 tasks
- 5 to 20 attempts per task
- save markdown report and screenshots

Job B: Qwen Stage 0 SFT
- formatting/action traces
- 1 to 2 hours

Job C: Qwen GRPO Stage 1/2
- easy to medium curriculum
- 6 to 10 hours
- checkpoint every 30 to 60 minutes
```

Metrics to monitor:

- total reward,
- build success rate,
- connected component pass rate,
- semantic part score,
- silhouette score,
- editability pass rate,
- average tool calls to best design,
- compile failure rate,
- examples every N steps.

Stop the run if:

- compile failure rate stays above 80 percent after warmup,
- reward rises while topology gets worse,
- outputs start exploiting file paths or constants,
- model stops using valid action JSON.

## Demo plan

The winning demo should be visual and measurable.

Screen 1:

- user prompt,
- reference GLB thumbnails,
- baseline small Qwen attempt,
- broken render and reward report.

Screen 2:

- multi-step tool trace,
- failed topology warning,
- edit patch,
- rerender.

Screen 3:

- post-GRPO Qwen attempt,
- fewer revisions,
- better topology,
- better silhouette,
- reward improvement.

Screen 4:

- GPT-5.5 benchmark report as teacher/frontier baseline,
- trained tiny model improvement curve,
- environment API/OpenEnv story.

Core claim:

> We built a professional CAD RL environment, not just a CAD generator. The same verifier can train small models, benchmark frontier agents, and generate adaptive curricula.

## Concrete next build tasks

### Today: environment and rewards

1. Convert the existing CadQuery renderer into a repeatable backend environment call.
2. Add a `runs/<episode_id>/` artifact writer.
3. Add reward JSON output for:
   - build,
   - topology,
   - bbox,
   - semantic parts,
   - screenshots.
4. Add GLB reference preprocessing.
5. Add a one-command smoke test.

### Next: benchmark report

1. Build `scripts/experiment-2/run-gpt-cadquery-benchmark.js` or Python equivalent.
2. Run GPT model for 5 tasks.
3. Save every attempt as Markdown plus images.
4. Summarize improvement with more tool calls.

### Then: OpenEnv wrapper

1. Define observation model:
   - task prompt,
   - current code,
   - last reward,
   - render paths,
   - verifier warnings.
2. Define action model:
   - tool name,
   - patch or code,
   - commit flag.
3. Implement `reset()`.
4. Implement `step(action)`.
5. Add timeout and sandbox limits.
6. Validate with OpenEnv CLI.

### Then: GRPO

1. Create small curriculum dataset.
2. Run formatting SFT if needed.
3. Run GRPO with 4 to 8 samples per prompt.
4. Save checkpoints and eval artifacts.
5. Compare baseline Qwen vs trained Qwen.

## Submission story

Use this structure in the final hackathon README:

1. Problem: LLMs produce plausible but unreliable CAD.
2. Environment: CadQuery tool-use world with persistent geometry state.
3. Rewards: topology-first, reference similarity, editability, process efficiency.
4. Themes: long horizon, professional world modeling, self-improvement, optional multi-agent.
5. Training: GRPO on small Qwen with verifiable rewards.
6. Evidence: GPT benchmark traces plus Qwen before/after curves.
7. Product: CADForge can become a sellable CAD-agent evaluation and training platform.

## What not to do

- Do not train before reward functions are stable.
- Do not optimize only screenshots.
- Do not let similarity beat topology.
- Do not make the first benchmark generic CAD generation.
- Do not promise full FEA for the first demo.
- Do not make the small model write arbitrary long Python without a structured action wrapper.

## Final scope recommendation

The hackathon-winning scope is:

> CadQuery Markus Chair RLVE: a verifiable long-horizon CAD environment where frontier models and small open models iteratively generate, inspect, repair, and improve parametric CAD against a real GLB reference, with GRPO training showing that a tiny Qwen model learns to produce valid chair CAD in fewer revisions.

This is narrow enough to finish and strong enough to sell.
