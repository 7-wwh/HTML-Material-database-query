#!/usr/bin/env python3
"""
convert_to_firestore.py

Reads YH_HandBook.json (262 parsed tables) and Json_formatting.json (Firestore schema),
maps each table to the correct Firestore collection, transforms data, and outputs
YH_HandBook_firestore.json.

Usage:
    python3 convert_to_firestore.py
"""

import json
import re
import os
import sys
from collections import OrderedDict

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

INPUT_TABLES = os.path.join(SCRIPT_DIR, "YH_HandBook.json")
INPUT_SCHEMA = os.path.join(SCRIPT_DIR, "Json_formatting.json")
OUTPUT_PATH = os.path.join(SCRIPT_DIR, "YH_HandBook_firestore.json")

# ── Section → Collection Mapping ──────────────────────────────────────────
# Maps every known section path to a Firestore collection name.
SECTION_MAP = {
    # Metadata / Company Info
    "STRUCTURAL  STEEL / CONTENTS": "metadata",

    # Reference tables (engineering data, conversion, specs comparisons)
    "COMPARABLE SPECIFICATIONS AND CHEMICAL ANALYSIS": "reference_tables",
    "AVAILABLE SPECIFICATIONS": "reference_tables",
    "COMPARISON OF EN10025 & BS4360": "reference_tables",
    "EXPLANATORY NOTES": "reference_tables",
    "OFFSHORE	PLATFORM,	F.P.S.O.,	BRIDGE	GIRDERS,	STRUCTURAL	TUBULARS	&	FABRICATIONS.	LOW TEMP CHARPY TESTED, + M = T.M.C.P QUALITY": "reference_tables",
    "PRODUCTS STOCK SIZES": "reference_tables",
    "DESIGN OF BEAMS / Design formulae for beams": "reference_tables",
    "DESIGN OF BEAMS / RA = RB": "reference_tables",
    "RA	= W	RA	= W / C	(L+ )	C": "reference_tables",
    "GEOMETRICAL PROPERTIES OF SECTIONS": "reference_tables",
    "STRESS AND DEFLECTION OF BEAMS": "reference_tables",
    "WORKING STRESSES": "reference_tables",
    "BEAMS WITHOUT LATERAL SUPPORT": "reference_tables",
    "DESIGN OF STANCHIONS AND STRUTS / I-BEAMS": "reference_tables",
    "COMPARATIVE TABLES OF STEEL QUALITIES": "reference_tables",
    "DIMENSIONAL TOLERANCES": "reference_tables",
    "LENGTH TOLERANCE": "reference_tables",
    "CHEMICAL COMPOSITION AND MECHANICAL PROPERTIES": "reference_tables",
    "CONVERSION FACTORS": "reference_tables",
    "CONVERSION FACTORS / GAUGE TABLE": "reference_tables",
    "WEIGHT PER UNIT VOLUME": "reference_tables",
    "TABLE OF UNIT WEIGHT": "reference_tables",
    "IMPERIAL UNITS: APPROX. WT. LBS/FT": "reference_tables",
    "METRIC UNITS: APPROX. WT. KG/M": "reference_tables",
    "METRIC UNIT: APPROX. WT. KG/M": "reference_tables",
    "METRIC UNIT: APPROX. WT. KG/M / ROUND BARS": "reference_tables",
    "STOCK SIZES & WEIGHTS": "reference_tables",

    # Structural Beams
    "STRESS AND SAFE LOAD TABLES": "structural_beams",
    "SAFE LOADS FOR GRADE 43 STEEL": "structural_beams",
    "Y	UNIVERSAL BEAMS / AND COLUMNS": "structural_beams",
    "Y	LIGHT BEAMS / AND JOISTS": "structural_beams",

    # Piles
    "BEARING PILES": "piles",
    "RECOMMENDED WORKING STRESSES FOR STEEL SHEET PILING": "piles",
    "RECOMMENDED MAXIMUM LENGTHS FOR DRIVING": "piles",
    "INTERLOCKING SECTIONS": "piles",
    "CIRCULAR CONSTRUCTION": "piles",
    "EFFECTIVE LIFE": "piles",
    "KSP DIMENSIONS & PROPERTIES": "piles",
    "KSP DIMENSIONS & PROPERTIES / U-TYPE": "piles",
    "KSP DIMENSIONS & PROPERTIES / Z-TYPE": "piles",
    "STRAIGHT WEB-TYPE": "piles",

    # Pipes
    "API MECHANICAL & CHEMICAL SPECIFICATION": "pipes",
    "CHEMICAL REQUIREMENTS FOR LADLE ANALYSES, %": "pipes",
    "TECHNICAL SPECIFICATION REFERENCE -STEEL PIPES": "pipes",
    "TECHNICAL SPECIFICATION REFERENCE -STEEL TUBES": "pipes",
    "TECHNICAL SPECIFICATION REFERENCE -STEEL TUBES AND LIPPED CHANNEL": "pipes",
    "BRITISH STANDARD WELDED STEEL PIPES": "pipes",
    "EARTH PIPE - MANUFACTURER STANDARD": "pipes",
    "CARBON STEEL PIPES FOR SCAFFOLDING": "pipes",
    "CARBON STEEL PIPES FOR ORDINARY PIPING": "pipes",
    "CARBON STEEL PIPES FOR MACHINE STRUCTURAL PURPOSES": "pipes",
    "CARBON STEEL PIPES FOR GENERAL STRUCTURAL PURPOSES": "pipes",

    # Hollow Sections
    "STANDARD SPECIFICATIONS FOR WELDED CIRCULAR & NON-CIRCULAR STEEL TUBES": "hollow_sections",
    "STANDARD SPECIFICATIONS FOR WELDED CIRCULAR & NON-CIRCULAR STEEL TUBES / SQUARE": "hollow_sections",
    "STANDARD SPECIFICATIONS FOR WELDED CIRCULAR & NON-CIRCULAR STEEL TUBES / RECTANGULAR": "hollow_sections",
    "COMPARABLE SPECIFICATIONS": "hollow_sections",
    "COMPARABLE SPECIFICATIONS / SQUARE": "hollow_sections",
    "COMPARABLE SPECIFICATIONS / RECTANGULAR": "hollow_sections",
    "HOT FORMED HOLLOW SECTIONS / CIRCULAR": "hollow_sections",
    "STAINLESS STEEL WELDED TUBINGS": "hollow_sections",
    "STAINLESS STEEL WELDED TUBINGS / TOLERANCES": "hollow_sections",
    "STAINLESS STEEL WELDED TUBINGS / FITTINGS": "hollow_sections",
    "WELDED STAINLESS STEEL TUBING MECHANICAL PROPERTIES": "hollow_sections",

    # Channels
    "PLAIN CHANNELS": "channels",
    "PLAIN CHANNELS / CHANNELS": "channels",
    "PLAIN CHANNELS / INCH SERIES": "channels",
    "WELDED CHANNELS": "channels",

    # Purlins
    "HIGH-TENSILE GALVANISED Z-PURLINS": "purlins",
    "HIGH-TENSILE GALVANISED Z-PURLINS / Z-PURLINS": "purlins",
    "MATERIAL SPECIFICATION": "purlins",
    "TABLE NO. 1 - PURLIN DIMENSIONS AND PROPERTIES": "purlins",
    "TABLE NO. 2 - PURLIN SELECTION TABLE": "purlins",
    "TABLE NO. 2 - PURLIN SELECTION TABLE / INVERTED ANGLES": "purlins",
    "TABLE NO. 2 - PURLIN SELECTION TABLE / UNEQUAL": "purlins",

    # Angles
    "INVERTED ANGLES": "angles",

    # Bars
    "MILD STEEL TEE BARS - WEIGHT TABLE": "bars",
    "MILD STEEL TEE BARS - WEIGHT TABLE / DEFORMED AND ROUND BARS": "bars",
    "MILD STEEL TEE BARS - WEIGHT TABLE / BULB FLATS": "bars",
    "MILD STEEL TEE BARS - WEIGHT TABLE / SQUARE": "bars",
    "ROUND BARS, HEXAGON BARS & SQUARE BARS": "bars",
    "ROUND BARS, HEXAGON BARS & SQUARE BARS / FLAT BARS": "bars",
    "ROUND BARS, HEXAGON BARS & SQUARE BARS / SHEETS": "bars",
    "COLD FINISHED / STEEL BAR": "bars",
    "CARBON STEEL KS D3752, JIS G4051": "bars",
    "ALLOY STEEL KS D3707 D3711, JIS G4104 G4105": "bars",
    "ALLOY STEEL KS D3708 D3709, JIS G4102 G4103": "bars",

    # Plates
    "PLATES-SPECIFICATIONS": "plates",
    "SPECIFICATIONS": "plates",
    "SPECIFICATION": "plates",
    "TECHNICAL SPECIFICATION REFERENCE - STEEL PLATES, SHEETS": "plates",
    "CHEQUERED (FLOOR) PLATES / WEIGHT TABLE": "plates",
    "COLD ROLLED COILS AND SHEETS - SPECIFICATIONS": "plates",
    "GENERAL COLD ROLLED STEELS": "plates",
    "DIMENSIONS AND WEIGHTS": "plates",
    "ELECTROLYTIC GALVANISED COILS AND SHEETS -SPECIFICATIONS": "plates",
    "GALVANISED STEEL SHEETS": "plates",

    # Misc Products (gratings)
    "GRATINGS LOADING TABLE \u201c4/1\u201c SERIES": "misc_products",
    "QUICK SELECTION TABLE FOR WALKWAYS": "misc_products",

    # Flanges
    "SPECIFICATIONS / SLIP-ON FLANGES (BS 10)": "flanges",
    "WELDING NECK FLANGES": "flanges",
    "WELDING NECK FLANGES / TABLE A": "flanges",
    "WELDING NECK FLANGES / TABLE E": "flanges",
    "WELDING NECK FLANGES / TABLE H": "flanges",
    "WELDING NECK FLANGES / TABLE J": "flanges",
    "WELDING NECK FLANGES / TABLE K": "flanges",
    "WELDING NECK FLANGES / TABLE S": "flanges",

    # Pipe Fittings
    "REDUCERS\tANSI B 16.9": "pipe_fittings",
    "TEES\tANSI B 16.9": "pipe_fittings",
    "REDUCING\tANSI B 16.9": "pipe_fittings",

    # Stainless Steel Corrosion / Mechanical Properties
    "SPECIFICATIONS: MECHANICAL PROPERTIES OF STAINLESS STEEL SHEETS": "reference_tables",
    "SPECIFICATIONS: MECHANICAL PROPERTIES OF STAINLESS STEEL SHEETS / MAIN USES": "reference_tables",
    "SPECIFICATIONS: MECHANICAL PROPERTIES OF STAINLESS STEEL SHEETS / FINISHES": "reference_tables",
    "CHEMICAL COMPOSITION\tAISI, ASTM A276-78": "stainless_corrosion_resistance",
    "TYPICAL CHARACTERISTICS FOR CHEMICAL COMPOSITION": "stainless_corrosion_resistance",
    "MECHANICAL PROPERTIES ASTM A276-78": "stainless_corrosion_resistance",
    "MECHANICAL PROPERTIES OF AISI 304 BUTT WELDED JOINT": "stainless_corrosion_resistance",
}

