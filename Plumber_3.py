import pdfplumber
import camelot
import sqlite3
import pandas as pd
import os
import sys
import re
import json
import warnings
import math
import hashlib
from datetime import datetime
from tqdm import tqdm
import logging
from PIL import Image

# Suppress noisy external library warnings
warnings.filterwarnings("ignore")
logging.getLogger("pdfminer").setLevel(logging.WARNING)

# =====================================================================
# MACHINE LEARNING & ML PIPELINE DEPENDENCIES
# =====================================================================
try:
    from sentence_transformers import SentenceTransformer, util
    HAS_SENTENCE_TRANSFORMERS = True
except ImportError:
    HAS_SENTENCE_TRANSFORMERS = False

try:
    import chromadb
    HAS_CHROMADB = True
except ImportError:
    HAS_CHROMADB = False

# Fallbacks and existing dependencies...
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
# ML MODELS INITIALIZATION
# =====================================================================
# We load a lightweight embedding model for taxonomy classification and semantic search
if HAS_SENTENCE_TRANSFORMERS:
    print("[ML Pipeline] Loading SentenceTransformer model (all-MiniLM-L6-v2)...")
    model = SentenceTransformer('all-MiniLM-L6-v2')
else:
    model = None

# Initialize Vector Database
if HAS_CHROMADB:
    chroma_client = chromadb.PersistentClient(path="./chroma_db")
    vector_collection = chroma_client.get_or_create_collection(name="steel_semantic_search")
else:
    vector_collection = None

# =====================================================================
# TAXONOMY (NOW POWERED BY DENSE EMBEDDINGS)
# =====================================================================
TAXONOMY_TERMS = {
    "Stainless Steel": "stainless steel austenitic martensitic tp304 tp316 sus304 a240 corrosion resistant",
    "Alloy Steel": "alloy steel machinery carbon scm440 sncm439 s45c harden tempered high strength",
    "Mild Steel": "mild steel structural carbon astm a36 s275 s355 universal beam column hollow section rebar",
    "Non-Ferrous": "copper brass bronze aluminum zinc lead continuous casting non-magnetic"
}

# Pre-compute taxonomy embeddings if ML is available
if HAS_SENTENCE_TRANSFORMERS:
    TAXONOMY_EMBEDDINGS = {k: model.encode(v, convert_to_tensor=True) for k, v in TAXONOMY_TERMS.items()}
else:
    TAXONOMY_EMBEDDINGS = {}


def classify_material_embeddings(raw_text: str, col_headers: list, page_num: int) -> tuple:
    """Uses Dense Vector Embeddings for Taxonomy Classification."""
    combined_text = (raw_text[:1000] + " " + " ".join(str(h) for h in col_headers)).lower()
    
    best_material = "Mild Steel"
    
    if HAS_SENTENCE_TRANSFORMERS and combined_text.strip():
        text_embedding = model.encode(combined_text, convert_to_tensor=True)
        max_score = -1.0
        
        for material, tax_emb in TAXONOMY_EMBEDDINGS.items():
            # Calculate Cosine Similarity
            score = util.cos_sim(text_embedding, tax_emb).item()
            if score > max_score:
                max_score = score
                best_material = material
    else:
        # Fallback keyword logic if ML is missing
        if "stainless" in combined_text or "tp304" in combined_text: best_material = "Stainless Steel"
        elif "alloy" in combined_text or "tempered" in combined_text: best_material = "Alloy Steel"
        elif "bronze" in combined_text or "copper" in combined_text: best_material = "Non-Ferrous"

    # Default structural heuristics based on headers
    category = "Miscellaneous"
    subcategory = "Other Profiles"
    prefix = "steel_misc"
    standard = "Standard"

    if "beam" in combined_text or "ub" in combined_text:
        category, subcategory, prefix = "Beams & Columns", "Universal Beams", "beam_universal"
    elif "pipe" in combined_text or "schedule" in combined_text:
        category, subcategory, prefix = "Pipes & Tubings", "Steel Pipes", "pipe_general"
    elif "plate" in combined_text or "thickness" in combined_text:
        category, subcategory, prefix = "Bars & Plates", "Steel Plates", "plate_structural"
    
    if "jis" in combined_text: standard = "JIS"
    elif "astm" in combined_text: standard = "ASTM"
    elif "bs" in combined_text: standard = "BS/EN"

    return best_material, category, subcategory, prefix, standard


