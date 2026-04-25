# GPT-5.4 Agentic CAD Repair: Two-Finger Robot Gripper

Trace: `openai-gpt-5.4-robot_gripper_two_finger-missing_features-2026-04-25T14-39-27-233Z`
Model: `gpt-5.4`
Vision feedback: `no`
Seed mode: `missing_features`

## Input Prompt

Design a simple two-finger robot gripper as editable CadQuery. Include a palm block, two parallel fingers, pivot bosses, linkage bars, fingertip pads, and mounting holes.

Additional teacher-data variant: prioritize robust build correctness, recovery from invalid or brittle CadQuery, and simple manufacturable shapes. Avoid fragile loft/sweep/fillet chains; prefer reliable boxes, cylinders, extrusions, cuts, named dimensions, and helper functions.

## Task Spec

- Task id: `robot_gripper_two_finger`
- Family: `robotics`
- Difficulty: `hard`
- Semantic hints: `robot_gripper`, `palm_block`, `two_finger`, `pivot_boss`, `linkage_bar`, `fingertip_pad`, `mounting_hole`
- Target bbox profile: `160 x 120 x 60 mm`

## Primary Creation Stage

The seed begins as an under-specified block with missing functional details. The agent must create an editable robot gripper with a palm block, two fingers, pivot bosses, linkage bars, fingertip pads, and mounting holes.

The environment evaluates the current code, saves renders/STL/reward JSON, sends the model the previous code plus verifier feedback, then evaluates the revised CadQuery file. Each row below is one full observe -> edit -> score step.

| State | Reward | Delta | Isometric | Front | Left |
|---|---:|---:|---|---|---|
| Seed broken CAD | 0.635 | - | ![](/Users/sanju/Desktop/coding/python/open-env-meta-final/experiment-2-cadforge/runs/cadquery-env/openai-gpt-5.4-robot_gripper_two_finger-missing_features-2026-04-25T14-39-27-233/seed/renders/isometric.png) | ![](/Users/sanju/Desktop/coding/python/open-env-meta-final/experiment-2-cadforge/runs/cadquery-env/openai-gpt-5.4-robot_gripper_two_finger-missing_features-2026-04-25T14-39-27-233/seed/renders/front.png) | ![](/Users/sanju/Desktop/coding/python/open-env-meta-final/experiment-2-cadforge/runs/cadquery-env/openai-gpt-5.4-robot_gripper_two_finger-missing_features-2026-04-25T14-39-27-233/seed/renders/left.png) |
| Step 1 repair | 0.793 | +0.158 | ![](/Users/sanju/Desktop/coding/python/open-env-meta-final/experiment-2-cadforge/runs/cadquery-env/openai-gpt-5.4-robot_gripper_two_finger-missing_features-2026-04-25T14-39-27-233/step-1/renders/isometric.png) | ![](/Users/sanju/Desktop/coding/python/open-env-meta-final/experiment-2-cadforge/runs/cadquery-env/openai-gpt-5.4-robot_gripper_two_finger-missing_features-2026-04-25T14-39-27-233/step-1/renders/front.png) | ![](/Users/sanju/Desktop/coding/python/open-env-meta-final/experiment-2-cadforge/runs/cadquery-env/openai-gpt-5.4-robot_gripper_two_finger-missing_features-2026-04-25T14-39-27-233/step-1/renders/left.png) |
| Step 2 repair | 0.812 | +0.018 | ![](/Users/sanju/Desktop/coding/python/open-env-meta-final/experiment-2-cadforge/runs/cadquery-env/openai-gpt-5.4-robot_gripper_two_finger-missing_features-2026-04-25T14-39-27-233/step-2/renders/isometric.png) | ![](/Users/sanju/Desktop/coding/python/open-env-meta-final/experiment-2-cadforge/runs/cadquery-env/openai-gpt-5.4-robot_gripper_two_finger-missing_features-2026-04-25T14-39-27-233/step-2/renders/front.png) | ![](/Users/sanju/Desktop/coding/python/open-env-meta-final/experiment-2-cadforge/runs/cadquery-env/openai-gpt-5.4-robot_gripper_two_finger-missing_features-2026-04-25T14-39-27-233/step-2/renders/left.png) |
| Step 3 repair | 0.817 | +0.005 | ![](/Users/sanju/Desktop/coding/python/open-env-meta-final/experiment-2-cadforge/runs/cadquery-env/openai-gpt-5.4-robot_gripper_two_finger-missing_features-2026-04-25T14-39-27-233/step-3/renders/isometric.png) | ![](/Users/sanju/Desktop/coding/python/open-env-meta-final/experiment-2-cadforge/runs/cadquery-env/openai-gpt-5.4-robot_gripper_two_finger-missing_features-2026-04-25T14-39-27-233/step-3/renders/front.png) | ![](/Users/sanju/Desktop/coding/python/open-env-meta-final/experiment-2-cadforge/runs/cadquery-env/openai-gpt-5.4-robot_gripper_two_finger-missing_features-2026-04-25T14-39-27-233/step-3/renders/left.png) |

