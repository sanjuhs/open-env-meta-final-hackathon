# CadQuery Agentic Traces, SFT, and GRPO Plan

## Current truth

The first benchmark was multi-attempt generation, not a full agent loop. The new trace runner is the real loop:

1. Evaluate current CadQuery code.
2. Save reward JSON, rendered views, STL, and verifier report.
3. Send the model the prompt, previous code, reward JSON, and optionally rendered images.
4. Ask for a complete revised CadQuery file.
5. Evaluate the revised code.
6. Save a step transcript for SFT, preference learning, and RL rollouts.

The current GPT-5.4 vision trace improved the Markus repair seed from `0.613` to `0.800` in one edit. The second edit reached `0.794`, so it is a useful negative/preference example: more edits are only good when reward increases.

Qwen 3.5 2B can produce CadQuery-shaped code after `think: false`, but it currently fails builds. That is expected before SFT. Its failed trace is useful because the verifier now exposes concrete Python errors, for example undefined dimensions.

## Data we are collecting

### SFT rows

Path: `experiment-2-cadforge/data/sft/cadquery_agentic_sft.jsonl`

Each row teaches:

- system prompt with CadQuery tool rules
- user observation: task, previous code, reward JSON
- assistant action: corrected complete CadQuery code
- metadata: reward before, reward after, reward delta, artifact path

Use only positive or mildly positive rows for the first SFT pass. Filter with:

- `reward_after > reward_before`
- `reward_after >= 0.70`
- `build == 1`

### Preference rows

Path: `experiment-2-cadforge/data/preferences/cadquery_agentic_preferences.jsonl`

Each row teaches:

- prompt: same observation as SFT
- chosen: higher reward code
- rejected: lower reward code
- chosen/rejected rewards

Use this for DPO/RLHF-style ranking if there is time. For the hackathon, this is also strong evidence that the environment can produce preference data automatically.

### RL rollout rows

Path: `experiment-2-cadforge/data/rl/cadquery_rollouts.jsonl`

Each row teaches:

- state: prompt + code + reward JSON
- action: next CadQuery file
- reward: absolute reward after action
- reward_delta: improvement from previous step
- done: whether this was the last rollout step

This is the GRPO/RLVE substrate. For early GRPO, reward the action with:

```text
step_reward = 0.60 * reward_after
            + 0.35 * max(reward_after - reward_before, -0.25)
            + 0.05 * build_bonus
```

For group-relative training, sample several candidate revisions for the same observation and rank them by `step_reward`.

## Reward design

### Build reward

This is the first gate. If code does not execute or does not export `fixture`, reward is `-1`.

Why it matters: tiny models hallucinate APIs or undefined variables. Penalizing build failures prevents reward hacking through long invalid code.

### Topology reward

Checks mesh health:

- face count sane
- boundary/non-manifold/degenerate ratios low
- component count acceptable for an assembly

For chairs, many parts are allowed. For future single-piece objects, add a stricter single-body mode.

### Contact/gap reward

Checks whether major components are plausibly connected. This catches:

- floating backrest
- disconnected caster assembly
- floating base
- armrests that hover too far away

For chairs, small gaps are not fatal because real chairs have visual separations. Large gaps should hurt.

### Semantic parts reward

Uses code and geometry hints to see whether the model contains chair-like intent:

- seat
- backrest
- headrest
- armrest
- gas cylinder or central column
- star base
- caster proxies
- mechanism/lumbar hints

This should not force exact function names. It should reward discoverable part structure and meaningful dimensions.

### Reference similarity reward

Compares candidate geometry to both:

- IKEA Markus GLB reference
- ideal Markus CadQuery reference

This gives a grounded target while still allowing the generated CadQuery to differ from the exact ideal code.

### Silhouette reward

Compares rendered masks across:

- front
- back
- left
- right
- top
- isometric

This catches shape-level errors faster than pure point-cloud comparison and makes the markdown reports human-readable.

### Editability reward

Rewards code that a future agent can keep editing:

- named dimensions
- helper functions
- final `fixture`
- clear construction blocks
- avoids brittle operations like fragile loft/sweep chains

This is important because the goal is long-horizon CAD editing, not one-shot mesh generation.

## What counts as improvement

Do not reward more steps by itself. Reward useful steps.

Good step:

- code builds
- reward increases
- one major issue is fixed
- model remains editable

Bad step:

- code stops building
- reward decreases sharply
- adds meaningless geometry to game semantic keywords
- bloats code without improving geometry

Long horizon comes from decomposing into many useful edits, not from forcing a fixed number of edits.

## GPT teacher data plan

Use GPT-5.4/GPT-5.5 as teacher agents to generate traces.

Recommended overnight settings:

```bash
scripts/experiment-2/run-cadquery-agentic-trace.js \
  --provider openai \
  --model gpt-5.4 \
  --steps 4 \
  --vision
```

Repeat with different task prompts and seeded failure modes:

- missing armrests
- floating base
- too-short backrest
- failed `loft()` replaced with boxes/cylinders
- disconnected caster assembly
- no final `fixture`
- wrong cylinder height/radius
- overfit blocky chair with no semantics

For each failure mode, GPT sees the reward report and optionally images, repairs the code, and creates training examples automatically.

## Qwen student plan

Start with SFT, not GRPO.

1. Collect 100-300 high-quality GPT repair steps.
2. Filter for positive deltas and successful builds.
3. SFT Qwen 3.5 2B on observation-to-code repair.
4. Run Qwen in the same environment.
5. Keep Qwen traces as before/after evidence.
6. Then run GRPO using reward deltas.

Qwen 0.8B is useful as a dramatic baseline. Qwen 2B is the better hackathon target.

## Generalization plan

The environment can generalize if every object has:

- task prompt
- reference GLB
- optional ideal CadQuery code
- object-specific semantic hints
- reward profile

Object families to add after Markus:

- table
- simple stool
- shelf bracket
- screw/bolt
- hinge
- drawer handle
- caster wheel

For each object, preprocess:

1. Normalize GLB scale/origin/orientation.
2. Extract bounding box, silhouettes, point samples, topology.
3. Evaluate ideal CadQuery if available.
4. Run teacher traces from seeded failures.
5. Add object-specific semantic hints.

## Tomorrow demo story

Show three things:

1. GPT teacher improves a broken CAD file through multiple tool calls.
2. The environment records every observation, action, reward, render, and code revision.
3. Qwen starts weak, then after SFT/GRPO it builds more often and reaches higher reward in fewer edits.

The sellable product is not just "CAD generation." It is a repeatable professional-tool RL environment for teaching small models to use CAD tools over long horizons with persistent state and verifiable rewards.
