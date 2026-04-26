---
title: CADForge RLVE
colorFrom: blue
colorTo: green
sdk: docker
pinned: false
app_port: 8791
base_path: /
tags:
  - openenv
  - cadquery
  - grpo
  - rlhf
  - code-cad
---

# CADForge RLVE

### Can a tiny model learn editable CAD by interacting with a real CadQuery build-and-reward environment?

CADForge is a reinforcement learning environment for code-CAD. The agent receives a product/design request, writes executable CadQuery Python, gets a real compiler/render/reward observation back, and learns to repair its CAD over long-horizon revision loops.

The goal is not just text-to-3D mesh generation. The goal is **editable, parametric CAD**: named dimensions, reusable helper functions, final fixture construction, stable topology, semantic parts, and buildable geometry that can survive a professional engineering workflow.

This project targets OpenEnv themes:

- **Theme 2: Long-horizon planning**: CAD improves over repeated code edits and reward feedback.
- **Theme 3.1: Professional world modeling**: the model interacts with real CadQuery tooling, mesh exports, renders, task specs, and persistent artifacts.
- **Theme 4: Self-improvement**: teacher traces, reward failures, and adversarial task generation improve both the model and the environment.

---

## The Story: From Pretty Code to Buildable CAD

### Act 1: The Cold Start

The initial model can often write plausible-looking CadQuery code, but the environment quickly reveals a painful truth: plausible CAD code is not the same thing as executable CAD.

Early generations failed on simple but fatal issues:

- invalid Python syntax
- invented CadQuery APIs such as non-existent `Workplane` methods
- missing `fixture = ...`
- undefined helper variables
- too-long outputs clipped before the final fixture
- disconnected assemblies or oversized gaps

That is exactly why CADForge is an environment, not a static benchmark. The model has to survive a compiler, a mesh pipeline, semantic scoring, and visual/structural comparison.

### Act 2: SFT Teaches the Language of CADQuery

We generated teacher traces and prompt-to-CAD examples from:

- ideal Markus chair CadQuery code
- GPT-5.4/GPT-5.5 agentic repair traces
- prompt-to-CAD cold-start rows
- environment transcripts with previous code, reward JSON, and corrected code

SFT worked clearly. Both Qwen3.5 models learned the shape of editable CADQuery programs.

| Model | Train Loss | Eval Loss | Result |
|---|---:|---:|---|
| Qwen3.5-2B SFT | `1.4480 -> 0.1658` | `0.4477 -> 0.2676` | Learned prompt-to-CAD and repair format |
| Qwen3.5-9B SFT | `2.6020 -> 0.1413` | `0.3650 -> 0.2398` | Stronger syntax/style learning |

