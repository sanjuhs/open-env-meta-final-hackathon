#!/usr/bin/env bash
set -euo pipefail

# Wait for the current 2B GRPO run, then continue with 9B SFT and a 9B GRPO smoke.
# This is intentionally conservative: it does not start long 9B GRPO unless the
# 9B smoke succeeds.

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

LOG_DIR="${LOG_DIR:-training/logs}"
mkdir -p "$LOG_DIR"
WATCH_LOG="${WATCH_LOG:-$LOG_DIR/continue-after-2b-grpo.log}"

log() {
  echo "[$(date -Is)] $*" | tee -a "$WATCH_LOG"
}

wait_pidfile() {
  local pid_file="$1"
  local label="$2"
  if [[ ! -s "$pid_file" ]]; then
    log "No pid file for $label: $pid_file"
    return 0
  fi
  local pid
  pid="$(cat "$pid_file")"
  log "Waiting for $label pid=$pid"
  while kill -0 "$pid" 2>/dev/null; do
    sleep 60
  done
  log "$label finished"
}

log "Continuation watcher started"

wait_pidfile training/logs/grpo-2b-from-sft-20260425.pid "2B GRPO"

log "Generating 2B GRPO report"
training/cadforge_training_pipeline.sh report-grpo-2b || log "2B GRPO report failed; continuing"

log "Uploading 2B SFT adapter to Hugging Face if auth is available"
training/cadforge_training_pipeline.sh upload-sft-2b || log "2B SFT upload failed or HF auth is missing; continuing"

log "Launching 9B SFT"
training/cadforge_training_pipeline.sh sft-9b
wait_pidfile training/logs/sft-9b-full-20260426.pid "9B SFT"

log "Generating 9B SFT report"
training/cadforge_training_pipeline.sh report-sft-9b || log "9B report failed; continuing to smoke check"

log "Running 9B GRPO smoke"
rm -f training/logs/grpo-9b-smoke.log
SMOKE_MAX_STEPS="${SMOKE_MAX_STEPS:-2}" \
SMOKE_LIMIT_PROMPTS="${SMOKE_LIMIT_PROMPTS:-4}" \
SMOKE_NUM_GENERATIONS="${SMOKE_NUM_GENERATIONS:-2}" \
SMOKE_MAX_COMPLETION_LENGTH="${SMOKE_MAX_COMPLETION_LENGTH:-2048}" \
training/cadforge_training_pipeline.sh smoke-grpo-9b 2>&1 | tee -a training/logs/grpo-9b-smoke.log

log "Generating 9B GRPO smoke report"
uv run training/make_training_report.py \
  --log training/logs/grpo-9b-smoke.log \
  --trainer-output-dir outputs/qwen35-9b-cadforge-grpo-from-sft-smoke \
  --debug-jsonl training/logs/grpo-9b-smoke-completions.jsonl \
  --title "Qwen3.5-9B CADForge GRPO Smoke" \
  --output-dir training/reports/qwen35-9b-grpo-smoke || log "9B GRPO smoke report failed; smoke itself already completed"

if [[ "${AUTO_START_9B_GRPO:-1}" == "1" ]]; then
  log "9B GRPO smoke succeeded. Launching long 9B GRPO because AUTO_START_9B_GRPO=1."
  training/cadforge_training_pipeline.sh grpo-9b
  wait_pidfile training/logs/grpo-9b-from-sft-20260426.pid "9B GRPO"
  log "Generating 9B GRPO report"
  training/cadforge_training_pipeline.sh report-grpo-9b || log "9B GRPO report failed"
  log "Full 2B->9B continuation pipeline completed"
else
  log "9B GRPO smoke succeeded. Long 9B GRPO is ready but not auto-started."
  log "To start it: training/cadforge_training_pipeline.sh grpo-9b"
fi
