import pdfplumber
import sqlite3
import re
import os
import sys
from datetime import datetime
from tqdm import tqdm

# =====================================================================
# ENHANCED STEEL TAXONOMY & CLASSIFICATION CONFIGURATION
# =====================================================================

TAXONOMY_RULES = [
    # --- STAINLESS STEEL SECTION ---
    {
        "material": "Stainless Steel",
        "category": "Stainless Pipes & Tubings",
        "subcategory": "Stainless Steel Pipes",
        "patterns": [r"stainless\s+steel\s+pipes", r"tp\s*304", r"tp\s*316", r"b36\.19"],
        "table_prefix": "ss_pipe"
    },
    {
        "material": "Stainless Steel",
        "category": "Stainless Pipes & Tubings",
        "subcategory": "Stainless Steel Welded Tubings",
        "patterns": [r"stainless\s+steel\s+welded\s+tubings?", r"round\s+tubing", r"stkm\s*11a"],
        "table_prefix": "ss_tubing"
    },
    {
        "material": "Stainless Steel",
        "category": "Stainless Angles & Flats",
        "subcategory": "Stainless Steel Angles",
        "patterns": [r"stainless\s+steel\s+angles", r"angles?\s+and\s+flats"],
        "table_prefix": "ss_angle"
    },
    {
        "material": "Stainless Steel",
        "category": "Stainless Bars",
        "subcategory": "Stainless Steel Bars (Round/Hex/Square)",
        "patterns": [r"stainless\s+steel\ss+bars", r"hexagon\s+bars", r"square\s+bars", r"ss\s+bars"],
        "table_prefix": "ss_bar"
    },
    {
        "material": "Stainless Steel",
        "category": "Stainless Channels",
        "subcategory": "Stainless Steel Welded Channels",
        "patterns": [r"stainless\s+steel\s+welded\s+channels"],
        "table_prefix": "ss_channel"
    },
    {
        "material": "Stainless Steel",
        "category": "Stainless Fittings",
        "subcategory": "Stainless Steel Fittings & Stub Ends",
        "patterns": [r"stainless\s+steel\s+fittings", r"stub\s+ends", r"long\s+radius\s+elbows"],
        "table_prefix": "ss_fitting"
    },

    # --- MACHINERY / ALLOY STEEL ---
    {
        "material": "Alloy Steel",
        "category": "Machinery Steel",
        "subcategory": "Harden & Tempered Carbon Steel",
        "patterns": [r"carbon\s+steel\s+ks\s+d3752", r"s10c", r"s45c", r"harden\s+&\s+tempered\s+steel"],
        "table_prefix": "alloy_carbon_tempered"
    },
    {
        "material": "Alloy Steel",
        "category": "Machinery Steel",
        "subcategory": "Pre-Harden & Tempered Alloy Steel",
        "patterns": [r"alloy\s+steel\s+ks\s+d3707", r"scm440", r"sncm439", r"pre-harden"],
        "table_prefix": "alloy_tempered"
    },
    {
        "material": "Alloy Steel",
        "category": "Machinery Steel",
        "subcategory": "Cold Finished Steel Bars",
        "patterns": [r"cold\s+finished\s+steel\s+bar", r"free\s+cutting\s+steel", r"sum22"],
        "table_prefix": "alloy_cold_finished"
    },

    # --- MILD STEEL - BEAMS & COLUMNS ---
    {
        "material": "Mild Steel",
        "category": "Beams & Columns",
        "subcategory": "Standard I-Beams",
        "patterns": [r"\bi\s*-\s*beams\b", r"\bibeams?\b", r"design\s+formulae\s+for\s+beams", r"stress\s+and\s+deflection\s+of\s+beams"],
        "table_prefix": "beam_standard_ibeam"
    },
    {
        "material": "Mild Steel",
        "category": "Beams & Columns",
        "subcategory": "Universal Beams (UB)",
        "patterns": [r"universal\s+beams", r"\bub\b", r"safe\s+loads\s+for\s+grade\s+43"],
        "table_prefix": "beam_universal"
    },
    {
        "material": "Mild Steel",
        "category": "Beams & Columns",
        "subcategory": "Universal Columns (UC)",
        "patterns": [r"universal\s+columns", r"\buc\b"],
        "table_prefix": "column_universal"
    },
    {
        "material": "Mild Steel",
        "category": "Beams & Columns",
        "subcategory": "Light Beams & Joists",
        "patterns": [r"light\s+beams\s+and\s+joists", r"joists?\b", r"r\s*s\s*j\b"],
        "table_prefix": "beam_joist"
    },
    {
        "material": "Mild Steel",
        "category": "Beams & Columns",
        "subcategory": "Bearing Piles",
        "patterns": [r"bearing\s+piles", r"\b8\s*x\s*8\s+bearing\b", r"\b12\s*x\s*12\s+bearing\b"],
        "table_prefix": "piles_bearing"
    },

    # --- MILD STEEL - PILES ---
    {
        "material": "Mild Steel",
        "category": "Piles",
        "subcategory": "Steel Sheet Piles (Larssen/Frodingham)",
        "patterns": [r"sheet\s+piles?", r"larssen", r"frodingham", r"interlocking\s+sections"],
        "table_prefix": "piles_sheet"
    },

    # --- MILD STEEL - PIPES & HOLLOW SECTIONS ---
    {
        "material": "Mild Steel",
        "category": "Pipes & Hollow Sections",
        "subcategory": "API & Seamless Pipes",
        "patterns": [r"api\s+pipes", r"seamless\s+pipes", r"api\s+mechanical", r"line\s+pipe"],
        "table_prefix": "pipe_api_seamless"
    },
    {
        "material": "Mild Steel",
        "category": "Pipes & Hollow Sections",
        "subcategory": "Cold Formed Hollow Sections",
        "patterns": [r"cold\s+formed\s+hollow\s+sections?", r"stkr-41", r"stkr-50"],
        "table_prefix": "hollow_cold_formed"
    },
    {
        "material": "Mild Steel",
        "category": "Pipes & Hollow Sections",
        "subcategory": "Hot Formed Hollow Sections",
        "patterns": [r"hot\s+formed\s+hollow\s+sections?", r"bs\s+4848\s+part\s+2"],
        "table_prefix": "hollow_hot_formed"
    },
    {
        "material": "Mild Steel",
        "category": "Pipes & Hollow Sections",
        "subcategory": "General Pipes (SGP / Scaffolding / Conduit)",
        "patterns": [r"\bpipes?\b", r"welded\s+steel\s+pipes", r"conduit", r"scaffolding", r"sgp\b"],
        "table_prefix": "pipe_general"
    },

    # --- MILD STEEL - CHANNELS ---
    {
        "material": "Mild Steel",
        "category": "Channels & Purlins",
        "subcategory": "Mild Steel Channels",
        "patterns": [r"plain\s+channels", r"lipped\s+channels", r"din\s+1026\s+channels", r"u-channels", r"g\s+3350"],
        "table_prefix": "channel_standard"
    },
    {
        "material": "Mild Steel",
        "category": "Channels & Purlins",
        "subcategory": "Z-Purlins",
        "patterns": [r"z-purlins?", r"high-tensile\s+galvanised\s+z-purlins?", r"\bbsz\b"],
        "table_prefix": "purlin_z"
    },
    {
        "material": "Mild Steel",
        "category": "Channels & Purlins",
        "subcategory": "C-Purlins",
        "patterns": [r"c-purlins?", r"high-tensile\s+galvanised\s+c-purlins?", r"\bbsc\b"],
        "table_prefix": "purlin_c"
    },

    # --- MILD STEEL - ANGLES ---
    {
        "material": "Mild Steel",
        "category": "Angles & Tees",
        "subcategory": "Equal Angles",
        "patterns": [r"equal\s+angles\b", r"equal\s+leg\s+angles?\b"],
        "table_prefix": "angle_equal"
    },
    {
        "material": "Mild Steel",
        "category": "Angles & Tees",
        "subcategory": "Unequal Angles",
        "patterns": [r"unequal\s+angles\b", r"unequal\s+leg\s+angles?\b"],
        "table_prefix": "angle_unequal"
    },
    {
        "material": "Mild Steel",
        "category": "Angles & Tees",
        "subcategory": "Inverted Angles",
        "patterns": [r"inverted\s+angles", r"unequal\s+legs?\s+and\s+thickness"],
        "table_prefix": "angle_inverted"
    },
    {
        "material": "Mild Steel",
        "category": "Angles & Tees",
        "subcategory": "Mild Steel Tee Bars",
        "patterns": [r"tee\s+bars", r"t\s+section\s+and\s+their\s+sectional"],
        "table_prefix": "tee_bars"
    },

    # --- MILD STEEL - BARS ---
    {
        "material": "Mild Steel",
        "category": "Bars & Plates",
        "subcategory": "Flat Bars",
        "patterns": [r"flat\s+bars\b", r"flat\b\s*(?!.*\bplates?\b)"],
        "table_prefix": "bar_flat"
    },
    {
        "material": "Mild Steel",
        "category": "Bars & Plates",
        "subcategory": "Bulb Flats",
        "patterns": [r"bulb\s+flats"],
        "table_prefix": "bar_bulb_flat"
    },
    {
        "material": "Mild Steel",
        "category": "Bars & Plates",
        "subcategory": "Square Bars",
        "patterns": [r"square\s+bars\b"],
        "table_prefix": "bar_square"
    },
    {
        "material": "Mild Steel",
        "category": "Bars & Plates",
        "subcategory": "Deformed & Round Bars",
        "patterns": [r"deformed\s+and\s+round\s+bars", r"rebar"],
        "table_prefix": "bar_round_deformed"
    },

    # --- MILD STEEL - PLATES & OTHERS ---
    {
        "material": "Mild Steel",
        "category": "Bars & Plates",
        "subcategory": "Steel Plates",
        "patterns": [r"plates\b", r"plates-specifications", r"chequered\s+\S+\s+plates?"],
        "table_prefix": "plate_standard"
    },
    {
        "material": "Mild Steel",
        "category": "Grating & Expanded Metal",
        "subcategory": "Gratings & Expanded Metal",
        "patterns": [r"gratings?", r"serrated\s+gratings?", r"expanded\s+metal"],
        "table_prefix": "grating_expanded"
    },

    # --- FLANGES ---
    {
        "material": "Mild Steel",
        "category": "Flanges",
        "subcategory": "Flanges (JIS/ANSI/BS/DIN)",
        "patterns": [r"flanges?\b", r"jis\s+flanges", r"ansi\s+flanges", r"slip-on\s+flanges", r"welding\s+neck\s+flanges"],
        "table_prefix": "flanges"
    },

    # --- NON-FERROUS METALS ---
    {
        "material": "Non-Ferrous",
        "category": "Copper/Brass/Bronze",
        "subcategory": "Copper",
        "patterns": [r"\bcopper\b"],
        "table_prefix": "non_ferrous_copper"
    },
    {
        "material": "Non-Ferrous",
        "category": "Copper/Brass/Bronze",
        "subcategory": "Brass",
        "patterns": [r"\bbrass\b"],
        "table_prefix": "non_ferrous_brass"
    },
    {
        "material": "Non-Ferrous",
        "category": "Copper/Brass/Bronze",
        "subcategory": "Bronze",
        "patterns": [r"\bbronze\b", r"continuous\s+casting"],
        "table_prefix": "non_ferrous_bronze"
    }
]

