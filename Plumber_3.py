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
        "patterns": [r"stainless\s+steel\s+bars", r"hexagon\s+bars", r"square\s+bars", r"ss\s+bars"],
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
        "patterns": [r"plates\b", r"plates-specifications", r"chequered\s+（floor）\s+plates?"],
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

# Tracker variable used during processing to remember the active Material context
CURRENT_MATERIAL_CONTEXT = "Mild Steel"

def classify_table_enhanced(raw_text, title_context, col_headers, page_num):
    global CURRENT_MATERIAL_CONTEXT

    text_content = (raw_text + " " + title_context + " " + " ".join(col_headers)).lower()

    # Broad context tracking based on page headers or section markings
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

    # Attempt rule-based match within active context
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

    # Fallback to general pattern sweep if context rules missed
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
            "snap_tolerance": 6,
            "join_tolerance": 6,
            "text_x_tolerance": 5,
            "text_y_tolerance": 5,
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
        }
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
        }
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
    # Strip whitespace, strip control characters, normalize spaces
    clean = re.sub(r'\s+', ' ', str(val)).strip()
    return clean


def is_valid_structural_data(table, cursor, doc_id, page_num):
    if not table or len(table) < 2:
        return False, "Insufficient rows"
    
    col_count = len(table[0])
    if col_count < 2:
        return False, "Insufficient columns"

    # Fill rate analysis
    total_cells = len(table) * col_count
    filled_cells = sum(1 for row in table for cell in row if clean_cell(cell))
    fill_rate = filled_cells / total_cells
    if fill_rate < 0.15:
        return False, f"Extremely low cell fill rate: {fill_rate:.1%}"

    # Verify if header contains typical dimension/unit/spec tokens
    header_str = " ".join([clean_cell(c) for c in table[0]])
    if not DIM_HEADER_PATTERN.search(header_str) and not any(isinstance(r, (int, float)) for r in table[1][0:2]):
        # Check second row if first didn't match (for hierarchical headers)
        header_str_2 = " ".join([clean_cell(c) for c in table[1]]) if len(table) > 1 else ""
        if not DIM_HEADER_PATTERN.search(header_str_2):
            return False, "Header row does not contain expected dimension or structural attributes"

    return True, "Valid Table"


# =====================================================================
# HIERARCHICAL HEADER RESOLUTION & CELL WRAP MERGING (FIXES CUTOFFS)
# =====================================================================

def is_row_continuation(row, prev_row) -> bool:
    """
    Heuristic to determine if an empty-prefix row is a cell text-wrapping continuation
    or a brand new row containing vertically merged data cells.
    """
    # If the first column contains a value, it is definitely a new row.
    if clean_cell(row[0]):
        return False

    # Find non-empty columns
    non_empty_indices = [i for i, c in enumerate(row) if clean_cell(c)]
    if not non_empty_indices:
        return False  # Completely blank line

    # If any other key columns contain new numeric-like values,
    # it is a new vertically merged row rather than a text wrap continuation.
    for idx in non_empty_indices:
        val = clean_cell(row[idx])
        # Match standard decimal numbers, fractions, or spec identifiers (like 'sch40', '1/2', '12.7')
        if re.match(r'^\d+(\.\d+)?$|^\d+/\d+$|^\d+x\d+$|^\d+”?$|^sch\d+s?$', val, re.IGNORECASE):
            return False  # Likely a new metric set under a merged section name

    return True  # Otherwise, treat as cell wrapping continuation


