from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ColumnDef:
    name: str
    type: str = "float"
    unit: Optional[str] = None
    description: Optional[str] = None


@dataclass
class PageGroup:
    pages: list
    skip_header_rows: int
    footer_pattern: str
    section_pattern: str
    value_count: int = 0
    columns: list = field(default_factory=list)
    continuation_value_count: Optional[int] = None
    max_data_rows: Optional[int] = None
    section_column_idx: int = 0
    parser: str = "token"  # "token", "two_row", "paired", "matrix", "flange"
    pair_invert: bool = False  # for paired mode: True = split left half are value headers
    cell_aligned: bool = False  # True: each cell maps directly to a column (no token split)
    join_remaining: bool = False  # True: join extra tokens into last column value
    merge_fractions: bool = False  # True: merge "N/" rows with following row
    strip_metrics: bool = False  # True: strip parenthetical "(mm)" values
    parse_fractions: bool = False  # True: convert "1/2" to 0.5 in numeric fields
    grid_cols: int = 0  # number of column headers in a grid (for page 33-34 style tables)
    grid_header_row: int = 0  # row index (within data rows) containing column headers
    section_suffix: str = ""  # appended to section keys to avoid cross-page collisions


LEAF_DATA_TABLE = "table"
LEAF_DATA_SKIP = "skip"
LEAF_DATA_RAW = "raw"


@dataclass
class LeafSchema:
    leaf_id: str
    name: str
    pages: list
    data_type: str = LEAF_DATA_TABLE
    page_groups: list = field(default_factory=list)


# ── Pattern definitions (kept from original) ──

SECTION_PATTERN_CORE = (
    r"^("
    r"(?:W\d+\s+\d+(?:\s*x\s*\d+(?:/\d+)?)?\s*(?:\([^)]+\))?)"
    r"|"
    r"(?:\d+(?:\.\d+)?\s*x\s*\d+(?:/\d+)?\s*(?:\([^)]+\))?)"
    r")"
    r"\s*"
)

SECTION_PATTERN_DIM = r"^(\d+(?:\.\d+)?\s*x\s*\d+(?:\.\d+)?(?:\s*x\s*\d+(?:\.\d+)?)?)\s*"

SECTION_PATTERN_DIM_IMPERIAL = (
    r"^(\d+(?:\.\d+)?\s*x\s*\d+(?:\.\d+)?(?:\s*x\s*\d+(?:\.\d+)?)?"
    r"\s*\([^)]*\))\s*"
)

SECTION_PATTERN_FRAC_DIM = (
    r"^((?:\d+(?:[-\s]\d+)?(?:/\d+)?\s*x\s*)+\d+(?:[-\s]\d+)?(?:/\d+)?"
    r"(?:\s+\d+(?:\.\d+)?\s*x\s*\d+(?:\.\d+)?)?)\s*"
)

SECTION_PATTERN_PILE = (
    r"^([A-Za-z0-9][-A-Za-z0-9]*(?:\s+(?![0-9]+(?:\s|$))[A-Za-z0-9][-A-Za-z0-9]*)?)\s*"
)

SECTION_PATTERN_NUMERIC = r"^(\d+(?:\.\d+)?)\s*"

SECTION_PATTERN_FLANGE = r"^(\d+(?:/\d+)?|½|¼|¾|⅛|⅜|⅝|⅞)\s*"

SECTION_PATTERN_DIM_OPT_IMPERIAL = (
    r"^(\d+(?:\.\d+)?\s*x\s*\d+(?:\.\d+)?(?:\s*x\s*\d+(?:\.\d+)?)?"
    r"(?:\s*\([^)]*\))?)\s*"
)

SECTION_PATTERN_PURLIN_Z = r"^(SZ\s+\d+-\d+)\s*"
SECTION_PATTERN_PURLIN_C = r"^(SC\d+-\d+)\s*"

SECTION_PATTERN_PIPE_NOM_FRAC = r"^((?:\d*[\u00BC-\u00BE\u2150-\u215E]|\d+(?:/\d+)?))\s*"

SECTION_PATTERN_PIPE_NOM_DUAL = r"^(\d+(?:\s+(?:\d*[\u00BC-\u00BE\u2150-\u215E]|\d+/\d+|\d+))?)\s*"

SECTION_PATTERN_STK_OD = r"^(\d{2,}(?:\.\d+)?)\s*"

SECTION_PATTERN_INCH_CHANNEL = r"^(C\d+(?:\.\d+)?\s*x\s*\d+(?:\.\d+)?)\s*"

SECTION_PATTERN_MATRIX_DIM = r"^(\d+(?:\.\d+)?(?:\s*x\s*\d+(?:\.\d+)?)?)\s*"

SECTION_PATTERN_GAUGE = r"^(\d+)\s*"

SECTION_PATTERN_SS_GRADE = r"^(SUS\s*\d+|AISI\s*\d+|Type\s+\d+)\s*"

SECTION_PATTERN_API = r"^(\d+(?:-\d+(?:/\d+)?)?(?:/\d+)?\s+\d+(?:[-\s]\d+(?:/\d+)?)?(?:\.\d+)?\s+\d+(?:\.\d+)?)\s*"

FOOTER_PATTERN = r"YICK HOE|YICK HOE GROUP OF COMPANY"
FOOTER_PATTERN_NOTES = r"YICK HOE|YICK HOE GROUP OF COMPANY|Note\s*:|Sizes indicated|L = Light|Intermediate values"
FOOTER_PATTERN_TOL = r"YICK HOE|YICK HOE GROUP OF COMPANY|Note\s*:|Tolerance|Wall Thickness"
FOOTER_PATTERN_STK = r"YICK HOE|YICK HOE GROUP OF COMPANY|Applicable Tolerances|mm and over|Outside Diameter Under|mm or over|Note\s*:"


# ══════════════════════════════════════════════════════════════════════════════
# LEAF SCHEMA DEFINITIONS
# ══════════════════════════════════════════════════════════════════════════════

SKIP_LEAF = LEAF_DATA_SKIP

# ── Helper to mark product_list / descriptive-only leaves ──

def skip(name, pages):
    return LeafSchema(leaf_id=name, name=name, pages=pages, data_type=LEAF_DATA_SKIP)

# ── I-BEAMS (pages 14-55) ──

I_BEAMS_PRODUCT_LIST = skip("i_beams_product_list", list(range(14, 55)))

LEAVES = []

# 1) I-Beams intro: product list + design formulae (pages 14-32) — skip (descriptive)
LEAVES.append(skip("product_list_and_design_formulae", list(range(14, 21))))
LEAVES.append(skip("i_beam_stress_strain_diagram", list(range(21, 33))))

# 1a) Slenderness & geometry ratio allowable stress (page 33, BS 449 grid table)
LEAVES.append(LeafSchema(
    leaf_id="slenderness_and_geometry_ratio_allowable_stress",
    name="Slenderness and Geometry Ratio - Allowable Stress (BS 449 Table 3a)",
    pages=[33],
    page_groups=[
        PageGroup(pages=[33], skip_header_rows=4,
                  footer_pattern=FOOTER_PATTERN_NOTES, section_pattern=r"^(\d+)",
                  parser="grid", grid_header_row=0, max_data_rows=25,
                  columns=[
                      ColumnDef("dt_10", unit="N/mm2"),
                      ColumnDef("dt_15", unit="N/mm2"),
                      ColumnDef("dt_20", unit="N/mm2"),
                      ColumnDef("dt_25", unit="N/mm2"),
                      ColumnDef("dt_30", unit="N/mm2"),
                      ColumnDef("dt_35", unit="N/mm2"),
                      ColumnDef("dt_40", unit="N/mm2"),
                      ColumnDef("dt_50", unit="N/mm2"),
                  ]),
    ],
))

# 1b) Stanchions allowable axial stress (page 34, BS 449 Table 17a)
LEAVES.append(LeafSchema(
    leaf_id="stanchios_and_struts_allowable_stress",
    name="Stanchions and Struts - Allowable Axial Stress (BS 449 Table 17a)",
    pages=[34],
    page_groups=[
        PageGroup(pages=[34], skip_header_rows=9,
                  footer_pattern=FOOTER_PATTERN_NOTES, section_pattern=r"^(\d+)",
                  parser="grid", grid_header_row=0, max_data_rows=25,
                  columns=[
                      ColumnDef("pc_0", unit="N/mm2"),
                      ColumnDef("pc_1", unit="N/mm2"),
                      ColumnDef("pc_2", unit="N/mm2"),
                      ColumnDef("pc_3", unit="N/mm2"),
                      ColumnDef("pc_4", unit="N/mm2"),
                      ColumnDef("pc_5", unit="N/mm2"),
                      ColumnDef("pc_6", unit="N/mm2"),
                      ColumnDef("pc_7", unit="N/mm2"),
                      ColumnDef("pc_8", unit="N/mm2"),
                      ColumnDef("pc_9", unit="N/mm2"),
                  ]),
    ],
))

# 2) Safe loads for grade 43 steel (pages 35-36) — variable span count per beam
LEAVES.append(LeafSchema(
    leaf_id="safe_loads_for_grade_43_steel",
    name="Safe Loads for Grade 43 Steel",
    pages=[35, 36],
    page_groups=[
        PageGroup(pages=[35], skip_header_rows=8,
                  footer_pattern=FOOTER_PATTERN, section_pattern=r"^(\d+\s*x\s*\d+)",
                  parser="safe_loads",
                  columns=[
                      ColumnDef("mass_per_m", unit="kg"),
                      ColumnDef("span_2_00", unit="kN"), ColumnDef("span_2_50", unit="kN"),
                      ColumnDef("span_3_00", unit="kN"), ColumnDef("span_3_50", unit="kN"),
                      ColumnDef("span_4_00", unit="kN"), ColumnDef("span_4_50", unit="kN"),
                      ColumnDef("span_5_00", unit="kN"), ColumnDef("span_5_50", unit="kN"),
                      ColumnDef("span_6_00", unit="kN"), ColumnDef("span_7_00", unit="kN"),
                      ColumnDef("span_8_00", unit="kN"), ColumnDef("span_9_00", unit="kN"),
                      ColumnDef("span_10_00", unit="kN"),
                      ColumnDef("critical_span", unit="m"),
                  ]),
        PageGroup(pages=[36], skip_header_rows=8,
                  footer_pattern=FOOTER_PATTERN, section_pattern=r"^(\d+\s*x\s*\d+)",
                  parser="safe_loads",
                  columns=[
                      ColumnDef("mass_per_m", unit="kg"),
                      ColumnDef("span_4_00", unit="kN"), ColumnDef("span_5_00", unit="kN"),
                      ColumnDef("span_6_00", unit="kN"), ColumnDef("span_7_00", unit="kN"),
                      ColumnDef("span_8_00", unit="kN"), ColumnDef("span_9_00", unit="kN"),
                      ColumnDef("span_10_00", unit="kN"), ColumnDef("span_11_00", unit="kN"),
                      ColumnDef("span_12_00", unit="kN"), ColumnDef("span_13_00", unit="kN"),
                      ColumnDef("span_14_00", unit="kN"), ColumnDef("span_15_00", unit="kN"),
                      ColumnDef("span_16_00", unit="kN"),
                      ColumnDef("critical_span", unit="m"),
                  ]),
    ],
))

