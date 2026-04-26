#!/usr/bin/env bash
set -euo pipefail

# CADForge training pipeline wrapper for RunPod.
# Run from the repo root, or anywhere inside the repo:
#   training/cadforge_training_pipeline.sh status
#   training/cadforge_training_pipeline.sh smoke-grpo-2b
#   training/cadforge_training_pipeline.sh grpo-2b
#   training/cadforge_training_pipeline.sh sft-9b
#
# Each stage uses explicit cache/env settings so SFT, GRPO, eval, and CADForge
# stay isolated even when their Python dependencies differ.

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ -f "$ROOT/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$ROOT/.env"
  set +a
fi
if [[ -f "$ROOT/training/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$ROOT/training/.env"
  set +a
fi

export UV_CACHE_DIR="${UV_CACHE_DIR:-/workspace/.uv-cache}"
export HF_HOME="${HF_HOME:-/workspace/.cache/huggingface}"
export TORCH_HOME="${TORCH_HOME:-/workspace/.cache/torch}"
export TRITON_CACHE_DIR="${TRITON_CACHE_DIR:-/workspace/.cache/triton}"
export VLLM_CACHE_ROOT="${VLLM_CACHE_ROOT:-/workspace/.cache/vllm}"
export UV_LINK_MODE="${UV_LINK_MODE:-copy}"
export HF_HUB_ENABLE_HF_TRANSFER="${HF_HUB_ENABLE_HF_TRANSFER:-1}"

CADFORGE_PYTHON="${CADFORGE_PYTHON:-$ROOT/experiment-2-cadforge/.venv/bin/python}"
LOG_DIR="${LOG_DIR:-training/logs}"
GRPO_2B_RL_JSONL="${GRPO_2B_RL_JSONL:-training/output/cadforge_sft_mix_train.jsonl}"
GRPO_2B_SMOKE_JSONL="${GRPO_2B_SMOKE_JSONL:-training/output/cadforge_sft_mix_val.jsonl}"
GRPO_9B_RL_JSONL="${GRPO_9B_RL_JSONL:-experiment-2-cadforge/data/sft/cadquery_prompt_to_cadquery_train.jsonl}"
GRPO_9B_SMOKE_JSONL="${GRPO_9B_SMOKE_JSONL:-experiment-2-cadforge/data/sft/cadquery_prompt_to_cadquery_val.jsonl}"
mkdir -p "$LOG_DIR"

run_detached() {
  local pid_file="$1"
  local log_file="$2"
  shift 2
  if [[ -s "$pid_file" ]] && kill -0 "$(cat "$pid_file")" 2>/dev/null; then
    echo "Already running: pid=$(cat "$pid_file")"
    echo "log=$log_file"
    return 0
  fi
  nohup bash -lc '
    set -o pipefail
    "$@" 2>&1 | while IFS= read -r line; do
      printf "[%s] %s\n" "$(date -Is)" "$line"
    done
  ' bash "$@" > "$log_file" 2>&1 &
  echo $! > "$pid_file"
  echo "Started: pid=$(cat "$pid_file")"
  echo "log=$log_file"
}

require_adapter() {
  local adapter="$1"
  if [[ ! -f "$adapter/adapter_config.json" ]]; then
    echo "Missing adapter: $adapter/adapter_config.json" >&2
    exit 2
  fi
}

status() {
  echo "GPU:"
  nvidia-smi --query-gpu=name,memory.used,memory.total,utilization.gpu --format=csv,noheader || true
  echo
  echo "Running training processes:"
  pgrep -af "train_(sft|grpo)|cadforge_training_pipeline" || true
  echo
  echo "2B SFT adapter:"
  if [[ -f outputs/qwen35-2b-cadforge-sft-full-20260425/adapter_config.json ]]; then
    ls -lh outputs/qwen35-2b-cadforge-sft-full-20260425/adapter_model.safetensors
  else
    echo "not ready"
  fi
}

report_sft_2b() {
  uv run training/make_training_report.py \
    --log training/logs/sft-2b-full-20260425.log \
    --trainer-output-dir outputs/qwen35-2b-cadforge-sft-full-20260425 \
    --title "Qwen3.5-2B CADForge SFT" \
    --output-dir training/reports/qwen35-2b-sft-final
}

report_grpo_2b() {
  uv run training/make_training_report.py \
    --log training/logs/grpo-2b-from-sft-20260425.log \
    --trainer-output-dir outputs/qwen35-2b-cadforge-grpo-from-sft-20260425 \
    --debug-jsonl training/logs/grpo-2b-completions.jsonl \
    --title "Qwen3.5-2B CADForge GRPO" \
    --output-dir training/reports/qwen35-2b-grpo-final
}

upload_sft_2b() {
  require_adapter outputs/qwen35-2b-cadforge-sft-full-20260425
  local repo="${HF_2B_SFT_REPO:-sanjuhs/qwen35-2b-cadforge-sft-lora}"
  uv run --with "huggingface_hub[cli]" --with hf_transfer \
    hf upload "$repo" outputs/qwen35-2b-cadforge-sft-full-20260425 \
      --repo-type model \
      --commit-message "Upload Qwen3.5 2B CADForge SFT LoRA adapter"
}

eval_sft_2b() {
  require_adapter outputs/qwen35-2b-cadforge-sft-full-20260425
  uv run training/evaluate_cadforge_model.py \
    --base-model unsloth/Qwen3.5-2B \
    --adapter outputs/qwen35-2b-cadforge-sft-full-20260425 \
    --rl-jsonl "$GRPO_2B_SMOKE_JSONL" \
    --eval-jsonl training/output/cadforge_sft_mix_val.jsonl \
    --output-dir training/eval/qwen35-2b-cadforge-sft-full-20260425 \
    --limit "${EVAL_LIMIT:-24}" \
    --max-new-tokens "${EVAL_MAX_NEW_TOKENS:-2048}" \
    --reward-mode fast \
    --episode-prefix qwen35-2b-sft-eval
}

smoke_grpo_2b() {
  require_adapter outputs/qwen35-2b-cadforge-sft-full-20260425
  rm -f training/logs/grpo-2b-smoke-completions.jsonl
  uv run training/train_grpo_cadforge.py \
    --model unsloth/Qwen3.5-2B \
    --adapter outputs/qwen35-2b-cadforge-sft-full-20260425 \
    --output-dir outputs/qwen35-2b-cadforge-grpo-from-sft-smoke \
    --reward-backend cadforge \
    --build-fail-shaping \
    --cadforge-python "$CADFORGE_PYTHON" \
    --cadforge-reward-mode fast \
    --limit-prompts "${SMOKE_LIMIT_PROMPTS:-4}" \
    --max-steps "${SMOKE_MAX_STEPS:-3}" \
    --num-generations "${SMOKE_NUM_GENERATIONS:-2}" \
    --max-prompt-length "${SMOKE_MAX_PROMPT_LENGTH:-4096}" \
    --max-completion-length "${SMOKE_MAX_COMPLETION_LENGTH:-2048}" \
    --max-seq-length "${SMOKE_MAX_SEQ_LENGTH:-8192}" \
    --per-device-train-batch-size "${SMOKE_BATCH:-2}" \
    --gradient-accumulation-steps 1 \
    --learning-rate 5e-6 \
    --debug-completions-jsonl training/logs/grpo-2b-smoke-completions.jsonl \
    --run-name qwen35-2b-grpo-from-sft-smoke
  echo "Smoke completions: training/logs/grpo-2b-smoke-completions.jsonl"
}

grpo_2b() {
  require_adapter outputs/qwen35-2b-cadforge-sft-full-20260425
  run_detached \
    training/logs/grpo-2b-from-sft-20260425.pid \
    training/logs/grpo-2b-from-sft-20260425.log \
    uv run training/train_grpo_cadforge.py \
      --model unsloth/Qwen3.5-2B \
      --adapter outputs/qwen35-2b-cadforge-sft-full-20260425 \
      --rl-jsonl "$GRPO_2B_RL_JSONL" \
      --output-dir outputs/qwen35-2b-cadforge-grpo-from-sft-20260425 \
      --reward-backend cadforge \
      --build-fail-shaping \
      --cadforge-python "$CADFORGE_PYTHON" \
      --cadforge-reward-mode fast \
      --limit-prompts "${GRPO_2B_LIMIT_PROMPTS:-64}" \
      --max-steps "${GRPO_2B_MAX_STEPS:-80}" \
      --num-generations "${GRPO_2B_NUM_GENERATIONS:-4}" \
      --max-prompt-length "${GRPO_2B_MAX_PROMPT_LENGTH:-4096}" \
      --max-completion-length "${GRPO_2B_MAX_COMPLETION_LENGTH:-2048}" \
      --max-seq-length 8192 \
      --per-device-train-batch-size "${GRPO_2B_BATCH:-4}" \
      --gradient-accumulation-steps "${GRPO_2B_GRAD_ACCUM:-4}" \
      --learning-rate 5e-6 \
      --debug-completions-jsonl training/logs/grpo-2b-completions.jsonl \
      --run-name qwen35-2b-cadforge-grpo-from-sft-20260425
}

sft_9b() {
  run_detached \
    training/logs/sft-9b-full-20260426.pid \
    training/logs/sft-9b-full-20260426.log \
    uv run training/train_sft_unsloth.py \
      --model unsloth/Qwen3.5-9B \
      --output-dir outputs/qwen35-9b-cadforge-sft-full-20260426 \
      --max-steps 0 \
      --num-train-epochs "${SFT_9B_EPOCHS:-2}" \
      --max-seq-length 8192 \
      --per-device-train-batch-size 1 \
      --gradient-accumulation-steps 8 \
      --learning-rate 1e-4 \
      --lora-r 32 \
      --lora-alpha 64 \
      --eval-steps 25 \
      --save-steps 50 \
      --cold-start-upsample 4 \
      --run-name qwen35-9b-cadforge-sft-full-20260426
}

report_sft_9b() {
  uv run training/make_training_report.py \
    --log training/logs/sft-9b-full-20260426.log \
    --trainer-output-dir outputs/qwen35-9b-cadforge-sft-full-20260426 \
    --title "Qwen3.5-9B CADForge SFT" \
    --output-dir training/reports/qwen35-9b-sft-final
}

report_grpo_9b() {
  uv run training/make_training_report.py \
    --log training/logs/grpo-9b-from-sft-20260426.log \
    --trainer-output-dir outputs/qwen35-9b-cadforge-grpo-from-sft-20260426 \
    --debug-jsonl training/logs/grpo-9b-completions.jsonl \
    --title "Qwen3.5-9B CADForge GRPO" \
    --output-dir training/reports/qwen35-9b-grpo-final
}

smoke_grpo_9b() {
  require_adapter outputs/qwen35-9b-cadforge-sft-full-20260426
  rm -f training/logs/grpo-9b-smoke-completions.jsonl
  uv run training/train_grpo_cadforge.py \
    --model unsloth/Qwen3.5-9B \
    --adapter outputs/qwen35-9b-cadforge-sft-full-20260426 \
    --rl-jsonl "$GRPO_9B_SMOKE_JSONL" \
    --output-dir outputs/qwen35-9b-cadforge-grpo-from-sft-smoke \
    --reward-backend cadforge \
    --build-fail-shaping \
    --cadforge-python "$CADFORGE_PYTHON" \
    --cadforge-reward-mode fast \
    --limit-prompts "${SMOKE_LIMIT_PROMPTS:-4}" \
    --max-steps "${SMOKE_MAX_STEPS:-3}" \
    --num-generations "${SMOKE_NUM_GENERATIONS:-2}" \
    --max-prompt-length "${SMOKE_MAX_PROMPT_LENGTH:-4096}" \
    --max-completion-length "${SMOKE_MAX_COMPLETION_LENGTH:-2048}" \
    --max-seq-length "${SMOKE_MAX_SEQ_LENGTH:-8192}" \
    --per-device-train-batch-size "${SMOKE_BATCH:-2}" \
    --gradient-accumulation-steps 1 \
    --learning-rate 5e-6 \
    --debug-completions-jsonl training/logs/grpo-9b-smoke-completions.jsonl \
    --run-name qwen35-9b-grpo-from-sft-smoke
  echo "Smoke completions: training/logs/grpo-9b-smoke-completions.jsonl"
}

grpo_9b() {
  require_adapter outputs/qwen35-9b-cadforge-sft-full-20260426
  run_detached \
    training/logs/grpo-9b-from-sft-20260426.pid \
    training/logs/grpo-9b-from-sft-20260426.log \
    uv run training/train_grpo_cadforge.py \
      --model unsloth/Qwen3.5-9B \
      --adapter outputs/qwen35-9b-cadforge-sft-full-20260426 \
      --rl-jsonl "$GRPO_9B_RL_JSONL" \
      --output-dir outputs/qwen35-9b-cadforge-grpo-from-sft-20260426 \
      --reward-backend cadforge \
      --build-fail-shaping \
      --cadforge-python "$CADFORGE_PYTHON" \
      --cadforge-reward-mode fast \
      --limit-prompts "${GRPO_9B_LIMIT_PROMPTS:-20}" \
      --max-steps "${GRPO_9B_MAX_STEPS:-40}" \
      --num-generations "${GRPO_9B_NUM_GENERATIONS:-2}" \
      --max-prompt-length "${GRPO_9B_MAX_PROMPT_LENGTH:-4096}" \
      --max-completion-length "${GRPO_9B_MAX_COMPLETION_LENGTH:-2048}" \
      --max-seq-length 8192 \
      --per-device-train-batch-size "${GRPO_9B_BATCH:-2}" \
      --gradient-accumulation-steps "${GRPO_9B_GRAD_ACCUM:-2}" \
      --learning-rate 5e-6 \
      --debug-completions-jsonl training/logs/grpo-9b-completions.jsonl \
      --run-name qwen35-9b-cadforge-grpo-from-sft-20260426
}

case "${1:-}" in
  status) status ;;
  report-sft-2b) report_sft_2b ;;
  report-grpo-2b) report_grpo_2b ;;
  upload-sft-2b) upload_sft_2b ;;
  eval-sft-2b) eval_sft_2b ;;
  smoke-grpo-2b) smoke_grpo_2b ;;
  grpo-2b) grpo_2b ;;
  sft-9b) sft_9b ;;
  report-sft-9b) report_sft_9b ;;
  report-grpo-9b) report_grpo_9b ;;
  smoke-grpo-9b) smoke_grpo_9b ;;
  grpo-9b) grpo_9b ;;
  *)
    echo "Usage: $0 {status|report-sft-2b|report-grpo-2b|upload-sft-2b|eval-sft-2b|smoke-grpo-2b|grpo-2b|sft-9b|report-sft-9b|report-grpo-9b|smoke-grpo-9b|grpo-9b}" >&2
    exit 2
    ;;
esac