def clean_and_process_subtable(sub_rows: list) -> list:
    """
    1. Detects and compresses hierarchical headers dynamically (up to 3 rows).
    2. Runs a robust row wrapping layout parser. Continuations of long descriptions
       and wrapped texts are intelligently concatenated back into their parent cells
       instead of producing broken, empty-key database rows.
    3. Performs forward filling propagation on empty cells belonging to vertical merges.
    """
    if not sub_rows or len(sub_rows) < 2:
        return sub_rows

    # Step 1: Resolve header rows index
    header_lines = 1
    if len(sub_rows) >= 2:
        header_2 = [clean_cell(c) for c in sub_rows[1]]
        sub_patterns = r"^(mm|in|kg|lb|ft|cm|sec|max|min|depth|width|thickness|area|inertia|gyration|modulus|m|t|pc|pcs|wt|thk|od|id|dia)$"
        if any(re.match(sub_patterns, val.lower()) for val in header_2 if val):
            header_lines = 2
            if len(sub_rows) >= 3:
                header_3 = [clean_cell(c) for c in sub_rows[2]]
                if any(re.match(sub_patterns, val.lower()) for val in header_3 if val):
                    header_lines = 3

    headers_to_merge = sub_rows[:header_lines]
    data_rows = sub_rows[header_lines:]

    num_cols = len(sub_rows[0])
    flat_header = [""] * num_cols

    # Compress parent spans down-across
    for col_idx in range(num_cols):
        col_parts = []
        for row_idx in range(header_lines):
            val = clean_cell(headers_to_merge[row_idx][col_idx])
            if not val and col_idx > 0:
                for left_idx in range(col_idx - 1, -1, -1):
                    left_val = clean_cell(headers_to_merge[row_idx][left_idx])
                    if left_val:
                        val = left_val
                        break
            if val and val not in col_parts:
                col_parts.append(val)
        flat_header[col_idx] = "_".join(col_parts).strip()

    # Step 2: Merge wrapped rows
    merged_data = []
    for row in data_rows:
        is_continuation = False
        if merged_data:
            is_continuation = is_row_continuation(row, merged_data[-1])

        if is_continuation and merged_data:
            prev_row = merged_data[-1]
            for col_idx in range(min(len(row), len(prev_row))):
                curr_val = clean_cell(row[col_idx])
                if curr_val:
                    prev_val = clean_cell(prev_row[col_idx])
                    if prev_val:
                        prev_row[col_idx] = f"{prev_val} {curr_val}"
                    else:
                        prev_row[col_idx] = curr_val
        else:
            merged_data.append([clean_cell(c) for c in row])

    # Step 3: Vertical forward-fill (propagation of vertically merged cell values)
    last_seen = [""] * num_cols
    for row_idx in range(len(merged_data)):
        for col_idx in range(num_cols):
            val = merged_data[row_idx][col_idx]
            
            # We forward-fill the left-most columns (columns 0, 1, 2)
            # or columns whose header names indicate category grouping keys
            header_name = flat_header[col_idx].lower() if col_idx < len(flat_header) else ""
            is_grouping_col = (
                col_idx < 3 or 
                any(term in header_name for term in ["size", "class", "grade", "type", "dimension", "nominal", "outside_diameter", "pipe_size"])
            )
            
            if val:
                last_seen[col_idx] = val
            elif is_grouping_col and last_seen[col_idx]:
                merged_data[row_idx][col_idx] = last_seen[col_idx]

    return [flat_header] + merged_data


# =====================================================================
# ADVANCED TABLE SPLITTING HEURISTICS
# =====================================================================

def split_table_rows(raw_table: list) -> list:
    """
    Splits a single extracted raw table (list of list of strings) into multiple
    independent tables if it contains repeating headers or title dividers mid-table.
    Returns list of dicts: [{"title_context": str, "rows": list}]
    """
    if not raw_table:
        return []
        
    subtables = []
    current_rows = []
    current_title_context = ""
    
    # Helper to check if a row is a title/divider row
    def is_title_row(row):
        non_empty = [clean_cell(c) for c in row if clean_cell(c)]
        if len(non_empty) == 1:
            val = non_empty[0]
            # Title rows are usually longer text strings
            if len(val) > 4 and not re.match(r'^\d+(\.\d+)?$', val):
                return True, val
        # Check for rows that look like full title span (sometimes split across 2 adjacent columns)
        if len(non_empty) == 2:
            joined = " ".join(non_empty)
            if len(joined) > 10 and any(x in joined.lower() for x in ["elbow", "return", "tee", "reducer", "cap", "table", "pn", "class", "flange", "pipe", "bar", "plate", "angle", "channel", "purlin", "metal", "grating"]):
                return True, joined
        return False, ""

    # Helper to check if a row is a repeating header row
    def is_header_repeat(row, first_row_header):
        cleaned_row = [clean_cell(c).lower() for c in row]
        cleaned_first = [clean_cell(c).lower() for c in first_row_header]
        # If it matches the first row's columns closely
        matches = sum(1 for r, f in zip(cleaned_row, cleaned_first) if r == f and r)
        if matches >= max(2, len(cleaned_first) * 0.4):
            return True
        # Or if it contains typical header keywords
        header_words = sum(1 for r in cleaned_row if DIM_HEADER_PATTERN.search(r))
        if header_words >= max(2, len(cleaned_row) * 0.4):
            return True
        return False

    first_header = None
    for idx, row in enumerate(raw_table):
        is_title, title_text = is_title_row(row)
        
        # Check if we should split at this row
        should_split = False
        if idx > 0:
            if is_title:
                should_split = True
            elif first_header and is_header_repeat(row, first_header):
                should_split = True
        
        if should_split:
            if current_rows:
                subtables.append({
                    "title_context": current_title_context,
                    "rows": current_rows
                })
            current_rows = []
            if is_title:
                current_title_context = title_text
                first_header = None  # Reset first header to detect next actual column header row
            else:
                # If splitting on a repeated header, keep it as the start of the next subtable
                current_rows.append(row)
                first_header = row
        else:
            if not current_rows:
                if not is_title:
                    first_header = row
                    current_rows.append(row)
                else:
                    current_title_context = title_text
            else:
                current_rows.append(row)
    
    if current_rows:
        subtables.append({
            "title_context": current_title_context,
            "rows": current_rows
        })
        
    return subtables