# 3) Universal beams and columns (pages 37-48) — FULL coverage, merge 4 page types
LEAVES.append(LeafSchema(
    leaf_id="universal_beams_and_columns",
    name="Universal Beams and Columns",
    pages=list(range(37, 49)),
    page_groups=[
        PageGroup(pages=[37, 39, 41, 43, 45], skip_header_rows=6,
                  footer_pattern=FOOTER_PATTERN, section_pattern=SECTION_PATTERN_CORE,
                  value_count=14,
                  columns=[
                      ColumnDef("weight_lb_ft", unit="lb/ft"), ColumnDef("weight_kg_m", unit="kg/m"),
                      ColumnDef("area_in2", unit="in²"), ColumnDef("area_cm2", unit="cm²"),
                      ColumnDef("depth_in", unit="in"), ColumnDef("depth_mm", unit="mm"),
                      ColumnDef("flange_width_in", unit="in"), ColumnDef("flange_width_mm", unit="mm"),
                      ColumnDef("flange_thickness_in", unit="in"), ColumnDef("flange_thickness_mm", unit="mm"),
                      ColumnDef("web_thickness_in", unit="in"), ColumnDef("web_thickness_mm", unit="mm"),
                      ColumnDef("corner_radius_in", unit="in"), ColumnDef("corner_radius_mm", unit="mm"),
                  ]),
        PageGroup(pages=[38, 40, 42, 44, 46], skip_header_rows=9,
                  footer_pattern=FOOTER_PATTERN, section_pattern=SECTION_PATTERN_CORE,
                  value_count=12,
                  columns=[
                      ColumnDef("Ix_in4", unit="in⁴"), ColumnDef("Ix_cm4", unit="cm⁴"),
                      ColumnDef("Iy_in4", unit="in⁴"), ColumnDef("Iy_cm4", unit="cm⁴"),
                      ColumnDef("ix_in", unit="in"), ColumnDef("ix_cm", unit="cm"),
                      ColumnDef("iy_in", unit="in"), ColumnDef("iy_cm", unit="cm"),
                      ColumnDef("Zx_in3", unit="in³"), ColumnDef("Zx_cm3", unit="cm³"),
                      ColumnDef("Zy_in3", unit="in³"), ColumnDef("Zy_cm3", unit="cm³"),
                  ]),
        PageGroup(pages=[47], skip_header_rows=6,
                  footer_pattern=FOOTER_PATTERN, section_pattern=SECTION_PATTERN_CORE,
                  value_count=13,
                  columns=[
                      ColumnDef("weight_kg_m", unit="kg/m"), ColumnDef("depth_mm", unit="mm"),
                      ColumnDef("flange_width_mm", unit="mm"), ColumnDef("web_thickness_mm", unit="mm"),
                      ColumnDef("flange_thickness_mm", unit="mm"), ColumnDef("corner_radius_mm", unit="mm"),
                      ColumnDef("area_cm2", unit="cm²"), ColumnDef("Ix_cm4", unit="cm⁴"),
                      ColumnDef("Iy_cm4", unit="cm⁴"), ColumnDef("ix_cm", unit="cm"),
                      ColumnDef("iy_cm", unit="cm"), ColumnDef("Zx_cm3", unit="cm³"),
                      ColumnDef("Zy_cm3", unit="cm³"),
                  ]),
        PageGroup(pages=[48], skip_header_rows=9,
                  footer_pattern=FOOTER_PATTERN, section_pattern=SECTION_PATTERN_CORE,
                  value_count=13,
                  columns=[
                      ColumnDef("weight_kg_m", unit="kg/m"), ColumnDef("depth_mm", unit="mm"),
                      ColumnDef("flange_width_mm", unit="mm"), ColumnDef("web_thickness_mm", unit="mm"),
                      ColumnDef("flange_thickness_mm", unit="mm"), ColumnDef("corner_radius_mm", unit="mm"),
                      ColumnDef("area_cm2", unit="cm²"), ColumnDef("Ix_cm4", unit="cm⁴"),
                      ColumnDef("Iy_cm4", unit="cm⁴"), ColumnDef("ix_cm", unit="cm"),
                      ColumnDef("iy_cm", unit="cm"), ColumnDef("Zx_cm3", unit="cm³"),
                      ColumnDef("Zy_cm3", unit="cm³"),
                  ]),
    ]))

# 4) Light beam and joist (pages 49-52)
LEAVES.append(LeafSchema(
    leaf_id="light_beam_and_joist",
    name="Light Beam and Joist",
    pages=list(range(49, 53)),
    page_groups=[
        PageGroup(pages=[49], skip_header_rows=6,
                  footer_pattern=FOOTER_PATTERN_NOTES, section_pattern=SECTION_PATTERN_CORE,
                  value_count=14,
                  columns=[
                      ColumnDef("weight_lb_ft", unit="lb/ft"), ColumnDef("weight_kg_m", unit="kg/m"),
                      ColumnDef("depth_in", unit="in"), ColumnDef("depth_mm", unit="mm"),
                      ColumnDef("flange_width_in", unit="in"), ColumnDef("flange_width_mm", unit="mm"),
                      ColumnDef("web_thickness_in", unit="in"), ColumnDef("web_thickness_mm", unit="mm"),
                      ColumnDef("flange_thickness_in", unit="in"), ColumnDef("flange_thickness_mm", unit="mm"),
                      ColumnDef("corner_radius_in", unit="in"), ColumnDef("corner_radius_mm", unit="mm"),
                      ColumnDef("area_in2", unit="in²"), ColumnDef("area_cm2", unit="cm²"),
                  ]),
        PageGroup(pages=[50, 52], skip_header_rows=9,
                  footer_pattern=FOOTER_PATTERN, section_pattern=SECTION_PATTERN_CORE,
                  value_count=12,
                  columns=[
                      ColumnDef("Ix_in4", unit="in⁴"), ColumnDef("Ix_cm4", unit="cm⁴"),
                      ColumnDef("Iy_in4", unit="in⁴"), ColumnDef("Iy_cm4", unit="cm⁴"),
                      ColumnDef("ix_in", unit="in"), ColumnDef("ix_cm", unit="cm"),
                      ColumnDef("iy_in", unit="in"), ColumnDef("iy_cm", unit="cm"),
                      ColumnDef("Zx_in3", unit="in³"), ColumnDef("Zx_cm3", unit="cm³"),
                      ColumnDef("Zy_in3", unit="in³"), ColumnDef("Zy_cm3", unit="cm³"),
                  ]),
        PageGroup(pages=[51], skip_header_rows=6,
                  footer_pattern=FOOTER_PATTERN, section_pattern=SECTION_PATTERN_CORE,
                  value_count=12,
                  columns=[
                      ColumnDef("weight_kg_m", unit="kg/m"), ColumnDef("weight_lb_ft", unit="lb/ft"),
                      ColumnDef("web_thickness_mm", unit="mm"), ColumnDef("web_thickness_in", unit="in"),
                      ColumnDef("flange_thickness_mm", unit="mm"), ColumnDef("flange_thickness_in", unit="in"),
                      ColumnDef("root_radius_mm", unit="mm"), ColumnDef("root_radius_in", unit="in"),
                      ColumnDef("toe_radius_mm", unit="mm"), ColumnDef("toe_radius_in", unit="in"),
                      ColumnDef("area_cm2", unit="cm²"), ColumnDef("area_in2", unit="in²"),
                  ]),
    ]))

# 5) Bearing pile (pages 53-55) — page 55 is just a footer
LEAVES.append(LeafSchema(
    leaf_id="bearing_pile",
    name="Bearing Pile",
    pages=[53, 54, 55],
    page_groups=[
        PageGroup(pages=[53], skip_header_rows=5,
                  footer_pattern=FOOTER_PATTERN, section_pattern=SECTION_PATTERN_CORE,
                  value_count=12,
                  columns=[
                      ColumnDef("weight_lb_ft", unit="lb/ft"), ColumnDef("weight_kg_m", unit="kg/m"),
                      ColumnDef("depth_in", unit="in"), ColumnDef("depth_mm", unit="mm"),
                      ColumnDef("flange_width_in", unit="in"), ColumnDef("flange_width_mm", unit="mm"),
                      ColumnDef("web_thickness_in", unit="in"), ColumnDef("web_thickness_mm", unit="mm"),
                      ColumnDef("corner_radius_in", unit="in"), ColumnDef("corner_radius_mm", unit="mm"),
                      ColumnDef("area_in2", unit="in²"), ColumnDef("area_cm2", unit="cm²"),
                  ]),
        PageGroup(pages=[54], skip_header_rows=8,
                  footer_pattern=FOOTER_PATTERN, section_pattern=SECTION_PATTERN_CORE,
                  value_count=12,
                  columns=[
                      ColumnDef("Ix_in4", unit="in⁴"), ColumnDef("Ix_cm4", unit="cm⁴"),
                      ColumnDef("Iy_in4", unit="in⁴"), ColumnDef("Iy_cm4", unit="cm⁴"),
                      ColumnDef("ix_in", unit="in"), ColumnDef("ix_cm", unit="cm"),
                      ColumnDef("iy_in", unit="in"), ColumnDef("iy_cm", unit="cm"),
                      ColumnDef("Zx_in3", unit="in³"), ColumnDef("Zx_cm3", unit="cm³"),
                      ColumnDef("Zy_in3", unit="in³"), ColumnDef("Zy_cm3", unit="cm³"),
                  ]),
    ]))

# ── STEEL PILES (pages 57-65) ──

LEAVES.append(skip("steel_qualities", [57]))
LEAVES.append(skip("recommended_working_stresses_for_steel_sheet_piling", [57]))
LEAVES.append(skip("circular_construction", [60]))

