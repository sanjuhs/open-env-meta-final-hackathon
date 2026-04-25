# Brainstorm 14: CadQuery SFT + GRPO/RLVE Training Plan

Date: 2026-04-25

## Goal

Train a small Qwen3.5 model to act as a CadQuery CAD agent. The model should learn to generate and revise editable chair CAD with fewer failed attempts and fewer revision steps.

The target task is not free-form mesh generation. It is code-CAD tool use:

```text
prompt
-> candidate.py
-> CadQuery build/export
-> mesh + rendered views
-> reward report
-> code edit/revision
-> repeat
-> commit
```

## Why SFT First

GRPO needs nonzero reward. A tiny 0.8B or 2B model may fail before it even reaches CadQuery execution unless we teach the basic format.

SFT is only a warm start. It should teach:

- return complete Python files,
- use `import cadquery as cq`,
- assign a final object to `fixture`,
- avoid unsafe imports and fragile CadQuery APIs,
- organize CAD as functions and named dimensions,
- revise code using verifier feedback.

SFT should not try to memorize the whole ideal chair. Keep it small and behavioral.

## SFT Data

Create examples from:

1. The ideal Markus CadQuery code.
2. GPT-5.4/GPT-5.5 benchmark traces.
3. Handwritten repair examples:
   - missing armrests,
   - floating base,
   - too-short backrest,
   - failed `loft()` replaced with boxes/cylinders,
   - disconnected caster assembly,
   - no final `fixture`.
4. Environment transcripts:
   - prompt,
   - previous code,
   - reward JSON,
   - next corrected code.

Recommended first dataset size:

```text
50 to 200 examples
```

That is enough for format and tool behavior.

## GRPO Setup

Use normal GRPO with vLLM in serve mode on RunPod, as suggested by the judge.

Architecture:

```text
GRPO trainer
-> requests N samples from vLLM server
-> parses candidate code
-> runs CADForge evaluator
-> computes reward
-> updates LoRA adapter
```

For Qwen3.5, avoid vLLM async complications initially. Run vLLM as a plain server and call it synchronously from the rollout function.

Local Ollama is for baseline/debug only. It is not the training backend.

## Reward Modes

Use two reward modes:

### Fast Mode

Used for most rollout candidates.

Scores:

- build success,
- topology sanity,
- contact/gap score,
- semantic/code structure,
- bbox similarity,
- editability.

Does not write colored screenshots or run expensive point-cloud/silhouette scoring.

### Full Mode

Used for:

- final commit,
- every N training steps,
- benchmark reports,
- judge artifacts.

Scores:

- everything from fast mode,
- colored view renders,
- silhouette IoU,
- Chamfer-style point-cloud similarity,
- candidate vs ideal CadQuery,
- candidate vs GLB.

## Reward Functions

### Build Reward

High only if:

- code executes,
- CadQuery object exists,
- STL export succeeds,
- mesh loads.

Hard failure:

```text
reward = -1.0
```

if code cannot run or no mesh exports.

### Topology Reward

Checks mesh health:

- component count,
- watertightness,
- boundary edges,
- non-manifold edges,
- degenerate faces,
- face count sanity.

For chairs, many components can be okay because a chair is an assembly. For monolithic hooks/brackets, this should become stricter later.

### Contact/Gap Reward

This handles the important chair case:

- small assembly gaps are tolerated,
- large separated parts are penalized,
- lots of floating components are bad.

This prevents a model from making a plausible-looking chair where the base, back, or armrests float far away.

### Semantic Reward

Checks whether the candidate behaves like a Markus-style chair:

- code mentions and organizes chair concepts,
- proportions are chair-like,
- there is a tall upper body/back region,
- there is lower base spread,
- code is split into reusable functions.

This is hackable if used alone, so it is never the only reward.

### Reference Similarity

Compares the candidate to:

1. ideal CadQuery reference,
2. real Markus GLB.

Signals:

- bbox proportions,
- point-cloud distance,
- silhouette similarity.

The ideal CadQuery reference is the gold code target. The GLB is the real-world visual target.

### Editability Reward

Rewards:

- functions,
- named dimensions,
- returns from helper builders,
- final object assignment.

Later this should become stronger by actually mutating parameters and rebuilding.

### Efficiency Reward

For multi-step episodes:

- fewer failed CadQuery builds,
- fewer tool calls,
- fewer repeated edits,
- higher reward with fewer revisions.

This is where the final product claim comes from:

> After GRPO, the small model reaches a good CadQuery chair in fewer revisions.

## Reward Hacking Risks

Known risks:

- naming a variable `backrest` without real geometry,
- making a giant bounding-box slab,
- making visually close but non-editable geometry,
- creating many disconnected decorative parts,
- overfitting to the ideal code,
- using APIs that work once but break under edits.

Mitigations:

- final full reward uses silhouettes and point clouds,
- contact/gap reward punishes large separation,
- editability reward punishes one-off blobs,
- holdout tasks change dimensions and requirements,
- inspect rendered reports often.

## How We Know It Is Improving

Do not trust only average training reward.

Track:

- build success rate,
- best full reward on fixed holdout prompts,
- average revisions to reach reward greater than 0.75,
- contact/gap score,
- silhouette score,
- editability score,
- failure categories,
- rendered Markdown reports before and after training.

Main demo metric:

```text
Baseline Qwen: needs many attempts, often fails build/contact.
Trained Qwen: builds earlier, fewer gaps, better full reward, fewer revisions.
```

## Local Baseline With Ollama

Use Ollama to see what 0.8B and 2B can do before training:

```bash
scripts/experiment-2/run-gpt-cadquery-benchmark.js \
  --run \
  --provider ollama \
  --model qwen3.5:0.8b \
  --tasks 1 \
  --attempts 1 \
  --timeout-ms 180000
```

The benchmark caps generation with `num_predict`, disables streaming, and has a timeout so a small model cannot hang forever.

## RunPod Training Plan

Only start RunPod after:

- local Ollama baselines run,
- reward reports look sensible,
- SFT examples exist,
- the evaluator survives 20 to 100 episodes.

RunPod jobs:

1. SFT warm start on 50 to 200 examples.
2. GRPO Stage 1 on easy build/topology tasks.
3. GRPO Stage 2 on Markus-chair reward.
4. Full benchmark report against baseline Qwen and GPT-5.4.

Use vLLM serve mode for rollouts, not async mode, for the first stable GRPO run.

## Immediate Next Steps

1. Run Ollama 0.8B baseline.
2. Run Ollama 2B baseline when download finishes.
3. Save both reports with rendered images.
4. Create first SFT JSONL from ideal code and GPT traces.
5. Build a minimal GRPO script that calls the evaluator.
6. Move to RunPod.
