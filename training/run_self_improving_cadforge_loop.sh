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
export TMPDIR="${TMPDIR:-$WORKSPACE_ROOT/tmp}"
export TORCHINDUCTOR_CACHE_DIR="${TORCHINDUCTOR_CACHE_DIR:-$WORKSPACE_ROOT/.cache/torchinductor}"
export UV_LINK_MODE=copy
export HF_HUB_ENABLE_HF_TRANSFER=1
export HF_HUB_DISABLE_XET=1
export TORCH_COMPILE_DISABLE=1

mkdir -p "$TMPDIR" "$TORCHINDUCTOR_CACHE_DIR" training/logs training/output training/reports

RUN_PREFIX="${RUN_PREFIX:-20260426-self-improve}"
ROUNDS="${ROUNDS:-3}"
STEPS_PER_ROUND="${STEPS_PER_ROUND:-12}"
LIMIT_PROMPTS="${LIMIT_PROMPTS:-24}"
MAX_ROWS="${MAX_ROWS:-180}"
NUM_GENERATIONS="${NUM_GENERATIONS:-2}"
BASE_MODEL="${BASE_MODEL:-unsloth/Qwen3.5-9B}"
ADAPTER="${ADAPTER:-outputs/qwen35-9b-cadforge-grpo-strict-build-20260426-strict-build}"
SOURCE_DEBUG="${SOURCE_DEBUG:-training/logs/grpo-9b-strict-build-20260426-strict-build-completions.jsonl}"
MASTER_LOG="training/logs/${RUN_PREFIX}.log"

{
  echo "[$(date -Is)] Starting CADForge self-improving loop"
  echo "Base model: $BASE_MODEL"
  echo "Initial adapter: $ADAPTER"
  echo "Initial debug source: $SOURCE_DEBUG"
  echo "Rounds: $ROUNDS, steps per round: $STEPS_PER_ROUND"

  for round in $(seq 1 "$ROUNDS"); do
    ROUND_NAME="${RUN_PREFIX}-round-${round}"
    CURRICULUM="training/output/${ROUND_NAME}-curriculum.jsonl"
    SUMMARY="training/output/${ROUND_NAME}-summary.json"
    OUT="outputs/qwen35-9b-cadforge-grpo-${ROUND_NAME}"
    LOG="training/logs/grpo-9b-${ROUND_NAME}.log"
    DEBUG="training/logs/grpo-9b-${ROUND_NAME}-completions.jsonl"
    REPORT="training/reports/qwen35-9b-grpo-${ROUND_NAME}"

    echo "[$(date -Is)] Round $round: mining failures from $SOURCE_DEBUG"
    uv run training/generate_repair_curriculum.py \
      --debug-jsonl "$SOURCE_DEBUG" \
      --tasks experiment-2-cadforge/data/cad_tasks.json \
      --output "$CURRICULUM" \
      --summary "$SUMMARY" \
      --max-rows "$MAX_ROWS"

    echo "[$(date -Is)] Round $round: training adapter $ADAPTER"
    rm -f "$DEBUG"
    uv run training/train_grpo_cadforge.py \
      --model "$BASE_MODEL" \
      --adapter "$ADAPTER" \
      --rl-jsonl "$CURRICULUM" \
      --output-dir "$OUT" \
      --reward-backend cadforge \
      --strict-build-gate \
      --cadforge-python "$ROOT/experiment-2-cadforge/.venv/bin/python" \
      --cadforge-reward-mode fast \
      --limit-prompts "$LIMIT_PROMPTS" \
      --max-steps "$STEPS_PER_ROUND" \
      --num-generations "$NUM_GENERATIONS" \
      --max-prompt-length 6144 \
      --max-completion-length 1536 \
      --max-seq-length 8192 \
      --per-device-train-batch-size 2 \
      --gradient-accumulation-steps 2 \
      --learning-rate 2e-6 \
      --debug-completions-jsonl "$DEBUG" \
      --run-name "qwen35-9b-grpo-${ROUND_NAME}" \
      > "$LOG" 2>&1

    echo "[$(date -Is)] Round $round: generating report"
    uv run training/make_training_report.py \
      --log "$LOG" \
      --trainer-output-dir "$OUT" \
      --debug-jsonl "$DEBUG" \
      --title "Qwen3.5-9B CADForge Self-Improving GRPO Round $round" \
      --output-dir "$REPORT"

    ADAPTER="$OUT"
    SOURCE_DEBUG="$DEBUG"
    echo "[$(date -Is)] Round $round complete. Next adapter: $ADAPTER"
  done

  echo "[$(date -Is)] CADForge self-improving loop complete"
} | tee -a "$MASTER_LOG"
