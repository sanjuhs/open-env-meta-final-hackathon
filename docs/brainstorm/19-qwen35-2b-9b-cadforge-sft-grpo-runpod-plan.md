# Qwen3.5 2B/9B CADForge SFT + GRPO Plan

## Recommendation

Use `Qwen/Qwen3.5-2B` for the fast hackathon loop and `Qwen/Qwen3.5-9B` for the serious "we can win this" run.

Default plan:

1. Train `Qwen/Qwen3.5-2B` with LoRA SFT to prove the environment/data loop works.
2. Evaluate base vs SFT on held-out CADForge tasks.
3. Train `Qwen/Qwen3.5-9B` with LoRA SFT on the same data.
4. Run GRPO from the stronger SFT adapter, using CADForge as the reward environment.
5. Report both: 2B as the tiny-model story, 9B as the strongest small open model result.

If H200 budget is available, do not waste time optimizing around 24 GB constraints. Use Unsloth BF16 LoRA for both SFT runs, keep QLoRA only as a last-resort fallback, and test FP8 mainly for GRPO/rollout throughput once the BF16 SFT baseline is working.

## LoRA vs QLoRA vs PEFT

`PEFT` is the umbrella library/pattern: parameter-efficient fine-tuning. It includes LoRA, QLoRA-style quantized LoRA, prefix tuning, adapters, etc.

`LoRA` means the base model stays frozen and we train small low-rank matrices inserted into attention/MLP layers. It is the best default when we have enough VRAM.

`QLoRA` means the base model is loaded in 4-bit quantized form while training LoRA adapters. It saves VRAM, but can be slower, more finicky, and slightly less clean when memory is not the bottleneck.

For CADForge:

- Use `LoRA BF16` on H200/H100/A100/L40S, preferably with Unsloth for Qwen3.5.
- Use `FP8 LoRA/GRPO` as an optimization after the BF16 baseline, especially for RL where rollout inference dominates runtime.
- Use `QLoRA` only if nothing else fits. Unsloth's Qwen3.5 guide specifically says 4-bit QLoRA is not recommended for Qwen3.5 because quantization differences are higher than normal.
- Do not full fine-tune first. Full fine-tune is overkill for 1.7M-2.0M SFT tokens and increases risk of overfitting/catastrophic drift.
- Consider full fine-tune later only if we have much more data, a stable eval suite, and the LoRA result is clearly adapter-limited.

Suggested adapter settings:

| Model | Method | Rank | Alpha | Target Modules | Notes |
|---|---:|---:|---:|---|---|
| Qwen3.5-2B | Unsloth BF16 LoRA | 16-32 | 32-64 | attention + MLP projections | Fast proof run |
| Qwen3.5-9B | Unsloth BF16 LoRA | 32-64 | 64-128 | attention + MLP projections | Main result |
| GRPO optimization | Unsloth FP8 LoRA/GRPO | 32-64 | 64-128 | attention + MLP projections | Test after BF16 SFT |
| Emergency low-VRAM fallback | QLoRA | 16-32 | 32-64 | attention + MLP projections | Avoid for Qwen3.5 unless forced |

## BF16 vs FP8 vs Ollama Q8

These are easy to mix up:

- `BF16` is the stable training dtype for our SFT baseline. On H200 it is the right first choice.
- `FP8` is a GPU precision/quantized-weight training and inference path. Unsloth supports FP8 RL/GRPO with `load_in_fp8=True`; their docs report faster RL inference and much lower VRAM. This is worth testing for CADForge GRPO after the normal BF16 SFT result exists.
- `Q8_0` / `q8` in Ollama or GGUF is an inference quantization format, not the same thing as FP8 training. A model served as Q8 in Ollama does not mean we should train in FP8.
- Export path should be: train BF16 LoRA -> evaluate -> optionally merge -> export GGUF `q8_0` or `q4_k_m` for llama.cpp/Ollama-style demos.

