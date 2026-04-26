#!/usr/bin/env bash
set -euo pipefail

ROOT="${ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
cd "$ROOT"

set -a
source .env 2>/dev/null || true
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

mkdir -p "$TMPDIR" "$TORCHINDUCTOR_CACHE_DIR" training/logs training/output training/reports

RUN="${RUN:-20260426-adaptive-repair}"
STRICT_RUN="${STRICT_RUN:-20260426-strict-build}"
STRICT_DEBUG="${STRICT_DEBUG:-training/logs/grpo-9b-strict-build-$STRICT_RUN-completions.jsonl}"
CURRICULUM="${CURRICULUM:-training/output/cadforge_adaptive_repair_curriculum.jsonl}"
SUMMARY="${SUMMARY:-training/output/cadforge_adaptive_repair_summary.json}"
BASE_ADAPTER="${BASE_ADAPTER:-outputs/qwen35-9b-cadforge-grpo-strict-build-$STRICT_RUN}"
OUT="${OUT:-outputs/qwen35-9b-cadforge-grpo-$RUN}"
LOG="${LOG:-training/logs/grpo-9b-$RUN.log}"
DEBUG="${DEBUG:-training/logs/grpo-9b-$RUN-completions.jsonl}"
REPORT="${REPORT:-training/reports/qwen35-9b-grpo-$RUN}"
MAX_ROWS="${MAX_ROWS:-180}"
LIMIT_PROMPTS="${LIMIT_PROMPTS:-48}"
MAX_STEPS="${MAX_STEPS:-30}"
NUM_GENERATIONS="${NUM_GENERATIONS:-2}"
PREVIOUS_CODE_CHARS="${PREVIOUS_CODE_CHARS:-2200}"
MAX_PROMPT_LENGTH="${MAX_PROMPT_LENGTH:-4096}"
MAX_COMPLETION_LENGTH="${MAX_COMPLETION_LENGTH:-8192}"
MAX_SEQ_LENGTH="${MAX_SEQ_LENGTH:-16384}"
PER_DEVICE_TRAIN_BATCH_SIZE="${PER_DEVICE_TRAIN_BATCH_SIZE:-1}"
GRADIENT_ACCUMULATION_STEPS="${GRADIENT_ACCUMULATION_STEPS:-4}"
CURRICULUM_STAGE="${CURRICULUM_STAGE:-foundation}"

rm -f "$DEBUG"

{
  echo "[$(date -Is)] Generating adaptive repair curriculum from $STRICT_DEBUG"
  uv run training/generate_repair_curriculum.py \
    --debug-jsonl "$STRICT_DEBUG" \
    --tasks experiment-2-cadforge/data/cad_tasks.json \
    --output "$CURRICULUM" \
    --summary "$SUMMARY" \
    --max-rows "$MAX_ROWS" \
    --previous-code-chars "$PREVIOUS_CODE_CHARS" \
    --curriculum-stage "$CURRICULUM_STAGE"

  echo "[$(date -Is)] Starting adaptive repair GRPO from $BASE_ADAPTER"
  uv run training/train_grpo_cadforge.py \
    --model unsloth/Qwen3.5-9B \
    --adapter "$BASE_ADAPTER" \
    --rl-jsonl "$CURRICULUM" \
    --output-dir "$OUT" \
    --reward-backend cadforge \
    --strict-build-gate \
    --cadforge-python "$ROOT/experiment-2-cadforge/.venv/bin/python" \
    --cadforge-reward-mode fast \
    --limit-prompts "$LIMIT_PROMPTS" \
    --max-steps "$MAX_STEPS" \
    --num-generations "$NUM_GENERATIONS" \
    --max-prompt-length "$MAX_PROMPT_LENGTH" \
    --max-completion-length "$MAX_COMPLETION_LENGTH" \
    --max-seq-length "$MAX_SEQ_LENGTH" \
    --per-device-train-batch-size "$PER_DEVICE_TRAIN_BATCH_SIZE" \
    --gradient-accumulation-steps "$GRADIENT_ACCUMULATION_STEPS" \
    --learning-rate 2e-6 \
    --debug-completions-jsonl "$DEBUG" \
    --run-name "qwen35-9b-grpo-$RUN"

  echo "[$(date -Is)] Generating adaptive repair report"
  uv run training/make_training_report.py \
    --log "$LOG" \
    --trainer-output-dir "$OUT" \
    --debug-jsonl "$DEBUG" \
    --title "Qwen3.5-9B CADForge Adaptive Repair GRPO" \
    --output-dir "$REPORT"

  if [[ -n "${HF_TOKEN:-}" ]]; then
    echo "[$(date -Is)] Uploading adaptive repair adapter"
    uv run --with "huggingface_hub[cli]" --with hf_transfer hf upload \
      sanjuhs/qwen35-9b-cadforge-grpo-adaptive-repair-lora "$OUT" \
      --repo-type model \
      --commit-message "Upload Qwen3.5 9B CADForge adaptive repair GRPO LoRA adapter" || true
  fi

  echo "[$(date -Is)] Adaptive repair GRPO pipeline complete"
} > "$LOG" 2>&1