# ── Collection → Schema Reference ─────────────────────────────────────────
# Maps each collection to the fields defined in Json_formatting.json.
# We load the schema to validate field names.
COLLECTION_FIELDS = {}  # populated from schema

def load_schema(schema_path):
    with open(schema_path, "r", encoding="utf-8") as f:
        return json.load(f)

def extract_fields_from_schema(schema, collection_name):
    """Extract the flat field paths for a given collection from the schema."""
    collections = schema.get("collections", {})
    if collection_name not in collections:
        return None
    col_def = collections[collection_name]
    doc = col_def.get("_document", {})
    # Extract handbook_page and meta
    meta_page = None
    meta = doc.get("_meta", {})
    if "handbook_page" in meta:
        meta_page = meta["handbook_page"]

    fields = {}
    for key, val in doc.items():
        if key.startswith("_"):
            continue
        if isinstance(val, dict) and "type" in val:
            # Simple field
            fields[key] = {"type": val["type"], "example": val.get("example")}
        elif isinstance(val, dict) and "type" not in val:
            # Nested object like "dimensions", "section_properties"
            for subkey, subval in val.items():
                if subkey.startswith("_"):
                    continue
                if isinstance(subval, dict) and "type" in subval:
                    fields[f"{key}.{subkey}"] = {
                        "type": subval["type"],
                        "example": subval.get("example"),
                        "description": subval.get("description"),
                    }
    return {"meta_page": meta_page, "fields": fields}

