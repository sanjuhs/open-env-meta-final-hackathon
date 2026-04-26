#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "unsloth",
#     "transformers>=5.2.0",
#     "torch>=2.10.0",
#     "peft",
#     "datasets",
#     "huggingface_hub",
#     "hf_transfer",
#     "tqdm",
# ]
# ///
"""Generate CadQuery with a trained Qwen adapter and score it in CADForge."""

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


REPO_ROOT = Path(__file__).resolve().parents[1]
APP_ROOT = REPO_ROOT / "experiment-2-cadforge"
DEFAULT_VAL = REPO_ROOT / "training/output/cadforge_sft_mix_val.jsonl"
CADQUERY_ENV = APP_ROOT / "python_tools/cadquery_env.py"
DEFAULT_PYTHON = APP_ROOT / ".venv/bin/python"


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    with path.open() as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def assistantless_messages(row: dict[str, Any]) -> list[dict[str, str]]:
    messages = row["messages"]
    trimmed = []
    for message in messages:
        if message.get("role") == "assistant":
            break
        trimmed.append({"role": message["role"], "content": message["content"]})
    return trimmed


def extract_code(text: str) -> str:
    text = re.sub(r"<think>.*?</think>", "", text or "", flags=re.DOTALL | re.IGNORECASE)
    match = re.search(r"```(?:python|py)?\s*\n(.*?)```", text, re.IGNORECASE | re.DOTALL)
    code = match.group(1) if match else text
    return code.strip()


def parse_json_stdout(stdout: str) -> dict[str, Any]:
    text = stdout.strip()
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end < start:
        raise ValueError("No JSON object found in CADForge stdout")
    return json.loads(text[start : end + 1])


def task_prompt(row: dict[str, Any]) -> str:
    spec = row.get("task_spec") or {}
    if spec.get("prompt"):
        return str(spec["prompt"])
    for message in row.get("messages", []):
        if message.get("role") == "user":
            return str(message.get("content", ""))
    return ""


def task_id(row: dict[str, Any]) -> str:
    spec = row.get("task_spec") or {}
    return str(row.get("task_id") or spec.get("id") or "")


def evaluate_code(
    code: str,
    row: dict[str, Any],
    index: int,
    python_bin: Path,
    reward_mode: str,
    timeout: int,
    episode_prefix: str,
) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="cadforge-eval-") as tmp:
        code_path = Path(tmp) / "candidate.py"
        code_path.write_text(code)
        cmd = [
            str(python_bin),
            str(CADQUERY_ENV),
            "evaluate",
            "--code-file",
            str(code_path),
            "--episode-id",
            f"{episode_prefix}-{index:03d}",
            "--step-id",
            "model-output",
            "--task-prompt",
            task_prompt(row),
            "--reward-mode",
            reward_mode,
        ]
        tid = task_id(row)
        if tid:
            cmd.extend(["--task-spec", tid])
        proc = subprocess.run(cmd, cwd=APP_ROOT, text=True, capture_output=True, timeout=timeout)
    if proc.returncode != 0:
        return {
            "ok": False,
            "reward": {"total": -1.0, "build": 0.0},
            "error": (proc.stderr or proc.stdout)[-2000:],
        }
    return parse_json_stdout(proc.stdout)


def apply_chat_template(tokenizer: Any, messages: list[dict[str, str]], disable_thinking: bool) -> str:
    kwargs = {
        "tokenize": False,
        "add_generation_prompt": True,
    }
    if disable_thinking:
        kwargs["enable_thinking"] = False
    try:
        return tokenizer.apply_chat_template(messages, **kwargs)
    except TypeError:
        kwargs.pop("enable_thinking", None)
        return tokenizer.apply_chat_template(messages, **kwargs)


def generate_one(
    model: Any,
    tokenizer: Any,
    messages: list[dict[str, str]],
    max_new_tokens: int,
    temperature: float,
    top_p: float,
    disable_thinking: bool,
) -> str:
    import torch

    text = apply_chat_template(tokenizer, messages, disable_thinking=disable_thinking)
    encoded = tokenizer(text=text, return_tensors="pt").to(model.device)
    generate_kwargs: dict[str, Any] = {
        **encoded,
        "max_new_tokens": max_new_tokens,
        "do_sample": temperature > 0,
        "top_p": top_p,
        "pad_token_id": tokenizer.eos_token_id,
    }
    if temperature > 0:
        generate_kwargs["temperature"] = temperature
    with torch.inference_mode():
        output_ids = model.generate(**generate_kwargs)
    new_ids = output_ids[0][encoded["input_ids"].shape[-1] :]
    return tokenizer.decode(new_ids, skip_special_tokens=True)