## How The Reward Model Acts

The reward is not a single judge opinion. It is a weighted verifier made of build success, mesh topology, contact/gaps, task semantics, reference/GLB similarity, silhouette overlap, editability, and efficiency. Build failure is a hard `-1`; otherwise every step gets a component score in `[0, 1]`.

Full-mode total reward is weighted approximately as: build `0.18`, topology `0.17`, contact `0.10`, semantic parts `0.15`, reference similarity `0.15`, silhouette `0.10`, editability `0.10`, efficiency `0.05`.

## Step-by-Step Reward Breakdown

### Step 1

Previous reward: `0.635`
New reward: `0.793`
Delta: `+0.158`

| Component | Score |
|---|---:|
| Build | 1.000 |
| Topology | 1.000 |
| Contact | 1.000 |
| Semantic Parts | 0.379 |
| Reference Similarity | 0.635 |
| Silhouette | 0.587 |
| Editability | 0.825 |
| Efficiency | 1.000 |
| Total | 0.793 |

What changed:
- Editability improved from 0.275 to 0.825; Reference Similarity improved from 0.150 to 0.635; Silhouette improved from 0.376 to 0.587; Topology improved from 0.930 to 1.000.
- Helper functions: 0 -> 3. Named numeric dimensions: 3 -> 22.
- Verifier note: Candidate is weak on robot_gripper_two_finger semantic hints; add/organize recognizable subassemblies in code.

### Step 2

Previous reward: `0.793`
New reward: `0.812`
Delta: `+0.018`

| Component | Score |
|---|---:|
| Build | 1.000 |
| Topology | 1.000 |
| Contact | 1.000 |
| Semantic Parts | 0.392 |
| Reference Similarity | 0.663 |
| Silhouette | 0.592 |
| Editability | 0.942 |
| Efficiency | 1.000 |
| Total | 0.812 |

What changed:
- Editability improved from 0.825 to 0.942; Reference Similarity improved from 0.635 to 0.663; Semantic Parts improved from 0.379 to 0.392; Silhouette improved from 0.587 to 0.592.
- Helper functions: 3 -> 5. Named numeric dimensions: 22 -> 25.
- Verifier note: Candidate is weak on robot_gripper_two_finger semantic hints; add/organize recognizable subassemblies in code.

### Step 3

Previous reward: `0.812`
New reward: `0.817`
Delta: `+0.005`

| Component | Score |
|---|---:|
| Build | 1.000 |
| Topology | 1.000 |
| Contact | 1.000 |
| Semantic Parts | 0.446 |
| Reference Similarity | 0.643 |
| Silhouette | 0.591 |
| Editability | 0.942 |
| Efficiency | 1.000 |
| Total | 0.817 |

