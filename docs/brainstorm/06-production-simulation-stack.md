# Production Simulation Stack For MechForge

Date: 2026-04-24

## Short Answer

For a production-quality MechForge, do **not** use MuJoCo as the main solver for stress, heat, or electromagnetics.

Use MuJoCo only if the environment is about:

- mechanism motion,
- contact,
- robotics,
- actuated joints,
- dynamic control,
- impact-like rigid-body behavior.

For a full-stack engineering design simulator, the better architecture is:

```text
LLM / Agent
  -> constrained design actions
  -> CAD kernel
  -> meshing
  -> multiphysics solvers
  -> post-processing
  -> reward + visual trace
```

## Recommended Production Stack

| Layer | Recommended tool | Why |
|---|---|---|
| Agent orchestration | OpenAI Responses API now, Agents SDK later | Responses is enough for benchmark; Agents SDK is useful when tool traces and multi-agent workflows become first-class. |
| Design representation | Parametric feature graph | Better than arbitrary mesh generation; supports CAD, constraints, versioning, and RL actions. |
| CAD kernel | CadQuery / OpenCASCADE | Python-native CAD generation, real B-rep/STEP export, deterministic parametric geometry. |
| Meshing | Gmsh | Mature, scriptable 2D/3D mesh generator with OpenCASCADE geometry support. |
| Structural FEA | FEniCSx or scikit-fem | FEniCSx is stronger for serious PDE work; scikit-fem is lighter and easier for hackathon packaging. |
| Thermal FEA | FEniCSx / scikit-fem / Elmer | Heat equation is straightforward in finite element tools. |
| Electromagnetic FEA | Elmer FEM, GetDP, MFEM, or FEMM/Pyleecan for motor-specific workflows | Motors need magnetic vector potential, materials, windings, airgap, torque extraction. |
| Visualization | Three.js in UI, ParaView/VTK for heavy post-processing | Three.js is judge/demo-facing; VTK/ParaView is engineering-facing. |
| Optimization | OpenMDAO or custom curriculum/RL loop | OpenMDAO is excellent for deterministic design-variable optimization; OpenEnv/RL is the hackathon learning loop. |
| Artifact storage | per-iteration JSON + STEP/STL + mesh + VTK + screenshot | Enables side-by-side version comparison. |

## Exact Production Loop

A single design episode should look like this:

```text
1. reset()
   - Generate design brief.
   - Define load cases, fixtures, materials, constraints, objective.

2. agent action: edit_design
   - Add rib, change thickness, move hole, set magnet width, change winding turns, etc.

3. geometry build
   - Build CAD from parametric feature graph through CadQuery/OpenCASCADE.
   - Export STEP/STL.

4. mesh build
   - Run Gmsh.
   - Tag boundaries: fixed faces, load faces, heat sources, winding regions, magnets, airgap.

5. solver run
   - Structural: displacement, stress, strain, safety factor.
   - Thermal: temperature field, hot spot, thermal margin.
   - Electromagnetic: flux density, torque, losses, cogging proxy.

6. post-process
   - Save VTK/VTU fields.
   - Produce scalar metrics.
   - Render screenshot or send mesh fields to Three.js.

7. reward
   - Score constraints and objective tradeoffs.

8. next observation
   - Return metrics, failed constraints, top stress/thermal/EM hotspots, and visual artifacts.
```

## What The Agent Should Output

Do not ask the LLM to output an entire arbitrary CAD file as the main action.

For serious parts, use tool calls like:

```json
{"tool": "set_parameter", "name": "base_thickness_mm", "value": 4.5}
{"tool": "add_rib", "start": [12, -18, 4], "end": [92, -4, 20], "width_mm": 5}
{"tool": "move_lightening_hole", "id": "hole_2", "center": [54, 12, 0], "radius_mm": 4}
{"tool": "set_boundary_condition", "face": "left_mount_faces", "type": "fixed"}
{"tool": "set_load", "face": "tip_boss", "vector_n": [0, 0, -120]}
{"tool": "run_simulation", "physics": ["structural", "thermal"]}
```

Why:

- Tool calls are inspectable.
- Invalid actions can be rejected.
- The environment can apply partial progress rewards.
- The CAD remains valid more often.
- The same action sequence becomes training data.

The current experiment returns a full structured design JSON because it is a fast benchmark. The OpenEnv version should move toward smaller incremental design actions.

## 3D Structural FEA Path

For full 3D structural FEA, I would implement:

```text
CadQuery/OpenCASCADE -> STEP/B-rep -> Gmsh tetra mesh -> FEniCSx or scikit-fem -> VTU fields -> Three.js/VTK viewer
```

### Fastest hackathon path

- Use `scikit-fem` for 3D linear elasticity on simple tetrahedral meshes.
- Use Gmsh for meshing simple CAD.
- Use meshio to bridge Gmsh meshes into Python/VTK outputs.

### More serious production path

- Use FEniCSx for PDE solves and scalable linear algebra.
- Use PETSc-backed solvers.
- Store post-processing fields as VTK/VTU.

## Electromagnetic + Thermal Motor Path

For motor design, do **not** start with arbitrary 3D motor FEA.

Production path:

```text
parametric motor template
  -> 2D cross-section CAD
  -> Gmsh mesh with material regions
  -> EM solver for magnetic vector potential
  -> torque / B-field / losses
  -> thermal network or thermal FEA
  -> reward
```

Candidate solvers:

- Elmer FEM: multiphysics, includes heat transfer and electromagnetics.
- GetDP: finite element solver often used with Gmsh for EM problems.
- Pyleecan: motor-specific design framework, but deployment constraints need checking.
- FEMM: common motor workflow but Windows-centric, not ideal for HF/Linux deployment.

## Visual Versioning

Every iteration should save:

```text
runs/{run_id}/
  iter_001/
    design.json
    actions.jsonl
    geometry.step
    geometry.stl
    mesh.msh
    structural.vtu
    thermal.vtu
    electromagnetic.vtu
    screenshot.png
    metrics.json
  iter_002/
    ...
```

The UI should show:

- version timeline,
- side-by-side geometry,
- stress heatmap,
- deformation magnification slider,
- thermal heatmap,
- EM flux density heatmap for motor tasks,
- tool-call/action trace,
- score curve over iterations.

## What To Build First

Best next implementation step:

1. Replace the current JS frame FEA with a Python simulator service.
2. Start with scikit-fem 3D structural FEA for a simple cantilever bracket template.
3. Add Gmsh meshing.
4. Add VTK/VTU export.
5. Keep Three.js for browser rendering.
6. Only then add thermal.
7. Add electromagnetics only if we pick motor design as the final domain.

## Installation Note

The local environment currently does not have the heavy solver packages installed:

- `scikit-fem`
- `dolfinx`
- `gmsh`
- `meshio`
- `cadquery`
- `mujoco`
- `openmdao`

Installing those packages is a real environment change. Do it intentionally once we pick the stack.