![Qwen3.5-9B SFT loss](https://huggingface.co/spaces/sanjuhs/cadforge-cadquery-openenv/resolve/main/training/reports/qwen35-9b-sft-final/sft_loss_curve.png)

### Act 3: First GRPO Run, Too Much Reward Too Soon

The first GRPO reward was intentionally dense. It rewarded build attempts, topology, semantic parts, reference similarity, contact/gap structure, and editability.

That produced positive reward movement:

| Model | Mean Reward | Best Reward | Trend |
|---|---:|---:|---:|
| Qwen3.5-2B GRPO | `0.3387` | `0.5303` | `+0.000887 / step` |
| Qwen3.5-9B GRPO | `0.4355` | `0.6828` | `+0.000475 / step` |

![Qwen3.5-2B GRPO reward](https://huggingface.co/spaces/sanjuhs/cadforge-cadquery-openenv/resolve/main/training/reports/qwen35-2b-grpo-final/grpo_reward_curve.png)

The 2B GRPO run is not the headline result, but it is important evidence. It proved that the tiny model could receive a real CADForge reward signal and move in the right direction. Its weakness was diagnostic: because the dense reward was too generous, the model could improve style and partial structure without reliably crossing the buildability gate.

![Qwen3.5-9B GRPO reward](https://huggingface.co/spaces/sanjuhs/cadforge-cadquery-openenv/resolve/main/training/reports/qwen35-9b-grpo-final/grpo_reward_curve.png)

But training exposed an environment bug in the reward design: the reward was still too forgiving when CadQuery execution failed. The model learned structure and editability signals, but too many completions still failed the real build gate.

This is the same pattern as strong OpenEnv projects: the model's failures teach us where the environment is wrong.

### Act 4: The Environment Fights Back

We tightened GRPO into a **strict build-gated reward**:

- executable CadQuery build is now the first gate
- invalid builds get negative rewards
- syntax errors, missing fixtures, undefined variables, and invented APIs are explicitly penalized
- successful builds recover positive dense rewards for topology, semantics, contact, reference similarity, and editability
- debug logs now store parsed reward JSON directly, instead of inferring build status from truncated stdout

Strict smoke test produced the intended signal:

| Failure | Reward Behavior |
|---|---:|
| Missing final fixture | negative |
| TypeError in helper call | negative |
| SyntaxError | more negative |
| NameError undefined variable | negative |

This gives GRPO useful variance: buildable CAD should separate sharply from pretty-but-broken CAD.

The strict 9B run completed on an H200 and produced exactly that separation:

| Run | Completions | Buildable CAD | Build Rate | Best Candidate Reward | Best CADForge Score |
|---|---:|---:|---:|---:|---:|
| Qwen3.5-9B strict GRPO | `320` | `96` | `30.0%` | `0.9449` | `0.9352` |
| Qwen3.5-9B adaptive repair GRPO final | `180` | `53` | `29.4%` | `0.8817` | `0.8608` |

The raw logs and report artifacts are backed up here:

- Training evidence dataset: [sanjuhs/cadforge-training-evidence](https://huggingface.co/datasets/sanjuhs/cadforge-training-evidence)
- Compressed archive on that dataset: `archives/cadforge-training-evidence-20260426.tar.gz`
- Final adaptive repair report: `training/reports/qwen35-9b-grpo-20260426-adaptive-repair-final-8192/`

![Training evidence build-rate summary](https://huggingface.co/spaces/sanjuhs/cadforge-cadquery-openenv/resolve/main/docs/detailed-blog/rendered-assets/training-evidence-build-rate-summary.png)

The per-step GRPO reward mean stayed lower because failed builds are now intentionally negative. That is good: GRPO now sees the contrast between broken syntax and real executable CAD instead of rewarding both.

---

## How It Works

```
┌─────────────────────────────────────────────────────────────────────┐
│                         CADFORGE RLVE LOOP                          │
│                                                                     │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐             │
│  │ CAD Task      │──►│ Qwen / GPT    │──►│ CadQuery Code │             │
│  │ prompt + ref  │   │ CAD Agent     │   │ candidate     │             │
│  └──────┬───────┘   └──────────────┘   └──────┬───────┘             │
│         │                                      │                     │
│         │            real tools                 ▼                     │
│         │   ┌──────────────────────────────────────────────┐         │
│         └──►│ CadQuery build → STL/mesh → normalize → score │         │
│             └──────────────────────┬───────────────────────┘         │
│                                    │ reward JSON + artifacts          │
│                                    ▼                                  │
│                            SFT traces + GRPO                         │
└─────────────────────────────────────────────────────────────────────┘
```

The environment writes persistent artifacts under each episode:

- candidate code
- build logs
- STL/mesh exports
- normalized mesh metrics
- rendered views
- reward JSON
- markdown reports

---

## Reward Function

CADForge uses layered rewards so the model cannot win with a single shortcut.

| Dimension | What It Checks | Why It Matters |
|---|---|---|
| Build | CadQuery executes and exports geometry | CAD must compile before anything else matters |
| Topology | component count, volume, watertightness, bounds | prevents empty or broken geometry |
| Contact/gaps | disconnected bodies and large separations | chairs/fixtures need plausible physical assembly |
| Semantic parts | task-specific part hints in code and geometry | asks for the requested object, not generic blobs |
| Reference similarity | bbox/profile/silhouette/mesh comparison when GLB exists | aligns generated CAD to target object |
| Editability | named dimensions, helper functions, final fixture, clean structure | rewards reusable engineering CAD |
| Efficiency | compact code and stable build path | discourages bloated or brittle outputs |

Strict GRPO changes the order:

1. Build first.
2. If build fails, return negative reward with small code-structure shaping.
3. If build succeeds, use dense CADForge reward.

This is the important lesson from the first GRPO run: **dense rewards are useful only after the build gate is respected.**

---

## Results

### Run 1: Qwen3.5-2B SFT

The 2B model learned the basic grammar of CADForge traces. It moved from broad, uncertain outputs to compact CadQuery-style responses.

![2B SFT loss](https://huggingface.co/spaces/sanjuhs/cadforge-cadquery-openenv/resolve/main/training/reports/qwen35-2b-sft-final/sft_loss_curve.png)

### Run 1.5: Qwen3.5-2B Dense GRPO

The 2B GRPO run was intentionally included as the small-model learning probe. It reached mean reward `0.3387`, best reward `0.5303`, and a positive trend of `+0.000887 / step`.

That result is useful but incomplete. It shows the small model can respond to CADForge reward, but it also exposed the flaw that dense reward allowed too much credit for non-buildable programs. We used that failure to redesign the environment into strict build-gated GRPO.

![2B dense GRPO reward](https://huggingface.co/spaces/sanjuhs/cadforge-cadquery-openenv/resolve/main/training/reports/qwen35-2b-grpo-final/grpo_reward_curve.png)

![2B dense GRPO code health](https://huggingface.co/spaces/sanjuhs/cadforge-cadquery-openenv/resolve/main/training/reports/qwen35-2b-grpo-final/grpo_code_health.png)

### Run 2: Qwen3.5-9B SFT

The 9B model learned faster and reached better eval loss than 2B.

![9B SFT loss](https://huggingface.co/spaces/sanjuhs/cadforge-cadquery-openenv/resolve/main/training/reports/qwen35-9b-sft-final/sft_loss_curve.png)

### Run 3: Dense GRPO

Dense GRPO improved reward, but still allowed too many non-buildable completions. This run exposed the reward-design flaw.

![9B dense GRPO code health](https://huggingface.co/spaces/sanjuhs/cadforge-cadquery-openenv/resolve/main/training/reports/qwen35-9b-grpo-final/grpo_code_health.png)

### Run 4: Strict Build-Gated GRPO

This run is designed to fix the first GRPO issue. It starts from the 9B SFT checkpoint, not the forgiving GRPO checkpoint, and trains with buildability as the first reward gate.

Completed result:

- `320` completions scored through the real CADForge environment
- `96` completions built successfully
- `30.0%` strict build rate during GRPO
- best individual candidate reward: `0.9449`
- best CADForge total score: `0.9352`
- mean per-step reward trend: `+0.003549 / step`

![Strict 9B GRPO reward](https://huggingface.co/spaces/sanjuhs/cadforge-cadquery-openenv/resolve/main/training/reports/qwen35-9b-grpo-strict-build-20260426-strict-build/grpo_reward_curve.png)

![Strict 9B GRPO code health](https://huggingface.co/spaces/sanjuhs/cadforge-cadquery-openenv/resolve/main/training/reports/qwen35-9b-grpo-strict-build-20260426-strict-build/grpo_code_health.png)

The remaining failures are useful curriculum targets:

| Outcome | Count |
|---|---:|
| SyntaxError | `109` |
| build_ok | `96` |
| TypeError | `25` |
| ValueError | `24` |
| NameError | `24` |
| AttributeError | `21` |

### Quick Held-Out Eval

After upload, the strict adapter was evaluated on 3 prompts:

| Task | Reward | Build | Semantic | Editability |
|---|---:|---:|---:|---:|
| axial_motor_stator_12_slot | `0.708` | `1.0` | `0.300` | `0.825` |
| caster_wheel_fork | `0.738` | `1.0` | `0.452` | `0.942` |
| four_leg_chair_700n | `-1.000` | `0.0` | `0.000` | `0.000` |

Eval summary: **2/3 buildable**, `66.7%` build rate, best reward `0.738`. The failed chair output was clipped before the final union closed, which tells us the next curriculum should target shorter valid finalization and syntax closure.

### Run 5: Adaptive Repair GRPO, Final 8192 Completion Run

The final adaptive repair run closes the self-improvement loop. It starts from the strict build-gated adapter, mines failed strict-GRPO rollouts into repair prompts, and trains the model to rewrite broken CadQuery into complete executable files.

The key comparison is against the earlier adaptive repair attempt. The earlier run had the right idea but the wrong sequence budget: completions clipped before `fixture`, so build rate stayed at `0%`. The final run raised the completion budget to `8192`, kept the prompt compact, and used a foundation-stage repair curriculum.

| Metric | Earlier adaptive repair | Final adaptive repair 8192 |
|---|---:|---:|
| repair completions scored | `120` | `180` |
| buildable repairs | `0` | `53` |
| build rate | `0.0%` | `29.4%` |
| fixture rate | `0.8%` | `97.2%` |
| CadQuery import rate | `96.7%` | `100.0%` |
| clipped completions | `100%` pattern | `0` |
| best candidate reward | `-0.740` | `0.8817` |
| best CADForge total | `-1.000` | `0.8608` |

The failure distribution also changed in the direction we wanted:

| Outcome | Earlier adaptive repair | Final adaptive repair 8192 |
|---|---:|---:|
| build_ok | `0` | `53` |
| SyntaxError | `95` | `12` |
| NameError | `6` | `37` |
| TypeError | `4` | `21` |
| ValueError | `15` | `21` |
| AttributeError | `0` | `18` |

That is a good trade. Syntax closure stopped dominating the run, buildable repairs appeared, and the remaining failures became more specific CAD/Python repair targets.

![Final adaptive repair reward](https://huggingface.co/spaces/sanjuhs/cadforge-cadquery-openenv/resolve/main/reports/20260426-adaptive-repair-final-8192/grpo_reward_curve.png)

![Final adaptive repair code health](https://huggingface.co/spaces/sanjuhs/cadforge-cadquery-openenv/resolve/main/reports/20260426-adaptive-repair-final-8192/grpo_code_health.png)

![Final adaptive repair error breakdown](https://huggingface.co/spaces/sanjuhs/cadforge-cadquery-openenv/resolve/main/reports/20260426-adaptive-repair-final-8192/grpo_error_breakdown.png)

The headline is not that adaptive repair beats strict GRPO on the same benchmark; the tasks are different. The headline is that the environment found a concrete weakness, generated a curriculum for it, and a new run fixed the clipping failure while producing `53` buildable repairs.

---

## Inference Comparison: Base Qwen vs RL-Tuned Qwen vs GPT-5.4

To make the final result concrete, we ran a same-task CadQuery comparison on the medium-difficulty `axial_motor_stator_12_slot` prompt:

> Design a simple 12-slot axial motor stator concept. It should visibly look like a circular stator ring with radial teeth and a center shaft opening. Use steel and keep the structure compact.

The comparison script is [inference/compare_cadquery_models.py](../inference/compare_cadquery_models.py). It can run local Ollama Qwen, score saved trained artifacts, and optionally call a live OpenAI model when `OPENAI_API_KEY` is available.

![Base Qwen vs RL-tuned Qwen vs GPT-5.4](../inference/results/stator-qwen-vs-frontier/comparison.png)

| Model | Source | Total | Build | Semantic | Reference | Editability |
|---|---|---:|---:|---:|---:|---:|
| Base Qwen | local Ollama `qwen3.5:9b` output | `-1.000` | `0.0` | `0.000` | `0.000` | `0.000` |
| RL-tuned Qwen | strict build-gated GRPO held-out stator artifact | `0.654` | `1.0` | `0.300` | `0.067` | `0.825` |
| GPT-5.4 | saved frontier stator artifact | `0.709` | `1.0` | `0.638` | `0.078` | `0.825` |

This is not a broad leaderboard. It is one part-family comparison. But it is the right kind of final evidence: base Qwen failed to produce exportable CAD, while the RL-tuned Qwen produced a buildable, editable stator in the same task family where GPT-5.4 also succeeds.

The honest claim is:

> CADForge makes a small Qwen model competitive on buildable, editable code-CAD behavior for a medium-difficulty mechanical part. GPT-5.4 is still stronger semantically on this single stator example, but the gap is now about part richness and task detail rather than basic executability.

With longer GRPO, more reference-backed tasks, and adaptive curricula focused on semantic subassemblies, this is the path toward small specialist CAD models that can compete with frontier models in a narrower engineering domain.

---

## Model Artifacts

- [Qwen3.5-2B CADForge SFT LoRA](https://huggingface.co/sanjuhs/qwen35-2b-cadforge-sft-lora)
- [Qwen3.5-2B CADForge GRPO LoRA](https://huggingface.co/sanjuhs/qwen35-2b-cadforge-grpo-lora)
- [Qwen3.5-9B CADForge SFT LoRA](https://huggingface.co/sanjuhs/qwen35-9b-cadforge-sft-lora)
- [Qwen3.5-9B CADForge GRPO LoRA](https://huggingface.co/sanjuhs/qwen35-9b-cadforge-grpo-lora)
- [Qwen3.5-9B CADForge Strict Build-Gated GRPO LoRA](https://huggingface.co/sanjuhs/qwen35-9b-cadforge-grpo-strict-build-lora)
- [Qwen3.5-9B CADForge Adaptive Repair GRPO LoRA](https://huggingface.co/sanjuhs/qwen35-9b-cadforge-grpo-adaptive-repair-lora)

---

## Final Hackathon Submission Package

The submission should emphasize four concrete artifacts:

| Artifact | What to show | Why it matters |
|---|---|---|
| Live demo / Space | prompt, CadQuery code, render, reward JSON, repair feedback | proves CADForge is an environment, not just a report |
| Detailed report | SFT, dense GRPO, strict GRPO, adaptive repair results | shows the training story and the reward-design lesson |
| Rendered visual pack | stator, caster, failed chair, reward JSON, charts, code beside render | makes the evidence understandable in one glance |
| Hugging Face adapters | SFT, dense GRPO, strict GRPO, adaptive repair LoRAs | proves the model artifacts were actually persisted |

The strongest final claim is:

> CADForge turned executable CAD failures into reward and curriculum data. Dense reward alone gave 0% buildability; strict build-gated GRPO reached 30.0% buildable completions; adaptive repair then fixed the clipping failure and produced 53/180 buildable repairs with zero clipped completions.

The adaptive repair run started from the **strict build-gated GRPO adapter**, not the original SFT checkpoint. In `training/run_adaptive_repair_grpo.sh`, `BASE_ADAPTER` points to `outputs/qwen35-9b-cadforge-grpo-strict-build-20260426-strict-build`. That matters because adaptive repair is the second stage of RL specialization: first learn buildability, then learn targeted repair.

The report should stay honest about limits:

- it is not production-ready CAD automation yet;
- STL export is working, but STEP export and stricter topology checks are future work;
- the strict held-out eval is small at 3 tasks;
- adaptive repair and strict GRPO use different prompt distributions, so their build rates should not be treated as a direct same-benchmark leaderboard;
- mechanical load analysis is still the next stage after buildability.

That honesty helps the result, because the system can clearly say what it learned and what the next curriculum should target.

---

## Training on RunPod H200

```bash
cd /workspace/open-env-meta-final
export HF_TOKEN=...
export OPENAI_API_KEY=...
export FAL_AI_API_KEY=...

# Full overnight chain used for SFT + GRPO
./training/continue_after_2b_grpo.sh

# Strict build-gated 9B GRPO follow-up
./training/run_strict_9b_grpo.sh

# Final adaptive repair GRPO run
./training/run_adaptive_repair_grpo.sh
```

---

## What We Learned

1. SFT is necessary for CADQuery. Tiny models need to learn the program shape before RL can help.
2. Dense reward alone is too easy to exploit. Buildability must be the first gate.
3. Reward logs need parsed components, not only human-readable stdout tails.
4. Output clipping is a real CAD failure mode. If the model never reaches `fixture = ...`, the geometry cannot build.
5. CADForge should train on repair loops, not only one-shot prompt-to-code. The real skill is diagnosis and correction.
6. The adaptive curriculum loop worked: clipping dropped to zero and repair build rate rose from `0.0%` to `29.4%`.

---

## Next Steps

- Add AST-level syntax checks before CadQuery execution for faster reward.
- Add the next targeted repair curricula for common remaining failures: undefined names, type/value errors, invalid Workplane API, and CAD-kernel exceptions.
- Run strict GRPO with more generations per prompt once build-rate starts moving.
- Add vLLM server mode for higher-throughput Qwen rollouts.
- Evaluate trained adapters against held-out GLB-backed tasks and Markus chair reference similarity.
