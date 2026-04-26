# CADForge Inference Comparisons

This folder contains local inference/evaluation scripts for comparing generated CadQuery outputs.

The main benchmark is:

```bash
.venv/bin/python inference/compare_cadquery_models.py --baseline-source ollama
```

It compares three candidates on the same `axial_motor_stator_12_slot` task:

- **Base Qwen**: generated live through local Ollama, default `qwen3.5:9b`.
- **RL-tuned Qwen**: saved strict build-gated GRPO held-out stator artifact.
- **GPT-5.4**: saved frontier baseline artifact by default, or live OpenAI generation with `--gpt-source openai` and `OPENAI_API_KEY`.

Outputs are written under `inference/results/<run-id>/`:

- `report.md`
- `comparison.png`
- `results.json`
- per-model `candidate.py`, `reward.json`, STL files, and render images

Important: the default run is a reproducible local comparison using one live base-Qwen generation plus saved trained/frontier artifacts. It is not a broad benchmark. The right claim is that CADForge makes a small Qwen model competitive on buildable, editable code-CAD behavior for a medium-difficulty part family, not that it beats frontier models globally.

## Current Stator Result

Latest local run:

- Report: [results/stator-qwen-vs-frontier/report.md](results/stator-qwen-vs-frontier/report.md)
- Comparison image: [results/stator-qwen-vs-frontier/comparison.png](results/stator-qwen-vs-frontier/comparison.png)

| Model | Total | Build | Semantic | Editability |
|---|---:|---:|---:|---:|
| Base Qwen | -1.000 | 0.0 | 0.000 | 0.000 |
| RL-tuned Qwen | 0.654 | 1.0 | 0.300 | 0.825 |
| GPT-5.4 | 0.709 | 1.0 | 0.638 | 0.825 |

![Base Qwen vs RL-tuned Qwen vs GPT-5.4](results/stator-qwen-vs-frontier/comparison.png)