# ── Helper Functions ──────────────────────────────────────────────────────

def title_to_id(title):
    """Convert a display title to a document ID."""
    s = str(title).strip().lower()
    s = re.sub(r'[^a-z0-9]+', '-', s)
    s = s.strip('-')
    return s

def parse_number(val):
    """Try to parse a number from a string. Return None if not possible."""
    if isinstance(val, (int, float)):
        return float(val)
    val = str(val).strip().replace(',', '')
    if not val or val in ('-', '--', '—', '–', ''):
        return None
    try:
        return float(val)
    except ValueError:
        # Handle ranges like "430/580" - take the first number
        m = re.match(r'^([\d.]+)', val)
        if m:
            try:
                return float(m.group(1))
            except ValueError:
                return None
        return None

def parse_number_or_keep(val):
    """Parse to float if possible, otherwise return string."""
    n = parse_number(val)
    return n if n is not None else val

def is_numeric(val):
    return parse_number(val) is not None

def split_compound(val):
    """Split compound values like '1.44 2.03' into array."""
    if not val or val in ('-', '--', '—', '–', ''):
        return []
    parts = str(val).strip().split()
    result = []
    for p in parts:
        n = parse_number(p)
        if n is not None:
            result.append(n)
        else:
            result.append(p)
    return result

def detect_unit(header_text):
    """Detect unit from header text. Returns ('field', 'unit_suffix', is_imperial)."""
    h = header_text.lower()
    if 'in4' in h or 'in⁴' in h:
        return (None, '_in4', True)
    if 'cm4' in h or 'cm⁴' in h:
        return (None, '_cm4', False)
    if 'in3' in h or 'in³' in h:
        return (None, '_in3', True)
    if 'cm3' in h or 'cm³' in h:
        return (None, '_cm3', False)
    if 'in' in h and ('/' not in h or '/in' in h):
        return (None, '_in', True)
    if 'mm' in h:
        return (None, '_mm', False)
    if 'cm2' in h or 'cm²' in h:
        return (None, '_cm2', False)
    if 'in2' in h or 'in²' in h:
        return (None, '_in2', True)
    if 'lb/ft' in h or 'lb/' in h or 'lbs/ft' in h:
        return (None, '_lb_ft', True)
    if 'kg/m' in h:
        return (None, '_kg_m', False)
    if 'n/mm2' in h or 'mpa' in h:
        return (None, '_mpa', False)
    return (None, '', False)

def extract_section_label(row_data):
    """Extract a section label from the first column value."""
    for key in list(row_data.keys()):
        val = row_data.get(key, '')
        if val and val not in ('-', '--', '—'):
            return val
    return ""


def is_header_row(row_data, headers):
    """Check if a row is actually a header/unit row rather than data."""
    first_key = list(row_data.keys())[0] if row_data else ""
    first_val = str(list(row_data.values())[0]).strip() if row_data else ""

    if not first_val or first_val in ("-", "--", "\u2014", "\u2013", ""):
        return True

    header_keywords = ['quality', 'grade', 'designation', 'section size', 'unit weight',
                       'section', 'standard', 'specification', 'application', 'size',
                       'nominal', 'thickness', 'width', 'length', 'weight', 'dia',
                       'outside', 'inside', 'tensile', 'yield', 'elongation',
                       'condition', 'finish', 'type', 'shape', 'formation',
                       'material', 'product', 'model', 'classification',
                       'composition', 'mechanical', 'chemical', 'test',
                       'scope', 'marking', 'surface', 'heat', 'treatment']

    first_lower = first_val.lower().strip()
    for kw in header_keywords:
        if first_lower == kw or first_lower.startswith(kw + " ") or first_lower.startswith(kw + "/"):
            return True

    # Check if first value looks like a unit indicator
    unit_patterns = [
        r"^in\\b", r"^mm\\b", r"^cm\\b", r"^kg/", r"^lb/", r"^in\\d", r"^cm\\d",
        r"^n/mm", r"^mpa", r"^kn",
    ]
    for pat in unit_patterns:
        if re.search(pat, first_lower):
            return True

    # Common unit-only values
    unit_values = {
        "mm", "in", "cm", "kg/m", "lb/ft", "in4", "in3", "cm4", "cm3",
        "n/mm2", "mpa", "kn", "kg", "lb", "ft", "m", "cm2", "in2", "kg/ft",
        "in (mm)", "mm (in)", "ib/in2", "kg/mm2",
        "in2 (cm2)", "cm2 (in2)", "in4 (cm4)", "in3 (cm3)",
        "yes", "no", "min", "max", "in (cm)", "kg/m2",
        "-", "--", "\u2014", "\u2013", "", " ",
    }

    check_first = first_val.lower().strip()
    if check_first in unit_values:
        return True

    # Check if ALL values look like units or column labels
    all_units = True
    for k, v in list(row_data.items()):
        vs = str(v).strip().lower()
        if not vs:
            continue
        if vs not in unit_values:
            # If it is just a number it could be real data (not a unit row)
            if not re.match(r"^[\\d.,\\s/\\-]+$", vs):
                all_units = False
                break
    if all_units and len(row_data) >= 2:
        return True

    return False

def generate_keywords(row_data, section_label_val):
    """Generate keywords array for Firestore search."""
    keywords = set()
    if section_label_val:
        keywords.add(section_label_val.lower())
    for key, val in row_data.items():
        if val and isinstance(val, str) and len(val) < 50:
            keywords.add(val.lower())
        elif val and isinstance(val, (int, float)):
            keywords.add(str(val))
    sorted_kw = sorted(keywords - {''})
    return sorted_kw[:50]  # limit

# ── Structural Beams Parser ───────────────────────────────────────────────

