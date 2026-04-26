# CADForge Inference Comparison

Task: `axial_motor_stator_12_slot`

Design a simple 12-slot axial motor stator concept. It should visibly look like a circular stator ring with radial teeth and a center shaft opening. Use steel and keep the structure compact.

![Model comparison](comparison.png)

## Summary

| Model | Source | Total | Build | Semantic | Reference | Editability | Local artifacts |
|---|---|---:|---:|---:|---:|---:|---|
| Base Qwen | saved local Ollama base-Qwen output | -1.000 | 0.0 | 0.000 | 0.000 | 0.000 | `base-qwen` |
| RL-tuned Qwen | strict build-gated GRPO held-out stator artifact | 0.654 | 1.0 | 0.300 | 0.067 | 0.825 | `rl-tuned-qwen` |
| GPT-5.4 | saved GPT-5.4 artifact `/Users/sanju/Desktop/coding/python/open-env-meta-final/experiment-2-cadforge/runs/cadquery-env/openai-gpt-5.4-axial_motor_stator_12_slot-disconnected-2026-04-25T14-06-43-357Z/step-2/candidate.py` | 0.709 | 1.0 | 0.638 | 0.078 | 0.825 | `gpt-5-4` |

## Interpretation

This is a single-task qualitative comparison, not a leaderboard. The useful signal is that the RL-tuned Qwen adapter produces a buildable, editable stator on the same medium-difficulty part family where a frontier model also succeeds.

The base Qwen row is generated locally through Ollama when `--baseline-source ollama` is used. The fine-tuned Qwen row defaults to the saved strict-GRPO held-out stator artifact, because the local laptop does not include the full HF/PEFT stack and merged model weights. The script can still run a live HF/PEFT model on a GPU machine by replacing the code source or extending the candidate generator.

The honest claim is: CADForge does not prove small Qwen beats frontier models yet. It proves that a small model can become competitive on buildable code-CAD behavior when trained inside a strict executable CAD reward environment, and that longer training plus broader reference tasks is the right next scaling path.

## Reproduce

```bash
.venv/bin/python inference/compare_cadquery_models.py --baseline-source ollama
```