LEAVES.append(skip("minimum_effective_life_for_maximum_stress", [61]))

LEAVES.append(LeafSchema(
    leaf_id="frodingham_steel_sheet_piling",
    name="Frodingham Steel Sheet Piling",
    pages=[58],
    page_groups=[
        PageGroup(pages=[58], skip_header_rows=9,
                  footer_pattern=FOOTER_PATTERN, section_pattern=SECTION_PATTERN_PILE,
                  value_count=11, max_data_rows=7,
                  columns=[
                      ColumnDef("width_b_mm", unit="mm"), ColumnDef("height_h_mm", unit="mm"),
                      ColumnDef("web_thickness_d_mm", unit="mm"), ColumnDef("flange_thickness_t_mm", unit="mm"),
                      ColumnDef("f1_mm", unit="mm"), ColumnDef("f2_mm", unit="mm"),
                      ColumnDef("section_area_cm2", unit="cm²"),
                      ColumnDef("weight_per_m_wall_kg", unit="kg/m of wall"),
                      ColumnDef("weight_per_m2_kg", unit="kg/m²"),
                      ColumnDef("moment_of_inertia_cm4", unit="cm⁴"),
                      ColumnDef("modulus_of_section_cm3", unit="cm³"),
                  ]),
    ]))

LEAVES.append(LeafSchema(
    leaf_id="larssen_steel_sheet_piling",
    name="Larssen Steel Sheet Piling",
    pages=[59],
    page_groups=[
        PageGroup(pages=[59], skip_header_rows=8,
                  footer_pattern=FOOTER_PATTERN, section_pattern=SECTION_PATTERN_PILE,
                  value_count=10, max_data_rows=11,
                  columns=[
                      ColumnDef("width_b_mm", unit="mm"), ColumnDef("height_h_mm", unit="mm"),
                      ColumnDef("web_thickness_d_mm", unit="mm"), ColumnDef("flange_thickness_t_mm", unit="mm"),
                      ColumnDef("flat_pan_mm", unit="mm"),
                      ColumnDef("section_area_cm2", unit="cm²"),
                      ColumnDef("weight_per_m_wall_kg", unit="kg/m of wall"),
                      ColumnDef("weight_per_m2_kg", unit="kg/m²"),
                      ColumnDef("moment_of_inertia_cm4", unit="cm⁴"),
                      ColumnDef("modulus_of_section_cm3", unit="cm³"),
                  ]),
    ]))

LEAVES.append(LeafSchema(
    leaf_id="u_type",
    name="U-Type Steel Piles",
    pages=[62, 63],
    page_groups=[
        PageGroup(pages=[62], skip_header_rows=9,
                  footer_pattern=FOOTER_PATTERN, section_pattern=SECTION_PATTERN_PILE,
                  value_count=10,
                  columns=[
                      ColumnDef("width_w_mm", unit="mm"), ColumnDef("height_h_mm", unit="mm"),
                      ColumnDef("thickness_t_mm", unit="mm"),
                      ColumnDef("section_area_cm2", unit="cm²"),
                      ColumnDef("weight_per_pile_kg", unit="kg/m"),
                      ColumnDef("weight_per_wall_kg", unit="kg/m²"),
                      ColumnDef("moment_inertia_cm4", unit="cm⁴"),
                      ColumnDef("moment_inertia_per_m_cm4", unit="cm⁴/m"),
                      ColumnDef("modulus_cm3", unit="cm³"),
                      ColumnDef("modulus_per_m_cm3", unit="cm³/m"),
                  ]),
        PageGroup(pages=[63], skip_header_rows=8,
                  footer_pattern=FOOTER_PATTERN, section_pattern=SECTION_PATTERN_PILE,
                  value_count=13,
                  columns=[
                      ColumnDef("width_w_mm", unit="mm"), ColumnDef("height_h_mm", unit="mm"),
                      ColumnDef("thickness_t_mm", unit="mm"),
                      ColumnDef("section_area_cm2", unit="cm²"),
                      ColumnDef("weight_per_pile_kg", unit="kg/m"),
                      ColumnDef("weight_per_wall_kg", unit="kg/m²"),
                      ColumnDef("moment_inertia_cm4", unit="cm⁴"),
                      ColumnDef("moment_inertia_per_m_cm4", unit="cm⁴/m"),
                      ColumnDef("modulus_cm3", unit="cm³"),
                      ColumnDef("modulus_per_m_cm3", unit="cm³/m"),
                      ColumnDef("width_w_in", unit="in"), ColumnDef("height_h_in", unit="in"),
                      ColumnDef("thickness_t_in", unit="in"),
                  ]),
    ]))

# z_type and straight_web_type both on page 64, one is the main table + continuation
LEAVES.append(LeafSchema(
    leaf_id="z_type",
    name="Z-Type Steel Piles",
    pages=[64],
    page_groups=[
        PageGroup(pages=[64], skip_header_rows=9,
                  footer_pattern=FOOTER_PATTERN, section_pattern=SECTION_PATTERN_PILE,
                  value_count=12,
                  columns=[
                      ColumnDef("width_w_mm", unit="mm"), ColumnDef("height_h_mm", unit="mm"),
                      ColumnDef("t1_mm", unit="mm"), ColumnDef("t2_mm", unit="mm"),
                      ColumnDef("section_area_cm2", unit="cm²"),
                      ColumnDef("weight_per_pile_kg", unit="kg/m"),
                      ColumnDef("weight_per_wall_kg", unit="kg/m²"),
                      ColumnDef("moment_inertia_cm4", unit="cm⁴"),
                      ColumnDef("moment_inertia_per_m_cm4", unit="cm⁴/m"),
                      ColumnDef("modulus_cm3", unit="cm³"),
                      ColumnDef("modulus_per_m_cm3", unit="cm³/m"),
                      ColumnDef("width_w_in", unit="in"),
                  ]),
    ]))

LEAVES.append(skip("straight_web_type", [64]))

# ── API PIPES (pages 66-85) ──
LEAVES.append(LeafSchema(
    leaf_id="api_pipes",
    name="API Pipes ERW & Seamless",
    pages=list(range(66, 85)),
    page_groups=[
        PageGroup(pages=[72, 73], skip_header_rows=7,
                  footer_pattern=FOOTER_PATTERN, section_pattern=SECTION_PATTERN_API,
                  parser="api_pipes",
                  columns=[
                      ColumnDef("schedule_number"),
                      ColumnDef("schedule_type"),
                      ColumnDef("wall_thickness_in", unit="in"),
                      ColumnDef("wall_thickness_mm", unit="mm"),
                      ColumnDef("weight_lb_ft", unit="lb/ft"),
                      ColumnDef("weight_kg_m", unit="kg/m"),
                      ColumnDef("weight_kg_ft", unit="kg/ft"),
                      ColumnDef("hydro_std", unit="psi"),
                      ColumnDef("hydro_alt", unit="psi"),
                      ColumnDef("hydro_std_2", unit="psi"),
                      ColumnDef("hydro_alt_2", unit="psi"),
                      ColumnDef("x42", unit="psi"), ColumnDef("x46", unit="psi"),
                      ColumnDef("x52", unit="psi"), ColumnDef("x56", unit="psi"),
                      ColumnDef("x60", unit="psi"), ColumnDef("x65", unit="psi"),
                      ColumnDef("x70", unit="psi"),
                  ]),
        PageGroup(pages=list(range(74, 85)), skip_header_rows=7,
                  footer_pattern=FOOTER_PATTERN, section_pattern=SECTION_PATTERN_API,
                  parser="api_pipes",
                  columns=[
                      ColumnDef("schedule_number"),
                      ColumnDef("schedule_type"),
                      ColumnDef("wall_thickness_in", unit="in"),
                      ColumnDef("wall_thickness_mm", unit="mm"),
                      ColumnDef("weight_lb_ft", unit="lb/ft"),
                      ColumnDef("weight_kg_m", unit="kg/m"),
                      ColumnDef("weight_kg_ft", unit="kg/ft"),
                      ColumnDef("hydro_std", unit="psi"),
                      ColumnDef("hydro_alt", unit="psi"),
                      ColumnDef("hydro_std_2", unit="psi"),
                      ColumnDef("hydro_alt_2", unit="psi"),
                      ColumnDef("x42", unit="psi"), ColumnDef("x46", unit="psi"),
                      ColumnDef("x52", unit="psi"), ColumnDef("x56", unit="psi"),
                  ]),
    ],
))

# ── COLD FORMED HOLLOW SECTIONS (pages 86-100) ──
LEAVES.append(skip("product_list_and_standard_specifications", list(range(86, 90))))

LEAVES.append(LeafSchema(
    leaf_id="square_metric",
    name="Cold Formed Square Hollow Sections (Metric)",
    pages=[90, 91, 92],
    page_groups=[
        PageGroup(pages=[91, 92], skip_header_rows=7,
                  footer_pattern=FOOTER_PATTERN, section_pattern=SECTION_PATTERN_DIM,
                  value_count=9,
                  columns=[
                      ColumnDef("wall_thickness_mm", unit="mm"), ColumnDef("weight_kg_m", unit="kg/m"),
                      ColumnDef("area_cm2", unit="cm²"),
                      ColumnDef("Ix_cm4", unit="cm⁴"), ColumnDef("Iy_cm4", unit="cm⁴"),
                      ColumnDef("ix_cm", unit="cm"), ColumnDef("iy_cm", unit="cm"),
                      ColumnDef("Zx_cm3", unit="cm³"), ColumnDef("Zy_cm3", unit="cm³"),
                  ]),
    ]))

LEAVES.append(LeafSchema(
    leaf_id="rectangular_metric",
    name="Cold Formed Rectangular Hollow Sections (Metric)",
    pages=[92, 93, 94],
    page_groups=[
        PageGroup(pages=[93, 94], skip_header_rows=7,
                  footer_pattern=FOOTER_PATTERN, section_pattern=SECTION_PATTERN_DIM,
                  value_count=9,
                  columns=[
                      ColumnDef("wall_thickness_mm", unit="mm"), ColumnDef("weight_kg_m", unit="kg/m"),
                      ColumnDef("area_cm2", unit="cm²"),
                      ColumnDef("Ix_cm4", unit="cm⁴"), ColumnDef("Iy_cm4", unit="cm⁴"),
                      ColumnDef("ix_cm", unit="cm"), ColumnDef("iy_cm", unit="cm"),
                      ColumnDef("Zx_cm3", unit="cm³"), ColumnDef("Zy_cm3", unit="cm³"),
                  ]),
    ]))

