from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ColumnDef:
    name: str
    type: str = "float"
    unit: Optional[str] = None
    description: Optional[str] = None


@dataclass
class TableSchema:
    page_type: str
    name: str
    pages: list
    skip_header_rows: int
    footer_pattern: str
    section_pattern: str
    value_count: int
    columns: list
    continuation_value_count: Optional[int] = None
    max_data_rows: Optional[int] = None


# Matches section names that start with W (e.g. "W4 4 x 4 (102 x 102)")
# OR contain an x-dimension (e.g. "8 x 8", "100 x 50", "6 x 4 (J)")
SECTION_PATTERN_CORE = (
    r"^("
    r"(?:W\d+\s+\d+(?:\s*x\s*\d+(?:/\d+)?)?\s*(?:\([^)]+\))?)"
    r"|"
    r"(?:\d+(?:\.\d+)?\s*x\s*\d+(?:/\d+)?\s*(?:\([^)]+\))?)"
    r")"
    r"\s*"
)

# Pattern for dimension-based sections like "13 x 13", "50 x 25", "100 x 50 x 20"
SECTION_PATTERN_DIM = r"^(\d+(?:\.\d+)?\s*x\s*\d+(?:\.\d+)?(?:\s*x\s*\d+(?:\.\d+)?)?)\s*"

# Pattern for dimension with optional imperial equivalent like "127 x 64 (5 x 2 1/2)"
SECTION_PATTERN_DIM_IMPERIAL = (
    r"^(\d+(?:\.\d+)?\s*x\s*\d+(?:\.\d+)?(?:\s*x\s*\d+(?:\.\d+)?)?"
    r"\s*\([^)]*\))\s*"
)

# Pattern for imperial+fraction dimension like "1/2 x 1/2 12.7 x 12.7"
SECTION_PATTERN_FRAC_DIM = (
    r"^((?:\d+(?:[-\s]\d+)?(?:/\d+)?\s*x\s*)+\d+(?:[-\s]\d+)?(?:/\d+)?"
    r"(?:\s+\d+(?:\.\d+)?\s*x\s*\d+(?:\.\d+)?)?)\s*"
)

# Pattern for pile section names like "1BXN", "6W", "KSP-IA", "YSP II"
# Single token (alphanumeric, may contain hyphen) - stops at first space
SECTION_PATTERN_PILE = (
    r"^([A-Za-z0-9][-A-Za-z0-9]*(?:\s+(?![0-9]+(?:\s|$))[A-Za-z0-9][-A-Za-z0-9]*)?)\s*"
)

# Pattern for simple numeric section (pipe OD, bar size)
SECTION_PATTERN_NUMERIC = r"^(\d+(?:\.\d+)?)\s*"

# Pattern for pipe section with optional fraction like "1/2", "1 1/4", "2 1/2"
SECTION_PATTERN_PIPE_NOM = r"^(\d+(?:\s+\d+)?(?:/\d+)?)\s*"

# Pattern for flange nominal size
SECTION_PATTERN_FLANGE = r"^(\d+(?:/\d+)?|½|¼|¾|⅛|⅜|⅝|⅞)\s*"

# Pattern for inverted angle sections
SECTION_PATTERN_INV_ANGLE = r"^(\d+\s*x\s*\d+(?:\s+\d+\s+\d+\s+\d+\s+\d+)?)\s*"

# Pattern for dimension with optional parenthesized imperial (e.g. "75 x 40 x 5" or "127 x 64 (5 x 2 1/2)")
SECTION_PATTERN_DIM_OPT_IMPERIAL = (
    r"^(\d+(?:\.\d+)?\s*x\s*\d+(?:\.\d+)?(?:\s*x\s*\d+(?:\.\d+)?)?"
    r"(?:\s*\([^)]*\))?)\s*"
)

# Pattern for purlin section IDs like "SZ 100-16", "SC100-16"
SECTION_PATTERN_PURLIN_Z = r"^(SZ\s+\d+-\d+)\s*"
SECTION_PATTERN_PURLIN_C = r"^(SC\d+-\d+)\s*"

# Pattern for pipe nominal with fraction chars — for "½", "1¼", "2½", "5" etc.
SECTION_PATTERN_PIPE_NOM_FRAC = r"^((?:\d*[\u00BC-\u00BE\u2150-\u215E]|\d+(?:/\d+)?))\s*"

# Pattern for pipe nominal with both mm + inch cells combined — for "6 ⅛", "50 2", "32 1¼"
SECTION_PATTERN_PIPE_NOM_DUAL = r"^(\d+(?:\s+(?:\d*[\u00BC-\u00BE\u2150-\u215E]|\d+/\d+|\d+))?)\s*"

# Pattern for pipe OD section — requires at least 2 leading digits to avoid matching continuation rows
SECTION_PATTERN_STK_OD = r"^(\d{2,}(?:\.\d+)?)\s*"

# Pattern for inch-series channel designations like "C3 x 4.1", "C8 x 11.5"
SECTION_PATTERN_INCH_CHANNEL = r"^(C\d+(?:\.\d+)?\s*x\s*\d+(?:\.\d+)?)\s*"

FOOTER_PATTERN = r"YICK HOE|YICK HOE GROUP OF COMPANY"
FOOTER_PATTERN_NOTES = r"YICK HOE|YICK HOE GROUP OF COMPANY|Note:|Sizes indicated|L = Light"
FOOTER_PATTERN_TOL = r"YICK HOE|YICK HOE GROUP OF COMPANY|Note:|Tolerance|Wall Thickness"
FOOTER_PATTERN_STK = r"YICK HOE|YICK HOE GROUP OF COMPANY|Applicable Tolerances|mm and over|Outside Diameter Under|mm or over"

# ──────────────────────────────────────────────
# 1) Universal Beam Dimensions (imperial, 7 pairs)
# ──────────────────────────────────────────────
BEAM_DIMENSIONS = TableSchema(
    page_type="beam_dimensions",
    name="Universal Beam Dimensions",
    pages=[37, 39, 41, 43, 45],
    skip_header_rows=6,
    footer_pattern=FOOTER_PATTERN,
    section_pattern=SECTION_PATTERN_CORE,
    value_count=14,
    columns=[
        ColumnDef("weight_lb_ft", unit="lb/ft"),
        ColumnDef("weight_kg_m", unit="kg/m"),
        ColumnDef("area_in2", unit="in²"),
        ColumnDef("area_cm2", unit="cm²"),
        ColumnDef("depth_in", unit="in"),
        ColumnDef("depth_mm", unit="mm"),
        ColumnDef("flange_width_in", unit="in"),
        ColumnDef("flange_width_mm", unit="mm"),
        ColumnDef("flange_thickness_in", unit="in"),
        ColumnDef("flange_thickness_mm", unit="mm"),
        ColumnDef("web_thickness_in", unit="in"),
        ColumnDef("web_thickness_mm", unit="mm"),
        ColumnDef("corner_radius_in", unit="in"),
        ColumnDef("corner_radius_mm", unit="mm"),
    ],
)

