# GPT-5.4 Agentic CAD Repair: Four-Leg Chair

Trace: `openai-gpt-5.4-four_leg_chair_700n-disconnected-2026-04-25T14-03-09-167Z`
Model: `gpt-5.4`
Vision feedback: `no`
Seed mode: `disconnected`

## Input Prompt

Build a simple four-legged chair as editable code-CAD. It must support a 700 N seated load, include a seat panel, four connected legs, lower crossbars, and a backrest, fit inside a 500 mm x 500 mm x 900 mm envelope, and avoid floating parts.

Additional teacher-data variant: prioritize clean editable CadQuery with named dimensions and helper functions, then improve silhouette/contact against the reference. Make a different repair strategy from previous attempts.

## Task Spec

- Task id: `four_leg_chair_700n`
- Family: `furniture`
- Difficulty: `easy`
- Semantic hints: `seat`, `four_leg`, `leg`, `crossbar`, `backrest`, `connected`, `load_700n`
- Target bbox profile: `500 x 500 x 900 mm`

## Primary Creation Stage

The seed starts as a disconnected furniture-like assembly: a blocky seat/back and one separated support. The agent must turn it into an editable chair with four legs, crossbars, and a backrest while matching the generated GLB reference.

The environment evaluates the current code, saves renders/STL/reward JSON, sends the model the previous code plus verifier feedback, then evaluates the revised CadQuery file. Each row below is one full observe -> edit -> score step.

| State | Reward | Delta | Isometric | Front | Left |
|---|---:|---:|---|---|---|
| Seed broken CAD | 0.441 | - | ![](/Users/sanju/Desktop/coding/python/open-env-meta-final/experiment-2-cadforge/runs/cadquery-env/openai-gpt-5.4-four_leg_chair_700n-disconnected-2026-04-25T14-03-09-167Z/seed/renders/isometric.png) | ![](/Users/sanju/Desktop/coding/python/open-env-meta-final/experiment-2-cadforge/runs/cadquery-env/openai-gpt-5.4-four_leg_chair_700n-disconnected-2026-04-25T14-03-09-167Z/seed/renders/front.png) | ![](/Users/sanju/Desktop/coding/python/open-env-meta-final/experiment-2-cadforge/runs/cadquery-env/openai-gpt-5.4-four_leg_chair_700n-disconnected-2026-04-25T14-03-09-167Z/seed/renders/left.png) |
| Step 1 repair | 0.802 | +0.361 | ![](/Users/sanju/Desktop/coding/python/open-env-meta-final/experiment-2-cadforge/runs/cadquery-env/openai-gpt-5.4-four_leg_chair_700n-disconnected-2026-04-25T14-03-09-167Z/step-1/renders/isometric.png) | ![](/Users/sanju/Desktop/coding/python/open-env-meta-final/experiment-2-cadforge/runs/cadquery-env/openai-gpt-5.4-four_leg_chair_700n-disconnected-2026-04-25T14-03-09-167Z/step-1/renders/front.png) | ![](/Users/sanju/Desktop/coding/python/open-env-meta-final/experiment-2-cadforge/runs/cadquery-env/openai-gpt-5.4-four_leg_chair_700n-disconnected-2026-04-25T14-03-09-167Z/step-1/renders/left.png) |
| Step 2 repair | 0.806 | +0.005 | ![](/Users/sanju/Desktop/coding/python/open-env-meta-final/experiment-2-cadforge/runs/cadquery-env/openai-gpt-5.4-four_leg_chair_700n-disconnected-2026-04-25T14-03-09-167Z/step-2/renders/isometric.png) | ![](/Users/sanju/Desktop/coding/python/open-env-meta-final/experiment-2-cadforge/runs/cadquery-env/openai-gpt-5.4-four_leg_chair_700n-disconnected-2026-04-25T14-03-09-167Z/step-2/renders/front.png) | ![](/Users/sanju/Desktop/coding/python/open-env-meta-final/experiment-2-cadforge/runs/cadquery-env/openai-gpt-5.4-four_leg_chair_700n-disconnected-2026-04-25T14-03-09-167Z/step-2/renders/left.png) |
| Step 3 repair | 0.822 | +0.016 | ![](/Users/sanju/Desktop/coding/python/open-env-meta-final/experiment-2-cadforge/runs/cadquery-env/openai-gpt-5.4-four_leg_chair_700n-disconnected-2026-04-25T14-03-09-167Z/step-3/renders/isometric.png) | ![](/Users/sanju/Desktop/coding/python/open-env-meta-final/experiment-2-cadforge/runs/cadquery-env/openai-gpt-5.4-four_leg_chair_700n-disconnected-2026-04-25T14-03-09-167Z/step-3/renders/front.png) | ![](/Users/sanju/Desktop/coding/python/open-env-meta-final/experiment-2-cadforge/runs/cadquery-env/openai-gpt-5.4-four_leg_chair_700n-disconnected-2026-04-25T14-03-09-167Z/step-3/renders/left.png) |

