# CADForge Training Curves

- Log: `training/logs/grpo-2b-from-sft-20260425.log`
- Parsed log metric rows: `41`
- TensorBoard scalar tags: `28`
- Train steps logged: `40`
- Eval points logged: `0`
- Train loss: `0.0123` -> `0.0000`
- GRPO reward points: `40`
- GRPO mean/best reward: `0.3387` / `0.5303`
- GRPO trend slope: `0.000887` per step
- Completion debug rows: `160`
- Build rate from debug rows: `0.0%`
- Final fixture/import rates: `73.8%` / `100.0%`

## Charts

![sft_loss_curve](training/reports/qwen35-2b-grpo-final/sft_loss_curve.png)
![training_timeline](training/reports/qwen35-2b-grpo-final/training_timeline.png)
![optimizer_health](training/reports/qwen35-2b-grpo-final/optimizer_health.png)
![grpo_reward_curve](training/reports/qwen35-2b-grpo-final/grpo_reward_curve.png)
![grpo_code_health](training/reports/qwen35-2b-grpo-final/grpo_code_health.png)
![grpo_error_breakdown](training/reports/qwen35-2b-grpo-final/grpo_error_breakdown.png)

## Final Trainer Metrics

```json
{
  "train_runtime": 3694.0,
  "train_samples_per_second": 0.043,
  "train_steps_per_second": 0.011,
  "train_loss": -0.0004301,
  "epoch": 4.0
}
```

## Recent Train Loss

| step | loss |
|---:|---:|
| 21 | 0.0078 |
| 22 | 0.0000 |
| 23 | 0.0000 |
| 24 | 0.0000 |
| 25 | 0.0000 |
| 26 | 0.0000 |
| 27 | -0.1891 |
| 28 | 0.0413 |
| 29 | 0.0000 |
| 30 | -0.0014 |
| 31 | -0.0189 |
| 32 | -0.0567 |
| 33 | 0.0049 |
| 34 | 0.1492 |
| 35 | 0.0723 |
| 36 | -0.3844 |
| 37 | -0.0182 |
| 38 | 0.0230 |
| 39 | 0.0587 |
| 40 | 0.0000 |

## GRPO Error Breakdown

| outcome | count |
|---|---:|
| `SyntaxError` | 63 |
| `shaped_build_fail` | 28 |
| `NameError` | 23 |
| `AttributeError` | 17 |
| `ValueError` | 16 |
| `TypeError` | 11 |
| `BRep_API` | 1 |
| `StdFail` | 1 |