LEAVES.append(LeafSchema(
    leaf_id="square_imperial",
    name="Cold Formed Square Hollow Sections (Imperial)",
    pages=[94, 95, 96, 97],
    page_groups=[
        PageGroup(pages=[95, 96, 97], skip_header_rows=7,
                  footer_pattern=FOOTER_PATTERN, section_pattern=SECTION_PATTERN_FRAC_DIM,
                  value_count=8,
                  columns=[
                      ColumnDef("wall_thickness_in", unit="in"), ColumnDef("wall_thickness_mm", unit="mm"),
                      ColumnDef("weight_lb_ft", unit="lb/ft"), ColumnDef("weight_kg_m", unit="kg/m"),
                      ColumnDef("area_in2", unit="in²"),
                      ColumnDef("I_in4", unit="in⁴"), ColumnDef("i_in", unit="in"),
                      ColumnDef("Z_in3", unit="in³"),
                  ]),
    ]))

LEAVES.append(LeafSchema(
    leaf_id="rectangular_imperial",
    name="Cold Formed Rectangular Hollow Sections (Imperial)",
    pages=[97, 98, 99, 100],
    page_groups=[
        PageGroup(pages=[98, 99, 100], skip_header_rows=7,
                  footer_pattern=FOOTER_PATTERN, section_pattern=SECTION_PATTERN_FRAC_DIM,
                  value_count=11,
                  columns=[
                      ColumnDef("wall_thickness_in", unit="in"), ColumnDef("wall_thickness_mm", unit="mm"),
                      ColumnDef("weight_lb_ft", unit="lb/ft"), ColumnDef("weight_kg_m", unit="kg/m"),
                      ColumnDef("area_in2", unit="in²"),
                      ColumnDef("Ix_in4", unit="in⁴"), ColumnDef("Iy_in4", unit="in⁴"),
                      ColumnDef("ix_in", unit="in"), ColumnDef("iy_in", unit="in"),
                      ColumnDef("Zx_in3", unit="in³"), ColumnDef("Zy_in3", unit="in³"),
                  ]),
    ]))

# ── HOT FORMED HOLLOW SECTIONS (pages 101-111) ──
LEAVES.append(skip("hot_formed_hollow_sections_intro", list(range(101, 105))))
LEAVES.append(LeafSchema(
    leaf_id="hot_formed_hollow_sections",
    name="Hot Formed Hollow Sections",
    pages=[105, 106, 107, 108, 109, 110, 111],
    page_groups=[
        PageGroup(pages=[105, 106, 107], skip_header_rows=7,
                  footer_pattern=FOOTER_PATTERN, section_pattern=SECTION_PATTERN_DIM,
                  value_count=11,
                  columns=[
                      ColumnDef("wall_thickness_mm", unit="mm"), ColumnDef("weight_kg_m", unit="kg/m"),
                      ColumnDef("area_cm2", unit="cm²"),
                      ColumnDef("I_cm4", unit="cm⁴"), ColumnDef("r_cm", unit="cm"),
                      ColumnDef("Z_cm3", unit="cm³"), ColumnDef("S_cm3", unit="cm³"),
                      ColumnDef("J_cm4", unit="cm⁴"), ColumnDef("C_cm3", unit="cm³"),
                      ColumnDef("superficial_area_m2", unit="m²/m"),
                      ColumnDef("length_per_tonne_m", unit="m"),
                  ]),
        PageGroup(pages=[108, 109], skip_header_rows=8,
                  footer_pattern=FOOTER_PATTERN, section_pattern=SECTION_PATTERN_DIM,
                  value_count=15,
                  columns=[
                      ColumnDef("wall_thickness_mm", unit="mm"), ColumnDef("weight_kg_m", unit="kg/m"),
                      ColumnDef("area_cm2", unit="cm²"),
                      ColumnDef("Ix_cm4", unit="cm⁴"), ColumnDef("Iy_cm4", unit="cm⁴"),
                      ColumnDef("ix_cm", unit="cm"), ColumnDef("iy_cm", unit="cm"),
                      ColumnDef("Zx_cm3", unit="cm³"), ColumnDef("Zy_cm3", unit="cm³"),
                      ColumnDef("Sx_cm3", unit="cm³"), ColumnDef("Sy_cm3", unit="cm³"),
                      ColumnDef("J_cm4", unit="cm⁴"), ColumnDef("C_cm3", unit="cm³"),
                      ColumnDef("superficial_area_m2", unit="m²/m"),
                      ColumnDef("length_per_tonne_m", unit="m"),
                  ]),
        PageGroup(pages=[110, 111], skip_header_rows=7,
                  footer_pattern=FOOTER_PATTERN, section_pattern=SECTION_PATTERN_NUMERIC,
                  value_count=10,
                  columns=[
                      ColumnDef("wall_thickness_mm", unit="mm"), ColumnDef("weight_kg_m", unit="kg/m"),
                      ColumnDef("area_cm2", unit="cm²"),
                      ColumnDef("I_cm4", unit="cm⁴"), ColumnDef("r_cm", unit="cm"),
                      ColumnDef("Z_cm3", unit="cm³"), ColumnDef("S_cm3", unit="cm³"),
                      ColumnDef("J_cm4", unit="cm⁴"), ColumnDef("C_cm3", unit="cm³"),
                      ColumnDef("superficial_area_m2", unit="m²/m"),
                  ]),
    ]))

# ── PIPES (pages 112-125) ──
LEAVES.append(skip("technical_specs_and_standards", list(range(112, 116))))
LEAVES.append(LeafSchema(
    leaf_id="bs_welded_steel_pipes",
    name="BS 1387 Welded Steel Pipes",
    pages=[117],
    page_groups=[
        PageGroup(pages=[117], skip_header_rows=7,
                  footer_pattern=FOOTER_PATTERN, section_pattern=r"",
                  parser="bs1387", max_data_rows=18,
                  columns=[
                      ColumnDef("od_max_mm", unit="mm"),
                      ColumnDef("od_min_mm", unit="mm"),
                      ColumnDef("wall_thickness_mm", unit="mm"),
                      ColumnDef("weight_plain_kg_m", unit="kg/m"),
                      ColumnDef("weight_plain_kg_ft", unit="kg/ft"),
                      ColumnDef("weight_coupling_kg_m", unit="kg/m"),
                      ColumnDef("weight_coupling_kg_ft", unit="kg/ft"),
                      ColumnDef("threads_per_inch"),
                      ColumnDef("socket_od_mm", unit="mm"),
                      ColumnDef("socket_length_min_mm", unit="mm"),
                  ]),
    ],
))

LEAVES.append(LeafSchema(
    leaf_id="carbon_steel_for_general_structural",
    name="Carbon Steel Pipes for General Structural JIS G3444",
    pages=[120, 125],
    page_groups=[
        PageGroup(pages=[120], skip_header_rows=6,
                  footer_pattern=FOOTER_PATTERN_TOL, section_pattern=SECTION_PATTERN_PIPE_NOM_FRAC,
                  value_count=8,
                  columns=[
                      ColumnDef("nominal_mm", unit="mm"),
                      ColumnDef("od_min_mm", unit="mm"), ColumnDef("od_max_mm", unit="mm"),
                      ColumnDef("wall_in", unit="in"), ColumnDef("wall_mm", unit="mm"),
                      ColumnDef("weight_kg_m", unit="kg/m"),
                      ColumnDef("weight_kg_ft", unit="kg/ft"), ColumnDef("weight_lb_ft", unit="lb/ft"),
                  ]),
        PageGroup(pages=[125], skip_header_rows=7,
                  footer_pattern=FOOTER_PATTERN_STK, section_pattern=SECTION_PATTERN_STK_OD,
                  value_count=6,
                  columns=[
                      ColumnDef("wall_thickness_mm", unit="mm"), ColumnDef("weight_kg_m", unit="kg/m"),
                      ColumnDef("area_cm2", unit="cm²"),
                      ColumnDef("I_cm4", unit="cm⁴"), ColumnDef("Z_cm3", unit="cm³"),
                      ColumnDef("r_cm", unit="cm"),
                  ]),
    ]))

LEAVES.append(LeafSchema(
    leaf_id="carbon_steel_for_scaffolding",
    name="Carbon Steel Pipes for Scaffolding JIS G3444",
    pages=[121],
    page_groups=[
        PageGroup(pages=[121], skip_header_rows=8,
                  footer_pattern=FOOTER_PATTERN, section_pattern=r"",
                  parser="scaffolding",
                  columns=[
                      ColumnDef("stk_grade"),
                      ColumnDef("od_min_mm", unit="mm"),
                      ColumnDef("od_max_mm", unit="mm"),
                      ColumnDef("wall_thickness_mm", unit="mm"),
                      ColumnDef("weight_kg_m", unit="kg/m"),
                      ColumnDef("area_cm2", unit="cm²"),
                      ColumnDef("moment_inertia_cm4", unit="cm⁴"),
                      ColumnDef("section_modulus_cm3", unit="cm³"),
                      ColumnDef("gyration_radius_cm", unit="cm"),
                  ]),
    ],
))

LEAVES.append(LeafSchema(
    leaf_id="carbon_steel_for_ordinary_piping",
    name="Carbon Steel Pipes for Ordinary Piping JIS G3452",
    pages=[122],
    page_groups=[
        PageGroup(pages=[122], skip_header_rows=5,
                  footer_pattern=FOOTER_PATTERN, section_pattern=SECTION_PATTERN_PIPE_NOM_DUAL,
                  value_count=8,
                  columns=[
                      ColumnDef("od_mm", unit="mm"), ColumnDef("od_in", unit="in"),
                      ColumnDef("wall_mm", unit="mm"), ColumnDef("wall_in", unit="in"),
                      ColumnDef("weight_lb_ft", unit="lb/ft"), ColumnDef("weight_kg_m", unit="kg/m"),
                      ColumnDef("test_pressure_kg", unit="kg/cm²"),
                      ColumnDef("test_pressure_psi", unit="psi"),
                  ]),
    ]))

LEAVES.append(skip("carbon_steel_for_machine_structural", [123, 124]))

# ── CHANNELS (pages 126-135) ──
LEAVES.append(skip("product_list_channels", [126]))
LEAVES.append(skip("safe_loads_channels", [127]))