What changed:
- Semantic Parts improved from 0.392 to 0.446; Reference Similarity dropped from 0.663 to 0.643; Silhouette dropped from 0.592 to 0.591; Build improved from 1.000 to 1.000.
- Helper functions: 5 -> 5. Named numeric dimensions: 25 -> 26.
- Verifier note: Candidate is weak on robot_gripper_two_finger semantic hints; add/organize recognizable subassemblies in code.

## Updated Code Per Step

<details><summary>Step 1 CadQuery code</summary>

```python
import cadquery as cq

# Simple editable two-finger robot gripper
# Coordinate convention:
# X = finger closing direction
# Y = gripper depth
# Z = vertical / finger length direction

# ----------------------------
# Named dimensions
# ----------------------------
palm_w = 70.0
palm_d = 34.0
palm_h = 20.0

finger_len = 70.0
finger_w = 12.0
finger_t = 12.0
finger_gap = 30.0
finger_base_overlap = 8.0

pad_len = 16.0
pad_w = 10.0
pad_t = 6.0

boss_r = 8.0
boss_len = 14.0
boss_z = 8.0
boss_x_offset = 18.0

link_len = 34.0
link_w = 8.0
link_t = 6.0
link_z = palm_h + 7.0

mount_hole_spacing_x = 34.0
mount_hole_spacing_y = 18.0
mount_hole_r = 2.5

pivot_hole_r = 2.2

# ----------------------------
# Helper builders
# ----------------------------
def make_finger(x_center):
    base_z = palm_h - finger_base_overlap
    body = (
        cq.Workplane("XY")
        .box(finger_w, finger_t, finger_len)
        .translate((x_center, 0, base_z + finger_len / 2.0))
    )

    tip_z = base_z + finger_len - pad_len / 2.0
    pad_x = x_center / abs(x_center) * (finger_w / 2.0 + pad_t / 2.0 - 1.0)
    pad = (
        cq.Workplane("XY")
        .box(pad_t, pad_w, pad_len)
        .translate((x_center - pad_x, 0, tip_z))
    )

    return body.union(pad)

def make_pivot_boss(x_center):
    boss = (
        cq.Workplane("YZ")
        .circle(boss_r)
        .extrude(boss_len)
        .translate((x_center - boss_len / 2.0, 0, boss_z))
    )
    hole = (
        cq.Workplane("YZ")
        .circle(pivot_hole_r)
        .extrude(boss_len + 2.0)
        .translate((x_center - (boss_len + 2.0) / 2.0, 0, boss_z))
    )
    return boss.cut(hole)

def make_link_bar(x0, x1, zc):
    length = abs(x1 - x0)
    center_x = (x0 + x1) / 2.0
    bar = (
        cq.Workplane("XY")
        .box(length, link_w, link_t)
        .translate((center_x, 0, zc))
    )

    hole0 = (
        cq.Workplane("YZ")
        .circle(pivot_hole_r)
        .extrude(link_t + 2.0)
        .translate((x0 - (link_t + 2.0) / 2.0, 0, zc))
    )
    hole1 = (
        cq.Workplane("YZ")
        .circle(pivot_hole_r)
        .extrude(link_t + 2.0)
        .translate((x1 - (link_t + 2.0) / 2.0, 0, zc))
    )
    return bar.cut(hole0).cut(hole1)

# ----------------------------
# Palm block
# ----------------------------
palm = cq.Workplane("XY").box(palm_w, palm_d, palm_h).translate((0, 0, palm_h / 2.0))

# Mounting holes through palm
mount_holes = (
    cq.Workplane("XY")
    .pushPoints([
        (-mount_hole_spacing_x / 2.0, -mount_hole_spacing_y / 2.0),
        (-mount_hole_spacing_x / 2.0,  mount_hole_spacing_y / 2.0),
        ( mount_hole_spacing_x / 2.0, -mount_hole_spacing_y / 2.0),
        ( mount_hole_spacing_x / 2.0,  mount_hole_spacing_y / 2.0),
    ])
    .circle(mount_hole_r)
    .extrude(palm_h + 2.0)
    .translate((0, 0, -1.0))
)
palm = palm.cut(mount_holes)

# ----------------------------
# Fingers
# ----------------------------
left_x = -(finger_gap / 2.0 + finger_w / 2.0)
right_x = (finger_gap / 2.0 + finger_w / 2.0)

left_finger = make_finger(left_x)
right_finger = make_finger(right_x)

# ----------------------------
# Pivot bosses on palm top/front area
# ----------------------------
left_boss = make_pivot_boss(-boss_x_offset)
right_boss = make_pivot_boss(boss_x_offset)

# Secondary bosses near finger bases to suggest linkage attachment
left_finger_boss = make_pivot_boss(left_x)
right_finger_boss = make_pivot_boss(right_x)

# ----------------------------
# Linkage bars
# ----------------------------
left_link = make_link_bar(-boss_x_offset, left_x, link_z)
right_link = make_link_bar(boss_x_offset, right_x, link_z)

center_cross_link = (
    cq.Workplane("XY")
    .box(2.0 * boss_x_offset, link_w, link_t)
    .translate((0, 0, link_z + 8.0))
)

# ----------------------------
# Final assembly
# ----------------------------
fixture = (
    palm
    .union(left_finger)
    .union(right_finger)
    .union(left_boss)
    .union(right_boss)
    .union(left_finger_boss)
    .union(right_finger_boss)
    .union(left_link)
    .union(right_link)
    .union(center_cross_link)
).clean()
```