CURRENT_MATERIAL_CONTEXT = "Mild Steel"

def classify_table_enhanced(raw_text, title_context, col_headers, page_num):
    global CURRENT_MATERIAL_CONTEXT

    text_content = (raw_text + " " + title_context + " " + " ".join(col_headers)).lower()

    if "stainless steel" in text_content or page_num >= 206:
        if page_num < 248:
            CURRENT_MATERIAL_CONTEXT = "Stainless Steel"
    if "machinery steel" in text_content or "harden & tempered" in text_content or page_num >= 248:
        if page_num < 254:
            CURRENT_MATERIAL_CONTEXT = "Alloy Steel"
    if "non-ferrous" in text_content or "bronze" in text_content or "copper" in text_content or page_num >= 254:
        CURRENT_MATERIAL_CONTEXT = "Non-Ferrous"
    if page_num < 206 and CURRENT_MATERIAL_CONTEXT != "Mild Steel":
        CURRENT_MATERIAL_CONTEXT = "Mild Steel"

    for rule in TAXONOMY_RULES:
        if rule["material"] == CURRENT_MATERIAL_CONTEXT:
            for pattern in rule["patterns"]:
                if re.search(pattern, text_content):
                    standard = "Standard"
                    if re.search(r'\bjis\b|\bjp\b', text_content):
                        standard = "JIS"
                    elif re.search(r'\bbs\s*en\b|\bbs\b|\ben\b', text_content):
                        standard = "BS/EN"
                    elif re.search(r'\bastm\b|\bansi\b', text_content):
                        standard = "ASTM/ANSI"
                    elif re.search(r'\bstkm\b|\bks\b', text_content):
                        standard = "KS/STKM"
                    elif re.search(r'\bdin\b', text_content):
                        standard = "DIN"
                    elif re.search(r'\bapi\b', text_content):
                        standard = "API"
                    return CURRENT_MATERIAL_CONTEXT, rule["category"], rule["subcategory"], rule["table_prefix"], standard

    for rule in TAXONOMY_RULES:
        for pattern in rule["patterns"]:
            if re.search(pattern, text_content):
                return rule["material"], rule["category"], rule["subcategory"], rule["table_prefix"], "Standard"

    return CURRENT_MATERIAL_CONTEXT, "Miscellaneous", "Other Profiles", "steel_misc", "Unknown"


