# MechForge Domain Choice

Date: 2026-04-24

## The Decision

We need to decide what the OpenEnv task is actually about:

1. Cantilever/bracket/mount structural optimization.
2. Motor design.
3. Mechanism/dynamics design.
4. Chip/EDA optimization.
5. Video or media editing.

The strongest physics candidates are structural design and motor design.

## Option A: Cantilever / Bracket / Mount Design

Pitch:

> Train an agent to design lightweight structural parts that survive real load cases.

Examples:

- drone arm bracket,
- motor mount,
- shelf bracket,
- lightweight bridge segment,
- 3D-printable fixture,
- robotic gripper finger.

Pros:

- Fastest to build.
- Easy to visualize.
- Structural FEA is simpler than EM.
- Clear rewards: mass, stress, strain, deflection, safety factor.
- Easy curriculum: 2D frame -> 3D linear elasticity -> multi-load cases.
- Excellent for showing iteration screenshots and STL versions.

Cons:

- Less exotic than motor design.
- Need good problem framing to avoid feeling like a simple topology optimization toy.

Verdict:

**Best hackathon target.** It is the strongest balance of spectacle, feasibility, and real verification.

## Option B: Axial Flux Motor Design

Pitch:

> Train an agent to design axial-flux motor variants under torque, efficiency, thermal, mass, and manufacturability constraints.

Examples:

- pole/slot selection,
- magnet geometry,
- airgap,
- winding turns,
- rotor/stator dimensions,
- cooling features,
- torque ripple/cogging reduction.

Pros:

- Most personally differentiated for a mechanical/electrical engineer.
- Very impressive story.
- Naturally multiphysics: EM + thermal + structural.
- Strong R&D flavor.

Cons:

- Hardest to implement correctly.
- EM FEA and motor post-processing are not trivial.
- 3D axial-flux simulation is expensive.
- Faster practical path is 2D/axisymmetric/analytical first, which may disappoint if pitched as full 3D.

Verdict:

**Best long-term product/research direction, risky for this hackathon.** Use as a stretch or second environment if structural MechForge works.

## Option C: Mechanism / Dynamics Design

Pitch:

> Train an agent to design mechanisms that move correctly under physical simulation.

Examples:

- linkage design,
- gripper mechanism,
- passive walker,
- robot end-effector,
- compliant-ish mechanism approximated as rigid joints.

Pros:

- MuJoCo is actually a great fit.
- Visual and interactive.
- Rewards are measurable: trajectory error, contact stability, energy, joint limits.

Cons:

- Not FEA.
- Less aligned with stress/thermal/electromagnetics.
- Could drift into robotics control instead of engineering design.

Verdict:

Good if we want MuJoCo. Not the right answer if we want structural/thermal/EM.

## Option D: Full Multiphysics MotorBench

Pitch:

> A multiphysics OpenEnv where agents design electric machines and learn from EM, thermal, and structural simulation.

Pros:

- Huge wow factor.
- Most ambitious.
- Strong self-improvement story.

Cons:

- Too much for a two-day MVP unless heavily constrained.
- Many solvers and file formats.
- Risk of spending the whole hackathon packaging tools.

Verdict:

Great final vision, not the first build.

## Recommendation

Build:

> **MechForge Structural 3D: motor-mount/bracket optimization with real 3D FEA.**

Frame it as the first task family in a larger MechForge platform:

- structural bracket/motor mount now,
- thermal add-on next,
- motor EM design later.

This preserves the big dream while keeping the first submission shippable.

## Why Motor Mount Is The Sweet Spot

A motor mount bridges both worlds:

- It is structurally verifiable.
- It is visually clear.
- It can later connect to motor design.
- It supports heat and vibration extensions.
- It feels more interesting than a generic cantilever.

Suggested final prompt family:

> Design a lightweight motor mount for a drone/EV test rig. It must support thrust/load, keep shaft alignment under deflection, avoid high stress near bolt holes, and optionally dissipate heat from the motor face.

That gives us:

- structural FEA now,
- thermal next,
- motor design story later.

