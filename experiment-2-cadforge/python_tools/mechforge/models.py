from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


MaterialName = Literal["aluminum_6061", "aluminum_7075", "pla", "petg", "steel_1018"]
FeatureType = Literal[
    "rib",
    "lightening_hole",
    "boss",
    "fillet_marker",
    "hook_curve",
    "clamp_jaw",
    "stator_ring",
    "stator_tooth",
    "seat_panel",
    "chair_leg",
    "chair_back",
    "chair_crossbar",
    "decorative_curve",
    "generic_panel",
    "support_tube",
    "curved_tube",
    "flat_foot",
    "armrest",
    "headrest",
    "tabletop",
    "table_leg",
]


class Feature(BaseModel):
    type: FeatureType
    x: float = 0.0
    y: float = 0.0
    x2: float = 0.0
    y2: float = 0.0
    width: float = 0.0
    height: float = 0.0
    radius: float = 0.0
    note: str = ""


class Hole(BaseModel):
    x: float
    y: float
    radius: float


class Design(BaseModel):
    title: str = "Untitled design"
    rationale: str = ""
    material: MaterialName = "aluminum_6061"
    load_newtons: float = 120.0
    load_point_x_mm: float = 90.0
    load_point_y_mm: float = 0.0
    base_length_mm: float = 105.0
    base_width_mm: float = 44.0
    base_thickness_mm: float = 4.0
    fixed_holes: list[Hole] = Field(default_factory=list)
    features: list[Feature] = Field(default_factory=list)
    expected_failure_mode: str = ""
    action_plan: list[str] = Field(default_factory=list)


class ToolAction(BaseModel):
    tool: str
    params: dict = Field(default_factory=dict)


class Material(BaseModel):
    density_g_cm3: float
    yield_mpa: float
    young_mpa: float
    thermal_w_mk: float
    poisson: float = 0.33


MATERIALS: dict[str, Material] = {
    "aluminum_6061": Material(density_g_cm3=2.70, yield_mpa=276, young_mpa=69000, thermal_w_mk=167),
    "aluminum_7075": Material(density_g_cm3=2.81, yield_mpa=503, young_mpa=71700, thermal_w_mk=130),
    "pla": Material(density_g_cm3=1.24, yield_mpa=55, young_mpa=3500, thermal_w_mk=0.13),
    "petg": Material(density_g_cm3=1.27, yield_mpa=50, young_mpa=2100, thermal_w_mk=0.20),
    "steel_1018": Material(density_g_cm3=7.87, yield_mpa=370, young_mpa=200000, thermal_w_mk=51),
}


def sample_design() -> Design:
    return Design(
        title="Two-rib lightweight cantilever bracket",
        rationale=(
            "A broad thin base keeps bolt spacing stable, two diagonal ribs move material "
            "toward the bending load path, and small lightening holes reduce mass away "
            "from the fixed edge."
        ),
        material="aluminum_6061",
        load_newtons=120,
        load_point_x_mm=90,
        load_point_y_mm=0,
        base_length_mm=105,
        base_width_mm=44,
        base_thickness_mm=4,
        fixed_holes=[Hole(x=12, y=-13, radius=3), Hole(x=12, y=13, radius=3)],
        features=[
            Feature(type="rib", x=16, y=-14, x2=88, y2=-4, width=5, height=18, note="lower diagonal rib"),
            Feature(type="rib", x=16, y=14, x2=88, y2=4, width=5, height=18, note="upper diagonal rib"),
            Feature(type="rib", x=18, y=0, x2=96, y2=0, width=4, height=12, note="center spine rib"),
            Feature(type="lightening_hole", x=52, y=-13, radius=4, note="low-stress pocket"),
            Feature(type="lightening_hole", x=52, y=13, radius=4, note="low-stress pocket"),
            Feature(type="boss", x=92, y=0, height=7, radius=6, note="load application boss"),
        ],
        expected_failure_mode="Bending stress at the fixed edge and rib roots.",
        action_plan=[
            "Search the load path",
            "Add ribs along tension/compression lines",
            "Remove material from low-stress regions",
            "Run simulation",
            "Iterate dimensions",
        ],
    )