# =====================================================================
# LAYOUT & READING ORDER DETECTION
# =====================================================================

def detect_reading_order_and_formulas(page_obj, document_id, page_num, cursor):
    """
    Simulates advanced layout detection by sorting elements geometrically (Reading Order).
    Detects and extracts equations/formulas from non-tabular text blocks.
    """
    words = page_obj.extract_words()
    # Sort top-to-bottom, then left-to-right
    words.sort(key=lambda w: (round(w['top'] / 10), w['x0']))
    
    text_blocks = []
    current_block = []
    last_bottom = 0
    
    for w in words:
        if current_block and (w['top'] - last_bottom > 15):
            text_blocks.append(" ".join(current_block))
            current_block = []
        current_block.append(w['text'])
        last_bottom = w['bottom']
    if current_block:
        text_blocks.append(" ".join(current_block))

    # Formula Detection Heuristics
    math_symbols = r'[\+\-\=\/\*\(\)σπθΔΣ]'
    for block in text_blocks:
        if "=" in block and re.search(math_symbols, block) and len(block) < 100:
            # Looks like an equation (e.g., I = bh^3/12)
            cursor.execute("""
                INSERT INTO extracted_formulas (document_id, page_number, formula_text)
                VALUES (?, ?, ?)
            """, (document_id, page_num, block))


# =====================================================================
# FIGURE & DIAGRAM EXTRACTION
# =====================================================================

def extract_figures(page_obj, document_id, page_num, cursor, output_dir="./extracted_figures"):
    """Detects and extracts images, charts, and structural cross-sections."""
    if getattr(page_obj, 'images', None):
        os.makedirs(output_dir, exist_ok=True)
        
        for idx, img in enumerate(page_obj.images):
            try:
                # Extract image bounding box
                x0, top, x1, bottom = img["x0"], img["top"], img["x1"], img["bottom"]
                width, height = x1 - x0, bottom - top
                
                # Filter out tiny logos or noise
                if width < 50 or height < 50:
                    continue
                
                # Crop and save the figure
                cropped = page_obj.within_bbox((x0, top, x1, bottom)).to_image(resolution=150)
                img_filename = f"doc_{document_id}_pg_{page_num}_fig_{idx}.png"
                img_path = os.path.join(output_dir, img_filename)
                cropped.save(img_path, format="PNG")
                
                cursor.execute("""
                    INSERT INTO extracted_figures (document_id, page_number, filepath, width, height)
                    VALUES (?, ?, ?, ?, ?)
                """, (document_id, page_num, img_path, width, height))
            except Exception as e:
                pass


# =====================================================================
# HASHING FOR DUPLICATE DETECTION
# =====================================================================

def compute_table_hash(headers: list, data_rows: list) -> str:
    """Cryptographic hash to ensure Camelot/pdfplumber overlap doesn't cause duplicates."""
    table_string = json.dumps({"headers": headers, "rows": data_rows}, sort_keys=True)
    return hashlib.md5(table_string.encode('utf-8')).hexdigest()


# =====================================================================
# TABLE SCHEMA & CONTINUITY MANAGEMENT (FROM PREVIOUS VERSION)
# =====================================================================

