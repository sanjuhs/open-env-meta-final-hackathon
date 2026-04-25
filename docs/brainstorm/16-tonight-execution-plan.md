# CADForge Tonight Execution Plan

## Time Budget

You have 3-5 focused hours before overnight training. Use them like this:

| Block | Time | Goal |
|---|---:|---|
| Reward sanity + task setup | 30-45 min | Confirm task-specific rewards and prompts work. Done for Markus + six-leg table. |
| Asset generation | 60-120 min wall time | Generate 20-24 white-background reference images and optionally FAL GLBs in parallel. |
| Teacher traces | 90-180 min wall time | Run GPT-5.4/GPT-5.5 agentic repair traces, 2-4 steps each. |
| SFT packaging | 20-40 min | Filter positive deltas, make train/val JSONL, quick dataset card. |
| RunPod setup | 30-60 min | Start Qwen 2B/9B SFT. If SFT finishes, start GRPO. |
| README + demo assets | 60-120 min | Results table, trace screenshots, short video, slides. |

Overnight from 12am-6am:

1. SFT Qwen 2B or 9B on positive GPT repair traces.
2. Evaluate the tuned model on held-out tasks.
3. If build rate is non-zero, run GRPO with grouped repair candidates.
4. Save reward/loss curves and before/after traces.

## Are Qwen 0.8B/2B Too Dumb?

They are not useless, but they are too cold for raw CAD repair. Qwen 2B currently writes CadQuery-shaped code but fails on undefined variables and API mistakes. That means:

- Do SFT first.
- Use Qwen 0.8B as a weak baseline.
- Use Qwen 2B as the realistic small-model demo.
- Downloading Qwen 9B is a good idea if you can afford the inference/training memory, because it should produce more buildable rollouts for GRPO.

## What Is Graded Per Step?

Each agentic step is graded independently:

- previous code
- reward JSON
- rendered views if available
- next code
- next reward
- reward delta

The training data records:

- SFT: observation -> improved code
- Preference/RLHF: chosen higher-reward code vs rejected lower-reward code
- RL/GRPO: observation, action, reward, reward_delta

Do not reward more steps by itself. Reward useful improvement:

```text
step_reward = 0.60 * reward_after
            + 0.35 * clamp(reward_after - reward_before, -0.25, 0.25)
            + 0.05 * build_success
```

## Current Reward Functions

### Build

Hard gate. Invalid code or missing STL gets `-1`. This catches hallucinated CadQuery APIs, undefined variables, no final `fixture`, and execution crashes.

### Topology

Checks mesh health: faces, components, watertightness, boundaries, non-manifold edges, and degenerate faces. Assemblies can have multiple components; future monolithic tasks should use stricter settings.

### Contact/Gaps

Penalizes large disconnected components. Small chair/table gaps are tolerated; floating bases, detached backrests, disconnected caster assemblies, and floating load bosses lose reward.

### Task Semantics

Now task-specific. A stator is rewarded for `stator`, `radial_tooth`, `center_bore`; a table is rewarded for `tabletop`, `leg`, `crossbar`, `stretcher`. This fixes the previous Markus-only bias.

### Reference Similarity

If a task GLB exists, the evaluator compares bbox, point-cloud similarity, and silhouettes. If no GLB exists yet, this component is neutral and the report says so explicitly.

### Silhouette

Full mode renders front/back/left/right/top/isometric masks. These are used for scoring when a GLB reference exists and are always saved for human inspection.

### Editability

Rewards named dimensions, helper functions, clean final `fixture`, and reusable code structure. This matters because the project is about long-horizon editable CAD, not just one-shot meshes.

## Commands

Generate reference images and FAL GLBs for the first 8 tasks:

```bash
scripts/experiment-2/generate-cad-assets.js --limit 8 --concurrency 3
```

Use FAL text-to-3D only, fastest path:

```bash
scripts/experiment-2/generate-cad-assets.js --skip-images --limit 8 --concurrency 4
```

Use image-to-3D after GPT images:

```bash
scripts/experiment-2/generate-cad-assets.js --limit 8 --concurrency 2 --image-to-3d
```

Run teacher traces on easy tasks:

```bash
scripts/experiment-2/run-teacher-trace-batch.js --provider openai --model gpt-5.4 --levels easy --limit 8 --steps 3
```

Run richer vision traces after images/renders exist:

```bash
scripts/experiment-2/run-teacher-trace-batch.js --provider openai --model gpt-5.4 --levels easy,medium --limit 12 --steps 4 --vision
```

Filter positive SFT rows:

```bash
scripts/experiment-2/filter-positive-sft.js --min-after 0.70 --min-delta 0.001
```

Run Qwen baseline:

```bash
scripts/experiment-2/run-cadquery-agentic-trace.js --provider ollama --model qwen3.5:2b --task-spec table_six_leg_500n --task-id table_six_leg_500n --steps 1
```

## Submission Story

The story should mirror the best example project:

1. Cold start: Qwen fails to emit valid CadQuery.
2. Environment: CAD code executes in real CadQuery, renders, and scores every step.
3. Teacher: GPT-5.4/GPT-5.5 improves broken CAD over multiple tool calls.
4. Data: every observation/action/reward becomes SFT, preference, and RL rollout data.
5. Student: Qwen learns to build valid editable CAD in fewer revisions.
6. Self-improvement: new object prompts + generated GLBs expand the curriculum automatically.
