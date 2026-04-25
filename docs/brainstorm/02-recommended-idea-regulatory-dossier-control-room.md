# Recommended Idea: Regulatory Dossier Control Room

## Short Pitch

**Regulatory Dossier Control Room** is an OpenEnv environment where an LLM acts as a regulatory operations agent during a simulated pharma submission crisis.

The agent receives a high-level change request, such as a dosage update, safety warning, manufacturing site change, or adverse-event correction. The change is scattered across a dossier of many interlinked documents: drug label, clinical study report, investigator brochure, patient leaflet, quality summary, cover letter, amendment log, and internal review notes.

The agent has up to 300 tool steps to inspect, search, edit, validate, and audit the dossier. Rewards come from objective checks against a hidden consistency graph and regulatory rules.

## Why Judges Should Care

Real regulatory work is long-horizon, high-stakes, and brutally detail-sensitive. A single inconsistent dosage, date, or contraindication across documents can delay a submission.

Current LLMs are good at explaining documents, but they struggle with:

- Tracking facts across many files.
- Applying the same change consistently.
- Avoiding collateral damage.
- Remembering decisions over long sessions.
- Recovering from early mistakes.
- Knowing when to validate and when to stop.

This environment trains exactly that behavior.

## Theme Fit

Primary theme:

- Theme 2: Super long-horizon planning and instruction following.

Secondary themes:

- Theme 3.1: Professional task world modeling.
- Theme 4: Self-improvement through adaptive curricula.
- Theme 5: Wild card, because it turns document editing into a realistic compliance control room.

## The 300-Step Task

Hard episodes have:

- 20 to 60 dossier files.
- 40 to 150 hidden obligations.
- 100 to 300 possible action steps.
- Cross-document dependencies.
- Red herrings and stale memo fragments.
- Validation reports that reveal partial but not complete truth.

Example hard prompt:

> A late safety update changes the maximum daily dose from 40 mg to 30 mg for renal impairment patients, adds a contraindication for severe hepatic impairment, removes an outdated trial endpoint from Study RX-204, and requires all patient-facing materials to use plain-language wording. Update the dossier, preserve unrelated content, and leave an audit trail.

The agent must discover that this affects:

- Drug label dosage section.
- Contraindications section.
- Patient leaflet.
- Clinical study report summary table.
- Investigator brochure safety section.
- Cover letter.
- Amendment log.
- Cross-reference table.
- Internal review checklist.

## Action Space

Potential actions:

```json
{"tool": "search", "query": "renal impairment 40 mg"}
{"tool": "open_file", "path": "label/section_4_2_dosage.xml"}
{"tool": "inspect_window", "path": "csr/rx_204_summary.xml", "start": 120, "length": 40}
{"tool": "replace_text", "path": "label/section_4_2_dosage.xml", "target": "40 mg", "replacement": "30 mg"}
{"tool": "patch_section", "path": "patient_leaflet.xml", "section_id": "dose_warning", "content": "..."}
{"tool": "add_audit_note", "document": "amendment_log.xml", "note": "..."}
{"tool": "run_validator", "validator": "dose_consistency"}
{"tool": "commit_episode"}
```

Optional later actions:

```json
{"tool": "assign_subtask", "agent": "safety_reviewer", "objective": "..."}
{"tool": "resolve_conflict", "fact": "max_daily_dose", "value": "30 mg", "evidence": ["..."]}
```

## Observation Space

The agent sees:

- Current task brief.
- Current file/window content.
- Search results.
- Known facts discovered so far.
- Validation warnings.
- Edit history.
- Remaining step budget.
- Reward components from the last action.

The agent does not see:

- The full hidden canonical answer.
- All affected files upfront.
- The complete dependency graph.

## Reward Design

Use multiple independent reward components:

| Reward component | Purpose |
|---|---|
| Fact correction reward | Correctly updates canonical facts like dosage, dates, safety claims, study endpoints. |
| Cross-document consistency reward | Same fact is consistent across all required files. |
| Coverage reward | Agent discovers and touches all impacted nodes in the hidden dependency graph. |
| Collateral damage penalty | Penalize changing unrelated text or breaking valid facts. |
| Audit reward | Correctly records what changed and why. |
| Validation reward | Reward using validators and resolving their warnings. |
| Efficiency reward | Encourage completion before 300 steps. |
| Anti-hacking penalty | Penalize invalid paths, repeated no-ops, format-breaking edits, or validator spam. |

