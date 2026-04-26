# CADForge Training Curves

- Log: `training/logs/grpo-9b-20260426-adaptive-repair-final-8192.log`
- Parsed log metric rows: `46`
- TensorBoard scalar tags: `28`
- Train steps logged: `45`
- Eval points logged: `0`
- Train loss: `0.0144` -> `-0.0425`
- GRPO reward points: `45`
- GRPO mean/best reward: `-0.2128` / `0.7366`
- GRPO trend slope: `-0.000669` per step
- Completion debug rows: `180`
- Build rate from debug rows: `29.4%`
- Final fixture/import rates: `97.2%` / `100.0%`

## Charts

![sft_loss_curve](training/reports/qwen35-9b-grpo-20260426-adaptive-repair-final-8192/sft_loss_curve.png)
![training_timeline](training/reports/qwen35-9b-grpo-20260426-adaptive-repair-final-8192/training_timeline.png)
![optimizer_health](training/reports/qwen35-9b-grpo-20260426-adaptive-repair-final-8192/optimizer_health.png)
![grpo_reward_curve](training/reports/qwen35-9b-grpo-20260426-adaptive-repair-final-8192/grpo_reward_curve.png)
![grpo_code_health](training/reports/qwen35-9b-grpo-20260426-adaptive-repair-final-8192/grpo_code_health.png)
![grpo_error_breakdown](training/reports/qwen35-9b-grpo-20260426-adaptive-repair-final-8192/grpo_error_breakdown.png)

## Final Trainer Metrics

```json
{
  "train_runtime": 4269.0,
  "train_samples_per_second": 0.042,
  "train_steps_per_second": 0.011,
  "train_loss": -0.004462,
  "epoch": 1.875
}
```

## Recent Train Loss

| step | loss |
|---:|---:|
| 26 | 0.0649 |
| 27 | 0.0120 |
| 28 | 0.0000 |
| 29 | 0.0395 |
| 30 | -0.1055 |
| 31 | 0.0580 |
| 32 | 0.0289 |
| 33 | -0.0186 |
| 34 | -0.0770 |
| 35 | -0.0182 |
| 36 | 0.0557 |
| 37 | 0.0222 |
| 38 | -0.0843 |
| 39 | 0.0414 |
| 40 | -0.1063 |
| 41 | 0.1229 |
| 42 | 0.0183 |
| 43 | -0.0280 |
| 44 | -0.0205 |
| 45 | -0.0425 |

## GRPO Error Breakdown

| outcome | count |
|---|---:|
| `build_ok` | 53 |
| `NameError` | 37 |
| `TypeError` | 21 |
| `ValueError` | 21 |
| `AttributeError` | 18 |
| `SyntaxError` | 12 |
| `BRep_API` | 9 |
| `unknown` | 8 |
| `StdFail` | 1 |
