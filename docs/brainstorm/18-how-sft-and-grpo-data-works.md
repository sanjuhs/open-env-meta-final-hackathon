# How CADForge SFT and GRPO Data Works

## What The Agent Sees During A Trace

Each step is an observe -> edit -> score loop.

The observation includes:

1. The task prompt.
2. The previous CadQuery code.
3. The reward JSON from the verifier.
4. Verifier notes such as build errors, disconnected components, weak semantic hints, or missing reference similarity.
5. Optional rendered views for teacher traces when vision is enabled.

The action is always a complete replacement CadQuery file. The model is not asked to emit prose. It is asked to emit executable Python where the final object is assigned to `fixture`.

## Example SFT Row Shape

A training row looks like this:

```json
{
  "messages": [
    {
      "role": "system",
      "content": "You are CADForge, a careful CadQuery CAD repair agent... Return only a complete executable Python CadQuery file."
    },
    {
      "role": "user",
      "content": "Task: Build a simple four-legged chair...\n\nCurrent reward JSON: ...\n\nCurrent CadQuery code: ...\n\nRevise the code to improve the reward."
    },
    {
      "role": "assistant",
      "content": "import cadquery as cq\n\nseat_width = 420\n...\nfixture = chair.clean()"
    }
  ],
  "reward_before": 0.441,
  "reward_after": 0.802,
  "reward_delta": 0.361,
  "artifacts_dir": ".../step-1"
}
```

During SFT, Qwen learns the mapping:

```text
(previous code + verifier feedback + task) -> better complete CadQuery code
```

It does not learn from hidden GPT thinking. It learns from the repair action.

## Why We Do Not Want Long Thinking In The Output

Qwen 3.5 can overthink in Ollama and spend tokens on internal reasoning before answering. For CADForge this is bad because:

- the environment needs code, not a long explanation;
- excess thinking slows rollouts;
- verbose traces can pollute SFT if included as assistant output;
- invalid prose around code can break execution.

For Ollama inference use:

```json
{
  "think": false,
  "stream": false,
  "options": {
    "temperature": 0.2,
    "num_predict": 3000,
    "num_ctx": 8192
  }
}
```

And use a strict system prompt:

```text
Return only complete executable Python CadQuery code. No markdown. No explanation.
```

## Which Rows Go Into SFT

We generated several files:

- `cadquery_agentic_sft.jsonl`: all raw teacher steps, including regressions and failures.
- `cadquery_agentic_sft_positive.jsonl`: strict positives, `reward_after >= 0.70` and `reward_delta > 0`.
- `cadquery_agentic_sft_positive_060.jsonl`: recommended first SFT set, `reward_after >= 0.60` and `reward_delta > 0`.
- `cadquery_agentic_sft_delta_positive.jsonl`: every improving step, even if final reward is still modest.
- `cadquery_agentic_sft_train.jsonl` and `cadquery_agentic_sft_val.jsonl`: train/val split from the recommended set.

For the first overnight run, train on:

```text
experiment-2-cadforge/data/sft/cadquery_agentic_sft_train.jsonl
```

Use the validation set:

```text
experiment-2-cadforge/data/sft/cadquery_agentic_sft_val.jsonl
```

## What Preference/RLHF Data Means

Preference rows are chosen/rejected pairs for the same prompt.

If a teacher repair improves reward, the repair is chosen and the previous code is rejected. If it regresses, the previous code is chosen and the repair is rejected.

This supports DPO/RLHF-style training:

```text
same observation -> prefer higher-reward code over lower-reward code
```

## What RL/GRPO Data Means

RL rollout rows contain:

- observation
- action code
- reward after action
- reward delta
- done flag
- artifact paths

For GRPO, we should use live environment scoring, not only static rows. The static rollout rows are useful for debugging and offline analysis; the live verifier is what makes the RLVE environment real.

A practical step reward is:

```text
step_reward = 0.60 * reward_after
            + 0.35 * clamp(reward_after - reward_before, -0.25, 0.25)
            + 0.05 * build_success
```

Why this shape:

- absolute reward teaches final quality;
- reward delta teaches improvement;
- build success prevents invalid code from getting accidental credit.

## Is More Data Better?

More data helps if it is diverse. Blind duplication does not help much.

Our diversity knobs are:

- 24 object prompts;
- easy/medium/hard tasks;
- generated images and GLBs;
- five seed modes: weak, missing features, disconnected, bad dimensions, build error;
- teacher prompt variants: editability, silhouette/contact, build robustness;
- multiple repair steps per trace;
- reward filtering that keeps only improving SFT examples.

This gives the small model patterns like:

- repair undefined variables;
- replace fragile geometry with reliable Workplane operations;
- add missing semantic parts;
- reconnect floating components;
- improve proportions against a GLB reference;
- expose dimensions and helper functions for later edits.

## What To Expect After SFT

Before SFT, Qwen 2B/9B may:

- overthink;
- output prose;
- hallucinate CadQuery APIs;
- forget `fixture`;
- create disconnected blocky assemblies.

After SFT, success should first show up as:

- higher build rate;
- more `fixture = ...` completions;
- fewer fake APIs;
- more named dimensions/helper functions;
- better first-repair reward.

Do not expect perfect CAD from SFT alone. SFT makes the model trainable for GRPO. GRPO should then optimize reward and reduce revision count.

## Recommended Training Order

1. Baseline Qwen 2B and 9B on 5 held-out prompts.
2. SFT Qwen 2B on recommended positive rows.
3. SFT Qwen 9B on the same data.
4. Evaluate build rate, reward, and average steps-to-threshold.
5. Run GRPO with vLLM serve mode and live verifier rewards.
6. Compare before/after traces in the demo UI and markdown reports.
