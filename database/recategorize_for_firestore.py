import json
import os
from collections import OrderedDict

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_PATH = os.path.join(SCRIPT_DIR, "raw_handbook.json")
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "firestore_export")

CATEGORY_MAP = [
    {
        "id": "i_beams",
        "name": "I-Beams",
        "pages": (14, 55),
        "sections": [
            {
                "id": "product_list_and_design_formulae",
                "name": "Product List & Design Formulae",
                "pages": (14, 20),
            },
            {
                "id": "i_beam_stress_strain_diagram",
                "name": "I-Beam Stress Strain Diagram",
                "pages": (21, 32),
            },
            {
                "id": "safe_loads",
                "name": "Safe Loads",
                "sections": [
                    {"id": "slenderness_and_geometry_ratio_allowable_stress", "name": "Slenderness & Geometry Ratio Allowable Stress", "pages": (33, 33)},
                    {"id": "stanchios_and_struts_allowable_stress", "name": "Stanchios & Struts Allowable Stress", "pages": (34, 34)},
                    {"id": "safe_loads_for_grade_43_steel", "name": "Safe Loads for Grade 43 Steel", "pages": (35, 36)},
                ],
            },
            {
                "id": "dimensions_and_values",
                "name": "Dimensions and Values",
                "sections": [
                    {"id": "universal_beams_and_columns", "name": "Universal Beams and Columns", "pages": (37, 48)},
                    {"id": "light_beam_and_joist", "name": "Light Beam and Joist", "pages": (49, 52)},
                    {"id": "bearing_pile", "name": "Bearing Pile", "pages": (53, 55)},
                ],
            },
        ],
    },
    {
        "id": "steel_piles",
        "name": "Steel Piles",
        "pages": (57, 65),
        "sections": [
            {"id": "steel_qualities", "name": "Steel Qualities", "pages": (57, 57)},
            {"id": "recommended_working_stresses_for_steel_sheet_piling", "name": "Recommended Working Stresses for Steel Sheet Piling", "pages": (57, 57)},
            {"id": "frodingham_steel_sheet_piling", "name": "Frodingham Steel Sheet Piling", "pages": (58, 58)},
            {"id": "larssen_steel_sheet_piling", "name": "Larssen Steel Sheet Piling", "pages": (59, 59)},
            {"id": "circular_construction", "name": "Circular Construction", "pages": (60, 60)},
            {"id": "minimum_effective_life_for_maximum_stress", "name": "Minimum Effective Life for Maximum Stress", "pages": (61, 61)},
            {
                "id": "dimensions_and_properties",
                "name": "Dimensions and Properties",
                "sections": [
                    {"id": "u_type", "name": "U-Type", "pages": (62, 63)},
                    {"id": "z_type", "name": "Z-Type", "pages": (64, 64)},
                    {"id": "straight_web_type", "name": "Straight Web Type", "pages": (64, 64)},
                ],
            },
        ],
    },
    {
        "id": "api_pipes",
        "name": "API Pipes ERW & Seamless Pipes",
        "pages": (66, 84),
        "sections": [
            {"id": "product_list", "name": "Product List", "pages": (66, 66)},
            {"id": "tensile_and_chemical_requirements", "name": "Tensile & Chemical Requirements", "pages": (67, 67)},
            {"id": "chemical_requirement_for_ladle_analysis", "name": "Chemical Requirement for Ladle Analysis", "pages": (68, 68)},
            {"id": "comparative_tables_of_steel_qualities", "name": "Comparative Tables of Steel Qualities", "pages": (69, 70)},
            {"id": "tolerances", "name": "Tolerances", "pages": (71, 71)},
            {"id": "sizing_and_pressure", "name": "Sizing & Pressure", "pages": (72, 84)},
        ],
    },
    {
        "id": "cold_formed_hollow_sections",
        "name": "Cold Formed Hollow Sections",
        "pages": (86, 100),
        "sections": [
            {"id": "product_list_and_standard_specifications", "name": "Product List & Standard Specifications", "pages": (86, 89)},
            {"id": "square_metric", "name": "Square (Metric)", "pages": (90, 91)},
            {"id": "rectangular_metric", "name": "Rectangular (Metric)", "pages": (92, 93)},
            {"id": "square_imperial", "name": "Square (Imperial)", "pages": (94, 96)},
            {"id": "rectangular_imperial", "name": "Rectangular (Imperial)", "pages": (97, 100)},
        ],
    },
    {
        "id": "hot_formed_hollow_sections",
        "name": "Hot Formed Hollow Sections",
        "pages": (101, 111),
    },
    {
        "id": "pipes",
        "name": "Pipes",
        "pages": (112, 125),
        "sections": [
            {"id": "technical_specs_and_standards", "name": "Technical Specs & Standards", "pages": (112, 115)},
            {"id": "bs_welded_steel_pipes", "name": "BS Welded Steel Pipes", "pages": (116, 119)},
            {"id": "carbon_steel_for_general_structural", "name": "Carbon Steel for General Structural", "pages": (120, 120)},
            {"id": "carbon_steel_for_scaffolding", "name": "Carbon Steel for Scaffolding", "pages": (121, 121)},
            {"id": "carbon_steel_for_ordinary_piping", "name": "Carbon Steel for Ordinary Piping", "pages": (122, 122)},
            {"id": "carbon_steel_for_machine_structural", "name": "Carbon Steel for Machine Structural", "pages": (123, 124)},
            {"id": "carbon_steel_for_general_structural_2", "name": "Carbon Steel for General Structural", "pages": (125, 125)},
        ],
    },
    {
        "id": "channels",
        "name": "Channels",
        "pages": (126, 135),
        "sections": [
            {"id": "product_list", "name": "Product List", "pages": (126, 126)},
            {"id": "safe_loads", "name": "Safe Loads", "pages": (127, 127)},
            {"id": "plain_channels", "name": "Plain Channels", "pages": (128, 128)},
            {"id": "lipped_channels", "name": "Lipped Channels", "pages": (129, 129)},
            {"id": "din_1026_channels", "name": "DIN 1026 Channels", "pages": (130, 130)},
            {"id": "u_channels", "name": "U-Channels", "pages": (131, 134)},
            {"id": "inch_series", "name": "Inch Series", "pages": (135, 135)},
        ],
    },
    {
        "id": "z_purlins",
        "name": "Z-Purlins",
        "pages": (136, 137),
        "sections": [
            {"id": "high_tensile_galvanised", "name": "High-Tensile Galvanised", "pages": (136, 137)},
        ],
    },
    {
        "id": "c_purlins",
        "name": "C-Purlins",
        "pages": (138, 140),
        "sections": [
            {"id": "high_tensile_galvanised", "name": "High-Tensile Galvanised", "pages": (138, 139)},
            {"id": "purlin_selection_tables", "name": "Purlin Selection Tables", "pages": (140, 140)},
        ],
    },
    {
        "id": "angles",
        "name": "Angles",
        "pages": (142, 151),
        "sections": [
            {"id": "product_list", "name": "Product List", "pages": (142, 142)},
            {"id": "equal_angles", "name": "Equal Angles", "pages": (143, 144)},
            {"id": "unequal_angles", "name": "Unequal Angles", "pages": (145, 150)},
            {"id": "inverted_angles", "name": "Inverted Angles", "pages": (151, 151)},
        ],
    },
    {
        "id": "bars",
        "name": "Bars",
        "pages": (152, 157),
        "sections": [
            {"id": "flat_bars", "name": "Flat Bars", "pages": (152, 154)},
            {"id": "bulb_flats", "name": "Bulb Flats", "pages": (155, 155)},
            {"id": "square_deformed_and_round_bars", "name": "Square, Deformed & Round Bars", "pages": (156, 157)},
        ],
    },
    {
        "id": "plates",
        "name": "Plates",
        "pages": (158, 176),
        "sections": [
            {"id": "product_list", "name": "Product List", "pages": (158, 158)},
            {"id": "specifications", "name": "Specifications", "pages": (159, 167)},
            {"id": "weight_tables", "name": "Weight Tables", "pages": (168, 169)},
            {"id": "technical_reference", "name": "Technical Reference", "pages": (170, 170)},
            {"id": "chequered_plates", "name": "Chequered Plates", "pages": (171, 171)},
            {"id": "cold_rolled_coils_and_sheets", "name": "Cold Rolled Coils & Sheets", "pages": (172, 173)},
            {"id": "electrolytic_galvanised", "name": "Electrolytic Galvanised", "pages": (174, 174)},
            {"id": "hot_dip_galvanised", "name": "Hot Dip Galvanised", "pages": (175, 175)},
            {"id": "galvanised_steel_sheets_dimensions", "name": "Galvanised Steel Sheets Dimensions", "pages": (176, 176)},
        ],
    },
    {
        "id": "galvanised_serrated_gratings",
        "name": "Galvanised Serrated Gratings",
        "pages": (177, 177),
    },
    {
        "id": "expanded_metal",
        "name": "Expanded Metal",
        "pages": (178, 179),
    },
    {
        "id": "wrought_steel_fittings",
        "name": "Wrought Steel Butt Welding Fittings",
        "pages": (180, 187),
        "sections": [
            {"id": "product_list", "name": "Product List", "pages": (180, 180)},
            {"id": "fitting_ends_and_45_degree_elbows", "name": "Fitting Ends & 45 Degree Elbows", "pages": (181, 181)},
            {"id": "90_degree_elbows", "name": "90 Degree Elbows", "pages": (182, 182)},
            {"id": "180_degree_returns", "name": "180 Degree Returns", "pages": (183, 183)},
            {"id": "reducers", "name": "Reducers", "pages": (184, 185)},
            {"id": "tees", "name": "Tees", "pages": (186, 186)},
            {"id": "reducing_fittings", "name": "Reducing Fittings", "pages": (187, 187)},
        ],
    },
    {
        "id": "flanges",
        "name": "Flanges",
        "pages": (188, 205),
        "sections": [
            {"id": "jis_5k", "name": "JIS 5K", "pages": (188, 188)},
            {"id": "jis_10k", "name": "JIS 10K", "pages": (188, 188)},
            {"id": "ansi_150lb_blind", "name": "ANSI 150LB Blind", "pages": (189, 189)},
            {"id": "ansi_300lb_blind", "name": "ANSI 300LB Blind", "pages": (189, 189)},
            {"id": "ansi_150lb_slip_on", "name": "ANSI 150LB Slip-On", "pages": (190, 190)},
            {"id": "ansi_300lb_slip_on", "name": "ANSI 300LB Slip-On", "pages": (190, 190)},
            {"id": "ansi_150lb_welding_neck", "name": "ANSI 150LB Welding Neck", "pages": (191, 191)},
            {"id": "ansi_300lb_welding_neck", "name": "ANSI 300LB Welding Neck", "pages": (191, 191)},
            {"id": "ansi_class_600", "name": "ANSI CLASS 600", "pages": (192, 192)},
            {"id": "ansi_class_900", "name": "ANSI CLASS 900", "pages": (192, 192)},
            {"id": "ansi_class_1500", "name": "ANSI CLASS 1500", "pages": (193, 193)},
            {"id": "bs_slip_on_pn_6", "name": "BS Slip-On PN 6", "pages": (194, 194)},
            {"id": "bs_slip_on_pn_10", "name": "BS Slip-On PN 10", "pages": (194, 194)},
            {"id": "bs_slip_on_pn_16", "name": "BS Slip-On PN 16", "pages": (195, 195)},
            {"id": "bs_slip_on_pn_25", "name": "BS Slip-On PN 25", "pages": (195, 195)},
            {"id": "bs_slip_on_pn_40", "name": "BS Slip-On PN 40", "pages": (196, 196)},
            {"id": "bs_slip_on_pn_64", "name": "BS Slip-On PN 64", "pages": (196, 196)},
            {"id": "bs_slip_on_pn_100", "name": "BS Slip-On PN 100", "pages": (197, 197)},
            {"id": "bs_slip_on_pn_160", "name": "BS Slip-On PN 160", "pages": (197, 197)},
            {"id": "bs_slip_on_pn_250", "name": "BS Slip-On PN 250", "pages": (198, 198)},
            {"id": "din_welding_neck_pn_16", "name": "DIN Welding Neck PN 16", "pages": (199, 199)},
            {"id": "din_welding_neck_pn_40", "name": "DIN Welding Neck PN 40", "pages": (200, 200)},
            {"id": "bs10_table_a", "name": "BS10 TABLE A", "pages": (201, 201)},
            {"id": "bs10_table_d", "name": "BS10 TABLE D", "pages": (201, 201)},
            {"id": "bs10_table_e", "name": "BS10 TABLE E", "pages": (202, 202)},
            {"id": "bs10_table_f", "name": "BS10 TABLE F", "pages": (202, 202)},
            {"id": "bs10_table_h", "name": "BS10 TABLE H", "pages": (203, 203)},
            {"id": "bs10_table_j", "name": "BS10 TABLE J", "pages": (203, 203)},
            {"id": "bs10_table_k", "name": "BS10 TABLE K", "pages": (204, 204)},
            {"id": "bs10_table_r", "name": "BS10 TABLE R", "pages": (204, 204)},
            {"id": "bs10_table_s", "name": "BS10 TABLE S", "pages": (205, 205)},
            {"id": "bs10_table_t", "name": "BS10 TABLE T", "pages": (205, 205)},
        ],
    },
    {
        "id": "stainless_steel_products",
        "name": "Stainless Steel Products",
        "pages": (206, 247),
        "sections": [
            {"id": "general_information", "name": "General Information", "pages": (206, 209)},
            {"id": "coils_sheets_and_plates", "name": "Coils, Sheets & Plates", "pages": (210, 214)},
            {"id": "angles_and_flats", "name": "Angles & Flats", "pages": (215, 218)},
            {"id": "bars", "name": "Bars", "pages": (219, 223)},
            {"id": "welded_channels", "name": "Welded Channels", "pages": (224, 224)},
            {"id": "welded_tubings", "name": "Welded Tubings", "pages": (225, 229)},
            {"id": "pipes", "name": "Pipes", "pages": (230, 233)},
            {"id": "fittings", "name": "Fittings", "pages": (234, 247)},
        ],
    },
    {
        "id": "machinery_steel_products",
        "name": "Machinery Steel Products",
        "pages": (248, 253),
        "sections": [
            {"id": "harden_and_tempered_steel", "name": "Harden & Tempered Steel", "pages": (248, 250)},
            {"id": "cold_finished_steel_bar", "name": "Cold Finished Steel Bar", "pages": (251, 253)},
        ],
    },
    {
        "id": "non_ferrous_metals",
        "name": "Non-Ferrous Metals",
        "pages": (254, 263),
        "sections": [
            {"id": "product_list", "name": "Product List", "pages": (254, 254)},
            {"id": "copper", "name": "Copper", "pages": (255, 255)},
            {"id": "brass", "name": "Brass", "pages": (256, 259)},
            {"id": "bronze", "name": "Bronze", "pages": (260, 263)},
        ],
    },
]


