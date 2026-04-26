---
title: CADForge CadQuery
emoji: 🪑
colorFrom: green
colorTo: blue
sdk: docker
pinned: false
app_port: 8000
base_path: /web
tags:
  - openenv
  - cadquery
  - reinforcement-learning
---

# CADForge Experiment 2

CADForge is an OpenEnv environment for training LLMs to produce **editable, buildable CadQuery CAD**.

The agent receives a design request, writes a complete CadQuery Python file, and the environment runs real CAD tooling: CadQuery build, STL export, topology checks, semantic scoring, reference similarity, editability scoring, and persistent artifact logging.

## Notebook

- **Open notebook in Hugging Face:** [training/cadforge_openenv_training_colab.ipynb](https://huggingface.co/spaces/sanjuhs/cadforge-cadquery-openenv/blob/main/training/cadforge_openenv_training_colab.ipynb)
- **Open notebook in Google Colab:** [CADForge OpenEnv training notebook](https://colab.research.google.com/github/sanjuhs/open-env-meta-final-hackathon/blob/main/training/cadforge_openenv_training_colab.ipynb)

**RunPod/H200 clarification:** the full 2B/9B SFT and GRPO runs were executed on RunPod H200 as distinct production scripts. The Colab notebook is the judge-runnable smoke path that validates OpenEnv, the public dataset, the CadQuery reward backend, and tiny SFT/GRPO launches using those same scripts.

## Judge-Facing Links

- **GitHub repo:** [sanjuhs/open-env-meta-final-hackathon](https://github.com/sanjuhs/open-env-meta-final-hackathon)
- **GitHub Gist: training scripts:** [CADForge OpenEnv SFT/GRPO scripts](https://gist.github.com/sanjuhs/10596f688e8b4560910a3b1b137bfeeb)
- **Raw training logs and evidence:** [sanjuhs/cadforge-training-evidence](https://huggingface.co/datasets/sanjuhs/cadforge-training-evidence)
- Training notebook on this HF Space: [training/cadforge_openenv_training_colab.ipynb](https://huggingface.co/spaces/sanjuhs/cadforge-cadquery-openenv/blob/main/training/cadforge_openenv_training_colab.ipynb)
- Open the same notebook in Google Colab: [Colab training notebook](https://colab.research.google.com/github/sanjuhs/open-env-meta-final-hackathon/blob/main/training/cadforge_openenv_training_colab.ipynb)
- Mini-blog: [CADFORGE_BLOG.md](CADFORGE_BLOG.md)
- Detailed technical blog: [docs/detailed-blog/cadforge-detailed-blog.md](docs/detailed-blog/cadforge-detailed-blog.md)
- Full project report: [docs/cadforge-openenv-project-report.md](docs/cadforge-openenv-project-report.md)
- Self-improving RLVE design: [docs/brainstorm/21-cadforge-self-improving-rlve.md](docs/brainstorm/21-cadforge-self-improving-rlve.md)
- Strict GRPO training report: [training/reports/qwen35-9b-grpo-strict-build-20260426-strict-build/training_curve_report.md](https://huggingface.co/spaces/sanjuhs/cadforge-cadquery-openenv/blob/main/training/reports/qwen35-9b-grpo-strict-build-20260426-strict-build/training_curve_report.md)
- Strict GRPO eval report: [training/eval/qwen35-9b-cadforge-grpo-strict-build-20260426-strict-build/eval_report.md](training/eval/qwen35-9b-cadforge-grpo-strict-build-20260426-strict-build/eval_report.md)
- Inference comparison: [inference/results/stator-qwen-vs-frontier/report.md](https://huggingface.co/spaces/sanjuhs/cadforge-cadquery-openenv/blob/main/inference/results/stator-qwen-vs-frontier/report.md)
- Training dataset: [sanjuhs/cadforge-cadquery-agentic-traces](https://huggingface.co/datasets/sanjuhs/cadforge-cadquery-agentic-traces)
- Training logs and evidence bundle: [sanjuhs/cadforge-training-evidence](https://huggingface.co/datasets/sanjuhs/cadforge-training-evidence)
- Strict 9B GRPO LoRA: [sanjuhs/qwen35-9b-cadforge-grpo-strict-build-lora](https://huggingface.co/sanjuhs/qwen35-9b-cadforge-grpo-strict-build-lora)
- Adaptive repair GRPO LoRA: [sanjuhs/qwen35-9b-cadforge-grpo-adaptive-repair-lora](https://huggingface.co/sanjuhs/qwen35-9b-cadforge-grpo-adaptive-repair-lora)

## Results Snapshot

| Run | Result |
|---|---|
| Qwen3.5-2B SFT | train loss `1.4480 -> 0.1658`, eval loss `0.4477 -> 0.2676` |
| Qwen3.5-2B dense GRPO | mean reward `0.3387`, best `0.5303`; useful reward signal but too forgiving on broken builds |
| Qwen3.5-9B SFT | train loss `2.6020 -> 0.1413`, eval loss `0.3650 -> 0.2398` |
| Qwen3.5-9B strict GRPO | `320` completions, `96` buildable, best CADForge score `0.9352` |
| Qwen3.5-9B adaptive repair GRPO | `180` repair completions, `53` buildable, `0` clipped completions |
| Strict 9B quick eval | `2/3` held-out prompts built successfully |
| Stator inference comparison | base Qwen failed build; RL-tuned Qwen built a `0.654` stator; GPT-5.4 built a `0.709` stator |

![Strict GRPO reward curve](https://huggingface.co/spaces/sanjuhs/cadforge-cadquery-openenv/resolve/main/training/reports/qwen35-9b-grpo-strict-build-20260426-strict-build/grpo_reward_curve.png)

![Strict GRPO code health](https://huggingface.co/spaces/sanjuhs/cadforge-cadquery-openenv/resolve/main/training/reports/qwen35-9b-grpo-strict-build-20260426-strict-build/grpo_code_health.png)

![Base Qwen vs RL-tuned Qwen vs GPT-5.4 stator comparison](https://huggingface.co/spaces/sanjuhs/cadforge-cadquery-openenv/resolve/main/inference/results/stator-qwen-vs-frontier/comparison.png)

## Training Logs

The raw logs are backed up separately so judges can inspect the training evidence without relying on screenshots:

- Evidence dataset: [sanjuhs/cadforge-training-evidence](https://huggingface.co/datasets/sanjuhs/cadforge-training-evidence)
- Compressed archive: `archives/cadforge-training-evidence-20260426.tar.gz`
- Key JSONL traces: `training/logs/*completions.jsonl`

The logs show the core result: dense GRPO had positive-looking reward but `0%` buildability; strict build-gating produced `96/320` buildable completions; adaptive repair fixed clipped outputs and produced `53/180` buildable repairs.

## Hackathon Theme Alignment

- **Theme 2: Long-horizon planning**: CAD improves through repeated code edits and reward feedback.
- **Theme 3.1: Professional world modeling**: the agent must use real CadQuery tools and survive compiler/export/mesh checks.
- **Theme 4: Self-improvement**: environment failures become new curriculum. The strict build-gated reward was created because the first dense reward was too forgiving.
- **Theme 5: Wild Card**: editable CAD generation is a practical, underexplored RLVE target.

## The Environment Fights Back

The first dense GRPO reward gave useful shape feedback, but it still rewarded some non-buildable CAD. CADForge responded by tightening the rules:

1. Buildability became the first gate.
2. failed CadQuery code receives negative reward.
3. syntax errors, missing `fixture`, undefined variables, and invented APIs are tracked separately.
4. successful builds unlock dense rewards for topology, semantics, reference similarity, contact, editability, and efficiency.

This produced useful GRPO variance: buildable CAD separated from pretty-but-broken code.

---

Legacy prototype notes follow.

Local prototype for a multi-step CADForge environment: prompt -> CSG/CAD actions -> geometry validation -> structural household part scoring.

Experiment 1 focuses on prompt-to-mechanical-design plus coarse 3D FEA. Experiment 2 keeps that renderer/verifier base, but reframes the loop around reliable code-CAD behavior:

- the agent plans small CAD operations,
- the trace is treated like an AST/feature-tree construction episode,
- the verifier reports CADForge metrics such as AST nodes, connected components, watertight/manifold proxy, editability proxy, and pseudo-OpenSCAD output,
- structural MechForge feedback remains as the first physical reward suite.

## Why This Exists

LLMs can often describe a chair, hook, or bracket, but they are unreliable at making CAD that builds, edits, exports, and stays physically coherent. CADForge turns those failure modes into reward:

- no floating parts,
- connected CSG/feature tree,
- watertight/manifold exported geometry,
- clean editable parameters,
- manufacturable features,
- structural safety under load.

The long-term target is an OpenEnv-compatible RLVE environment where an agent can take 100-300 CAD actions before committing a valid part.

## OpenEnv Space

This directory is now a deployable OpenEnv environment named `cadforge_cadquery`.
The action is a complete CadQuery Python file. The environment runs it through a constrained CadQuery runner, exports STL, scores build/topology/contact/task semantics/reference similarity/editability, and returns reward JSON plus verifier notes.

Local validation:

```bash
../.venv/bin/openenv validate .
PYTHONPATH=python_tools ../.venv/bin/uvicorn server.app:app --host 0.0.0.0 --port 8000
OPENENV_BASE_URL=http://localhost:8000 ../.venv/bin/python inference.py
```

Push to Hugging Face Spaces:

```bash
set -a; source ../.env; set +a
../.venv/bin/openenv push . --repo-id sanjuhs/cadforge-cadquery-openenv --interface
```

## Setup

```bash
cp .env.example .env
# Either paste your OpenAI key into this .env, or keep it in the repo-root .env.
npm install
npm run dev
```

Open:

```text
http://localhost:5177
```

The API listens on:

```text
http://localhost:8791
```

## What To Try

Chair benchmark:

```text
Build a simple four-legged chair as editable code-CAD. It must support a 700 N seated load, include a seat panel, four connected legs, lower crossbars, and a backrest, fit inside a 500 mm x 500 mm x 900 mm envelope, and avoid floating parts.
```

Truss benchmark:

```text
Build a simple lightweight truss support as code-CAD. Use connected triangular load paths, two fixed mounting holes on the left, a load boss on the right, and enough ribs/cross-members to carry a 250 N downward load with safety factor above 2.0.
```

Wall hook benchmark:

```text
Build a wall-mounted J hook as code-CAD. It needs two screw holes, one connected curved hook arm, a rounded tip lip, and support ribs at the root. It must carry a 120 N hanging load and avoid floating or disconnected geometry.
```

## OpenSCAD Rendering

The UI includes an OpenSCAD code panel with:

- `Generate SCAD`
- `Iterate SCAD`
- `Render SCAD`
- `Load Example`

This is a real browser-side CSG renderer for a constrained OpenSCAD subset. It currently supports:

- `cube`
- `sphere`
- `cylinder`
- `translate`
- `rotate`
- `scale`
- `union`
- `difference`
- `intersection`

The renderer parses SCAD text and builds an actual Three.js mesh. Boolean operations use `three-csg-ts`.

Full OpenSCAD CLI rendering is not enabled yet because `openscad` is not installed on this machine. The UI and README should not claim full OpenSCAD compatibility until that real dependency is available.

The server endpoints are:

```text
POST /api/scad-generate
POST /api/scad-iterate
```

Both use the configured model API key. They do not return fallback or mock SCAD when the key is missing.

## Current CADForge Metrics

The current prototype adds a `cadforge` block to each analysis result:

- `ast_nodes`
- `connected_components`
- `floating_parts`
- `watertight_proxy`
- `manifold_proxy`
- `clean_feature_tree_proxy`
- `named_parameter_count`
- `editability_score`
- `chair_core_features_passed`
- `pseudo_openscad`

These are MVP proxies, not a full OpenSCAD/trimesh compile yet. The next step is to replace the analysis proxies with:

```text
CSG AST -> OpenSCAD/CadQuery -> STL/STEP -> trimesh/solid validation -> reward
```

## OpenEnv Direction

The final environment should expose actions such as:

- `add_cube`
- `add_cylinder`
- `translate`
- `rotate`
- `union`
- `difference`
- `add_mount_hole`
- `add_rib`
- `compile_cad`
- `check_connected_components`
- `check_watertight`
- `check_editability`
- `run_structural_check`
- `commit_design`

This gives judges the story they want:

> The agent improves on a long-horizon world-modeling task where every CAD operation changes the physical world, and rewards come from objective geometric and structural checks.

## Python Solver

This copy still includes the MechForge Python solver under `python_tools/mechforge`. Prefer the repo-level Python 3.12 virtual environment:

```bash
UV_CACHE_DIR=.uv-cache uv venv --python python3.12 .venv
UV_CACHE_DIR=.uv-cache uv pip install numpy scipy pydantic fastapi uvicorn meshio gmsh scikit-fem cadquery openmdao openenv-core openai trimesh
```

Headless smoke test:

```bash
PYTHONPATH=experiment-2-cadforge/python_tools .venv/bin/python -m mechforge.cli sample
```
