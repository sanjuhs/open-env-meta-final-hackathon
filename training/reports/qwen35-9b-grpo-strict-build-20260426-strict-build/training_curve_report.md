# CADForge Training Curves

- Log: `training/logs/grpo-9b-strict-build-20260426-strict-build.log`
- Parsed log metric rows: `81`
- TensorBoard scalar tags: `28`
- Train steps logged: `80`
- Eval points logged: `0`
- Train loss: `-0.0394` -> `-0.0649`
- GRPO reward points: `80`
- GRPO mean/best reward: `-0.2616` / `0.4533`
- GRPO trend slope: `0.003549` per step
- Completion debug rows: `320`
- Build rate from debug rows: `30.0%`
- Final fixture/import rates: `72.5%` / `99.7%`

## Charts

![sft_loss_curve](training/reports/qwen35-9b-grpo-strict-build-20260426-strict-build/sft_loss_curve.png)
![training_timeline](training/reports/qwen35-9b-grpo-strict-build-20260426-strict-build/training_timeline.png)
![optimizer_health](training/reports/qwen35-9b-grpo-strict-build-20260426-strict-build/optimizer_health.png)
![grpo_reward_curve](training/reports/qwen35-9b-grpo-strict-build-20260426-strict-build/grpo_reward_curve.png)
![grpo_code_health](training/reports/qwen35-9b-grpo-strict-build-20260426-strict-build/grpo_code_health.png)
![grpo_error_breakdown](training/reports/qwen35-9b-grpo-strict-build-20260426-strict-build/grpo_error_breakdown.png)

## Final Trainer Metrics

```json
{
  "train_runtime": 9112.0,
  "train_samples_per_second": 0.035,
  "train_steps_per_second": 0.009,
  "train_loss": 0.02709,
  "epoch": 8.0
}
```

## Recent Train Loss

| step | loss |
|---:|---:|
| 61 | 0.0083 |
| 62 | 0.0341 |
| 63 | 0.0703 |
| 64 | 0.0000 |
| 65 | 0.1354 |
| 66 | -0.0281 |
| 67 | 0.0320 |
| 68 | -0.0335 |
| 69 | 0.0253 |
| 70 | 0.0686 |
| 71 | 0.0550 |
| 72 | 0.0400 |
| 73 | -0.0062 |
| 74 | 0.0030 |
| 75 | 0.0276 |
| 76 | 0.1387 |
| 77 | 0.0939 |
| 78 | -0.0663 |
| 79 | 0.0535 |
| 80 | -0.0649 |

## GRPO Error Breakdown

| outcome | count |
|---|---:|
| `SyntaxError` | 109 |
| `build_ok` | 96 |
| `TypeError` | 25 |
| `ValueError` | 24 |
| `NameError` | 24 |
| `AttributeError` | 21 |
| `unknown` | 15 |
| `BRep_API` | 5 |
| `StdFail` | 1 |
