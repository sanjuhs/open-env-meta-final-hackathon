# CADForge RunPod Smoke Report

Date: 2026-04-25

Pod:

- Host: RunPod direct TCP SSH from `training/runpod-info-temp.md`
- Workspace: `/workspace/open-env-meta-final`
- GPU: NVIDIA H200, 143771 MiB
- Root disk after cache cleanup: 21 GB free
- Workspace disk: large network volume, about 267 TB free

## Setup

Completed:

- Synced local working tree to `/workspace/open-env-meta-final`.
- Removed accidentally synced root `.env` from the pod.
- Installed CADForge/CadQuery app environment with:

```bash
uv sync --project experiment-2-cadforge
```

- Moved heavy caches to workspace:

```bash
export UV_CACHE_DIR=/workspace/.uv-cache
export HF_HOME=/workspace/.cache/huggingface
export TORCH_HOME=/workspace/.cache/torch
export TRITON_CACHE_DIR=/workspace/.cache/triton
export VLLM_CACHE_ROOT=/workspace/.cache/vllm
export UV_LINK_MODE=copy
```

## Dataset Smoke

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

## CADForge Reward Smoke

Command:

```bash
/workspace/open-env-meta-final/experiment-2-cadforge/.venv/bin/python \
  training/smoke_cadforge_reward.py \
  --python /workspace/open-env-meta-final/experiment-2-cadforge/.venv/bin/python \
  --reward-mode fast
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

## SFT Smoke

Final clean command:

```bash
uv run training/train_sft_unsloth.py \
  --model Qwen/Qwen3.5-2B \
  --output-dir outputs/qwen35-2b-cadforge-sft-smoke-clean \
  --max-steps 2 \
  --limit-train-rows 8 \
  --limit-val-rows 4 \
  --max-seq-length 2048 \
  --per-device-train-batch-size 1 \
  --gradient-accumulation-steps 2 \
  --lora-r 16 \
  --lora-alpha 32 \
  --run-name qwen35-2b-sft-smoke-clean
```

Result:

- Passed.
- Qwen3.5 loaded with Unsloth and Transformers 5.5.0.
- LoRA trainable params: 10,911,744 of 2,224,153,408, about 0.49%.
- Train loss logged.
- Eval completed.
- Output saved to `outputs/qwen35-2b-cadforge-sft-smoke-clean`.

Observed final metrics:

```text
loss step 1: 2.500
loss step 2: 2.497
eval_loss: 1.428
train_loss: 2.498
```

Earlier 10-step SFT run also trained successfully through all 10 steps before an eval padding fix was applied. Its loss decreased from `1.755` to `0.7996`.

## Longer SFT Smoke

The clean longer smoke used the official Unsloth checkpoint name and a 4096-token context:

```bash
uv run training/train_sft_unsloth.py \
  --model unsloth/Qwen3.5-2B \
  --output-dir outputs/qwen35-2b-cadforge-sft-smoke-10step-unsloth \
  --max-steps 10 \
  --limit-train-rows 32 \
  --limit-val-rows 8 \
  --max-seq-length 4096 \
  --per-device-train-batch-size 1 \
  --gradient-accumulation-steps 4 \
  --eval-steps 5 \
  --save-steps 10 \
  --lora-r 16 \
  --lora-alpha 32 \
  --run-name qwen35-2b-sft-smoke-10step-unsloth
```

Result:

- Passed.
- Train loss moved from `1.755` to roughly `0.801`.
- Eval loss moved from `0.9451` to `0.8695`.
- Adapter output saved to `outputs/qwen35-2b-cadforge-sft-smoke-10step-unsloth`.
- First step was slower because Qwen3.5 compiles custom kernels; later steps were steady.

This is the strongest local signal that the SFT path is healthy.

## Qwen3.5 / Unsloth Notes

- Unsloth's Qwen3.5 guide says Qwen3.5 needs Transformers v5; older Transformers builds do not recognize `qwen3_5`.
- Qwen3.5 is a unified vision-language model, so the processor can accept images and text.
- The earlier image decode error was caused by calling the processor positionally with a text string. The processor treated that string as an image input. The fix is to call `tokenizer(text=...)` for text-only SFT rows.
- This was not evidence that image fine-tuning is broken. It was a text-only tokenization bug against a vision-capable processor.
- The GRPO CADForge smoke produced 128-token completions because the smoke command explicitly used `--max-completion-length 128`. Production GRPO should use 1024-2048 tokens.

## Full 2B SFT Run

Started on the H200:

```bash
uv run training/train_sft_unsloth.py \
  --model unsloth/Qwen3.5-2B \
  --output-dir outputs/qwen35-2b-cadforge-sft-full-20260425 \
  --max-steps 0 \
  --num-train-epochs 3 \
  --max-seq-length 8192 \
  --per-device-train-batch-size 1 \
  --gradient-accumulation-steps 8 \
  --eval-steps 25 \
  --save-steps 50 \
  --lora-r 16 \
  --lora-alpha 32 \
  --cold-start-upsample 4 \
  --run-name qwen35-2b-cadforge-sft-full-20260425
