# Rapid Build Plan For The Recommended Idea

## Goal

Build a convincing OpenEnv submission around **Regulatory Dossier Control Room** with long-horizon tasks, adaptive curriculum, objective rewards, and visible training improvement.

## First 45 Minutes

Decision checkpoint:

- Commit to Regulatory Dossier Control Room unless a better idea beats it on build speed and judge impact.
- Define the MVP around 5 scenario families and 3 difficulty levels.
- Keep the first implementation deterministic and lightweight.

Immediate choices:

- Python 3.12 + uv.
- OpenEnv latest release.
- FastAPI server.
- Simple HTML/JS or Gradio demo if time allows.
- Store generated dossier as in-memory structured files, with optional JSON fixtures.

## Build Architecture

```text
regulatory_dossier_control_room/
  openenv.yaml
  pyproject.toml
  README.md
  inference.py
  train_grpo.py
  server/
    app.py
    environment.py
    models.py
    scenario_generator.py
    dossier.py
    tools.py
    validators.py
    rewards.py
    curriculum.py
  assets/
    reward_curve.png
    baseline_vs_trained.png
```

## Core Environment

State:

- Task seed.
- Difficulty.
- Dossier files.
- Hidden canonical facts.
- Hidden affected file graph.
- Current file/window.
- Search history.
- Edit history.
- Validator history.
- Step count.
- Score components.

Actions:

- `search`
- `open_file`
- `inspect_window`
- `replace_text`
- `patch_section`
- `add_audit_note`
- `run_validator`
- `commit_episode`

Observations:

- Task brief.
- Current file/window.
- Search or validator output.
- Last reward breakdown.
- Known discovered facts.
- Remaining steps.

## Scenario Families

1. Dosage update:
   - Change max dose across label, patient leaflet, CSR, investigator brochure.
2. Contraindication update:
   - Add/remove safety contraindications across medical and patient documents.
3. Clinical endpoint correction:
   - Correct endpoint wording and tables across CSR, abstract, briefing doc.
4. Manufacturing site change:
   - Update site names, IDs, certificates, cover letter, audit trail.
5. Patient-language simplification:
   - Convert technical warnings to patient-facing plain language without changing meaning.

## Difficulty Tiers

| Tier | Files | Hidden obligations | Max steps | Use |
|---|---:|---:|---:|---|
| Easy | 2 to 4 | 3 to 8 | 30 | Fast learning signal. |
| Medium | 8 to 15 | 12 to 30 | 100 | Main training target. |
| Hard | 20 to 60 | 40 to 150 | 300 | Headline long-horizon demo. |

## Training Evidence Plan

Minimum viable evidence:

- Run baseline over 20 seeds.
- Run short GRPO or SFT+GRPO over easy/medium curriculum.
- Save reward curve.
- Evaluate base vs trained on 20 held-out seeds.

Metrics:

- Mean episode reward.
- Final dossier score.
- Fact accuracy.
- Cross-document consistency.
- Affected file coverage.
- Collateral damage.
- Validator warnings remaining.
- Steps to completion.

## Demo Output

README should include:

- One-paragraph pitch.
- Why long-horizon dossier management matters.
- Action/observation space.
- Reward breakdown.
- Curriculum/self-improvement loop.
- Baseline vs trained table.
- Reward plot.
- One trace excerpt showing better behavior after training.

Video or mini-blog story:

1. "A safety change arrives 12 hours before submission."
2. Baseline fixes only the obvious label line.
3. Validator reveals missed patient leaflet and CSR table.
4. Training reward improves.
5. Trained agent searches, patches, validates, audits, and commits.

## What To Avoid

- Do not market this as "DocEdit V3." That undersells it.
- Do not start with full 300-step training. Build 30-step and 100-step curricula first.
- Do not rely on an LLM judge as the only reward.
- Do not make the UI the main project. The environment and training evidence are the submission.
- Do not overfit to static hand-authored tasks. Procedural seeds matter.

## Final Recommendation

Start implementation with a narrow MVP:

- Dosage update family only.
- 6 documents.
- 3 difficulty settings.
- Hidden consistency graph.
- Search/open/replace/validate/audit/commit tools.

Once this works, add the other scenario families and the adversarial curriculum.

