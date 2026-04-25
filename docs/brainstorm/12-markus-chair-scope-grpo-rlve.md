# Brainstorm 12: Markus Chair Scope for CADForge RLVE

## Core scope

For the hackathon, CADForge should scope down to one object family: an office chair similar to the IKEA Markus chair. This is narrow enough for a 0.6B model to learn meaningful structure, but still hard enough to prove the thesis that a model can generate editable, valid CAD instead of merely producing decorative 3D mesh output.

The environment should train and evaluate prompts such as:

- Make an editable SCAD model as similar as possible to the Markus chair reference.
- Make a Markus-like chair with a taller backrest.
- Make the chair with thicker armrests.
- Make the chair base wider while preserving the five-star support.
- Repair this candidate chair so every structural part touches the assembly.
- Improve the candidate so it is watertight, editable, and made from clean primitives.

This gives us a focused benchmark: not "make any CAD object," but "learn the grammar and construction pattern for one real household/mechanical object."

## Why this is good for GRPO and RLVE

This is a strong fit for GRPO because each prompt can produce a group of SCAD candidates, and the verifier can rank them with real geometry signals. The reward does not need to be vague preference text. It can be built from compile success, mesh validity, connected components, watertightness, contact graph quality, bounding-box alignment, silhouette similarity, and shape similarity to the reference GLB.

It is also a strong fit for RLVE because the environment is not only judging final text. It is compiling and rendering the artifact, measuring what actually exists, and feeding that back into the next attempt.

The important constraint is that the 0.6B model should not be asked to emit arbitrary raw CAD text from nothing. It should be trained around a constrained SCAD/CSG grammar or AST-style action space:

- Add primitive: cube, cylinder, sphere.
- Add transform: translate, rotate, scale.
- Add boolean: union, difference, intersection.
- Add semantic chair part: seat, backrest, armrest, central column, five-star base spoke, caster proxy.
- Repair operation: snap a part to nearest body, thicken a thin wall, union overlapping contact regions, remove floating component.

That is how a small model can become surprisingly good. It learns the local construction game and the verifier keeps it from drifting into invalid geometry.

## Reference target

The fixed hackathon reference should be the existing Markus chair GLB in the repo. We normalize it once and use it as the reward target:

1. Load the GLB.
2. Normalize scale, orientation, and origin.
3. Extract reference bounding box, silhouette renders, voxel occupancy, point cloud samples, and major-part hints.
4. Generate a SCAD candidate.
5. Render candidate to mesh.
6. Normalize candidate to the same coordinate frame.
7. Score topology first, then score similarity.

The reference mesh does not need to be CAD-native. It can be a target signal. The output we care about is still editable SCAD.

## Reward shape

Topology should dominate the reward. A model that makes a pretty chair with floating parts should lose badly.

Suggested hard gates:

- Uncompilable SCAD: terminate with severe penalty.
- Empty mesh: terminate with severe penalty.
- More than one connected component: severe penalty or terminate.
- Non-watertight mesh: severe penalty.
- Boundary edges or non-manifold edges: severe penalty.
- Parts that are close but not touching: high penalty.
- Excessive node count for the same shape quality: mild parsimony penalty.

Suggested positive rewards:

- Similar voxel occupancy to Markus reference.
- Low Chamfer distance between sampled candidate/reference point clouds.
- Matching front, side, top, and isometric silhouettes.
- Matching chair-specific dimensions: tall backrest, seat height, base radius, armrest height.
- Valid contact graph: back touches seat, armrests touch seat/back, column touches seat/base, all spokes touch the hub.
- Clean editability: named or segmented code blocks for seat, backrest, arms, hub, spokes, and caster proxies.

The reward should look roughly like:

```text
R = topology_gate
  + shape_similarity
  + silhouette_similarity
  + chair_part_contact_score
  + editability_score
  - node_count_penalty
  - thin_wall_penalty
```

