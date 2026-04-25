# CADForge Experiment 2

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

