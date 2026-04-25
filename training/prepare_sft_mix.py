#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "huggingface_hub",
#     "hf_transfer",
# ]
# ///
"""Build the CADForge mixed SFT JSONL used for Qwen LoRA training.

The mix intentionally repeats cold-start prompt->CadQuery rows because there
are far fewer of them than repair rows.
"""

from __future__ import annotations

import argparse
import json
import os
import random
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DATASET_REPO = "sanjuhs/cadforge-cadquery-agentic-traces"
DEFAULT_COLD_TRAIN = REPO_ROOT / "experiment-2-cadforge/data/sft/cadquery_prompt_to_cadquery_train.jsonl"
DEFAULT_REPAIR_TRAIN = REPO_ROOT / "experiment-2-cadforge/data/sft/cadquery_agentic_sft_train.jsonl"
DEFAULT_COLD_VAL = REPO_ROOT / "experiment-2-cadforge/data/sft/cadquery_prompt_to_cadquery_val.jsonl"
DEFAULT_REPAIR_VAL = REPO_ROOT / "experiment-2-cadforge/data/sft/cadquery_agentic_sft_val.jsonl"
DEFAULT_OUT = REPO_ROOT / "training/output/cadforge_sft_mix_train.jsonl"
DEFAULT_VAL_OUT = REPO_ROOT / "training/output/cadforge_sft_mix_val.jsonl"


def download_dataset_file(filename: str) -> Path:
    from huggingface_hub import hf_hub_download

    os.environ.setdefault("HF_HUB_ENABLE_HF_TRANSFER", "1")
    return Path(hf_hub_download(repo_id=DATASET_REPO, repo_type="dataset", filename=filename))


def resolve_data_file(path: Path, fallback_filename: str) -> Path:
    if path.exists():
        return path
    print(f"{path} not found; downloading {fallback_filename} from {DATASET_REPO}")
    return download_dataset_file(fallback_filename)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open() as handle:
        for line_number, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            validate_row(row, path, line_number)
            rows.append(row)
    return rows


def validate_row(row: dict[str, Any], path: Path, line_number: int) -> None:
    messages = row.get("messages")
    if not isinstance(messages, list) or len(messages) < 2:
        raise ValueError(f"{path}:{line_number} missing messages list")
    roles = [message.get("role") for message in messages if isinstance(message, dict)]
    if "user" not in roles or roles[-1] != "assistant":
        raise ValueError(f"{path}:{line_number} expected user context and final assistant answer")
    for message in messages:
        if not isinstance(message.get("content"), str) or not message["content"].strip():
            raise ValueError(f"{path}:{line_number} has an empty message")


def tag_rows(rows: list[dict[str, Any]], source: str, repeat_index: int = 0) -> list[dict[str, Any]]:
    tagged = []
    for row in rows:
        copied = dict(row)
        copied["sft_mix_source"] = source
        copied["sft_mix_repeat_index"] = repeat_index
        tagged.append(copied)
    return tagged


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def build_mix(
    cold_rows: list[dict[str, Any]],
    repair_rows: list[dict[str, Any]],
    cold_start_upsample: int,
    seed: int,
) -> list[dict[str, Any]]:
    if cold_start_upsample < 1:
        raise ValueError("--cold-start-upsample must be >= 1")

    mixed: list[dict[str, Any]] = []
    for repeat_index in range(cold_start_upsample):
        mixed.extend(tag_rows(cold_rows, "cold_start_prompt_to_cadquery", repeat_index))
    mixed.extend(tag_rows(repair_rows, "agentic_repair", 0))

    rng = random.Random(seed)
    rng.shuffle(mixed)
    return mixed


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cold-train", type=Path, default=DEFAULT_COLD_TRAIN)
    parser.add_argument("--repair-train", type=Path, default=DEFAULT_REPAIR_TRAIN)
    parser.add_argument("--cold-val", type=Path, default=DEFAULT_COLD_VAL)
    parser.add_argument("--repair-val", type=Path, default=DEFAULT_REPAIR_VAL)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--val-output", type=Path, default=DEFAULT_VAL_OUT)
    parser.add_argument("--cold-start-upsample", type=int, default=4)
    parser.add_argument("--seed", type=int, default=3407)
    parser.add_argument("--max-cold-start-rows", type=int, default=0, help="Optional smoke-test limit")
    parser.add_argument("--max-repair-rows", type=int, default=0, help="Optional smoke-test limit")
    return parser.parse_args()


def maybe_limit(rows: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    return rows[:limit] if limit and limit > 0 else rows


def main() -> None:
    args = parse_args()

    cold_train_path = resolve_data_file(args.cold_train, "data/sft/cadquery_prompt_to_cadquery_train.jsonl")
    repair_train_path = resolve_data_file(args.repair_train, "data/sft/cadquery_agentic_sft_train.jsonl")
    cold_val_path = resolve_data_file(args.cold_val, "data/sft/cadquery_prompt_to_cadquery_val.jsonl")
    repair_val_path = resolve_data_file(args.repair_val, "data/sft/cadquery_agentic_sft_val.jsonl")

    cold_train = maybe_limit(read_jsonl(cold_train_path), args.max_cold_start_rows)
    repair_train = maybe_limit(read_jsonl(repair_train_path), args.max_repair_rows)
    train_rows = build_mix(cold_train, repair_train, args.cold_start_upsample, args.seed)
    write_jsonl(args.output, train_rows)

    cold_val = read_jsonl(cold_val_path)
    repair_val = read_jsonl(repair_val_path)
    val_rows = build_mix(cold_val, repair_val, 1, args.seed)
    write_jsonl(args.val_output, val_rows)

    summary = {
        "train_output": str(args.output),
        "val_output": str(args.val_output),
        "cold_train_rows": len(cold_train),
        "repair_train_rows": len(repair_train),
        "cold_start_upsample": args.cold_start_upsample,
        "mixed_train_rows": len(train_rows),
        "mixed_val_rows": len(val_rows),
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