STRUCTURAL_BEAM_HEADER_MAP = [
    (r'(section\s*size|designation|serial\s*size)', 'section_label'),
    (r'mass\s*per\s*metre|weight\s*(kg/m|per\s*m)|unit\s*weight', 'mass_per_metre_kg'),
    (r'depth|height.*mm|d\b(?!\s*(in|lb))', 'dimensions.depth_mm'),
    (r'width|breadth.*mm|b\b(?!\s*(in|lb))', 'dimensions.width_mm'),
    (r'flange.*thick|t\b.*(?!w)', 'dimensions.flange_thickness_mm'),
    (r'web.*thick|t\b.*w', 'dimensions.web_thickness_mm'),
    (r'corner.*radius|root.*radius', 'dimensions.corner_radius_mm'),
    (r'section.*area|area\s*of\s*sect', 'dimensions.section_area_cm2'),
    (r'Ix|moment.*inertia.*x|ix\b(?!\s*(y|z))', 'section_properties.Ix_cm4'),
    (r'Iy|moment.*inertia.*y|iy\b', 'section_properties.Iy_cm4'),
    (r'Zx|modulus.*section.*x|zx\b', 'section_properties.Zx_cm3'),
    (r'Zy|modulus.*section.*y|zy\b', 'section_properties.Zy_cm3'),
    (r'radius.*gyration.*x|ix\b(?!\s*(y|z))', 'section_properties.ix_cm'),
    (r'radius.*gyration.*y|iy\b', 'section_properties.iy_cm'),
]

def parse_structural_beam_row(row_data, table_info):
    """Parse a single structural beam data row into a Firestore document."""
    doc = OrderedDict()
    doc["section_label"] = ""
    doc["mass_per_metre_kg"] = None

    for raw_key, val in row_data.items():
        if val in ('-', '--', '—', '–', ''):
            continue
        key_lower = raw_key.lower()
        nval = parse_number(val)

        # Section size / designation
        if any(kw in key_lower for kw in ['section size', 'designation', 'serial size']):
            doc["section_label"] = val
            doc["display_name"] = val
            continue

        # Mass per metre
        if any(kw in key_lower for kw in ['unit weight', 'mass per', 'weight']) and nval is not None:
            if 'lb' in key_lower or 'ft' in key_lower:
                pass  # skip imperial
            else:
                doc["mass_per_metre_kg"] = nval
            continue

        # Depth
        if any(kw in key_lower for kw in ['depth', 'height', ' d ']) and 'section' not in key_lower:
            unit, suffix, imperial = detect_unit(key_lower)
            if imperial:
                doc["dimensions.depth_in"] = nval
            elif suffix == '_mm':
                doc["dimensions.depth_mm"] = nval
            continue

        # Width
        if any(kw in key_lower for kw in ['width', 'breadth', 'flange width']):
            unit, suffix, imperial = detect_unit(key_lower)
            if imperial:
                doc["dimensions.width_in"] = nval
            elif suffix == '_mm':
                doc["dimensions.width_mm"] = nval
            continue

        # Flange thickness
        if any(kw in key_lower for kw in ['flange thick', ' t ']) and 'web' not in key_lower:
            unit, suffix, imperial = detect_unit(key_lower)
            if imperial:
                doc["dimensions.flange_thickness_in"] = nval
            elif suffix == '_mm':
                doc["dimensions.flange_thickness_mm"] = nval
            continue

        # Web thickness
        if any(kw in key_lower for kw in ['web thick', ' w ']):
            doc["dimensions.web_thickness_mm"] = nval
            continue

        # Section area
        if 'area' in key_lower and 'section' in key_lower and 'load' not in key_lower:
            doc["dimensions.section_area_cm2"] = nval
            continue

        # Moment of inertia
        if 'ix' in key_lower or ('inertia' in key_lower and 'x' in key_lower):
            unit, suffix, imperial = detect_unit(key_lower)
            if 'in4' in key_lower or imperial:
                doc["section_properties.Ix_in4"] = nval
            else:
                doc["section_properties.Ix_cm4"] = nval
            continue
        if 'iy' in key_lower or ('inertia' in key_lower and 'y' in key_lower):
            unit, suffix, imperial = detect_unit(key_lower)
            if 'in4' in key_lower or imperial:
                doc["section_properties.Iy_in4"] = nval
            else:
                doc["section_properties.Iy_cm4"] = nval
            continue

        # Radius of gyration
        if 'ix' in key_lower and ('radius' in key_lower or 'gyration' in key_lower):
            doc["section_properties.ix_cm"] = nval
            continue
        if 'iy' in key_lower and ('radius' in key_lower or 'gyration' in key_lower):
            doc["section_properties.iy_cm"] = nval
            continue

        # Section modulus
        if 'zx' in key_lower or ('modulus' in key_lower and 'x' in key_lower):
            unit, suffix, imperial = detect_unit(key_lower)
            if 'in3' in key_lower or imperial:
                doc["section_properties.Zx_in3"] = nval
            else:
                doc["section_properties.Zx_cm3"] = nval
            continue
        if 'zy' in key_lower or ('modulus' in key_lower and 'y' in key_lower):
            unit, suffix, imperial = detect_unit(key_lower)
            if 'in3' in key_lower or imperial:
                doc["section_properties.Zy_in3"] = nval
            else:
                doc["section_properties.Zy_cm3"] = nval
            continue

        # Miscellaneous
        doc[f"raw_{raw_key}"] = nval if nval is not None else val

    return doc

# ── Piles Parser ──────────────────────────────────────────────────────────

def parse_pile_row(row_data, table_info):
    """Parse a bearing pile row."""
    doc = OrderedDict()
    doc["section_label"] = ""
    doc["mass_per_metre_kg"] = None

    for raw_key, val in row_data.items():
        if val in ('-', '--', '—', '–', ''):
            continue
        key_lower = raw_key.lower()
        nval = parse_number(val)

        if any(kw in key_lower for kw in ['section size', 'designation']):
            doc["section_label"] = val
            continue

        if any(kw in key_lower for kw in ['unit weight', 'weight', 'mass']):
            if 'kg' in key_lower or 'kg/m' in key_lower:
                doc["mass_per_metre_kg"] = nval
            continue

        if 'depth' in key_lower or 'd ' in key_lower.split():
            unit, suffix, imperial = detect_unit(key_lower)
            if imperial:
                doc["dimensions.depth_in"] = nval
            else:
                doc["dimensions.depth_mm"] = nval
            continue

        if 'width' in key_lower or 'flange' in key_lower:
            unit, suffix, imperial = detect_unit(key_lower)
            if imperial:
                doc["dimensions.width_in"] = nval
            else:
                doc["dimensions.width_mm"] = nval
            continue

        if 'thick' in key_lower:
            doc["dimensions.flange_and_web_thickness_mm"] = nval
            continue

        if 'area' in key_lower:
            doc["dimensions.section_area_cm2"] = nval
            continue

        doc[f"raw_{raw_key}"] = nval if nval is not None else val

    return doc

