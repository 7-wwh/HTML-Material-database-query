import os
import shutil

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SOURCE_DIR = os.path.join(SCRIPT_DIR, "firestore_export")
TARGET_ROOT = os.path.join(SCRIPT_DIR, "firestore_organized")

MAPPING = {
    "universal_beams_and_columns": "i_beams/Dimensions_and_values",
    "light_beam_and_joist": "i_beams/Dimensions_and_values",
    "bearing_pile": "i_beams/Dimensions_and_values",
    "slenderness_and_geometry_ratio_allowable_stress": "i_beams/safe_loads",
    "stanchios_and_struts_allowable_stress": "i_beams/safe_loads",
    "safe_loads_for_grade_43_steel": "i_beams/safe_loads",
    "frodingham_steel_sheet_piling": "steel_piles",
    "larssen_steel_sheet_piling": "steel_piles",
    "u_type": "steel_piles/dimensions_and_properties",
    "z_type": "steel_piles/dimensions_and_properties",
    "api_pipes": "",
    "square_metric": "cold_formed_hollow_sections",
    "rectangular_metric": "cold_formed_hollow_sections",
    "square_imperial": "cold_formed_hollow_sections",
    "rectangular_imperial": "cold_formed_hollow_sections",
    "hot_formed_hollow_sections": "",
    "bs_welded_steel_pipes": "pipes",
    "carbon_steel_for_general_structural": "pipes",
    "carbon_steel_for_scaffolding": "pipes",
    "carbon_steel_for_ordinary_piping": "pipes",
    "plain_channels": "channels",
    "lipped_channels": "channels",
    "din_1026_channels": "channels",
    "u_channels": "channels",
    "inch_series": "channels",
    "z_purlins_high_tensile_galvanised": "z_purlins",
    "c_purlins_high_tensile_galvanised": "c_purlins",
    "equal_angles": "angles",
    "unequal_angles": "angles",
    "flat_bars": "bars",
    "bulb_flats": "bars",
    "square_deformed_and_round_bars": "bars",
    "chequered_plates": "plates",
    "galvanised_steel_sheets_dimensions": "plates",
    "round_bars_stainless": "stainless_steel_products",
    "welded_channels_stainless": "stainless_steel_products",
    "sheets_plates_weights": "stainless_steel_products",
    "carbon_steel_machinery": "machinery_steel_products",
    "chromium_and_crmo_steels": "machinery_steel_products",
    "nickel_chromium_steels": "machinery_steel_products",
    "cold_finished_free_cutting_steel": "machinery_steel_products",
    "copper_round_hex_square_bars": "non_ferrous_metals",
    "brass_round_hex_square_bars": "non_ferrous_metals",
    "brass_sheets": "non_ferrous_metals",
    "gauge_table": "",
}


def main():
    if os.path.exists(TARGET_ROOT):
        shutil.rmtree(TARGET_ROOT)

    for name, subpath in MAPPING.items():
        src = os.path.join(SOURCE_DIR, f"{name}.ndjson")
        if subpath:
            dst_dir = os.path.join(TARGET_ROOT, subpath)
            dst = os.path.join(dst_dir, f"{name}.ndjson")
            os.makedirs(dst_dir, exist_ok=True)
        else:
            dst = os.path.join(TARGET_ROOT, f"{name}.ndjson")
        shutil.copy2(src, dst)
        print(f"  {name}.ndjson -> {'./' if not subpath else subpath + '/'}")

    print(f"\nDone. Files organized under {TARGET_ROOT}")


if __name__ == "__main__":
    main()
