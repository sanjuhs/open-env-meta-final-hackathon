# CADForge Training Curves

- Log: `training/logs/grpo-9b-smoke.log`
- Parsed log metric rows: `3`
- TensorBoard scalar tags: `28`
- Train steps logged: `2`
- Eval points logged: `0`
- Train loss: `0.0000` -> `0.0000`
- GRPO reward points: `2`
- GRPO mean/best reward: `0.2350` / `0.2500`
- GRPO trend slope: `-0.030000` per step
- Completion debug rows: `4`
- Build rate from debug rows: `0.0%`
- Final fixture/import rates: `25.0%` / `100.0%`

## Charts

![sft_loss_curve](training/reports/qwen35-9b-grpo-smoke/sft_loss_curve.png)
![training_timeline](training/reports/qwen35-9b-grpo-smoke/training_timeline.png)
![optimizer_health](training/reports/qwen35-9b-grpo-smoke/optimizer_health.png)
![grpo_reward_curve](training/reports/qwen35-9b-grpo-smoke/grpo_reward_curve.png)
![grpo_code_health](training/reports/qwen35-9b-grpo-smoke/grpo_code_health.png)
![grpo_error_breakdown](training/reports/qwen35-9b-grpo-smoke/grpo_error_breakdown.png)

## Final Trainer Metrics

```json
{
  "train_runtime": 205.9,
  "train_samples_per_second": 0.019,
  "train_steps_per_second": 0.01,
  "train_loss": 0.0,
  "epoch": 0.5
}
```

## Recent Train Loss

| step | loss |
|---:|---:|
| 1 | 0.0000 |
| 2 | 0.0000 |

## GRPO Error Breakdown

| outcome | count |
|---|---:|
| `SyntaxError` | 2 |
| `ValueError` | 1 |
| `NameError` | 1 |