# =====================================================================
# DATABASE SETUP
# =====================================================================

def init_db(db_path: str):
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            document_id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT,
            filepath TEXT,
            title TEXT,
            author TEXT,
            page_count INTEGER,
            indexed_time TEXT,
            filesize INTEGER
        );
    """)

    cur.execute("PRAGMA table_info(documents);")
    existing_columns = [row[1] for row in cur.fetchall()]
    if existing_columns and "filepath" not in existing_columns:
        cur.execute("ALTER TABLE documents ADD COLUMN filepath TEXT;")

    cur.execute("""
        CREATE TABLE IF NOT EXISTS pdf_pages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_id INTEGER,
            page_number INTEGER,
            width REAL,
            height REAL,
            raw_text TEXT,
            FOREIGN KEY(document_id) REFERENCES documents(document_id)
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS pdf_chunks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            page_id INTEGER,
            chunk_index INTEGER,
            chunk_text TEXT,
            FOREIGN KEY(page_id) REFERENCES pdf_pages(id)
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS extracted_tables_registry (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_id INTEGER,
            page_number INTEGER,
            table_index INTEGER,
            table_name TEXT,
            material TEXT,
            category TEXT,
            subcategory TEXT,
            standard_group TEXT,
            num_rows INTEGER,
            num_cols INTEGER,
            strategy_used TEXT,
            FOREIGN KEY(document_id) REFERENCES documents(document_id)
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS pdf_errors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_id INTEGER,
            page_number INTEGER,
            error_type TEXT,
            error_message TEXT,
            offending_snippet TEXT,
            FOREIGN KEY(document_id) REFERENCES documents(document_id)
        );
    """)

    cur.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS pdf_pages_fts USING fts5(
            raw_text,
            content='pdf_pages',
            content_rowid='id'
        );
    """)

    cur.execute("CREATE INDEX IF NOT EXISTS idx_pages_doc_page ON pdf_pages(document_id, page_number);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_chunks_page_id ON pdf_chunks(page_id);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_registry_doc_page ON extracted_tables_registry(document_id, page_number);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_registry_taxonomy ON extracted_tables_registry(material, category, subcategory);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_registry_name ON extracted_tables_registry(table_name);")

    conn.commit()
    return conn


