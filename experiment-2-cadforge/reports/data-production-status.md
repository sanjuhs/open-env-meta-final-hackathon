# CADForge Data Production Status

## Reference Assets

- Task prompts: `24/24`
- GPT reference images: `24/24`
- FAL SAM 3D GLBs: `24/24`
- Preprocessed reward references: `24/24`

The FAL model used for GLB creation is `fal-ai/sam-3/3d-objects`. It works best with concise segmentation prompts such as `aluminum shelf bracket`, `metal object`, or `steel circular motor stator ring`, not full engineering design specs.

## Teacher Trace Data

- Raw repair SFT-format rows: `1240`
- Cold-start prompt-to-CadQuery rows: `25`
- Preference pairs: `1239`
- RL rollout rows: `1239`

## SFT Files

Repair/editing data:

- `data/sft/cadquery_agentic_sft.jsonl`: raw repair rows, `1240` rows.
- `data/sft/cadquery_agentic_sft_positive.jsonl`: strict positives, `436` rows.
- `data/sft/cadquery_agentic_sft_positive_060.jsonl`: recommended repair SFT, `704` rows.
- `data/sft/cadquery_agentic_sft_train.jsonl`: repair train split, `633` rows.
- `data/sft/cadquery_agentic_sft_val.jsonl`: repair validation split, `71` rows.

Cold-start generation data:

- `data/sft/cadquery_prompt_to_cadquery_sft.jsonl`: prompt -> complete CadQuery, `25` rows.
- `data/sft/cadquery_prompt_to_cadquery_train.jsonl`: train split, `20` rows.
- `data/sft/cadquery_prompt_to_cadquery_val.jsonl`: validation split, `5` rows.

Recommended first SFT mix:

- Use all `cadquery_prompt_to_cadquery_train.jsonl` rows.
- Use all `cadquery_agentic_sft_train.jsonl` rows.
- Optionally upsample cold-start rows 2-4x so the model learns prompt-to-CAD, not only repair.

Important clarification: upsampling does **not** mean removing or skipping cold-start rows. It means repeating the cold-start rows a few extra times in the mixed training file. Right now there are only `20` cold-start train rows but `633` repair train rows. If we mix each row once, the model mostly sees repair examples and may learn "fix this existing CAD code" better than "create complete CAD from a prompt." A 4x cold-start mix means the model sees the 20 prompt-to-CAD rows four times, or 80 cold-start training examples, alongside the 633 repair examples.

This gives the first SFT run both skills:

1. `prompt -> complete CadQuery code` for first drafts.
2. `prompt + previous code + reward JSON -> improved CadQuery code` for agentic repair.

For the first Qwen run, use 4x cold-start upsampling because cold-start is the behavior we need in the live demo before the repair loop starts.

## Token Estimates

- Raw repair SFT: `3.52M`
- Recommended repair SFT: `1.95M`
- Cold-start prompt-to-CAD: see `data/token_estimate.json`
- Preference data: `4.16M`
- RL rollout data: `3.33M`

## Readiness

The dataset now supports both modes:

1. `prompt -> complete CadQuery code` for first drafts.
2. `prompt + previous code + reward JSON -> improved CadQuery code` for agentic repair.

This is ready for Qwen 2B/9B SFT warm-start training.