# ── Hollow Sections Parser ────────────────────────────────────────────────

def parse_hollow_section_row(row_data, table_info):
    """Parse a hollow section (SHS/RHS/CHS) row."""
    doc = OrderedDict()
    doc["size_label"] = ""
    doc["mass_per_metre_kg"] = None

    section_name = (table_info.get("section") or "").lower()

    if "circular" in section_name or "chs" in section_name:
        doc["shape"] = "CHS"
    elif "square" in section_name:
        doc["shape"] = "SHS"
    elif "rectangular" in section_name:
        doc["shape"] = "RHS"
    else:
        doc["shape"] = "SHS"

    if "cold" in section_name or "cf" in section_name:
        doc["formation"] = "COLD_FORMED"
    else:
        doc["formation"] = "HOT_FORMED"

    for raw_key, val in row_data.items():
        if val in ('-', '--', '—', '–', ''):
            continue
        key_lower = raw_key.lower()
        nval = parse_number(val)

        if any(kw in key_lower for kw in ['size', 'designation', 'section']):
            doc["size_label"] = val
            continue

        if any(kw in key_lower for kw in ['mass', 'weight', 'kg/m']):
            doc["mass_per_metre_kg"] = nval
            continue

        if any(kw in key_lower for kw in ['width', 'diameter', 'od', 'a ']) and 'thick' not in key_lower:
            doc["dimensions.width_mm"] = nval
            continue

        if 'height' in key_lower or 'b ' in key_lower.split():
            doc["dimensions.height_mm"] = nval
            continue

        if any(kw in key_lower for kw in ['thick', 'wall', ' t ']):
            doc["dimensions.wall_thickness_mm"] = nval
            continue

        if 'radius' in key_lower or 'corner' in key_lower:
            doc["dimensions.corner_radius_mm"] = nval
            continue

        if 'area' in key_lower:
            doc["dimensions.section_area_cm2"] = nval
            continue

        if 'ix' in key_lower or ('inertia' in key_lower and 'x' in key_lower):
            doc["section_properties.Ix_cm4"] = nval
            continue
        if 'iy' in key_lower or ('inertia' in key_lower and 'y' in key_lower):
            doc["section_properties.Iy_cm4"] = nval
            continue
        if 'ix' in key_lower and ('radius' in key_lower or 'gyration' in key_lower):
            doc["section_properties.ix_cm"] = nval
            continue
        if 'iy' in key_lower and ('radius' in key_lower or 'gyration' in key_lower):
            doc["section_properties.iy_cm"] = nval
            continue
        if 'zx' in key_lower or ('modulus' in key_lower and 'x' in key_lower):
            doc["section_properties.Zx_cm3"] = nval
            continue
        if 'zy' in key_lower or ('modulus' in key_lower and 'y' in key_lower):
            doc["section_properties.Zy_cm3"] = nval
            continue

        doc[f"raw_{raw_key}"] = nval if nval is not None else val

    return doc

# ── Pipes Parser ──────────────────────────────────────────────────────────

def parse_pipe_row(row_data, table_info):
    """Parse a pipe row."""
    doc = OrderedDict()
    doc["nominal_bore_inch"] = ""
    doc["outside_diameter_mm"] = None
    doc["wall_thickness_mm"] = None
    doc["mass_per_metre_kg"] = None

    for raw_key, val in row_data.items():
        if val in ('-', '--', '—', '–', ''):
            continue
        key_lower = raw_key.lower()
        nval = parse_number(val)

        if any(kw in key_lower for kw in ['nominal', 'nb', 'size', 'bore']):
            doc["nominal_bore_inch"] = val
            n = parse_number(val)
            if n is not None:
                doc["nominal_bore_mm"] = n * 25.4 if n < 50 else n
            continue

        if any(kw in key_lower for kw in ['outside diameter', 'od', 'outer']):
            doc["outside_diameter_mm"] = nval
            continue

        if any(kw in key_lower for kw in ['thick', 'wall']):
            doc["wall_thickness_mm"] = nval
            if nval is not None:
                doc["inside_diameter_mm"] = round((doc.get("outside_diameter_mm", 0) or 0) - 2 * nval, 2)
            continue

        if any(kw in key_lower for kw in ['weight', 'mass', 'kg/m']):
            doc["mass_per_metre_kg"] = nval
            continue

        if 'area' in key_lower:
            doc["section_area_cm2"] = nval
            continue

        if 'ix' in key_lower or ('inertia' in key_lower and 'x' in key_lower):
            doc["Ix_cm4"] = nval
            continue
        if 'zx' in key_lower or ('modulus' in key_lower and 'x' in key_lower):
            doc["Zx_cm3"] = nval
            continue

        if 'schedule' in key_lower or 'sch' in key_lower:
            doc["schedule"] = val
            continue

        if 'grade' in key_lower:
            doc["grade"] = val
            continue

        doc[f"raw_{raw_key}"] = nval if nval is not None else val

    return doc

# ── Channels Parser ───────────────────────────────────────────────────────

def parse_channel_row(row_data, table_info):
    """Parse a channel row."""
    doc = OrderedDict()
    doc["size_label"] = ""
    doc["mass_per_metre_kg"] = None

    for raw_key, val in row_data.items():
        if val in ('-', '--', '—', '–', ''):
            continue
        key_lower = raw_key.lower()
        nval = parse_number(val)

        if any(kw in key_lower for kw in ['size', 'section', 'designation']):
            doc["size_label"] = val
            continue

        if any(kw in key_lower for kw in ['weight', 'mass', 'kg/m']):
            doc["mass_per_metre_kg"] = nval
            continue

        if 'thick' in key_lower:
            doc["thickness_mm"] = nval
            continue

        if any(kw in key_lower for kw in ['height', 'depth', 'a x']):
            doc["dimensions.height_mm"] = nval
            continue

        if 'width' in key_lower or 'b x' in key_lower:
            doc["dimensions.width_mm"] = nval
            continue

        if 'area' in key_lower:
            doc["dimensions.section_area_cm2"] = nval
            continue

        if 'ix' in key_lower or ('inertia' in key_lower and 'x' in key_lower):
            doc["section_properties.Ix_cm4"] = nval
            continue
        if 'iy' in key_lower or ('inertia' in key_lower and 'y' in key_lower):
            doc["section_properties.Iy_cm4"] = nval
            continue
        if any(kw in key_lower for kw in ['rx', 'ix radius', 'radius x', 'gyration.*x']):
            doc["section_properties.ix_cm"] = nval
            continue
        if any(kw in key_lower for kw in ['ry', 'iy radius', 'radius y', 'gyration.*y']):
            doc["section_properties.iy_cm"] = nval
            continue
        if 'zx' in key_lower or ('modulus' in key_lower and 'x' in key_lower):
            doc["section_properties.Zx_cm3"] = nval
            continue
        if 'zy' in key_lower or ('modulus' in key_lower and 'y' in key_lower):
            doc["section_properties.Zy_cm3"] = nval
            continue

        doc[f"raw_{raw_key}"] = nval if nval is not None else val

    return doc

