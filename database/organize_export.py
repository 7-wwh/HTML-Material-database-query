import os
import shutil

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SOURCE_DIR = os.path.join(SCRIPT_DIR, "firestore_export")
TARGET_ROOT = os.path.join(SCRIPT_DIR, "firestore_organized")

MAPPING = {
    "universal_beams_and_columns": "i_beams/Dimensions_and_values/universal_beams_and_columns",
    "light_beam_and_joist": "i_beams/Dimensions_and_values/light_beam_and_joist",
    "bearing_pile": "i_beams/Dimensions_and_values/bearing_pile",
    "slenderness_and_geometry_ratio_allowable_stress": "i_beams/safe_loads/slenderness_and_geometry_ratio_allowable_stress",
    "stanchios_and_struts_allowable_stress": "i_beams/safe_loads/stanchios_and_struts_allowable_stress",
    "safe_loads_for_grade_43_steel": "i_beams/safe_loads/safe_loads_for_grade_43_steel",
    "frodingham_steel_sheet_piling": "steel_piles/frodingham_steel_sheet_piling",
    "larssen_steel_sheet_piling": "steel_piles/larssen_steel_sheet_piling",
    "u_type": "steel_piles/dimensions_and_properties/u_type",
    "z_type": "steel_piles/dimensions_and_properties/z_type",
    "api_pipes": "api_pipes",
    "square_metric": "cold_formed_hollow_sections/square_metric",
    "rectangular_metric": "cold_formed_hollow_sections/rectangular_metric",
    "square_imperial": "cold_formed_hollow_sections/square_imperial",
    "rectangular_imperial": "cold_formed_hollow_sections/rectangular_imperial",
    "hot_formed_hollow_sections": "hot_formed_hollow_sections",
    "bs_welded_steel_pipes": "pipes/bs_welded_steel_pipes",
    "carbon_steel_for_general_structural": "pipes/carbon_steel_for_general_structural",
    "carbon_steel_for_scaffolding": "pipes/carbon_steel_for_scaffolding",
    "carbon_steel_for_ordinary_piping": "pipes/carbon_steel_for_ordinary_piping",
    "plain_channels": "channels/plain_channels",
    "lipped_channels": "channels/lipped_channels",
    "din_1026_channels": "channels/din_1026_channels",
    "u_channels": "channels/u_channels",
    "inch_series": "channels/inch_series",
    "z_purlins_high_tensile_galvanised": "z_purlins/high_tensile_galvanised",
    "c_purlins_high_tensile_galvanised": "c_purlins/high_tensile_galvanised",
    "equal_angles": "angles/equal_angles",
    "unequal_angles": "angles/unequal_angles",
    "flat_bars": "bars/flat_bars",
    "bulb_flats": "bars/bulb_flats",
    "square_deformed_and_round_bars": "bars/square_deformed_and_round_bars",
    "chequered_plates": "plates/chequered_plates",
    "galvanised_steel_sheets_dimensions": "plates/galvanised_steel_sheets_dimensions",
    "round_bars_stainless": "stainless_steel_products/round_bars",
    "welded_channels_stainless": "stainless_steel_products/welded_channels",
    "sheets_plates_weights": "stainless_steel_products/sheets_plates",
    "carbon_steel_machinery": "machinery_steel_products/carbon_steel",
    "chromium_and_crmo_steels": "machinery_steel_products/chromium_and_crmo_steels",
    "nickel_chromium_steels": "machinery_steel_products/nickel_chromium_steels",
    "cold_finished_free_cutting_steel": "machinery_steel_products/cold_finished_free_cutting_steel",
    "copper_round_hex_square_bars": "non_ferrous_metals/copper_round_hex_square_bars",
    "brass_round_hex_square_bars": "non_ferrous_metals/brass_round_hex_square_bars",
    "brass_sheets": "non_ferrous_metals/brass_sheets",
}


def main():
    if os.path.exists(TARGET_ROOT):
        shutil.rmtree(TARGET_ROOT)

    for name, subpath in MAPPING.items():
        src = os.path.join(SOURCE_DIR, f"{name}.ndjson")
        dst_dir = os.path.join(TARGET_ROOT, subpath)
        dst = os.path.join(dst_dir, f"{name}.ndjson")
        os.makedirs(dst_dir, exist_ok=True)
        shutil.copy2(src, dst)
        print(f"  {name}.ndjson -> {subpath}/")

    gauge_src = os.path.join(SOURCE_DIR, "gauge_table.ndjson")
    gauge_dst = os.path.join(TARGET_ROOT, "gauge_table.ndjson")
    shutil.copy2(gauge_src, gauge_dst)
    print(f"  gauge_table.ndjson -> . (root)")

    print(f"\nDone. Files organized under {TARGET_ROOT}")


if __name__ == "__main__":
    main()