## How The Reward Model Acts

The reward is not a single judge opinion. It is a weighted verifier made of build success, mesh topology, contact/gaps, task semantics, reference/GLB similarity, silhouette overlap, editability, and efficiency. Build failure is a hard `-1`; otherwise every step gets a component score in `[0, 1]`.

Full-mode total reward is weighted approximately as: build `0.18`, topology `0.17`, contact `0.10`, semantic parts `0.15`, reference similarity `0.15`, silhouette `0.10`, editability `0.10`, efficiency `0.05`.

## Step-by-Step Reward Breakdown

### Step 1

Previous reward: `0.441`
New reward: `0.802`
Delta: `+0.361`

| Component | Score |
|---|---:|
| Build | 1.000 |
| Topology | 1.000 |
| Contact | 1.000 |
| Semantic Parts | 0.707 |
| Reference Similarity | 0.562 |
| Silhouette | 0.405 |
| Editability | 0.708 |
| Efficiency | 1.000 |
| Total | 0.802 |

What changed:
- Contact improved from 0.000 to 1.000; Semantic Parts improved from 0.050 to 0.707; Reference Similarity improved from 0.035 to 0.562; Editability improved from 0.200 to 0.708.
- Helper functions: 0 -> 1. Named numeric dimensions: 0 -> 14.
- Verifier note: Candidate built and scored successfully.

### Step 2

Previous reward: `0.802`
New reward: `0.806`
Delta: `+0.005`

| Component | Score |
|---|---:|
| Build | 1.000 |
| Topology | 1.000 |
| Contact | 1.000 |
| Semantic Parts | 0.727 |
| Reference Similarity | 0.537 |
| Silhouette | 0.401 |
| Editability | 0.767 |
| Efficiency | 1.000 |
| Total | 0.806 |

What changed:
- Editability improved from 0.708 to 0.767; Reference Similarity dropped from 0.562 to 0.537; Semantic Parts improved from 0.707 to 0.727; Silhouette dropped from 0.405 to 0.401.
- Helper functions: 1 -> 2. Named numeric dimensions: 14 -> 25.
- Verifier note: Candidate built and scored successfully.

### Step 3

Previous reward: `0.806`
New reward: `0.822`
Delta: `+0.016`

| Component | Score |
|---|---:|
| Build | 1.000 |
| Topology | 1.000 |
| Contact | 1.000 |
| Semantic Parts | 0.747 |
| Reference Similarity | 0.540 |
| Silhouette | 0.406 |
| Editability | 0.883 |
| Efficiency | 1.000 |
| Total | 0.822 |

What changed:
- Editability improved from 0.767 to 0.883; Semantic Parts improved from 0.727 to 0.747; Silhouette improved from 0.401 to 0.406; Reference Similarity improved from 0.537 to 0.540.
- Helper functions: 2 -> 4. Named numeric dimensions: 25 -> 27.
- Verifier note: Candidate built and scored successfully.

## Updated Code Per Step

<details><summary>Step 1 CadQuery code</summary>

