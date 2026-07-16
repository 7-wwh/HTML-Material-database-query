import pdfplumber
import camelot
import sqlite3
import pandas as pd
import os
import sys
import re
import warnings
from datetime import datetime
from tqdm import tqdm
import logging

# Suppress noisy camelot/ghostscript warnings
warnings.filterwarnings("ignore", category=UserWarning)
logging.getLogger("pdfminer").setLevel(logging.WARNING)

# =====================================================================
# OCR DEPENDENCIES SETUP
# =====================================================================
try:
    import ocrmypdf
    HAS_OCRMYPDF = True
except ImportError:
    HAS_OCRMYPDF = False

try:
    import pytesseract
    HAS_TESSERACT = True
except ImportError:
    HAS_TESSERACT = False

# =====================================================================
# PDFMINER DRM BYPASS (MONKEYPATCH)
# =====================================================================
# We use a custom data descriptor that always returns True and safely 
# absorbs write/setter operations. This perfectly bypasses DRM checks 
# and prevents "AttributeError: can't set attribute" across all versions of pdfminer.
try:
    from pdfminer.pdfdocument import PDFDocument
    
    class SafeExtractableDescriptor:
        def __get__(self, instance, owner):
            return True
        def __set__(self, instance, value):
            pass  # Safely ignore all setter attempts to avoid write errors
            
    PDFDocument.is_extractable = SafeExtractableDescriptor()
    print("[DRM Bypass] Successfully applied universal pdfminer DRM bypass.")
except Exception as e:
    print(f"[DRM Bypass] Failed to apply pdfminer patch (non-fatal): {e}")

# Try importing restriction stripping libraries as a secondary backup
try:
    import pikepdf
    HAS_PIKEPDF = True
except ImportError:
    HAS_PIKEPDF = False

try:
    from pypdf import PdfReader, PdfWriter
    HAS_PYPDF = True
except ImportError:
    HAS_PYPDF = False

# =====================================================================
# PDF RESTRICTION / DRM REMOVER (PREPROCESSOR FALLBACK)
# =====================================================================

def strip_pdf_restrictions(input_path: str) -> str:
    """
    Backup strategy: Checks if a PDF has restrictions and generates a clean copy.
    With the pdfminer monkeypatch above active, this is rarely needed but kept for safety.
    """
    unrestricted_path = input_path.replace(".pdf", "_unrestricted.pdf")
    if os.path.exists(unrestricted_path):
        return unrestricted_path

    # Strategy 1: pikepdf (Highly reliable, rebuilds internal objects and strips DRM)
    if HAS_PIKEPDF:
        try:
            with pikepdf.open(input_path, allow_overwriting_input=False) as pdf:
                pdf.save(unrestricted_path)
            print(f"  [Preprocessor] Successfully stripped restrictions using pikepdf -> {unrestricted_path}")
            return unrestricted_path
        except Exception as e:
            print(f"  [Preprocessor] pikepdf failed: {e}")

    # Strategy 2: pypdf Fallback
    if HAS_PYPDF:
        try:
            reader = PdfReader(input_path)
            if reader.is_encrypted:
                reader.decrypt("") # Empty password unlocks owner permissions
            writer = PdfWriter()
            for page in reader.pages:
                writer.add_page(page)
            with open(unrestricted_path, "wb") as f:
                writer.write(f)
            print(f"  [Preprocessor] Successfully stripped restrictions using pypdf -> {unrestricted_path}")
            return unrestricted_path
        except Exception as e:
            print(f"  [Preprocessor] pypdf fallback failed: {e}")

    # Fall back directly to original path (pdfminer patch will handle it)
    return input_path


# =====================================================================
# OCR PREPROCESSOR (SCANNED PDF HANDLER)
# =====================================================================