def log_error(cursor, document_id: int, page_num: int, error_type: str,
              error_message: str, offending_snippet: str = None):
    snippet = str(offending_snippet)[:500] if offending_snippet else None
    cursor.execute("""
        INSERT INTO pdf_errors (document_id, page_number, error_type, error_message, offending_snippet)
        VALUES (?, ?, ?, ?, ?)
    """, (document_id, page_num, error_type, error_message, snippet))


# =====================================================================
# TABLE EXTRACTION STRATEGIES & HEURISTICS
# =====================================================================

EXTRACTION_STRATEGIES = [
    {
        "name": "lines_strict",
        "settings": {
            "vertical_strategy": "lines",
            "horizontal_strategy": "lines",
            "snap_tolerance": 3,
            "join_tolerance": 3,
            "text_x_tolerance": 3,
            "text_y_tolerance": 3,
        }
    },
    {
        "name": "lines_relaxed",
        "settings": {
            "vertical_strategy": "lines",
            "horizontal_strategy": "lines",
            "snap_tolerance": 5,
            "join_tolerance": 5,
            "edge_min_length": 3,
            "text_x_tolerance": 5,
            "text_y_tolerance": 5,
            "intersection_tolerance": 5,
        }
    },
    {
        "name": "hybrid_text_vertical",
        "settings": {
            "vertical_strategy": "text",
            "horizontal_strategy": "lines",
            "snap_tolerance": 5,
            "join_tolerance": 5,
            "text_x_tolerance": 12,
            "text_y_tolerance": 5,
            "min_words_vertical": 3,
        },
    },
    {
        "name": "text_aligned",
        "settings": {
            "vertical_strategy": "text",
            "horizontal_strategy": "text",
            "snap_tolerance": 5,
            "join_tolerance": 5,
            "text_x_tolerance": 12,
            "text_y_tolerance": 5,
            "min_words_vertical": 3,
        },
    }
]