def markdown_report(results: list[dict[str, Any]], out_dir: Path) -> str:
    scores = [float(row["reward"].get("total", -1.0)) for row in results]
    builds = [float(row["reward"].get("build", 0.0)) for row in results]
    mean_score = sum(scores) / max(1, len(scores))
    build_rate = sum(1 for value in builds if value >= 1.0) / max(1, len(builds))
    best = max(results, key=lambda row: float(row["reward"].get("total", -1.0)), default=None)
    lines = [
        "# CADForge Model Evaluation",
        "",
        f"- Rows: `{len(results)}`",
        f"- Mean reward: `{mean_score:.3f}`",
        f"- Build rate: `{build_rate:.1%}`",
    ]
    if best:
        lines.extend([
            f"- Best task: `{best.get('task_id', '')}`",
            f"- Best reward: `{float(best['reward'].get('total', -1.0)):.3f}`",
            f"- Best artifacts: `{best.get('artifacts_dir', '')}`",
        ])
    lines.extend([
        "",
        "| # | task | reward | build | semantic | editability | artifacts |",
        "|---:|---|---:|---:|---:|---:|---|",
    ])
    for row in results:
        reward = row["reward"]
        lines.append(
            "| {index} | `{task}` | {total:.3f} | {build:.1f} | {semantic:.3f} | {editability:.3f} | `{artifacts}` |".format(
                index=row["index"],
                task=row.get("task_id", ""),
                total=float(reward.get("total", -1.0)),
                build=float(reward.get("build", 0.0)),
                semantic=float(reward.get("semantic_parts", 0.0)),
                editability=float(reward.get("editability", 0.0)),
                artifacts=row.get("artifacts_dir", ""),
            )
        )
    lines.extend([
        "",
        "## Files",
        "",
        f"- Raw rows: `{out_dir / 'eval_results.jsonl'}`",
        f"- Generated code: `{out_dir / 'generated_code'}`",
    ])
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-model", default="unsloth/Qwen3.5-2B")
    parser.add_argument("--adapter", default="", help="Optional LoRA adapter directory or HF repo")
    parser.add_argument("--eval-jsonl", type=Path, default=DEFAULT_VAL)
    parser.add_argument("--output-dir", type=Path, default=REPO_ROOT / "training/eval/qwen35-2b-cadforge-sft")
    parser.add_argument("--limit", type=int, default=16)
    parser.add_argument("--max-new-tokens", type=int, default=2048)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--top-p", type=float, default=0.95)
    parser.add_argument("--reward-mode", choices=["fast", "full"], default="fast")
    parser.add_argument("--python", type=Path, default=DEFAULT_PYTHON if DEFAULT_PYTHON.exists() else Path(sys.executable))
    parser.add_argument("--timeout", type=int, default=240)
    parser.add_argument("--episode-prefix", default="sft-eval")
    parser.add_argument("--disable-thinking", action="store_true", default=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    os.environ.setdefault("HF_HUB_ENABLE_HF_TRANSFER", "1")

    import unsloth  # noqa: F401
    from peft import PeftModel
    from tqdm import tqdm
    from unsloth import FastLanguageModel

    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=args.base_model,
        max_seq_length=8192,
        load_in_4bit=False,
    )
    if args.adapter:
        model = PeftModel.from_pretrained(model, args.adapter)
    FastLanguageModel.for_inference(model)

    rows = read_jsonl(args.eval_jsonl)[: args.limit]
    out_dir = args.output_dir
    code_dir = out_dir / "generated_code"
    code_dir.mkdir(parents=True, exist_ok=True)

    results: list[dict[str, Any]] = []
    for index, row in enumerate(tqdm(rows, desc="evaluating")):
        messages = assistantless_messages(row)
        raw = generate_one(
            model,
            tokenizer,
            messages,
            max_new_tokens=args.max_new_tokens,
            temperature=args.temperature,
            top_p=args.top_p,
            disable_thinking=args.disable_thinking,
        )
        code = extract_code(raw)
        code_path = code_dir / f"{index:03d}-{task_id(row) or 'task'}.py"
        code_path.write_text(code)
        eval_result = evaluate_code(
            code,
            row,
            index,
            python_bin=args.python,
            reward_mode=args.reward_mode,
            timeout=args.timeout,
            episode_prefix=args.episode_prefix,
        )
        reward = eval_result.get("reward", {"total": -1.0, "build": 0.0})
        results.append({
            "index": index,
            "task_id": task_id(row),
            "reward": reward,
            "ok": bool(eval_result.get("ok")),
            "artifacts_dir": eval_result.get("artifacts_dir"),
            "code_path": str(code_path),
            "raw_completion": raw,
            "notes": eval_result.get("notes", []),
        })

    write_jsonl(out_dir / "eval_results.jsonl", results)
    (out_dir / "eval_report.md").write_text(markdown_report(results, out_dir))
    print(json.dumps({
        "rows": len(results),
        "output_dir": str(out_dir),
        "report": str(out_dir / "eval_report.md"),
        "mean_reward": sum(float(row["reward"].get("total", -1.0)) for row in results) / max(1, len(results)),
        "build_rate": sum(1 for row in results if float(row["reward"].get("build", 0.0)) >= 1.0) / max(1, len(results)),
    }, indent=2))


if __name__ == "__main__":
    main()