def apply_ocr_if_needed(input_path: str) -> str:
    """
    Detects if a PDF consists of scanned images. If so, uses ocrmypdf 
    to burn a searchable text layer into the PDF so Camelot can read it.
    """
    ocr_path = input_path.replace(".pdf", "_ocr.pdf")
    if os.path.exists(ocr_path):
        print(f"  [OCR Check] Found existing OCR'd file -> {ocr_path}")
        return ocr_path

    print(f"  [OCR Check] Analyzing {input_path} for embedded text...")
    has_text = False
    try:
        with pdfplumber.open(input_path) as pdf:
            # Sample up to the first 3 pages
            for page in pdf.pages[:min(3, len(pdf.pages))]:
                text = page.extract_text()
                if text and len(text.strip()) > 50:
                    has_text = True
                    break
    except Exception:
        pass

    if has_text:
        print("  [OCR Check] Text layer detected. No full-document OCR required.")
        return input_path
        
    print("  [OCR Check] No text layer detected (Looks like a Scanned PDF).")
    if HAS_OCRMYPDF:
        print("  [OCR Engine] Running ocrmypdf to reconstruct text layer. This may take a few minutes...")
        try:
            # force_ocr ensures it applies OCR even if it finds vector artifacts.
            # deskew fixes crooked pages which drastically improves Camelot accuracy.
            ocrmypdf.ocr(input_path, ocr_path, force_ocr=True, deskew=True, optimize=1)
            print(f"  [OCR Engine] Successfully created text-layered PDF -> {ocr_path}")
            return ocr_path
        except Exception as e:
            print(f"  [OCR Engine] Failed to run ocrmypdf: {e}")
            print("  [OCR Engine] Info: Proceeding without OCR using the fallback text reader.")
    else:
        print("  [OCR Engine] WARNING: 'ocrmypdf' is not installed. Camelot will not find tables in images.")
        print("               Please install system dependencies (tesseract, ghostscript) and run: pip install ocrmypdf")
    
    return input_path


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

CURRENT_MATERIAL_CONTEXT = "Mild Steel"


def classify_table_enhanced(raw_text, col_headers, page_num):
    global CURRENT_MATERIAL_CONTEXT
    text_content = (raw_text + " " + " ".join(str(h) for h in col_headers)).lower()

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
                    standard = _detect_standard(text_content)
                    return CURRENT_MATERIAL_CONTEXT, rule["category"], rule["subcategory"], rule["table_prefix"], standard

    for rule in TAXONOMY_RULES:
        for pattern in rule["patterns"]:
            if re.search(pattern, text_content):
                return rule["material"], rule["category"], rule["subcategory"], rule["table_prefix"], "Standard"

    return CURRENT_MATERIAL_CONTEXT, "Miscellaneous", "Other Profiles", "steel_misc", "Unknown"


def _detect_standard(text_content):
    if re.search(r'\bjis\b|\bjp\b', text_content):
        return "JIS"
    elif re.search(r'\bbs\s*en\b|\bbs\b|\ben\b', text_content):
        return "BS/EN"
    elif re.search(r'\bastm\b|\bansi\b', text_content):
        return "ASTM/ANSI"
    elif re.search(r'\bstkm\b|\bks\b', text_content):
        return "KS/STKM"
    elif re.search(r'\bdin\b', text_content):
        return "DIN"
    elif re.search(r'\bapi\b', text_content):
        return "API"
    return "Standard"


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
            filename TEXT, filepath TEXT, title TEXT, author TEXT,
            page_count INTEGER, indexed_time TEXT, filesize INTEGER
        );
    """)

    cur.execute("PRAGMA table_info(documents);")
    existing_columns = [row[1] for row in cur.fetchall()]
    if existing_columns and "filepath" not in existing_columns:
        print("[MIGRATION] Adding missing 'filepath' column to documents table...")
        cur.execute("ALTER TABLE documents ADD COLUMN filepath TEXT;")

    cur.execute("""
        CREATE TABLE IF NOT EXISTS pdf_pages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_id INTEGER, page_number INTEGER,
            width REAL, height REAL, raw_text TEXT,
            FOREIGN KEY(document_id) REFERENCES documents(document_id)
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS pdf_chunks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            page_id INTEGER, chunk_index INTEGER, chunk_text TEXT,
            FOREIGN KEY(page_id) REFERENCES pdf_pages(id)
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS extracted_tables_registry (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_id INTEGER, page_number INTEGER,
            table_index INTEGER, table_name TEXT,
            material TEXT, category TEXT, subcategory TEXT,
            standard_group TEXT, extraction_strategy TEXT,
            num_rows INTEGER, num_cols INTEGER,
            FOREIGN KEY(document_id) REFERENCES documents(document_id)
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS pdf_errors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_id INTEGER, page_number INTEGER, error_message TEXT,
            FOREIGN KEY(document_id) REFERENCES documents(document_id)
        );
    """)

    cur.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS pdf_pages_fts USING fts5(
            raw_text, content='pdf_pages', content_rowid='id'
        );
    """)

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
        if not cursor.fetchone():
            return table_name
        cursor.execute(f"PRAGMA table_info([{table_name}])")
        existing_cols = [row[1] for row in cursor.fetchall()]
        non_meta_cols = [c for c in col_headers if c != "page_number"]
        non_meta_existing = [c for c in existing_cols if c != "page_number"]
        
        # CRITICAL FIX: Use exact list matching instead of set(). 
        # Using set() ignored column order, which would cause positional SQL INSERTS to mix up data
        # if a table had the same columns but in a different order (e.g. [A, B] vs [B, A]).
        if non_meta_cols == non_meta_existing:
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


