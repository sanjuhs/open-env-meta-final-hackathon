# Python Simulation Plan

## Current Installed Python Options

System Python:

- Path: `/Library/Frameworks/Python.framework/Versions/3.14/bin/python3`
- Version: 3.14.3
- Heavy simulation libraries currently missing.

Bundled workspace Python:

- Path: `/Users/sanju/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3`
- Version: 3.12.13
- Installed now: `numpy`, `pydantic`
- Missing now: `scipy`, `fastapi`, `uvicorn`, `meshio`, `gmsh`, `skfem`, `cadquery`

## What I Built Without New Installs

The folder `python_tools/mechforge/` now contains:

- `models.py`: design, feature, material, and tool-action schemas.
- `load_manager.py`: natural-language load inference and region defaults.
- `mesh.py`: coarse structured tetrahedral mesh generation from the parametric part.
- `solver3d.py`: real 3D linear tetrahedral elasticity using NumPy.
- `tools.py`: agent-style design actions and simulator calls.
- `cli.py`: headless CLI for sample simulation, direct simulation, and action traces.

## Headless Commands

Use bundled Python:

```bash
cd experiment-mechanical-idea
PYTHONPATH=python_tools /Users/sanju/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -m mechforge.cli sample
```

Run an action trace:

```bash
cat <<'JSON' | PYTHONPATH=python_tools /Users/sanju/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -m mechforge.cli run-actions
{
  "prompt": "Design a 6061 aluminum cantilever bracket with 120 N downward load at the tip.",
  "actions": [
    {"tool": "create_design_family", "params": {"family": "ribbed_cantilever_bracket"}},
    {"tool": "set_envelope", "params": {"length_mm": 105, "width_mm": 44, "thickness_mm": 4}},
    {"tool": "add_rib", "params": {"id": "r1", "start": [16, -14, 4], "end": [88, -4, 18], "width_mm": 5, "height_mm": 18}},
    {"tool": "add_rib", "params": {"id": "r2", "start": [16, 14, 4], "end": [88, 4, 18], "width_mm": 5, "height_mm": 18}},
    {"tool": "set_load", "params": {"point_mm": [90, 0, 4], "vector_n": [0, 0, -120]}},
    {"tool": "run_fea", "params": {}},
    {"tool": "commit_design", "params": {}}
  ]
}
JSON
```

## Recommended Installs For Production-Grade 3D

After approval, install into a local project venv:

```bash
cd experiment-mechanical-idea
uv venv --python 3.12 .venv
source .venv/bin/activate
uv pip install numpy scipy pydantic fastapi uvicorn meshio gmsh scikit-fem
```

Optional/heavier:

```bash
uv pip install cadquery openmdao
```

Notes:

- `scikit-fem` + `gmsh` + `meshio` is the fastest serious 3D FEA path.
- `cadquery` is ideal for real CAD generation but may pull heavier OpenCASCADE dependencies.
- `FEniCSx/dolfinx` is more production-serious but harder to install reliably on macOS through pip.