Suggested total:

```text
reward =
  delta_fact_score
  + delta_consistency_score
  + 0.2 * delta_coverage
  + 0.1 * audit_score_delta
  + validator_resolution_bonus
  - collateral_damage_penalty
  - repeat_action_penalty
  - invalid_action_penalty
```

Final success score:

```text
final_score =
  0.35 * fact_accuracy
  + 0.25 * cross_doc_consistency
  + 0.15 * affected_file_coverage
  + 0.10 * audit_quality
  + 0.10 * structural_validity
  + 0.05 * efficiency
  - collateral_damage
```

## Self-Improvement Loop

The environment includes an **Adversarial Compliance Designer**.

It tracks the agent's weaknesses:

- Misses patient-facing documents.
- Fixes label but forgets clinical study report tables.
- Over-edits unrelated sections.
- Fails to write audit notes.
- Repeats search actions.
- Stops before running validators.

Then it generates harder future episodes:

- More files.
- More cross-references.
- More red herrings.
- More subtle wording differences.
- Compound changes.
- Longer dependency chains.

Curriculum levels:

| Level | Episode shape | Expected horizon |
|---|---|---:|
| 1 | One file, one fact | 5 to 15 steps |
| 2 | Three files, one fact | 15 to 35 steps |
| 3 | Ten files, two facts | 35 to 80 steps |
| 4 | Twenty files, compound update | 80 to 160 steps |
| 5 | Full dossier crisis with red herrings | 160 to 300 steps |

This gives us non-zero reward early, then a path to the 300-step headline.

## What We Train

Start with a small instruct model and train it to:

- Search before editing.
- Build a working memory of discovered facts.
- Use validators.
- Apply narrow patches instead of broad rewrites.
- Maintain consistency across files.
- Stop only after validation passes.

Training recipe:

1. Baseline inference with frontier or small model.
2. Optional light SFT on synthetic tool traces from an oracle policy.
3. GRPO or RLVR using the verifier reward.
4. Compare base vs trained on held-out dossier seeds.

## Demo Story

The demo can be extremely clear:

1. Show the crisis brief.
2. Show a baseline model making local edits but missing cross-document consequences.
3. Show the validator catching unresolved inconsistencies.
4. Show reward curve improving during training.
5. Show trained agent: search, patch, validate, audit, commit.
6. Show final score breakdown and affected-file map.

Tagline:

> From "edit this paragraph" to "manage a 300-step regulatory crisis."

## Why This Can Win

It has the same strengths as Kube SRE Gym without copying it:

- Professional task.
- Tool-based world.
- Multi-step investigation.
- Adaptive curriculum.
- Agent learns from verifier feedback.
- Strong before/after story.

But it is more directly aligned with the user's existing assets:

- Existing DocEdit document generation.
- Existing structured edit actions.
- Existing similarity/collateral grading idea.
- Existing proof that small-model training can improve document repair.

## MVP Scope

Minimum credible hackathon version:

- 8 to 12 document templates.
- 5 scenario families.
- 3 difficulty tiers.
- 8 to 10 tools.
- Hidden consistency graph.
- Programmatic validators.
- OpenEnv server.
- Baseline inference.
- TRL/Unsloth training script.
- Reward plots from at least one short training run.
- README plus 2-minute pitch video or mini-blog.

Scenario families:

1. Dosage update.
2. Contraindication update.
3. Clinical endpoint correction.
4. Manufacturing site change.
5. Patient-language simplification.

## Risk And Mitigation

| Risk | Mitigation |
|---|---|
| 300-step tasks are too hard for training | Use curriculum. Train on 5 to 80 steps first, show hard eval as stretch. |
| Reward is too complex | Keep hidden graph simple: facts, required files, forbidden changes. |
| Judges think it is just DocEdit V2 | Pitch it as dossier-level world modeling, not local editing. |
| Training takes too long | Train a tiny model or run short GRPO over easy/medium levels and show upward reward. |
| LLM outputs invalid JSON | Constrain action schema and give format rewards/penalties. |

## Decision

This is the idea I would pick.

It is ambitious enough to impress, grounded enough to build, and close enough to existing work that we have a realistic path to shipping evidence rather than just slides.