DIM_HEADER_PATTERN = re.compile(
    r'\b(mm|in|kg|lb|od|id|thk|wt|dia|size|width|depth|area|mass|weight|'
    r'no\.?|nom|sch|grade|spec|type|length|ixx|iyy|zxx|zyy|thickness|'
    r'section|designation|flange|web|radius|modulus|inertia|gyration)\b',
    re.IGNORECASE
)


def clean_cell(val):
    if val is None:
        return ""
    clean = re.sub(r'\s+', ' ', str(val)).strip()
    return clean


# =====================================================================
# UTILITIES AND DATA CLEANING (from Plumber_1)
# =====================================================================

def sanitize_identifier(name: str, default_prefix: str = "col") -> str:
    if not name or not str(name).strip():
        return default_prefix
    clean = str(name).strip().lower()
    clean = re.sub(r'[^a-z0-9_]', '_', clean)
    clean = re.sub(r'_+', '_', clean).strip('_')
    if clean and clean[0].isdigit():
        clean = f"_{clean}"
    return clean if clean else default_prefix


def get_consolidated_table_name(cursor, prefix: str, col_headers: list) -> str:
    candidate_base = f"cat_{prefix}"
    counter = 1
    while True:
        table_name = candidate_base if counter == 1 else f"{candidate_base}_v{counter}"
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
        table_exists = cursor.fetchone()
        if not table_exists:
            return table_name
        cursor.execute(f"PRAGMA table_info([{table_name}])")
        existing_cols = [row[1] for row in cursor.fetchall()]
        non_meta_cols = [c for c in col_headers if c != "page_number"]
        non_meta_existing = [c for c in existing_cols if c != "page_number"]
        if set(non_meta_cols) == set(non_meta_existing):
            return table_name
        counter += 1


