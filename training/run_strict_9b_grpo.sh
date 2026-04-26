#!/usr/bin/env bash
set -euo pipefail
ROOT="${ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
cd "$ROOT"
set -a
source .env || true
set +a
WORKSPACE_ROOT="${WORKSPACE_ROOT:-/workspace}"
export UV_CACHE_DIR="${UV_CACHE_DIR:-$WORKSPACE_ROOT/.uv-cache}"
export HF_HOME="${HF_HOME:-$WORKSPACE_ROOT/.cache/huggingface}"
export TORCH_HOME="${TORCH_HOME:-$WORKSPACE_ROOT/.cache/torch}"
export TRITON_CACHE_DIR="${TRITON_CACHE_DIR:-$WORKSPACE_ROOT/.cache/triton}"
export VLLM_CACHE_ROOT="${VLLM_CACHE_ROOT:-$WORKSPACE_ROOT/.cache/vllm}"
export TMPDIR="${TMPDIR:-$WORKSPACE_ROOT/tmp}"
export TORCHINDUCTOR_CACHE_DIR="${TORCHINDUCTOR_CACHE_DIR:-$WORKSPACE_ROOT/.cache/torchinductor}"
export UV_LINK_MODE=copy
export HF_HUB_ENABLE_HF_TRANSFER=1
export HF_HUB_DISABLE_XET=1
export TORCH_COMPILE_DISABLE=1
mkdir -p "$TMPDIR" "$TORCHINDUCTOR_CACHE_DIR" training/logs
RUN=20260426-strict-build
OUT=outputs/qwen35-9b-cadforge-grpo-strict-build-$RUN
LOG=training/logs/grpo-9b-strict-build-$RUN.log
DEBUG=training/logs/grpo-9b-strict-build-$RUN-completions.jsonl
REPORT=training/reports/qwen35-9b-grpo-strict-build-$RUN
rm -f "$DEBUG"
{
  echo "[$(date -Is)] Starting strict-build GRPO"
  uv run training/train_grpo_cadforge.py \
    --model unsloth/Qwen3.5-9B \
    --adapter outputs/qwen35-9b-cadforge-sft-full-20260426 \
    --rl-jsonl experiment-2-cadforge/data/sft/cadquery_prompt_to_cadquery_train.jsonl \
    --output-dir "$OUT" \
    --reward-backend cadforge \
    --strict-build-gate \
    --cadforge-python "$ROOT/experiment-2-cadforge/.venv/bin/python" \
    --cadforge-reward-mode fast \
    --limit-prompts 20 \
    --max-steps 80 \
    --num-generations 2 \
    --max-prompt-length 4096 \
    --max-completion-length 2048 \
    --max-seq-length 8192 \
    --per-device-train-batch-size 2 \
    --gradient-accumulation-steps 2 \
    --learning-rate 3e-6 \
    --debug-completions-jsonl "$DEBUG" \
    --run-name qwen35-9b-grpo-strict-build-$RUN
  echo "[$(date -Is)] Generating strict-build report"
  uv run training/make_training_report.py \
    --log "$LOG" \
    --trainer-output-dir "$OUT" \
    --debug-jsonl "$DEBUG" \
    --title "Qwen3.5-9B CADForge Strict Build GRPO" \
    --output-dir "$REPORT"
  echo "[$(date -Is)] Uploading strict-build adapter"
  uv run --with "huggingface_hub[cli]" --with hf_transfer hf upload \
    sanjuhs/qwen35-9b-cadforge-grpo-strict-build-lora "$OUT" \
    --repo-type model \
    --commit-message "Upload Qwen3.5 9B CADForge strict-build GRPO LoRA adapter"
  echo "[$(date -Is)] Running strict-build quick eval"
  uv run training/evaluate_cadforge_model.py \
    --base-model unsloth/Qwen3.5-9B \
    --adapter "$OUT" \
    --eval-jsonl experiment-2-cadforge/data/sft/cadquery_prompt_to_cadquery_val.jsonl \
    --output-dir training/eval/qwen35-9b-cadforge-grpo-strict-build-$RUN \
    --limit 3 \
    --max-new-tokens 1536 \
    --reward-mode fast \
    --episode-prefix qwen35-9b-grpo-strict-build-$RUN || echo "[$(date -Is)] Eval failed; training/upload already completed"
  echo "[$(date -Is)] Strict-build GRPO pipeline complete"
} > "$LOG" 2>&1