</details>

<details><summary>Step 2 CadQuery code</summary>

```python
import cadquery as cq

# Editable two-finger robot gripper
# Axes:
# X = jaw opening direction
# Y = gripper depth
# Z = finger length / upward direction

# ----------------------------
# Named dimensions
# ----------------------------
palm_w = 72.0
palm_d = 36.0
palm_h = 18.0

finger_len = 72.0
finger_w = 12.0
finger_t = 12.0
finger_gap = 28.0
finger_base_embed = 10.0

pad_len = 16.0
pad_w = 10.0
pad_t = 6.0
pad_inset = 2.0

boss_r = 7.0
boss_len = 12.0
pivot_hole_r = 2.2

palm_boss_x = 18.0
finger_boss_z = palm_h + 10.0
palm_boss_z = palm_h + 10.0

link_w = 8.0
link_t = 6.0
link_z = palm_h + 10.0

bridge_w = 44.0
bridge_d = 10.0
bridge_t = 6.0
bridge_z = palm_h + 18.0

mount_hole_spacing_x = 36.0
mount_hole_spacing_y = 18.0
mount_hole_r = 2.5

# ----------------------------
# Helper builders
# ----------------------------
def x_cylinder(xc, yc, zc, radius, length):
    return (
        cq.Workplane("YZ")
        .circle(radius)
        .extrude(length)
        .translate((xc - length / 2.0, yc, zc))
    )

def make_boss(xc, yc, zc, radius, length, hole_r):
    boss = x_cylinder(xc, yc, zc, radius, length)
    hole = x_cylinder(xc, yc, zc, hole_r, length + 2.0)
    return boss.cut(hole)

def make_finger(x_center, inward_sign):
    base_center_z = palm_h + (finger_len - finger_base_embed) / 2.0
    body = (
        cq.Workplane("XY")
        .box(finger_w, finger_t, finger_len)
        .translate((x_center, 0, base_center_z))
    )

    finger_boss = make_boss(
        x_center,
        0,
        finger_boss_z,
        boss_r,
        boss_len,
        pivot_hole_r,
    )

    pad_center_x = x_center + inward_sign * (finger_w / 2.0 - pad_t / 2.0 - pad_inset)
    pad_center_z = palm_h + finger_len - pad_len / 2.0
    pad = (
        cq.Workplane("XY")
        .box(pad_t, pad_w, pad_len)
        .translate((pad_center_x, 0, pad_center_z))
    )

    return body.union(finger_boss).union(pad)

def make_link_between_points(x0, z0, x1, z1, y_center=0.0):
    dx = x1 - x0
    dz = z1 - z0
    length = (dx * dx + dz * dz) ** 0.5
    angle = 0.0
    if length > 1e-6:
        angle = degrees_from_radians(dz, dx)

    bar = (
        cq.Workplane("XY")
        .box(length, link_w, link_t)
        .rotate((0, 0, 0), (0, 1, 0), angle)
        .translate(((x0 + x1) / 2.0, y_center, (z0 + z1) / 2.0))
    )

    hole0 = x_cylinder(x0, y_center, z0, pivot_hole_r, link_t + 2.0)
    hole1 = x_cylinder(x1, y_center, z1, pivot_hole_r, link_t + 2.0)
    return bar.cut(hole0).cut(hole1)

def degrees_from_radians(dz, dx):
    import math
    return math.degrees(math.atan2(dz, dx))

# ----------------------------
# Main reference positions
# ----------------------------
left_x = -(finger_gap / 2.0 + finger_w / 2.0)
right_x = (finger_gap / 2.0 + finger_w / 2.0)

left_palm_boss_x = -palm_boss_x
right_palm_boss_x = palm_boss_x

# ----------------------------
# Palm block
# ----------------------------
palm = cq.Workplane("XY").box(palm_w, palm_d, palm_h).translate((0, 0, palm_h / 2.0))

mount_holes = (
    cq.Workplane("XY")
    .pushPoints([
        (-mount_hole_spacing_x / 2.0, -mount_hole_spacing_y / 2.0),
        (-mount_hole_spacing_x / 2.0,  mount_hole_spacing_y / 2.0),
        ( mount_hole_spacing_x / 2.0, -mount_hole_spacing_y / 2.0),
        ( mount_hole_spacing_x / 2.0,  mount_hole_spacing_y / 2.0),
    ])
    .circle(mount_hole_r)
    .extrude(palm_h + 2.0)
    .translate((0, 0, -1.0))
)
palm = palm.cut(mount_holes)

# Add a top bridge block to emphasize the gripper head / actuator region
top_bridge = (
    cq.Workplane("XY")
    .box(bridge_w, bridge_d, bridge_t)
    .translate((0, 0, bridge_z))
)

# ----------------------------
# Palm pivot bosses
# ----------------------------
left_palm_boss = make_boss(left_palm_boss_x, 0, palm_boss_z, boss_r, boss_len, pivot_hole_r)
right_palm_boss = make_boss(right_palm_boss_x, 0, palm_boss_z, boss_r, boss_len, pivot_hole_r)

# ----------------------------
# Fingers with integrated finger bosses and pads
# ----------------------------
left_finger = make_finger(left_x, 1.0)
right_finger = make_finger(right_x, -1.0)

# ----------------------------
# Linkage bars
# ----------------------------
left_link = make_link_between_points(left_palm_boss_x, palm_boss_z, left_x, finger_boss_z)
right_link = make_link_between_points(right_palm_boss_x, palm_boss_z, right_x, finger_boss_z)

upper_cross_link = (
    cq.Workplane("XY")
    .box(2.0 * palm_boss_x, link_w, link_t)
    .translate((0, 0, bridge_z))
)

# Vertical support posts between palm and bridge for clearer semantics
left_support = (
    cq.Workplane("XY")
    .box(8.0, 8.0, bridge_z - palm_h)
    .translate((left_palm_boss_x, 0, palm_h + (bridge_z - palm_h) / 2.0))
)
right_support = (
    cq.Workplane("XY")
    .box(8.0, 8.0, bridge_z - palm_h)
    .translate((right_palm_boss_x, 0, palm_h + (bridge_z - palm_h) / 2.0))
)

# ----------------------------
# Final assembly
# ----------------------------
fixture = (
    palm
    .union(top_bridge)
    .union(left_palm_boss)
    .union(right_palm_boss)
    .union(left_support)
    .union(right_support)
    .union(left_finger)
    .union(right_finger)
    .union(left_link)
    .union(right_link)
    .union(upper_cross_link)
).clean()
```