def sanitize_column_headers(headers: list) -> list:
    sanitized_cols = []
    seen_names = {}
    for i, h in enumerate(headers):
        clean_h = sanitize_identifier(h, default_prefix=f"col_{i+1}")
        if clean_h == "page_number":
            clean_h = "page_number_data"
        if clean_h in seen_names:
            seen_names[clean_h] += 1
            clean_h = f"{clean_h}_{seen_names[clean_h]}"
        else:
            seen_names[clean_h] = 0
        sanitized_cols.append(clean_h)
    sanitized_cols.append("page_number")
    return sanitized_cols


def compress_hierarchical_headers(table: list) -> list:
    if len(table) < 2:
        return table
    header_1 = [str(x).strip() if x is not None else "" for x in table[0]]
    header_2 = [str(x).strip() if x is not None else "" for x in table[1]]
    sub_patterns = r"^(mm|in|kg|lb|ft|cm|sec|max|min|depth|width|thickness|area|inertia|gyration|modulus|m|t|pc|pcs|wt|thk|od|id|dia)$"
    looks_hierarchical = any(re.match(sub_patterns, val.lower()) for val in header_2 if val)
    if looks_hierarchical:
        compressed_header = []
        current_parent = ""
        for parent, child in zip(header_1, header_2):
            if parent:
                current_parent = parent
            if current_parent and child and current_parent.lower() != child.lower():
                compressed_header.append(f"{current_parent}_{child}")
            elif current_parent:
                compressed_header.append(current_parent)
            else:
                compressed_header.append(child if child else "dimension")
        table[0] = compressed_header
        del table[1]
    return table


def clean_extracted_table(table: list, page_num: int) -> list:
    if not table:
        return []
    table = compress_hierarchical_headers(table)
    raw_rows = []
    for row in table:
        cleaned_row = [str(cell).strip() if cell is not None else "" for cell in row]
        if any(cell != "" for cell in cleaned_row):
            raw_rows.append(cleaned_row)
    if not raw_rows:
        return []
    base_col_count = max(len(row) for row in raw_rows)
    cleaned_rows = []
    header_row = raw_rows[0]
    if len(header_row) < base_col_count:
        header_row += [""] * (base_col_count - len(header_row))
    else:
        header_row = header_row[:base_col_count]
    cleaned_rows.append(header_row)
    for row in raw_rows[1:]:
        if len(row) < base_col_count:
            row += [""] * (base_col_count - len(row))
        else:
            row = row[:base_col_count]
        row.append(page_num)
        cleaned_rows.append(row)
    return cleaned_rows


# =====================================================================
# MULTI-STRATEGY EXTRACTION & GEOMETRIC DEDUPLICATION (from Plumber_1)
# =====================================================================

MIN_ROWS = 2
MIN_COLS = 2


def is_useful(table: list) -> bool:
    if not table or len(table) < MIN_ROWS:
        return False
    if not table[0] or len(table[0]) < MIN_COLS:
        return False
    data = table[1:]
    total = sum(len(r) for r in data)
    if total == 0:
        return False
    filled = sum(1 for r in data for c in r if c is not None and str(c).strip())
    return (filled / total) >= 0.20


def get_area(box) -> float:
    w = box[2] - box[0]
    h = box[3] - box[1]
    return max(w * h, 1e-5)


def get_intersection_area(box1, box2) -> float:
    x0 = max(box1[0], box2[0])
    y0 = max(box1[1], box2[1])
    x1 = min(box1[2], box2[2])
    y1 = min(box1[3], box2[3])
    if x0 < x1 and y0 < y1:
        return (x1 - x0) * (y1 - y0)
    return 0.0


