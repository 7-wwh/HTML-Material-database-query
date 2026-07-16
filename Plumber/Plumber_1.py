import pdfplumber
import sqlite3
import json
import os
import sys
import re
from datetime import datetime
from tqdm import tqdm

# =====================================================================
# ENHANCED STEEL TAXONOMY & CLASSIFICATION CONFIGURATION
# =====================================================================

TAXONOMY_RULES = [
    # --- STAINLESS STEEL SECTION (Pages 206+) ---
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
        "patterns": [r"stainless\s+steel\s+bars", r"hexagon\s+bars", r"square\s+bars"],
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

    # --- MACHINERY / ALLOY STEEL (Pages 248+) ---
    {
        "material": "Alloy Steel",
        "category": "Machinery Steel",
        "subcategory": "Harden & Tempered Carbon Steel",
        "patterns": [r"carbon\s+steel\s+ks\s+d3752", r"s10c", r"s45c", r"harden\s+&\s+tempered"],
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

    # --- FLANGES (Pages 187+) ---
    {
        "material": "Mild Steel",
        "category": "Flanges",
        "subcategory": "Flanges (JIS/ANSI/BS/DIN)",
        "patterns": [r"flanges?\b", r"jis\s+flanges", r"ansi\s+flanges", r"slip-on\s+flanges", r"welding\s+neck\s+flanges"],
        "table_prefix": "flanges"
    },
    
    # --- NON-FERROUS METALS (Pages 254+) ---
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

def classify_table_enhanced(raw_text, col_headers, page_num):
    """
    Stateful classifier that maps page text to taxonomy.
    Maintains a global track of the active material context (e.g. Mild vs Stainless)
    to prevent cross-material collisions.
    """
    global CURRENT_MATERIAL_CONTEXT
    
    text_content = (raw_text + " " + " ".join(col_headers)).lower()
    
    # Update state context if we see explicit section changes
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
        
    # Match against rules filtering by the active Material context first
    for rule in TAXONOMY_RULES:
        if rule["material"] == CURRENT_MATERIAL_CONTEXT:
            for pattern in rule["patterns"]:
                if re.search(pattern, text_content):
                    # Determine specification standard if present
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

    # Broad backup match across all rules if contextual match misses
    for rule in TAXONOMY_RULES:
        for pattern in rule["patterns"]:
            if re.search(pattern, text_content):
                return rule["material"], rule["category"], rule["subcategory"], rule["table_prefix"], "Standard"
                
    # Fallback default category
    return CURRENT_MATERIAL_CONTEXT, "Miscellaneous", "Other Profiles", "steel_misc", "Unknown"


# =====================================================================
# DATABASE SETUP
# =====================================================================

def init_db(db_path: str):
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    cur = conn.cursor()

    # Master document registry
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

    # --- AUTO MIGRATION CHECK ---
    # In case an older schema exists without the 'filepath' column, migrate it now.
    cur.execute("PRAGMA table_info(documents);")
    existing_columns = [row[1] for row in cur.fetchall()]
    if existing_columns and "filepath" not in existing_columns:
        print("[MIGRATION] Adding missing 'filepath' column to documents table...")
        cur.execute("ALTER TABLE documents ADD COLUMN filepath TEXT;")

    # General page registry
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

    # Page text chunks for search/RAG
    cur.execute("""
        CREATE TABLE IF NOT EXISTS pdf_chunks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            page_id INTEGER,
            chunk_index INTEGER,
            chunk_text TEXT,
            FOREIGN KEY(page_id) REFERENCES pdf_pages(id)
        );
    """)

    # Master registry updated with fine-grained taxonomy columns
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
            FOREIGN KEY(document_id) REFERENCES documents(document_id)
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS pdf_errors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_id INTEGER,
            page_number INTEGER,
            error_message TEXT,
            FOREIGN KEY(document_id) REFERENCES documents(document_id)
        );
    """)

    # FTS5 Virtual Table for full-text search
    cur.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS pdf_pages_fts USING fts5(
            raw_text,
            content='pdf_pages',
            content_rowid='id'
        );
    """)

    # Core B-Tree indexes
    cur.execute("CREATE INDEX IF NOT EXISTS idx_pages_doc_page ON pdf_pages(document_id, page_number);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_chunks_page_id ON pdf_chunks(page_id);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_registry_doc_page ON extracted_tables_registry(document_id, page_number);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_registry_taxonomy ON extracted_tables_registry(material, category, subcategory);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_registry_name ON extracted_tables_registry(table_name);")

    conn.commit()
    return conn


