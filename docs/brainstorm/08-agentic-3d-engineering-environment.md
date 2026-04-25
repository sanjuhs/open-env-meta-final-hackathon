# Document 8: Agentic 3D Engineering Environment

Date: 2026-04-24

## Honest Product Definition

The winning product is not:

> LLM generates a 3D model.

The winning product is:

> An AI engineering agent that turns natural-language physical requirements into parameterized CAD, runs simulation and manufacturability checks, optimizes the design, and outputs manufacturable files with a safety-factor report.

For fixtures:

> Given load, material, envelope, mounting constraints, print/manufacturing process, and target safety factor, generate a manufacturable bracket/fixture and prove it with FEA.

For motors:

> Given magnets, bearings, shaft, voltage/current limits, printer/process, and target torque/RPM, generate a printable axial-flux BLDC motor kit and prove it with EM/thermal/structural simulation.

The fixture path is more commercially useful and shippable.
The motor path is more fun and demo-worthy.
Together, they are a strong long-term research/product direction.

## Hackathon Choice

For the next 24 to 26 effective hours, pick:

> **Option A: 3D structural motor-mount/bracket/fixture design with real 3D linear elasticity.**

Why:

- It is doable fast.
- It is visual.
- It is objectively verifiable.
- It supports 300+ step agentic loops.
- It can expand later to thermal, dynamics, NVH, and motor design.

Do not start with full axial-flux motor EM unless structural MechForge is already working. MotorBench should be the long-term second stage.

## Agent Loop

The environment should run this loop:

```text
prompt
  -> parse requirements
  -> ask/assume missing boundary conditions
  -> generate 3-5 design families
  -> create parametric CAD/actions
  -> run 3D FEA
  -> identify stress concentrations and deflection
  -> add fillets/ribs/thickness or move holes
  -> re-run FEA
  -> optimize mass/safety/deflection/manufacturability
  -> export CAD/STL + simulation report
```

In OpenEnv terms:

```text
reset(task_seed)
  -> observation: design brief, constraints, materials, available tools

step(action)
  -> environment applies CAD/tool action
  -> if requested, simulator runs
  -> reward components returned
  -> observation includes metrics, warnings, hotspots, artifacts

done
  -> when agent commits a design or exceeds step budget
```

## Missing-Information Handling

A naive LLM will fail because it will not know boundary conditions.

The environment must either ask for or infer:

- Is 120 Nm a torque around a shaft?
- Is it a force through a hook/tip/load face?
- Where is the fixture mounted?
- What are the bolt holes?
- Static, cyclic, or impact load?
- Desired safety factor?
- Material ambiguity, e.g. "601 aluminum" likely means 6061 aluminum.
- Manufacturing process: 3D print, CNC, sheet metal, casting.
- Temperature or thermal expansion constraints.

For hackathon speed, the environment should include default load templates:

1. **Cantilever tip load**: fixed face at x=0, downward force at free tip.
2. **Motor mount**: bolt holes fixed, radial/axial motor load at boss, optional torque couple.
3. **Chair/seat support**: fixed feet or base, downward distributed load on seat surface.
4. **Torque fixture**: equal/opposite force couple around a shaft axis.

If the user explicitly tells where the load goes, that overrides defaults.

## Tool Calls

Use incremental tool calls rather than one huge CAD file.

Design tools:

```json
{"tool": "create_design_family", "family": "ribbed_cantilever_bracket"}
{"tool": "set_material", "material": "aluminum_6061"}
{"tool": "set_envelope", "length_mm": 100, "width_mm": 45, "height_mm": 30}
{"tool": "add_mount_hole", "id": "m1", "center": [10, -15, 0], "radius_mm": 2.6}
{"tool": "add_rib", "id": "r1", "start": [12, -15, 4], "end": [92, -4, 22], "width_mm": 5}
{"tool": "add_lightening_hole", "id": "h1", "center": [55, 12, 2], "radius_mm": 4}
{"tool": "set_base_thickness", "value_mm": 4.5}
```

Load/boundary tools:

```json
{"tool": "set_fixed_region", "region": "left_face"}
{"tool": "set_fixed_region", "region": "mounting_holes"}
{"tool": "set_force", "region": "tip_boss", "vector_n": [0, 0, -120]}
{"tool": "set_torque", "axis": "x", "origin": [90, 0, 10], "torque_nm": 120}
{"tool": "set_temperature", "region": "motor_face", "temperature_c": 80}
{"tool": "set_heat_source", "region": "motor_face", "power_w": 12}
```

Simulation tools:

```json
{"tool": "build_cad"}
{"tool": "mesh_geometry", "target_size_mm": 5}
{"tool": "run_fea", "physics": "linear_elasticity"}
{"tool": "run_thermal", "physics": "steady_state_heat"}
{"tool": "inspect_hotspots", "field": "von_mises_stress"}
{"tool": "export_artifacts", "formats": ["json", "stl", "step", "vtu", "png"]}
```

Optimization tools:

```json
{"tool": "propose_revision", "objective": "reduce_mass_keep_sf_above_2"}
{"tool": "sweep_parameter", "name": "base_thickness_mm", "values": [3.5, 4, 4.5, 5]}
{"tool": "optimize_parameters", "method": "cma_es", "budget": 40}
{"tool": "commit_design"}
```

## Environment Responses

After a design action:

```json
{
  "valid": true,
  "changed_parameters": ["base_thickness_mm"],
  "geometry_status": "buildable",
  "warnings": []
}
```

After FEA:

```json
{
  "method": "3D linear tetrahedral elasticity",
  "nodes": 240,
  "elements": 620,
  "max_von_mises_mpa": 138.4,
  "max_principal_strain": 0.0021,
  "max_displacement_mm": 2.7,
  "safety_factor": 2.0,
  "mass_g": 51.2,
  "hotspots": [
    {"region": "fixed_root", "severity": 0.50},
    {"region": "rib_root_r1", "severity": 0.42}
  ],
  "constraints": {
    "safety_factor_above_2": true,
    "mass_below_45g": false,
    "tip_deflection_below_2mm": false
  }
}
```

After commit:

```json
{
  "final_score": 0.82,
  "reward_breakdown": {
    "safety": 0.30,
    "stiffness": 0.22,
    "mass": 0.12,
    "manufacturability": 0.10,
    "invalid_action_penalty": 0.0
  },
  "artifacts": {
    "design_json": "runs/.../design.json",
    "stl": "runs/.../geometry.stl",
    "report": "runs/.../report.md"
  }
}
```

## Long-Horizon Step Design

A 300-500 step episode is plausible if the environment exposes detailed action space:

- 20-50 requirement parsing and constraint-confirmation actions.
- 30-80 design family generation and selection actions.
- 100-250 geometry edits.
- 50-100 simulation/inspection actions.
- 50-100 optimization sweeps and revisions.
- 10-20 final export/report actions.

Training goal:

- Baseline model takes many invalid or inefficient steps.
- Trained model learns good action order:
  - clarify/assume loads,
  - create feasible design family,
  - run simulation early,
  - inspect hotspots,
  - revise local features,
  - avoid over-lightening,
  - commit only after constraints pass.

The story becomes:

> RL teaches engineering workflow discipline, not just CAD generation.

## 24-Hour MVP

Build in order:

1. Current experiment: GPT-5.4 structured design + Three.js viewer.
2. Add 3D tetrahedral linear elasticity solver.
3. Add load manager for cantilever/motor-mount/torque defaults.
4. Add trace view for tool calls and simulator responses.
5. Save per-iteration artifacts.
6. Convert to OpenEnv API.
7. Add baseline inference.
8. Run short training or at least repeated benchmark showing improvement.

## What To Say In The Pitch

> We built an OpenEnv for engineering design agents. The agent receives physical requirements, infers boundary conditions, creates parametric CAD actions, runs real 3D FEA, reads stress/deformation feedback, and iteratively improves the design. This is a foundation for simulation-trained engineering models across fixtures, mounts, thermal constraints, and eventually motors.

