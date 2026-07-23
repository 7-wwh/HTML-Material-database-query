"""
Generate output-schema-plan.txt — documents the output fields for all 133 leaves.
"""

import schemas
from schemas import LeafSchema


def fmt_col(col):
    typ = col.type if col.type != "float" else "num"
    unit = f" ({col.unit})" if col.unit else ""
    return f"    {col.name:<28s} {typ:<6s}{unit}"


def active_leaf_block(leaf):
    pages = ", ".join(str(p) for p in sorted(leaf.pages))
    lines = [f"✅ {leaf.leaf_id}  (p{pages})"]
    lines.append(f"  Description: {leaf.name or leaf.leaf_id}")
    lines.append("  Output fields:")
    fields = []
    for pg in leaf.page_groups:
        for c in pg.columns:
            fields.append(fmt_col(c))
    if not fields:
        lines.append("    (no columns defined)")
    for f in fields:
        lines.append(f)
    lines.append("")
    return "\n".join(lines)


PA = "PLANNED"

def plan_block(leaf_id, pages, name, fields, note=""):
    pages_str = ", ".join(str(p) for p in sorted(pages))
    lines = [f"⏭️ {leaf_id}  (p{pages_str})"]
    lines.append(f"  Description: {name}")
    if note:
        lines.append(f"  Note: {note}")
    lines.append("  Planned output fields:")
    for fname, ftype, funit, fdesc in fields:
        unit = f" ({funit})" if funit else ""
        lines.append(f"    {fname:<28s} {ftype:<6s}{unit}")
    lines.append("")
    return "\n".join(lines)


def no_data_block(leaf_id, pages, name, reason=""):
    pages_str = ", ".join(str(p) for p in sorted(pages))
    lines = [f"⏭️ {leaf_id}  (p{pages_str})"]
    lines.append(f"  Description: {name}")
    lines.append("  No tabular data — not parseable.")
    if reason:
        lines.append(f"  ({reason})")
    lines.append("")
    return "\n".join(lines)


# Collect active leaf IDs
active_ids = set()
for leaf in schemas.LEAVES:
    if isinstance(leaf, LeafSchema) and leaf.page_groups:
        active_ids.add(leaf.leaf_id)


def auto_active_leaves(ids):
    """Return active leaf blocks for the given leaf IDs, in schema order."""
    blocks = []
    for leaf in schemas.LEAVES:
        if isinstance(leaf, LeafSchema) and leaf.leaf_id in ids and leaf.page_groups:
            blocks.append(active_leaf_block(leaf))
    return "\n".join(blocks)


def all_active():
    """Return all active leaves in schema order."""
    blocks = []
    for leaf in schemas.LEAVES:
        if isinstance(leaf, LeafSchema) and leaf.page_groups:
            blocks.append(active_leaf_block(leaf))
    return "\n".join(blocks)


# ══════════════════════════════════════════════════════════════════════════════
# SECTIONS — define ALL leaves (active + planned) in section order
# Each section is a list of (type, args) where type is 'active', 'plan', or 'none'
# ══════════════════════════════════════════════════════════════════════════════

SECTIONS = [
    # (section_header, [(type, leaf_id, pages, name, fields_or_note_or_none)])
    # type: 'A' = active (from schemas), 'P' = plan, 'N' = no data
]