def calculate_raw_table_score(raw_table: list) -> float:
    if not raw_table:
        return 0.0
    rows = len(raw_table)
    cols = len(raw_table[0]) if rows > 0 else 0
    if rows < MIN_ROWS or cols < MIN_COLS:
        return 0.0
    total_cells = rows * cols
    filled_cells = sum(1 for r in raw_table for c in r if c is not None and str(c).strip())
    fill_rate = filled_cells / total_cells
    if fill_rate < 0.2:
        return 0.0
    return (cols * 10.0) + (rows * 2.5) + (fill_rate * 100.0)


def extract_tables_multi(page) -> list:
    detected_tables = []
    for strategy in EXTRACTION_STRATEGIES:
        try:
            tables = page.find_tables(table_settings=strategy["settings"])
        except Exception as e:
            continue
        for table_obj in tables:
            try:
                raw = table_obj.extract()
            except Exception:
                continue
            if not is_useful(raw):
                continue
            score = calculate_raw_table_score(raw)
            if score <= 0.0:
                continue
            detected_tables.append({
                "raw": raw,
                "strategy": strategy["name"],
                "bbox": table_obj.bbox,
                "score": score
            })
    detected_tables.sort(key=lambda x: x["score"], reverse=True)
    accepted_tables = []
    for candidate in detected_tables:
        overlap_found = False
        for accepted in accepted_tables:
            intersection = get_intersection_area(candidate["bbox"], accepted["bbox"])
            if intersection > 0.0:
                area_cand = get_area(candidate["bbox"])
                area_acc = get_area(accepted["bbox"])
                if (intersection / area_cand > 0.3) or (intersection / area_acc > 0.3):
                    overlap_found = True
                    break
        if not overlap_found:
            accepted_tables.append(candidate)
    accepted_tables.sort(key=lambda x: x["bbox"][1])
    return [(t["raw"], t["strategy"]) for t in accepted_tables]


# =====================================================================
# TABLE INSERTS WITH CONSOLIDATION SUPPORT (from Plumber_1)
# =====================================================================

def save_and_populate_table(conn, table_name: str, col_headers: list, data_rows: list):
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
    exists = cursor.fetchone()
    if not exists:
        col_defs = []
        for col in col_headers:
            if col == "page_number":
                col_defs.append("[page_number] INTEGER")
            else:
                col_defs.append(f"[{col}] TEXT")
        create_sql = f"CREATE TABLE [{table_name}] ({', '.join(col_defs)})"
        cursor.execute(create_sql)
        critical_dimensions = ["size", "depth", "width", "thickness", "weight", "mass", "grade", "section_size", "diameter"]
        for header in col_headers:
            if any(term in header for term in critical_dimensions):
                idx_name = sanitize_identifier(f"idx_{table_name}_{header}"[:60], default_prefix="idx_custom")
                try:
                    cursor.execute(f"CREATE INDEX IF NOT EXISTS [{idx_name}] ON [{table_name}]([{header}]);")
                except Exception:
                    pass
        page_idx = sanitize_identifier(f"idx_{table_name}_page_number", default_prefix="idx_page")
        cursor.execute(f"CREATE INDEX IF NOT EXISTS [{page_idx}] ON [{table_name}]([page_number]);")
    placeholders = ", ".join(["?"] * len(col_headers))
    insert_sql = f"INSERT INTO [{table_name}] VALUES ({placeholders})"
    cursor.executemany(insert_sql, data_rows)


def chunk_text(text: str, chunk_size: int = 100, overlap: int = 20) -> list:
    if not text:
        return []
    words = text.split()
    chunks = []
    start = 0
    while start < len(words):
        end = start + chunk_size
        chunks.append(" ".join(words[start:end]))
        start += chunk_size - overlap
    return chunks


# =====================================================================
# SYSTEM PROCESSING PIPELINE
# =====================================================================

