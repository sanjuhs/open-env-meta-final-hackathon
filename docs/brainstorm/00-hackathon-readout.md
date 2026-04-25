# OpenEnv Hackathon Readout

Date: 2026-04-24

## What The Hackathon Wants

The winning submission should be an OpenEnv-compliant environment where an LLM acts step by step, receives programmatic feedback, and measurably improves through RL or RL-style training.

The most important judging weights are:

| Criterion | Weight | Practical meaning |
|---|---:|---|
| Environment innovation | 40% | Novel, challenging, meaningful agent behavior, not a clone of common games or toy tasks. |
| Storytelling | 30% | A judge should understand the world, the agent, what it learned, and why it matters in 3 to 5 minutes. |
| Showing improvement | 20% | Reward curves, before/after runs, baseline comparison, actual training evidence. |
| Reward/training pipeline | 10% | Coherent rubrics, TRL or Unsloth script, reproducible pipeline. |

Minimum gates:

- Use latest OpenEnv.
- Hosted Hugging Face Space.
- OpenEnv-compliant `reset`, `step`, `state`, typed models, `openenv.yaml`.
- Training script using Unsloth or HF TRL, ideally Colab.
- Evidence of real training, including reward/loss plots.
- README with problem, environment, actions, observations, tasks, setup, results.

## Strategic Lessons From The Docs

1. Pick a task where success can be verified programmatically.
2. Make the environment ambitious but keep the first curriculum levels easy enough for non-zero reward.
3. Use multiple reward signals, not one monolithic score.
4. Build the environment and verifier before training.
5. Show a before/after behavior difference, not only a training script.
6. Avoid a static benchmark. Adaptive curriculum and self-play read as much more ambitious.
7. The story matters almost as much as the engineering.

## Lessons From The Prior DocEdit Work

The old DocEdit environment passed because it was:

- Real-world, not a game.
- OpenEnv compliant.
- Lightweight enough for the constraints.
- Deterministically graded.
- Easy to explain.

The later Qwen SFT + GRPO postmortem proved that document repair can improve with training, but it also exposed a strategic limitation: full-document rewrite policies are probably not the best final design. A stronger next step is a planner/executor setup with structured edit actions and verifier feedback.

## Lessons From The Winning Kube SRE Example

The winning pattern was not just "Kubernetes environment." It was:

- A vivid professional world: a tiny model learns to be on-call.
- Real or realistic tools.
- Multi-step investigation and repair.
- Adaptive curriculum.
- Adversarial scenario generation.
- Multi-layer rewards.
- A story where the agent and environment co-evolve.

The key insight to borrow:

> The environment should fight back as the agent improves.

## Our Target Shape

To maximize win probability, the idea should combine:

- Theme 2: long-horizon planning, ideally up to 300 actions.
- Theme 3.1: professional world modeling with realistic tools and persistent state.
- Theme 4: self-improvement through adaptive scenario generation.
- Existing leverage from DocEdit so we can build fast.

The strongest direction is therefore not "another document editor." It is a long-horizon professional control room where document edits are one part of a larger verified workflow.

