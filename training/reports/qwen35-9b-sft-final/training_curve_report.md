# CADForge Training Curves

- Log: `training/logs/sft-9b-full-20260426.log`
- Parsed log metric rows: `189`
- TensorBoard scalar tags: `13`
- Train steps logged: `180`
- Eval points logged: `8`
- Train loss: `2.6020` -> `0.1413`
- Eval loss: `0.3650` -> `0.2398`

## Charts

![sft_loss_curve](training/reports/qwen35-9b-sft-final/sft_loss_curve.png)
![training_timeline](training/reports/qwen35-9b-sft-final/training_timeline.png)
![optimizer_health](training/reports/qwen35-9b-sft-final/optimizer_health.png)

## Final Trainer Metrics

```json
{
  "train_runtime": 4019.0,
  "train_samples_per_second": 0.355,
  "train_steps_per_second": 0.045,
  "train_loss": 0.3343,
  "epoch": 2.0
}
```

## Recent Train Loss

| step | loss |
|---:|---:|
| 161 | 0.2270 |
| 162 | 0.2305 |
| 163 | 0.2198 |
| 164 | 0.2362 |
| 165 | 0.2067 |
| 166 | 0.2393 |
| 167 | 0.2180 |
| 168 | 0.2173 |
| 169 | 0.2152 |
| 170 | 0.2017 |
| 171 | 0.2097 |
| 172 | 0.2209 |
| 173 | 0.2394 |
| 174 | 0.2141 |
| 175 | 0.2174 |
| 176 | 0.2327 |
| 177 | 0.2072 |
| 178 | 0.2089 |
| 179 | 0.2125 |
| 180 | 0.1413 |

## Eval Loss

| step | eval_loss |
|---:|---:|
| 25 | 0.3650 |
| 50 | 0.2951 |
| 75 | 0.2690 |
| 100 | 0.2544 |
| 125 | 0.2455 |
| 150 | 0.2409 |
| 175 | 0.2398 |
| 180 | 0.2398 |