# =====================================================================
# UTILITIES AND DATA CLEANING
# =====================================================================

def sanitize_identifier(name: str, default_prefix: str = "col") -> str:
    """Turn any cell text into a safe SQLite column identifier."""
    if not name or not str(name).strip():
        return default_prefix
    
    clean = str(name).strip().lower()
    clean = re.sub(r'[^a-z0-9_]', '_', clean)
    clean = re.sub(r'_+', '_', clean).strip('_')
    
    if clean and clean[0].isdigit():
        clean = f"_{clean}"
        
    return clean if clean else default_prefix


def get_consolidated_table_name(cursor, prefix: str, col_headers: list) -> str:
    """
    Groups identical structural layouts under unified prefix-based names.
    If layouts deviate (e.g. angle layouts change), spins up versioned variants.
    """
    candidate_base = f"cat_{prefix}"
    counter = 1
    
    while True:
        table_name = candidate_base if counter == 1 else f"{candidate_base}_v{counter}"
        
        # Check if table already exists in the SQLite database
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
        table_exists = cursor.fetchone()
        
        if not table_exists:
            return table_name
            
        # Verify alignment with existing table info
        cursor.execute(f"PRAGMA table_info([{table_name}])")
        existing_cols = [row[1] for row in cursor.fetchall()]
        
        # Filter out metadata column for schema layout comparisons
        non_meta_cols = [c for c in col_headers if c != "page_number"]
        non_meta_existing = [c for c in existing_cols if c != "page_number"]
        
        if set(non_meta_cols) == set(non_meta_existing):
            return table_name
            
        counter += 1


def sanitize_column_headers(headers: list) -> list:
    """Deduplicates and sanitizes raw header columns."""
    sanitized_cols = []
    seen_names = {}
    
    for i, h in enumerate(headers):
        clean_h = sanitize_identifier(h, default_prefix=f"col_{i+1}")
        if clean_h == "page_number":
            clean_h = "page_number_data"  # Protect mandatory page_number identifier
        
        if clean_h in seen_names:
            seen_names[clean_h] += 1
            clean_h = f"{clean_h}_{seen_names[clean_h]}"
        else:
            seen_names[clean_h] = 0
            
        sanitized_cols.append(clean_h)
        
    sanitized_cols.append("page_number")  # Appended directly at the end
    return sanitized_cols


def compress_hierarchical_headers(table: list) -> list:
    """
    Looks at the first few rows of an extracted table to compress multi-level
    or hierarchical header blocks (e.g. nested column layouts) into a 
    single flattened row of unique descriptive column names.
    """
    if len(table) < 2:
        return table

    # Inspect the first 2 rows. If they contain duplicates/empty spaces 
    # and look like subcolumns, we join them.
    header_1 = [str(x).strip() if x is not None else "" for x in table[0]]
    header_2 = [str(x).strip() if x is not None else "" for x in table[1]]
    
    # Quick heuristic check: if second row contains units/subterms like 'mm', 'in', 'kg', 'lb'
    sub_patterns = r"^(mm|in|kg|lb|ft|cm|sec|max|min|depth|width|thickness|area|inertia|gyration|modulus|m|t|pc|pcs|wt|thk|od|id|dia)$"
    looks_hierarchical = any(re.match(sub_patterns, val.lower()) for val in header_2 if val)

    if looks_hierarchical:
        compressed_header = []
        current_parent = ""
        for parent, child in zip(header_1, header_2):
            if parent:
                current_parent = parent
            # Combine parent name and child term if they differ
            if current_parent and child and current_parent.lower() != child.lower():
                compressed_header.append(f"{current_parent}_{child}")
            elif current_parent:
                compressed_header.append(current_parent)
            else:
                compressed_header.append(child if child else "dimension")
        
        # Replace the first two rows with the compressed header row
        table[0] = compressed_header
        del table[1]
        
    return table