```python
import cadquery as cq

# Simple four-legged chair sized to fit within a 500 x 500 x 900 mm envelope.
# Dimensions are chosen to produce a recognizable, connected, and editable chair.

seat_width = 420
seat_depth = 420
seat_thickness = 22
seat_top_z = 450
seat_bottom_z = seat_top_z - seat_thickness

leg_size = 36
leg_height = seat_bottom_z

leg_inset_x = 36
leg_inset_y = 36

crossbar_thickness = 24
crossbar_height = 18
lower_crossbar_z = 150

back_post_height_above_seat = 380
back_post_total_height = seat_top_z + back_post_height_above_seat
backrest_thickness = 22
backrest_height = 160
backrest_width = seat_width - 2 * leg_inset_x + leg_size
backrest_bottom_z = seat_top_z + 170

side_top_rail_height = 24
side_top_rail_z = seat_top_z + 130

def box_centered(x, y, z, center):
    return cq.Workplane("XY").box(x, y, z).translate(center)

chair = cq.Workplane("XY")

# Seat panel
seat = box_centered(
    seat_width,
    seat_depth,
    seat_thickness,
    (0, 0, seat_bottom_z + seat_thickness / 2),
)
chair = chair.union(seat)

# Leg positions
leg_x = seat_width / 2 - leg_inset_x - leg_size / 2
leg_y = seat_depth / 2 - leg_inset_y - leg_size / 2

leg_positions = [
    (-leg_x, -leg_y),  # front-left
    ( leg_x, -leg_y),  # front-right
    (-leg_x,  leg_y),  # back-left
    ( leg_x,  leg_y),  # back-right
]

# Four legs connected up to underside of seat
for x, y in leg_positions:
    leg = box_centered(leg_size, leg_size, leg_height, (x, y, leg_height / 2))
    chair = chair.union(leg)

# Lower front and back crossbars
front_crossbar = box_centered(
    seat_width - 2 * leg_inset_x - leg_size,
    crossbar_thickness,
    crossbar_height,
    (0, -leg_y, lower_crossbar_z),
)
back_lower_crossbar = box_centered(
    seat_width - 2 * leg_inset_x - leg_size,
    crossbar_thickness,
    crossbar_height,
    (0, leg_y, lower_crossbar_z),
)
chair = chair.union(front_crossbar).union(back_lower_crossbar)

# Lower left and right side crossbars
left_crossbar = box_centered(
    crossbar_thickness,
    seat_depth - 2 * leg_inset_y - leg_size,
    crossbar_height,
    (-leg_x, 0, lower_crossbar_z),
)
right_crossbar = box_centered(
    crossbar_thickness,
    seat_depth - 2 * leg_inset_y - leg_size,
    crossbar_height,
    (leg_x, 0, lower_crossbar_z),
)
chair = chair.union(left_crossbar).union(right_crossbar)

# Back posts continue above the seat using the rear legs for a connected backrest structure
for x in (-leg_x, leg_x):
    back_post = box_centered(
        leg_size,
        leg_size,
        back_post_height_above_seat,
        (x, leg_y, seat_top_z + back_post_height_above_seat / 2),
    )
    chair = chair.union(back_post)

# Backrest panel between rear posts
backrest = box_centered(
    backrest_width,
    backrest_thickness,
    backrest_height,
    (0, leg_y, backrest_bottom_z + backrest_height / 2),
)
chair = chair.union(backrest)

# Upper side rails to visually connect seat to back posts and improve silhouette/contact
left_top_rail = box_centered(
    crossbar_thickness,
    seat_depth - 2 * leg_inset_y - leg_size,
    side_top_rail_height,
    (-leg_x, 0, side_top_rail_z),
)
right_top_rail = box_centered(
    crossbar_thickness,
    seat_depth - 2 * leg_inset_y - leg_size,
    side_top_rail_height,
    (leg_x, 0, side_top_rail_z),
)
chair = chair.union(left_top_rail).union(right_top_rail)

fixture = chair.clean()
```

</details>

<details><summary>Step 2 CadQuery code</summary>