def make_sections():
    s = []

    def sec(title):
        s.append("=" * 79)
        s.append(title)
        s.append("=" * 79)
        s.append("")

    def auto(ids):
        for leaf in schemas.LEAVES:
            if isinstance(leaf, LeafSchema) and leaf.leaf_id in ids and leaf.page_groups:
                s.append(active_leaf_block(leaf))

    def plan(lid, pages, name, fields, note=""):
        s.append(plan_block(lid, pages, name, fields, note))

    def nodata(lid, pages, name, reason=""):
        s.append(no_data_block(lid, pages, name, reason))

    # ── I-BEAMS ──
    sec("I-BEAMS (pages 14-55)")
    nodata("product_list_and_design_formulae", range(14,21),
        "Product List and Design Formulae", "Product index and engineering formulae (descriptive)")
    nodata("i_beam_stress_strain_diagram", range(21,33),
        "I-Beam Stress-Strain Diagram", "Beam theory and design text (descriptive)")
    auto(["slenderness_and_geometry_ratio_allowable_stress",
          "stanchios_and_struts_allowable_stress",
          "safe_loads_for_grade_43_steel",
          "universal_beams_and_columns",
          "light_beam_and_joist",
          "bearing_pile"])

    # ── STEEL PILES ──
    sec("STEEL PILES (pages 57-65)")
    nodata("steel_qualities", [57], "Steel Qualities", "Descriptive text")
    nodata("recommended_working_stresses_for_steel_sheet_piling", [57],
        "Recommended Working Stresses", "Reference stress table")
    auto(["frodingham_steel_sheet_piling", "larssen_steel_sheet_piling"])
    nodata("circular_construction", [60], "Circular Construction", "Engineering reference data")
    nodata("minimum_effective_life_for_maximum_stress", [61],
        "Minimum Effective Life for Max Stress", "Complex process table")
    auto(["u_type", "z_type"])
    nodata("straight_web_type", [64], "Straight Web Type", "Part of Z-type page")

    # ── API PIPES ──
    sec("API PIPES (pages 66-85)")
    auto(["api_pipes"])

    # ── COLD FORMED HOLLOW SECTIONS ──
    sec("COLD FORMED HOLLOW SECTIONS (pages 86-100)")
    nodata("product_list_and_standard_specifications", range(86,90),
        "Product List and Standard Specs", "Product list + spec text")
    auto(["square_metric", "rectangular_metric", "square_imperial", "rectangular_imperial"])

    # ── HOT FORMED HOLLOW SECTIONS ──
    sec("HOT FORMED HOLLOW SECTIONS (pages 101-111)")
    nodata("hot_formed_hollow_sections_intro", range(101,105),
        "Hot Formed Hollow Sections Intro", "Intro + spec references")
    auto(["hot_formed_hollow_sections"])

    # ── PIPES ──
    sec("PIPES (pages 112-125)")
    nodata("technical_specs_and_standards", range(112,116),
        "Technical Specs and Standards", "Pipe spec reference text")
    auto(["bs_welded_steel_pipes", "carbon_steel_for_general_structural",
          "carbon_steel_for_scaffolding", "carbon_steel_for_ordinary_piping"])
    plan("carbon_steel_for_machine_structural", [123, 124],
        "Carbon Steel for Machine Structural JIS G3445",
        [("section", "str", "", "Grade designation"),
         ("nominal_mm", "num", "mm", "Nominal diameter"),
         ("od_min_mm", "num", "mm", "Outside diameter min"),
         ("od_max_mm", "num", "mm", "Outside diameter max"),
         ("wall_in", "num", "in", "Wall thickness (inches)"),
         ("wall_mm", "num", "mm", "Wall thickness (mm)"),
         ("weight_kg_m", "num", "kg/m", "Weight per metre"),
         ("weight_lb_ft", "num", "lb/ft", "Weight per foot")],
        "Schedule-like table with continuation rows")

    # ── CHANNELS ──
    sec("CHANNELS (pages 126-135)")
    nodata("product_list_channels", [126], "Product List — Channels", "TOC")
    plan("safe_loads_channels", [127], "Safe Loads — Channels",
        [("section", "str", "", "Channel designation"),
         ("mass_per_m", "num", "kg/m", "Mass per metre"),
         ("span_*", "num", "kN", "Safe load at given span"),
         ("critical_span", "num", "m", "Critical span")],
        "Safe load matrix; similar to I-beam safe loads")
    auto(["plain_channels", "lipped_channels", "din_1026_channels", "u_channels", "inch_series"])

    # ── PURLINS ──
    sec("PURLINS (pages 136-140)")
    auto(["z_purlins_high_tensile_galvanised", "c_purlins_high_tensile_galvanised"])
    nodata("purlin_selection_tables", [140], "Purlin Selection Tables", "Selection guide text")

    # ── ANGLES ──
    sec("ANGLES (pages 142-151)")
    nodata("product_list_angles", [142], "Product List — Angles", "TOC")
    auto(["equal_angles", "unequal_angles"])
    nodata("inverted_angles", [151], "Inverted Angles", "Text + complex table")

    # ── BARS ──
    sec("BARS (pages 152-157)")
    nodata("product_list_bars", [152], "Product List — Bars", "TOC")
    auto(["flat_bars", "bulb_flats", "square_deformed_and_round_bars"])

    # ── PLATES ──
    sec("PLATES (pages 158-176)")
    nodata("product_list_plates", [158], "Product List — Plates", "TOC")
    plan("specifications_plates", range(159,168), "Plates Specifications",
        [("section", "str", "", "Application / category"),
         ("ks", "str", "", "KS standard designation"),
         ("jis", "str", "", "JIS standard designation"),
         ("astm", "str", "", "ASTM standard designation"),
         ("bs", "str", "", "BS standard designation")],
        "Spec reference tables (KS/JIS/ASTM/BS)")
    plan("weight_tables_plates", [168, 169], "Plates Weight Tables",
        [("section", "num", "mm", "Thickness"),
         ("unit_weight", "num", "kg/m²", "Unit weight"),
         ("wt_size_*", "num", "kg", "Weight per sheet size")],
        "Matrix weight table — imperial (p168) + metric (p169)")
    nodata("technical_reference_plates", [170],
        "Technical Reference — Plates", "Chem comp + mech properties reference")
    auto(["chequered_plates"])
    plan("cold_rolled_coils_and_sheets", [172, 173], "Cold Rolled Coils and Sheets",
        [("section", "str", "", "Gauge (SWG/BWG/USG/BG)"),
         ("thickness_mm", "num", "mm", "Thickness"),
         ("size", "str", "", "Sheet size"),
         ("weight_lb_pc", "num", "lb/pc", "Weight per piece (lb)"),
         ("weight_kg_pc", "num", "kg/pc", "Weight per piece (kg)"),
         ("pcs_per_ton", "num", "", "Pieces per metric ton")],
        "Gauge/thickness/weight table with continuation rows")
    nodata("electrolytic_galvanised", [174],
        "Electrolytic Galvanised Coils and Sheets", "Spec reference (KS/JIS/ASTM)")
    nodata("hot_dip_galvanised", [175],
        "Hot Dip Galvanised Coils and Sheets", "Spec reference (KS/JIS/ASTM/BS)")
    auto(["galvanised_steel_sheets_dimensions"])

    # ── GRATINGS / EXPANDED METAL ──
    sec("GRATINGS / EXPANDED METAL (pages 177-179)")
    plan("galvanised_serrated_gratings", [177], "Galvanised Serrated Gratings — Loading Table",
        [("section", "str", "", "Bar type (e.g. 25x3)"),
         ("load_factor", "num", "", "Load factor"),
         ("mass_kg_m2", "num", "kg/m²", "Mass per m²"),
         ("span_*", "num", "N", "Safe load at given span (mm)"),
         ("max_span", "num", "mm", "Max recommended span")],
        "Complex loading table with multiple series")
    plan("expanded_metal", [178, 179], "Expanded Metal Specifications",
        [("section", "str", "", "Code (XM-nnn / G-nnnn)"),
         ("code_no", "num", "", "Code number"),
         ("material", "str", "", "Material"),
         ("swm_mm", "num", "mm", "Short way mesh"),
         ("lwm_mm", "num", "mm", "Long way mesh"),
         ("thickness_mm", "num", "mm", "Strand thickness (optional)"),
         ("strand_width_mm", "num", "mm", "Strand width (optional)"),
         ("weight_kg_m2", "num", "kg/m²", "Approx weight")],
        "Two sub-tables (XM + G); variable column count")

    # ── WROUGHT STEEL FITTINGS ──
    sec("WROUGHT STEEL FITTINGS (pages 180-187)")
    nodata("product_list_wrought_fittings", [180], "Product List — Wrought Fittings", "TOC")
    plan("fitting_ends_and_45_degree_elbows", [181],
        "Fitting Ends and 45° Elbows — Wrought",
        [("section", "str", "", "Nominal pipe size"),
         ("od_mm", "num", "mm", "Outside diameter"),
         ("center_to_face_mm", "num", "mm", "Center to face"),
         ("wall_thickness_mm", "num", "mm", "Wall thickness")])
    plan("90_degree_elbows_wrought", [182], "90° Elbows — Wrought",
        [("section", "str", "", "Nominal pipe size"),
         ("od_mm", "num", "mm", "Outside diameter"),
         ("center_to_face_mm", "num", "mm", "Center to face"),
         ("wall_thickness_mm", "num", "mm", "Wall thickness")])
    plan("180_degree_returns_wrought", [183], "180° Returns — Wrought",
        [("section", "str", "", "Nominal pipe size"),
         ("od_mm", "num", "mm", "Outside diameter"),
         ("center_to_center_mm", "num", "mm", "Center to center"),
         ("wall_thickness_mm", "num", "mm", "Wall thickness")])
    plan("reducers_wrought", [184, 185], "Reducers — Wrought",
        [("section", "str", "", "Large x small size"),
         ("length_mm", "num", "mm", "Overall length"),
         ("wall_thickness_mm", "num", "mm", "Wall thickness")])
    plan("tees_wrought", [186], "Tees — Wrought",
        [("section", "str", "", "Nominal pipe size"),
         ("od_mm", "num", "mm", "Outside diameter"),
         ("center_to_face_run_mm", "num", "mm", "Center to face (run)"),
         ("center_to_face_branch_mm", "num", "mm", "Center to face (branch)"),
         ("wall_thickness_mm", "num", "mm", "Wall thickness")])
    plan("reducing_fittings_wrought", [187], "Reducing Fittings — Wrought",
        [("section", "str", "", "Nominal size"),
         ("od_mm", "num", "mm", "Outside diameter"),
         ("wall_thickness_mm", "num", "mm", "Wall thickness"),
         ("dimensions", "str", "", "Various fitting dimensions")],
        "Complex multi-size fitting dimensions")

    # ── FLANGES ──
    sec("FLANGES (pages 188-205)")
    FLANGE_FIELDS = [
        ("section", "str", "", "Nominal diameter (mm/in)"),
        ("od_mm", "num", "mm", "Flange outside diameter"),
        ("thickness_mm", "num", "mm", "Flange thickness"),
        ("bolt_circle_mm", "num", "mm", "Bolt circle diameter"),
        ("bolt_holes", "num", "", "Number of bolt holes"),
        ("bolt_dia_mm", "num", "mm", "Bolt hole diameter"),
        ("hub_dia_mm", "num", "mm", "Hub diameter (welding neck)"),
        ("hub_length_mm", "num", "mm", "Hub length"),
    ]
    for lid, lname, lpages in [
        ("jis_5k", "JIS 5K Slip-On Flanges", [188]),
        ("jis_10k", "JIS 10K Slip-On Flanges", [188]),
        ("ansi_150lb_blind", "ANSI 150LB Blind Flanges", [189]),
        ("ansi_300lb_blind", "ANSI 300LB Blind Flanges", [189]),
        ("ansi_150lb_slip_on", "ANSI 150LB Slip-On Flanges", [190]),
        ("ansi_300lb_slip_on", "ANSI 300LB Slip-On Flanges", [190]),
        ("ansi_150lb_welding_neck", "ANSI 150LB Welding Neck Flanges", [191]),
        ("ansi_300lb_welding_neck", "ANSI 300LB Welding Neck Flanges", [191]),
        ("ansi_class_600", "ANSI Class 600 Flanges", [192]),
        ("ansi_class_900", "ANSI Class 900 Flanges", [192]),
        ("ansi_class_1500", "ANSI Class 1500 Flanges", [193]),
        ("bs_slip_on_pn_6", "BS Slip-On PN 6 Flanges", [194]),
        ("bs_slip_on_pn_10", "BS Slip-On PN 10 Flanges", [194]),
        ("bs_slip_on_pn_16", "BS Slip-On PN 16 Flanges", [195]),
        ("bs_slip_on_pn_25", "BS Slip-On PN 25 Flanges", [195]),
        ("bs_slip_on_pn_40", "BS Slip-On PN 40 Flanges", [196]),
        ("bs_slip_on_pn_64", "BS Slip-On PN 64 Flanges", [196]),
        ("bs_slip_on_pn_100", "BS Slip-On PN 100 Flanges", [197]),
        ("bs_slip_on_pn_160", "BS Slip-On PN 160 Flanges", [197]),
        ("bs_slip_on_pn_250", "BS Slip-On PN 250 Flanges", [198]),
        ("din_welding_neck_pn_16", "DIN Welding Neck PN 16 Flanges", [199]),
        ("din_welding_neck_pn_40", "DIN Welding Neck PN 40 Flanges", [200]),
        ("bs10_table_a", "BS10 Table A Flanges", [201]),
        ("bs10_table_d", "BS10 Table D Flanges", [201]),
        ("bs10_table_e", "BS10 Table E Flanges", [202]),
        ("bs10_table_f", "BS10 Table F Flanges", [202]),
        ("bs10_table_h", "BS10 Table H Flanges", [203]),
        ("bs10_table_j", "BS10 Table J Flanges", [203]),
        ("bs10_table_k", "BS10 Table K Flanges", [204]),
        ("bs10_table_r", "BS10 Table R Flanges", [204]),
        ("bs10_table_s", "BS10 Table S Flanges", [205]),
        ("bs10_table_t", "BS10 Table T Flanges", [205]),
    ]:
        plan(lid, lpages, lname, FLANGE_FIELDS, "Fraction-based nominal sizes")

    # ── STAINLESS STEEL PRODUCTS ──
    sec("STAINLESS STEEL PRODUCTS (pages 206-246)")
    nodata("general_information", range(206,210),
        "General Information — Stainless Steel", "Product list + descriptive text")
    plan("coils_sheets", [210], "Stainless Steel Coils & Sheets — Specifications",
        [("section", "str", "", "Application category"),
         ("aisi", "str", "", "AISI"), ("jis", "str", "", "JIS"),
         ("bs", "str", "", "BS"), ("din", "str", "", "DIN")],
        "Spec reference table")
    plan("sheets_plates", range(211,215),
        "Stainless Steel Sheets & Plates — Chemical Composition",
        [("section", "str", "", "Type"),
         ("aisi", "str", "", "AISI"), ("jis", "str", "", "JIS"),
         ("din", "str", "", "DIN"),
         ("c_percent", "str", "", "C %"), ("si_percent", "str", "", "Si % max"),
         ("mn_percent", "str", "", "Mn %"), ("p_percent", "str", "", "P % max"),
         ("s_percent", "str", "", "S % max"), ("ni_percent", "str", "", "Ni %"),
         ("cr_percent", "str", "", "Cr %"), ("mo_percent", "str", "", "Mo %"),
         ("other", "str", "", "Other elements")],
        "Two-row entries for some grades")
    plan("angles_stainless", [216, 217, 218],
        "Stainless Steel Angles — Dimensions & Properties",
        [("section", "str", "", "AISI type"),
         ("characteristics", "str", "", "Typical characteristics (text)")],
        "p216-217: descriptive text; p218: angle dimensions")
    auto(["sheets_plates_weights"])
    plan("flats_stainless", [219], "Stainless Steel Flats — Weight Table",
        [("section", "str", "", "Flat size"),
         ("thickness_mm", "num", "mm", "Thickness"),
         ("width_mm", "num", "mm", "Width"),
         ("weight_kg_m", "num", "kg/m", "Weight per metre")],
        "Matrix weight table")
    auto(["round_bars_stainless", "welded_channels_stainless"])
    plan("hexagon_square_bars_stainless", [224],
        "Stainless Steel Hexagon & Square Bars — Weights",
        [("section", "str", "", "Size"),
         ("weight_lb_ft", "num", "lb/ft", "Weight per foot"),
         ("weight_kg_ft", "num", "kg/ft", "Weight per foot (kg)")],
        "Two side-by-side tables (hex + square)")
    plan("welded_tubings_stainless", [226, 227, 228, 229],
        "Stainless Steel Welded Tubings — Dimensions & Weights",
        [("section", "num", "mm", "Outside diameter"),
         ("wall_thickness_mm", "num", "mm", "Wall thickness"),
         ("weight_kg_m", "num", "kg/m", "Weight per metre"),
         ("available_304l", "bool", "", "Available in 304L"),
         ("available_316l", "bool", "", "Available in 316L"),
         ("available_321", "bool", "", "Available in 321")],
        "Round/square/rectangular tubing tables")
    plan("pipes_stainless", range(230,235),
        "Stainless Steel Pipes — Schedules & Dimensions",
        [("section", "str", "", "Nominal size / schedule"),
         ("od_mm", "num", "mm", "Outside diameter"),
         ("wall_mm", "num", "mm", "Wall thickness"),
         ("schedule", "str", "", "Schedule"),
         ("weight_kg_m", "num", "kg/m", "Weight per metre")],
        "Mix of gauge reference + pipe schedules + chem specs")
    plan("elbows_90_long_radius", [236],
        "Stainless Steel 90° Long Radius Elbows",
        [("section", "str", "", "Nominal pipe size"),
         ("od_mm", "num", "mm", "Outside diameter"),
         ("center_to_face_mm", "num", "mm", "Center to face"),
         ("wall_thickness_mm", "num", "mm", "Wall thickness")])
    plan("elbows_90_short_radius", [237],
        "Stainless Steel 90° Short Radius Elbows",
        [("section", "str", "", "Nominal pipe size"),
         ("od_mm", "num", "mm", "Outside diameter"),
         ("center_to_face_mm", "num", "mm", "Center to face"),
         ("wall_thickness_mm", "num", "mm", "Wall thickness")])
    plan("returns_180_long_radius", [238],
        "Stainless Steel 180° Long Radius Returns",
        [("section", "str", "", "Nominal pipe size"),
         ("od_mm", "num", "mm", "Outside diameter"),
         ("center_to_center_mm", "num", "mm", "Center to center"),
         ("wall_thickness_mm", "num", "mm", "Wall thickness")])
    plan("straight_tees", [239], "Stainless Steel Straight Tees",
        [("section", "str", "", "Nominal pipe size"),
         ("od_mm", "num", "mm", "Outside diameter"),
         ("center_to_face_run_mm", "num", "mm", "Center to face (run)"),
         ("center_to_face_branch_mm", "num", "mm", "Center to face (branch)"),
         ("wall_thickness_mm", "num", "mm", "Wall thickness")])
    plan("reducing_outlet_tees", [240, 241], "Stainless Steel Reducing Outlet Tees",
        [("section", "str", "", "Run x branch size"),
         ("od_run_mm", "num", "mm", "Run OD"),
         ("od_branch_mm", "num", "mm", "Branch OD"),
         ("center_to_face_mm", "num", "mm", "Center to face"),
         ("wall_thickness_mm", "num", "mm", "Wall thickness")])
    plan("lap_joint_stub_ends", [242], "Stainless Steel Lap Joint Stub Ends",
        [("section", "str", "", "Nominal pipe size"),
         ("od_mm", "num", "mm", "Outside diameter"),
         ("length_mm", "num", "mm", "Overall length"),
         ("flange_diameter_mm", "num", "mm", "Flange diameter"),
         ("wall_thickness_mm", "num", "mm", "Wall thickness")])
    plan("reducers_stainless", [243, 244, 245], "Stainless Steel Reducers",
        [("section", "str", "", "Large x small size"),
         ("large_od_mm", "num", "mm", "Large end OD"),
         ("small_od_mm", "num", "mm", "Small end OD"),
         ("length_mm", "num", "mm", "Overall length"),
         ("wall_thickness_mm", "num", "mm", "Wall thickness")])
    nodata("caps_stainless", [246], "Stainless Steel Caps",
        "Complex dimension table with variable columns")

    # ── MACHINERY STEEL ──
    sec("MACHINERY STEEL (pages 248-252)")
    nodata("product_list_machinery", [248], "Product List — Machinery Steel", "TOC")
    auto(["carbon_steel_machinery", "chromium_and_crmo_steels",
          "nickel_chromium_steels", "cold_finished_free_cutting_steel"])

    # ── NON-FERROUS METALS ──
    sec("NON-FERROUS METALS (pages 254-262)")
    nodata("product_list_non_ferrous", [254], "Product List — Non-Ferrous", "TOC")
    auto(["copper_round_hex_square_bars", "brass_round_hex_square_bars"])
    plan("copper_flat_bars", [256], "Copper Flat Bars — Sizes and Unit Weights",
        [("section", "str", "", "Width (fractional inches)"),
         ("weight_lb_ft", "num", "lb/ft", "Weight per foot for each thickness")],
        "Matrix weight table (width x thickness); fraction-based")
    plan("brass_flat_bars", [258], "Brass Flat Bars — Sizes and Unit Weights",
        [("section", "str", "", "Width (fractional inches)"),
         ("weight_lb_ft", "num", "lb/ft", "Weight per foot for each thickness")],
        "Matrix weight table; identical structure to copper flat bars")
    auto(["brass_sheets"])
    nodata("bronze_continuous_casting_info", [260],
        "Bronze Continuous Casting Info", "Descriptive text")
    plan("bronze_tube_stock_sizes", [261], "Bronze Tube Stock Sizes & Weights",
        [("section", "str", "", "OD mm(in)"),
         ("id_mm", "num", "mm", "Inside diameter"),
         ("solid_weight_kg_ft", "num", "kg/ft", "Solid weight")],
        "Paired-column layout with continuation rows")
    plan("bronze_centrifugal_cast", [262], "Bronze Centrifugally Cast — Sizes",
        [("section", "str", "", "OD mm(in)"),
         ("id_mm", "num", "mm", "Inside diameter"),
         ("solid_weight_kg_ft", "num", "kg/ft", "Solid weight")],
        "Same paired-column layout as tube stock")

    # ── APPENDIX ──
    sec("APPENDIX (page 265)")
    auto(["gauge_table"])

    return "\n".join(s)


output = make_sections()

# Add header
header = """OUTPUT SCHEMA PLAN — Handbook Material Database
================================================
This document describes the output fields for each of the 133 Firestore leaves.
✅ = ACTIVE — schema implemented, NDJSON output being produced
⏭️ = PLANNED — schema not yet implemented (proposed output shown)

"""

with open("output_schema_plan.txt", "w") as f:
    f.write(header + output)

active_count = sum(1 for l in schemas.LEAVES if isinstance(l, LeafSchema) and l.page_groups)
skip_count = sum(1 for l in schemas.LEAVES if not isinstance(l, LeafSchema) or not l.page_groups)
print(f"Generated output_schema_plan.txt")
print(f"Active: {active_count} leaves | Skipped: {skip_count} leaves | Total: {active_count + skip_count}")
