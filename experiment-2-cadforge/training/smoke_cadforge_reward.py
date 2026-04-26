#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "huggingface_hub",
#     "hf_transfer",
# ]
# ///
"""Smoke-test the CADForge reward backend with one known-good SFT row."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
APP_ROOT = REPO_ROOT / "experiment-2-cadforge"
DEFAULT_ROW_FILE = APP_ROOT / "data/sft/cadquery_prompt_to_cadquery_train.jsonl"
DEFAULT_ENV = APP_ROOT / "python_tools/cadquery_env.py"
DEFAULT_PROJECT_PYTHON = APP_ROOT / ".venv/bin/python"
DEFAULT_ROOT_PYTHON = REPO_ROOT / ".venv/bin/python"
DATASET_REPO = "sanjuhs/cadforge-cadquery-agentic-traces"


def resolve_row_file(path: Path) -> Path:
    if path.exists():
        return path
    from huggingface_hub import hf_hub_download

    return Path(hf_hub_download(
        repo_id=DATASET_REPO,
        repo_type="dataset",
        filename="data/sft/cadquery_prompt_to_cadquery_train.jsonl",
    ))


def read_first_row(path: Path) -> dict[str, Any]:
    with path.open() as handle:
        for line in handle:
            if line.strip():
                return json.loads(line)
    raise ValueError(f"No rows found in {path}")


def assistant_code(row: dict[str, Any]) -> str:
    for message in reversed(row["messages"]):
        if message.get("role") == "assistant":
            return message["content"]
    raise ValueError("No assistant code found")


def parse_json_stdout(stdout: str) -> dict[str, Any]:
    text = stdout.strip()
    if not text:
        raise ValueError("Reward backend returned empty stdout")
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end < start:
        raise ValueError(f"Reward backend did not return JSON:\n{text[-1000:]}")
    return json.loads(text[start : end + 1])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--row-file", type=Path, default=DEFAULT_ROW_FILE)
    parser.add_argument(
        "--python",
        type=Path,
        default=DEFAULT_PROJECT_PYTHON if DEFAULT_PROJECT_PYTHON.exists() else DEFAULT_ROOT_PYTHON if DEFAULT_ROOT_PYTHON.exists() else Path(sys.executable),
    )
    parser.add_argument("--reward-mode", choices=["fast", "full"], default="fast")
    parser.add_argument("--episode-id", default="training-smoke")
    parser.add_argument("--step-id", default="known-good-cold-start")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    row = read_first_row(resolve_row_file(args.row_file))
    task_id = row.get("task_id") or row.get("task_spec", {}).get("id") or ""
    code = assistant_code(row)

    with tempfile.TemporaryDirectory(prefix="cadforge-smoke-") as tmp:
        code_path = Path(tmp) / "candidate.py"
        code_path.write_text(code)
        cmd = [
            str(args.python),
            str(DEFAULT_ENV),
            "evaluate",
            "--code-file",
            str(code_path),
            "--episode-id",
            args.episode_id,
            "--step-id",
            args.step_id,
            "--task-prompt",
            row.get("task_spec", {}).get("prompt", ""),
            "--reward-mode",
            args.reward_mode,
        ]
        if task_id:
            cmd.extend(["--task-spec", task_id])

        proc = subprocess.run(cmd, cwd=APP_ROOT, text=True, capture_output=True, timeout=240)
        if proc.returncode != 0:
            print(proc.stdout)
            print(proc.stderr, file=sys.stderr)
            raise SystemExit(proc.returncode)

    result = parse_json_stdout(proc.stdout)
    reward = result.get("reward", {})
    print(json.dumps({
        "ok": True,
        "task_id": task_id,
        "reward_mode": args.reward_mode,
        "total": reward.get("total"),
        "build": reward.get("build"),
        "topology": reward.get("topology"),
        "contact": reward.get("contact"),
        "semantic_parts": reward.get("semantic_parts"),
        "reference_similarity": reward.get("reference_similarity"),
        "editability": reward.get("editability"),
        "artifacts_dir": result.get("artifacts_dir"),
    }, indent=2))


if __name__ == "__main__":
    main()