</details>

<details><summary>Step 3 CadQuery code</summary>

```python
import cadquery as cq
import math

# Simple editable two-finger robot gripper
# Axes:
# X = finger opening direction
# Y = gripper depth
# Z = finger length / upward direction

# ----------------------------
# Named dimensions
# ----------------------------
palm_w = 74.0
palm_d = 38.0
palm_h = 18.0

mount_hole_spacing_x = 40.0
mount_hole_spacing_y = 20.0
mount_hole_r = 2.6

finger_len = 78.0
finger_w = 12.0
finger_t = 12.0
finger_gap = 28.0
finger_base_overlap = 8.0

pad_len = 18.0
pad_w = 10.0
pad_t = 6.0
pad_inset = 1.5

boss_r = 7.0
boss_len = 12.0
pivot_hole_r = 2.2

palm_pivot_x = 18.0
palm_pivot_z = palm_h + 10.0

finger_pivot_z = palm_h + 12.0
link_w = 8.0
link_t = 6.0

actuator_bridge_w = 42.0
actuator_bridge_d = 12.0
actuator_bridge_t = 8.0
actuator_bridge_z = palm_h + 24.0

support_post_w = 8.0
support_post_d = 8.0

# ----------------------------
# Helpers
# ----------------------------
def x_cylinder(center_x, center_y, center_z, radius, length):
    return (
        cq.Workplane("YZ")
        .circle(radius)
        .extrude(length)
        .translate((center_x - length / 2.0, center_y, center_z))
    )

def make_boss(center_x, center_y, center_z, radius, length, hole_r):
    outer = x_cylinder(center_x, center_y, center_z, radius, length)
    hole = x_cylinder(center_x, center_y, center_z, hole_r, length + 2.0)
    return outer.cut(hole)

def angle_deg(x0, z0, x1, z1):
    return math.degrees(math.atan2(z1 - z0, x1 - x0))

def make_link_bar(x0, z0, x1, z1, y_center=0.0):
    length = ((x1 - x0) ** 2 + (z1 - z0) ** 2) ** 0.5
    bar = (
        cq.Workplane("XY")
        .box(length, link_w, link_t)
        .rotate((0, 0, 0), (0, 1, 0), angle_deg(x0, z0, x1, z1))
        .translate(((x0 + x1) / 2.0, y_center, (z0 + z1) / 2.0))
    )

    end_pad0 = (
        cq.Workplane("XY")
        .box(link_t, link_w + 4.0, link_t)
        .translate((x0, y_center, z0))
    )
    end_pad1 = (
        cq.Workplane("XY")
        .box(link_t, link_w + 4.0, link_t)
        .translate((x1, y_center, z1))
    )

    hole0 = x_cylinder(x0, y_center, z0, pivot_hole_r, link_t + 2.0)
    hole1 = x_cylinder(x1, y_center, z1, pivot_hole_r, link_t + 2.0)

    return bar.union(end_pad0).union(end_pad1).cut(hole0).cut(hole1)

def make_finger(x_center, inward_sign):
    finger_center_z = palm_h + (finger_len / 2.0) - finger_base_overlap

    body = (
        cq.Workplane("XY")
        .box(finger_w, finger_t, finger_len)
        .translate((x_center, 0, finger_center_z))
    )

    pivot_boss = make_boss(
        x_center,
        0,
        finger_pivot_z,
        boss_r,
        boss_len,
        pivot_hole_r,
    )

    tip_z = palm_h + finger_len - finger_base_overlap - pad_len / 2.0
    pad_x = x_center + inward_sign * (finger_w / 2.0 - pad_t / 2.0 - pad_inset)
    tip_pad = (
        cq.Workplane("XY")
        .box(pad_t, pad_w, pad_len)
        .translate((pad_x, 0, tip_z))
    )

    return body.union(pivot_boss).union(tip_pad)

# ----------------------------
# Layout positions
# ----------------------------
left_finger_x = -(finger_gap / 2.0 + finger_w / 2.0)
right_finger_x = (finger_gap / 2.0 + finger_w / 2.0)

left_palm_pivot_x = -palm_pivot_x
right_palm_pivot_x = palm_pivot_x

# ----------------------------
# Palm block with mounting holes
# ----------------------------
palm = cq.Workplane("XY").box(palm_w, palm_d, palm_h).translate((0, 0, palm_h / 2.0))

mount_holes = (
    cq.Workplane("XY")
    .pushPoints(
        [
            (-mount_hole_spacing_x / 2.0, -mount_hole_spacing_y / 2.0),
            (-mount_hole_spacing_x / 2.0, mount_hole_spacing_y / 2.0),
            (mount_hole_spacing_x / 2.0, -mount_hole_spacing_y / 2.0),
            (mount_hole_spacing_x / 2.0, mount_hole_spacing_y / 2.0),
        ]
    )
    .circle(mount_hole_r)
    .extrude(palm_h + 2.0)
    .translate((0, 0, -1.0))
)
palm = palm.cut(mount_holes)

# Front jaw carrier ridge for stronger gripper semantics
jaw_carrier = (
    cq.Workplane("XY")
    .box(palm_w * 0.72, palm_d * 0.42, 8.0)
    .translate((0, 0, palm_h + 4.0))
)

# Palm pivot bosses
left_palm_boss = make_boss(left_palm_pivot_x, 0, palm_pivot_z, boss_r, boss_len, pivot_hole_r)
right_palm_boss = make_boss(right_palm_pivot_x, 0, palm_pivot_z, boss_r, boss_len, pivot_hole_r)

# Fingers
left_finger = make_finger(left_finger_x, 1.0)
right_finger = make_finger(right_finger_x, -1.0)

# Linkage bars from palm bosses to finger bosses
left_link = make_link_bar(left_palm_pivot_x, palm_pivot_z, left_finger_x, finger_pivot_z)
right_link = make_link_bar(right_palm_pivot_x, palm_pivot_z, right_finger_x, finger_pivot_z)

# Upper actuator region
actuator_bridge = (
    cq.Workplane("XY")
    .box(actuator_bridge_w, actuator_bridge_d, actuator_bridge_t)
    .translate((0, 0, actuator_bridge_z))
)

center_actuator_block = (
    cq.Workplane("XY")
    .box(18.0, 18.0, 16.0)
    .translate((0, 0, palm_h + 16.0))
)

left_support = (
    cq.Workplane("XY")
    .box(support_post_w, support_post_d, actuator_bridge_z - palm_h)
    .translate(
        (
            left_palm_pivot_x,
            0,
            palm_h + (actuator_bridge_z - palm_h) / 2.0,
        )
    )
)

right_support = (
    cq.Workplane("XY")
    .box(support_post_w, support_post_d, actuator_bridge_z - palm_h)
    .translate(
        (
            right_palm_pivot_x,
            0,
            palm_h + (actuator_bridge_z - palm_h) / 2.0,
        )
    )
)

cross_link = (
    cq.Workplane("XY")
    .box(2.0 * palm_pivot_x + boss_len, link_w, link_t)
    .translate((0, 0, actuator_bridge_z))
)

# ----------------------------
# Final assembly
# ----------------------------
fixture = (
    palm
    .union(jaw_carrier)
    .union(left_palm_boss)
    .union(right_palm_boss)
    .union(left_finger)
    .union(right_finger)
    .union(left_link)
    .union(right_link)
    .union(left_support)
    .union(right_support)
    .union(actuator_bridge)
    .union(center_actuator_block)
    .union(cross_link)
).clean()
```

</details>