# ──────────────────────────────────────────────
# 2) Universal Beam Inertia (imperial, 6 pairs)
# ──────────────────────────────────────────────
BEAM_INERTIA = TableSchema(
    page_type="beam_inertia",
    name="Universal Beam Inertia / Modulus",
    pages=[38, 40, 42, 44, 46],
    skip_header_rows=9,
    footer_pattern=FOOTER_PATTERN,
    section_pattern=SECTION_PATTERN_CORE,
    value_count=12,
    columns=[
        ColumnDef("Ix_in4", unit="in⁴"),
        ColumnDef("Ix_cm4", unit="cm⁴"),
        ColumnDef("Iy_in4", unit="in⁴"),
        ColumnDef("Iy_cm4", unit="cm⁴"),
        ColumnDef("ix_in", unit="in"),
        ColumnDef("ix_cm", unit="cm"),
        ColumnDef("iy_in", unit="in"),
        ColumnDef("iy_cm", unit="cm"),
        ColumnDef("Zx_in3", unit="in³"),
        ColumnDef("Zx_cm3", unit="cm³"),
        ColumnDef("Zy_in3", unit="in³"),
        ColumnDef("Zy_cm3", unit="cm³"),
    ],
)

# ──────────────────────────────────────────────
# 3) Universal Beam Metric Dimensions (page 47)
# ──────────────────────────────────────────────
BEAM_METRIC_DIMENSIONS = TableSchema(
    page_type="beam_metric_dimensions",
    name="Universal Beam Metric Dimensions",
    pages=[47],
    skip_header_rows=6,
    footer_pattern=FOOTER_PATTERN,
    section_pattern=SECTION_PATTERN_CORE,
    value_count=13,
    columns=[
        ColumnDef("weight_kg_m", unit="kg/m"),
        ColumnDef("depth_mm", unit="mm"),
        ColumnDef("flange_width_mm", unit="mm"),
        ColumnDef("web_thickness_mm", unit="mm"),
        ColumnDef("flange_thickness_mm", unit="mm"),
        ColumnDef("corner_radius_mm", unit="mm"),
        ColumnDef("area_cm2", unit="cm²"),
        ColumnDef("Ix_cm4", unit="cm⁴"),
        ColumnDef("Iy_cm4", unit="cm⁴"),
        ColumnDef("ix_cm", unit="cm"),
        ColumnDef("iy_cm", unit="cm"),
        ColumnDef("Zx_cm3", unit="cm³"),
        ColumnDef("Zy_cm3", unit="cm³"),
    ],
)

# ──────────────────────────────────────────────
# 4) Universal Beam Metric Inertia (page 48)
# ──────────────────────────────────────────────
BEAM_METRIC_INERTIA = TableSchema(
    page_type="beam_metric_inertia",
    name="Universal Beam Metric Inertia",
    pages=[48],
    skip_header_rows=9,
    footer_pattern=FOOTER_PATTERN,
    section_pattern=SECTION_PATTERN_CORE,
    value_count=13,
    columns=[
        ColumnDef("weight_kg_m", unit="kg/m"),
        ColumnDef("depth_mm", unit="mm"),
        ColumnDef("flange_width_mm", unit="mm"),
        ColumnDef("web_thickness_mm", unit="mm"),
        ColumnDef("flange_thickness_mm", unit="mm"),
        ColumnDef("corner_radius_mm", unit="mm"),
        ColumnDef("area_cm2", unit="cm²"),
        ColumnDef("Ix_cm4", unit="cm⁴"),
        ColumnDef("Iy_cm4", unit="cm⁴"),
        ColumnDef("ix_cm", unit="cm"),
        ColumnDef("iy_cm", unit="cm"),
        ColumnDef("Zx_cm3", unit="cm³"),
        ColumnDef("Zy_cm3", unit="cm³"),
    ],
)

# ──────────────────────────────────────────────
# 5) Light Beam Dimensions (imperial)
# ──────────────────────────────────────────────
LIGHT_BEAM_DIMENSIONS = TableSchema(
    page_type="light_beam_dimensions",
    name="Light Beam Dimensions",
    pages=[49],
    skip_header_rows=6,
    footer_pattern=FOOTER_PATTERN_NOTES,
    section_pattern=SECTION_PATTERN_CORE,
    value_count=14,
    columns=[
        ColumnDef("weight_lb_ft", unit="lb/ft"),
        ColumnDef("weight_kg_m", unit="kg/m"),
        ColumnDef("depth_in", unit="in"),
        ColumnDef("depth_mm", unit="mm"),
        ColumnDef("flange_width_in", unit="in"),
        ColumnDef("flange_width_mm", unit="mm"),
        ColumnDef("web_thickness_in", unit="in"),
        ColumnDef("web_thickness_mm", unit="mm"),
        ColumnDef("flange_thickness_in", unit="in"),
        ColumnDef("flange_thickness_mm", unit="mm"),
        ColumnDef("corner_radius_in", unit="in"),
        ColumnDef("corner_radius_mm", unit="mm"),
        ColumnDef("area_in2", unit="in²"),
        ColumnDef("area_cm2", unit="cm²"),
    ],
)

# ──────────────────────────────────────────────
# 6) Light Beam Inertia (imperial)
# ──────────────────────────────────────────────
LIGHT_BEAM_INERTIA = TableSchema(
    page_type="light_beam_inertia",
    name="Light Beam Inertia / Modulus",
    pages=[50, 52],
    skip_header_rows=9,
    footer_pattern=FOOTER_PATTERN,
    section_pattern=SECTION_PATTERN_CORE,
    value_count=12,
    columns=[
        ColumnDef("Ix_in4", unit="in⁴"),
        ColumnDef("Ix_cm4", unit="cm⁴"),
        ColumnDef("Iy_in4", unit="in⁴"),
        ColumnDef("Iy_cm4", unit="cm⁴"),
        ColumnDef("ix_in", unit="in"),
        ColumnDef("ix_cm", unit="cm"),
        ColumnDef("iy_in", unit="in"),
        ColumnDef("iy_cm", unit="cm"),
        ColumnDef("Zx_in3", unit="in³"),
        ColumnDef("Zx_cm3", unit="cm³"),
        ColumnDef("Zy_in3", unit="in³"),
        ColumnDef("Zy_cm3", unit="cm³"),
    ],
)

