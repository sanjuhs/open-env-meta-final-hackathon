# CADForge Training Smoke Report

## Local Checks Completed

Date: 2026-04-25

Local machine checks:

- Mixed SFT dataset build: passed.
- Python syntax compile for training scripts: passed.
- CADForge reward backend smoke: passed.

## SFT Mix

Command:

```bash
uv run training/prepare_sft_mix.py --cold-start-upsample 4
```

Result:

```json
{
  "cold_train_rows": 20,
  "repair_train_rows": 633,
  "cold_start_upsample": 4,
  "mixed_train_rows": 713,
  "mixed_val_rows": 76
}
```

Interpretation:

- The model will see 80 cold-start prompt-to-CadQuery examples.
- The model will see 633 agentic repair examples.
- This keeps first-draft CAD generation from being drowned out by repair-only data.

## Reward Backend Smoke

Command:

```bash
uv run training/smoke_cadforge_reward.py --reward-mode fast
```

Result:

```json
{
  "ok": true,
  "task_id": "bench_vise_simplified",
  "reward_mode": "fast",
  "total": 0.8126117485948784,
  "build": 1.0,
  "topology": 1.0,
  "contact": 0.9613198802378905,
  "semantic_parts": 0.6690134518653259,
  "reference_similarity": 0.0,
  "editability": 1.0
}
```

Interpretation:

- CadQuery execution works.
- Mesh export works.
- Fast reward returns dense scalar components.
- The reference similarity is 0.0 in this specific smoke because the smoke uses fast-mode/reference-light scoring for a generated task; build, topology, contact, semantics, and editability are the important plumbing checks here.

## Not Run Locally

The actual Unsloth SFT and GRPO smoke tests were not run on this Mac because the scripts require CUDA. They are ready for the H200 RunPod.

Run first on RunPod:

```bash
uv run training/train_sft_unsloth.py \
  --model Qwen/Qwen3.5-2B \
  --output-dir outputs/qwen35-2b-cadforge-sft-smoke \
  --max-steps 10 \
  --limit-train-rows 32 \
  --limit-val-rows 8 \
  --max-seq-length 4096 \
  --per-device-train-batch-size 1 \
  --gradient-accumulation-steps 4 \
  --run-name qwen35-2b-sft-smoke
```

Then:

```bash
uv run training/train_grpo_cadforge.py \
  --model Qwen/Qwen3.5-2B \
  --output-dir outputs/qwen35-2b-cadforge-grpo-smoke \
  --reward-backend cheap \
  --limit-prompts 8 \
  --max-steps 5 \
  --num-generations 4 \
  --run-name qwen35-2b-grpo-cheap-smoke
```