# =====================================================================
# FORWARD-FILL: PROPAGATE MERGED/SPANNING CELL VALUES
# =====================================================================

def forward_fill_merged_cells(table: list) -> list:
    if not table or len(table) < 2:
        return table

    num_cols = max(len(row) for row in table)

    # Pad all rows to uniform width first
    padded = []
    for row in table:
        padded_row = list(row) + [""] * (num_cols - len(row))
        padded.append(padded_row)

    # ── 1. Horizontal forward-fill (skip header row) ──────────────────
    for r_idx in range(1, len(padded)):
        last_val = ""
        for c_idx in range(num_cols):
            cell = padded[r_idx][c_idx]
            cell_str = str(cell).strip() if cell is not None else ""
            if cell_str:
                last_val = cell_str
                padded[r_idx][c_idx] = cell_str
            else:
                if last_val and last_val not in ("-", "—", "–", "N/A", "n/a"):
                    padded[r_idx][c_idx] = last_val
        last_val = ""

    # ── 2. Vertical forward-fill (skip header row) ────────────────────
    for c_idx in range(num_cols):
        last_val = ""
        for r_idx in range(1, len(padded)):
            cell_str = str(padded[r_idx][c_idx]).strip() if padded[r_idx][c_idx] is not None else ""
            if cell_str:
                last_val = cell_str
            else:
                if last_val and last_val not in ("-", "—", "–", "N/A", "n/a"):
                    padded[r_idx][c_idx] = last_val

    return padded


def clean_extracted_table(table: list, page_num: int) -> list:
    if not table:
        return []

    table = compress_hierarchical_headers(table)

    # Drop completely blank rows
    raw_rows = []
    for row in table:
        cleaned_row = [str(cell).strip() if cell is not None else "" for cell in row]
        if any(cell != "" for cell in cleaned_row):
            raw_rows.append(cleaned_row)

    if not raw_rows:
        return []

    raw_rows = forward_fill_merged_cells(raw_rows)

    base_col_count = max(len(row) for row in raw_rows)
    cleaned_rows = []

    # Header row
    header_row = raw_rows[0]
    if len(header_row) < base_col_count:
        header_row += [""] * (base_col_count - len(header_row))
    else:
        header_row = header_row[:base_col_count]
    cleaned_rows.append(header_row)

    # Data rows — append page_number as an integer at the very end
    for row in raw_rows[1:]:
        if len(row) < base_col_count:
            row += [""] * (base_col_count - len(row))
        else:
            row = row[:base_col_count]
        row.append(page_num)
        cleaned_rows.append(row)

    return cleaned_rows


# =====================================================================
# CAMELOT TABLE EXTRACTION (PRIMARY ENGINE)
# =====================================================================

CAMELOT_STRATEGIES = [
    {
        "name": "camelot_lattice",
        "flavor": "lattice",
        "kwargs": {
            "copy_text":        ["h", "v"],
            "line_scale":       40,
            "process_background": False,
            "strip_text":       "\n",
        },
    },
    {
        "name": "camelot_lattice_bg",
        "flavor": "lattice",
        "kwargs": {
            "copy_text":        ["h", "v"],
            "line_scale":       40,
            "process_background": True,
            "strip_text":       "\n",
        },
    },
    {
        "name": "camelot_stream",
        "flavor": "stream",
        "kwargs": {
            "row_tol":          8,
            "column_tol":       4,
            "strip_text":       "\n",
        },
    },
    {
        "name": "camelot_stream_loose",
        "flavor": "stream",
        "kwargs": {
            "row_tol":          15,
            "column_tol":       6,
            "strip_text":       "\n",
            "edge_tol":          50,
        },
    },
]

