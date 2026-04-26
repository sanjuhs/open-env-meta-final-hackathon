# CADForge Submission Checklist

## Non-Negotiables

| Requirement | Status | File / Link |
|---|---|---|
| OpenEnv environment | done | `experiment-2-cadforge/openenv.yaml` |
| Hugging Face Space | ready to push | `sanjuhs/cadforge-cadquery-openenv` |
| Training notebook | done | `training/cadforge_openenv_training_colab.ipynb` |
| Unsloth / TRL scripts | done | `training/train_sft_unsloth.py`, `training/train_grpo_cadforge.py` |
| Evidence of training | done | `training/reports/qwen35-9b-grpo-strict-build-20260426-strict-build/` |
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
6. Held-out eval built `2/3` objects.

## Remaining Optional Polish

- Add a <2 minute YouTube link to both READMEs if you record one.
- Add the HF Space URL after pushing/confirming the live Space.
- Add screenshots from the live browser UI if there is time.
- Run one more held-out eval with a higher `max-new-tokens` for chair tasks to reduce clipping.

