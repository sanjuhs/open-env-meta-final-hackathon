# CadQuery Environment Report: inference-stator-qwen-vs-frontier / rl-tuned-qwen

- Total reward: `0.654`
- Build: `1.000`
- Topology: `1.000`
- Contact/gaps: `1.000`
- Semantic parts: `0.300`
- Reference similarity: `0.067`
- Silhouette: `0.167`
- Editability: `0.825`

## Topology

```json
{
  "vertices": 600,
  "faces": 1248,
  "components": 1,
  "floating_components": 0,
  "watertight": true,
  "winding_consistent": true,
  "boundary_edges": 0,
  "non_manifold_edges": 0,
  "degenerate_faces": 0
}
```

## Notes
- Candidate is weak on axial_motor_stator_12_slot semantic hints; add/organize recognizable subassemblies in code.
- Candidate is still far from the ideal CadQuery/reference GLB shape.
