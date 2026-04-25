```py
import cadquery as cq

# ==========================================
# IKEA Markus Chair - CadQuery Model
# ==========================================

def get_caster():
    """Generates a single dual-wheel caster"""
    base = cq.Workplane("XY").cylinder(20, 18).translate((0, 0, 15))
    w1 = cq.Workplane("XZ").cylinder(10, 25).translate((0, 12, 15))
    w2 = cq.Workplane("XZ").cylinder(10, 25).translate((0, -12, 15))
    axle = cq.Workplane("XZ").cylinder(30, 4).translate((0, 0, 15))
    return base.union(w1).union(w2).union(axle)

def get_star_base():
    """Generates the 5-point aluminum star base"""
    base = cq.Workplane("XY").cylinder(60, 38).translate((0, 0, 40))
    for i in range(5):
        angle = i * (360 / 5)
        prong = (cq.Workplane("XY")
                 .workplane(offset=40).circle(35)
                 .workplane(offset=-20).center(320, 0).circle(20)
                 .loft()
                 .rotate((0,0,0), (0,0,1), angle))
        base = base.union(prong)
    return base

def get_gas_cylinder():
    """Generates the pneumatic lift cylinder bridging Z=70 to Z=365"""
    # Outer sleeve spans roughly Z=70 to Z=230
    outer = cq.Workplane("XY").cylinder(160, 25).translate((0, 0, 150))
    # Inner steel rod spans roughly Z=225 to Z=365
    inner = cq.Workplane("XY").cylinder(140, 14).translate((0, 0, 295))
    return outer, inner

def get_mechanism():
    """Generates the under-seat tilt/lift mechanism"""
    box = cq.Workplane("XY").box(180, 220, 40).translate((0, -20, 385))
    knob = cq.Workplane("XZ").cylinder(30, 25).translate((0, 100, 385))
    lever = cq.Workplane("YZ").cylinder(80, 5).translate((90, -40, 385))
    return box.union(knob).union(lever)

def get_seat():
    """Generates the filleted seat cushion"""
    return cq.Workplane("XY").box(520, 480, 70).edges().fillet(14.9).translate((0, 20, 425))

def get_backrest():
    """Generates the backrest components: frame, mesh, headrest, and lumbar support"""
    outer = cq.Workplane("XY").box(440, 40, 780).edges().fillet(9.9).translate((0, 0, 390))
    inner_cut = cq.Workplane("XY").box(380, 50, 700).translate((0, 0, 350))
    frame = outer.cut(inner_cut)
    bracket = cq.Workplane("XY").box(150, 15, 60).translate((0, 10, -30))
    frame = frame.union(bracket)
    
    mesh = cq.Workplane("XY").box(380, 2, 690).translate((0, 5, 345))
    headrest = cq.Workplane("XY").box(424, 59, 164).edges().fillet(11.9).translate((0, 15, 740))
    lumbar = cq.Workplane("XY").box(380, 45, 110).edges().fillet(9.9).rotate((0,0,0), (1,0,0), 10).translate((0, 20, 140))
    
    rotated_parts = []
    for part in [frame, mesh, headrest, lumbar]:
        rotated_parts.append(part.rotate((0,0,0), (1,0,0), -8).translate((0, -210, 450)))
        
    return rotated_parts 

def get_armrests():
    """Generates the left and right armrests"""
    metal_parts = cq.Workplane("XY")
    pad_parts = cq.Workplane("XY")
    
    for m in [1, -1]:
        # Upright moved up to Z=475 to connect mechanism to arm pads
        upright = cq.Workplane("XY").cylinder(190, 12).translate((240*m, -50, 475))
        support = cq.Workplane("XY").box(20, 250, 10).translate((240*m, 0, 575)) 
        metal_parts = metal_parts.union(upright).union(support)
        
        pad = cq.Workplane("XY").box(47, 272, 22).edges().fillet(5.9).translate((240*m, 0, 585))
        pad_parts = pad_parts.union(pad)
        
    return metal_parts, pad_parts

# ==========================================
# Assembly & Coloring
# ==========================================

chair = cq.Assembly(name="IKEA_Markus")

color_black = cq.Color(0.08, 0.08, 0.08, 1.0)
color_aluminum = cq.Color(0.75, 0.75, 0.75, 1.0)
color_steel = cq.Color(0.5, 0.5, 0.5, 1.0)
color_dark_grey = cq.Color(0.17, 0.17, 0.18, 1.0)
color_mesh = cq.Color(0.13, 0.13, 0.13, 0.9)

for i in range(5):
    angle = i * (360 / 5)
    caster = get_caster().translate((320, 0, -10)).rotate((0,0,0), (0,0,1), angle)
    chair.add(caster, color=color_black, name=f"caster_{i}")

chair.add(get_star_base(), color=color_aluminum, name="star_base")

cyl_outer, cyl_inner = get_gas_cylinder()
chair.add(cyl_outer, color=color_black, name="gas_cyl_outer")
chair.add(cyl_inner, color=color_steel, name="gas_cyl_inner")

chair.add(get_mechanism(), color=color_black, name="mechanism")
chair.add(get_seat(), color=color_dark_grey, name="seat")

frame, mesh, headrest, lumbar = get_backrest()
chair.add(frame, color=color_black, name="backrest_frame")
chair.add(mesh, color=color_mesh, name="backrest_mesh")
chair.add(headrest, color=color_dark_grey, name="headrest")
chair.add(lumbar, color=color_black, name="lumbar")

arm_metal, arm_pad = get_armrests()
chair.add(arm_metal, color=color_aluminum, name="armrest_metal")
chair.add(arm_pad, color=color_dark_grey, name="armrest_pad")

# ==========================================
# Display 
# ==========================================
if 'show_object' in locals():
    show_object(chair, name="IKEA Markus")
```
