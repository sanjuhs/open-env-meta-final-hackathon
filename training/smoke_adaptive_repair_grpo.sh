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
export HUGGINGFACE_HUB_CACHE="${HUGGINGFACE_HUB_CACHE:-$HF_HOME/hub}"
export TRANSFORMERS_CACHE="${TRANSFORMERS_CACHE:-$HF_HOME/transformers}"
export TORCH_HOME="${TORCH_HOME:-$WORKSPACE_ROOT/.cache/torch}"
export TRITON_CACHE_DIR="${TRITON_CACHE_DIR:-$WORKSPACE_ROOT/.cache/triton}"
export VLLM_CACHE_ROOT="${VLLM_CACHE_ROOT:-$WORKSPACE_ROOT/.cache/vllm}"
export TMPDIR="${TMPDIR:-$WORKSPACE_ROOT/tmp}"
export TORCHINDUCTOR_CACHE_DIR="${TORCHINDUCTOR_CACHE_DIR:-$WORKSPACE_ROOT/.cache/torchinductor}"
export UV_LINK_MODE=copy
export HF_HUB_DISABLE_XET=1
export TORCH_COMPILE_DISABLE=1

mkdir -p "$TMPDIR" "$UV_CACHE_DIR" "$HF_HOME" "$HUGGINGFACE_HUB_CACHE" "$TRANSFORMERS_CACHE" "$TORCH_HOME" "$TRITON_CACHE_DIR" "$VLLM_CACHE_ROOT" "$TORCHINDUCTOR_CACHE_DIR" training/logs training/output

STRICT_RUN="${STRICT_RUN:-20260426-strict-build}"
STRICT_DEBUG="${STRICT_DEBUG:-training/logs/grpo-9b-strict-build-$STRICT_RUN-completions.jsonl}"
BASE_ADAPTER="${BASE_ADAPTER:-outputs/qwen35-9b-cadforge-grpo-strict-build-$STRICT_RUN}"
CURRICULUM="${CURRICULUM:-training/output/cadforge_adaptive_repair_curriculum_smoke.jsonl}"
SUMMARY="${SUMMARY:-training/output/cadforge_adaptive_repair_summary_smoke.json}"
OUT="${OUT:-/tmp/cadforge-grpo-smoke-8192}"
DEBUG="${DEBUG:-/tmp/cadforge-grpo-smoke-8192-completions.jsonl}"

rm -rf "$OUT"
rm -f "$DEBUG"

echo "[$(date -Is)] Smoke: generating foundation repair curriculum"
uv run training/generate_repair_curriculum.py \
  --debug-jsonl "$STRICT_DEBUG" \
  --tasks experiment-2-cadforge/data/cad_tasks.json \
  --output "$CURRICULUM" \
  --summary "$SUMMARY" \
  --max-rows 64 \
  --previous-code-chars 2200 \
  --curriculum-stage foundation

echo "[$(date -Is)] Smoke: running one GRPO step with 8192 completion budget"
uv run training/train_grpo_cadforge.py \
  --model unsloth/Qwen3.5-9B \
  --adapter "$BASE_ADAPTER" \
  --rl-jsonl "$CURRICULUM" \
  --output-dir "$OUT" \
  --reward-backend cadforge \
  --strict-build-gate \
  --cadforge-python "$ROOT/experiment-2-cadforge/.venv/bin/python" \
  --cadforge-reward-mode fast \
  --limit-prompts 4 \
  --max-steps 1 \
  --num-generations 2 \
  --max-prompt-length 4096 \
  --max-completion-length 8192 \
  --max-seq-length 16384 \
  --per-device-train-batch-size 1 \
  --gradient-accumulation-steps 2 \
  --learning-rate 2e-6 \
  --debug-completions-jsonl "$DEBUG" \
  --run-name cadforge-smoke-8192

echo "[$(date -Is)] Smoke: inspecting completions"
python - "$DEBUG" <<'PY'
import collections
import json
import pathlib
import sys

path = pathlib.Path(sys.argv[1])
rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
builds = collections.Counter(row.get("cadforge_build") for row in rows)
fixtures = sum(bool(row.get("has_fixture")) for row in rows)
imports = sum(bool(row.get("has_cadquery_import")) for row in rows)
lengths = [len(row.get("code", "")) for row in rows]
print(f"rows={len(rows)} builds={dict(builds)} fixtures={fixtures} imports={imports} code_chars={lengths}")
if not rows:
    raise SystemExit("Smoke failed: no debug completions were written")
if fixtures < len(rows):
    raise SystemExit("Smoke failed: at least one completion lacked fixture")
if imports < len(rows):
    raise SystemExit("Smoke failed: at least one completion lacked cadquery import")
if max(lengths, default=0) < 1000:
    raise SystemExit("Smoke failed: completions are unexpectedly short")
print("Smoke passed: launch path, completion budget, and reward backend are alive.")
PY
