import cadquery as cq

# 12-slot axial motor stator concept
# Compact steel stator ring with visible radial teeth and center shaft opening.

# ----------------------------
# Named dimensions
# ----------------------------
slot_count = 12

outer_diameter = 120.0
inner_diameter = 44.0
shaft_hole_diameter = 22.0

stator_thickness = 8.0

tooth_radial_length = 18.0
tooth_arc_width = 12.0
tooth_root_inner_radius = 28.0

back_iron_outer_radius = outer_diameter / 2.0
back_iron_inner_radius = inner_diameter / 2.0

tooth_tip_radius = back_iron_outer_radius - 2.0
tooth_base_radius = tooth_root_inner_radius

# Derived
tooth_center_radius = (tooth_base_radius + tooth_tip_radius) / 2.0
tooth_half_width = tooth_arc_width / 2.0

# ----------------------------
# Helper builders
# ----------------------------
def make_back_iron_ring():
    outer = cq.Workplane("XY").circle(back_iron_outer_radius).extrude(stator_thickness)
    inner = cq.Workplane("XY").circle(back_iron_inner_radius).extrude(stator_thickness)
    return outer.cut(inner)


def make_radial_tooth(angle_deg):
    # Tooth extends radially inward from the outer ring toward the center opening.
    tooth = (
        cq.Workplane("XY")
        .center(tooth_center_radius, 0)
        .rect(tooth_radial_length, tooth_arc_width)
        .extrude(stator_thickness)
        .rotate((0, 0, 0), (0, 0, 1), angle_deg)
    )
    return tooth


def make_slot_window():
    # Axial slots cut through the stator thickness, leaving the teeth and ring visible.
    slot_radius = inner_diameter / 2.0 + tooth_radial_length * 0.55
    slot_width = 5.0
    slots = None
    for i in range(slot_count):
        angle = 360.0 * i / slot_count
        slot = (
            cq.Workplane("XY")
            .center(slot_radius, 0)
            .rect(slot_width, stator_thickness + 2.0)
            .extrude(stator_thickness)
            .rotate((0, 0, 0), (0, 0, 1), angle)
        )
        slots = slot if slots is None else slots.union(slot)
    return slots


# ----------------------------
# Build stator
# ----------------------------
back_iron = make_back_iron_ring()

teeth = None
for i in range(slot_count):
    angle = 360.0 * i / slot_count
    tooth = make_radial_tooth(angle)
    teeth = tooth if teeth is None else teeth.union(tooth)

stator = back_iron.union(teeth)

# Cut axial slots between teeth
stator = stator.cut(make_slot_window())

# Center shaft opening
shaft_hole = (
    cq.Workplane("XY")
    .circle(shaft_hole_diameter / 2.0)
    .extrude(stator_thickness + 2.0)
)

fixture = stator.cut(shaft_hole).clean()