LEAVES.append(LeafSchema(
    leaf_id="plain_channels",
    name="Plain Channels JIS G3350",
    pages=[128],
    page_groups=[
        PageGroup(pages=[128], skip_header_rows=7,
                  footer_pattern=FOOTER_PATTERN, section_pattern=SECTION_PATTERN_DIM,
                  value_count=14,
                  columns=[
                      ColumnDef("weight_kg_m", unit="kg/m"), ColumnDef("thickness_mm", unit="mm"),
                      ColumnDef("area_cm2", unit="cm²"),
                      ColumnDef("Cx_cm", unit="cm"), ColumnDef("Cy_cm", unit="cm"),
                      ColumnDef("Ix_cm4", unit="cm⁴"), ColumnDef("Iy_cm4", unit="cm⁴"),
                      ColumnDef("Rx_cm", unit="cm"), ColumnDef("Ry_cm", unit="cm"),
                      ColumnDef("Zx_cm3", unit="cm³"), ColumnDef("Zy_cm3", unit="cm³"),
                      ColumnDef("Mx_kg_m", unit="kg/m"), ColumnDef("M", unit="cm"),
                      ColumnDef("Q", unit="kg/m"),
                  ]),
    ]))

LEAVES.append(LeafSchema(
    leaf_id="lipped_channels",
    name="Lipped Channels JIS G3350",
    pages=[129],
    page_groups=[
        PageGroup(pages=[129], skip_header_rows=7,
                  footer_pattern=FOOTER_PATTERN, section_pattern=SECTION_PATTERN_DIM,
                  value_count=15,
                  columns=[
                      ColumnDef("weight_kg_m", unit="kg/m"), ColumnDef("thickness_mm", unit="mm"),
                      ColumnDef("area_cm2", unit="cm²"),
                      ColumnDef("Cx_cm", unit="cm"), ColumnDef("Cy_cm", unit="cm"),
                      ColumnDef("Ix_cm4", unit="cm⁴"), ColumnDef("Iy_cm4", unit="cm⁴"),
                      ColumnDef("Rx_cm", unit="cm"), ColumnDef("Ry_cm", unit="cm"),
                      ColumnDef("Zx_cm3", unit="cm³"), ColumnDef("Zy_cm3", unit="cm³"),
                      ColumnDef("Zx1_cm3", unit="cm³"),
                      ColumnDef("Mx_kg_m", unit="kg/m"), ColumnDef("M", unit="cm"),
                      ColumnDef("Q", unit="kg/m"),
                  ]),
    ]))

LEAVES.append(LeafSchema(
    leaf_id="din_1026_channels",
    name="DIN 1026 Channels",
    pages=[130],
    page_groups=[
        PageGroup(pages=[130], skip_header_rows=7,
                  footer_pattern=FOOTER_PATTERN, section_pattern=SECTION_PATTERN_DIM,
                  value_count=19,
                  columns=[
                      ColumnDef("height_h_mm", unit="mm"), ColumnDef("width_b_mm", unit="mm"),
                      ColumnDef("web_s_mm", unit="mm"), ColumnDef("flange_t_mm", unit="mm"),
                      ColumnDef("r1_mm", unit="mm"), ColumnDef("r2_mm", unit="mm"),
                      ColumnDef("area_cm2", unit="cm²"), ColumnDef("weight_kg_m", unit="kg/m"),
                      ColumnDef("surface_m2", unit="m²/m"),
                      ColumnDef("Jx_cm4", unit="cm⁴"), ColumnDef("Wx_cm3", unit="cm³"),
                      ColumnDef("ix_cm", unit="cm"),
                      ColumnDef("Jy_cm4", unit="cm⁴"), ColumnDef("Wy_cm3", unit="cm³"),
                      ColumnDef("iy_cm", unit="cm"),
                      ColumnDef("Sx_cm3", unit="cm³"), ColumnDef("sx_cm3", unit="cm³"),
                      ColumnDef("ey_cm", unit="cm"), ColumnDef("XM", unit="cm"),
                  ]),
    ]))

LEAVES.append(LeafSchema(
    leaf_id="u_channels",
    name="U-Channels",
    pages=[131, 132, 133, 134],
    page_groups=[
        PageGroup(pages=[131, 133], skip_header_rows=6,
                  footer_pattern=FOOTER_PATTERN, section_pattern=SECTION_PATTERN_DIM_OPT_IMPERIAL,
                  value_count=14,
                  columns=[
                      ColumnDef("weight_kg_m", unit="kg/m"), ColumnDef("weight_lb_ft", unit="lb/ft"),
                      ColumnDef("depth_A_mm", unit="mm"), ColumnDef("depth_A_in", unit="in"),
                      ColumnDef("width_B_mm", unit="mm"), ColumnDef("width_B_in", unit="in"),
                      ColumnDef("flange_thickness_t1_mm", unit="mm"),
                      ColumnDef("flange_thickness_t1_in", unit="in"),
                      ColumnDef("web_thickness_t2_mm", unit="mm"),
                      ColumnDef("web_thickness_t2_in", unit="in"),
                      ColumnDef("corner_r1_mm", unit="mm"), ColumnDef("corner_r1_in", unit="in"),
                      ColumnDef("r2_mm", unit="mm"), ColumnDef("r2_in", unit="in"),
                  ]),
        PageGroup(pages=[132, 134], skip_header_rows=8,
                  footer_pattern=FOOTER_PATTERN, section_pattern=SECTION_PATTERN_DIM_OPT_IMPERIAL,
                  value_count=16,
                  columns=[
                      ColumnDef("area_cm2", unit="cm²"), ColumnDef("area_in2", unit="in²"),
                      ColumnDef("y_cm", unit="cm"), ColumnDef("y_in", unit="in"),
                      ColumnDef("Ix_cm4", unit="cm⁴"), ColumnDef("Ix_in4", unit="in⁴"),
                      ColumnDef("Iy_cm4", unit="cm⁴"), ColumnDef("Iy_in4", unit="in⁴"),
                      ColumnDef("ix_cm", unit="cm"), ColumnDef("ix_in", unit="in"),
                      ColumnDef("iy_cm", unit="cm"), ColumnDef("iy_in", unit="in"),
                      ColumnDef("Zx_cm3", unit="cm³"), ColumnDef("Zx_in3", unit="in³"),
                      ColumnDef("Zy_cm3", unit="cm³"), ColumnDef("Zy_in3", unit="in³"),
                  ]),
    ]))

LEAVES.append(LeafSchema(
    leaf_id="inch_series",
    name="U-Channel Inch Series",
    pages=[135],
    page_groups=[
        PageGroup(pages=[135], skip_header_rows=10,
                  footer_pattern=FOOTER_PATTERN, section_pattern=SECTION_PATTERN_INCH_CHANNEL,
                  value_count=12,
                  columns=[
                      ColumnDef("depth_H_in", unit="in"), ColumnDef("width_B_in", unit="in"),
                      ColumnDef("flange_t1_in", unit="in"), ColumnDef("web_t2_in", unit="in"),
                      ColumnDef("fillet_r_in", unit="in"), ColumnDef("area_in2", unit="in²"),
                      ColumnDef("weight_kg_m", unit="kg/m"), ColumnDef("weight_kg_ft", unit="kg/ft"),
                      ColumnDef("weight_lb_ft", unit="lb/ft"),
                      ColumnDef("weight_20ft_kg", unit="kg"), ColumnDef("weight_30ft_kg", unit="kg"),
                      ColumnDef("weight_40ft_kg", unit="kg"),
                  ]),
    ]))

# ── PURLINS (pages 136-140) ──
LEAVES.append(LeafSchema(
    leaf_id="z_purlins_high_tensile_galvanised",
    name="High-Tensile Galvanised Z-Purlins",
    pages=[136, 137],
    page_groups=[
        PageGroup(pages=[137], skip_header_rows=6,
                  footer_pattern=FOOTER_PATTERN, section_pattern=SECTION_PATTERN_PURLIN_Z,
                  value_count=7,
                  columns=[
                      ColumnDef("depth_A_mm", unit="mm"), ColumnDef("width_B_mm", unit="mm"),
                      ColumnDef("flange_C_mm", unit="mm"), ColumnDef("lip_D_mm", unit="mm"),
                      ColumnDef("thickness_t_mm", unit="mm"),
                      ColumnDef("area_mm2", unit="mm²"), ColumnDef("mass_kg_m", unit="kg/m"),
                  ]),
    ]))

LEAVES.append(LeafSchema(
    leaf_id="c_purlins_high_tensile_galvanised",
    name="High-Tensile Galvanised C-Purlins",
    pages=[138, 139],
    page_groups=[
        PageGroup(pages=[139], skip_header_rows=6,
                  footer_pattern=FOOTER_PATTERN, section_pattern=SECTION_PATTERN_PURLIN_C,
                  value_count=6,
                  columns=[
                      ColumnDef("depth_A_mm", unit="mm"), ColumnDef("width_B_mm", unit="mm"),
                      ColumnDef("flange_C_mm", unit="mm"), ColumnDef("lip_D_mm", unit="mm"),
                      ColumnDef("thickness_t_mm", unit="mm"), ColumnDef("mass_kg_m", unit="kg/m"),
                  ]),
    ]))

LEAVES.append(skip("purlin_selection_tables", [140]))

# ── ANGLES (pages 142-151) ──
LEAVES.append(skip("product_list_angles", [142]))
LEAVES.append(skip("inverted_angles", [151]))

LEAVES.append(LeafSchema(
    leaf_id="equal_angles",
    name="Equal Angles",
    pages=[143, 144],
    page_groups=[
        PageGroup(pages=[143, 144], skip_header_rows=6,
                  footer_pattern=FOOTER_PATTERN, section_pattern=SECTION_PATTERN_DIM,
                  value_count=9,
                  columns=[
                      ColumnDef("thickness_mm", unit="mm"), ColumnDef("weight_kg_m", unit="kg/m"),
                      ColumnDef("fillet_radius_mm", unit="mm"),
                      ColumnDef("area_cm2", unit="cm²"), ColumnDef("Cx_cm", unit="cm"),
                      ColumnDef("I_cm4", unit="cm⁴"), ColumnDef("i_cm", unit="cm"),
                      ColumnDef("iv_cm", unit="cm"), ColumnDef("Z_cm3", unit="cm³"),
                  ]),
    ]))

