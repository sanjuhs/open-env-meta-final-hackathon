#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "trl==0.22.2",
#     "transformers>=5.2.0",
#     "torch==2.10.0",
#     "torchvision==0.25.0",
#     "accelerate",
#     "peft",
#     "datasets",
#     "huggingface_hub",
#     "hf_transfer",
#     "trackio",
#     "tensorboard",
#     "vllm>=0.13.0",
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
DEFAULT_TASKS = APP_ROOT / "data/cad_tasks.json"
DEFAULT_PYTHON = REPO_ROOT / ".venv/bin/python"


def completion_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        parts = []
        for item in value:
            if isinstance(item, dict):
                role = item.get("role")
                content = item.get("content", "")
                if role == "assistant" and isinstance(content, str):
                    parts.append(content)
            elif isinstance(item, str):
                parts.append(item)
        if parts:
            return "\n".join(parts)
    return str(value or "")


def extract_code(text: Any) -> str:
    text = completion_text(text)
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL | re.IGNORECASE)
    match = re.search(r"```(?:python|py)?\s*\n(.*?)```", text, re.IGNORECASE | re.DOTALL)
    code = (match.group(1) if match else text).strip()
    import_index = code.find("import cadquery as cq")
    if import_index > 0:
        code = code[import_index:]
    return code.strip()


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


def assistantless_messages(row: dict[str, Any]) -> list[dict[str, str]]:
    messages = row.get("messages")
    if not isinstance(messages, list):
        return []
    trimmed = []
    for message in messages:
        if message.get("role") == "assistant":
            break
        if isinstance(message.get("content"), str):
            trimmed.append({"role": message.get("role", "user"), "content": message["content"]})
    return trimmed


def row_task_id(row: dict[str, Any]) -> str:
    spec = row.get("task_spec") if isinstance(row.get("task_spec"), dict) else {}
    return str(row.get("task_id") or spec.get("id") or "")


def row_task_prompt(row: dict[str, Any]) -> str:
    spec = row.get("task_spec") if isinstance(row.get("task_spec"), dict) else {}
    if spec.get("prompt"):
        return str(spec["prompt"])
    for message in row.get("messages", []):
        if message.get("role") == "user":
            return str(message.get("content", ""))[:2000]
    return str(row.get("observation", ""))[:2000]


def download_dataset_file(filename: str) -> Path:
    from huggingface_hub import hf_hub_download

    return Path(hf_hub_download(repo_id=DATASET_REPO, repo_type="dataset", filename=filename))


def resolve_or_download(path: Path, fallback_filename: str) -> Path:
    if path.exists():
        return path
    return download_dataset_file(fallback_filename)


