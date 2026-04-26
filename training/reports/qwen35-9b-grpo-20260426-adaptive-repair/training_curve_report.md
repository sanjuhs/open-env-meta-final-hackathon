# CADForge Training Curves

- Log: `training/logs/grpo-9b-20260426-adaptive-repair.log`
- Parsed log metric rows: `31`
- TensorBoard scalar tags: `28`
- Train steps logged: `30`
- Eval points logged: `0`
- Train loss: `0.0000` -> `0.0000`
- GRPO reward points: `30`
- GRPO mean/best reward: `-0.8302` / `-0.8025`
- GRPO trend slope: `-0.000382` per step
- Completion debug rows: `120`
- Build rate from debug rows: `0.0%`
- Final fixture/import rates: `0.8%` / `96.7%`

## Charts

![sft_loss_curve](training/reports/qwen35-9b-grpo-20260426-adaptive-repair/sft_loss_curve.png)
![training_timeline](training/reports/qwen35-9b-grpo-20260426-adaptive-repair/training_timeline.png)
![optimizer_health](training/reports/qwen35-9b-grpo-20260426-adaptive-repair/optimizer_health.png)
![grpo_reward_curve](training/reports/qwen35-9b-grpo-20260426-adaptive-repair/grpo_reward_curve.png)
![grpo_code_health](training/reports/qwen35-9b-grpo-20260426-adaptive-repair/grpo_code_health.png)
![grpo_error_breakdown](training/reports/qwen35-9b-grpo-20260426-adaptive-repair/grpo_error_breakdown.png)

## Final Trainer Metrics

```json
{
  "train_runtime": 2895.0,
  "train_samples_per_second": 0.041,
  "train_steps_per_second": 0.01,
  "train_loss": 7.153e-08,
  "epoch": 2.5
}
```

## Recent Train Loss

| step | loss |
|---:|---:|
| 11 | 0.0000 |
| 12 | 0.0000 |
| 13 | 0.0000 |
| 14 | 0.0000 |
| 15 | 0.0000 |
| 16 | 0.0000 |
| 17 | 0.0000 |
| 18 | 0.0000 |
| 19 | -0.0000 |
| 20 | 0.0000 |
| 21 | 0.0000 |
| 22 | 0.0000 |
| 23 | 0.0000 |
| 24 | 0.0000 |
| 25 | -0.0000 |
| 26 | 0.0000 |
| 27 | 0.0000 |
| 28 | 0.0000 |
| 29 | 0.0000 |
| 30 | 0.0000 |

## GRPO Error Breakdown

| outcome | count |
|---|---:|
| `SyntaxError` | 95 |
| `ValueError` | 15 |
| `NameError` | 6 |
| `TypeError` | 4 |