LEAVES.append(LeafSchema(
    leaf_id="unequal_angles",
    name="Unequal Angles",
    pages=[145, 146, 147, 148, 149, 150],
    page_groups=[
        PageGroup(pages=[145, 147, 149], skip_header_rows=6,
                  footer_pattern=FOOTER_PATTERN, section_pattern=SECTION_PATTERN_DIM,
                  value_count=10,
                  columns=[
                      ColumnDef("thickness_mm", unit="mm"), ColumnDef("weight_kg_m", unit="kg/m"),
                      ColumnDef("weight_lb_ft", unit="lb/ft"),
                      ColumnDef("leg_A_mm", unit="mm"), ColumnDef("leg_A_in", unit="in"),
                      ColumnDef("leg_B_mm", unit="mm"), ColumnDef("leg_B_in", unit="in"),
                      ColumnDef("r1_mm", unit="mm"), ColumnDef("r2_mm", unit="mm"),
                      ColumnDef("r2_in", unit="in"),
                  ]),
        PageGroup(pages=[146, 148, 150], skip_header_rows=6,
                  footer_pattern=FOOTER_PATTERN, section_pattern=SECTION_PATTERN_DIM,
                  value_count=21,
                  columns=[
                      ColumnDef("Ix_cm4", unit="cm⁴"), ColumnDef("Ix_in4", unit="in⁴"),
                      ColumnDef("Iy_cm4", unit="cm⁴"), ColumnDef("Iy_in4", unit="in⁴"),
                      ColumnDef("Iu_cm4", unit="cm⁴"), ColumnDef("Iu_in4", unit="in⁴"),
                      ColumnDef("Iv_cm4", unit="cm⁴"), ColumnDef("Iv_in4", unit="in⁴"),
                      ColumnDef("ix_cm", unit="cm"), ColumnDef("ix_in", unit="in"),
                      ColumnDef("iy_cm", unit="cm"), ColumnDef("iy_in", unit="in"),
                      ColumnDef("iu_cm", unit="cm"), ColumnDef("iu_in", unit="in"),
                      ColumnDef("iv_cm", unit="cm"), ColumnDef("iv_in", unit="in"),
                      ColumnDef("tan_a"),
                      ColumnDef("Zx_cm3", unit="cm³"), ColumnDef("Zx_in3", unit="in³"),
                      ColumnDef("Zy_cm3", unit="cm³"), ColumnDef("Zy_in3", unit="in³"),
                  ]),
    ]))

# ── BARS (pages 152-157) ──
LEAVES.append(skip("product_list_bars", [152]))
LEAVES.append(LeafSchema(
    leaf_id="flat_bars",
    name="Flat Bars",
    pages=[153, 154],
    page_groups=[
        PageGroup(pages=[153, 154], skip_header_rows=6,
                  footer_pattern=FOOTER_PATTERN,
                  section_pattern=r"^(\d+\.?\d*\s+\d+\.?\d*)",
                  value_count=6,
                  columns=[
                      ColumnDef("left_M_kg_m", unit="kg/m"),
                      ColumnDef("left_A_cm2", unit="cm²"),
                      ColumnDef("right_thickness_mm", unit="mm"),
                      ColumnDef("right_width_mm", unit="mm"),
                      ColumnDef("right_M_kg_m", unit="kg/m"),
                      ColumnDef("right_A_cm2", unit="cm²"),
                  ]),
    ]))

LEAVES.append(LeafSchema(
    leaf_id="bulb_flats",
    name="Bulb Flats",
    pages=[155],
    page_groups=[
        PageGroup(pages=[155], skip_header_rows=8,
                  footer_pattern=FOOTER_PATTERN, section_pattern=SECTION_PATTERN_NUMERIC,
                  value_count=4,
                  columns=[
                      ColumnDef("thickness_mm", unit="mm"), ColumnDef("bulb_height_mm", unit="mm"),
                      ColumnDef("area_cm2", unit="cm²"), ColumnDef("mass_kg_m", unit="kg/m"),
                  ]),
    ]))

LEAVES.append(LeafSchema(
    leaf_id="square_deformed_and_round_bars",
    name="Square, Deformed and Round Bars",
    pages=[156, 157],
    page_groups=[
        PageGroup(pages=[156], skip_header_rows=5,
                  footer_pattern=FOOTER_PATTERN, section_pattern=SECTION_PATTERN_NUMERIC,
                  value_count=9,
                  columns=[
                      ColumnDef("weight_kg_m", unit="kg/m"), ColumnDef("weight_lb_ft", unit="lb/ft"),
                      ColumnDef("side_mm", unit="mm"), ColumnDef("side_in", unit="in"),
                      ColumnDef("area_cm2", unit="cm²"), ColumnDef("area_in2", unit="in²"),
                      ColumnDef("I_in4", unit="in⁴"), ColumnDef("i_in", unit="in"),
                      ColumnDef("Z_in3", unit="in³"),
                  ]),
        PageGroup(pages=[157], skip_header_rows=7,
                  footer_pattern=FOOTER_PATTERN, section_pattern=SECTION_PATTERN_NUMERIC,
                  value_count=2,
                  columns=[
                      ColumnDef("weight_kg_m", unit="kg/m"), ColumnDef("area_cm2", unit="cm²"),
                  ]),
    ]))

# ── PLATES (pages 158-176) ──
LEAVES.append(skip("product_list_plates", [158]))
LEAVES.append(skip("specifications_plates", list(range(159, 168))))
LEAVES.append(LeafSchema(
    leaf_id="weight_tables_plates",
    name="Steel Plates Weight Table — Imperial and Metric",
    pages=[168, 169],
    page_groups=[
        PageGroup(pages=[168], skip_header_rows=6,
                  footer_pattern=FOOTER_PATTERN, merge_fractions=True,
                  section_pattern=r"^(\d+(?:/\d+)?)", value_count=10,
                  section_suffix="in",
                  columns=[
                      ColumnDef("thickness_mm", unit="mm"),
                      ColumnDef("unit_weight_kg_ft2", unit="kg/ft²"),
                      ColumnDef("wt_4x8"),
                      ColumnDef("wt_5x10"),
                      ColumnDef("wt_5x20"),
                      ColumnDef("wt_5x30"),
                      ColumnDef("wt_6x20"),
                      ColumnDef("wt_6x24"),
                      ColumnDef("wt_6x30"),
                      ColumnDef("wt_8x30"),
                  ]),
        PageGroup(pages=[169], skip_header_rows=6,
                  footer_pattern=FOOTER_PATTERN,
                  section_pattern=r"^(\d+(?:\.\d+)?)", value_count=12,
                  columns=[
                      ColumnDef("unit_weight_kg", unit="kg"),
                      ColumnDef("wt_3x6"),
                      ColumnDef("wt_4x8"),
                      ColumnDef("wt_4x10"),
                      ColumnDef("wt_4x16"),
                      ColumnDef("wt_4x20"),
                      ColumnDef("wt_5x10"),
                      ColumnDef("wt_5x20"),
                      ColumnDef("wt_5x30"),
                      ColumnDef("wt_5x40"),
                      ColumnDef("wt_6x30"),
                      ColumnDef("wt_6x40"),
                  ]),
    ],
))
LEAVES.append(skip("technical_reference_plates", [170]))
LEAVES.append(LeafSchema(
    leaf_id="chequered_plates",
    name="Chequered (Floor) Plates Weight Table",
    pages=[171],
    page_groups=[
        PageGroup(pages=[171], skip_header_rows=6,
                  footer_pattern=FOOTER_PATTERN,
                  section_pattern=SECTION_PATTERN_NUMERIC,
                  value_count=9, parser="token",
                  columns=[
                      ColumnDef("unit_weight_kg_m2", unit="kg/m²"),
                      ColumnDef("wt_914x1829"),
                      ColumnDef("wt_914x3658"),
                      ColumnDef("wt_1219x2438"),
                      ColumnDef("wt_1219x3048"),
                      ColumnDef("wt_1219x4877"),
                      ColumnDef("wt_1219x6096"),
                      ColumnDef("wt_1524x3048"),
                      ColumnDef("wt_1524x6096"),
                  ]),
        PageGroup(pages=[171], skip_header_rows=19,
                  footer_pattern=FOOTER_PATTERN,
                  section_pattern=SECTION_PATTERN_NUMERIC,
                  value_count=9, parser="token",
                  columns=[
                      ColumnDef("unit_weight_lb_ft2", unit="lb/ft²"),
                      ColumnDef("wt_3x6_ft"),
                      ColumnDef("wt_3x12_ft"),
                      ColumnDef("wt_4x8_ft"),
                      ColumnDef("wt_4x10_ft"),
                      ColumnDef("wt_4x16_ft"),
                      ColumnDef("wt_4x20_ft"),
                      ColumnDef("wt_5x10_ft"),
                      ColumnDef("wt_5x20_ft"),
                  ]),
    ],
))
LEAVES.append(skip("cold_rolled_coils_and_sheets", [172, 173]))
LEAVES.append(LeafSchema(
    leaf_id="electrolytic_galvanised",
    name="Electrolytic Galvanised Coils and Sheets — Weight Table",
    pages=[174],
    page_groups=[
        PageGroup(pages=[174], skip_header_rows=17,
                  footer_pattern=FOOTER_PATTERN,
                  section_pattern=r"^([\d.]+)", value_count=1,
                  parser="paired",
                  columns=[ColumnDef("weight_kg_sht")]),
    ],
))
LEAVES.append(skip("hot_dip_galvanised", [175]))
LEAVES.append(LeafSchema(
    leaf_id="galvanised_steel_sheets_dimensions",
    name="Galvanised Steel Sheets Dimensions JIS G3302",
    pages=[176],
    page_groups=[
        PageGroup(pages=[176], skip_header_rows=9, footer_pattern=FOOTER_PATTERN,
                  section_pattern=r"^([\d.]+)",
                  value_count=9, parser="token",
                  columns=[
                      ColumnDef("z18_kg_pc", unit="kg/pc"),
                      ColumnDef("z18_ib_pc", unit="lb/pc"),
                      ColumnDef("z18_pcs_mt", unit="pcs/mt"),
                      ColumnDef("z22_kg_pc", unit="kg/pc"),
                      ColumnDef("z22_ib_pc", unit="lb/pc"),
                      ColumnDef("z22_pcs_mt", unit="pcs/mt"),
                      ColumnDef("z27_kg_pc", unit="kg/pc"),
                      ColumnDef("z27_ib_pc", unit="lb/pc"),
                      ColumnDef("z27_pcs_mt", unit="pcs/mt"),
                  ]),
    ],
))

# ── GRATINGS / EXPANDED METAL (pages 177-179) ──
LEAVES.append(skip("galvanised_serrated_gratings", [177]))
LEAVES.append(skip("expanded_metal", [178, 179]))