def clean_extracted_table(table: list, page_num: int) -> list:
    """
    Standardizes raw tabular data to guarantee a uniform rectangular layout.
    Cleans cells, resolves column mismatch, and appends the source page number 
    strictly as the very last column of each row.
    """
    if not table:
        return []
        
    # Compress any multi-line or nested headers
    table = compress_hierarchical_headers(table)
        
    # Clean up empty characters and drop completely blank rows
    raw_rows = []
    for row in table:
        cleaned_row = [str(cell).strip() if cell is not None else "" for cell in row]
        if any(cell != "" for cell in cleaned_row):
            raw_rows.append(cleaned_row)
            
    if not raw_rows:
        return []
        
    # Determine the maximum column length of raw rows to establish a perfect layout
    base_col_count = max(len(row) for row in raw_rows)
    
    cleaned_rows = []
    
    # Header Row (The first non-empty row)
    header_row = raw_rows[0]
    if len(header_row) < base_col_count:
        header_row += [""] * (base_col_count - len(header_row))
    else:
        header_row = header_row[:base_col_count]
    cleaned_rows.append(header_row)
    
    # Dataset Rows
    for row in raw_rows[1:]:
        if len(row) < base_col_count:
            row += [""] * (base_col_count - len(row))
        else:
            row = row[:base_col_count]
        row.append(page_num)  # Appended directly at the end as an integer
        cleaned_rows.append(row)
        
    return cleaned_rows


# =====================================================================
# MULTI-STRATEGY EXTRACTION & GEOMETRIC DEDUPLICATION
# =====================================================================

EXTRACTION_STRATEGIES = [
    {
        "name": "lines_strict",
        "settings": {
            "vertical_strategy":   "lines",
            "horizontal_strategy": "lines",
            "snap_tolerance":      3,
            "join_tolerance":      3,
            "text_x_tolerance":    3,
            "text_y_tolerance":    3,
        },
    },
    {
        "name": "lines_relaxed",
        "settings": {
            "vertical_strategy":   "lines",
            "horizontal_strategy": "lines",
            "snap_tolerance":      5,
            "join_tolerance":      5,
            "edge_min_length":     3,
            "text_x_tolerance":    5,
            "text_y_tolerance":    5,
            "intersection_tolerance": 5,
        },
    },
    {
        # HYBRID STRATEGY: This fixes the missing left-most column!
        # It uses drawn horizontal lines but relies on text alignment for columns.
        "name": "hybrid_text_vertical",
        "settings": {
            "vertical_strategy":   "text",
            "horizontal_strategy": "lines",
            "snap_tolerance":      5,
            "join_tolerance":      5,
            # INCREASED significantly to bridge internal cell spaces (e.g. '0.067  700')
            # preventing false vertical column splits in the middle of words/numbers.
            "text_x_tolerance":    12,
            "text_y_tolerance":    5,
            "min_words_vertical":  3,
        },
    },
    {
        "name": "text_aligned",
        "settings": {
            "vertical_strategy":   "text",
            "horizontal_strategy": "text",
            "snap_tolerance":      5,
            "join_tolerance":      5,
            # INCREASED significantly to bridge internal cell spaces
            "text_x_tolerance":    12,
            "text_y_tolerance":    5,
            "min_words_vertical":  3,
        },
    }
]

MIN_ROWS = 2      # Minimum rows (including header) to consider a table real
MIN_COLS = 2      # Minimum columns


def is_useful(table: list) -> bool:
    """True if the raw table has enough structural richness to process."""
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
    """Calculates table bounding box area."""
    w = box[2] - box[0]
    h = box[3] - box[1]
    return max(w * h, 1e-5)


def get_intersection_area(box1, box2) -> float:
    """Returns intersecting area of two bounding boxes (x0, y0, x1, y1)."""
    x0 = max(box1[0], box2[0])
    y0 = max(box1[1], box2[1])
    x1 = min(box1[2], box2[2])
    y1 = min(box1[3], box2[3])
    if x0 < x1 and y0 < y1:
        return (x1 - x0) * (y1 - y0)
    return 0.0


def calculate_raw_table_score(raw_table: list) -> float:
    """
    Score quality of table layout.
    Balances column count with data density (fill rate) to prevent 
    rewarding tables that are artificially shattered into tiny columns.
    """
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

    # Decreased the column reward multiplier from 30 to 10 so it doesn't over-prioritize 
    # broken/shattered column extractions, and heavily rewards the fill rate.
    return (cols * 10.0) + (rows * 2.5) + (fill_rate * 100.0)