Practical choice:

1. Train SFT in BF16 LoRA with Unsloth.
2. Evaluate base vs SFT.
3. Run GRPO first in the simplest working Unsloth setup.
4. If GRPO rollout generation is the bottleneck, enable FP8 with `load_in_fp8=True` and compare reward/build-rate against BF16.

Do not switch the whole plan to FP8 before we have a BF16 control run. FP8 may be faster, especially in RL, but the hackathon needs a clean ablation: base -> SFT BF16 -> GRPO BF16/FP8.

## Hardware

Since H200 spend is okay:

- `1x H200 141GB`: best single-GPU choice for SFT + GRPO. Use this if available.
- `1x H100 80GB`: good fallback for GRPO.
- `1x L40S 48GB`: fine for SFT and eval, less ideal for GRPO throughput.
- `1x RTX 4090 24GB`: only for cheap SFT experiments with QLoRA.

For `Qwen/Qwen3.5-2B`:

- SFT LoRA: H200 is more than enough; this should be quick.
- GRPO: possible on H200, but 2B may be too weak unless SFT build-rate improves clearly.

For `Qwen/Qwen3.5-9B`:

- SFT LoRA: H200 Unsloth BF16 LoRA, sequence length 8192-16384 depending on trace length. Unsloth lists Qwen3.5-9B BF16 LoRA around 22GB VRAM before our batch/context choices.
- GRPO: H200 preferred because we can keep policy, reference, optimizer state, and rollout engine comfortable. Test FP8 GRPO if rollout throughput or memory becomes the bottleneck.
- If using vLLM colocated, start conservative: 4 completions per prompt, then push to 8 if memory/throughput is stable.

## Current Data

Local current snapshot:

- Raw SFT: 1240 rows, about 3.52M tokens.
- Relaxed positive SFT: 704 rows, about 1.95M tokens.
- Train split: 633 rows, about 1.76M tokens.
- Val split: 71 rows, about 0.19M tokens.
- Preferences: 1239 rows, about 4.16M tokens.
- RL rollouts: 1239 rows, about 3.33M tokens.
- Prompt-to-CadQuery direct set: 25 high-quality task-to-code rows.

Use this order:

1. SFT on `cadquery_agentic_sft_train.jsonl`.
2. Mix in `cadquery_prompt_to_cadquery_train.jsonl` at a small weight or oversample it 2-4x so the model can also do first-shot CAD, not only repair.
3. Evaluate on `cadquery_agentic_sft_val.jsonl` plus held-out task prompts.
4. Use preferences later for DPO/ORPO only if GRPO is too slow.
5. Use `cadquery_rollouts.jsonl` to seed GRPO prompts and replay evals.

## Thinking Traces

CAD is logical and step-by-step, so thinking can help at inference time. But we should not train on hidden chain-of-thought.

Important distinction:

- OpenAI hidden reasoning is not in our data. We only have the final visible model output.
- The SFT JSONL maps observation/reward/current-code context to improved CadQuery code.
- The trace JSON files contain `raw_model_output`, but for OpenAI traces this is visible output we asked for, usually complete code, not protected internal reasoning.
- A scan of the current local data found zero `<think>` / `</think>` blocks.

For training:

- Do not fabricate long chain-of-thought.
- Do not train the model to emit `<think>` blocks before code.
- Train it to produce clean final CadQuery code only.
- If we want structured reasoning, make it explicit and safe: short public planning comments inside the code or a separate non-submitted planning field for experiments, not hidden CoT imitation.

For inference/eval:

- For 2B, start non-thinking mode for SFT evaluation because the target output is only code and extra thinking tokens can leak into invalid Python.
- Also run a small A/B: thinking enabled vs disabled, then strip `<think>...</think>` before passing code to CADForge. If thinking improves build/reward, mention it as an inference-time scaffold, not SFT data.
- For 9B, thinking mode is worth testing more seriously. CAD repair benefits from multi-step reasoning, but the final action must still be clean code.
- Best demo agent: "think privately or in scratch, then submit only code to CADForge." The environment should never score thinking text; it scores executable code.