CAM_MIN_ROWS = 2
CAM_MIN_COLS = 2
CAM_MIN_ACCURACY = 60.0


def _camelot_table_to_list(cam_table) -> list:
    return cam_table.data


def _score_table(data: list) -> float:
    if not data:
        return 0.0
    rows = len(data)
    cols = len(data[0]) if rows else 0
    if rows < CAM_MIN_ROWS or cols < CAM_MIN_COLS:
        return 0.0
    total = rows * cols
    filled = sum(1 for r in data for c in r if c is not None and str(c).strip())
    fill_rate = filled / total
    if fill_rate < 0.15:
        return 0.0
    return (cols * 10.0) + (rows * 2.5) + (fill_rate * 100.0)


def extract_tables_camelot(pdf_path: str, page_num: int) -> list:
    page_str = str(page_num)
    accepted = []

    for strategy in CAMELOT_STRATEGIES:
        try:
            tables = camelot.read_pdf(
                pdf_path,
                pages=page_str,
                flavor=strategy["flavor"],
                suppress_stdout=True,
                **strategy["kwargs"],
            )
        except Exception as exc:
            print(f"  [Camelot/{strategy['name']}] page {page_num}: {exc}")
            continue

        for cam_tbl in tables:
            try:
                accuracy = cam_tbl.parsing_report.get("accuracy", 0)
                if accuracy < CAM_MIN_ACCURACY:
                    continue
            except Exception:
                pass

            data = _camelot_table_to_list(cam_tbl)
            if not data or len(data) < CAM_MIN_ROWS or len(data[0]) < CAM_MIN_COLS:
                continue

            score = _score_table(data)
            if score <= 0.0:
                continue

            try:
                bbox_y = cam_tbl._bbox[1]
            except Exception:
                bbox_y = 0.0

            duplicate = False
            for existing in accepted:
                same_region = abs(bbox_y - existing["bbox_y"]) < 20
                same_shape = abs(len(data[0]) - len(existing["data"][0])) <= 1
                if same_region and same_shape:
                    if score > existing["score"]:
                        existing["data"] = data
                        existing["score"] = score
                        existing["strategy"] = strategy["name"]
                    duplicate = True
                    break

            if not duplicate:
                accepted.append({
                    "data":     data,
                    "bbox_y":   bbox_y,
                    "score":    score,
                    "strategy": strategy["name"],
                })

    accepted.sort(key=lambda x: x["bbox_y"], reverse=True)
    return [(item["data"], item["strategy"]) for item in accepted]


# =====================================================================
# PDFPLUMBER FALLBACK ENGINE (COMPLETED AND IMPROVED)
# =====================================================================

PDFPLUMBER_STRATEGIES = [
    {
        "name": "plumber_lines_strict",
        "settings": {
            "vertical_strategy": "lines", "horizontal_strategy": "lines",
            "snap_tolerance": 3, "join_tolerance": 3,
            "text_x_tolerance": 3, "text_y_tolerance": 3,
        },
    },
    {
        "name": "plumber_hybrid",
        "settings": {
            "vertical_strategy": "text", "horizontal_strategy": "lines",
            "snap_tolerance": 5, "join_tolerance": 5,
            "text_x_tolerance": 12, "text_y_tolerance": 5,
            "min_words_vertical": 3,
        },
    },
    {
        "name": "plumber_text_aligned",
        "settings": {
            "vertical_strategy": "text", "horizontal_strategy": "text",
            "snap_tolerance": 5, "join_tolerance": 5,
            "text_x_tolerance": 12, "text_y_tolerance": 5,
            "min_words_vertical": 3,
        },
    },
]

MIN_ROWS = 2
MIN_COLS = 2


def _plumber_is_useful(table: list) -> bool:
    if not table or len(table) < MIN_ROWS or not table[0] or len(table[0]) < MIN_COLS:
        return False
    data = table[1:]
    total = sum(len(r) for r in data)
    if total == 0:
        return False
    filled = sum(1 for r in data for c in r if c is not None and str(c).strip())
    return (filled / total) >= 0.20


def _plumber_score(raw_table: list) -> float:
    if not raw_table:
        return 0.0
    rows = len(raw_table)
    cols = len(raw_table[0]) if rows > 0 else 0
    if rows < MIN_ROWS or cols < MIN_COLS:
        return 0.0
    total = rows * cols
    filled = sum(1 for r in raw_table for c in r if c is not None and str(c).strip())
    fill_rate = filled / total
    if fill_rate < 0.2:
        return 0.0
    return (cols * 10.0) + (rows * 2.5) + (fill_rate * 100.0)