def extract_tables_multi(page) -> list:
    """
    Runs multi-strategy table extraction, maps table bounding boxes on the page,
    deduplicates matching tables (retaining the highest-quality schema),
    and correctly extracts multiple discrete tables on a single page.
    
    Returns a list of tuples: [(raw_table, strategy_name)]
    """
    detected_tables = []

    for strategy in EXTRACTION_STRATEGIES:
        try:
            # Locate distinct table boundary objects on the page
            tables = page.find_tables(table_settings=strategy["settings"])
        except Exception as e:
            # Print the error instead of swallowing it silently
            print(f"  [Warning] Strategy {strategy['name']} failed: {e}")
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
                "bbox": table_obj.bbox,  # Bounding box: (x0, y0, x1, y1)
                "score": score
            })

    # Sort candidates by overall score descending so best extractions take priority
    detected_tables.sort(key=lambda x: x["score"], reverse=True)
    accepted_tables = []

    for candidate in detected_tables:
        overlap_found = False
        for accepted in accepted_tables:
            intersection = get_intersection_area(candidate["bbox"], accepted["bbox"])
            if intersection > 0.0:
                area_cand = get_area(candidate["bbox"])
                area_acc = get_area(accepted["bbox"])
                # If intersecting area represents > 30% of either table, they are duplicates
                if (intersection / area_cand > 0.3) or (intersection / area_acc > 0.3):
                    overlap_found = True
                    break

        if not overlap_found:
            accepted_tables.append(candidate)

    # Re-sort accepted non-overlapping tables top-to-bottom relative to reading order
    accepted_tables.sort(key=lambda x: x["bbox"][1])

    return [(t["raw"], t["strategy"]) for t in accepted_tables]


# =====================================================================
# TABLE INSERTS WITH CONSOLIDATION SUPPORT
# =====================================================================

def save_and_populate_table(conn, table_name: str, col_headers: list, data_rows: list):
    """
    Creates consolidated SQLite tables if they do not exist, 
    otherwise appends matching table layouts seamlessly.
    Ensures 'page_number' is parsed as INTEGER and indexed.
    """
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
        
        # Build index over critical steel dimensions for lightning-fast search
        critical_dimensions = ["size", "depth", "width", "thickness", "weight", "mass", "grade", "section_size", "diameter"]
        for header in col_headers:
            if any(term in header for term in critical_dimensions):
                idx_name = sanitize_identifier(f"idx_{table_name}_{header}"[:60], default_prefix="idx_custom")
                try:
                    cursor.execute(f"CREATE INDEX IF NOT EXISTS [{idx_name}] ON [{table_name}]([{header}]);")
                except Exception:
                    pass
        
        # Create explicit B-Tree index on page_number column
        page_idx = sanitize_identifier(f"idx_{table_name}_page_number", default_prefix="idx_page")
        cursor.execute(f"CREATE INDEX IF NOT EXISTS [{page_idx}] ON [{table_name}]([page_number]);")
        
    placeholders = ", ".join(["?"] * len(col_headers))
    insert_sql = f"INSERT INTO [{table_name}] VALUES ({placeholders})"
    cursor.executemany(insert_sql, data_rows)


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


# =====================================================================
# PIPELINE PROCESSOR
# =====================================================================