# ──────────────────────────────────────────────
# 7) Light Beam Metric (page 51)
# ──────────────────────────────────────────────
LIGHT_BEAM_METRIC = TableSchema(
    page_type="light_beam_metric",
    name="Light Beam Metric Dimensions",
    pages=[51],
    skip_header_rows=6,
    footer_pattern=FOOTER_PATTERN,
    section_pattern=SECTION_PATTERN_CORE,
    value_count=12,
    columns=[
        ColumnDef("weight_kg_m", unit="kg/m"),
        ColumnDef("weight_lb_ft", unit="lb/ft"),
        ColumnDef("web_thickness_mm", unit="mm"),
        ColumnDef("web_thickness_in", unit="in"),
        ColumnDef("flange_thickness_mm", unit="mm"),
        ColumnDef("flange_thickness_in", unit="in"),
        ColumnDef("root_radius_mm", unit="mm"),
        ColumnDef("root_radius_in", unit="in"),
        ColumnDef("toe_radius_mm", unit="mm"),
        ColumnDef("toe_radius_in", unit="in"),
        ColumnDef("area_cm2", unit="cm²"),
        ColumnDef("area_in2", unit="in²"),
    ],
)

# ──────────────────────────────────────────────
# 8) Bearing Pile Dimensions (page 53)
# ──────────────────────────────────────────────
BEARING_PILE_DIMENSIONS = TableSchema(
    page_type="bearing_pile_dimensions",
    name="Bearing Pile Dimensions",
    pages=[53],
    skip_header_rows=5,
    footer_pattern=FOOTER_PATTERN,
    section_pattern=SECTION_PATTERN_CORE,
    value_count=12,
    columns=[
        ColumnDef("weight_lb_ft", unit="lb/ft"),
        ColumnDef("weight_kg_m", unit="kg/m"),
        ColumnDef("depth_in", unit="in"),
        ColumnDef("depth_mm", unit="mm"),
        ColumnDef("flange_width_in", unit="in"),
        ColumnDef("flange_width_mm", unit="mm"),
        ColumnDef("web_thickness_in", unit="in"),
        ColumnDef("web_thickness_mm", unit="mm"),
        ColumnDef("corner_radius_in", unit="in"),
        ColumnDef("corner_radius_mm", unit="mm"),
        ColumnDef("area_in2", unit="in²"),
        ColumnDef("area_cm2", unit="cm²"),
    ],
)

# ──────────────────────────────────────────────
# 9) Bearing Pile Inertia (page 54)
# ──────────────────────────────────────────────
BEARING_PILE_INERTIA = TableSchema(
    page_type="bearing_pile_inertia",
    name="Bearing Pile Inertia / Modulus",
    pages=[54],
    skip_header_rows=8,
    footer_pattern=FOOTER_PATTERN,
    section_pattern=SECTION_PATTERN_CORE,
    value_count=12,
    columns=[
        ColumnDef("Ix_in4", unit="in⁴"),
        ColumnDef("Ix_cm4", unit="cm⁴"),
        ColumnDef("Iy_in4", unit="in⁴"),
        ColumnDef("Iy_cm4", unit="cm⁴"),
        ColumnDef("ix_in", unit="in"),
        ColumnDef("ix_cm", unit="cm"),
        ColumnDef("iy_in", unit="in"),
        ColumnDef("iy_cm", unit="cm"),
        ColumnDef("Zx_in3", unit="in³"),
        ColumnDef("Zx_cm3", unit="cm³"),
        ColumnDef("Zy_in3", unit="in³"),
        ColumnDef("Zy_cm3", unit="cm³"),
    ],
)

# ══════════════════════════════════════════════
# 10) STEEL PILES
# ══════════════════════════════════════════════

# Frodingham Steel Sheet Piling (page 58)
# Columns: b, h, d, t, f1, f2, section_area, weight_per_m_wall, weight_per_m2, moment_of_inertia, modulus_of_section
FRODINGHAM_PILE = TableSchema(
    page_type="frodingham_pile",
    name="Frodingham Steel Sheet Piling",
    pages=[58],
    skip_header_rows=9,
    footer_pattern=FOOTER_PATTERN,
    section_pattern=SECTION_PATTERN_PILE,
    value_count=11,
    max_data_rows=7,
    columns=[
        ColumnDef("width_b_mm", unit="mm"),
        ColumnDef("height_h_mm", unit="mm"),
        ColumnDef("web_thickness_d_mm", unit="mm"),
        ColumnDef("flange_thickness_t_mm", unit="mm"),
        ColumnDef("f1_mm", unit="mm"),
        ColumnDef("f2_mm", unit="mm"),
        ColumnDef("section_area_cm2", unit="cm²"),
        ColumnDef("weight_per_m_wall_kg", unit="kg/m of wall"),
        ColumnDef("weight_per_m2_kg", unit="kg/m²"),
        ColumnDef("moment_of_inertia_cm4", unit="cm⁴"),
        ColumnDef("modulus_of_section_cm3", unit="cm³"),
    ],
)

# Larssen Steel Sheet Piling (page 59)
LARSSEN_PILE = TableSchema(
    page_type="larssen_pile",
    name="Larssen Steel Sheet Piling",
    pages=[59],
    skip_header_rows=8,
    footer_pattern=FOOTER_PATTERN,
    section_pattern=SECTION_PATTERN_PILE,
    value_count=10,
    max_data_rows=11,
    columns=[
        ColumnDef("width_b_mm", unit="mm"),
        ColumnDef("height_h_mm", unit="mm"),
        ColumnDef("web_thickness_d_mm", unit="mm"),
        ColumnDef("flange_thickness_t_mm", unit="mm"),
        ColumnDef("flat_pan_mm", unit="mm"),
        ColumnDef("section_area_cm2", unit="cm²"),
        ColumnDef("weight_per_m_wall_kg", unit="kg/m of wall"),
        ColumnDef("weight_per_m2_kg", unit="kg/m²"),
        ColumnDef("moment_of_inertia_cm4", unit="cm⁴"),
        ColumnDef("modulus_of_section_cm3", unit="cm³"),
    ],
)