# ── Angles Parser ─────────────────────────────────────────────────────────

def parse_angle_row(row_data, table_info):
    """Parse an angle row."""
    doc = OrderedDict()
    doc["size_label"] = ""
    doc["mass_per_metre_kg"] = None

    for raw_key, val in row_data.items():
        if val in ('-', '--', '—', '–', ''):
            continue
        key_lower = raw_key.lower()
        nval = parse_number(val)

        if any(kw in key_lower for kw in ['size', 'section', 'designation', 'angle']):
            doc["size_label"] = val
            continue

        if any(kw in key_lower for kw in ['weight', 'mass', 'kg/m']):
            doc["mass_per_metre_kg"] = nval
            continue

        if 'thick' in key_lower:
            doc["thickness_mm"] = nval
            continue

        if 'area' in key_lower:
            doc["section_area_cm2"] = nval
            continue

        if 'ix' in key_lower or ('inertia' in key_lower and 'x' in key_lower):
            doc["section_properties.Ix_cm4"] = nval
            continue
        if 'iy' in key_lower or ('inertia' in key_lower and 'y' in key_lower):
            doc["section_properties.Iy_cm4"] = nval
            continue

        doc[f"raw_{raw_key}"] = nval if nval is not None else val

    return doc

# ── Bars Parser ───────────────────────────────────────────────────────────

def parse_bar_row(row_data, table_info):
    """Parse a bar (round, flat, square, hex) row."""
    doc = OrderedDict()
    doc["size_label"] = ""
    doc["mass_per_metre_kg"] = None

    for raw_key, val in row_data.items():
        if val in ('-', '--', '—', '–', ''):
            continue
        key_lower = raw_key.lower()
        nval = parse_number(val)

        if any(kw in key_lower for kw in ['size', 'diameter', 'dia', 'side', 'width', 'thick', 'thk']):
            doc["size_label"] = val
            if nval is not None:
                if 'dia' in key_lower or 'diameter' in key_lower:
                    doc["dimensions.diameter_mm"] = nval
                elif 'side' in key_lower:
                    doc["dimensions.side_mm"] = nval
                elif 'width' in key_lower:
                    doc["dimensions.width_mm"] = nval
                elif 'thick' in key_lower:
                    doc["dimensions.thickness_mm"] = nval
            continue

        if any(kw in key_lower for kw in ['weight', 'mass', 'kg/m', 'lb']):
            doc["mass_per_metre_kg"] = nval
            continue

        doc[f"raw_{raw_key}"] = nval if nval is not None else val

    return doc

# ── Flanges Parser ────────────────────────────────────────────────────────

def parse_flange_row(row_data, table_info):
    """Parse a flange row."""
    doc = OrderedDict()
    doc["nominal_bore_inch"] = ""

    for raw_key, val in row_data.items():
        if val in ('-', '--', '—', '–', ''):
            continue
        key_lower = raw_key.lower()
        nval = parse_number(val)

        if any(kw in key_lower for kw in ['nominal', 'nb', 'size', 'pipe size']):
            doc["nominal_bore_inch"] = val
            n = parse_number(val)
            if n is not None:
                doc["nominal_bore_mm"] = n * 25.4 if n < 50 else n
            continue

        if 'outside diameter' in key_lower or 'od' in key_lower:
            doc["od_mm"] = nval
            continue

        if 'inside diameter' in key_lower or 'id' in key_lower:
            continue  # skip ID for flanges

        if 'thick' in key_lower:
            doc["thickness_mm"] = nval
            continue

        if 'bolt' in key_lower and 'circle' in key_lower:
            doc["bolt_circle_dia_mm"] = nval
            continue

        if 'bolt' in key_lower and 'hole' in key_lower:
            doc["bolt_hole_dia_mm"] = nval
            continue

        if 'bolt' in key_lower and 'no' in key_lower:
            doc["no_of_bolts"] = nval
            continue

        if 'weight' in key_lower:
            doc["weight_kg"] = nval
            continue

        if 'wall' in key_lower or 'thick' in key_lower:
            doc["wall_thickness_mm"] = nval
            continue

        doc[f"raw_{raw_key}"] = nval if nval is not None else val

    return doc

# ── Pipe Fittings Parser ──────────────────────────────────────────────────

def parse_pipe_fitting_row(row_data, table_info):
    """Parse a pipe fitting row."""
    doc = OrderedDict()
    doc["nominal_bore_inch"] = ""

    for raw_key, val in row_data.items():
        if val in ('-', '--', '—', '–', ''):
            continue
        key_lower = raw_key.lower()
        nval = parse_number(val)

        if any(kw in key_lower for kw in ['nominal', 'nb', 'size', 'pipe size']):
            doc["nominal_bore_inch"] = val
            n = parse_number(val)
            if n is not None:
                doc["nominal_bore_mm"] = n * 25.4 if n < 50 else n
            continue

        if 'thick' in key_lower:
            doc["wall_thickness_mm"] = nval
            continue

        if 'weight' in key_lower:
            doc["weight_kg"] = nval
            continue

        if any(kw in key_lower for kw in ['centre', 'center', 'face']) and 'to' in key_lower:
            doc["center_to_end_mm"] = nval
            continue

        if 'outside' in key_lower or 'od' in key_lower:
            doc["outside_diameter_mm"] = nval
            continue

        if 'length' in key_lower:
            doc["length_mm"] = nval
            continue

        doc[f"raw_{raw_key}"] = nval if nval is not None else val

    return doc

# ── Plates Parser ─────────────────────────────────────────────────────────