# ── WROUGHT STEEL FITTINGS (pages 180-187) ──
LEAVES.append(skip("product_list_wrought_fittings", [180]))
# Fittings pages: skip for now (complex layouts)
for leaf_id, leaf_pages in [
    ("fitting_ends_and_45_degree_elbows", [181]),
    ("90_degree_elbows_wrought", [182]),
    ("180_degree_returns_wrought", [183]),
    ("reducers_wrought", [184, 185]),
    ("tees_wrought", [186]),
    ("reducing_fittings_wrought", [187]),
]:
    LEAVES.append(skip(leaf_id, leaf_pages))

# ── FLANGES (pages 188-205) ──
# JIS 5K and 10K share page 188 (5K data rows 7-27, 10K data rows 33-53)
SECTION_FLANGE_NOM = r"^(\d+(?:-\d+/\d+)?(?:/\d+)?)"
LEAVES.append(LeafSchema(
    leaf_id="jis_5k", name="JIS 5K Slip-On Flanges (JIS B2220)",
    pages=[188],
    page_groups=[PageGroup(pages=[188], skip_header_rows=7,
                  footer_pattern=FOOTER_PATTERN,
                  section_pattern=SECTION_FLANGE_NOM,
                  value_count=10, max_data_rows=21,
                  columns=[
                      ColumnDef("nominal_mm", type="float", unit="mm"),
                      ColumnDef("pipe_od_mm", type="float", unit="mm"),
                      ColumnDef("pipe_id_mm", type="float", unit="mm"),
                      ColumnDef("flange_od_mm", type="float", unit="mm"),
                      ColumnDef("thickness_mm", type="float", unit="mm"),
                      ColumnDef("bolt_circle_mm", type="float", unit="mm"),
                      ColumnDef("hole_count", type="int"),
                      ColumnDef("hole_dia_mm", type="float", unit="mm"),
                      ColumnDef("bolt_size", type="string"),
                      ColumnDef("weight_kg", type="float", unit="kg"),
                  ])],
))
LEAVES.append(LeafSchema(
    leaf_id="jis_10k", name="JIS 10K Slip-On Flanges (JIS B2220)",
    pages=[188],
    page_groups=[PageGroup(pages=[188], skip_header_rows=33,
                  footer_pattern=FOOTER_PATTERN,
                  section_pattern=SECTION_FLANGE_NOM,
                  value_count=10,
                  columns=[
                      ColumnDef("nominal_mm", type="float", unit="mm"),
                      ColumnDef("pipe_od_mm", type="float", unit="mm"),
                      ColumnDef("pipe_id_mm", type="float", unit="mm"),
                      ColumnDef("flange_od_mm", type="float", unit="mm"),
                      ColumnDef("thickness_mm", type="float", unit="mm"),
                      ColumnDef("bolt_circle_mm", type="float", unit="mm"),
                      ColumnDef("hole_count", type="int"),
                      ColumnDef("hole_dia_mm", type="float", unit="mm"),
                      ColumnDef("bolt_size", type="string"),
                      ColumnDef("weight_kg", type="float", unit="kg"),
                  ])],
))
LEAVES.append(LeafSchema(
    leaf_id="ansi_150lb_blind", name="ANSI 150LB Blind Flanges (ANSI B16.5)",
    pages=[189],
    page_groups=[PageGroup(pages=[189], skip_header_rows=7,
                  footer_pattern=FOOTER_PATTERN,
                  section_pattern=SECTION_FLANGE_NOM,
                  value_count=7, max_data_rows=20,
                  columns=[
                      ColumnDef("flange_od", type="float", unit="in"),
                      ColumnDef("thickness", type="float", unit="in"),
                      ColumnDef("raised_face_dia", type="float", unit="in"),
                      ColumnDef("hole_count", type="int"),
                      ColumnDef("bolt_dia", type="float", unit="in"),
                      ColumnDef("bolt_circle_dia", type="float", unit="in"),
                      ColumnDef("weight_kg", type="float", unit="kg"),
                  ])],
))
LEAVES.append(LeafSchema(
    leaf_id="ansi_300lb_blind", name="ANSI 300LB Blind Flanges (ANSI B16.5)",
    pages=[189],
    page_groups=[PageGroup(pages=[189], skip_header_rows=32,
                  footer_pattern=FOOTER_PATTERN,
                  section_pattern=SECTION_FLANGE_NOM,
                  value_count=7,
                  columns=[
                      ColumnDef("flange_od", type="float", unit="in"),
                      ColumnDef("thickness", type="float", unit="in"),
                      ColumnDef("raised_face_dia", type="float", unit="in"),
                      ColumnDef("hole_count", type="int"),
                      ColumnDef("bolt_dia", type="float", unit="in"),
                      ColumnDef("bolt_circle_dia", type="float", unit="in"),
                      ColumnDef("weight_kg", type="float", unit="kg"),
                  ])],
))
LEAVES.append(LeafSchema(
    leaf_id="ansi_150lb_slip_on", name="ANSI 150LB Slip-On Flanges (ANSI B16.5)",
    pages=[190],
    page_groups=[PageGroup(pages=[190], skip_header_rows=6,
                  footer_pattern=FOOTER_PATTERN,
                  section_pattern=SECTION_FLANGE_NOM,
                  value_count=10, max_data_rows=20,
                  columns=[
                      ColumnDef("flange_od", type="float", unit="in"),
                      ColumnDef("thickness", type="float", unit="in"),
                      ColumnDef("raised_face_dia", type="float", unit="in"),
                      ColumnDef("hub_dia", type="float", unit="in"),
                      ColumnDef("hub_length", type="float", unit="in"),
                      ColumnDef("bore_dia", type="float", unit="in"),
                      ColumnDef("hole_count", type="int"),
                      ColumnDef("bolt_dia", type="float", unit="in"),
                      ColumnDef("bolt_circle_dia", type="float", unit="in"),
                      ColumnDef("weight_kg", type="float", unit="kg"),
                  ])],
))
LEAVES.append(LeafSchema(
    leaf_id="ansi_300lb_slip_on", name="ANSI 300LB Slip-On Flanges (ANSI B16.5)",
    pages=[190],
    page_groups=[PageGroup(pages=[190], skip_header_rows=31,
                  footer_pattern=FOOTER_PATTERN,
                  section_pattern=SECTION_FLANGE_NOM,
                  value_count=10,
                  columns=[
                      ColumnDef("flange_od", type="float", unit="in"),
                      ColumnDef("thickness", type="float", unit="in"),
                      ColumnDef("raised_face_dia", type="float", unit="in"),
                      ColumnDef("hub_dia", type="float", unit="in"),
                      ColumnDef("hub_length", type="float", unit="in"),
                      ColumnDef("bore_dia", type="float", unit="in"),
                      ColumnDef("hole_count", type="int"),
                      ColumnDef("bolt_dia", type="float", unit="in"),
                      ColumnDef("bolt_circle_dia", type="float", unit="in"),
                      ColumnDef("weight_kg", type="float", unit="kg"),
                  ])],
))
# Rest of flanges: skip for now
for leaf_id, leaf_pages in [
    ("ansi_150lb_welding_neck", [191]), ("ansi_300lb_welding_neck", [191]),
    ("ansi_class_600", [192]), ("ansi_class_900", [192]), ("ansi_class_1500", [193]),
    ("bs_slip_on_pn_6", [194]), ("bs_slip_on_pn_10", [194]),
    ("bs_slip_on_pn_16", [195]), ("bs_slip_on_pn_25", [195]),
    ("bs_slip_on_pn_40", [196]), ("bs_slip_on_pn_64", [196]),
    ("bs_slip_on_pn_100", [197]), ("bs_slip_on_pn_160", [197]),
    ("bs_slip_on_pn_250", [198]),
    ("din_welding_neck_pn_16", [199]), ("din_welding_neck_pn_40", [200]),
    ("bs10_table_a", [201]), ("bs10_table_d", [201]),
    ("bs10_table_e", [202]), ("bs10_table_f", [202]),
    ("bs10_table_h", [203]), ("bs10_table_j", [203]),
    ("bs10_table_k", [204]), ("bs10_table_r", [204]),
    ("bs10_table_s", [205]), ("bs10_table_t", [205]),
]:
    LEAVES.append(skip(leaf_id, leaf_pages))

# ── STAINLESS STEEL PRODUCTS (pages 206-246) ──
LEAVES.append(skip("general_information", [206, 207, 208, 209]))
LEAVES.append(skip("coils_sheets", [210]))
LEAVES.append(skip("sheets_plates", [211, 212, 213, 214]))
LEAVES.append(LeafSchema(
    leaf_id="sheets_plates_weights",
    name="Stainless Steel Sheets and Plates Weights",
    pages=[215],
    page_groups=[
        PageGroup(pages=[215], skip_header_rows=6,
                  footer_pattern=FOOTER_PATTERN, section_pattern=r"^(\d+\.?\d*)",
                  value_count=8,
                  columns=[
                      ColumnDef("weight_304_4x8_kg_pc", unit="kg/pc"),
                      ColumnDef("pcs_mt_304_4x8", unit="pcs/mt"),
                      ColumnDef("weight_316_4x8_kg_pc", unit="kg/pc"),
                      ColumnDef("pcs_mt_316_4x8", unit="pcs/mt"),
                      ColumnDef("weight_304_5x10_kg_pc", unit="kg/pc"),
                      ColumnDef("pcs_mt_304_5x10", unit="pcs/mt"),
                      ColumnDef("weight_316_5x10_kg_pc", unit="kg/pc"),
                      ColumnDef("pcs_mt_316_5x10", unit="pcs/mt"),
                  ]),
    ]))
LEAVES.append(skip("angles_stainless", [216, 217, 218]))
LEAVES.append(skip("flats_stainless", [219]))
SECTION_PATTERN_UNS = r"^([A-Za-z0-9\s()/.·°’‘-]+)"

LEAVES.append(LeafSchema(
    leaf_id="round_bars_stainless",
    name="Stainless Steel Round Bars",
    pages=[220, 221, 222],
    page_groups=[
        PageGroup(pages=[220, 221, 222], skip_header_rows=5,
                  footer_pattern=FOOTER_PATTERN,
                  section_pattern=r"^(\d+\s*\([A-Z]\d+\))",
                  value_count=12, parser="two_row", join_remaining=True,
                  columns=[
                      ColumnDef("JIS"), ColumnDef("BS"), ColumnDef("DIN"),
                      ColumnDef("C_percent"), ColumnDef("Mn_percent"),
                      ColumnDef("P_percent"), ColumnDef("S_percent"),
                      ColumnDef("Si_percent"),
                      ColumnDef("Cr_percent"), ColumnDef("Ni_percent"),
                      ColumnDef("Mo_percent"), ColumnDef("other_elements"),
                  ]),
    ]))
