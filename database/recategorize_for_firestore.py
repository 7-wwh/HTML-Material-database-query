import json
import os
from collections import OrderedDict

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_PATH = os.path.join(SCRIPT_DIR, "raw_handbook.json")
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "firestore_export")

CATEGORY_MAP = [
    {
        "id": "front_matter",
        "name": "Front Matter",
        "pages": (1, 13),
        "sections": [
            {"name": "Cover", "pages": (1, 1)},
            {"name": "Table of Contents", "pages": (2, 3)},
            {"name": "Company Profile", "pages": (4, 5)},
            {"name": "Explanatory Notes", "pages": (6, 13)},
        ],
    },
    {
        "id": "i_beams",
        "name": "I-Beams",
        "pages": (14, 34),
        "sections": [
            {"name": "Product List & Design Formulae", "pages": (14, 20)},
            {"name": "Safe Loads & Dimensions", "pages": (21, 33)},
            {"name": "Axial Stresses", "pages": (34, 34)},
        ],
    },
    {
        "id": "universal_beams_and_columns",
        "name": "Universal Beams and Columns",
        "pages": (35, 48),
        "sections": [
            {"name": "Safe Loads", "pages": (35, 47)},
            {"name": "Section Properties", "pages": (48, 48)},
        ],
    },
    {
        "id": "light_beams_and_joists",
        "name": "Light Beams and Joists",
        "pages": (49, 52),
    },
    {
        "id": "bearing_piles",
        "name": "Bearing Piles",
        "pages": (53, 55),
    },
    {
        "id": "steel_piles",
        "name": "Steel Piles",
        "pages": (56, 65),
    },
    {
        "id": "api_pipes",
        "name": "API Pipes ERW & Seamless Pipes",
        "pages": (66, 85),
    },
    {
        "id": "cold_formed_hollow_sections",
        "name": "Cold Formed Hollow Sections",
        "pages": (86, 100),
        "sections": [
            {"name": "Product List & Standard Specifications", "pages": (86, 89)},
            {"name": "Square (Metric)", "pages": (90, 91)},
            {"name": "Rectangular (Metric)", "pages": (92, 93)},
            {"name": "Square (Imperial)", "pages": (94, 96)},
            {"name": "Rectangular (Imperial)", "pages": (97, 100)},
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
            {"name": "Technical Specs & British Standard", "pages": (112, 116)},
            {"name": "Carbon Steel Pipes", "pages": (117, 125)},
        ],
    },
    {
        "id": "channels",
        "name": "Channels",
        "pages": (126, 135),
        "sections": [
            {"name": "Safe Loads", "pages": (126, 131)},
            {"name": "Lipped Channels", "pages": (132, 134)},
            {"name": "Inch Series", "pages": (135, 135)},
        ],
    },
    {
        "id": "z_purlins",
        "name": "Z-Purlins",
        "pages": (136, 137),
    },
    {
        "id": "c_purlins",
        "name": "C-Purlins",
        "pages": (138, 141),
    },
    {
        "id": "angles",
        "name": "Angles",
        "pages": (142, 151),
        "sections": [
            {"name": "Equal Angles", "pages": (142, 149)},
            {"name": "Unequal Angles", "pages": (150, 151)},
        ],
    },
    {
        "id": "bars",
        "name": "Bars",
        "pages": (152, 157),
        "sections": [
            {"name": "Flat Bars", "pages": (152, 154)},
            {"name": "Bulb Flats", "pages": (155, 155)},
            {"name": "Square, Deformed & Round Bars", "pages": (156, 157)},
        ],
    },
    {
        "id": "plates",
        "name": "Plates",
        "pages": (158, 176),
        "sections": [
            {"name": "Specifications", "pages": (158, 169)},
            {"name": "Chequered Plates", "pages": (170, 170)},
            {"name": "Cold Rolled Coils & Sheets", "pages": (171, 172)},
            {"name": "Galvanised Steel Sheets", "pages": (173, 176)},
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
    },
    {
        "id": "flanges",
        "name": "Flanges",
        "pages": (188, 205),
        "sections": [
            {"name": "JIS Flanges", "pages": (188, 192)},
            {"name": "ANSI Flanges", "pages": (193, 197)},
            {"name": "Slip-On Flanges", "pages": (198, 204)},
            {"name": "Welding Neck Flanges", "pages": (205, 205)},
        ],
    },
    {
        "id": "stainless_steel_products",
        "name": "Stainless Steel Products",
        "pages": (206, 247),
        "sections": [
            {"name": "General Information", "pages": (206, 209)},
            {"name": "Coils, Sheets & Plates", "pages": (210, 214)},
            {"name": "Angles & Flats", "pages": (215, 218)},
            {"name": "Bars", "pages": (219, 223)},
            {"name": "Welded Channels", "pages": (224, 224)},
            {"name": "Welded Tubings", "pages": (225, 229)},
            {"name": "Pipes", "pages": (230, 233)},
            {"name": "Fittings", "pages": (234, 247)},
        ],
    },
    {
        "id": "machinery_steel_products",
        "name": "Machinery Steel Products",
        "pages": (248, 253),
        "sections": [
            {"name": "Harden & Tempered Steel", "pages": (248, 250)},
            {"name": "Cold Finished Steel Bar", "pages": (251, 253)},
        ],
    },
    {
        "id": "non_ferrous_metals",
        "name": "Non-Ferrous Metals",
        "pages": (254, 263),
        "sections": [
            {"name": "Product List", "pages": (254, 254)},
            {"name": "Copper", "pages": (255, 255)},
            {"name": "Brass", "pages": (256, 259)},
            {"name": "Bronze", "pages": (260, 263)},
        ],
    },
    {
        "id": "appendix",
        "name": "Appendix",
        "pages": (264, 267),
        "sections": [
            {"name": "Gauge Table", "pages": (264, 265)},
            {"name": "Conversion Factors", "pages": (266, 267)},
        ],
    },
]


def build_page_lookup(categories):
    lookup = {}
    for cat in categories:
        c_start, c_end = cat["pages"]
        sections = cat.get("sections", [])
        if sections:
            for sec in sections:
                s_start, s_end = sec["pages"]
                for p in range(s_start, s_end + 1):
                    lookup[p] = {
                        "collection_id": cat["id"],
                        "category": cat["name"],
                        "subcategory": sec["name"],
                    }
        else:
            for p in range(c_start, c_end + 1):
                lookup[p] = {
                    "collection_id": cat["id"],
                    "category": cat["name"],
                    "subcategory": None,
                }
    return lookup


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    with open(INPUT_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    lookup = build_page_lookup(CATEGORY_MAP)

    pages_by_collection = {}

    for table in data["tables"]:
        page = table["page"]
        meta = lookup.get(page)
        if meta is None:
            print(f"WARNING: Page {page} not found in category map — skipping")
            continue

        col_id = meta["collection_id"]
        doc = {
            "_doc_id": f"page_{page:03d}",
            "page": page,
            "category": meta["category"],
            "subcategory": meta["subcategory"],
            "rows": table["rows"],
        }
        pages_by_collection.setdefault(col_id, []).append(doc)

    for col_id, docs in pages_by_collection.items():
        docs.sort(key=lambda d: d["page"])
        out_path = os.path.join(OUTPUT_DIR, f"{col_id}.ndjson")
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
                        ("sections", [
                            OrderedDict([
                                ("name", sec["name"]),
                                ("page_start", sec["pages"][0]),
                                ("page_end", sec["pages"][1]),
                                ("page_count", sec["pages"][1] - sec["pages"][0] + 1),
                            ]) for sec in cat.get("sections", [])
                        ] or None),
                    ]) for cat in CATEGORY_MAP
                ],
            },
            f, indent=2, ensure_ascii=False,
        )
    print(f"Wrote category map → {cat_map_path}")
    print("Done.")


if __name__ == "__main__":
    main()