# KSP U-Type Pile Dimensions & Properties (page 62)
KSP_U_PILE = TableSchema(
    page_type="ksp_u_pile",
    name="KSP U-Type Pile Dimensions and Properties",
    pages=[62],
    skip_header_rows=9,
    footer_pattern=FOOTER_PATTERN,
    section_pattern=SECTION_PATTERN_PILE,
    value_count=10,
    columns=[
        ColumnDef("width_w_mm", unit="mm"),
        ColumnDef("height_h_mm", unit="mm"),
        ColumnDef("thickness_t_mm", unit="mm"),
        ColumnDef("section_area_cm2", unit="cm²"),
        ColumnDef("weight_per_pile_kg", unit="kg/m"),
        ColumnDef("weight_per_wall_kg", unit="kg/m²"),
        ColumnDef("moment_inertia_cm4", unit="cm⁴"),
        ColumnDef("moment_inertia_per_m_cm4", unit="cm⁴/m"),
        ColumnDef("modulus_cm3", unit="cm³"),
        ColumnDef("modulus_per_m_cm3", unit="cm³/m"),
    ],
)

# KSP U-Type Pile continued (page 63) - mixed metric/imperial
KSP_U_PILE_IMP = TableSchema(
    page_type="ksp_u_pile_imp",
    name="KSP U-Type Pile Dimensions (Imperial)",
    pages=[63],
    skip_header_rows=8,
    footer_pattern=FOOTER_PATTERN,
    section_pattern=SECTION_PATTERN_PILE,
    value_count=13,
    columns=[
        ColumnDef("width_w_mm", unit="mm"),
        ColumnDef("height_h_mm", unit="mm"),
        ColumnDef("thickness_t_mm", unit="mm"),
        ColumnDef("section_area_cm2", unit="cm²"),
        ColumnDef("weight_per_pile_kg", unit="kg/m"),
        ColumnDef("weight_per_wall_kg", unit="kg/m²"),
        ColumnDef("moment_inertia_cm4", unit="cm⁴"),
        ColumnDef("moment_inertia_per_m_cm4", unit="cm⁴/m"),
        ColumnDef("modulus_cm3", unit="cm³"),
        ColumnDef("modulus_per_m_cm3", unit="cm³/m"),
        ColumnDef("width_w_in", unit="in"),
        ColumnDef("height_h_in", unit="in"),
        ColumnDef("thickness_t_in", unit="in"),
    ],
)

# Z-Type Pile (page 64)
Z_TYPE_PILE = TableSchema(
    page_type="z_type_pile",
    name="Z-Type Pile Dimensions and Properties",
    pages=[64],
    skip_header_rows=9,
    footer_pattern=FOOTER_PATTERN,
    section_pattern=SECTION_PATTERN_PILE,
    value_count=12,
    columns=[
        ColumnDef("width_w_mm", unit="mm"),
        ColumnDef("height_h_mm", unit="mm"),
        ColumnDef("t1_mm", unit="mm"),
        ColumnDef("t2_mm", unit="mm"),
        ColumnDef("section_area_cm2", unit="cm²"),
        ColumnDef("weight_per_pile_kg", unit="kg/m"),
        ColumnDef("weight_per_wall_kg", unit="kg/m²"),
        ColumnDef("moment_inertia_cm4", unit="cm⁴"),
        ColumnDef("moment_inertia_per_m_cm4", unit="cm⁴/m"),
        ColumnDef("modulus_cm3", unit="cm³"),
        ColumnDef("modulus_per_m_cm3", unit="cm³/m"),
        ColumnDef("width_w_in", unit="in"),
    ],
)

# ══════════════════════════════════════════════
# 11) COLD FORMED HOLLOW SECTIONS
# ══════════════════════════════════════════════

# Cold Formed Square Hollow Sections - Metric (pages 91-92)
# Columns: t, M(kg/m), A(cm2), Ix(cm4), Iy(cm4), ix(cm), iy(cm), Zx(cm3), Zy(cm3)
CF_SQUARE_METRIC = TableSchema(
    page_type="cf_square_metric",
    name="Cold Formed Square Hollow Sections (Metric)",
    pages=[91, 92],
    skip_header_rows=7,
    footer_pattern=FOOTER_PATTERN,
    section_pattern=SECTION_PATTERN_DIM,
    value_count=9,
    columns=[
        ColumnDef("wall_thickness_mm", unit="mm"),
        ColumnDef("weight_kg_m", unit="kg/m"),
        ColumnDef("area_cm2", unit="cm²"),
        ColumnDef("Ix_cm4", unit="cm⁴"),
        ColumnDef("Iy_cm4", unit="cm⁴"),
        ColumnDef("ix_cm", unit="cm"),
        ColumnDef("iy_cm", unit="cm"),
        ColumnDef("Zx_cm3", unit="cm³"),
        ColumnDef("Zy_cm3", unit="cm³"),
    ],
)

# Cold Formed Rectangular Hollow Sections - Metric (pages 93-94)
CF_RECT_METRIC = TableSchema(
    page_type="cf_rect_metric",
    name="Cold Formed Rectangular Hollow Sections (Metric)",
    pages=[93, 94],
    skip_header_rows=7,
    footer_pattern=FOOTER_PATTERN,
    section_pattern=SECTION_PATTERN_DIM,
    value_count=9,
    columns=[
        ColumnDef("wall_thickness_mm", unit="mm"),
        ColumnDef("weight_kg_m", unit="kg/m"),
        ColumnDef("area_cm2", unit="cm²"),
        ColumnDef("Ix_cm4", unit="cm⁴"),
        ColumnDef("Iy_cm4", unit="cm⁴"),
        ColumnDef("ix_cm", unit="cm"),
        ColumnDef("iy_cm", unit="cm"),
        ColumnDef("Zx_cm3", unit="cm³"),
        ColumnDef("Zy_cm3", unit="cm³"),
    ],
)

# Cold Formed Square Hollow Sections - Imperial (pages 95-97)
# Columns: t(in/mm), M(in/lb/ft kg/m), A(in2), I(in4), i(in), Z(in3)
CF_SQUARE_IMPERIAL = TableSchema(
    page_type="cf_square_imperial",
    name="Cold Formed Square Hollow Sections (Imperial)",
    pages=[95, 96, 97],
    skip_header_rows=7,
    footer_pattern=FOOTER_PATTERN,
    section_pattern=SECTION_PATTERN_FRAC_DIM,
    value_count=8,
    columns=[
        ColumnDef("wall_thickness_in", unit="in"),
        ColumnDef("wall_thickness_mm", unit="mm"),
        ColumnDef("weight_lb_ft", unit="lb/ft"),
        ColumnDef("weight_kg_m", unit="kg/m"),
        ColumnDef("area_in2", unit="in²"),
        ColumnDef("I_in4", unit="in⁴"),
        ColumnDef("i_in", unit="in"),
        ColumnDef("Z_in3", unit="in³"),
    ],
)