# =====================================================================
# SYSTEM PROCESSING PIPELINE
# =====================================================================

def process_pdf(pdf_path: str, conn):
    cur = conn.cursor()
    filename = os.path.basename(pdf_path)
    filesize = os.path.getsize(pdf_path)

    # Register document
    cur.execute("""
        INSERT INTO documents (filename, filepath, title, author, page_count, indexed_time, filesize)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (filename, pdf_path, "Yick Hoe Structural Steel Handbook", "Yick Hoe Group", 0, datetime.now().isoformat(), filesize))
    document_id = cur.lastrowid

    print(f"[*] Started processing: {filename} (ID: {document_id})")

    with pdfplumber.open(pdf_path) as pdf:
        page_count = len(pdf.pages)
        cur.execute("UPDATE documents SET page_count = ? WHERE document_id = ?", (page_count, document_id))

        for page_idx, page in enumerate(tqdm(pdf.pages, desc="Extracting pages")):
            page_num = page_idx + 1
            width = float(page.width)
            height = float(page.height)
            
            raw_text = page.extract_text() or ""
            
            # Save raw page text
            cur.execute("""
                INSERT INTO pdf_pages (document_id, page_number, width, height, raw_text)
                VALUES (?, ?, ?, ?, ?)
            """, (document_id, page_num, width, height, raw_text))
            page_id = cur.lastrowid

            # Save basic search chunks
            chunks = chunk_text(raw_text)
            for chunk_idx, chunk_text_val in enumerate(chunks):
                cur.execute("""
                    INSERT INTO pdf_chunks (page_id, chunk_index, chunk_text)
                    VALUES (?, ?, ?)
                """, (page_id, chunk_idx, chunk_text_val))

            # Apply table extraction strategies adaptively
            table_extracted = False
            extracted_subtables = []

            for strategy in EXTRACTION_STRATEGIES:
                try:
                    tables = page.extract_tables(table_settings=strategy["settings"])
                    if tables:
                        for tbl_idx, raw_table in enumerate(tables):
                            # Clean the cells first
                            cleaned_raw = [[clean_cell(c) for c in row] for row in raw_table if row]
                            
                            # Dynamically split sub-tables on this page
                            sub_tables = split_table_rows(cleaned_raw)
                            
                            for sub_tbl in sub_tables:
                                sub_rows = sub_tbl["rows"]
                                sub_title = sub_tbl["title_context"]
                                
                                valid, reason = is_valid_structural_data(sub_rows, cur, document_id, page_num)
                                if valid:
                                    # Process, flatten, merge, and forward-fill cells
                                    structured_table = clean_and_process_subtable(sub_rows)
                                    extracted_subtables.append((sub_title, structured_table, strategy["name"]))
                                    table_extracted = True
                        
                        if table_extracted:
                            break  # Move to saving steps once a robust strategy succeeds
                except Exception as ex:
                    log_error(cur, document_id, page_num, "STRATEGY_FAILED", f"Strategy '{strategy['name']}' crashed: {str(ex)}")

            # If visual grid strategy failed, log page skip or fallback attempt
            if not table_extracted:
                log_error(cur, document_id, page_num, "GRID_EXTRACTION_EMPTY", "Visual grid checks returned zero validated tables.")

            # Save extracted tables
            for tbl_idx, (title_context, table_data, strategy_used) in enumerate(extracted_subtables):
                save_table_to_db(cur, document_id, page_num, tbl_idx, title_context, table_data, strategy_used, raw_text)

            conn.commit()

    conn.commit()
    print("[+] Processing complete. Database updated successfully.")


# =====================================================================
# DYNAMIC SCHEMA GENERATION & INGESTION
# =====================================================================

def save_table_to_db(cur, document_id: int, page_num: int, table_idx: int, title_context: str, table_data: list, strategy_used: str, raw_text: str):
    headers = table_data[0]
    data_rows = table_data[1:]

    # Clean headers to produce unique SQL column safe identifiers
    clean_headers = []
    seen = {}
    for i, h in enumerate(headers):
        clean = re.sub(r'[^a-zA-Z0-9_]', '_', h.strip()).lower()
        clean = re.sub(r'_+', '_', clean).strip('_')
        if not clean:
            clean = f"col_{i+1}"
        if clean in seen:
            seen[clean] += 1
            clean = f"{clean}_{seen[clean]}"
        else:
            seen[clean] = 0
        clean_headers.append(clean)

    # Classify material taxonomy
    material, category, subcategory, prefix, standard = classify_table_enhanced(raw_text, title_context, headers, page_num)
    
    # Generate unique dynamic table name
    if title_context:
        # Sanitize subtitle context to form unique split table name
        sanitized_title = re.sub(r'[^a-zA-Z0-9]', '_', title_context.strip()).lower()
        sanitized_title = re.sub(r'_+', '_', sanitized_title).strip('_')
        title_slug = "_".join(sanitized_title.split("_")[:4])
        table_name = f"cat_{prefix}_{title_slug}"
    else:
        table_name = f"cat_{prefix}"
    
    # Verify/Adjust SQLite table schema dynamically
    column_defs = ", ".join([f"[{col}] TEXT" for col in clean_headers])
    
    try:
        # Check if table already exists
        cur.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'")
        table_exists = cur.fetchone()

        if not table_exists:
            # Create a brand new consolidated table
            cur.execute(f"""
                CREATE TABLE IF NOT EXISTS [{table_name}] (
                    row_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    document_id INTEGER,
                    page_number INTEGER,
                    subtable_title TEXT,
                    {column_defs}
                )
            """)
        else:
            # Table exists; verify if we need to append any missing columns (Schema Evolution)
            cur.execute(f"PRAGMA table_info([{table_name}])")
            existing_cols = [col[1] for col in cur.fetchall()]
            
            if "subtable_title" not in existing_cols:
                cur.execute(f"ALTER TABLE [{table_name}] ADD COLUMN subtable_title TEXT")
                
            for clean_col in clean_headers:
                if clean_col not in existing_cols:
                    cur.execute(f"ALTER TABLE [{table_name}] ADD COLUMN [{clean_col}] TEXT")

        # Ingest row data safely
        for row in data_rows:
            # Ensure row matches the expected column layout
            row_data = row + [""] * (len(headers) - len(row))  # Pad if shorter
            row_data = row_data[:len(headers)]                # Clip if longer

            columns_segment = ", ".join([f"[{c}]" for c in clean_headers])
            placeholders = ", ".join(["?"] * (len(clean_headers) + 3))
            
            insert_query = f"""
                INSERT INTO [{table_name}] (document_id, page_number, subtable_title, {columns_segment})
                VALUES ({placeholders})
            """
            cur.execute(insert_query, [document_id, page_num, title_context] + row_data)

        # Log entry inside registry
        cur.execute("""
            INSERT INTO extracted_tables_registry 
            (document_id, page_number, table_index, table_name, material, category, subcategory, standard_group, num_rows, num_cols, strategy_used)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (document_id, page_num, table_idx, table_name, material, category, subcategory, standard, len(data_rows), len(headers), strategy_used))

    except Exception as ex:
        log_error(cur, document_id, page_num, "SCHEMA_OR_INGESTION_ERROR", 
                  f"Failed table ingestion into [{table_name}]: {str(ex)}", offending_snippet=str(headers))


# =====================================================================
# TEXT CHUNKING
# =====================================================================

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