def parse_plate_row(row_data, table_info):
    """Parse a plate row."""
    doc = OrderedDict()
    doc["thickness_mm"] = None
    doc["width_mm"] = None

    for raw_key, val in row_data.items():
        if val in ('-', '--', '—', '–', ''):
            continue
        key_lower = raw_key.lower()
        nval = parse_number(val)

        if 'thick' in key_lower:
            doc["thickness_mm"] = nval
            continue

        if 'width' in key_lower:
            doc["width_mm"] = nval
            continue

        if 'length' in key_lower:
            doc["length_mm"] = nval
            continue

        if any(kw in key_lower for kw in ['weight', 'mass', 'kg']):
            doc["weight_kg_m2"] = nval
            continue

        doc[f"raw_{raw_key}"] = nval if nval is not None else val

    return doc

# ── Purlins Parser ────────────────────────────────────────────────────────

def parse_purlin_row(row_data, table_info):
    """Parse a purlin row."""
    doc = OrderedDict()
    doc["size_label"] = ""
    doc["thickness_mm"] = None

    for raw_key, val in row_data.items():
        if val in ('-', '--', '—', '–', ''):
            continue
        key_lower = raw_key.lower()
        nval = parse_number(val)

        if any(kw in key_lower for kw in ['size', 'designation', 'section']):
            doc["size_label"] = val
            continue

        if any(kw in key_lower for kw in ['thick', 'thk', 'gauge']):
            doc["thickness_mm"] = nval
            continue

        if 'height' in key_lower or 'depth' in key_lower:
            doc["dimensions.height_mm"] = nval
            continue

        if 'flange' in key_lower or 'width' in key_lower:
            doc["dimensions.flange_mm"] = nval
            continue

        if 'lip' in key_lower:
            doc["dimensions.lip_mm"] = nval
            continue

        if any(kw in key_lower for kw in ['weight', 'mass', 'kg/m']):
            doc["mass_per_metre_kg"] = nval
            continue

        if 'ix' in key_lower:
            doc["section_properties.Ix_cm4"] = nval
            continue
        if 'iy' in key_lower:
            doc["section_properties.Iy_cm4"] = nval
            continue
        if 'zx' in key_lower:
            doc["section_properties.Zx_cm3"] = nval
            continue
        if 'zy' in key_lower:
            doc["section_properties.Zy_cm3"] = nval
            continue

        doc[f"raw_{raw_key}"] = nval if nval is not None else val

    return doc

# ── Reference Table Parser ────────────────────────────────────────────────

def parse_reference_row(row_data, table_info):
    """Parse a reference table row into a flat document."""
    doc = OrderedDict()
    for raw_key, val in row_data.items():
        if val in ('-', '--', '—', '–', ''):
            continue
        key_lower = raw_key.lower().replace(' ', '_').replace('/', '_')
        nval = parse_number(val)
        doc[key_lower] = nval if nval is not None else val
    return doc

# ── Parser Dispatcher ─────────────────────────────────────────────────────

COLLECTION_PARSERS = {
    "structural_beams": parse_structural_beam_row,
    "piles": parse_pile_row,
    "hollow_sections": parse_hollow_section_row,
    "pipes": parse_pipe_row,
    "channels": parse_channel_row,
    "angles": parse_angle_row,
    "bars": parse_bar_row,
    "flanges": parse_flange_row,
    "pipe_fittings": parse_pipe_fitting_row,
    "plates": parse_plate_row,
    "purlins": parse_purlin_row,
    "reference_tables": parse_reference_row,
    "stainless_corrosion_resistance": parse_reference_row,
    "misc_products": parse_reference_row,
    "non_ferrous": parse_reference_row,
    "metadata": parse_reference_row,
}

def parse_row_for_collection(collection, row_data, table_info):
    parser = COLLECTION_PARSERS.get(collection, parse_reference_row)
    return parser(row_data, table_info)

# ── Main Processing ───────────────────────────────────────────────────────