# Cold Formed Rectangular Hollow Sections - Imperial (pages 98-100)
CF_RECT_IMPERIAL = TableSchema(
    page_type="cf_rect_imperial",
    name="Cold Formed Rectangular Hollow Sections (Imperial)",
    pages=[98, 99, 100],
    skip_header_rows=7,
    footer_pattern=FOOTER_PATTERN,
    section_pattern=SECTION_PATTERN_FRAC_DIM,
    value_count=11,
    columns=[
        ColumnDef("wall_thickness_in", unit="in"),
        ColumnDef("wall_thickness_mm", unit="mm"),
        ColumnDef("weight_lb_ft", unit="lb/ft"),
        ColumnDef("weight_kg_m", unit="kg/m"),
        ColumnDef("area_in2", unit="in²"),
        ColumnDef("Ix_in4", unit="in⁴"),
        ColumnDef("Iy_in4", unit="in⁴"),
        ColumnDef("ix_in", unit="in"),
        ColumnDef("iy_in", unit="in"),
        ColumnDef("Zx_in3", unit="in³"),
        ColumnDef("Zy_in3", unit="in³"),
    ],
)

# ══════════════════════════════════════════════
# 12) HOT FORMED HOLLOW SECTIONS
# ══════════════════════════════════════════════

# Hot Formed Square Hollow Sections (pages 105-107)
# Columns: t, M, A, I, r, Z, S, J, C, superficial_area, length_per_tonne
HF_SQUARE = TableSchema(
    page_type="hf_square",
    name="Hot Formed Square Hollow Sections",
    pages=[105, 106, 107],
    skip_header_rows=7,
    footer_pattern=FOOTER_PATTERN,
    section_pattern=SECTION_PATTERN_DIM,
    value_count=11,
    columns=[
        ColumnDef("wall_thickness_mm", unit="mm"),
        ColumnDef("weight_kg_m", unit="kg/m"),
        ColumnDef("area_cm2", unit="cm²"),
        ColumnDef("I_cm4", unit="cm⁴"),
        ColumnDef("r_cm", unit="cm"),
        ColumnDef("Z_cm3", unit="cm³"),
        ColumnDef("S_cm3", unit="cm³"),
        ColumnDef("J_cm4", unit="cm⁴"),
        ColumnDef("C_cm3", unit="cm³"),
        ColumnDef("superficial_area_m2", unit="m²/m"),
        ColumnDef("length_per_tonne_m", unit="m"),
    ],
)

# Hot Formed Rectangular Hollow Sections (pages 108-109)
# Columns: t, M, A, Ix, Iy, ix, iy, Zx, Zy, Sx, Sy, J, C, superf, length/tonne = 15
HF_RECT = TableSchema(
    page_type="hf_rect",
    name="Hot Formed Rectangular Hollow Sections",
    pages=[108, 109],
    skip_header_rows=8,
    footer_pattern=FOOTER_PATTERN,
    section_pattern=SECTION_PATTERN_DIM,
    value_count=15,
    columns=[
        ColumnDef("wall_thickness_mm", unit="mm"),
        ColumnDef("weight_kg_m", unit="kg/m"),
        ColumnDef("area_cm2", unit="cm²"),
        ColumnDef("Ix_cm4", unit="cm⁴"),
        ColumnDef("Iy_cm4", unit="cm⁴"),
        ColumnDef("ix_cm", unit="cm"),
        ColumnDef("iy_cm", unit="cm"),
        ColumnDef("Zx_cm3", unit="cm³"),
        ColumnDef("Zy_cm3", unit="cm³"),
        ColumnDef("Sx_cm3", unit="cm³"),
        ColumnDef("Sy_cm3", unit="cm³"),
        ColumnDef("J_cm4", unit="cm⁴"),
        ColumnDef("C_cm3", unit="cm³"),
        ColumnDef("superficial_area_m2", unit="m²/m"),
        ColumnDef("length_per_tonne_m", unit="m"),
    ],
)

# Hot Formed Circular Hollow Sections (pages 110-111)
HF_CIRCULAR = TableSchema(
    page_type="hf_circular",
    name="Hot Formed Circular Hollow Sections",
    pages=[110, 111],
    skip_header_rows=7,
    footer_pattern=FOOTER_PATTERN,
    section_pattern=SECTION_PATTERN_NUMERIC,
    value_count=10,
    columns=[
        ColumnDef("wall_thickness_mm", unit="mm"),
        ColumnDef("weight_kg_m", unit="kg/m"),
        ColumnDef("area_cm2", unit="cm²"),
        ColumnDef("I_cm4", unit="cm⁴"),
        ColumnDef("r_cm", unit="cm"),
        ColumnDef("Z_cm3", unit="cm³"),
        ColumnDef("S_cm3", unit="cm³"),
        ColumnDef("J_cm4", unit="cm⁴"),
        ColumnDef("C_cm3", unit="cm³"),
        ColumnDef("superficial_area_m2", unit="m²/m"),
    ],
)

# ══════════════════════════════════════════════
# 13) CHANNELS
# ══════════════════════════════════════════════

# Plain Channels (page 128)
# Columns: M, t, A, Cx, Cy, Ix, Iy, Rx, Ry, Zx, Zy, Mx, M, Q
PLAIN_CHANNEL = TableSchema(
    page_type="plain_channel",
    name="Plain Channels JIS G3350",
    pages=[128],
    skip_header_rows=7,
    footer_pattern=FOOTER_PATTERN,
    section_pattern=SECTION_PATTERN_DIM,
    value_count=14,
    columns=[
        ColumnDef("weight_kg_m", unit="kg/m"),
        ColumnDef("thickness_mm", unit="mm"),
        ColumnDef("area_cm2", unit="cm²"),
        ColumnDef("Cx_cm", unit="cm"),
        ColumnDef("Cy_cm", unit="cm"),
        ColumnDef("Ix_cm4", unit="cm⁴"),
        ColumnDef("Iy_cm4", unit="cm⁴"),
        ColumnDef("Rx_cm", unit="cm"),
        ColumnDef("Ry_cm", unit="cm"),
        ColumnDef("Zx_cm3", unit="cm³"),
        ColumnDef("Zy_cm3", unit="cm³"),
        ColumnDef("Mx_kg_m", unit="kg/m"),
        ColumnDef("M", unit="cm"),
        ColumnDef("Q", unit="kg/m"),
    ],
)