Where `topology_gate` can zero out or heavily negate the rest when the CAD is invalid.

## Self-correction loop

The agent should be allowed to see verifier output and revise:

- connected component count
- boundary edge count
- non-manifold edge count
- watertight true/false
- bounding-box error
- silhouette error by view
- nearest-part contact gaps
- largest missing region against the reference voxel grid

This makes the task agentic. The model can take steps like:

- "The backrest is disconnected from the seat; lower it by 4 mm and overlap by 2 mm."
- "The five-star base spokes are separate; add a central hub cylinder and union each spoke into it."
- "The silhouette is too short; increase backrest height."
- "The right side silhouette is missing armrests; add two horizontal cylinders/boxes connected to the backrest and seat."

For this benchmark, part assembly is better than carving a chair from one large slab. A slab can make connected geometry easier, but it hurts editability and does not teach meaningful mechanical construction. The model should learn to assemble semantic parts with intentional overlaps and unions.

## FAL reference-model expansion path

For Markus scope, we start with the provided GLB. For broader household objects later, we can generate reference meshes from prompts:

1. User enters an engineering prompt.
2. OpenAI image generation creates a clean, white-background product image.
3. FAL SAM 3D Objects reconstructs the object from that image.
4. We download `model_glb`, `individual_glbs`, `gaussian_splat`, metadata, and `artifacts_zip` when available.
5. We normalize the GLB into a reward target.
6. CADForge trains or evaluates SCAD candidates against that reference.

Example input prompt:

```text
Design a simple 6061 aluminum wall-mounted J hook for a 120 N downward hanging load at the hook tip. It should visibly look like a hook, with a compact wall mount and a curved hook arm, not a ribbed cantilever bracket.
```

The image generation prompt should keep the reference clean:

```text
Design a simple 6061 aluminum wall-mounted J hook for a 120 N downward hanging load at the hook tip. It should visibly look like a hook, with a compact wall mount and a curved hook arm, not a ribbed cantilever bracket. Realistic product render, plain white background, isolated object, no labels, no text.
```

FAL's `fal-ai/sam-3/3d-objects` endpoint takes an `image_url` plus optional segmentation prompt/masks/point prompts/box prompts, and can return GLB outputs, Gaussian splat output, metadata, individual object files, and an artifacts zip. The API docs recommend keeping the FAL key on the server side through `FAL_KEY`. The playground currently lists the request cost as `$0.02` per generation, but the app should read and log actual cost metadata at runtime if FAL exposes it.

For our app, this should be server-side only:

```text
POST /api/reference-models
  prompt -> image generation
  image_url -> fal-ai/sam-3/3d-objects
  result -> download GLB/artifacts to data/reference-models/<slug>/
  normalized target -> rewards/<slug>.json
```

The frontend should never expose `FAL_KEY` or `FAL_AI_API_KEY`.

## Minimal hackathon deliverable

The most credible v1 is:

1. Simple UI with one `Generate` button.
2. Prompt asks for a Markus-like chair.
3. Model generates SCAD.
4. Browser renders the SCAD as real geometry.
5. Viewer automatically shows isometric, front, back, left, right, top, and bottom views.
6. Verifier reports watertightness, floating components, boundary edges, and non-manifold edges.
7. Reward code compares the candidate mesh against the Markus GLB reference.
8. GRPO loop ranks multiple candidates and fine-tunes a 0.6B model on the winning patterns.

This is a better hackathon scope than generic CAD generation because the demo can show visible learning: early chairs have floating parts and broken bases; later chairs become coherent, connected, watertight, and more Markus-like.

## Position

I would rate this direction a 9/10 for the hackathon if we keep the scope narrow. It has a clean story, a measurable verifier, a concrete reference object, and a realistic training target for a small model. The risk is trying to generalize too early. The winning move is to make one chair family work extremely well, then expand the same environment to hooks, brackets, tables, trusses, and other household mechanical objects.