def main():
    print("=" * 70)
    print("  YH Handbook → Firestore JSON Converter")
    print("=" * 70)

    # Load input data
    print(f"\n[1/4] Loading {INPUT_TABLES}...")
    with open(INPUT_TABLES, "r", encoding="utf-8") as f:
        handbook = json.load(f)

    print(f"[2/4] Loading schema from {INPUT_SCHEMA}...")
    schema = load_schema(INPUT_SCHEMA)

    tables_data = handbook["tables"]
    content = handbook["content"]

    # Build page number lookup from verified PDF-based mapping
    vp_path = os.path.join(SCRIPT_DIR, "verified_page_map.json")
    if os.path.exists(vp_path):
        with open(vp_path, "r", encoding="utf-8") as f:
            verified = json.load(f)
        page_lookup = {int(k): v for k, v in verified.items()}
    else:
        page_lookup = {}
        for item in content:
            if item["type"] == "table":
                page_lookup[item["table_idx"]] = item.get("page_number")

    print(f"     Tables in handbook: {len(tables_data)}")
    print(f"     Content items: {len(content)}")

    # Prepare output structure
    firestore_output = OrderedDict()
    firestore_output["_meta"] = {
        "source": "Yick Hoe Group of Company – Structural Steel Handbook",
        "generated_from": "YH_HandBook.json",
        "schema": "Json_formatting.json",
        "total_tables_processed": 0,
        "total_documents_generated": 0,
        "collections": OrderedDict(),
    }
    firestore_output["data"] = OrderedDict()

    # Initialize all collections from schema
    schema_collections = schema.get("collections", {})
    for col_name in schema_collections:
        firestore_output["data"][col_name] = OrderedDict()
        firestore_output["data"][col_name]["_collection_info"] = {
            "description": schema_collections[col_name].get("_description", ""),
            "tables_included": [],
            "document_count": 0,
            "handbook_page": None,
        }
        meta = schema_collections[col_name].get("_document", {}).get("_meta", {})
        if "handbook_page" in meta:
            firestore_output["data"][col_name]["_collection_info"]["handbook_page"] = meta["handbook_page"]

    # Add metadata collection for non-product tables
    firestore_output["data"]["metadata"] = OrderedDict()
    firestore_output["data"]["metadata"]["_collection_info"] = {
        "description": "Non-product content: TOC, company info, explanatory notes",
        "tables_included": [],
        "document_count": 0,
        "handbook_page": None,
    }

    # ── Process each table ──────────────────────────────────────────────
    processed = 0
    unmapped_tables = []
    empty_tables = []
    total_docs = 0
    tables_per_collection = {}
    skipped_header_rows = 0

    # Sort tables by index for consistent output
    sorted_tids = sorted(tables_data.keys(), key=int)

    for tid_str in sorted_tids:
        tid = int(tid_str)
        table = tables_data[tid_str]
        section = table.get("section", "")
        rows = table.get("rows", [])
        headers = table.get("headers", [])
        page = page_lookup.get(tid)

        # Determine collection
        collection = SECTION_MAP.get(section)
        if collection is None:
            unmapped_tables.append(tid)
            # Try partial match
            for sec_key, col_val in SECTION_MAP.items():
                if section.startswith(sec_key) or sec_key.startswith(section):
                    collection = col_val
                    break

        if collection is None:
            unmapped_tables.append(tid)
            continue

        # Track per-collection
        if collection not in tables_per_collection:
            tables_per_collection[collection] = []
        tables_per_collection[collection].append(tid)

        # Skip empty tables
        if not rows or len(rows) == 0:
            empty_tables.append(tid)
            # Still add an entry in the collection
            if collection in firestore_output["data"]:
                col_data = firestore_output["data"][collection]
                if "_empty_tables" not in col_data:
                    col_data["_empty_tables"] = []
                col_data["_empty_tables"].append({
                    "table_id": tid,
                    "section": section,
                    "page": page,
                    "headers": headers,
                    "note": "Empty table - no data rows"
                })
            processed += 1
            continue

        # Process each data row
        doc_count = 0
        for row_idx, row in rows.items() if isinstance(rows, dict) else enumerate(rows):
            # Skip header/unit rows that slipped through
            if is_header_row(row, headers):
                skipped_header_rows += 1
                continue

            # Parse row into Firestore document
            table_info = {
                "table_id": tid,
                "section": section,
                "headers": headers,
                "page": page,
            }

            parsed = parse_row_for_collection(collection, row, table_info)

            # Add meta block
            doc_id_val = parsed.get("section_label") or parsed.get("size_label") or parsed.get("nominal_bore_inch") or str(row_idx)
            doc_id = title_to_id(str(doc_id_val))

            firestore_doc = OrderedDict()
            firestore_doc["_meta"] = OrderedDict()
            firestore_doc["_meta"]["handbook_page"] = page
            firestore_doc["_meta"]["table_id"] = tid
            firestore_doc["_meta"]["section"] = section
            firestore_doc["_meta"]["row_index"] = row_idx

            # Add all parsed fields
            for key, val in parsed.items():
                if key.startswith("raw_"):
                    # Store raw fields under _raw_data
                    if "_raw_data" not in firestore_doc:
                        firestore_doc["_raw_data"] = OrderedDict()
                    firestore_doc["_raw_data"][key[4:]] = val
                else:
                    firestore_doc[key] = val

            # Generate keywords
            section_label_val = parsed.get("section_label") or parsed.get("size_label") or parsed.get("nominal_bore_inch") or ""
            keywords = generate_keywords(row, section_label_val)
            firestore_doc["keywords"] = keywords

            # Add to collection
            fdata = firestore_output["data"]
            if collection not in fdata:
                fdata[collection] = OrderedDict()
            # Avoid duplicate doc IDs
            unique_id = doc_id
            counter = 1
            while unique_id in fdata.get(collection, {}):
                unique_id = f"{doc_id}-{counter}"
                counter += 1
            if collection not in fdata:
                fdata[collection] = OrderedDict()
            fdata[collection][unique_id] = firestore_doc

            doc_count += 1

        if collection in firestore_output["data"]:
            col_info = firestore_output["data"][collection]["_collection_info"]
            col_info["tables_included"].append(tid)
            col_info["document_count"] = col_info.get("document_count", 0) + doc_count

        total_docs += doc_count
        processed += 1

        if processed % 50 == 0:
            print(f"     Processed {processed}/262 tables...")

    # ── Compile Report ──────────────────────────────────────────────────
    firestore_data = firestore_output["data"]
    firestore_output["_meta"]["total_tables_processed"] = processed
    firestore_output["_meta"]["total_documents_generated"] = total_docs
    firestore_output["_meta"]["unmapped_tables"] = unmapped_tables
    firestore_output["_meta"]["empty_tables"] = empty_tables
    firestore_output["_meta"]["tables_per_collection"] = {
        col: len(tids) for col, tids in sorted(tables_per_collection.items())
    }

    # Update collection info document counts
    for col_name, col_data in firestore_data.items():
        if "_collection_info" in col_data:
            info = col_data["_collection_info"]
            info["tables_included"] = sorted(set(info.get("tables_included", [])))
            doc_keys = [k for k in col_data.keys() if not k.startswith("_")]
            info["document_count"] = len(doc_keys)

    # ── Write Output ────────────────────────────────────────────────────
    print(f"\n[3/4] Writing {OUTPUT_PATH}...")
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(firestore_output, f, indent=2, ensure_ascii=False)

    file_size = os.path.getsize(OUTPUT_PATH)

    # ── Final Report ────────────────────────────────────────────────────
    print(f"\n{'='*70}")
    print(f"  CONVERSION COMPLETE")
    print(f"{'='*70}")
    print(f"  Output file: {OUTPUT_PATH}")
    print(f"  File size:   {file_size:,} bytes ({file_size/1024/1024:.1f} MB)")
    print(f"  Tables processed:    {processed}/262 ({100*processed/262:.1f}%)")
    print(f"  Documents generated: {total_docs}")
    print(f"  Unmapped tables:     {len(unmapped_tables)}: {unmapped_tables}")
    print(f"  Empty tables:        {len(empty_tables)}: {empty_tables}")
    print(f"  Skipped header rows: {skipped_header_rows}")
    print(f"  Collections populated:")
    for col_name, tids in sorted(tables_per_collection.items()):
        doc_count = len([k for k in firestore_data.get(col_name, {}).keys() if not k.startswith("_")])
        print(f"    {col_name:35s} {len(tids):3d} tables, {doc_count:5d} documents")
    print(f"{'='*70}")

    # Coverage check
    coverage = 100.0 * processed / 262
    print(f"\n  Coverage: {coverage:.1f}%")
    if coverage >= 99.0:
        print("  ✓ 100% table logging achieved (262/262)")
    else:
        print(f"  △ {262 - processed} tables not yet mapped")

    return processed == 262

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
