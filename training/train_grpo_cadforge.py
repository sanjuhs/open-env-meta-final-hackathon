#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "trl==0.22.2",
#     "transformers==4.57.3",
#     "accelerate",
#     "peft",
#     "datasets",
#     "huggingface_hub",
#     "hf_transfer",
#     "trackio",
#     "tensorboard",
# ]
# ///
"""CADForge GRPO smoke/production script.

Use --reward-backend cheap for a fast wiring smoke test, then --reward-backend
cadforge on the RunPod once CadQuery dependencies and references are present.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


DATASET_REPO = "sanjuhs/cadforge-cadquery-agentic-traces"
REPO_ROOT = Path(__file__).resolve().parents[1]
APP_ROOT = REPO_ROOT / "experiment-2-cadforge"
DEFAULT_RL = APP_ROOT / "data/rl/cadquery_rollouts.jsonl"
CADQUERY_ENV = APP_ROOT / "python_tools/cadquery_env.py"
DEFAULT_PYTHON = REPO_ROOT / ".venv/bin/python"


def extract_code(text: str) -> str:
    text = text or ""
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL | re.IGNORECASE)
    match = re.search(r"```(?:python|py)?\s*\n(.*?)```", text, re.IGNORECASE | re.DOTALL)
    return (match.group(1) if match else text).strip()


def parse_json_stdout(stdout: str) -> dict[str, Any]:
    text = stdout.strip()
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end < start:
        raise ValueError("No JSON object found in reward stdout")
    return json.loads(text[start : end + 1])


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    with path.open() as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def download_dataset_file(filename: str) -> Path:
    from huggingface_hub import hf_hub_download

    return Path(hf_hub_download(repo_id=DATASET_REPO, repo_type="dataset", filename=filename))


def resolve_or_download(path: Path, fallback_filename: str) -> Path:
    if path.exists():
        return path
    return download_dataset_file(fallback_filename)


def cheap_code_reward(completion: str) -> float:
    code = extract_code(completion)
    score = 0.0
    score += 0.25 if "import cadquery as cq" in code else 0.0
    score += 0.25 if re.search(r"\bfixture\s*=", code) else 0.0
    score += 0.20 if "cq.Workplane" in code else 0.0
    score += 0.15 if "def " in code else 0.0
    score += 0.10 if any(name in code.lower() for name in ["seat", "back", "arm", "base", "jaw", "hook", "leg", "rail"]) else 0.0
    score -= 0.25 if "```" in completion else 0.0
    score -= 0.50 if any(token in code for token in ["subprocess", "open(", "requests.", "os.system"]) else 0.0
    return max(0.0, min(1.0, score))


class CadforgeReward:
    def __init__(self, python_bin: Path, reward_mode: str, timeout: int) -> None:
        self.python_bin = python_bin
        self.reward_mode = reward_mode
        self.timeout = timeout

    def __call__(self, completion: str, task_id: str = "", task_prompt: str = "") -> float:
        code = extract_code(completion)
        if not code:
            return 0.0

        with tempfile.TemporaryDirectory(prefix="cadforge-grpo-") as tmp:
            code_path = Path(tmp) / "candidate.py"
            code_path.write_text(code)
            cmd = [
                str(self.python_bin),
                str(CADQUERY_ENV),
                "evaluate",
                "--code-file",
                str(code_path),
                "--episode-id",
                "grpo",
                "--step-id",
                "completion",
                "--task-prompt",
                task_prompt,
                "--reward-mode",
                self.reward_mode,
            ]
            if task_id:
                cmd.extend(["--task-spec", task_id])
            try:
                proc = subprocess.run(cmd, cwd=APP_ROOT, text=True, capture_output=True, timeout=self.timeout)
            except subprocess.TimeoutExpired:
                return 0.0
            if proc.returncode != 0:
                return 0.0
            try:
                result = parse_json_stdout(proc.stdout)
            except (json.JSONDecodeError, ValueError):
                return 0.0
            reward = result.get("reward", {})
            return float(reward.get("total", 0.0))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default="Qwen/Qwen3.5-2B")
    parser.add_argument("--rl-jsonl", type=Path, default=DEFAULT_RL)
    parser.add_argument("--output-dir", default="outputs/qwen35-2b-cadforge-grpo")
    parser.add_argument("--hub-model-id", default="")
    parser.add_argument("--limit-prompts", type=int, default=8)
    parser.add_argument("--max-steps", type=int, default=5)
    parser.add_argument("--num-generations", type=int, default=4)
    parser.add_argument("--max-prompt-length", type=int, default=4096)
    parser.add_argument("--max-completion-length", type=int, default=2048)
    parser.add_argument("--per-device-train-batch-size", type=int, default=1)
    parser.add_argument("--gradient-accumulation-steps", type=int, default=4)
    parser.add_argument("--learning-rate", type=float, default=5e-6)
    parser.add_argument("--reward-backend", choices=["cheap", "cadforge"], default="cheap")
    parser.add_argument("--cadforge-python", type=Path, default=DEFAULT_PYTHON if DEFAULT_PYTHON.exists() else Path(sys.executable))
    parser.add_argument("--cadforge-reward-mode", choices=["fast", "full"], default="fast")
    parser.add_argument("--cadforge-timeout", type=int, default=180)
    parser.add_argument("--push-to-hub", action="store_true")
    parser.add_argument("--trackio-project", default="cadforge")
    parser.add_argument("--run-name", default="qwen35-grpo-smoke")
    parser.add_argument("--use-vllm-server", action="store_true")
    parser.add_argument("--vllm-server-host", default="127.0.0.1")
    parser.add_argument("--vllm-server-port", type=int, default=8000)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    os.environ.setdefault("HF_HUB_ENABLE_HF_TRANSFER", "1")

    import torch
    from datasets import Dataset
    from trl import GRPOConfig, GRPOTrainer

    if not torch.cuda.is_available():
        raise SystemExit("CUDA is required for GRPO. Run this on the H200 RunPod.")

    rl_path = resolve_or_download(args.rl_jsonl, "data/rl/cadquery_rollouts.jsonl")
    rows = read_jsonl(rl_path)[: args.limit_prompts]
    dataset = Dataset.from_list([
        {
            "prompt": row["observation"],
            "task_id": row.get("task_id", ""),
            "task_prompt": row.get("observation", "")[:2000],
        }
        for row in rows
    ])

    cadforge_reward = CadforgeReward(args.cadforge_python, args.cadforge_reward_mode, args.cadforge_timeout)

    def reward_func(completions: list[str], task_id: list[str] | None = None, task_prompt: list[str] | None = None, **_: Any) -> list[float]:
        scores = []
        for index, completion in enumerate(completions):
            if args.reward_backend == "cheap":
                scores.append(cheap_code_reward(completion))
            else:
                scores.append(cadforge_reward(
                    completion,
                    task_id=(task_id or [""])[index],
                    task_prompt=(task_prompt or [""])[index],
                ))
        return scores

    config_kwargs: dict[str, Any] = {
        "output_dir": args.output_dir,
        "max_steps": args.max_steps,
        "per_device_train_batch_size": args.per_device_train_batch_size,
        "gradient_accumulation_steps": args.gradient_accumulation_steps,
        "learning_rate": args.learning_rate,
        "num_generations": args.num_generations,
        "max_prompt_length": args.max_prompt_length,
        "max_completion_length": args.max_completion_length,
        "logging_steps": 1,
        "save_steps": max(5, args.max_steps),
        "save_total_limit": 2,
        "bf16": True,
        "report_to": ["trackio", "tensorboard"],
        "project": args.trackio_project,
        "run_name": args.run_name,
        "push_to_hub": args.push_to_hub,
        "hub_model_id": args.hub_model_id or None,
    }
    if args.use_vllm_server:
        config_kwargs.update({
            "use_vllm": True,
            "vllm_mode": "server",
            "vllm_server_host": args.vllm_server_host,
            "vllm_server_port": args.vllm_server_port,
        })

    config = GRPOConfig(**config_kwargs)
    trainer = GRPOTrainer(
        model=args.model,
        reward_funcs=reward_func,
        train_dataset=dataset,
        args=config,
    )
    trainer.train()
    trainer.save_model(args.output_dir)
    if args.push_to_hub:
        trainer.push_to_hub()


if __name__ == "__main__":
    main()