```python
import cadquery as cq

# Editable four-legged chair with connected structure, sized within 500 x 500 x 900 mm.
# Repair strategy:
# - keep a simple box-built topology for reliability
# - improve silhouette with a thinner seat, taller back, and a visible apron under the seat
# - increase semantic clarity by using rear legs as continuous back posts
# - ensure all parts overlap or touch intentionally

# -----------------------------
# Named dimensions
# -----------------------------
envelope_x = 500
envelope_y = 500
envelope_z = 900

seat_width = 420
seat_depth = 400
seat_thickness = 20
seat_top_z = 450
seat_bottom_z = seat_top_z - seat_thickness

leg_size = 38
leg_height = seat_bottom_z

leg_inset_x = 34
leg_inset_y = 34

apron_height = 70
apron_thickness = 24
apron_top_z = seat_bottom_z
apron_center_z = apron_top_z - apron_height / 2

lower_crossbar_height = 22
lower_crossbar_thickness = 24
lower_crossbar_z = 155

back_post_extension = 400
back_top_z = seat_top_z + back_post_extension

backrest_width = 300
backrest_height = 190
backrest_thickness = 22
backrest_bottom_z = 610

upper_back_rail_height = 36
upper_back_rail_thickness = 22
upper_back_rail_z = 800

# -----------------------------
# Helpers
# -----------------------------
def centered_box(x, y, z, center):
    return cq.Workplane("XY").box(x, y, z).translate(center)

def add_part(base, part):
    return base.union(part)

# -----------------------------
# Derived placement
# -----------------------------
leg_x = seat_width / 2 - leg_inset_x - leg_size / 2
leg_y = seat_depth / 2 - leg_inset_y - leg_size / 2

front_y = -leg_y
back_y = leg_y
left_x = -leg_x
right_x = leg_x

inner_span_x = 2 * leg_x
inner_span_y = 2 * leg_y

# -----------------------------
# Build chair
# -----------------------------
chair = cq.Workplane("XY")

# Seat panel
seat = centered_box(
    seat_width,
    seat_depth,
    seat_thickness,
    (0, 0, seat_bottom_z + seat_thickness / 2),
)
chair = add_part(chair, seat)

# Four legs; rear legs continue upward later as back posts
for x, y in [(left_x, front_y), (right_x, front_y), (left_x, back_y), (right_x, back_y)]:
    leg = centered_box(leg_size, leg_size, leg_height, (x, y, leg_height / 2))
    chair = add_part(chair, leg)

# Seat apron under seat for stronger visual/support structure
front_apron = centered_box(
    inner_span_x + leg_size,
    apron_thickness,
    apron_height,
    (0, front_y, apron_center_z),
)
back_apron = centered_box(
    inner_span_x + leg_size,
    apron_thickness,
    apron_height,
    (0, back_y, apron_center_z),
)
left_apron = centered_box(
    apron_thickness,
    inner_span_y + leg_size,
    apron_height,
    (left_x, 0, apron_center_z),
)
right_apron = centered_box(
    apron_thickness,
    inner_span_y + leg_size,
    apron_height,
    (right_x, 0, apron_center_z),
)
chair = add_part(chair, front_apron)
chair = add_part(chair, back_apron)
chair = add_part(chair, left_apron)
chair = add_part(chair, right_apron)

# Lower crossbars between legs
front_lower = centered_box(
    inner_span_x + leg_size,
    lower_crossbar_thickness,
    lower_crossbar_height,
    (0, front_y, lower_crossbar_z),
)
back_lower = centered_box(
    inner_span_x + leg_size,
    lower_crossbar_thickness,
    lower_crossbar_height,
    (0, back_y, lower_crossbar_z),
)
left_lower = centered_box(
    lower_crossbar_thickness,
    inner_span_y + leg_size,
    lower_crossbar_height,
    (left_x, 0, lower_crossbar_z),
)
right_lower = centered_box(
    lower_crossbar_thickness,
    inner_span_y + leg_size,
    lower_crossbar_height,
    (right_x, 0, lower_crossbar_z),
)
chair = add_part(chair, front_lower)
chair = add_part(chair, back_lower)
chair = add_part(chair, left_lower)
chair = add_part(chair, right_lower)

# Rear leg extensions as back posts
rear_post_height = back_top_z - seat_bottom_z
rear_post_center_z = seat_bottom_z + rear_post_height / 2
for x in (left_x, right_x):
    post = centered_box(
        leg_size,
        leg_size,
        rear_post_height,
        (x, back_y, rear_post_center_z),
    )
    chair = add_part(chair, post)

# Backrest panel placed between rear posts
backrest = centered_box(
    backrest_width,
    backrest_thickness,
    backrest_height,
    (0, back_y, backrest_bottom_z + backrest_height / 2),
)
chair = add_part(chair, backrest)

# Top back rail to strengthen silhouette and contact with posts
top_back_rail = centered_box(
    inner_span_x + leg_size,
    upper_back_rail_thickness,
    upper_back_rail_height,
    (0, back_y, upper_back_rail_z),
)
chair = add_part(chair, top_back_rail)

fixture = chair.clean()
```

</details>

<details><summary>Step 3 CadQuery code</summary>

