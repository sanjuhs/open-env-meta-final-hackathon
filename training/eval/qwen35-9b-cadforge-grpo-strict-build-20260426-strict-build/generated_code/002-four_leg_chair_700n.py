import cadquery as cq

# Simple editable four-legged chair
# Strategy:
# - keep a compact 500 x 500 x 900 mm envelope
# - use a clear chair silhouette: seat, four legs, lower crossbars, and backrest
# - ensure all parts overlap or touch so nothing floats
# - make dimensions named and helper-based for easy editing

# Overall envelope targets
seat_width = 420.0
seat_depth = 420.0
seat_thickness = 24.0
seat_top_z = 450.0
seat_center_z = seat_top_z - seat_thickness / 2.0

# Leg geometry
leg_size = 34.0
leg_height = seat_top_z
leg_center_z = leg_height / 2.0

# Leg placement: slightly inset from seat edges for a more chair-like silhouette
leg_inset_x = 28.0
leg_inset_y = 28.0
leg_x = seat_width / 2.0 - leg_size / 2.0 - leg_inset_x
leg_y = seat_depth / 2.0 - leg_size / 2.0 - leg_inset_y

# Lower crossbars
lower_bar_z = 145.0
lower_bar_thickness = 22.0
lower_bar_length_x = 2 * leg_x
lower_bar_length_y = 2 * leg_y

# Seat support rails under the seat
rail_height = 18.0
rail_thickness = 20.0
rail_z = seat_center_z - rail_height / 2.0 - 4.0
rail_inset_x = 20.0
rail_inset_y = 20.0
rail_length_x = 2 * (leg_x - rail_inset_x)
rail_length_y = 2 * (leg_y - rail_inset_y)

# Backrest
back_post_height = 260.0
back_post_width = 34.0
back_post_thickness = 24.0
back_post_center_z = seat_top_z + back_post_height / 2.0 - 10.0
back_post_x = leg_x
back_post_y = -leg_y + back_post_thickness / 2.0 + 6.0

backrest_panel_height = 185.0
backrest_panel_thickness = 22.0
backrest_panel_center_z = seat_top_z + backrest_panel_height / 2.0 + 10.0
backrest_panel_width = 320.0
backrest_panel_y = -leg_y + back_post_thickness / 2.0 + 6.0

# Small front apron to improve silhouette and contact
apron_height = 28.0
apron_thickness = 22.0
apron_z = seat_top_z - apron_height / 2.0 - 6.0
apron_length_x = 2 * (leg_x - 18.0)
apron_length_y = 2 * (18.0)


def make_box(x, y, z, center):
    return cq.Workplane("XY").box(x, y, z).translate(center)


def make_x_bar(length_x, length_y, thickness, center_z):
    return (
        cq.Workplane("XY")
        .box(length_x, thickness, length_y)
        .translate((0, 0, center_z))
    )


def make_y_bar(length_x, length_y, thickness, center_z):
    return (
        cq.Workplane("XY")
        .box(thickness, length_y, length_x)
        .translate((0, 0, center_z))
    )


# Seat panel
seat = make_box(seat_width, seat_depth, seat_thickness, (0, 0, seat_center_z))

# Four legs
front_left_leg = make_box(
    leg_size, leg_size, leg_height, (-leg_x, leg_y, leg_center_z)
)
front_right_leg = make_box(
    leg_size, leg_size, leg_height, (leg_x, leg_y, leg_center_z)
)
rear_left_leg = make_box(
    leg_size, leg_size, leg_height, (-leg_x, -leg_y, leg_center_z)
)
rear_right_leg = make_box(
    leg_size, leg_size, leg_height, (leg_x, -leg_y, leg_center_z)
)

# Lower crossbars
front_lower_bar = make_x_bar(
    lower_bar_length_x, lower_bar_thickness, lower_bar_length_y, lower_bar_z
)
rear_lower_bar = make_x_bar(
    lower_bar_length_x, lower_bar_thickness, lower_bar_length_y, lower_bar_z
)
left_lower_bar = make_y_bar(
    lower_bar_thickness, lower_bar_length_y, lower_bar_length_x, lower_bar_z
)
right_lower_bar = make_y_bar(
    lower_bar_thickness, lower_bar_length_y, lower_bar_length_x, lower_bar_z
)

# Seat support rails
left_rail = make_box(
    rail_length_x, rail_thickness, rail_height, (-rail_inset_x, 0, rail_z)
)
right_rail = make_box(
    rail_length_x, rail_thickness, rail_height, (rail_inset_x, 0, rail_z)
)
front_rail = make_box(
    rail_thickness, rail_length_y, rail_height, (0, rail_inset_y, rail_z)
)
rear_rail = make_box(
    rail_thickness, rail_length_y, rail_height, (0, -rail_inset_y, rail_z)
)

# Back posts
left_back_post = make_box(
    back_post_width, back_post_thickness, back_post_height,
    (back_post_x, back_post_y, back_post_center_z)
)
right_back_post = make_box(
    back_post_width, back_post_thickness, back_post_height,
    (-back_post_x, back_post_y, back_post_center_z)
)

# Backrest panel, slightly narrower than seat for a cleaner silhouette
backrest_panel = make_box(
    backrest_panel_width, backrest_panel_thickness, backrest_panel_height,
    (0, back_post_y, backrest_panel_center_z)
)

# Front apron under seat
front_apron = make_box(
    apron_length_x, apron_thickness, apron_height,
    (0, apron_length_y / 2.0, apron_z)
)

fixture = (
    seat
    .union(front_left_leg)
    .union(front_right_leg)
    .union(rear_left_leg)
    .union(rear_right_leg)
    .union(front_lower_bar)
    .union(rear_lower_bar)
    .union(left_lower_bar)
    .union(right_lower_bar)
    .union(left_rail)
    .union(right_rail)
    .union(front_rail)
    .union