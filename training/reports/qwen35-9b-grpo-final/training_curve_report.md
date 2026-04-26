# CADForge Training Curves

- Log: `training/logs/grpo-9b-from-sft-20260426.log`
- Parsed log metric rows: `41`
- TensorBoard scalar tags: `28`
- Train steps logged: `40`
- Eval points logged: `0`
- Train loss: `-0.0394` -> `0.0697`
- GRPO reward points: `40`
- GRPO mean/best reward: `0.4355` / `0.6828`
- GRPO trend slope: `0.000475` per step
- Completion debug rows: `160`
- Build rate from debug rows: `0.0%`
- Final fixture/import rates: `74.4%` / `100.0%`

## Charts

![sft_loss_curve](training/reports/qwen35-9b-grpo-final/sft_loss_curve.png)
![training_timeline](training/reports/qwen35-9b-grpo-final/training_timeline.png)
![optimizer_health](training/reports/qwen35-9b-grpo-final/optimizer_health.png)
![grpo_reward_curve](training/reports/qwen35-9b-grpo-final/grpo_reward_curve.png)
![grpo_code_health](training/reports/qwen35-9b-grpo-final/grpo_code_health.png)
![grpo_error_breakdown](training/reports/qwen35-9b-grpo-final/grpo_error_breakdown.png)

## Final Trainer Metrics

```json
{
  "train_runtime": 4532.0,
  "train_samples_per_second": 0.035,
  "train_steps_per_second": 0.009,
  "train_loss": 0.01599,
  "epoch": 4.0
}
```

## Recent Train Loss

| step | loss |
|---:|---:|
| 21 | 0.0041 |
| 22 | 0.0036 |
| 23 | -0.0061 |
| 24 | 0.0210 |
| 25 | 0.0466 |
| 26 | 0.0000 |
| 27 | 0.0181 |
| 28 | 0.0393 |
| 29 | 0.0404 |
| 30 | 0.0590 |
| 31 | 0.0000 |
| 32 | 0.0970 |
| 33 | -0.0047 |
| 34 | 0.0294 |
| 35 | 0.0880 |
| 36 | -0.0081 |
| 37 | 0.0401 |
| 38 | 0.0000 |
| 39 | 0.0000 |
| 40 | 0.0697 |

## GRPO Error Breakdown

| outcome | count |
|---|---:|
| `shaped_build_fail` | 58 |
| `SyntaxError` | 48 |
| `ValueError` | 19 |
| `NameError` | 12 |
| `TypeError` | 11 |
| `AttributeError` | 10 |
| `StdFail` | 1 |
| `BRep_API` | 1 |