# Lipped Channels (page 129)
LIPPED_CHANNEL = TableSchema(
    page_type="lipped_channel",
    name="Lipped Channels C-Channel JIS G3350",
    pages=[129],
    skip_header_rows=7,
    footer_pattern=FOOTER_PATTERN,
    section_pattern=SECTION_PATTERN_DIM,
    value_count=15,
    columns=[
        ColumnDef("weight_kg_m", unit="kg/m"),
        ColumnDef("thickness_mm", unit="mm"),
        ColumnDef("area_cm2", unit="cm²"),
        ColumnDef("Cx_cm", unit="cm"),
        ColumnDef("Cy_cm", unit="cm"),
        ColumnDef("Ix_cm4", unit="cm⁴"),
        ColumnDef("Iy_cm4", unit="cm⁴"),
        ColumnDef("Rx_cm", unit="cm"),
        ColumnDef("Ry_cm", unit="cm"),
        ColumnDef("Zx_cm3", unit="cm³"),
        ColumnDef("Zy_cm3", unit="cm³"),
        ColumnDef("Zx1_cm3", unit="cm³"),
        ColumnDef("Mx_kg_m", unit="kg/m"),
        ColumnDef("M", unit="cm"),
        ColumnDef("Q", unit="kg/m"),
    ],
)

# U-Channel Dimensions (pages 131, 133)
# Columns: M(kg/m), M(lb/ft), A(mm), A(in), B(mm), B(in), t1(mm), t1(in), t2(mm), t2(in), r1(mm), r1(in), r2(mm), r2(in)
U_CHANNEL_DIM = TableSchema(
    page_type="u_channel_dim",
    name="U-Channel Dimensions",
    pages=[131, 133],
    skip_header_rows=6,
    footer_pattern=FOOTER_PATTERN,
    section_pattern=SECTION_PATTERN_DIM_OPT_IMPERIAL,
    value_count=14,
    columns=[
        ColumnDef("weight_kg_m", unit="kg/m"),
        ColumnDef("weight_lb_ft", unit="lb/ft"),
        ColumnDef("depth_A_mm", unit="mm"),
        ColumnDef("depth_A_in", unit="in"),
        ColumnDef("width_B_mm", unit="mm"),
        ColumnDef("width_B_in", unit="in"),
        ColumnDef("flange_thickness_t1_mm", unit="mm"),
        ColumnDef("flange_thickness_t1_in", unit="in"),
        ColumnDef("web_thickness_t2_mm", unit="mm"),
        ColumnDef("web_thickness_t2_in", unit="in"),
        ColumnDef("corner_r1_mm", unit="mm"),
        ColumnDef("corner_r1_in", unit="in"),
        ColumnDef("r2_mm", unit="mm"),
        ColumnDef("r2_in", unit="in"),
    ],
)

# U-Channel Properties (pages 132, 134)
U_CHANNEL_PROP = TableSchema(
    page_type="u_channel_prop",
    name="U-Channel Section Properties",
    pages=[132, 134],
    skip_header_rows=8,
    footer_pattern=FOOTER_PATTERN,
    section_pattern=SECTION_PATTERN_DIM_OPT_IMPERIAL,
    value_count=16,
    columns=[
        ColumnDef("area_cm2", unit="cm²"),
        ColumnDef("area_in2", unit="in²"),
        ColumnDef("y_cm", unit="cm"),
        ColumnDef("y_in", unit="in"),
        ColumnDef("Ix_cm4", unit="cm⁴"),
        ColumnDef("Ix_in4", unit="in⁴"),
        ColumnDef("Iy_cm4", unit="cm⁴"),
        ColumnDef("Iy_in4", unit="in⁴"),
        ColumnDef("ix_cm", unit="cm"),
        ColumnDef("ix_in", unit="in"),
        ColumnDef("iy_cm", unit="cm"),
        ColumnDef("iy_in", unit="in"),
        ColumnDef("Zx_cm3", unit="cm³"),
        ColumnDef("Zx_in3", unit="in³"),
        ColumnDef("Zy_cm3", unit="cm³"),
        ColumnDef("Zy_in3", unit="in³"),
    ],
)

# U-Channel Inch Series (page 135)
# Columns: H(in), B(in), t1(in), t2(in), r(in), A(in2), M(kg/m), M(kg/ft), M(lb/ft), 20ft(kg), 30ft(kg), 40ft(kg)
U_CHANNEL_INCH = TableSchema(
    page_type="u_channel_inch",
    name="U-Channel Inch Series",
    pages=[135],
    skip_header_rows=10,
    footer_pattern=FOOTER_PATTERN,
    section_pattern=SECTION_PATTERN_INCH_CHANNEL,
    value_count=12,
    columns=[
        ColumnDef("depth_H_in", unit="in"),
        ColumnDef("width_B_in", unit="in"),
        ColumnDef("flange_t1_in", unit="in"),
        ColumnDef("web_t2_in", unit="in"),
        ColumnDef("fillet_r_in", unit="in"),
        ColumnDef("area_in2", unit="in²"),
        ColumnDef("weight_kg_m", unit="kg/m"),
        ColumnDef("weight_kg_ft", unit="kg/ft"),
        ColumnDef("weight_lb_ft", unit="lb/ft"),
        ColumnDef("weight_20ft_kg", unit="kg"),
        ColumnDef("weight_30ft_kg", unit="kg"),
        ColumnDef("weight_40ft_kg", unit="kg"),
    ],
)

# DIN 1026 Channels (page 130)
DIN_CHANNEL = TableSchema(
    page_type="din_channel",
    name="DIN 1026 Channels",
    pages=[130],
    skip_header_rows=7,
    footer_pattern=FOOTER_PATTERN,
    section_pattern=SECTION_PATTERN_DIM,
    value_count=19,
    columns=[
        ColumnDef("height_h_mm", unit="mm"),
        ColumnDef("width_b_mm", unit="mm"),
        ColumnDef("web_s_mm", unit="mm"),
        ColumnDef("flange_t_mm", unit="mm"),
        ColumnDef("r1_mm", unit="mm"),
        ColumnDef("r2_mm", unit="mm"),
        ColumnDef("area_cm2", unit="cm²"),
        ColumnDef("weight_kg_m", unit="kg/m"),
        ColumnDef("surface_m2", unit="m²/m"),
        ColumnDef("Jx_cm4", unit="cm⁴"),
        ColumnDef("Wx_cm3", unit="cm³"),
        ColumnDef("ix_cm", unit="cm"),
        ColumnDef("Jy_cm4", unit="cm⁴"),
        ColumnDef("Wy_cm3", unit="cm³"),
        ColumnDef("iy_cm", unit="cm"),
        ColumnDef("Sx_cm3", unit="cm³"),
        ColumnDef("sx_cm3", unit="cm³"),
        ColumnDef("ey_cm", unit="cm"),
        ColumnDef("XM", unit="cm"),
    ],
)

