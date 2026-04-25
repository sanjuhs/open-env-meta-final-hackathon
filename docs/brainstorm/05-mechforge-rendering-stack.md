# MechForge Rendering And Simulation Stack

Date: 2026-04-24

## The Confusion To Resolve

For MechForge there are four separate jobs:

1. Generate or modify a design.
2. Render the design so humans can inspect it.
3. Simulate or verify the design.
4. Export the design to real CAD/manufacturing formats.

One tool does not need to do all four.

## Recommended MVP Stack

| Layer | MVP choice | Why |
|---|---|---|
| Design representation | Structured parametric JSON | Easy for LLMs, easy to validate, easy to convert. |
| Browser renderer | Three.js | Fast, visual, interactive, works inside a web demo. |
| Fast verifier | Custom beam/truss-style solver | Good enough for reward curves and RL feedback. |
| Export | STL from Three.js mesh | Immediate tangible artifact. |
| Future CAD backend | CadQuery first, OpenSCAD second | CadQuery is Python-native and more flexible for OpenEnv. |
| Future simulation backend | simplified FEM, FEniCSx, or specialized solver | Swap in after the environment loop works. |

## Why Not OpenSCAD First?

OpenSCAD is good for deterministic programmatic CAD. It is available on macOS and can generate real geometry, but it is not the fastest path for a live web app.

Use OpenSCAD later if we want:

- scriptable constructive solid geometry,
- reproducible `.scad` artifacts,
- STL export through the OpenSCAD CLI,
- simple parts made from unions/differences.

For the first experiment, Three.js is better because it gives immediate visual feedback in the browser.

## Why Not Full FEA First?

Full FEA is the wrong first milestone. It risks spending the hackathon on meshing, solver stability, and packaging instead of the OpenEnv loop.

Better:

1. Start with a simplified verifier that produces a reward.
2. Show that LLM behavior improves under that reward.
3. Add higher-fidelity simulation only after the loop is stable.

The judges care most that the environment trains meaningful behavior and shows improvement. A simple but coherent verifier is acceptable if we explain the limitations honestly.

## Benchmark Plan

Before committing to the full environment, run GPT-5.4 through a small prompt-to-design benchmark:

- Prompt asks for a lightweight bracket under a load case.
- Model returns structured design JSON.
- Renderer shows the part.
- Verifier scores mass, stress proxy, deflection proxy, safety factor, and manufacturability.
- We inspect whether the model uses real design patterns like ribs, load paths, holes in low-stress areas, and avoids invalid geometry.

This tells us whether current frontier models already solve the task or whether there is room for RL improvement.

## What The Experiment App Does

The app in `experiment-mechanical-idea/` implements this benchmark:

- Frontend: Vite + Three.js.
- Backend: Express + OpenAI Responses API.
- Input: natural-language mechanical design prompt.
- Output: structured parametric design JSON.
- Render: plate, ribs, holes, bosses, fixed holes, load arrow.
- Verifier: fast beam-style estimate.
- Export: STL from the rendered mesh.

## Final Recommendation

For the OpenEnv version:

1. Keep the agent action space constrained.
2. Use Three.js for the judge-facing demo.
3. Use Python/CadQuery later for real CAD export.
4. Keep simulation/verifier independent from the renderer.
5. Do not let the LLM generate arbitrary meshes in the first version.

