# CADForge Qwen Training Runbook

## Goal

Train a small Qwen model to produce editable, buildable CadQuery and then improve it through reward feedback.

The hackathon story is:

1. Base Qwen often writes invalid or incomplete CadQuery.
2. SFT teaches two behaviors: create CAD from a prompt and repair CAD from verifier feedback.
3. GRPO/RLVE then rewards buildable, connected, semantically correct, editable CAD.
4. The environment stores artifacts, reward JSON, code, and renders, so improvement is visible and auditable.

## Hardware

Use the H200 for the real run.

Recommended setup:

- GPU: 1x H200 141 GB
- CUDA image: PyTorch 2.8 or latest RunPod PyTorch CUDA image
- Python: 3.10 or 3.11
- Package runner: `uv`
- Training dtype: BF16
- Method: Unsloth LoRA SFT first, then TRL GRPO

Do not start with QLoRA on the H200. BF16 LoRA is cleaner and the GPU has enough memory.

## Data Mix

The first SFT run should mix:

- all cold-start rows from `cadquery_prompt_to_cadquery_train.jsonl`
- all repair rows from `cadquery_agentic_sft_train.jsonl`
- cold-start rows repeated 4x

Upsampling means repeating the cold-start rows. It does not mean skipping them.

Why repeat them? We only have 20 cold-start train rows but 633 repair train rows. If each appears once, the model mostly learns "repair existing CAD." The demo also needs "write the first complete CAD file from a prompt," so we repeat cold-start rows to keep that behavior visible during training.

Expected mixed train size:

```text
20 cold-start rows * 4 = 80 cold-start examples
633 repair rows * 1 = 633 repair examples
total = 713 train examples
```

## Local Prep Commands

From the repo root:

```bash
uv run training/prepare_sft_mix.py --cold-start-upsample 4
uv run training/smoke_cadforge_reward.py --reward-mode fast
```

The first command creates:

- `training/output/cadforge_sft_mix_train.jsonl`
- `training/output/cadforge_sft_mix_val.jsonl`

The second command verifies that the CadQuery reward backend can build and score one known-good row.

## RunPod Setup

After the RunPod starts:

```bash
apt-get update
apt-get install -y git git-lfs build-essential curl
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.local/bin/env
git lfs install
git clone https://github.com/sanjuhs/open-env-meta-final-hackathon.git
cd open-env-meta-final-hackathon
```

Set secrets:

```bash
export HF_TOKEN=...
export TRACKIO_SPACE_ID=sanjuhs/cadforge-trackio
```

Install the app/runtime dependencies:

```bash
uv sync --project experiment-2-cadforge
uv run training/prepare_sft_mix.py --cold-start-upsample 4
uv run training/smoke_cadforge_reward.py --reward-mode fast
```

If the generated local data files are not present in git, the training scripts can download the uploaded dataset from Hugging Face.

## SFT Smoke Test

Run this first. It should take only a few minutes on the H200.

```bash
uv run training/train_sft_unsloth.py \
  --model Qwen/Qwen3.5-2B \
  --output-dir outputs/qwen35-2b-cadforge-sft-smoke \
  --max-steps 10 \
  --limit-train-rows 32 \
  --limit-val-rows 8 \
  --max-seq-length 4096 \
  --per-device-train-batch-size 1 \
  --gradient-accumulation-steps 4 \
  --lora-r 16 \
  --lora-alpha 32 \
  --run-name qwen35-2b-sft-smoke
```

Success criteria:

- model loads in BF16
- LoRA attaches
- loss logs for 10 steps
- one checkpoint/output folder is written
- no chat-template/data-format crash

## SFT Real 2B Run

```bash
uv run training/train_sft_unsloth.py \
  --model Qwen/Qwen3.5-2B \
  --output-dir outputs/qwen35-2b-cadforge-sft \
  --hub-model-id sanjuhs/qwen35-2b-cadforge-sft-lora \
  --push-to-hub \
  --max-steps 0 \
  --num-train-epochs 3 \
  --max-seq-length 8192 \
  --per-device-train-batch-size 1 \
  --gradient-accumulation-steps 8 \
  --learning-rate 2e-4 \
  --lora-r 16 \
  --lora-alpha 32 \
  --eval-steps 25 \
  --save-steps 50 \
  --run-name qwen35-2b-sft-full
```

Watch:

- train loss
- eval loss
- generated sample build rate after training
- whether outputs contain only Python code, not markdown or thinking tags