Qwen notes from official cards:

- `Qwen/Qwen3.5-2B` supports thinking and non-thinking; the model card says 2B operates in non-thinking mode by default and can be served with vLLM/SGLang.
- `Qwen/Qwen3.5-9B` is Apache-2.0, compatible with Transformers/vLLM/SGLang/KTransformers, and Qwen recommends vLLM/SGLang for throughput.
- Older `Qwen3-8B` docs explicitly describe `enable_thinking=True/False` and `<think>...</think>` parsing; the same care applies when testing Qwen thinking-mode models.

## SFT Plan

2B:

```text
model: Qwen/Qwen3.5-2B
method: Unsloth BF16 LoRA
rank: 16 or 32
seq_len: 8192 first, 16384 if examples need it
epochs: 2-4
lr: 1e-4 to 2e-4
batching: maximize tokens/sec; use grad accumulation rather than tiny context
eval: every 25-50 steps
```

9B:

```text
model: Qwen/Qwen3.5-9B
method: Unsloth BF16 LoRA on H200
rank: 32 or 64
seq_len: 8192-16384
epochs: 2-3
lr: 5e-5 to 1.5e-4
eval: held-out build rate and reward, not just loss
```

What to watch:

- Validation loss is secondary.
- Build rate is the first key metric.
- Mean reward and reward >= 0.70 / >= 0.85 rates are the real metrics.
- Inspect failures for Python syntax, CadQuery API hallucination, missing `fixture`, disconnected parts, and semantic misses.

## GRPO Plan

Run GRPO only after SFT has non-trivial build rate.

For 2B:

- Use as a proof of learning if SFT already reaches reasonable build rate.
- 4 completions per prompt, short rollouts, fast reward mode.
- Stop quickly if all completions fail to build.

For 9B:

- Main GRPO candidate.
- Start from SFT adapter.
- 4-8 completions per prompt.
- CADForge fast reward during training.
- Start BF16 for the clean baseline; then test Unsloth FP8 GRPO with `load_in_fp8=True` if rollout speed or VRAM is limiting.
- Periodically run full reward for report artifacts.
- Keep anti-hacking constraints: final object must be `fixture`, blocked tokens rejected, build hard-gated, semantic hints required.

Reward objective:

```text
step_reward = 0.60 * reward_after
            + 0.35 * clamp(reward_after - reward_before, -0.25, 0.25)
            + 0.05 * build_success
```

## Inference After Training

Quick eval:

- Load base model + LoRA adapter with Transformers/PEFT.
- Generate code from held-out observations.
- Strip markdown fences and any accidental `<think>` block.
- Submit code to the OpenEnv Space `/step`.

Serving:

- vLLM with LoRA adapter if Qwen3.5 adapter support is stable.
- Otherwise merge LoRA into a HF checkpoint and serve the merged model.
- For Ollama/llama.cpp demos, merge and convert to GGUF after training. Use `q8_0` for quality-first local demos, `q4_k_m` for portable demos. This is inference quantization, separate from BF16/FP8 training.

Demo loop:

```bash
OPENENV_BASE_URL=https://sanjuhs-cadforge-cadquery-openenv.hf.space \
  python experiment-2-cadforge/inference.py
```

## Final Report Story

Mirror `docs/best-example-project.md`:

1. Cold Qwen cannot reliably produce buildable CadQuery.
2. CADForge executes real CadQuery, exports STL, renders, and scores every step.
3. GPT teacher traces generate repair trajectories.
4. SFT teaches the small model the code-CAD grammar and repair style.
5. GRPO teaches verifier-directed improvement against objective geometry rewards.
6. 2B proves the tiny-model story; 9B gives the strongest open small-model result.
