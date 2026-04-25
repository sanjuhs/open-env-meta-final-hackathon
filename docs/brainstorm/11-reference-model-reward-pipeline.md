# Document 11: Reference Model Reward Pipeline

Date: 2026-04-25

## Core Idea

CADForge should not only reward whether code compiles. It should reward whether the generated CAD becomes a valid, watertight, physically coherent object that resembles the intended target.

The strongest reward stack is:

```text
prompt
-> reference image or reference mesh
-> agent-generated SCAD/CAD
-> compiled/rendered candidate mesh
-> topology gate
-> shape similarity reward
-> semantic contact graph reward
-> structural/editability reward
```

The topology gate comes first.

If the candidate does not compile, is not watertight, or has floating parts, the reward should be near zero regardless of visual similarity.

## Markus Chair Reference

Current reference asset:

```text
3d-models/ikea_markus_office_chair.glb
```

This can become the first chair-reference target.

The CAD agent still outputs editable SCAD/CAD code. The GLB is only used as a reward/reference object.

## Why A Reference Mesh Helps

Prompt-only reward is too fuzzy.

For example:

```text
Build an office chair.
```

The agent may create:

- a stool,
- a flat bracket,
- a disconnected pile of cubes,
- a chair-like silhouette with no structural connections,
- a raw mesh that looks okay but is not editable CAD.

A reference mesh gives a concrete target distribution:

- overall proportions,
- seat/back/arm/headrest layout,
- rough silhouette,
- support footprint,
- height/width/depth ratios,
- part presence.

But the reference mesh must not become the final output. The final output remains parametric CAD code.

## Reward Order

Use a strict reward order:

1. **Compile validity**
   - SCAD/CAD parses.
   - CAD kernel or renderer produces geometry.
   - No unsupported operations.

2. **Topology validity**
   - one connected component,
   - no floating parts,
   - watertight mesh,
   - no boundary edges,
   - no non-manifold edges,
   - nonzero volume.

3. **Semantic contact graph**
   - chair legs touch seat,
   - backrest touches seat or rear supports,
   - crossbars touch both intended legs,
   - hook arm touches wall plate,
   - truss members meet at nodes.

4. **Reference similarity**
   - voxel IoU,
   - Chamfer distance,
   - silhouette overlap,
   - bounding-box proportions,
   - support footprint similarity.

5. **Engineering checks**
   - load path,
   - safety factor,
   - deflection,
   - material/process constraints.

6. **Editability**
   - named parameters,
   - stable features,
   - rebuilds after dimension/load/material mutation.

## Reference Similarity Metrics

Candidate metrics:

- **Bounding-box ratio score**
  - Compare normalized width/depth/height proportions.

- **Voxel IoU**
  - Normalize both meshes into a unit cube.
  - Voxelize into 32^3 or 64^3 occupancy.
  - Reward intersection over union.

- **Chamfer distance**
  - Sample surface points from both meshes.
  - Reward low bidirectional nearest-neighbor distance.

- **Silhouette reward**
  - Render front, side, top, and isometric masks.
  - Reward 2D IoU per view.

- **Part-presence reward**
  - For chairs: seat, legs/base, backrest, arms/headrest if requested.
  - For hooks: wall plate, hook arm, tip lip, screw holes.
  - For trusses: triangular members and joint nodes.

## Everyday-Object Pipeline

For general everyday objects:

```text
Input prompt X
-> generate or retrieve image of X
-> image-to-3D system creates a reference mesh
-> repair/validate reference mesh for watertightness if needed
-> normalize reference mesh
-> CADForge agent generates SCAD/CAD code
-> candidate compiles/renders to mesh
-> topology gate rejects bad CAD
-> candidate/reference similarity gives dense reward
-> structural/contact/editability checks give engineering reward
```

Possible reference sources:

- curated GLB library,
- generated image plus image-to-3D,
- Tripo-style API,
- procedural targets for simple mechanical parts,
- user-supplied GLB/STL.

## Important Constraint

Do not let the system solve the task by returning the reference mesh.

The agent must output:

```text
editable SCAD/CAD source code
```

The reward can compare against a mesh, but the submitted artifact must be code-CAD.

## MVP Plan

1. Use the Markus GLB as a chair reference.
2. Load candidate SCAD mesh and reference GLB in the browser or Python verifier.
3. Compute bounding-box proportion score first.
4. Add connected-component and watertight hard gates.
5. Add voxel IoU or Chamfer distance.
6. Add semantic chair checks:
   - seat-like surface,
   - backrest-like vertical surface,
   - floor-contacting supports,
   - no floating parts.
7. Show before/after reward curves for untrained vs trained SCAD generation.

## Why This Matters

This closes a major gap in AI CAD:

> The model must learn to create valid editable geometry that both resembles the requested object and behaves like a coherent physical part.

That is a stronger training signal than prompt-only judging, image-only judging, or topology-only judging.