# ══════════════════════════════════════════════
# 14) Z-PURLINS
# ══════════════════════════════════════════════

# Z-Purlins (page 137)
# Columns from header: A, B, C, D, t (mm), area (mm²), mass (kg/m)
Z_PURLIN = TableSchema(
    page_type="z_purlin",
    name="High-Tensile Galvanised Z-Purlins",
    pages=[137],
    skip_header_rows=6,
    footer_pattern=FOOTER_PATTERN,
    section_pattern=SECTION_PATTERN_PURLIN_Z,
    value_count=7,
    columns=[
        ColumnDef("depth_A_mm", unit="mm"),
        ColumnDef("width_B_mm", unit="mm"),
        ColumnDef("flange_C_mm", unit="mm"),
        ColumnDef("lip_D_mm", unit="mm"),
        ColumnDef("thickness_t_mm", unit="mm"),
        ColumnDef("area_mm2", unit="mm²"),
        ColumnDef("mass_kg_m", unit="kg/m"),
    ],
)

# C-Purlins (page 139)
# Columns from header: A, B, C, D, t (mm), mass (kg/m)
C_PURLIN = TableSchema(
    page_type="c_purlin",
    name="High-Tensile Galvanised C-Purlins",
    pages=[139],
    skip_header_rows=6,
    footer_pattern=FOOTER_PATTERN,
    section_pattern=SECTION_PATTERN_PURLIN_C,
    value_count=6,
    columns=[
        ColumnDef("depth_A_mm", unit="mm"),
        ColumnDef("width_B_mm", unit="mm"),
        ColumnDef("flange_C_mm", unit="mm"),
        ColumnDef("lip_D_mm", unit="mm"),
        ColumnDef("thickness_t_mm", unit="mm"),
        ColumnDef("mass_kg_m", unit="kg/m"),
    ],
)

# ══════════════════════════════════════════════
# 15) ANGLES
# ══════════════════════════════════════════════

# Equal Angles Dimensions (pages 143-144)
# Columns: t, M, r, A, Cx=Cy, Ix=Iy, ix=iy, iv, Zx=Zy
EQUAL_ANGLE = TableSchema(
    page_type="equal_angle",
    name="Equal Angles Dimensions and Properties",
    pages=[143, 144],
    skip_header_rows=6,
    footer_pattern=FOOTER_PATTERN,
    section_pattern=SECTION_PATTERN_DIM,
    value_count=9,
    columns=[
        ColumnDef("thickness_mm", unit="mm"),
        ColumnDef("weight_kg_m", unit="kg/m"),
        ColumnDef("fillet_radius_mm", unit="mm"),
        ColumnDef("area_cm2", unit="cm²"),
        ColumnDef("Cx_cm", unit="cm"),
        ColumnDef("I_cm4", unit="cm⁴"),
        ColumnDef("i_cm", unit="cm"),
        ColumnDef("iv_cm", unit="cm"),
        ColumnDef("Z_cm3", unit="cm³"),
    ],
)

# Unequal Angles Dimensions (pages 145, 147, 149)
# Columns: t, M(kg/m), M(lb/ft), A(mm), B(mm), r1, r2, A_area, Cx, Cy
UNEQUAL_ANGLE_DIM = TableSchema(
    page_type="unequal_angle_dim",
    name="Unequal Angles Dimensions",
    pages=[145, 147, 149],
    skip_header_rows=6,
    footer_pattern=FOOTER_PATTERN,
    section_pattern=SECTION_PATTERN_DIM,
    value_count=10,
    columns=[
        ColumnDef("thickness_mm", unit="mm"),
        ColumnDef("weight_kg_m", unit="kg/m"),
        ColumnDef("weight_lb_ft", unit="lb/ft"),
        ColumnDef("leg_A_mm", unit="mm"),
        ColumnDef("leg_A_in", unit="in"),
        ColumnDef("leg_B_mm", unit="mm"),
        ColumnDef("leg_B_in", unit="in"),
        ColumnDef("r1_mm", unit="mm"),
        ColumnDef("r2_mm", unit="mm"),
        ColumnDef("r2_in", unit="in"),
    ],
)

# Unequal Angles Properties (pages 146, 148, 150)
UNEQUAL_ANGLE_PROP = TableSchema(
    page_type="unequal_angle_prop",
    name="Unequal Angles Section Properties",
    pages=[146, 148, 150],
    skip_header_rows=6,
    footer_pattern=FOOTER_PATTERN,
    section_pattern=SECTION_PATTERN_DIM,
    value_count=21,
    columns=[
        ColumnDef("Ix_cm4", unit="cm⁴"),
        ColumnDef("Ix_in4", unit="in⁴"),
        ColumnDef("Iy_cm4", unit="cm⁴"),
        ColumnDef("Iy_in4", unit="in⁴"),
        ColumnDef("Iu_cm4", unit="cm⁴"),
        ColumnDef("Iu_in4", unit="in⁴"),
        ColumnDef("Iv_cm4", unit="cm⁴"),
        ColumnDef("Iv_in4", unit="in⁴"),
        ColumnDef("ix_cm", unit="cm"),
        ColumnDef("ix_in", unit="in"),
        ColumnDef("iy_cm", unit="cm"),
        ColumnDef("iy_in", unit="in"),
        ColumnDef("iu_cm", unit="cm"),
        ColumnDef("iu_in", unit="in"),
        ColumnDef("iv_cm", unit="cm"),
        ColumnDef("iv_in", unit="in"),
        ColumnDef("tan_a"),
        ColumnDef("Zx_cm3", unit="cm³"),
        ColumnDef("Zx_in3", unit="in³"),
        ColumnDef("Zy_cm3", unit="cm³"),
        ColumnDef("Zy_in3", unit="in³"),
    ],
)

# ══════════════════════════════════════════════
# 16) BARS
# ══════════════════════════════════════════════

# Bulb Flats (page 155)
BULB_FLAT = TableSchema(
    page_type="bulb_flat",
    name="Bulb Flats",
    pages=[155],
    skip_header_rows=8,
    footer_pattern=FOOTER_PATTERN,
    section_pattern=SECTION_PATTERN_NUMERIC,
    value_count=4,
    columns=[
        ColumnDef("thickness_mm", unit="mm"),
        ColumnDef("bulb_height_mm", unit="mm"),
        ColumnDef("area_cm2", unit="cm²"),
        ColumnDef("mass_kg_m", unit="kg/m"),
    ],
)