def _get_area(box) -> float:
    return max((box[2] - box[0]) * (box[3] - box[1]), 1e-5)


def _intersection_area(b1, b2) -> float:
    x0, y0 = max(b1[0], b2[0]), max(b1[1], b2[1])
    x1, y1 = min(b1[2], b2[2]), min(b1[3], b2[3])
    return (x1 - x0) * (y1 - y0) if x0 < x1 and y0 < y1 else 0.0


def extract_tables_pdfplumber(page) -> list:
    """pdfplumber multi-strategy fallback — used when Camelot finds nothing."""
    candidates = []
    for strategy in PDFPLUMBER_STRATEGIES:
        try:
            tables = page.find_tables(table_settings=strategy["settings"])
        except Exception as e:
            print(f"  [pdfplumber/{strategy['name']}]: {e}")
            continue
        for tobj in tables:
            try:
                raw = tobj.extract()
            except Exception:
                continue
            if not _plumber_is_useful(raw):
                continue
            score = _plumber_score(raw)
            if score <= 0.0:
                continue
            candidates.append({
                "raw": raw,
                "strategy": strategy["name"],
                "bbox": tobj.bbox,
                "score": score
            })

    # Sort so best scores are evaluated first
    candidates.sort(key=lambda x: x["score"], reverse=True)
    
    accepted = []
    for cand in candidates:
        overlap = False
        for acc in accepted:
            iarea = _intersection_area(cand["bbox"], acc["bbox"])
            if iarea > 0:
                cand_area = _get_area(cand["bbox"])
                acc_area = _get_area(acc["bbox"])
                if (iarea / cand_area > 0.3) or (iarea / acc_area > 0.3):
                    overlap = True
                    if cand["score"] > acc["score"]:
                        acc["raw"] = cand["raw"]
                        acc["strategy"] = cand["strategy"]
                        acc["bbox"] = cand["bbox"]
                        acc["score"] = cand["score"]
                    break
        if not overlap:
            accepted.append(cand)

    return [(item["raw"], item["strategy"]) for item in accepted]


# =====================================================================
# INTEGRATED PIPELINE MAIN EXECUTION
# =====================================================================