```python
import cadquery as cq

# Simple editable four-legged chair sized within a 500 x 500 x 900 mm envelope.
# Revised strategy:
# - use continuous rear legs as back posts for a clearer chair silhouette
# - add a wider/taller backrest assembly with side supports to better match reference semantics
# - keep all parts orthogonal, overlapping, and robust for reliable generation/editing

# -----------------------------
# Named dimensions
# -----------------------------
envelope_x = 500
envelope_y = 500
envelope_z = 900

seat_width = 420
seat_depth = 400
seat_thickness = 22
seat_top_z = 450
seat_bottom_z = seat_top_z - seat_thickness

leg_size = 36
front_leg_height = seat_bottom_z
rear_leg_total_height = 840

leg_inset_x = 34
leg_inset_y = 34

apron_height = 72
apron_thickness = 22
apron_top_z = seat_bottom_z
apron_center_z = apron_top_z - apron_height / 2

lower_rail_height = 20
lower_rail_thickness = 22
side_lower_rail_z = 150
front_back_lower_rail_z = 170

back_panel_width = 320
back_panel_height = 220
back_panel_thickness = 20
back_panel_bottom_z = 560

back_side_slat_width = 42
back_side_slat_thickness = 22
back_side_slat_bottom_z = seat_top_z - 10
back_side_slat_top_z = 760

top_rail_height = 34
top_rail_thickness = 24
top_rail_center_z = 805

# -----------------------------
# Helpers
# -----------------------------
def centered_box(x, y, z, center):
    return cq.Workplane("XY").box(x, y, z).translate(center)

def union_part(base, part):
    return base.union(part)

def rail_x(length, y_pos, z_pos, thickness, height):
    return centered_box(length, thickness, height, (0, y_pos, z_pos))

def rail_y(length, x_pos, z_pos, thickness, height):
    return centered_box(thickness, length, height, (x_pos, 0, z_pos))

# -----------------------------
# Derived placement
# -----------------------------
leg_x = seat_width / 2 - leg_inset_x - leg_size / 2
leg_y = seat_depth / 2 - leg_inset_y - leg_size / 2

left_x = -leg_x
right_x = leg_x
front_y = -leg_y
back_y = leg_y

span_x = right_x - left_x
span_y = back_y - front_y

# -----------------------------
# Build chair
# -----------------------------
chair = cq.Workplane("XY")

# Seat
seat = centered_box(
    seat_width,
    seat_depth,
    seat_thickness,
    (0, 0, seat_bottom_z + seat_thickness / 2),
)
chair = union_part(chair, seat)

# Front legs
for x in (left_x, right_x):
    front_leg = centered_box(
        leg_size,
        leg_size,
        front_leg_height,
        (x, front_y, front_leg_height / 2),
    )
    chair = union_part(chair, front_leg)

# Rear legs continuing into back posts
for x in (left_x, right_x):
    rear_leg = centered_box(
        leg_size,
        leg_size,
        rear_leg_total_height,
        (x, back_y, rear_leg_total_height / 2),
    )
    chair = union_part(chair, rear_leg)

# Upper apron under seat
chair = union_part(
    chair,
    rail_x(span_x + leg_size, front_y, apron_center_z, apron_thickness, apron_height),
)
chair = union_part(
    chair,
    rail_x(span_x + leg_size, back_y, apron_center_z, apron_thickness, apron_height),
)
chair = union_part(
    chair,
    rail_y(span_y + leg_size, left_x, apron_center_z, apron_thickness, apron_height),
)
chair = union_part(
    chair,
    rail_y(span_y + leg_size, right_x, apron_center_z, apron_thickness, apron_height),
)

# Lower crossbars
chair = union_part(
    chair,
    rail_x(span_x + leg_size, front_y, front_back_lower_rail_z, lower_rail_thickness, lower_rail_height),
)
chair = union_part(
    chair,
    rail_x(span_x + leg_size, back_y, front_back_lower_rail_z, lower_rail_thickness, lower_rail_height),
)
chair = union_part(
    chair,
    rail_y(span_y + leg_size, left_x, side_lower_rail_z, lower_rail_thickness, lower_rail_height),
)
chair = union_part(
    chair,
    rail_y(span_y + leg_size, right_x, side_lower_rail_z, lower_rail_thickness, lower_rail_height),
)

# Backrest side slats to strengthen silhouette and semantics
back_side_slat_height = back_side_slat_top_z - back_side_slat_bottom_z
back_side_slat_center_z = back_side_slat_bottom_z + back_side_slat_height / 2
for x in (left_x + 18, right_x - 18):
    side_slat = centered_box(
        back_side_slat_width,
        back_side_slat_thickness,
        back_side_slat_height,
        (x, back_y, back_side_slat_center_z),
    )
    chair = union_part(chair, side_slat)

# Main backrest panel
back_panel = centered_box(
    back_panel_width,
    back_panel_thickness,
    back_panel_height,
    (0, back_y, back_panel_bottom_z + back_panel_height / 2),
)
chair = union_part(chair, back_panel)

# Top rail tying posts together
top_rail = centered_box(
    span_x + leg_size,
    top_rail_thickness,
    top_rail_height,
    (0, back_y, top_rail_center_z),
)
chair = union_part(chair, top_rail)

fixture = chair.clean()
```

</details>