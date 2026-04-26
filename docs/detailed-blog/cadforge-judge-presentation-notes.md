# CADForge Judge Presentation Notes

This file is internal presentation guidance. Do not include it in the public blog copy.

## Demo Story

The story should be shown in four beats:

1. **Frontier models struggle.** Show the Markus chair screenshots. Even huge models produce floating, disconnected, or brittle CAD.
2. **CADForge turns failure into reward.** Show the environment loop and reward table.
3. **SFT teaches syntax; GRPO teaches buildability.** Show SFT loss curves and strict GRPO reward/code-health graphs.
4. **The environment self-improves.** Show the adaptive curriculum loop: failed rollouts become the next training rows.

For non-technical audiences, the line is:

> We built a CAD teacher. It compiles the student's design, tells it exactly how it failed, and creates the next lesson from that failure.

For technical audiences, the line is:

> CADForge is a build-gated RLVE for executable CadQuery, with reward dimensions for topology, contact, semantic parts, reference similarity, editability, and adaptive curriculum mining from real compiler/geometry failures.

## Judging Criteria Mapping

### Environment Innovation: 40%

CADForge is novel because it is not just another text-to-3D generator. It is a real tool-using CAD environment:

- executable CadQuery code as the action;
- real compiler/export feedback;
- persistent artifacts;
- semantic and editability reward;
- GLB reference similarity;
- adaptive failure mining.

The challenge is genuinely hard because the model must satisfy syntax, API correctness, geometry, task semantics, and code structure at the same time.

### Storytelling and Presentation: 30%

The story is easy to follow:

1. even frontier models struggle with complex CAD;
2. a verifier catches what humans see immediately: floating parts, bad proportions, broken code;
3. SFT teaches the model to speak CadQuery;
4. GRPO teaches it that buildable CAD is better than broken text;
5. the environment mines failures to create the next curriculum.

### Showing Improvement in Rewards: 20%

The reward evidence is concrete:

- SFT loss falls for both 2B and 9B;
- dense GRPO exposed reward design flaws;
- strict GRPO produced 30% buildable completions and best score 0.9352;
- held-out eval built 2 of 3 objects;
- adaptive curriculum mining identified the next bottleneck: syntax closure on long repairs.

### Reward and Training Pipeline: 10%

The pipeline is coherent:

- prompt-to-CAD and repair SFT rows teach format;
- strict build-gated GRPO executes every candidate;
- reward JSON separates build, topology, semantics, reference similarity, and editability;
- failed trajectories are converted into targeted repair tasks;
- GLB reference generation gives a scalable route to more tasks.

## Visual Evidence Checklist

The blog already has:

- four frontier-model Markus chair screenshots;
- SFT loss curves for 2B and 9B;
- dense GRPO reward curves for 2B and 9B;
- strict GRPO reward, code-health, and error-breakdown graphs;
- Mermaid diagrams for the environment loop, adaptive curriculum, and GLB-reference loop.

The strongest missing visuals are:

| Priority | Visual | Why it helps |
|---|---|---|
| Must have | strict GRPO generated stator render | proves the trained model produces buildable CAD, not just better metrics |
| Must have | strict GRPO generated caster fork render | gives a second concrete success case and matches held-out eval |
| Must have | failed chair render or clipped-code screenshot from held-out eval | makes the remaining limitation honest and explains the next curriculum target |
| Must have | before/after comparison: base or SFT output vs strict GRPO output on the same prompt | shows model improvement visually, not only numerically |
| Should have | one reward JSON screenshot for a successful build | proves the environment returns structured verifier feedback |
| Should have | one traceback/failure-class screenshot for a failed build | shows how failures become repair data |
| Should have | Hugging Face Space or demo UI screenshot showing prompt, render, reward, and repair feedback | makes the tool feel real and interactive |
| Should have | sample generated CadQuery snippet beside its rendered STL | reinforces that the output is editable code-CAD, not a mesh-only asset |
| Should have | base Qwen vs RL-tuned Qwen vs GPT-5.4 stator comparison | shows the trained small model moving from build failure to frontier-comparable buildable CAD |
| Nice to have | GLB reference beside generated CadQuery render | explains reference-similarity rewards and the scalable data loop |
| Nice to have | compact bar chart comparing build rates: dense GRPO 0% vs strict GRPO 30% vs held-out 2/3 | turns the main result into a single glance |
| Nice to have | adaptive curriculum failure-class bar chart from the 180 repair rows | shows that the environment discovers what to train next |
| Nice to have | slide-style summary of both self-improvement loops | helps non-technical judges remember the system |

If time is short, prioritize these five:

1. strict GRPO stator render;
2. strict GRPO caster render;
3. base Qwen vs RL-tuned Qwen vs GPT-5.4 stator comparison;
4. reward JSON or UI screenshot;
5. build-rate comparison chart.

## Locally Rendered Assets

Generated assets live in `docs/detailed-blog/rendered-assets/`.

| Asset | File |
|---|---|
| strict GRPO stator render | `rendered-assets/strict-grpo-stator-render.png` |
| strict GRPO caster render | `rendered-assets/strict-grpo-caster-render.png` |
| held-out chair clipped-code failure | `rendered-assets/failed-chair-clipped-code.png` |
| weak seed vs strict GRPO caster comparison | `rendered-assets/before-after-caster-weak-vs-strict-grpo.png` |
| successful reward JSON screenshot | `rendered-assets/successful-build-reward-json.png` |
| failed-build traceback/failure-class screenshot | `rendered-assets/failed-build-traceback-json.png` |
| CadQuery snippet beside rendered STL | `rendered-assets/cadquery-code-beside-render.png` |
| GLB reference silhouette beside CadQuery render | `rendered-assets/glb-reference-vs-cadquery-render.png` |
| build-rate comparison chart | `rendered-assets/build-rate-comparison.png` |
| adaptive curriculum failure-class chart | `rendered-assets/adaptive-curriculum-failure-classes.png` |
| self-improvement loop summary | `rendered-assets/self-improvement-loop-summary.png` |
| local demo UI screenshot | `rendered-assets/hugging-face-space-repair-loop-ui.png` |
| base Qwen vs RL-tuned Qwen vs GPT-5.4 comparison | `../../inference/results/stator-qwen-vs-frontier/comparison.png` |

## Adaptive Repair Clarification

The adaptive repair run starts from the strict build-gated GRPO adapter, not from the original SFT checkpoint. That is the important two-stage story:

1. strict GRPO teaches buildability;
2. adaptive repair specializes that build-aware model on mined failure classes.

Regenerate the static pack with:

```bash
.venv/bin/python scripts/experiment-2/make-judge-visual-assets.py
```
