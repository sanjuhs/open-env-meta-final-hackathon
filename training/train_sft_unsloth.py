#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "unsloth",
#     "datasets",
#     "trl==0.22.2",
#     "transformers>=5.2.0",
#     "torch>=2.10.0",
#     "accelerate",
#     "peft",
#     "huggingface_hub",
#     "hf_transfer",
#     "trackio",
#     "tensorboard",
# ]
# ///
"""CADForge Qwen SFT with Unsloth BF16 LoRA.

Run this on the H200 RunPod. For local prep, use prepare_sft_mix.py first.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any


DATASET_REPO = "sanjuhs/cadforge-cadquery-agentic-traces"
REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TRAIN = REPO_ROOT / "training/output/cadforge_sft_mix_train.jsonl"
DEFAULT_VAL = REPO_ROOT / "training/output/cadforge_sft_mix_val.jsonl"


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


def ensure_mixed_files(train_path: Path, val_path: Path, cold_start_upsample: int) -> None:
    if train_path.exists() and val_path.exists():
        return
    prepare_script = REPO_ROOT / "training/prepare_sft_mix.py"
    subprocess.run(
        [
            sys.executable,
            str(prepare_script),
            "--cold-start-upsample",
            str(cold_start_upsample),
            "--output",
            str(train_path),
            "--val-output",
            str(val_path),
        ],
        cwd=REPO_ROOT,
        check=True,
    )


def tokenize_messages(tokenizer: Any, row: dict[str, Any], max_seq_length: int) -> dict[str, list[int]]:
    text = tokenizer.apply_chat_template(
        row["messages"],
        tokenize=False,
        add_generation_prompt=False,
    )
    encoded = tokenizer(
        text=text,
        truncation=True,
        max_length=max_seq_length,
        padding=False,
    )
    input_ids = encoded["input_ids"]
    attention_mask = encoded["attention_mask"]
    if input_ids and isinstance(input_ids[0], list):
        input_ids = input_ids[0]
    if attention_mask and isinstance(attention_mask[0], list):
        attention_mask = attention_mask[0]
    return {
        "input_ids": list(input_ids),
        "attention_mask": list(attention_mask),
        "labels": list(input_ids),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default="unsloth/Qwen3.5-2B", help="Base HF model id")
    parser.add_argument("--train-jsonl", type=Path, default=DEFAULT_TRAIN)
    parser.add_argument("--val-jsonl", type=Path, default=DEFAULT_VAL)
    parser.add_argument("--output-dir", default="outputs/qwen35-2b-cadforge-sft")
    parser.add_argument("--hub-model-id", default="", help="Optional HF model repo for push_to_hub")
    parser.add_argument("--max-seq-length", type=int, default=8192)
    parser.add_argument("--max-steps", type=int, default=10)
    parser.add_argument("--num-train-epochs", type=float, default=0.0)
    parser.add_argument("--per-device-train-batch-size", type=int, default=1)
    parser.add_argument("--gradient-accumulation-steps", type=int, default=8)
    parser.add_argument("--learning-rate", type=float, default=2e-4)
    parser.add_argument("--lora-r", type=int, default=16)
    parser.add_argument("--lora-alpha", type=int, default=32)
    parser.add_argument("--eval-steps", type=int, default=25)
    parser.add_argument("--save-steps", type=int, default=50)
    parser.add_argument("--logging-steps", type=int, default=1)
    parser.add_argument("--limit-train-rows", type=int, default=0)
    parser.add_argument("--limit-val-rows", type=int, default=0)
    parser.add_argument("--load-in-4bit", action="store_true")
    parser.add_argument("--push-to-hub", action="store_true")
    parser.add_argument("--trackio-project", default="cadforge")
    parser.add_argument("--enable-trackio", action="store_true")
    parser.add_argument("--run-name", default="qwen35-sft-smoke")
    parser.add_argument("--packing", action="store_true")
    parser.add_argument("--cold-start-upsample", type=int, default=4)
    return parser.parse_args()


def maybe_limit(rows: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    return rows[:limit] if limit and limit > 0 else rows


def main() -> None:
    args = parse_args()
    os.environ.setdefault("HF_HUB_ENABLE_HF_TRANSFER", "1")

    import unsloth  # noqa: F401  # Must be imported before TRL/Transformers for patching.
    from unsloth import FastLanguageModel

    import torch
    from datasets import Dataset
    from transformers import DataCollatorForSeq2Seq
    from trl import SFTConfig, SFTTrainer

    if not torch.cuda.is_available():
        raise SystemExit("CUDA is required for the Unsloth training script. Run this on the H200 RunPod.")

    ensure_mixed_files(args.train_jsonl, args.val_jsonl, args.cold_start_upsample)
    train_path = args.train_jsonl
    val_path = args.val_jsonl

    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=args.model,
        max_seq_length=args.max_seq_length,
        dtype=torch.bfloat16,
        load_in_4bit=args.load_in_4bit,
    )

    model = FastLanguageModel.get_peft_model(
        model,
        r=args.lora_r,
        lora_alpha=args.lora_alpha,
        lora_dropout=0,
        bias="none",
        use_gradient_checkpointing="unsloth",
        random_state=3407,
        target_modules=[
            "q_proj",
            "k_proj",
            "v_proj",
            "o_proj",
            "gate_proj",
            "up_proj",
            "down_proj",
        ],
    )

    train_rows = maybe_limit(read_jsonl(train_path), args.limit_train_rows)
    val_rows = maybe_limit(read_jsonl(val_path), args.limit_val_rows)
    train_dataset = Dataset.from_list([tokenize_messages(tokenizer, row, args.max_seq_length) for row in train_rows])
    val_dataset = Dataset.from_list([tokenize_messages(tokenizer, row, args.max_seq_length) for row in val_rows]) if val_rows else None

    max_steps = args.max_steps if args.max_steps > 0 else -1
    num_epochs = args.num_train_epochs if args.num_train_epochs > 0 else 1.0

    report_to = ["tensorboard"]
    if args.enable_trackio:
        report_to.insert(0, "trackio")

    config = SFTConfig(
        output_dir=args.output_dir,
        max_length=args.max_seq_length,
        remove_unused_columns=False,
        packing=args.packing,
        max_steps=max_steps,
        num_train_epochs=num_epochs,
        per_device_train_batch_size=args.per_device_train_batch_size,
        gradient_accumulation_steps=args.gradient_accumulation_steps,
        learning_rate=args.learning_rate,
        warmup_ratio=0.03,
        lr_scheduler_type="cosine",
        bf16=True,
        fp16=False,
        logging_steps=args.logging_steps,
        eval_strategy="steps" if val_dataset is not None else "no",
        eval_steps=args.eval_steps,
        save_strategy="steps",
        save_steps=args.save_steps,
        save_total_limit=3,
        report_to=report_to,
        project=args.trackio_project,
        run_name=args.run_name,
        push_to_hub=args.push_to_hub,
        hub_model_id=args.hub_model_id or None,
    )

    trainer = SFTTrainer(
        model=model,
        processing_class=tokenizer,
        train_dataset=train_dataset,
        eval_dataset=val_dataset,
        data_collator=DataCollatorForSeq2Seq(
            tokenizer=tokenizer,
            padding=True,
            label_pad_token_id=-100,
            return_tensors="pt",
        ),
        args=config,
    )
    trainer.train()
    trainer.save_model(args.output_dir)
    tokenizer.save_pretrained(args.output_dir)

    if args.push_to_hub:
        trainer.push_to_hub()


if __name__ == "__main__":
    main()