def _flatten_sections(cat, sections, parent_sub_id=None, parent_sub_name=None):
    results = []
    for sec in sections:
        if "sections" in sec:
            results.extend(_flatten_sections(cat, sec["sections"], sec["id"], sec["name"]))
        else:
            s_start, s_end = sec["pages"]
            for p in range(s_start, s_end + 1):
                results.append({
                    "page": p,
                    "collection_id": cat["id"],
                    "subcollection_id": parent_sub_id,
                    "sub_subcollection_id": sec["id"],
                    "category": cat["name"],
                    "subcategory": parent_sub_name,
                    "sub_subcategory": sec["name"],
                })
    return results


def build_page_lookup(categories):
    lookup = {}
    for cat in categories:
        sections = cat.get("sections", [])
        if sections:
            for entry in _flatten_sections(cat, sections):
                p = entry["page"]
                lookup.setdefault(p, []).append({
                    "collection_id": entry["collection_id"],
                    "subcollection_id": entry["subcollection_id"],
                    "sub_subcollection_id": entry["sub_subcollection_id"],
                    "category": entry["category"],
                    "subcategory": entry["subcategory"],
                    "sub_subcategory": entry["sub_subcategory"],
                })
        else:
            c_start, c_end = cat["pages"]
            for p in range(c_start, c_end + 1):
                lookup.setdefault(p, []).append({
                    "collection_id": cat["id"],
                    "subcollection_id": None,
                    "sub_subcollection_id": None,
                    "category": cat["name"],
                    "subcategory": None,
                    "sub_subcategory": None,
                })
    return lookup


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    with open(INPUT_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    lookup = build_page_lookup(CATEGORY_MAP)

    pages_by_group = {}

    for table in data["tables"]:
        page = table["page"]
        metas = lookup.get(page)
        if metas is None:
            print(f"WARNING: Page {page} not found in category map — skipping")
            continue

        for meta in metas:
            col_id = meta["collection_id"]
            sub_id = meta["subcollection_id"]
            subsub_id = meta["sub_subcollection_id"]
            group_key = (col_id, sub_id, subsub_id)

            doc = {
                "_doc_id": f"page_{page:03d}",
                "page": page,
                "category": meta["category"],
                "subcategory": meta["subcategory"],
                "sub_subcategory": meta["sub_subcategory"],
                "rows": table["rows"],
            }
            pages_by_group.setdefault(group_key, []).append(doc)

    for (col_id, sub_id, subsub_id), docs in pages_by_group.items():
        docs.sort(key=lambda d: d["page"])
        parts = [col_id]
        if sub_id:
            parts.append(sub_id)
        if subsub_id:
            parts.append(subsub_id)
        filename = "__".join(parts) + ".ndjson"
        out_path = os.path.join(OUTPUT_DIR, filename)
        with open(out_path, "w", encoding="utf-8") as f:
            for doc in docs:
                f.write(json.dumps(doc, ensure_ascii=False) + "\n")
        print(f"Wrote {len(docs)} docs → {out_path}")

    cat_map_path = os.path.join(OUTPUT_DIR, "category_map.json")
    with open(cat_map_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "filename": data["filename"],
                "pageCount": data["pageCount"],
                "collections": [
                    OrderedDict([
                        ("id", cat["id"]),
                        ("name", cat["name"]),
                        ("page_start", cat["pages"][0]),
                        ("page_end", cat["pages"][1]),
                        ("page_count", cat["pages"][1] - cat["pages"][0] + 1),
                        ("sections", _build_sections_json(cat.get("sections", [])) or None),
                    ]) for cat in CATEGORY_MAP
                ],
            },
            f, indent=2, ensure_ascii=False,
        )
    print(f"Wrote category map → {cat_map_path}")
    print("Done.")


def _build_sections_json(sections):
    if not sections:
        return None
    result = []
    for sec in sections:
        entry = OrderedDict([("id", sec["id"]), ("name", sec["name"])])
        if "pages" in sec:
            entry["page_start"] = sec["pages"][0]
            entry["page_end"] = sec["pages"][1]
            entry["page_count"] = sec["pages"][1] - sec["pages"][0] + 1
        if "sections" in sec:
            entry["sections"] = _build_sections_json(sec["sections"])
        result.append(entry)
    return result


if __name__ == "__main__":
    main()