## SFT Real 9B Run

Start this after the 2B path works:

```bash
uv run training/train_sft_unsloth.py \
  --model Qwen/Qwen3.5-9B \
  --output-dir outputs/qwen35-9b-cadforge-sft \
  --hub-model-id sanjuhs/qwen35-9b-cadforge-sft-lora \
  --push-to-hub \
  --max-steps 0 \
  --num-train-epochs 2 \
  --max-seq-length 8192 \
  --per-device-train-batch-size 1 \
  --gradient-accumulation-steps 8 \
  --learning-rate 1e-4 \
  --lora-r 32 \
  --lora-alpha 64 \
  --eval-steps 25 \
  --save-steps 50 \
  --run-name qwen35-9b-sft-full
```

## GRPO Smoke Test

First use the cheap reward backend. This verifies GRPO wiring without spending time on CadQuery execution for every completion.

```bash
uv run training/train_grpo_cadforge.py \
  --model Qwen/Qwen3.5-2B \
  --output-dir outputs/qwen35-2b-cadforge-grpo-smoke \
  --reward-backend cheap \
  --limit-prompts 8 \
  --max-steps 5 \
  --num-generations 4 \
  --max-prompt-length 4096 \
  --max-completion-length 1024 \
  --run-name qwen35-2b-grpo-cheap-smoke
```

Success criteria:

- GRPOTrainer starts
- four completions per prompt are generated
- reward function returns scalar scores
- loss/reward metrics log

## CADForge GRPO Smoke

Then use the real CADForge reward in fast mode:

```bash
uv run training/train_grpo_cadforge.py \
  --model Qwen/Qwen3.5-2B \
  --output-dir outputs/qwen35-2b-cadforge-grpo-cadforge-smoke \
  --reward-backend cadforge \
  --cadforge-reward-mode fast \
  --limit-prompts 4 \
  --max-steps 2 \
  --num-generations 4 \
  --max-prompt-length 4096 \
  --max-completion-length 1536 \
  --run-name qwen35-2b-grpo-cadforge-smoke
```

This is slower because every completion is executed as CadQuery, exported to mesh, and scored.

## vLLM Server Mode

The judge recommended normal GRPO with vLLM serve mode, not async mode. The script exposes that path:

```bash
python -m vllm.entrypoints.openai.api_server \
  --model Qwen/Qwen3.5-2B \
  --host 127.0.0.1 \
  --port 8000
```

Then:

```bash
uv run training/train_grpo_cadforge.py \
  --model Qwen/Qwen3.5-2B \
  --use-vllm-server \
  --vllm-server-host 127.0.0.1 \
  --vllm-server-port 8000 \
  --reward-backend cadforge \
  --cadforge-reward-mode fast \
  --limit-prompts 16 \
  --max-steps 20 \
  --num-generations 4 \
  --run-name qwen35-2b-grpo-vllm-server-smoke
```

If the local TRL version changes vLLM config names, disable `--use-vllm-server` for the first proof run and use standard colocated generation.

## GRPO Real Run

Only do the real GRPO run if SFT has a non-trivial build rate.

```bash
uv run training/train_grpo_cadforge.py \
  --model outputs/qwen35-2b-cadforge-sft \
  --output-dir outputs/qwen35-2b-cadforge-grpo \
  --hub-model-id sanjuhs/qwen35-2b-cadforge-grpo \
  --push-to-hub \
  --reward-backend cadforge \
  --cadforge-reward-mode fast \
  --limit-prompts 256 \
  --max-steps 100 \
  --num-generations 4 \
  --max-prompt-length 4096 \
  --max-completion-length 2048 \
  --learning-rate 5e-6 \
  --run-name qwen35-2b-grpo-cadforge-full
```

Full reward with renders should be used for periodic eval/reporting, not every GRPO step. Fast reward is the training signal; full reward is the judge-facing artifact generator.

## What To Report

For the initial report after smoke tests, capture:

- exact base model repo
- GPU name and VRAM
- SFT smoke loss logs
- GRPO smoke reward logs
- one CADForge reward JSON from `smoke_cadforge_reward.py`
- whether artifacts were written
- blocker list, if any

The hackathon result should compare:

- base Qwen prompt-only build rate
- SFT Qwen prompt-only build rate
- SFT Qwen repair reward delta
- GRPO Qwen reward delta
- GPT-5.4 teacher trace improvement as the upper-bound teacher demonstration