def flatten_recursive_headers(table_rows: list) -> tuple:
    if not table_rows or len(table_rows) < 2: return table_rows[0] if table_rows else [], 1
    num_cols = max(len(r) for r in table_rows)
    detected_depth = 1
    unit_patterns = r"^(mm|in|kg|lb|ft|cm|sec|mpa|hb|g/m|kg/m|\%|\/)$"
    for r_idx in range(1, min(4, len(table_rows))):
        row_values = [str(x).strip().lower() for x in table_rows[r_idx] if x is not None]
        if any(re.match(unit_patterns, val) or val == "" for val in row_values) and len([v for v in row_values if v]) > 0:
            detected_depth = r_idx + 1
        else: break
    header_block = [list(table_rows[r_idx]) + [""] * (num_cols - len(table_rows[r_idx])) for r_idx in range(detected_depth)]
    compressed_headers = []
    for col_idx in range(num_cols):
        path = []
        for row_idx in range(detected_depth):
            val = str(header_block[row_idx][col_idx]).strip()
            if not val and col_idx > 0: val = str(header_block[row_idx][col_idx - 1]).strip()
            if val and val not in path: path.append(val)
        compressed_headers.append("_".join(path) if path else f"col_{col_idx+1}")
    return compressed_headers, detected_depth

def parse_header_units(header: str) -> tuple:
    unit_regex = r"[\(\[\/](mm|in|kg|lb|ft|cm|sec|mpa|hb|g\/m|kg\/m|t|pc|pcs|wt|thk|od|id|dia|inches|meters)[\)\]]?"
    match = re.search(unit_regex, header, re.IGNORECASE)
    if match:
        return re.sub(unit_regex, "", header, flags=re.IGNORECASE).strip('_ '), match.group(1)
    return header, None

class FieldTypeInference:
    @staticmethod
    def clean_numeric_string(val: str) -> str:
        if not val: return ""
        cleaned = val.strip().replace('o', '0').replace('O', '0').replace('l', '1').replace('I', '1').replace('B', '8')
        return re.sub(r'[^\d\.\-]', '', cleaned)

    @staticmethod
    def infer_column_types(data_rows: list, num_cols: int) -> list:
        types = []
        for col_idx in range(num_cols):
            int_v, float_v, text_v = 0, 0, 0
            for row in data_rows:
                if col_idx >= len(row): continue
                val = str(row[col_idx]).strip()
                if not val or val in ("-", "—", "N/A"): continue
                cleaned = FieldTypeInference.clean_numeric_string(val)
                if not cleaned: text_v += 1; continue
                try: int(cleaned); int_v += 1
                except:
                    try: float(cleaned); float_v += 1
                    except: text_v += 1
            if (int_v + float_v + text_v) == 0 or text_v > (int_v + float_v) * 0.3: types.append("TEXT")
            elif float_v > int_v: types.append("REAL")
            else: types.append("INTEGER")
        return types

class TableContinuityResolver:
    def __init__(self):
        self.last_headers, self.last_table_name, self.last_page, self.last_category = None, None, None, None
    def evaluate_continuity(self, current_headers: list, current_category: str, current_page: int) -> bool:
        if not self.last_page or current_page != self.last_page + 1: return False
        if current_category != self.last_category or len(current_headers) != len(self.last_headers): return False
        overlap = set(current_headers).intersection(set(self.last_headers))
        return len(overlap) / len(current_headers) >= 0.70
    def update_state(self, table_name, headers, category, page_num):
        self.last_table_name, self.last_headers, self.last_category, self.last_page = table_name, headers, category, page_num

def consolidate_to_master_schema(conn, base_table_name: str, sanitized_headers: list, col_types: list) -> tuple:
    cursor = conn.cursor()
    master_table = f"cat_{base_table_name}"
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (master_table,))
    core_columns = ["id", "material_desc", "standard_name", "page_number", "confidence_score", "extra_attributes", "table_hash"]
    
    if not cursor.fetchone():
        col_defs = ["id INTEGER PRIMARY KEY AUTOINCREMENT", "material_desc TEXT", "standard_name TEXT", 
                    "page_number INTEGER", "confidence_score REAL", "extra_attributes TEXT", "table_hash TEXT UNIQUE"]
        primary_dims = ["size", "thickness", "width", "weight", "area", "diameter"]
        for h, t in zip(sanitized_headers, col_types):
            h_clean = h.replace("page_number", "page_num_val")
            if any(dim in h_clean for dim in primary_dims) and h_clean not in core_columns:
                col_defs.append(f"[{h_clean}] {t}")
                core_columns.append(h_clean)
        cursor.execute(f"CREATE TABLE [{master_table}] ({', '.join(col_defs)});")
        conn.commit()
    else:
        cursor.execute(f"PRAGMA table_info([{master_table}])")
        core_columns = [row[1] for row in cursor.fetchall()]
    return master_table, core_columns


