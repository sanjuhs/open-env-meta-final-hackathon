# CADForge Submission Checklist

## Non-Negotiables

| Requirement | Status | File / Link |
|---|---|---|
| OpenEnv environment | done | `experiment-2-cadforge/openenv.yaml` |
| Hugging Face Space | ready to push | `sanjuhs/cadforge-cadquery-openenv` |
| Training notebook | done | `training/cadforge_openenv_training_colab.ipynb` |
| Unsloth / TRL scripts | done | `training/train_sft_unsloth.py`, `training/train_grpo_cadforge.py` |
| Evidence of training | done | `training/reports/qwen35-9b-grpo-strict-build-20260426-strict-build/` |
| Raw training logs | done | [sanjuhs/cadforge-training-evidence](https://huggingface.co/datasets/sanjuhs/cadforge-training-evidence) |
| Final adaptive repair evidence | done | `training/reports/qwen35-9b-grpo-20260426-adaptive-repair-final-8192/` |
| Final inference comparison | done | `inference/results/stator-qwen-vs-frontier/report.md` |
| Separate HF blog markdown | done | `experiment-2-cadforge/CADFORGE_BLOG.md` |
| README links to all materials | done | `README.md`, `experiment-2-cadforge/README.md` |

## What To Push To The HF Space

Push from the Space root:

```bash
cd experiment-2-cadforge
set -a; source ../.env; set +a
../.venv/bin/openenv validate .
../.venv/bin/openenv push . --repo-id sanjuhs/cadforge-cadquery-openenv --interface
```

The HF Space should include:

- `README.md`
- `CADFORGE_BLOG.md`
- `openenv.yaml`
- server/client environment code

Do not upload large videos to the Space. Link to YouTube if a video is made.

## Judge Story

CADForge teaches an LLM to write buildable, editable CADQuery by interacting with a real CAD compiler and verifier.

The strongest 30-second story:

1. Base tiny models can write plausible CAD text, but much of it does not compile.
2. SFT teaches the model the shape of editable CadQuery programs.
3. First GRPO exposed a reward bug: dense reward was too forgiving.
4. The environment fought back with strict build gating.
5. Strict GRPO produced `96/320` buildable completions and a best CADForge score of `0.9352`.
6. Adaptive repair started from the strict-GRPO adapter and fixed the clipping failure: `53/180` buildable repairs with `0` clipped completions.
7. Final stator inference shows the product shape: base Qwen failed build, RL-tuned Qwen built editable CAD, and GPT-5.4 remained a strong frontier baseline.

## Training Log Narrative

Use this evidence arc if judges ask whether training really happened:

| Run | Log evidence | Interpretation |
|---|---|---|
| 2B SFT | `training/reports/qwen35-2b-sft-final/` | tiny model learns CadQuery grammar and trace format |
| 2B dense GRPO | `training/logs/grpo-2b-completions.jsonl` | reward moved, but `0/160` builds exposed forgiving reward |
| 9B SFT | `training/reports/qwen35-9b-sft-final/` | stronger syntax/style learning |
| 9B dense GRPO | `training/logs/grpo-9b-completions.jsonl` | bigger model got higher reward but still `0/160` builds |
| 9B strict GRPO | `training/logs/grpo-9b-strict-build-20260426-strict-build-completions.jsonl` | build-gated reward produced `96/320` buildable completions |
| Adaptive v1 | `training/logs/grpo-9b-20260426-adaptive-repair-completions.jsonl` | failed run exposed clipping and curriculum bug |
| Adaptive final 8192 | `training/logs/grpo-9b-20260426-adaptive-repair-final-8192-completions.jsonl` | fixed setup produced `53/180` buildable repairs |

## Remaining Optional Polish

- Add a <2 minute YouTube link to both READMEs if you record one.
- Add the HF Space URL after pushing/confirming the live Space.
- Add screenshots from the live browser UI if there is time.
- Run a broader 10-20 task inference comparison if there is extra GPU/API time.
