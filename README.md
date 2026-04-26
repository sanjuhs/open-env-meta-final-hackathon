# CADForge RLVE

CADForge is an OpenEnv environment for training LLMs to produce **editable, buildable CadQuery CAD** instead of one-shot decorative meshes.

The agent receives a design request, writes a complete CadQuery Python file, and the environment runs real tools: CadQuery build, STL export, mesh/topology checks, semantic scoring, reference similarity, editability checks, and artifact logging. The training target is long-horizon CAD repair: generate, observe reward JSON, fix syntax/topology/semantic failures, and improve.

## Submission Links

- Hugging Face Space: [sanjuhs/cadforge-cadquery-openenv](https://huggingface.co/spaces/sanjuhs/cadforge-cadquery-openenv)
- Training notebook on the HF Space: [training/cadforge_openenv_training_colab.ipynb](https://huggingface.co/spaces/sanjuhs/cadforge-cadquery-openenv/blob/main/training/cadforge_openenv_training_colab.ipynb)
- Open the training notebook in Google Colab: [Colab training notebook](https://colab.research.google.com/github/sanjuhs/open-env-meta-final-hackathon/blob/main/training/cadforge_openenv_training_colab.ipynb)
- Mini-blog markdown: [experiment-2-cadforge/CADFORGE_BLOG.md](experiment-2-cadforge/CADFORGE_BLOG.md)
- Judge rerun notebook in this repo: [training/cadforge_openenv_training_colab.ipynb](training/cadforge_openenv_training_colab.ipynb)
- Full project report: [docs/cadforge-openenv-project-report.md](docs/cadforge-openenv-project-report.md)
- Self-improving curriculum: [docs/cadforge-self-improving-curriculum.md](docs/cadforge-self-improving-curriculum.md)
- Inference comparison: [inference/results/stator-qwen-vs-frontier/report.md](inference/results/stator-qwen-vs-frontier/report.md)
- Submission checklist: [docs/cadforge-submission-checklist.md](docs/cadforge-submission-checklist.md)
- Training dataset: [sanjuhs/cadforge-cadquery-agentic-traces](https://huggingface.co/datasets/sanjuhs/cadforge-cadquery-agentic-traces)
- Training logs and evidence bundle: [sanjuhs/cadforge-training-evidence](https://huggingface.co/datasets/sanjuhs/cadforge-training-evidence)
- Strict GRPO model: [sanjuhs/qwen35-9b-cadforge-grpo-strict-build-lora](https://huggingface.co/sanjuhs/qwen35-9b-cadforge-grpo-strict-build-lora)
- Adaptive repair GRPO model: [sanjuhs/qwen35-9b-cadforge-grpo-adaptive-repair-lora](https://huggingface.co/sanjuhs/qwen35-9b-cadforge-grpo-adaptive-repair-lora)

## Why This Matters

Current LLMs can describe CAD objects, but tiny models often fail at professional code-CAD basics:

- invalid Python syntax
- invented CadQuery APIs
- missing final `fixture`
- disconnected parts
- clipped output before the final object is assembled
- low editability even when a mesh exists

CADForge turns those failures into reward. The environment is intentionally strict: broken CAD gets negative reward, while buildable, connected, semantically meaningful, editable CAD gets dense positive reward.

## Hackathon Theme Alignment

- **Theme 2: Long-horizon planning**: CAD is improved across revision loops, not solved by one token burst.
- **Theme 3.1: Professional world modeling**: the model interacts with real CadQuery, mesh export, task specs, persistent artifacts, and reward JSON.
- **Theme 4: Self-improvement**: failures become new curriculum. The strict run was created because the first dense reward was too forgiving.
- **Theme 5: Wild Card**: editable CAD generation is a practical, underexplored RLVE target with a clear commercial path.

## Evidence of Real Training

We trained Qwen3.5 2B and 9B adapters with SFT, then ran GRPO against the CADForge environment on a RunPod H200.

| Run | Result |
|---|---|
| Qwen3.5-2B SFT | train loss `1.4480 -> 0.1658`, eval loss `0.4477 -> 0.2676` |
| Qwen3.5-9B SFT | train loss `2.6020 -> 0.1413`, eval loss `0.3650 -> 0.2398` |
| Qwen3.5-9B strict GRPO | `320` completions, `96` buildable, best CADForge score `0.9352` |
| Qwen3.5-9B adaptive repair GRPO | `180` repair completions, `53` buildable, `0` clipped completions |
| Strict 9B quick eval | `2/3` held-out prompts built successfully |
| Final stator inference comparison | base Qwen failed build; RL-tuned Qwen built a `0.654` stator; GPT-5.4 built a `0.709` stator |

![Training evidence build-rate summary](docs/detailed-blog/rendered-assets/training-evidence-build-rate-summary.png)

![Strict GRPO reward curve](training/reports/qwen35-9b-grpo-strict-build-20260426-strict-build/grpo_reward_curve.png)

![Strict GRPO code health](training/reports/qwen35-9b-grpo-strict-build-20260426-strict-build/grpo_code_health.png)

![Final adaptive repair chunk metrics](docs/detailed-blog/rendered-assets/adaptive-final-8192-chunk-metrics.png)

![Base Qwen vs RL-tuned Qwen vs GPT-5.4 stator comparison](inference/results/stator-qwen-vs-frontier/comparison.png)

## Training Logs

Judges can inspect the raw training evidence here:

- Hugging Face evidence dataset: [sanjuhs/cadforge-training-evidence](https://huggingface.co/datasets/sanjuhs/cadforge-training-evidence)
- Compressed archive on the dataset: `archives/cadforge-training-evidence-20260426.tar.gz`
- Local working-copy backup, if this repo was prepared from the hackathon machine: `training/backups/cadforge-training-evidence-20260426`

The most useful files are `training/logs/*completions.jsonl` for per-sample rewards and `training/reports/*/*.png` for the judge-facing plots. The logs support the story directly: dense GRPO had positive-looking rewards but `0%` build rate, strict build-gating produced `96/320` buildable CAD completions, and the final adaptive repair run fixed the clipped-output failure with `53/180` buildable repairs.

## OpenEnv Environment

The environment lives in [experiment-2-cadforge](experiment-2-cadforge).

```bash
cd experiment-2-cadforge
../.venv/bin/openenv validate .
PYTHONPATH=python_tools ../.venv/bin/uvicorn server.app:app --host 0.0.0.0 --port 8000
```

Push to Hugging Face Spaces:

```bash
cd experiment-2-cadforge
set -a; source ../.env; set +a
../.venv/bin/openenv push . --repo-id sanjuhs/cadforge-cadquery-openenv --interface
```

## Training

The production training scripts are in [training](training). The notebook wraps these scripts so judges can rerun smoke tests or full runs:

```bash
uv run training/train_sft_unsloth.py --help
uv run training/train_grpo_cadforge.py --help
uv run training/evaluate_cadforge_model.py --help
training/run_strict_9b_grpo.sh
```

The final strict build-gated GRPO reward is the key design change: failed builds receive negative reward; successful builds unlock dense topology, semantic, reference, and editability scoring.

The adaptive repair run then starts from the strict build-gated GRPO adapter, not the original SFT checkpoint. It specializes the already build-aware model on mined repair failures.

## Self-Improvement Loop

CADForge's next curriculum is generated from the model's own failures:

```text
rollout batch -> reward JSON -> failure classifier -> targeted repair task -> adaptive sampler -> next GRPO batch
```

For example, a clipped chair answer with `SyntaxError: '(' was never closed` becomes a repair task that asks the model to preserve the structure, close the final union, and assign `fixture`. The next score is based on reward delta, so the environment teaches the model exactly where it failed.
