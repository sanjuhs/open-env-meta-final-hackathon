# CADForge Training Scripts Bundle

This is the gist-ready source bundle for the CADForge OpenEnv submission.

**Main GitHub repo:** https://github.com/sanjuhs/open-env-meta-final-hackathon  
**HF Space:** https://huggingface.co/spaces/sanjuhs/cadforge-cadquery-openenv  
**Judge-runnable Colab notebook:** https://colab.research.google.com/github/sanjuhs/open-env-meta-final-hackathon/blob/main/training/cadforge_openenv_training_colab.ipynb  
**Training logs and evidence:** https://huggingface.co/datasets/sanjuhs/cadforge-training-evidence

## Important Clarification for Judges

The full training runs were executed on a **RunPod H200** with persistent model/cache directories. The Colab notebook is intentionally a smoke/reproducibility notebook: it validates the OpenEnv app, loads the public dataset, runs the CadQuery reward backend, and launches tiny SFT/GRPO checks using the same scripts.

The production run used shell wrappers so each stage could run in the right Python/UV environment without interfering with CadQuery, TRL, Unsloth, and reward-backend dependencies.

## Exact Training Scripts

| Purpose | File |
|---|---|
| LoRA SFT with Unsloth | [`training/train_sft_unsloth.py`](https://github.com/sanjuhs/open-env-meta-final-hackathon/blob/main/training/train_sft_unsloth.py) |
| GRPO with CADForge reward calls | [`training/train_grpo_cadforge.py`](https://github.com/sanjuhs/open-env-meta-final-hackathon/blob/main/training/train_grpo_cadforge.py) |
| Strict build-gated 9B GRPO run | [`training/run_strict_9b_grpo.sh`](https://github.com/sanjuhs/open-env-meta-final-hackathon/blob/main/training/run_strict_9b_grpo.sh) |
| Adaptive repair GRPO run | [`training/run_adaptive_repair_grpo.sh`](https://github.com/sanjuhs/open-env-meta-final-hackathon/blob/main/training/run_adaptive_repair_grpo.sh) |
| Adaptive repair smoke test | [`training/smoke_adaptive_repair_grpo.sh`](https://github.com/sanjuhs/open-env-meta-final-hackathon/blob/main/training/smoke_adaptive_repair_grpo.sh) |
| Generate mined repair curriculum | [`training/generate_repair_curriculum.py`](https://github.com/sanjuhs/open-env-meta-final-hackathon/blob/main/training/generate_repair_curriculum.py) |
| Evaluate trained CADForge models | [`training/evaluate_cadforge_model.py`](https://github.com/sanjuhs/open-env-meta-final-hackathon/blob/main/training/evaluate_cadforge_model.py) |
| Build charts/reports from logs | [`training/make_training_report.py`](https://github.com/sanjuhs/open-env-meta-final-hackathon/blob/main/training/make_training_report.py) |
| Public notebook | [`training/cadforge_openenv_training_colab.ipynb`](https://github.com/sanjuhs/open-env-meta-final-hackathon/blob/main/training/cadforge_openenv_training_colab.ipynb) |

## Production Run Narrative

1. **SFT stage:** train Qwen3.5 2B and 9B on prompt-to-CadQuery rows plus repair traces.
2. **Dense GRPO stage:** run early GRPO against CADForge reward. This exposed the reward flaw: positive-looking dense reward could still allow non-buildable completions.
3. **Strict build-gated GRPO:** restart from the 9B SFT checkpoint and make buildability the first gate. Failed CAD is negative; successful builds unlock dense topology, semantics, editability, contact, and reference rewards.
4. **Adaptive repair GRPO:** mine strict-GRPO failures into repair classes such as syntax closure, missing fixture, invented API, undefined names, disconnected geometry, and weak semantics.
5. **Final 8192-token adaptive run:** fix clipped completions with larger completion length, persistent HF/model caches, and a staged curriculum.

## Evidence Links

- Training evidence dataset: https://huggingface.co/datasets/sanjuhs/cadforge-training-evidence
- Strict GRPO report: https://huggingface.co/spaces/sanjuhs/cadforge-cadquery-openenv/blob/main/training/reports/qwen35-9b-grpo-strict-build-20260426-strict-build/training_curve_report.md
- Strict GRPO eval report: https://huggingface.co/spaces/sanjuhs/cadforge-cadquery-openenv/blob/main/training/eval/qwen35-9b-cadforge-grpo-strict-build-20260426-strict-build/eval_report.md
- Detailed technical blog: https://huggingface.co/spaces/sanjuhs/cadforge-cadquery-openenv/blob/main/docs/detailed-blog/cadforge-detailed-blog.md

## Optional: Create the GitHub Gist

After authenticating GitHub CLI with gist permission:

```bash
gh auth login --scopes gist,repo
gh gist create training/GITHUB_GIST_TRAINING_SCRIPTS.md \
  training/train_sft_unsloth.py \
  training/train_grpo_cadforge.py \
  training/run_strict_9b_grpo.sh \
  training/run_adaptive_repair_grpo.sh \
  training/generate_repair_curriculum.py \
  training/evaluate_cadforge_model.py \
  --public \
  --desc "CADForge OpenEnv SFT/GRPO training scripts and RunPod H200 evidence"
```
