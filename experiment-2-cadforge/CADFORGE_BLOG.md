# CADForge: Training Tiny Models to Write Buildable CADQuery

Detailed judge-facing blog with screenshots, diagrams, references, and all run interpretation:

[docs/detailed-blog/cadforge-detailed-blog.md](docs/detailed-blog/cadforge-detailed-blog.md)

## Judge Reproducibility Links

- **GitHub repo:** [sanjuhs/open-env-meta-final-hackathon](https://github.com/sanjuhs/open-env-meta-final-hackathon)
- **GitHub Gist: training scripts:** [CADForge OpenEnv SFT/GRPO scripts](https://gist.github.com/sanjuhs/10596f688e8b4560910a3b1b137bfeeb)
- **Google Colab smoke notebook:** [cadforge_openenv_training_colab.ipynb](https://colab.research.google.com/github/sanjuhs/open-env-meta-final-hackathon/blob/main/training/cadforge_openenv_training_colab.ipynb)
- **Raw training logs and evidence:** [sanjuhs/cadforge-training-evidence](https://huggingface.co/datasets/sanjuhs/cadforge-training-evidence)

The full SFT and GRPO runs were executed on a RunPod H200 through distinct production scripts. The Colab notebook is the public judge-runnable smoke path that validates the same OpenEnv, dataset, reward backend, and training entry points on a tiny run.

## The Problem

LLMs can describe a chair, bracket, hook, or motor stator, but tiny models are still unreliable at producing CAD that an engineer can actually use.

The common failure mode is not imagination. It is execution:

- the code has a syntax error
- the model invents a CadQuery API
- the final `fixture` is missing
- the geometry exports but contains disconnected parts
- the shape looks roughly correct but has no editable dimensions or helper structure
- the answer is clipped before the final assembly is complete

CADForge turns those failures into a reinforcement learning environment.

The agent receives a professional design prompt and must output a complete executable CadQuery Python file. CADForge compiles it, exports geometry, scores topology and task semantics, writes artifacts, and returns reward JSON. The goal is not a pretty one-shot mesh. The goal is **editable, buildable code-CAD**.

## Why This Fits OpenEnv

CADForge targets three hackathon themes.

**Theme 2: Long-horizon planning.** A CAD model is naturally built through steps: make a base shape, add supports, add constraints, connect parts, repair broken operations, simplify brittle features, and finalize the object. The environment supports long-horizon repair traces where the model sees previous code, reward JSON, and verifier notes before producing the next revision.

**Theme 3.1: Professional world modeling.** The world is not a toy simulator. The model interacts with real CadQuery execution, mesh export, reference objects, task specs, and persistent artifacts. If the code does not build, the environment says so.

**Theme 4: Self-improvement.** The first reward design was too forgiving. Training exposed that flaw, so we tightened the environment: buildability became the first gate, broken code became negative reward, and individual failure types became curriculum targets.

## The Environment Loop

```text
design prompt
  -> LLM writes CadQuery Python
  -> CADForge runs CadQuery
  -> STL/mesh/artifacts are produced
  -> reward JSON scores build, topology, contact, semantics, reference similarity, editability
  -> model trains through SFT and GRPO
```

Each episode writes persistent artifacts:

- generated CadQuery code
- build logs
- STL/mesh outputs
- rendered views when available
- reward JSON
- verifier notes
- markdown summaries

## Reward Design

CADForge uses layered reward instead of a single pass/fail bit.

| Dimension | What It Checks | Why It Matters |
|---|---|---|
| Build | CadQuery executes and exports geometry | no professional CAD workflow starts from broken code |
| Topology | volume, bounds, connectedness, watertight proxy | prevents empty or incoherent geometry |
| Contact | disconnected assemblies and large gaps | chairs, fixtures, and hooks must be physically plausible |
| Semantic parts | task-specific shape hints | a chair should have chair-like structure, not a generic block |
| Reference similarity | bbox/silhouette/mesh comparison when a GLB exists | supports object-specific CAD imitation |
| Editability | named dimensions, helper functions, final fixture | rewards real code-CAD, not opaque mesh blobs |
| Efficiency | compact, stable output | discourages bloated brittle programs |

The final strict GRPO run changed the reward order:

1. Build first.
2. If build fails, return negative reward with diagnostics.
3. If build succeeds, unlock the dense CADForge score.

This is the environment "fighting back." The model can no longer get meaningful reward for pretty-looking text that does not compile.

## Training Data

We used:

- prompt-to-CadQuery cold-start examples
- GPT-5.4/GPT-5.5 teacher repair traces
- ideal Markus chair CadQuery code
- environment transcripts with previous code, reward JSON, and corrected code
- generated CAD prompts across easy, medium, and hard mechanical objects

Dataset: [sanjuhs/cadforge-cadquery-agentic-traces](https://huggingface.co/datasets/sanjuhs/cadforge-cadquery-agentic-traces)

The SFT mix upsampled cold-start rows because repair traces outnumbered fresh prompt-to-CAD examples. Upsampling means repeating those rows so the model still learns to create the first complete CAD file, not only repair an existing one.

## Training Pipeline

The runnable notebook is here:

[training/cadforge_openenv_training_colab.ipynb](training/cadforge_openenv_training_colab.ipynb)

The production scripts are:

- `training/train_sft_unsloth.py`
- `training/train_grpo_cadforge.py`
- `training/evaluate_cadforge_model.py`
- `training/make_training_report.py`
- `training/run_strict_9b_grpo.sh`

The real run used Unsloth for LoRA SFT and TRL GRPO for environment reward training on a RunPod H200.

## Training Logs and Evidence

The raw logs are public so the training claims are inspectable, not just summarized:

- Training evidence dataset: [sanjuhs/cadforge-training-evidence](https://huggingface.co/datasets/sanjuhs/cadforge-training-evidence)
- Compressed archive on that dataset: `archives/cadforge-training-evidence-20260426.tar.gz`
- Per-sample reward traces: `training/logs/*completions.jsonl`
- Generated plots and parsed metrics: `training/reports/*`

The most important thing the logs show is that reward alone was not enough. The dense GRPO runs had positive-looking scalar reward but `0%` buildability. The strict build-gated run changed the environment so broken CAD stayed negative and buildable CAD unlocked dense reward. The final adaptive run then mined failures from strict GRPO and trained directly on repair prompts.

![Training evidence build-rate summary](https://huggingface.co/spaces/sanjuhs/cadforge-cadquery-openenv/resolve/main/docs/detailed-blog/rendered-assets/training-evidence-build-rate-summary.png)

## Results

| Run | Result |
|---|---|
| Qwen3.5-2B SFT | train loss `1.4480 -> 0.1658`, eval loss `0.4477 -> 0.2676` |
| Qwen3.5-2B dense GRPO | mean reward `0.3387`, best `0.5303`; useful reward signal but too forgiving on broken builds |
| Qwen3.5-9B SFT | train loss `2.6020 -> 0.1413`, eval loss `0.3650 -> 0.2398` |
| Qwen3.5-9B strict GRPO | `320` completions, `96` buildable, `30.0%` build rate |
| Qwen3.5-9B adaptive repair v1 | `120` repair completions, `0` buildable; exposed clipped completions and bad curriculum ordering |
| Qwen3.5-9B adaptive repair final 8192 | `180` repair completions, `53` buildable, `0` clipped completions, best reward `0.882` |
| Strict 9B quick eval | `2/3` held-out prompts built successfully |

The strict GRPO run produced:

- best individual reward: `0.9449`
- best CADForge total score: `0.9352`
- mean per-step reward trend: `+0.003549 / step`
- held-out eval build rate: `66.7%`

![Strict GRPO reward curve](https://huggingface.co/spaces/sanjuhs/cadforge-cadquery-openenv/resolve/main/training/reports/qwen35-9b-grpo-strict-build-20260426-strict-build/grpo_reward_curve.png)

![Strict GRPO code health](https://huggingface.co/spaces/sanjuhs/cadforge-cadquery-openenv/resolve/main/training/reports/qwen35-9b-grpo-strict-build-20260426-strict-build/grpo_code_health.png)

![Final adaptive repair chunk metrics](https://huggingface.co/spaces/sanjuhs/cadforge-cadquery-openenv/resolve/main/docs/detailed-blog/rendered-assets/adaptive-final-8192-chunk-metrics.png)

## What The Model Learned

SFT taught the model the language of editable CadQuery:

- named dimensions
- helper builders
- final `fixture`
- compact Python-only output
- simple robust CadQuery operations

Strict GRPO then taught it the first hard constraint: **buildable CAD is categorically better than broken CAD**.

The quick eval built two held-out objects:

| Task | Reward | Build | Editability |
|---|---:|---:|---:|
| axial_motor_stator_12_slot | `0.708` | `1.0` | `0.825` |
| caster_wheel_fork | `0.738` | `1.0` | `0.942` |
| four_leg_chair_700n | `-1.000` | `0.0` | `0.000` |

The failed chair output was clipped before closing the final union. That failure is useful: it gives the next curriculum a concrete target.

## How CADForge Improves Itself

The self-improvement loop is automatic: the environment uses failed rollouts to create the next training distribution.

```text
rollout batch
  -> reward JSON
  -> failure classifier
  -> targeted repair task generator
  -> adaptive sampler
  -> next SFT / GRPO batch
```

Examples:

- `SyntaxError: '(' was never closed` becomes: "preserve the current chair structure, close the final union, and assign fixture."
- `AttributeError: Workplane has no cone` becomes: "replace the invented API with cylinders, boxes, lofts, or cuts that CadQuery supports."
- disconnected caster assembly becomes: "bridge the wheel, axle, fork, and top plate so contact reward improves."
- weak Markus similarity becomes: "adjust the backrest height, armrests, gas cylinder, star base, and caster proportions."

The next action is scored by reward delta:

```text
delta_reward = new_total_reward - previous_total_reward
```

This prevents the model from merely restating plausible CAD. It must repair the concrete failure the environment found.

The curriculum controller then samples more from weak failure types:

```text
weight = base_weight * (1 - recent_mastery)^2 * difficulty_multiplier
```

So if the model keeps failing syntax closure, syntax repair appears more often. Once build rate rises, the environment shifts toward harder semantic and reference-similarity tasks.

That turns CADForge into a curriculum engine: the environment watches where the model fails and creates the next training distribution from those failures.

Detailed plan: [docs/cadforge-self-improving-curriculum.md](docs/cadforge-self-improving-curriculum.md)

## Artifacts

- Space: [sanjuhs/cadforge-cadquery-openenv](https://huggingface.co/spaces/sanjuhs/cadforge-cadquery-openenv)
- Dataset: [sanjuhs/cadforge-cadquery-agentic-traces](https://huggingface.co/datasets/sanjuhs/cadforge-cadquery-agentic-traces)
- Qwen3.5-2B SFT: [sanjuhs/qwen35-2b-cadforge-sft-lora](https://huggingface.co/sanjuhs/qwen35-2b-cadforge-sft-lora)
- Qwen3.5-2B GRPO: [sanjuhs/qwen35-2b-cadforge-grpo-lora](https://huggingface.co/sanjuhs/qwen35-2b-cadforge-grpo-lora)
- Qwen3.5-9B SFT: [sanjuhs/qwen35-9b-cadforge-sft-lora](https://huggingface.co/sanjuhs/qwen35-9b-cadforge-sft-lora)
- Qwen3.5-9B GRPO: [sanjuhs/qwen35-9b-cadforge-grpo-lora](https://huggingface.co/sanjuhs/qwen35-9b-cadforge-grpo-lora)
- Qwen3.5-9B strict GRPO: [sanjuhs/qwen35-9b-cadforge-grpo-strict-build-lora](https://huggingface.co/sanjuhs/qwen35-9b-cadforge-grpo-strict-build-lora)
- Qwen3.5-9B adaptive repair GRPO: [sanjuhs/qwen35-9b-cadforge-grpo-adaptive-repair-lora](https://huggingface.co/sanjuhs/qwen35-9b-cadforge-grpo-adaptive-repair-lora)
- Training evidence bundle: [sanjuhs/cadforge-training-evidence](https://huggingface.co/datasets/sanjuhs/cadforge-training-evidence)

## Adaptive Repair Curriculum

After strict GRPO, CADForge mined the `320` completion traces and generated a new adaptive repair curriculum. The curriculum found the dominant failure class automatically:

| Failure class | Count |
|---|---:|
| syntax closure | `110` |
| type/value/CAD kernel errors | `47` |
| disconnected or weak geometry | `26` |
| undefined names | `20` |
| invented API | `17` |
| missing fixture | `15` |
| unknown build failure | `15` |
| low editability | `4` |

The first adaptive run was useful because it failed loudly: `120` repair completions produced `0` builds and showed clipped outputs. We fixed the curriculum and completion budget, reran it as `20260426-adaptive-repair-final-8192`, and got `53/180` buildable repairs with `0` clipped completions. That is the self-improvement loop in miniature: the environment found a concrete weakness, generated a targeted repair distribution, and the next run improved that failure mode.
