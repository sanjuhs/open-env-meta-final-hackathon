#!/usr/bin/env bash
set -euo pipefail

# Launch CADForge GRPO from the finished Qwen3.5-2B SFT LoRA adapter.
# Intended to run on the RunPod from /workspace/open-env-meta-final.

cd "$(dirname "$0")/.."

export UV_CACHE_DIR="${UV_CACHE_DIR:-/workspace/.uv-cache}"
export HF_HOME="${HF_HOME:-/workspace/.cache/huggingface}"
export TORCH_HOME="${TORCH_HOME:-/workspace/.cache/torch}"
export TRITON_CACHE_DIR="${TRITON_CACHE_DIR:-/workspace/.cache/triton}"
export VLLM_CACHE_ROOT="${VLLM_CACHE_ROOT:-/workspace/.cache/vllm}"
export UV_LINK_MODE="${UV_LINK_MODE:-copy}"
export HF_HUB_ENABLE_HF_TRANSFER="${HF_HUB_ENABLE_HF_TRANSFER:-1}"

BASE_MODEL="${BASE_MODEL:-unsloth/Qwen3.5-2B}"
SFT_ADAPTER="${SFT_ADAPTER:-outputs/qwen35-2b-cadforge-sft-full-20260425}"
OUT_DIR="${OUT_DIR:-outputs/qwen35-2b-cadforge-grpo-from-sft-20260425}"
LOG_DIR="${LOG_DIR:-training/logs}"
LOG_FILE="${LOG_FILE:-$LOG_DIR/grpo-2b-from-sft-20260425.log}"
PID_FILE="${PID_FILE:-$LOG_DIR/grpo-2b-from-sft-20260425.pid}"
CADFORGE_PYTHON="${CADFORGE_PYTHON:-/workspace/open-env-meta-final/experiment-2-cadforge/.venv/bin/python}"
LIMIT_PROMPTS="${LIMIT_PROMPTS:-64}"
MAX_STEPS="${MAX_STEPS:-80}"
NUM_GENERATIONS="${NUM_GENERATIONS:-4}"
MAX_PROMPT_LENGTH="${MAX_PROMPT_LENGTH:-4096}"
MAX_COMPLETION_LENGTH="${MAX_COMPLETION_LENGTH:-1536}"
PER_DEVICE_TRAIN_BATCH_SIZE="${PER_DEVICE_TRAIN_BATCH_SIZE:-4}"
GRADIENT_ACCUMULATION_STEPS="${GRADIENT_ACCUMULATION_STEPS:-4}"
LEARNING_RATE="${LEARNING_RATE:-5e-6}"

mkdir -p "$LOG_DIR"

if [[ ! -d "$SFT_ADAPTER" || ! -f "$SFT_ADAPTER/adapter_config.json" ]]; then
  echo "Missing SFT adapter directory: $SFT_ADAPTER" >&2
  echo "Expected $SFT_ADAPTER/adapter_config.json" >&2
  echo "Wait for SFT to finish, or set SFT_ADAPTER=/path/to/adapter." >&2
  exit 2
fi

if [[ -s "$PID_FILE" ]] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
  echo "GRPO already running: pid=$(cat "$PID_FILE")"
  echo "log=$LOG_FILE"
  exit 0
fi

nohup uv run training/train_grpo_cadforge.py \
  --model "$BASE_MODEL" \
  --adapter "$SFT_ADAPTER" \
  --output-dir "$OUT_DIR" \
  --reward-backend cadforge \
  --cadforge-python "$CADFORGE_PYTHON" \
  --cadforge-reward-mode fast \
  --limit-prompts "$LIMIT_PROMPTS" \
  --max-steps "$MAX_STEPS" \
  --num-generations "$NUM_GENERATIONS" \
  --max-prompt-length "$MAX_PROMPT_LENGTH" \
  --max-completion-length "$MAX_COMPLETION_LENGTH" \
  --max-seq-length 8192 \
  --per-device-train-batch-size "$PER_DEVICE_TRAIN_BATCH_SIZE" \
  --gradient-accumulation-steps "$GRADIENT_ACCUMULATION_STEPS" \
  --learning-rate "$LEARNING_RATE" \
  --run-name qwen35-2b-cadforge-grpo-from-sft-20260425 \
  > "$LOG_FILE" 2>&1 &

echo $! > "$PID_FILE"
echo "Started GRPO: pid=$(cat "$PID_FILE")"
echo "log=$LOG_FILE"
echo "output=$OUT_DIR"
