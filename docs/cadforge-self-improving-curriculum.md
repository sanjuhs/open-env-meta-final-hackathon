# CADForge Self-Improving Curriculum

## Thesis

CADForge is self-improving when the environment uses model failures to automatically create the next training distribution.

The key idea:

> Every failed CAD rollout becomes a labeled repair task. The environment does not only score the model; it diagnoses why the CAD failed, generates a targeted correction scenario, and samples more tasks from the failure modes the model has not mastered yet.

This makes Theme 4 stronger than "we changed the reward by hand." The environment can adapt on its own.

## Failure Taxonomy

CADForge already observes structured failure signals:

| Failure | Detection | New Curriculum Task |
|---|---|---|
| SyntaxError | Python parser / CadQuery runner stderr | close parentheses, finish final union, emit valid Python |
| missing fixture | no `fixture/result/model/solid/body/part` | assign final exportable object |
| invented API | AttributeError on CadQuery object | replace unsupported operation with boxes/cylinders/cuts/unions |
| NameError | undefined dimension/helper | define named dimensions before use |
| TypeError / ValueError | bad CadQuery call signature | simplify operation and preserve shape intent |
| disconnected parts | topology/contact reward | connect floating body with rails, ribs, overlaps, or bridge geometry |
| weak semantics | semantic hints score | add missing recognizable subassemblies |
| weak editability | editability score | introduce named dimensions and helper functions |
| poor reference similarity | GLB/reference metrics | adjust bbox, silhouette, and major part proportions |

## Automatic Loop

```text
rollout batch
  -> CADForge reward JSON
  -> failure classifier
  -> targeted repair task generator
  -> adaptive sampler
  -> SFT / GRPO next batch
```

## Scenario Generation

For each failed completion, CADForge can write a new repair row:

```json
{
  "task_id": "four_leg_chair_700n",
  "failure_type": "clipped_final_union",
  "previous_code": "...",
  "reward_json": {
    "total": -1.0,
    "build": 0.0,
    "editability": 0.0
  },
  "verifier_notes": [
    "CadQuery code did not execute or did not export an STL.",
    "Build error: SyntaxError: '(' was never closed"
  ],
  "repair_instruction": "Return a complete executable CadQuery file. Preserve the chair structure, close the final union, and assign fixture."
}
```

The next model action is scored by reward delta:

```text
delta_reward = new_total_reward - previous_total_reward
```

This rewards actual repair, not just a high one-shot score.

## Adaptive Sampling

The curriculum controller tracks mastery by failure type:

```text
mastery[failure_type] = recent_successful_repairs / recent_attempted_repairs
```

Sampling weight:

```text
weight = base_weight * (1.0 - mastery)^2 * difficulty_multiplier
```

So if the model keeps failing `SyntaxError` and `missing_fixture`, those categories are sampled more often. Once they are solved, the environment shifts toward harder semantic/reference tasks.

## Difficulty Ladder

1. **Syntax survival**: code parses, imports allowed modules, assigns `fixture`.
2. **Build survival**: CadQuery exports STL.
3. **Connectivity**: no floating parts or large gaps.
4. **Task semantics**: required parts appear in code and geometry.
5. **Editability**: named dimensions, helper functions, clean final fixture.
6. **Reference similarity**: match GLB/ideal-CAD bbox, silhouette, and major proportions.
7. **Long-horizon repair**: improve reward across multiple edits with persistent state.

## Why This Is Self-Improvement

The environment creates harder and more targeted tasks from the agent's own failures. No human has to manually author every repair case.

The final strict GRPO run already shows the first step:

- first dense reward was too forgiving
- strict build gating made failures negative
- logs exposed the next failure distribution: SyntaxError, TypeError, ValueError, NameError, AttributeError
- these failure counts define the next curriculum automatically

The next implementation step is to add a `curriculum_state.json` file with per-failure mastery and a script:

```bash
uv run training/generate_repair_curriculum.py \
  --debug-jsonl training/logs/grpo-9b-strict-build-20260426-strict-build-completions.jsonl \
  --output training/output/cadforge_adaptive_repair_curriculum.jsonl
```

That turns CADForge from a scorer into an adaptive teacher.