def convert_pdf_to_sqlite(pdf_path: str, db_path: str):
    if not os.path.exists(pdf_path):
        print(f"Error: The file {pdf_path} was not found.")
        sys.exit(1)
        
    conn = init_db(db_path)
    cursor = conn.cursor()
    
    filesize = os.path.getsize(pdf_path)
    filename = os.path.basename(pdf_path)
    # Get absolute path for authoritative tracking
    filepath = os.path.abspath(pdf_path)
    
    with pdfplumber.open(pdf_path) as pdf:
        total_pages = len(pdf.pages)
        pdf_meta = pdf.metadata or {}
        title = pdf_meta.get('Title', '')
        author = pdf_meta.get('Author', '')
        indexed_time = datetime.now().isoformat()
        
        cursor.execute('''
            INSERT INTO documents (filename, filepath, title, author, page_count, indexed_time, filesize)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (filename, filepath, title, author, total_pages, indexed_time, filesize))
        document_id = cursor.lastrowid
        conn.commit()
        
        stats = {"pages": 0, "tables_raw": 0, "errors": 0}
        
        for i, page in enumerate(tqdm(pdf.pages, desc=f"Processing {filename}")):
            page_num = i + 1
            
            # ── 1. Text Extraction & Search Index Setup ──────────────────
            try:
                raw_text = page.extract_text() or ""
                p_width = float(page.width)
                p_height = float(page.height)
                
                if len(raw_text.strip()) < 20:
                    cursor.execute('''
                        INSERT INTO pdf_errors (document_id, page_number, error_message) 
                        VALUES (?, ?, ?)
                    ''', (document_id, page_num, "OCR suggested: Scanned/low-text volume page."))
                    stats["errors"] += 1
                
                cursor.execute('''
                    INSERT INTO pdf_pages (document_id, page_number, width, height, raw_text)
                    VALUES (?, ?, ?, ?, ?)
                ''', (document_id, page_num, p_width, p_height, raw_text))
                page_id = cursor.lastrowid
                
                cursor.execute('''
                    INSERT INTO pdf_pages_fts (rowid, raw_text)
                    VALUES (?, ?)
                ''', (page_id, raw_text))
                
                chunks = chunk_text(raw_text)
                for chunk_idx, chunk in enumerate(chunks):
                    cursor.execute('''
                        INSERT INTO pdf_chunks (page_id, chunk_index, chunk_text)
                        VALUES (?, ?, ?)
                    ''', (page_id, chunk_idx, chunk))
                    
                stats["pages"] += 1
                    
            except Exception as e:
                cursor.execute('INSERT INTO pdf_errors (document_id, page_number, error_message) VALUES (?, ?, ?)',
                               (document_id, page_num, f"Text Extraction Error: {str(e)}"))
                stats["errors"] += 1
                conn.commit()
                continue

            # ── 2. Robust Adaptable Table Extraction ─────────────────────
            try:
                # Multi-strategy layout extractor supports multiple tables per page
                raw_tables = extract_tables_multi(page)
                
                for t_idx, (raw_table, strategy) in enumerate(raw_tables):
                    # Cleans rows and guarantees uniform rectangular bounds
                    cleaned_table = clean_extracted_table(raw_table, page_num)
                    if not cleaned_table or len(cleaned_table) < 2:
                        continue
                        
                    # Extract raw headers from row 0
                    raw_headers = cleaned_table[0]
                    col_headers = sanitize_column_headers(raw_headers)
                    data_rows = cleaned_table[1:]
                    
                    # Apply context-aware stateful classifier
                    material, category, subcategory, prefix, standard_group = classify_table_enhanced(raw_text, raw_headers, page_num)
                    
                    # Dynamic table grouping aligning with historical tables
                    final_table_name = get_consolidated_table_name(cursor, prefix, col_headers)
                    
                    # Populate consolidated tables
                    save_and_populate_table(conn, final_table_name, col_headers, data_rows)
                    
                    # Log table records in the metadata registry
                    cursor.execute('''
                        INSERT INTO extracted_tables_registry (
                            document_id, page_number, table_index, table_name, 
                            material, category, subcategory, standard_group, num_rows, num_cols
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (document_id, page_num, t_idx, final_table_name, 
                          material, category, subcategory, standard_group, len(data_rows), len(col_headers)))
                    stats["tables_raw"] += 1
                    
            except Exception as e:
                cursor.execute('INSERT INTO pdf_errors (document_id, page_number, error_message) VALUES (?, ?, ?)',
                               (document_id, page_num, f"Table Extraction/Taxonomy Error: {str(e)}"))
                stats["errors"] += 1

            # Safely commit records page-by-page to secure incremental extraction
            conn.commit()

    print(f"\n[SUCCESS] Document parsed successfully!")
    print(f"Stats: Pages={stats['pages']}, Tables={stats['tables_raw']}, Logged Errors={stats['errors']}")

# =====================================================================
# RUNNABLE ENTRY POINT
# =====================================================================

if __name__ == "__main__":
    # Point directly to your local file and define output SQLite file
    pdf_file_path = "./YH_HandBook.pdf"
    output_db_path = "./YH_HandBook.db"
    
    print(f"Initializing parsing: Searching for {pdf_file_path}...")
    if os.path.exists(pdf_file_path):
        convert_pdf_to_sqlite(pdf_file_path, output_db_path)
    else:
        print(f"[ERROR] Could not find '{pdf_file_path}' in the current folder.")
        print("Please verify the filename capitalization and ensure it resides in the same directory.")