# Square Bars (page 156)
SQUARE_BAR = TableSchema(
    page_type="square_bar",
    name="Square Bars",
    pages=[156],
    skip_header_rows=5,
    footer_pattern=FOOTER_PATTERN,
    section_pattern=SECTION_PATTERN_NUMERIC,
    value_count=9,
    columns=[
        ColumnDef("weight_kg_m", unit="kg/m"),
        ColumnDef("weight_lb_ft", unit="lb/ft"),
        ColumnDef("side_mm", unit="mm"),
        ColumnDef("side_in", unit="in"),
        ColumnDef("area_cm2", unit="cm²"),
        ColumnDef("area_in2", unit="in²"),
        ColumnDef("I_in4", unit="in⁴"),
        ColumnDef("i_in", unit="in"),
        ColumnDef("Z_in3", unit="in³"),
    ],
)

# Deformed and Round Bars (page 157)
DEFORMED_ROUND_BAR = TableSchema(
    page_type="deformed_round_bar",
    name="Deformed and Round Bars",
    pages=[157],
    skip_header_rows=7,
    footer_pattern=FOOTER_PATTERN,
    section_pattern=SECTION_PATTERN_NUMERIC,
    value_count=2,
    columns=[
        ColumnDef("weight_kg_m", unit="kg/m"),
        ColumnDef("area_cm2", unit="cm²"),
    ],
)

# ══════════════════════════════════════════════
# 17) PIPES
# ══════════════════════════════════════════════

# Carbon Steel Pipes for General Structural - Light AA (page 120)
# Columns: nominal_in, nominal_mm, OD_min, OD_max, wall_in, wall_mm, weight_kg_m, weight_kg_ft, weight_lb_ft
CS_PIPE_LIGHT_AA = TableSchema(
    page_type="cs_pipe_light_aa",
    name="Carbon Steel Pipes for General Structural Light AA",
    pages=[120],
    skip_header_rows=6,
    footer_pattern=FOOTER_PATTERN_TOL,
    section_pattern=SECTION_PATTERN_PIPE_NOM_FRAC,
    value_count=8,
    columns=[
        ColumnDef("nominal_mm", unit="mm"),
        ColumnDef("od_min_mm", unit="mm"),
        ColumnDef("od_max_mm", unit="mm"),
        ColumnDef("wall_in", unit="in"),
        ColumnDef("wall_mm", unit="mm"),
        ColumnDef("weight_kg_m", unit="kg/m"),
        ColumnDef("weight_kg_ft", unit="kg/ft"),
        ColumnDef("weight_lb_ft", unit="lb/ft"),
    ],
)

# Carbon Steel Pipes for Ordinary Piping JIS G3452 SGP (page 122)
CS_PIPE_SGP = TableSchema(
    page_type="cs_pipe_sgp",
    name="Carbon Steel Pipes for Ordinary Piping JIS G3452",
    pages=[122],
    skip_header_rows=5,
    footer_pattern=FOOTER_PATTERN,
    section_pattern=SECTION_PATTERN_PIPE_NOM_DUAL,
    value_count=8,
    columns=[
        ColumnDef("od_mm", unit="mm"),
        ColumnDef("od_in", unit="in"),
        ColumnDef("wall_mm", unit="mm"),
        ColumnDef("wall_in", unit="in"),
        ColumnDef("weight_lb_ft", unit="lb/ft"),
        ColumnDef("weight_kg_m", unit="kg/m"),
        ColumnDef("test_pressure_kg", unit="kg/cm²"),
        ColumnDef("test_pressure_psi", unit="psi"),
    ],
)

# Carbon Steel Pipes for General Structural JIS G3444 (page 125)
CS_PIPE_STK = TableSchema(
    page_type="cs_pipe_stk",
    name="Carbon Steel Pipes for General Structural JIS G3444",
    pages=[125],
    skip_header_rows=7,
    footer_pattern=FOOTER_PATTERN_STK,
    section_pattern=SECTION_PATTERN_STK_OD,
    value_count=6,
    columns=[
        ColumnDef("wall_thickness_mm", unit="mm"),
        ColumnDef("weight_kg_m", unit="kg/m"),
        ColumnDef("area_cm2", unit="cm²"),
        ColumnDef("I_cm4", unit="cm⁴"),
        ColumnDef("Z_cm3", unit="cm³"),
        ColumnDef("r_cm", unit="cm"),
    ],
)

# ══════════════════════════════════════════════
# 18) APPENDIX
# ══════════════════════════════════════════════

# Gauge Table (page 265)
GAUGE_TABLE = TableSchema(
    page_type="gauge_table",
    name="Gauge Table SWG BWG BG BS USG",
    pages=[265],
    skip_header_rows=4,
    footer_pattern=FOOTER_PATTERN,
    section_pattern=SECTION_PATTERN_NUMERIC,
    value_count=4,
    columns=[
        ColumnDef("swg_mm", unit="mm"),
        ColumnDef("bwg_mm", unit="mm"),
        ColumnDef("bg_mm", unit="mm"),
        ColumnDef("usg_mm", unit="mm"),
    ],
)


ALL_SCHEMAS = [
    BEAM_DIMENSIONS,
    BEAM_INERTIA,
    BEAM_METRIC_DIMENSIONS,
    BEAM_METRIC_INERTIA,
    LIGHT_BEAM_DIMENSIONS,
    LIGHT_BEAM_INERTIA,
    LIGHT_BEAM_METRIC,
    BEARING_PILE_DIMENSIONS,
    BEARING_PILE_INERTIA,
    FRODINGHAM_PILE,
    LARSSEN_PILE,
    KSP_U_PILE,
    KSP_U_PILE_IMP,
    Z_TYPE_PILE,
    CF_SQUARE_METRIC,
    CF_RECT_METRIC,
    CF_SQUARE_IMPERIAL,
    CF_RECT_IMPERIAL,
    HF_SQUARE,
    HF_RECT,
    HF_CIRCULAR,
    PLAIN_CHANNEL,
    LIPPED_CHANNEL,
    U_CHANNEL_DIM,
    U_CHANNEL_PROP,
    U_CHANNEL_INCH,
    DIN_CHANNEL,
    Z_PURLIN,
    C_PURLIN,
    EQUAL_ANGLE,
    UNEQUAL_ANGLE_DIM,
    UNEQUAL_ANGLE_PROP,
    BULB_FLAT,
    SQUARE_BAR,
    DEFORMED_ROUND_BAR,
    CS_PIPE_LIGHT_AA,
    CS_PIPE_SGP,
    CS_PIPE_STK,
    GAUGE_TABLE,
]


def get_schema_for_page(page_num):
    for s in ALL_SCHEMAS:
        if page_num in s.pages:
            return s
    return None
