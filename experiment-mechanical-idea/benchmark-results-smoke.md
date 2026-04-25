# MechForge Benchmark Smoke Result

Date: 2026-04-24

Prompt:

```text
Design a lightweight 6061 aluminum cantilever bracket fixed by two M5 bolts on the left and carrying 120 N downward at a tip 90 mm from the fixed edge. Keep mass below 45 g while maintaining safety factor above 2.0 and minimizing deflection.
```

## GPT-5.4 Three-Iteration Loop

| Iteration | Score | Safety factor | Stress MPa | Strain uε | Deflection mm | Thermal proxy C | Mass g |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 0.823 | 19.22 | 14.36 | 208.1 | 0.088 | 0.40 | 78.38 |
| 2 | 0.888 | 11.25 | 24.53 | 355.6 | 0.141 | 0.42 | 48.16 |
| 3 | 0.881 | 11.47 | 24.06 | 348.7 | 0.165 | 0.46 | 50.76 |

Best iteration: 2.

Interpretation: the feedback loop reduced mass substantially while preserving a high safety factor. This is encouraging as a first signal for an OpenEnv-style iterative design task.

## GPT-5.5 Access Check

The current API key returned:

```text
404 The model `gpt-5.5` does not exist or you do not have access to it.
```

The benchmark UI now handles this as a per-model error instead of failing the whole run.

## After Switching To 3D Linear FEA

The simulator now uses coarse 3D linear tetrahedral elasticity.

Sample design:

```text
method=3D linear tetrahedral elasticity
nodes=178
tets=462
stress=13.53 MPa
strain=297.6 uε
deflection=0.06 mm
safety factor=20.4
load=fixed left face + 120 N downward at inferred tip/load boss
```

This is intentionally coarse, but it is a real 3D finite-element solve and gives us an immediate benchmark path without waiting on external meshing packages.

## Earlier Frame FEA Check

Before the 3D tetrahedral solver, the simulator used a 2D Euler-Bernoulli frame FEA solve.

Sample design:

```text
method=2D Euler-Bernoulli frame FEA
nodes=12
elements=12
stress=97.96 MPa
strain=1419.7 uε
deflection=1.917 mm
safety factor=2.82
```

GPT-5.4 two-iteration FEA-backed run:

| Iteration | Score | Safety factor | Stress MPa | Strain uε | Deflection mm | Mass g | Best? |
|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | 0.633 | 2.06 | 133.83 | 1939.5 | 2.618 | 50.81 | yes |
| 2 | 0.599 | 1.85 | 149.14 | 2161.4 | 2.918 | 45.16 | no |

Interpretation: once the stricter FEA backend replaced the optimistic proxy, the second revision got lighter but violated the desired safety margin. This is useful: it exposes a real optimization tradeoff the agent must learn.