LEAVES.append(skip("hexagon_square_bars_stainless", [224]))
LEAVES.append(LeafSchema(
    leaf_id="welded_channels_stainless",
    name="Stainless Steel Welded Channels",
    pages=[225],
    page_groups=[
        PageGroup(pages=[225], skip_header_rows=5,
                  footer_pattern=FOOTER_PATTERN, section_pattern=SECTION_PATTERN_DIM_OPT_IMPERIAL,
                  value_count=4,
                  columns=[
                      ColumnDef("tolerance_d_in", unit="in"), ColumnDef("tolerance_bf_in", unit="in"),
                      ColumnDef("weight_304_lb_ft", unit="lb/ft"),
                      ColumnDef("weight_316_lb_ft", unit="lb/ft"),
                  ]),
    ]))
LEAVES.append(skip("welded_tubings_stainless", [226, 227, 228, 229]))

# Stainless steel pipes
LEAVES.append(skip("pipes_stainless", [230, 231, 232, 233, 234]))

# Stainless steel fittings
for leaf_id, leaf_pages in [
    ("elbows_90_long_radius", [236]),
    ("elbows_90_short_radius", [237]),
    ("returns_180_long_radius", [238]),
    ("straight_tees", [239]),
    ("reducing_outlet_tees", [240, 241]),
    ("lap_joint_stub_ends", [242]),
    ("reducers_stainless", [243, 244, 245]),
    ("caps_stainless", [246]),
]:
    LEAVES.append(skip(leaf_id, leaf_pages))

# ── MACHINERY STEEL (pages 248-252) ──
LEAVES.append(skip("product_list_machinery", [248]))
LEAVES.append(LeafSchema(
    leaf_id="carbon_steel_machinery",
    name="Carbon Steel Machinery KS D3752, JIS G4051",
    pages=[249],
    page_groups=[
        PageGroup(pages=[249], skip_header_rows=6,
                  footer_pattern=FOOTER_PATTERN,
                  section_pattern=r"^([A-Z]\w+)", parser="machinery",
                  columns=[
                      ColumnDef("c", type="str"), ColumnDef("si", type="str"),
                      ColumnDef("mn", type="str"), ColumnDef("p", type="str"),
                      ColumnDef("s", type="str"),
                      ColumnDef("yp", type="str"), ColumnDef("ts", type="str"),
                      ColumnDef("el", type="str"), ColumnDef("ra", type="str"),
                      ColumnDef("impact", type="str"), ColumnDef("hardness", type="str"),
                      ColumnDef("aisi", type="str"),
                  ]),
    ],
))
LEAVES.append(LeafSchema(
    leaf_id="chromium_and_crmo_steels",
    name="Alloy Steel Chromium & CrMo KS D3707 D3711, JIS G4104 G4105",
    pages=[250],
    page_groups=[
        PageGroup(pages=[250], skip_header_rows=6,
                  footer_pattern=FOOTER_PATTERN,
                  section_pattern=r"^([A-Z]\w+)", parser="machinery",
                  columns=[
                      ColumnDef("c", type="str"), ColumnDef("si", type="str"),
                      ColumnDef("mn", type="str"), ColumnDef("p", type="str"),
                      ColumnDef("s", type="str"), ColumnDef("cr", type="str"),
                      ColumnDef("mo", type="str"),
                      ColumnDef("yp", type="str"), ColumnDef("ts", type="str"),
                      ColumnDef("el", type="str"), ColumnDef("ra", type="str"),
                      ColumnDef("impact", type="str"), ColumnDef("hardness", type="str"),
                      ColumnDef("aisi", type="str"),
                  ]),
    ],
))
LEAVES.append(LeafSchema(
    leaf_id="nickel_chromium_steels",
    name="Alloy Steel NiCr KS D3708 D3709, JIS G4102 G4103",
    pages=[251],
    page_groups=[
        PageGroup(pages=[251], skip_header_rows=6,
                  footer_pattern=FOOTER_PATTERN,
                  section_pattern=r"^([A-Z]\w+)", parser="machinery",
                  columns=[
                      ColumnDef("c", type="str"), ColumnDef("si", type="str"),
                      ColumnDef("mn", type="str"), ColumnDef("p", type="str"),
                      ColumnDef("s", type="str"), ColumnDef("ni", type="str"),
                      ColumnDef("cr", type="str"), ColumnDef("mo", type="str"),
                      ColumnDef("yp", type="str"), ColumnDef("ts", type="str"),
                      ColumnDef("el", type="str"), ColumnDef("ra", type="str"),
                      ColumnDef("impact", type="str"), ColumnDef("hardness", type="str"),
                      ColumnDef("aisi", type="str"),
                  ]),
    ],
))
LEAVES.append(LeafSchema(
    leaf_id="cold_finished_free_cutting_steel",
    name="Free Cutting Steel KS D3567, JIS G4804",
    pages=[252],
    page_groups=[
        PageGroup(pages=[252], skip_header_rows=6,
                  footer_pattern=FOOTER_PATTERN,
                  section_pattern=r"^([A-Z]\w+)", parser="machinery",
                  columns=[
                      ColumnDef("c", type="str"), ColumnDef("si", type="str"),
                      ColumnDef("mn", type="str"), ColumnDef("p", type="str"),
                      ColumnDef("s", type="str"), ColumnDef("pb", type="str"),
                      ColumnDef("aisi", type="str"),
                  ]),
    ],
))

# ── NON-FERROUS METALS (pages 254-262) ──
LEAVES.append(skip("product_list_non_ferrous", [254]))
LEAVES.append(LeafSchema(
    leaf_id="copper_round_hex_square_bars",
    name="Copper Round, Hexagon & Square Bars Weights",
    pages=[255],
    page_groups=[
        PageGroup(pages=[255], skip_header_rows=5,
                  footer_pattern=FOOTER_PATTERN,
                  section_pattern=r"^([\d]+(?:/\d+)?)\s*",
                  value_count=9, parser="token",
                  merge_fractions=True,
                  columns=[
                      ColumnDef("round_kg_ft", unit="kg/ft"),
                      ColumnDef("round_lb_ft", unit="lb/ft"),
                      ColumnDef("round_kati_ft", unit="kati/ft"),
                      ColumnDef("hex_kg_ft", unit="kg/ft"),
                      ColumnDef("hex_lb_ft", unit="lb/ft"),
                      ColumnDef("hex_kati_ft", unit="kati/ft"),
                      ColumnDef("square_kg_ft", unit="kg/ft"),
                      ColumnDef("square_lb_ft", unit="lb/ft"),
                      ColumnDef("square_kati_ft", unit="kati/ft"),
                  ]),
    ],
))
LEAVES.append(skip("copper_flat_bars", [256]))
LEAVES.append(LeafSchema(
    leaf_id="brass_round_hex_square_bars",
    name="Brass Round, Hexagon & Square Bars Weights",
    pages=[257],
    page_groups=[
        PageGroup(pages=[257], skip_header_rows=5,
                  footer_pattern=FOOTER_PATTERN,
                  section_pattern=r"^([\d]+(?:/\d+)?)\s*",
                  value_count=9, parser="token",
                  merge_fractions=True,
                  columns=[
                      ColumnDef("round_kg_ft", unit="kg/ft"),
                      ColumnDef("round_lb_ft", unit="lb/ft"),
                      ColumnDef("round_kati_ft", unit="kati/ft"),
                      ColumnDef("hex_kg_ft", unit="kg/ft"),
                      ColumnDef("hex_lb_ft", unit="lb/ft"),
                      ColumnDef("hex_kati_ft", unit="kati/ft"),
                      ColumnDef("square_kg_ft", unit="kg/ft"),
                      ColumnDef("square_lb_ft", unit="lb/ft"),
                      ColumnDef("square_kati_ft", unit="kati/ft"),
                  ]),
    ],
))
LEAVES.append(skip("brass_flat_bars", [258]))
LEAVES.append(LeafSchema(
    leaf_id="brass_sheets",
    name="Brass Sheets",
    pages=[259],
    page_groups=[
        PageGroup(pages=[259], skip_header_rows=6,
                  footer_pattern=FOOTER_PATTERN, section_pattern=SECTION_PATTERN_NUMERIC,
                  value_count=4,
                  columns=[
                      ColumnDef("thickness_mm", type="float", unit="mm"),
                      ColumnDef("width_in", unit="in"), ColumnDef("length_in", unit="in"),
                      ColumnDef("weight_kg", unit="kg"),
                  ]),
    ]))
LEAVES.append(skip("bronze_continuous_casting_info", [260]))
LEAVES.append(skip("bronze_tube_stock_sizes", [261]))
LEAVES.append(skip("bronze_centrifugal_cast", [262]))

# ── APPENDIX ──
LEAVES.append(LeafSchema(
    leaf_id="gauge_table",
    name="Gauge Table SWG BWG BG BS USG",
    pages=[265],
    page_groups=[
        PageGroup(pages=[265], skip_header_rows=4,
                  footer_pattern=FOOTER_PATTERN, section_pattern=SECTION_PATTERN_NUMERIC,
                  value_count=4,
                  columns=[
                      ColumnDef("swg_mm", unit="mm"), ColumnDef("bwg_mm", unit="mm"),
                      ColumnDef("bg_mm", unit="mm"), ColumnDef("usg_mm", unit="mm"),
                  ]),
    ]))


# ══════════════════════════════════════════════════════════════════════════════
# LOOKUP FUNCTIONS
# ══════════════════════════════════════════════════════════════════════════════

LEAF_SCHEMAS_BY_ID = {leaf.leaf_id: leaf for leaf in LEAVES}

ALL_LEAF_IDS = sorted(LEAF_SCHEMAS_BY_ID.keys())


def get_leaf_by_id(leaf_id):
    return LEAF_SCHEMAS_BY_ID.get(leaf_id)


def get_leaf_ids_for_page(page_num):
    matches = []
    for leaf in LEAVES:
        if page_num in leaf.pages:
            matches.append(leaf.leaf_id)
    return matches


def get_schema_for_page(page_num):
    """Return first matching leaf schema for a page (backward compat)."""
    for leaf in LEAVES:
        if page_num in leaf.pages and leaf.page_groups:
            return leaf
    return None


def get_page_group_for_page(leaf, page_num):
    for pg in leaf.page_groups:
        if page_num in pg.pages:
            return pg
    return None