```

Log:

```text
/workspace/open-env-meta-final/training/logs/sft-2b-full-20260425.log
```

## GRPO Cheap Reward Smoke

Command:

```bash
uv run training/train_grpo_cadforge.py \
  --model Qwen/Qwen3.5-2B \
  --output-dir outputs/qwen35-2b-cadforge-grpo-cheap-smoke \
  --reward-backend cheap \
  --limit-prompts 4 \
  --max-steps 1 \
  --num-generations 2 \
  --max-prompt-length 1024 \
  --max-completion-length 256 \
  --per-device-train-batch-size 2 \
  --gradient-accumulation-steps 1 \
  --run-name qwen35-2b-grpo-cheap-smoke
```

Result:

- Passed.
- GRPO generated grouped completions.
- Reward function returned scalar rewards.
- Trainer logged reward and policy metrics.
- Output saved to `outputs/qwen35-2b-cadforge-grpo-cheap-smoke`.

Observed metrics:

```text
reward mean: 0.1
reward std: 0
completion mean length: 256
train_runtime: 44.62s
```

## GRPO CADForge Reward Smoke

Command:

```bash
uv run training/train_grpo_cadforge.py \
  --model Qwen/Qwen3.5-2B \
  --output-dir outputs/qwen35-2b-cadforge-grpo-cadforge-smoke \
  --reward-backend cadforge \
  --cadforge-python /workspace/open-env-meta-final/experiment-2-cadforge/.venv/bin/python \
  --cadforge-reward-mode fast \
  --limit-prompts 2 \
  --max-steps 1 \
  --num-generations 2 \
  --max-prompt-length 1024 \
  --max-completion-length 128 \
  --per-device-train-batch-size 2 \
  --gradient-accumulation-steps 1 \
  --run-name qwen35-2b-grpo-cadforge-smoke
```

Result:

- Passed.
- GRPO generated completions.
- CADForge reward backend was called from the reward function.
- Trainer accepted scalar CAD rewards and completed one training step.
- Output saved to `outputs/qwen35-2b-cadforge-grpo-cadforge-smoke`.

Observed metrics:

```text
reward mean: 0
reward std: 0
completion mean length: 128
train_runtime: 45.35s
```

The reward being zero is expected for a base 2B model with tiny 128-token completions. The smoke test proves the RLVE plumbing works; it does not measure trained model quality.

## Fixes Applied During Smoke

- Upgraded training script to Transformers v5 because Qwen3.5 uses model type `qwen3_5`.
- Pinned GRPO to `transformers==5.5.0`; the vLLM dependency can otherwise resolve `transformers 5.6.2`, which currently trips Unsloth's `auto_docstring` import path.
- Imported Unsloth before TRL/Transformers.
- Disabled Trackio by default for smoke tests; use `--enable-trackio` only after `HF_TOKEN` is configured.
- Pre-tokenized SFT rows and flattened Qwen processor output.
- Added `DataCollatorForSeq2Seq` so eval labels pad correctly.
- Added GRPO compatibility patches for optional TRL/vLLM dependencies on the H200:
  - disable Ascend vLLM path
  - disable MergeKit callbacks
  - disable PairRM/llm-blender judges
  - add a guided-decoding compatibility shim for current vLLM

## Readiness

Ready for the real 2B SFT run.

Recommended next command after setting `HF_TOKEN`:

```bash
uv run training/train_sft_unsloth.py \
  --model Qwen/Qwen3.5-2B \
  --output-dir outputs/qwen35-2b-cadforge-sft \
  --hub-model-id sanjuhs/qwen35-2b-cadforge-sft-lora \
  --push-to-hub \
  --enable-trackio \
  --max-steps 0 \
  --num-train-epochs 3 \
  --max-seq-length 8192 \
  --per-device-train-batch-size 1 \
  --gradient-accumulation-steps 8 \
  --learning-rate 2e-4 \
  --lora-r 16 \
  --lora-alpha 32 \
  --eval-steps 25 \
  --save-steps 50 \
  --run-name qwen35-2b-sft-full
```
