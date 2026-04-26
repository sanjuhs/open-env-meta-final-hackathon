# CADForge Training Curves

- Log: `training/logs/sft-2b-full-20260425.log`
- Parsed log metric rows: `282`
- TensorBoard scalar tags: `13`
- Train steps logged: `270`
- Eval points logged: `11`
- Train loss: `1.4480` -> `0.1658`
- Eval loss: `0.4477` -> `0.2676`

## Charts

![sft_loss_curve](training/reports/qwen35-2b-sft-final/sft_loss_curve.png)
![training_timeline](training/reports/qwen35-2b-sft-final/training_timeline.png)
![optimizer_health](training/reports/qwen35-2b-sft-final/optimizer_health.png)

## Final Trainer Metrics

```json
{
  "train_runtime": 4096.0,
  "train_samples_per_second": 0.522,
  "train_steps_per_second": 0.066,
  "train_loss": 0.3193,
  "epoch": 3.0
}
```

## Recent Train Loss

| step | loss |
|---:|---:|
| 251 | 0.2312 |
| 252 | 0.2340 |
| 253 | 0.2281 |
| 254 | 0.2349 |
| 255 | 0.2310 |
| 256 | 0.2098 |
| 257 | 0.2374 |
| 258 | 0.2132 |
| 259 | 0.2488 |
| 260 | 0.1955 |
| 261 | 0.1910 |
| 262 | 0.2291 |
| 263 | 0.2155 |
| 264 | 0.2187 |
| 265 | 0.1954 |
| 266 | 0.1992 |
| 267 | 0.2087 |
| 268 | 0.2210 |
| 269 | 0.2383 |
| 270 | 0.1658 |

## Eval Loss

| step | eval_loss |
|---:|---:|
| 25 | 0.4477 |
| 50 | 0.3645 |
| 75 | 0.3268 |
| 100 | 0.3060 |
| 125 | 0.2900 |
| 150 | 0.2812 |
| 175 | 0.2739 |
| 200 | 0.2716 |
| 225 | 0.2688 |
| 250 | 0.2676 |
| 270 | 0.2676 |