# =====================================================================
# DATABASE SETUP (WITH NEW ML TABLES)
# =====================================================================

def init_advanced_database(db_path: str):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS documents (id INTEGER PRIMARY KEY, filename TEXT, page_count INTEGER);")
    cur.execute("CREATE TABLE IF NOT EXISTS pdf_pages (id INTEGER PRIMARY KEY, document_id INTEGER, page_number INTEGER, raw_text TEXT);")
    cur.execute("CREATE TABLE IF NOT EXISTS extracted_figures (id INTEGER PRIMARY KEY, document_id INTEGER, page_number INTEGER, filepath TEXT, width REAL, height REAL);")
    cur.execute("CREATE TABLE IF NOT EXISTS extracted_formulas (id INTEGER PRIMARY KEY, document_id INTEGER, page_number INTEGER, formula_text TEXT);")
    cur.execute("CREATE VIRTUAL TABLE IF NOT EXISTS pdf_pages_fts USING fts5(raw_text, content='pdf_pages', content_rowid='id');")
    conn.commit()
    return conn


# =====================================================================
# MAIN ML PIPELINE
# =====================================================================

def process_pdf_document(pdf_path: str, db_path: str):
    conn = init_advanced_database(db_path)
    cursor = conn.cursor()

    cursor.execute("INSERT INTO documents (filename, page_count) VALUES (?, ?)", (os.path.basename(pdf_path), 0))
    document_id = cursor.lastrowid
    continuity_resolver = TableContinuityResolver()

    # Set tracking to avoid duplicates across Camelot/pdfplumber
    seen_table_hashes = set()

    with pdfplumber.open(pdf_path) as pdf:
        pages_to_process = len(pdf.pages)
        cursor.execute("UPDATE documents SET page_count = ? WHERE id = ?", (pages_to_process, document_id))
        conn.commit()

        print(f"\n[ML Pipeline] Commencing semantic parsing on {pages_to_process} pages...")

        for page_idx in tqdm(range(pages_to_process), desc="Processing Pages"):
            page_num = page_idx + 1
            page_obj = pdf.pages[page_idx]
            raw_text = page_obj.extract_text() or ""

            # 1. LAYOUT ANALYSIS: Extract Figures, Reading Order, and Formulas
            extract_figures(page_obj, document_id, page_num, cursor)
            detect_reading_order_and_formulas(page_obj, document_id, page_num, cursor)

            # Store Text
            cursor.execute("INSERT INTO pdf_pages (document_id, page_number, raw_text) VALUES (?, ?, ?)", (document_id, page_num, raw_text))
            
            # 2. TABLE EXTRACTION
            tables_found = []
            try:
                tables = camelot.read_pdf(pdf_path, pages=str(page_num), flavor="lattice", suppress_stdout=True)
                tables_found = [t.data for t in tables if t.parsing_report.get("accuracy", 0) > 60.0]
            except: pass

            if not tables_found:
                try: tables_found = [t.extract() for t in page_obj.find_tables()]
                except: pass

            # 3. SEMANTIC PROCESSING & DB INSERTION
            for raw_table in tables_found:
                if len(raw_table) < 2: continue
                
                headers, header_depth = flatten_recursive_headers(raw_table)
                data_rows = raw_table[header_depth:]
                if not data_rows: continue

                # Duplicate Detection Hash
                tbl_hash = compute_table_hash(headers, data_rows)
                if tbl_hash in seen_table_hashes:
                    continue
                seen_table_hashes.add(tbl_hash)

                clean_headers_with_units = [parse_header_units(h) for h in headers]
                sanitized_headers = [re.sub(r'[^a-z0-9_]', '_', h[0].lower().strip()).strip('_') for h in clean_headers_with_units]
                units_metadata = {sanitized_headers[i]: clean_headers_with_units[i][1] for i in range(len(sanitized_headers)) if clean_headers_with_units[i][1]}

                # Embeddings-based Classification
                material, category, subcategory, table_prefix, standard = classify_material_embeddings(raw_text, sanitized_headers, page_num)

                is_continuation = continuity_resolver.evaluate_continuity(sanitized_headers, category, page_num)
                if is_continuation:
                    target_table_name = continuity_resolver.last_table_name
                    cursor.execute(f"PRAGMA table_info([{target_table_name}])")
                    existing_columns = [row[1] for row in cursor.fetchall()]
                else:
                    col_types = FieldTypeInference.infer_column_types(data_rows, len(sanitized_headers))
                    target_table_name, existing_columns = consolidate_to_master_schema(conn, table_prefix, sanitized_headers, col_types)

                col_types = FieldTypeInference.infer_column_types(data_rows, len(sanitized_headers))
                
                for row in data_rows:
                    insert_dict = {
                        "material_desc": subcategory, "standard_name": standard, 
                        "page_number": page_num, "confidence_score": 95.0, 
                        "table_hash": tbl_hash, "extra_attributes": {}
                    }
                    
                    row_string_for_vector_db = f"{material} {subcategory} {standard}. "

                    for h, val, col_type in zip(sanitized_headers, row, col_types):
                        val_str = str(val).strip() if val is not None else ""
                        val_stored = val_str
                        
                        if col_type in ("INTEGER", "REAL"):
                            val_stored = FieldTypeInference.clean_numeric_string(val_str)
                        if val_stored and h in units_metadata:
                            val_stored = f"{val_stored} {units_metadata[h]}"

                        row_string_for_vector_db += f"{h}: {val_stored}, "
                        
                        h_clean = h.replace("page_number", "page_num_val")
                        if h_clean in existing_columns: insert_dict[h_clean] = val_stored
                        else: insert_dict["extra_attributes"][h_clean] = val_stored

                    insert_dict["extra_attributes"] = json.dumps(insert_dict["extra_attributes"])
                    cols = list(insert_dict.keys())
                    
                    try:
                        cursor.execute(f"INSERT INTO [{target_table_name}] ({', '.join(cols)}) VALUES ({', '.join(['?']*len(cols))})", [insert_dict[k] for k in cols])
                        row_id = cursor.lastrowid
                        
                        # Vector DB Insertion (Semantic Search)
                        if vector_collection and row_string_for_vector_db.strip():
                            vector_collection.add(
                                documents=[row_string_for_vector_db],
                                metadatas=[{"table": target_table_name, "row_id": row_id}],
                                ids=[f"{target_table_name}_{row_id}"]
                            )
                    except sqlite3.IntegrityError:
                        pass # Hash constraint prevented duplicate insertion

                continuity_resolver.update_state(target_table_name, sanitized_headers, category, page_num)
                conn.commit()

    conn.close()
    print(f"\n[Success] ML Pipeline completed. Structured data in SQLite. Embeddings in ChromaDB.")


if __name__ == "__main__":
    print("=== Document AI Pipeline Diagnostics ===")
    print(f"SentenceTransformers (Embeddings): {'Loaded' if HAS_SENTENCE_TRANSFORMERS else 'Missing (pip install sentence-transformers)'}")
    print(f"ChromaDB (Vector Search): {'Loaded' if HAS_CHROMADB else 'Missing (pip install chromadb)'}")
    
    process_pdf_document("./YH_HandBook.pdf", "./steel_specifications.db")