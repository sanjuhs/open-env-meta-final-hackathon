# MechForge Experiment

Small local experiment for checking whether a GPT model can produce useful constrained mechanical designs.

The app asks the model for a structured parametric design, renders it in Three.js, and runs a real finite-element solve over a coarse 3D tetrahedral mesh. This is not commercial-grade meshing, but it does assemble stiffness matrices, apply boundary conditions and forces, solve displacements, and compute von Mises stress/strain per tetrahedral element.

## Why Three.js Instead Of OpenSCAD First?

- Three.js gives immediate browser rendering and interaction.
- The model output is structured JSON, so we can later convert the same design to CadQuery, OpenSCAD, STEP, STL, or a real FEA backend.
- OpenSCAD is good for deterministic script-based CAD, but it is slower and less ergonomic for live browser iteration.
- CadQuery is probably the better CAD backend for the future OpenEnv version because it is Python-native and can export real geometry.

## Setup

```bash
cp .env.example .env
# Either paste your OpenAI key into this .env, or keep it in the repo-root .env.
npm install
npm run dev
```

Open the Vite URL, usually:

```text
http://localhost:5176
```

The default model is `gpt-5.4`; change `MODEL_NAME` in `.env` if your account uses a different GPT-5 model ID. The API key variable is `OPENAI_API_KEY`.

## Python Solver Install

The local Python environment is intentionally inside this experiment folder:

```bash
uv venv --python /Users/sanju/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 .venv
uv pip install numpy scipy pydantic fastapi uvicorn meshio gmsh scikit-fem cadquery openmdao openenv-core openai
uv pip install -e .
```

Installed simulation/CAD packages:

- `numpy` and `scipy` for matrix assembly and sparse/numeric solving.
- `pydantic` for strict tool/design schemas.
- `gmsh`, `meshio`, and `scikit-fem` as the next-step meshing/FEA stack.
- `cadquery` for production-grade parametric CAD and STEP/STL export.
- `openmdao` for multidisciplinary optimization loops.
- `openenv-core` for hackathon-compatible environment serving and validation.

The current fast verifier is `python_tools/mechforge/solver3d.py`: a real coarse 3D tetrahedral linear-elasticity solver. It applies fixed boundary conditions, distributes load to nearby 3D nodes, solves displacement, then reports von Mises stress, strain, deflection, safety factor, mass, hotspots, and score. Thermal is still a proxy, not a full heat-transfer solve.

Headless solver smoke test:

```bash
PYTHONPATH=python_tools .venv/bin/python -m mechforge.cli sample
```

## OpenEnv

This folder is also an OpenEnv environment:

```bash
.venv/bin/openenv validate --verbose
PYTHONPATH=python_tools ENABLE_WEB_INTERFACE=false .venv/bin/python -m server.app --port 8001
.venv/bin/openenv validate --url http://127.0.0.1:8001 --timeout 20
OPENENV_BASE_URL=http://127.0.0.1:8001 .venv/bin/python inference.py
```

The OpenEnv tool/action surface is:

- `create_design_family`
- `set_material`
- `set_envelope`
- `set_load`
- `add_mount_hole`
- `add_rib`
- `add_lightening_hole`
- `run_fea`
- `commit_design`

This is the long-horizon path: an agent can take hundreds of small tool actions, run FEA after candidate changes, observe stress/deflection/mass/reward, and continue optimizing until it commits.

## Trace Semantics

There are currently two traces:

- Browser demo trace: one GPT structured-design call, then one Python 3D FEA tool call per iteration. The UI groups that as a visible `tool run`, because the frontend is showing the iteration-level event.
- OpenEnv trace: each individual action is one environment tool call. For example, `add_rib` and `run_fea` are separate calls, each returning an observation/reward. This is the version to use for 300+ step agentic optimization and RL-style evaluation.

The browser's `Run Tool Episode` button shows the second style directly: separate `create_design_family`, `set_material`, `set_envelope`, `add_rib`, `set_load`, `run_fea`, and `commit_design` calls.

## Benchmarking

The UI has a **Run 5.4 Iterations** button. It runs GPT-5.4 through iterative generate -> simulate -> improve loops, then renders the best design.

You can also run:

```bash
curl -sS -X POST http://localhost:8790/api/benchmark \
  -H 'Content-Type: application/json' \
  -d '{"prompt":"Design a lightweight 6061 aluminum cantilever bracket fixed by two M5 bolts on the left and carrying 120 N downward at a tip 90 mm from the fixed edge. Keep mass below 45 g while maintaining safety factor above 2.0.","models":["gpt-5.4"],"iterations":3}'
```

If a model is not available to the key, that model returns a per-model error while the other models still run.

## What To Try

Example prompt:

```text
Design a lightweight 6061 aluminum cantilever bracket. It is fixed by two M5 bolts on the left side and must carry 120 N downward at the tip 90 mm from the fixed edge. Keep mass below 45 g and safety factor above 2.0.
```

## Current Limitations

- The verifier is real coarse 3D linear tetrahedral FEA, with a 2D frame fallback if the solid solve fails.
- Stress, strain, deformation, and force direction come from the 3D solve when available.
- Thermal rise is still a first-pass proxy, not thermal FEA.
- Geometry is parametric and renderable, not yet robust arbitrary CAD.
- STL export is available from the rendered mesh, but STEP export needs a CAD backend like CadQuery or OpenSCAD.