def known_task_ids() -> set[str]:
    if not DEFAULT_TASKS.exists():
        return set()
    try:
        return {str(row.get("id")) for row in json.loads(DEFAULT_TASKS.read_text()) if row.get("id")}
    except json.JSONDecodeError:
        return set()


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
        self.last_error = ""
        self.last_stdout = ""
        self.last_stderr = ""
        self.last_result: dict[str, Any] = {}

    def __call__(self, completion: str, task_id: str = "", task_prompt: str = "") -> float:
        code = extract_code(completion)
        self.last_error = ""
        self.last_stdout = ""
        self.last_stderr = ""
        self.last_result = {}
        if not code:
            self.last_error = "empty extracted code"
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
                self.last_error = "cadforge reward timeout"
                return 0.0
            self.last_stdout = proc.stdout[-2000:]
            self.last_stderr = proc.stderr[-2000:]
            if proc.returncode != 0:
                self.last_error = f"cadforge returncode {proc.returncode}"
                return 0.0
            try:
                result = parse_json_stdout(proc.stdout)
            except (json.JSONDecodeError, ValueError):
                self.last_error = "cadforge reward stdout json parse failed"
                return 0.0
            self.last_result = result
            reward = result.get("reward", {})
            if float(reward.get("total", 0.0)) == 0.0:
                self.last_error = "cadforge reward total was zero"
            return float(reward.get("total", 0.0))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default="unsloth/Qwen3.5-2B")
    parser.add_argument("--adapter", default="", help="Optional SFT LoRA adapter to continue from")
    parser.add_argument("--rl-jsonl", type=Path, default=DEFAULT_RL)
    parser.add_argument("--output-dir", default="outputs/qwen35-2b-cadforge-grpo")
    parser.add_argument("--hub-model-id", default="")
    parser.add_argument("--limit-prompts", type=int, default=8)
    parser.add_argument("--max-steps", type=int, default=5)
    parser.add_argument("--num-generations", type=int, default=4)
    parser.add_argument("--max-prompt-length", type=int, default=4096)
    parser.add_argument("--max-completion-length", type=int, default=2048)
    parser.add_argument("--max-seq-length", type=int, default=8192)
    parser.add_argument("--per-device-train-batch-size", type=int, default=1)
    parser.add_argument("--gradient-accumulation-steps", type=int, default=4)
    parser.add_argument("--learning-rate", type=float, default=5e-6)
    parser.add_argument("--reward-backend", choices=["cheap", "cadforge"], default="cheap")
    parser.add_argument("--build-fail-shaping", action="store_true", help="Use a small code-structure reward when CAD execution fails.")
    parser.add_argument("--strict-build-gate", action="store_true", help="Make executable CadQuery build success the first reward gate.")
    parser.add_argument("--cadforge-python", type=Path, default=DEFAULT_PYTHON if DEFAULT_PYTHON.exists() else Path(sys.executable))
    parser.add_argument("--cadforge-reward-mode", choices=["fast", "full"], default="fast")
    parser.add_argument("--cadforge-timeout", type=int, default=180)
    parser.add_argument("--push-to-hub", action="store_true")
    parser.add_argument("--trackio-project", default="cadforge")
    parser.add_argument("--enable-trackio", action="store_true")
    parser.add_argument("--run-name", default="qwen35-grpo-smoke")
    parser.add_argument("--debug-completions-jsonl", type=Path, default=Path(""))
    parser.add_argument("--use-vllm-server", action="store_true")
    parser.add_argument("--vllm-server-host", default="127.0.0.1")
    parser.add_argument("--vllm-server-port", type=int, default=8000)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    os.environ.setdefault("HF_HUB_ENABLE_HF_TRANSFER", "1")

    import torch
    from datasets import Dataset
    from transformers import AutoModelForImageTextToText, AutoTokenizer, PreTrainedModel
    import trl.import_utils as trl_import_utils
    import vllm.sampling_params as vllm_sampling_params

    # Some TRL/vLLM builds can detect a partial Ascend package on NVIDIA images
    # and then fail importing its HCCL communicator. CADForge RunPod uses CUDA.
    trl_import_utils._vllm_ascend_available = False
    # MergeKit is optional for TRL model-merge callbacks; the package can pull
    # old vLLM versions, so keep it disabled for GRPO training.
    trl_import_utils._mergekit_available = False
    # PairRM judges are optional and not used for CADForge scalar rewards.
    trl_import_utils._llm_blender_available = False
    if not hasattr(vllm_sampling_params, "GuidedDecodingParams"):
        class GuidedDecodingParams:  # Compatibility shim for TRL/vLLM API drift.
            def __init__(self, *args: Any, **kwargs: Any) -> None:
                self.args = args
                self.kwargs = kwargs

        vllm_sampling_params.GuidedDecodingParams = GuidedDecodingParams
    from trl import GRPOConfig, GRPOTrainer

    if not torch.cuda.is_available():
        raise SystemExit("CUDA is required for GRPO. Run this on the H200 RunPod.")
    if not hasattr(PreTrainedModel, "warnings_issued"):
        PreTrainedModel.warnings_issued = {}

    rl_path = resolve_or_download(args.rl_jsonl, "data/rl/cadquery_rollouts.jsonl")
    rows = read_jsonl(rl_path)[: args.limit_prompts]
    valid_task_ids = known_task_ids()
    system_prompt = (
        "You are CADForge, a careful CadQuery CAD generation and repair agent.\n"
        "Return only a complete executable Python CadQuery file. Do not return markdown fences.\n"
        "Use import cadquery as cq.\n"
        "Assign the final exportable object to fixture.\n"
        "Prefer named dimensions and helper functions so the CAD can be edited in later steps.\n"
        "Use conservative CadQuery operations: box, cylinder, circle/extrude, union, cut, fillet, translate, rotate.\n"
        "Do not invent APIs like Workplane.cone; do not put spaces in variable names; keep every statement valid Python.\n"
        "End the file immediately after assigning fixture = fixture.clean() or fixture = assembly.clean()."
    )
    prompt_rows = []
    for row in rows:
        tid = row_task_id(row)
        messages = assistantless_messages(row)
        if not messages:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": row["observation"] + "\n\nReturn only the complete updated Python file."},
            ]
        prompt_rows.append({
            "prompt": messages,
            "task_id": tid if tid in valid_task_ids else "",
            "task_prompt": row_task_prompt(row),
        })
    dataset = Dataset.from_list(prompt_rows)

    cadforge_reward = CadforgeReward(args.cadforge_python, args.cadforge_reward_mode, args.cadforge_timeout)
    reward_call_count = 0

    def reward_func(completions: list[str], task_id: list[str] | None = None, task_prompt: list[str] | None = None, **_: Any) -> list[float]:
        nonlocal reward_call_count
        reward_call_count += 1
        scores = []
        debug_rows = []
        for index, completion in enumerate(completions):
            code = extract_code(completion)
            code_score = cheap_code_reward(completion)
            if args.reward_backend == "cheap":
                score = code_score
            else:
                score = cadforge_reward(
                    completion,
                    task_id=(task_id or [""])[index],
                    task_prompt=(task_prompt or [""])[index],
                )
                reward_json = cadforge_reward.last_result.get("reward", {}) if isinstance(cadforge_reward.last_result, dict) else {}
                build_score = float(reward_json.get("build", 0.0) or 0.0)
                if args.strict_build_gate:
                    if build_score < 1.0:
                        score = -0.85 + 0.30 * code_score
                        error_text = f"{cadforge_reward.last_error}\n{cadforge_reward.last_stdout}\n{cadforge_reward.last_stderr}"
                        if "SyntaxError" in error_text:
                            score -= 0.10
                        if "AttributeError" in error_text or "NameError" in error_text:
                            score -= 0.05
                        if "import cadquery as cq" not in code or not re.search(r"\bfixture\s*=", code):
                            score -= 0.10
                        score = max(-1.0, min(-0.05, score))
                    else:
                        score = max(0.05, min(1.0, 0.15 + 0.85 * score))
                elif args.build_fail_shaping and score <= -1.0:
                    score = max(-0.25, -0.20 + 0.60 * code_score)
            scores.append(score)
            if args.debug_completions_jsonl:
                reward_json = cadforge_reward.last_result.get("reward", {}) if args.reward_backend == "cadforge" and isinstance(cadforge_reward.last_result, dict) else {}
                debug_rows.append({
                    "reward_call": reward_call_count,
                    "index": index,
                    "score": score,
                    "task_id": (task_id or [""])[index],
                    "completion_chars": len(completion_text(completion)),
                    "code_chars": len(code),
                    "has_fixture": "fixture" in code,
                    "has_cadquery_import": "import cadquery as cq" in code,
                    "completion_head": completion_text(completion)[:1000],
                    "code_head": code[:1000],
                    "code": code if len(code) <= 20000 else code[:20000],
                    "cadforge_reward": reward_json,
                    "cadforge_build": float(reward_json.get("build", 0.0) or 0.0),
                    "cadforge_total": float(reward_json.get("total", 0.0) or 0.0),
                    "cadforge_error": cadforge_reward.last_error if args.reward_backend == "cadforge" else "",
                    "cadforge_stdout_tail": cadforge_reward.last_stdout if args.reward_backend == "cadforge" else "",
                    "cadforge_stderr_tail": cadforge_reward.last_stderr if args.reward_backend == "cadforge" else "",
                })
        if args.debug_completions_jsonl and debug_rows:
            args.debug_completions_jsonl.parent.mkdir(parents=True, exist_ok=True)
            with args.debug_completions_jsonl.open("a") as handle:
                for row in debug_rows:
                    handle.write(json.dumps(row, ensure_ascii=False) + "\n")
        return scores

    report_to = ["tensorboard"]
    if args.enable_trackio:
        report_to.insert(0, "trackio")

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
        "report_to": report_to,
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
    if args.adapter and args.use_vllm_server:
        raise SystemExit("--adapter with --use-vllm-server is not wired yet; use direct GRPO or merge/export first.")

    processing_class = None
    trainer_model: str | Any = args.model
    if args.adapter:
        from peft import PeftModel

        tokenizer = AutoTokenizer.from_pretrained(args.adapter, trust_remote_code=True)
        model = AutoModelForImageTextToText.from_pretrained(
            args.model,
            dtype=torch.bfloat16,
            device_map="auto",
            trust_remote_code=True,
        )
        trainer_model = PeftModel.from_pretrained(model, args.adapter, is_trainable=True)
        processing_class = tokenizer

    trainer = GRPOTrainer(
        model=trainer_model,
        reward_funcs=reward_func,
        train_dataset=dataset,
        args=config,
        processing_class=processing_class,
    )
    trainer.train()
    trainer.save_model(args.output_dir)
    if args.push_to_hub:
        trainer.push_to_hub()


if __name__ == "__main__":
    main()