def process_pdf_document(pdf_path: str, db_path: str):
    # Ensure PDF restrictions are stripped out first (secondary backup)
    clean_pdf_path = strip_pdf_restrictions(pdf_path)
    
    # NEW: Ensure a text layer exists for Scanned PDFs
    clean_pdf_path = apply_ocr_if_needed(clean_pdf_path)

    conn = init_db(db_path)
    cursor = conn.cursor()

    # Register Document
    filesize = os.path.getsize(pdf_path)
    indexed_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    cursor.execute("""
        INSERT INTO documents (filename, filepath, title, page_count, indexed_time, filesize)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (os.path.basename(pdf_path), pdf_path, "Steel Handbook", 0, indexed_time, filesize))
    document_id = cursor.lastrowid

    # Open PDF using pdfplumber to count pages and store metadata
    try:
        with pdfplumber.open(clean_pdf_path) as pdf:
            pages_to_process = len(pdf.pages)
            cursor.execute("UPDATE documents SET page_count = ? WHERE document_id = ?", (pages_to_process, document_id))
            conn.commit()

            print(f"\n[Extraction Pipeline] Commencing extraction on '{pdf_path}' ({pages_to_process} pages)...")
            
            for page_idx in tqdm(range(pages_to_process), desc="Processing PDF Pages"):
                page_num = page_idx + 1
                page_obj = pdf.pages[page_idx]
                raw_text = page_obj.extract_text() or ""
                
                # NEW: PyTesseract Fallback for Page Text Indexing
                # If the page has no text (e.g. an isolated image in a mixed PDF), OCR it.
                if not raw_text.strip() and HAS_TESSERACT:
                    try:
                        im = page_obj.to_image(resolution=300)
                        raw_text = pytesseract.image_to_string(im.original)
                    except Exception:
                        pass

                # 1. Save general page structure
                cursor.execute("""
                    INSERT INTO pdf_pages (document_id, page_number, width, height, raw_text)
                    VALUES (?, ?, ?, ?, ?)
                """, (document_id, page_num, page_obj.width, page_obj.height, raw_text))
                page_db_id = cursor.lastrowid
                
                # Register page in virtual FTS table
                cursor.execute("INSERT INTO pdf_pages_fts(rowid, raw_text) VALUES(?, ?)", (page_db_id, raw_text))

                # 2. Extract tables - Primary Strategy (Camelot)
                tables_found = extract_tables_camelot(clean_pdf_path, page_num)
                strategy_used = "camelot"

                # Fallback Strategy (pdfplumber)
                if not tables_found:
                    tables_found = extract_tables_pdfplumber(page_obj)
                    strategy_used = "pdfplumber"

                # Process found tables
                for table_idx, (raw_table_data, strat_name) in enumerate(tables_found):
                    cleaned_table = clean_extracted_table(raw_table_data, page_num)
                    if not cleaned_table:
                        continue

                    headers = cleaned_table[0]
                    data_rows = cleaned_table[1:]

                    # Classify table category using metadata mapping
                    material, category, subcategory, table_prefix, standard = classify_table_enhanced(
                        raw_text, headers, page_num
                    )

                    # Create dynamic SQLite table for this material category
                    sanitized_headers = sanitize_column_headers(headers)
                    table_name = get_consolidated_table_name(cursor, table_prefix, sanitized_headers)

                    # Build columns query with TEXT type for all data, and page_number as integer
                    col_defs = []
                    for h in sanitized_headers:
                        if h == "page_number":
                            col_defs.append(f"[{h}] INTEGER")
                        else:
                            col_defs.append(f"[{h}] TEXT")
                            
                    create_table_sql = f"CREATE TABLE IF NOT EXISTS [{table_name}] ({', '.join(col_defs)});"
                    cursor.execute(create_table_sql)

                    # Insert tabular data
                    placeholders = ", ".join(["?"] * len(sanitized_headers))
                    insert_data_sql = f"INSERT INTO [{table_name}] VALUES ({placeholders})"
                    
                    for row in data_rows:
                        # Safety padding
                        if len(row) < len(sanitized_headers):
                            row += [""] * (len(sanitized_headers) - len(row))
                        cursor.execute(insert_data_sql, row[:len(sanitized_headers)])

                    # Log inside registry
                    cursor.execute("""
                        INSERT INTO extracted_tables_registry (
                            document_id, page_number, table_index, table_name,
                            material, category, subcategory, standard_group,
                            extraction_strategy, num_rows, num_cols
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        document_id, page_num, table_idx + 1, table_name,
                        material, category, subcategory, standard,
                        f"{strategy_used} ({strat_name})", len(data_rows), len(headers)
                    ))

                # Commit per page to optimize speed with journal WAL
                conn.commit()

        print(f"\n[Success] Extraction complete! All tables have been structured into '{db_path}'.")
    except Exception as general_err:
        print(f"\n[Fatal Error] Pipeline interrupted: {general_err}")
    finally:
        conn.close()


def run_diagnostics():
    """Validates the execution environment and package availability before running."""
    print("=== System Diagnostics & Pre-flight Check ===")
    print(f"Python Version: {sys.version.split()[0]}")
    print(f"pdfplumber: {'Installed' if 'pdfplumber' in sys.modules else 'Missing'}")
    print(f"camelot: {'Installed' if 'camelot' in sys.modules else 'Missing'}")
    print(f"pikepdf (DRM bypass): {'Installed' if HAS_PIKEPDF else 'Missing (Optional)'}")
    print(f"pypdf (DRM bypass): {'Installed' if HAS_PYPDF else 'Missing (Optional)'}")
    print(f"ocrmypdf (Table OCR Engine): {'Installed' if HAS_OCRMYPDF else 'Missing (Run: pip install ocrmypdf)'}")
    print(f"pytesseract (Text OCR Engine): {'Installed' if HAS_TESSERACT else 'Missing (Run: pip install pytesseract)'}")
    print("===========================================\n")


if __name__ == "__main__":
    # Configure your paths here
    PDF_FILE = "./YH_HandBook.pdf"
    SQLITE_DB = "./steel_specifications.db"

    # Run system tests to guarantee everything is functional
    run_diagnostics()

    if os.path.exists(PDF_FILE):
        process_pdf_document(PDF_FILE, SQLITE_DB)
    else:
        print(f"Error: Target file '{PDF_FILE}' was not found. Please place it in the same directory.")