def process_pdf(pdf_path: str, conn):
    cursor = conn.cursor()
    filename = os.path.basename(pdf_path)
    filesize = os.path.getsize(pdf_path)
    filepath = os.path.abspath(pdf_path)

    cursor.execute("""
        INSERT INTO documents (filename, filepath, title, author, page_count, indexed_time, filesize)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (filename, filepath, "Yick Hoe Structural Steel Handbook", "Yick Hoe Group", 0, datetime.now().isoformat(), filesize))
    document_id = cursor.lastrowid

    print(f"[*] Started processing: {filename} (ID: {document_id})")

    with pdfplumber.open(pdf_path) as pdf:
        total_pages = len(pdf.pages)
        cursor.execute("UPDATE documents SET page_count = ? WHERE document_id = ?", (total_pages, document_id))

        for i, page in enumerate(tqdm(pdf.pages, desc="Extracting pages")):
            page_num = i + 1
            width = float(page.width)
            height = float(page.height)

            # --- Text Extraction ---
            try:
                raw_text = page.extract_text() or ""
            except Exception as e:
                log_error(cursor, document_id, page_num, "TEXT_EXTRACTION_ERROR", str(e))
                conn.commit()
                continue

            cursor.execute("""
                INSERT INTO pdf_pages (document_id, page_number, width, height, raw_text)
                VALUES (?, ?, ?, ?, ?)
            """, (document_id, page_num, width, height, raw_text))
            page_id = cursor.lastrowid

            try:
                cursor.execute("""
                    INSERT INTO pdf_pages_fts (rowid, raw_text)
                    VALUES (?, ?)
                """, (page_id, raw_text))
            except Exception:
                pass

            chunks = chunk_text(raw_text)
            for chunk_idx, chunk in enumerate(chunks):
                cursor.execute("""
                    INSERT INTO pdf_chunks (page_id, chunk_index, chunk_text)
                    VALUES (?, ?, ?)
                """, (page_id, chunk_idx, chunk))

            # --- Table Extraction ---
            try:
                raw_tables = extract_tables_multi(page)
            except Exception as ex:
                log_error(cursor, document_id, page_num, "TABLE_EXTRACTION_FAILED", f"extract_tables_multi crashed: {str(ex)}")
                conn.commit()
                continue

            if not raw_tables:
                log_error(cursor, document_id, page_num, "NO_TABLES_FOUND", "No valid tables detected on this page.")

            for t_idx, (raw_table, strategy) in enumerate(raw_tables):
                try:
                    cleaned_table = clean_extracted_table(raw_table, page_num)
                    if not cleaned_table or len(cleaned_table) < 2:
                        continue

                    raw_headers = cleaned_table[0]
                    col_headers = sanitize_column_headers(raw_headers)
                    data_rows = cleaned_table[1:]

                    material, category, subcategory, prefix, standard_group = classify_table_enhanced(
                        raw_text, "", raw_headers, page_num
                    )

                    final_table_name = get_consolidated_table_name(cursor, prefix, col_headers)

                    save_and_populate_table(conn, final_table_name, col_headers, data_rows)

                    cursor.execute("""
                        INSERT INTO extracted_tables_registry (
                            document_id, page_number, table_index, table_name,
                            material, category, subcategory, standard_group, num_rows, num_cols, strategy_used
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (document_id, page_num, t_idx, final_table_name,
                          material, category, subcategory, standard_group, len(data_rows), len(col_headers), strategy))

                except Exception as ex:
                    log_error(cursor, document_id, page_num, "TABLE_INGESTION_ERROR", str(ex))

            conn.commit()

    conn.commit()
    print("[+] Processing complete. Database updated successfully.")


if __name__ == "__main__":
    pdf_file = "YH_HandBook.pdf"
    db_file = "structural_steel_handbook.db"

    if not os.path.exists(pdf_file):
        print(f"[-] Error: {pdf_file} not found. Put the PDF in this directory and try again.")
        sys.exit(1)

    print("[*] Initializing Database...")
    db_connection = init_db(db_file)

    try:
        process_pdf(pdf_file, db_connection)
    except KeyboardInterrupt:
        print("\n[-] Extraction interrupted by user.")
    finally:
        db_connection.close()
