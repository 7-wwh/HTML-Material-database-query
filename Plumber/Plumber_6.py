import pdfplumber
import camelot
import sqlite3
import os
import sys
import re
import subprocess
import warnings
from datetime import datetime
from tqdm import tqdm
import logging

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
# PDFMINER DRM BYPASS
# =====================================================================
try:
    from pdfminer.pdfdocument import PDFDocument

    class SafeExtractableDescriptor:
        def __get__(self, instance, owner):
            return True
        def __set__(self, instance, value):
            pass

    PDFDocument.is_extractable = SafeExtractableDescriptor()
    print("[DRM Bypass] Successfully applied universal pdfminer DRM bypass.")
except Exception as e:
    print(f"[DRM Bypass] Failed (non-fatal): {e}")

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
# PDF RESTRICTION / DRM REMOVER
# =====================================================================

def strip_pdf_restrictions(input_path: str) -> str:
    base, ext = os.path.splitext(input_path)
    unrestricted_path = f"{base}_unrestricted{ext}"
    if os.path.exists(unrestricted_path):
        return unrestricted_path

    if HAS_PIKEPDF:
        try:
            with pikepdf.open(input_path, allow_overwriting_input=False) as pdf:
                pdf.save(unrestricted_path)
            print(f"  [Preprocessor] Stripped restrictions via pikepdf -> {unrestricted_path}")
            return unrestricted_path
        except Exception as e:
            print(f"  [Preprocessor] pikepdf failed: {e}")

    if HAS_PYPDF:
        try:
            reader = PdfReader(input_path)
            if reader.is_encrypted:
                reader.decrypt("")
            writer = PdfWriter()
            for page in reader.pages:
                writer.add_page(page)
            with open(unrestricted_path, "wb") as f:
                writer.write(f)
            print(f"  [Preprocessor] Stripped restrictions via pypdf -> {unrestricted_path}")
            return unrestricted_path
        except Exception as e:
            print(f"  [Preprocessor] pypdf fallback failed: {e}")

    return input_path


# =====================================================================
# OCR PREPROCESSOR
# =====================================================================

def apply_ocr_if_needed(input_path: str) -> str:
    base, ext = os.path.splitext(input_path)
    ocr_path = f"{base}_ocr{ext}"
    if os.path.exists(ocr_path):
        print(f"  [OCR Check] Found existing OCR'd file -> {ocr_path}")
        return ocr_path

    has_text = False
    try:
        with pdfplumber.open(input_path) as pdf:
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

    print("  [OCR Check] No text layer detected.")
    if HAS_OCRMYPDF:
        try:
            ocrmypdf.ocr(input_path, ocr_path, force_ocr=True, deskew=True, optimize=1)
            print(f"  [OCR Engine] Created text-layered PDF -> {ocr_path}")
            return ocr_path
        except Exception as e:
            print(f"  [OCR Engine] Failed: {e}")
    else:
        print("  [OCR Engine] WARNING: ocrmypdf not installed.")

    return input_path


# =====================================================================
# LAYOUT-AWARE TEXT EXTRACTION VIA pdftotext
# =====================================================================

def extract_page_text_layout(pdf_path: str, page_num: int) -> str:
    """
    pdftotext -layout preserves column alignment via whitespace padding.
    Used as supplement and for the layout fallback table parser.
    """
    try:
        result = subprocess.run(
            ["pdftotext", "-layout", "-f", str(page_num), "-l", str(page_num), pdf_path, "-"],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0:
            return result.stdout
    except Exception:
        pass
    return ""


# =====================================================================
# PAGE SKIP — formula/TOC pages only
# =====================================================================

_FORMULA_INDICATORS = re.compile(
    r"\b(RA\s*=|RB\s*=|Mmax\s*=|deflect|cantilever|propped|formulae?\b|derivat)\b",
    re.IGNORECASE,
)
_TOC_DIVIDER_PATTERN = re.compile(r"product\s+list", re.IGNORECASE)
_NUMERIC_DATA_ROW = re.compile(
    r"^\s*[\d.,\-]+\s+[\d.,\-]+\s+[\d.,\-]+",
    re.MULTILINE,
)


def _is_skippable_page(raw_text: str, layout_text: str) -> tuple[bool, str]:
    combined = (raw_text + "\n" + layout_text).strip()
    line_count = len([l for l in combined.splitlines() if l.strip()])

    if _TOC_DIVIDER_PATTERN.search(combined):
        return True, "TOC/product-list divider page"

    if line_count < 5 and len(combined) < 200:
        return True, "near-empty cover/chapter page"

    formula_hits = len(_FORMULA_INDICATORS.findall(combined))
    numeric_rows = len(_NUMERIC_DATA_ROW.findall(combined))
    if formula_hits >= 6 and numeric_rows == 0:
        return True, f"pure formula/derivation page (formula_hits={formula_hits})"

    return False, ""


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
        cur.execute("ALTER TABLE documents ADD COLUMN filepath TEXT;")

    cur.execute("""
        CREATE TABLE IF NOT EXISTS pdf_pages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_id INTEGER, page_number INTEGER,
            width REAL, height REAL, raw_text TEXT, layout_text TEXT,
            skipped INTEGER DEFAULT 0, skip_reason TEXT,
            extraction_status TEXT DEFAULT 'pending',
            FOREIGN KEY(document_id) REFERENCES documents(document_id)
        );
    """)
    cur.execute("PRAGMA table_info(pdf_pages);")
    pdf_pages_cols = {row[1] for row in cur.fetchall()}
    if "layout_text" not in pdf_pages_cols:
        cur.execute("ALTER TABLE pdf_pages ADD COLUMN layout_text TEXT;")
    if "extraction_status" not in pdf_pages_cols:
        cur.execute("ALTER TABLE pdf_pages ADD COLUMN extraction_status TEXT DEFAULT 'pending';")
        cur.execute("UPDATE pdf_pages SET extraction_status = 'done' WHERE extraction_status = 'pending';")

    cur.execute("""
        CREATE TABLE IF NOT EXISTS pdf_chunks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            page_id INTEGER, chunk_index INTEGER, chunk_text TEXT,
            FOREIGN KEY(page_id) REFERENCES pdf_pages(id)
        );
    """)

    # ── Registry now stores raw_table_title (the header text as-found) ──
    cur.execute("""
        CREATE TABLE IF NOT EXISTS extracted_tables_registry (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_id INTEGER, page_number INTEGER,
            table_index INTEGER,
            table_name TEXT,           -- safe SQLite identifier
            raw_table_title TEXT,      -- exact text from the PDF header row
            extraction_strategy TEXT,
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
    cur.execute("CREATE INDEX IF NOT EXISTS idx_registry_name ON extracted_tables_registry(table_name);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_registry_title ON extracted_tables_registry(raw_table_title);")

    conn.commit()
    return conn


def log_error(cursor, document_id: int, page_number: int, error_message: str):
    try:
        cursor.execute(
            "INSERT INTO pdf_errors (document_id, page_number, error_message) VALUES (?, ?, ?)",
            (document_id, page_number, str(error_message)),
        )
    except Exception:
        pass


# =====================================================================
# DOCUMENT RESUME CHECKPOINT
# =====================================================================

def get_or_create_document(cursor, pdf_path: str, filesize: int) -> tuple[int, int]:
    abs_path = os.path.abspath(pdf_path)
    cursor.execute("SELECT document_id FROM documents WHERE filepath = ?", (abs_path,))
    row = cursor.fetchone()

    if row:
        document_id = row[0]
        cursor.execute(
            """SELECT MAX(page_number) FROM pdf_pages
               WHERE document_id = ? AND extraction_status = 'done'""",
            (document_id,)
        )
        last_done = cursor.fetchone()[0]
        resume_from = (last_done + 1) if last_done else 1
        print(f"  [Resume] Found existing document_id={document_id}. "
              f"Last completed page: {last_done or 'none'}. Resuming from page {resume_from}.")
        return document_id, resume_from

    indexed_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
        INSERT INTO documents (filename, filepath, title, page_count, indexed_time, filesize)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (os.path.basename(pdf_path), abs_path, "PDF Document", 0, indexed_time, filesize))
    return cursor.lastrowid, 1


# =====================================================================
# TABLE NAMING — derived directly from the PDF header row
# =====================================================================

def _make_safe_identifier(raw: str, max_len: int = 60) -> str:
    """
    Convert any raw string into a valid SQLite identifier.
    - Lowercased
    - Non-alphanumeric runs → single underscore
    - Leading digit → prefixed with "t_"
    - Truncated to max_len
    No taxonomy mapping; no category injection.
    """
    if not raw or not str(raw).strip():
        return "unnamed"
    s = str(raw).strip().lower()
    s = re.sub(r'[^a-z0-9]+', '_', s)
    s = re.sub(r'_+', '_', s).strip('_')
    if s and s[0].isdigit():
        s = f"t_{s}"
    return s[:max_len] if s else "unnamed"


def _derive_table_title_from_headers(headers: list[str]) -> str:
    """
    Pick the best representative title from the first header row.
    Strategy:
      1. Join all non-empty cells with ' | ' to capture multi-column headers.
      2. If the result is longer than 120 chars, use only the first non-empty cell.
    This is stored as raw_table_title and used as the basis for the table name.
    """
    non_empty = [str(h).strip() for h in headers if str(h).strip()]
    if not non_empty:
        return "unnamed_table"
    joined = " | ".join(non_empty)
    if len(joined) <= 120:
        return joined
    return non_empty[0]


def get_or_create_raw_table(cursor, raw_title: str, col_headers: list[str]) -> str:
    """
    Derive a stable SQLite table name from the raw PDF header text.
    If a table with the same name already exists and has compatible columns,
    reuse it (continuation across pages). Otherwise append _v2, _v3, etc.
    Returns the resolved table_name.
    """
    base_name = _make_safe_identifier(raw_title)
    if not base_name or base_name == "unnamed":
        # Fallback: use first meaningful header cell
        for h in col_headers:
            s = _make_safe_identifier(h)
            if s and s != "unnamed":
                base_name = s
                break
        else:
            base_name = "table_unknown"

    counter = 1
    while True:
        table_name = base_name if counter == 1 else f"{base_name}_v{counter}"
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (table_name,)
        )
        if not cursor.fetchone():
            # Brand-new table name — safe to use
            return table_name

        # Table exists — check if columns are compatible (same logical table)
        cursor.execute(f"PRAGMA table_info([{table_name}])")
        existing_cols = [row[1] for row in cursor.fetchall()]
        safe_new_cols = [_make_safe_identifier(h) or f"col_{i}"
                         for i, h in enumerate(col_headers)]
        safe_new_cols.append("page_number")

        if _columns_compatible(existing_cols, safe_new_cols):
            return table_name  # Same table, append rows

        counter += 1  # Name collision with different schema → try _v2, _v3 …


def _columns_compatible(existing: list[str], incoming: list[str]) -> bool:
    """
    True if two column lists represent the same logical table.
    Ignores trailing _N dedup suffixes and whitespace.
    Requires ≥80% positional match.
    """
    ex = [c for c in existing if c != "page_number"]
    nw = [c for c in incoming  if c != "page_number"]
    if len(ex) != len(nw) or not ex:
        return False
    def _norm(s: str) -> str:
        s = re.sub(r'[\s_]+', '', s.lower())
        return re.sub(r'\d+$', '', s)
    matches = sum(1 for a, b in zip(ex, nw) if _norm(a) == _norm(b))
    return matches / len(ex) >= 0.80


# =====================================================================
# COLUMN HEADER SANITISATION
# =====================================================================

def sanitize_column_headers(raw_headers: list[str]) -> tuple[list[str], list[str]]:
    """
    Returns (safe_headers, raw_headers_preserved).
    safe_headers   — valid SQLite column identifiers (used for CREATE TABLE).
    The original text is stored in extracted_tables_registry.raw_table_title
    so nothing is lost.
    """
    safe_cols = []
    seen: dict[str, int] = {}
    raw_preserved = []

    for i, h in enumerate(raw_headers):
        raw_text = str(h).strip() if h is not None else ""
        raw_preserved.append(raw_text)

        safe = _make_safe_identifier(raw_text) or f"col_{i + 1}"
        if safe == "page_number":
            safe = "page_number_col"

        if safe in seen:
            seen[safe] += 1
            safe = f"{safe}_{seen[safe]}"
        else:
            seen[safe] = 0

        safe_cols.append(safe)

    safe_cols.append("page_number")
    return safe_cols, raw_preserved


# =====================================================================
# RAW TABLE CLEANING  — NO reordering, NO forward-fill, NO compression
# =====================================================================

def clean_extracted_table_raw(table: list, page_num: int) -> tuple[list, list]:
    """
    Minimal cleaning:
      - Strip leading/trailing whitespace from each cell.
      - Remove completely blank rows.
      - Pad short rows to the width of the widest row.
      - Append page_number as the last column on data rows.
      - Return (cleaned_rows, raw_header_cells)
    Deliberately does NOT:
      - Merge hierarchical headers
      - Forward-fill any cells
      - Reorder or rename columns
    """
    if not table:
        return [], []

    # Strip whitespace, keep everything else verbatim
    stripped = []
    for row in table:
        cleaned_row = [str(cell).strip() if cell is not None else "" for cell in row]
        if any(cell != "" for cell in cleaned_row):
            stripped.append(cleaned_row)

    if not stripped:
        return [], []

    max_cols = max(len(row) for row in stripped)

    # Pad all rows to uniform width
    padded = [row + [""] * (max_cols - len(row)) for row in stripped]

    header_row  = padded[0]
    data_rows   = padded[1:]

    # Append page_number to every data row
    final_data = [row + [page_num] for row in data_rows]

    return [header_row] + final_data, header_row


# =====================================================================
# CAMELOT TABLE EXTRACTION (PRIMARY ENGINE)
# =====================================================================

CAMELOT_STRATEGIES = [
    {
        "name": "camelot_lattice",
        "flavor": "lattice",
        "kwargs": {
            "copy_text":          ["h", "v"],
            "line_scale":         40,
            "process_background": False,
            "strip_text":         "\n",
        },
    },
    {
        "name": "camelot_lattice_bg",
        "flavor": "lattice",
        "kwargs": {
            "copy_text":          ["h", "v"],
            "line_scale":         40,
            "process_background": True,
            "strip_text":         "\n",
        },
    },
    {
        "name": "camelot_stream",
        "flavor": "stream",
        "kwargs": {
            "row_tol":    8,
            "column_tol": 4,
            "strip_text": "\n",
        },
    },
    {
        "name": "camelot_stream_loose",
        "flavor": "stream",
        "kwargs": {
            "row_tol":    15,
            "column_tol": 6,
            "strip_text": "\n",
            "edge_tol":   50,
        },
    },
]

CAM_MIN_ROWS     = 2
CAM_MIN_COLS     = 2
CAM_MIN_ACCURACY = 75.0


def _score_table(data: list) -> float:
    if not data:
        return 0.0
    rows = len(data)
    cols = len(data[0]) if rows else 0
    if rows < CAM_MIN_ROWS or cols < CAM_MIN_COLS:
        return 0.0
    total    = rows * cols
    filled   = sum(1 for r in data for c in r if c is not None and str(c).strip())
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

            data = cam_tbl.data
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
                same_shape  = abs(len(data[0]) - len(existing["data"][0])) <= 1
                if same_region and same_shape:
                    if score > existing["score"]:
                        existing["data"]     = data
                        existing["score"]    = score
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
# PDFPLUMBER FALLBACK ENGINE
# =====================================================================

PDFPLUMBER_STRATEGIES = [
    {
        "name": "plumber_lines_strict",
        "settings": {
            "vertical_strategy":   "lines", "horizontal_strategy": "lines",
            "snap_tolerance":      3,        "join_tolerance":      3,
            "text_x_tolerance":    3,        "text_y_tolerance":    3,
        },
    },
    {
        "name": "plumber_hybrid",
        "settings": {
            "vertical_strategy":   "text",   "horizontal_strategy": "lines",
            "snap_tolerance":      5,        "join_tolerance":      5,
            "text_x_tolerance":    12,       "text_y_tolerance":    5,
            "min_words_vertical":  3,
        },
    },
    {
        "name": "plumber_text_aligned",
        "settings": {
            "vertical_strategy":   "text",   "horizontal_strategy": "text",
            "snap_tolerance":      5,        "join_tolerance":      5,
            "text_x_tolerance":    12,       "text_y_tolerance":    5,
            "min_words_vertical":  3,
        },
    },
]

MIN_ROWS = 2
MIN_COLS = 2


def _plumber_is_useful(table: list) -> bool:
    if not table or len(table) < MIN_ROWS or not table[0] or len(table[0]) < MIN_COLS:
        return False
    data  = table[1:]
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
    total     = rows * cols
    filled    = sum(1 for r in raw_table for c in r if c is not None and str(c).strip())
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
            candidates.append({"raw": raw, "strategy": strategy["name"],
                                "bbox": tobj.bbox, "score": score})

    candidates.sort(key=lambda x: x["score"], reverse=True)
    accepted = []
    for cand in candidates:
        overlap = False
        for acc in accepted:
            iarea      = _intersection_area(cand["bbox"], acc["bbox"])
            if iarea > 0:
                cand_area = _get_area(cand["bbox"])
                acc_area  = _get_area(acc["bbox"])
                if (iarea / cand_area > 0.3) or (iarea / acc_area > 0.3):
                    overlap = True
                    if cand["score"] > acc["score"]:
                        acc.update(cand)
                    break
        if not overlap:
            accepted.append(cand)

    return [(item["raw"], item["strategy"]) for item in accepted]


# =====================================================================
# LAYOUT TEXT FALLBACK TABLE PARSER — adaptive gap thresholding
# =====================================================================

def _parse_layout_text_as_table(layout_text: str) -> list | None:
    lines      = [l for l in layout_text.splitlines() if l.strip()]
    if len(lines) < 3:
        return None

    data_lines = [l for l in lines if len(re.findall(r'\b[\d.,]+\b', l)) >= 2]
    if len(data_lines) < max(3, len(lines) * 0.4):
        return None

    max_len = max((len(l) for l in data_lines), default=0)
    if max_len < 10:
        return None

    def _gap_positions(subset: list, width: int, threshold_frac: float) -> set:
        density = [0] * (width + 1)
        for l in subset:
            for i, ch in enumerate(l[:width]):
                if ch != ' ':
                    density[i] += 1
        thresh = len(subset) * threshold_frac
        return {i for i, d in enumerate(density) if d <= thresh}

    mid         = max(len(data_lines) // 2, 1)
    upper_gaps  = _gap_positions(data_lines[:mid], max_len, 0.15)
    lower_gaps  = _gap_positions(data_lines[mid:], max_len, 0.15)
    shared_gaps = upper_gaps & lower_gaps
    if len(shared_gaps) < 5:
        shared_gaps = upper_gaps | lower_gaps

    sorted_gap = sorted(shared_gaps)
    col_starts = []
    in_gap     = True
    for i in range(max_len + 1):
        in_g = i in shared_gaps
        if not in_g and in_gap:
            col_starts.append(i)
        in_gap = in_g

    if len(col_starts) < 2:
        return None

    col_starts.append(max_len + 1)

    def split_by_cols(line: str) -> list:
        return [
            line[col_starts[i]:col_starts[i + 1]].strip()
            if col_starts[i] < len(line) else ""
            for i in range(len(col_starts) - 1)
        ]

    header_candidates = [l for l in lines if l.strip() and l not in data_lines]
    header_line       = header_candidates[0] if header_candidates else data_lines[0]

    rows = [split_by_cols(header_line)]
    for l in data_lines:
        row = split_by_cols(l)
        if any(c.strip() for c in row):
            rows.append(row)

    if len(rows) < 3 or len(rows[0]) < 2:
        return None

    total  = sum(len(r) for r in rows[1:])
    filled = sum(1 for r in rows[1:] for c in r if c.strip())
    if total == 0 or filled / total < 0.3:
        return None

    return rows


# =====================================================================
# CROSS-PAGE CONTINUITY
# =====================================================================

def _page_ends_mid_table(tables_found: list) -> tuple | None:
    if not tables_found:
        return None
    last_raw, last_strat = tables_found[-1]
    if not last_raw or len(last_raw) < 2:
        return None
    if len(tables_found) == 1 and "lattice" in last_strat:
        return (last_raw, last_strat)
    return None


def _try_merge_continuation(prev_tail: tuple | None, current_tables: list) -> list:
    if prev_tail is None or not current_tables:
        return current_tables

    prev_data, _   = prev_tail
    prev_header    = prev_data[0] if prev_data else []
    if not prev_header:
        return current_tables

    prev_col_count = len(prev_header)

    for tbl_idx, (cur_raw, cur_strat) in enumerate(current_tables):
        if not cur_raw:
            continue
        if len(cur_raw[0]) != prev_col_count:
            continue

        first_row   = [str(c).strip() for c in cur_raw[0]]
        alpha_count = sum(1 for c in first_row if c and re.match(r'^[A-Za-z\s/().]+$', c))
        if alpha_count >= len(first_row) * 0.6:
            continue

        numeric_count = sum(1 for c in first_row if re.match(r'^[\d.,\-\+]+$', c))
        if numeric_count < len(first_row) * 0.5:
            continue

        merged_data = [prev_header] + cur_raw
        print(f"  [Continuity] Merged cross-page continuation into table[{tbl_idx}] "
              f"({len(prev_data)-1} rows prev + {len(cur_raw)} rows current)")
        current_tables[tbl_idx] = (merged_data, f"continuation+{cur_strat}")
        return current_tables

    return current_tables


# =====================================================================
# INTEGRATED PIPELINE
# =====================================================================

def process_pdf_document(pdf_path: str, db_path: str):
    clean_pdf_path = strip_pdf_restrictions(pdf_path)
    clean_pdf_path = apply_ocr_if_needed(clean_pdf_path)

    conn   = init_db(db_path)
    cursor = conn.cursor()

    filesize = os.path.getsize(pdf_path)
    document_id, resume_from_page = get_or_create_document(cursor, pdf_path, filesize)
    conn.commit()

    prev_page_tail:    tuple | None = None
    skipped_pages      = 0
    pages_with_tables  = 0
    layout_fallback_hits = 0
    resumed_pages      = resume_from_page - 1

    try:
        with pdfplumber.open(clean_pdf_path) as pdf:
            pages_to_process = len(pdf.pages)
            cursor.execute(
                "UPDATE documents SET page_count = ? WHERE document_id = ?",
                (pages_to_process, document_id),
            )
            conn.commit()

            print(f"\n[Extraction Pipeline] '{pdf_path}' ({pages_to_process} pages), "
                  f"starting from page {resume_from_page}...")

            for page_idx in tqdm(range(pages_to_process), desc="Processing PDF Pages"):
                page_num = page_idx + 1
                if page_num < resume_from_page:
                    continue

                page_obj = pdf.pages[page_idx]

                # ── 1. Extract text ──────────────────────────────────
                try:
                    raw_text = page_obj.extract_text() or ""
                    if not raw_text.strip() and HAS_TESSERACT:
                        im       = page_obj.to_image(resolution=300)
                        raw_text = pytesseract.image_to_string(im.original)
                except Exception as txt_err:
                    raw_text = ""
                    log_error(cursor, document_id, page_num, f"Text extraction: {txt_err}")

                layout_text = extract_page_text_layout(clean_pdf_path, page_num)

                # ── 2. Page skip check ───────────────────────────────
                should_skip, skip_reason = _is_skippable_page(raw_text, layout_text)

                # ── 3. Persist page record ───────────────────────────
                try:
                    cursor.execute("""
                        INSERT INTO pdf_pages
                          (document_id, page_number, width, height,
                           raw_text, layout_text, skipped, skip_reason, extraction_status)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (document_id, page_num, page_obj.width, page_obj.height,
                          raw_text, layout_text,
                          1 if should_skip else 0,
                          skip_reason if should_skip else None,
                          "skipped" if should_skip else "pending"))
                    page_db_id = cursor.lastrowid
                    cursor.execute(
                        "INSERT INTO pdf_pages_fts(rowid, raw_text) VALUES(?, ?)",
                        (page_db_id, raw_text),
                    )
                except Exception as db_err:
                    log_error(cursor, document_id, page_num, f"Page DB insert: {db_err}")
                    continue

                if should_skip:
                    skipped_pages += 1
                    prev_page_tail = None
                    cursor.execute(
                        "UPDATE pdf_pages SET extraction_status='done' WHERE id=?",
                        (page_db_id,)
                    )
                    conn.commit()
                    continue

                # ── 4. Extract tables ────────────────────────────────
                try:
                    tables_found  = extract_tables_camelot(clean_pdf_path, page_num)
                    strategy_used = "camelot"
                    if not tables_found:
                        tables_found  = extract_tables_pdfplumber(page_obj)
                        strategy_used = "pdfplumber"

                    if not tables_found and layout_text.strip():
                        parsed = _parse_layout_text_as_table(layout_text)
                        if parsed:
                            tables_found  = [(parsed, "layout_text_parser")]
                            strategy_used = "layout_fallback"
                            layout_fallback_hits += 1

                except Exception as ext_err:
                    log_error(cursor, document_id, page_num, f"Table extraction: {ext_err}")
                    prev_page_tail = None
                    cursor.execute(
                        "UPDATE pdf_pages SET extraction_status='error' WHERE id=?",
                        (page_db_id,)
                    )
                    conn.commit()
                    continue

                # ── 5. Cross-page continuity ─────────────────────────
                tables_found   = _try_merge_continuation(prev_page_tail, tables_found)
                prev_page_tail = _page_ends_mid_table(tables_found)

                if tables_found:
                    pages_with_tables += 1

                # ── 6. Process each table ────────────────────────────
                for table_idx, (raw_table_data, strat_name) in enumerate(tables_found):
                    try:
                        # Raw clean: whitespace only, no reordering
                        cleaned_rows, raw_header_cells = clean_extracted_table_raw(
                            raw_table_data, page_num
                        )
                        if not cleaned_rows:
                            continue

                        header_row = cleaned_rows[0]
                        data_rows  = cleaned_rows[1:]

                        # Derive table name from the actual PDF header text
                        raw_title  = _derive_table_title_from_headers(raw_header_cells)
                        table_name = get_or_create_raw_table(cursor, raw_title, header_row)

                        # Sanitise column names for SQLite (keeps raw text in registry)
                        safe_headers, _ = sanitize_column_headers(header_row)

                        col_defs = [
                            f"[{h}] INTEGER" if h == "page_number" else f"[{h}] TEXT"
                            for h in safe_headers
                        ]
                        cursor.execute(
                            f"CREATE TABLE IF NOT EXISTS [{table_name}] "
                            f"({', '.join(col_defs)});"
                        )

                        placeholders = ", ".join(["?"] * len(safe_headers))
                        for row in data_rows:
                            if len(row) < len(safe_headers):
                                row += [""] * (len(safe_headers) - len(row))
                            cursor.execute(
                                f"INSERT INTO [{table_name}] VALUES ({placeholders})",
                                row[:len(safe_headers)]
                            )

                        # Registry: store raw title alongside safe name
                        cursor.execute("""
                            INSERT INTO extracted_tables_registry (
                                document_id, page_number, table_index,
                                table_name, raw_table_title,
                                extraction_strategy, num_rows, num_cols
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            document_id, page_num, table_idx + 1,
                            table_name, raw_title,
                            f"{strategy_used} ({strat_name})",
                            len(data_rows), len(header_row),
                        ))

                    except Exception as tbl_err:
                        log_error(cursor, document_id, page_num,
                                  f"Table {table_idx + 1} processing: {tbl_err}")

                # Mark page done AFTER all tables are committed
                cursor.execute(
                    "UPDATE pdf_pages SET extraction_status='done' WHERE id=?",
                    (page_db_id,)
                )
                conn.commit()

        print(f"\n[Success] Extraction complete!")
        print(f"  Pages total      : {pages_to_process}")
        print(f"  Pages resumed/skipped (already done): {resumed_pages}")
        print(f"  Pages skipped (formulae/TOC): {skipped_pages}")
        print(f"  Pages with tables: {pages_with_tables}")
        print(f"  Layout-text fallback hits: {layout_fallback_hits}")
        print(f"  Output DB        : '{db_path}'")

    except Exception as general_err:
        print(f"\n[Fatal Error] Pipeline interrupted: {general_err}")
        log_error(cursor, document_id, 0, f"Fatal pipeline error: {general_err}")
        try:
            conn.commit()
        except Exception:
            pass
    finally:
        conn.close()


def run_diagnostics():
    print("=== System Diagnostics & Pre-flight Check ===")
    print(f"Python Version   : {sys.version.split()[0]}")
    print(f"pdfplumber       : {'OK' if 'pdfplumber' in sys.modules else 'MISSING'}")
    print(f"camelot          : {'OK' if 'camelot' in sys.modules else 'MISSING'}")
    print(f"pikepdf          : {'OK' if HAS_PIKEPDF else 'Optional - not installed'}")
    print(f"pypdf            : {'OK' if HAS_PYPDF else 'Optional - not installed'}")
    print(f"ocrmypdf         : {'OK' if HAS_OCRMYPDF else 'MISSING (pip install ocrmypdf)'}")
    print(f"pytesseract      : {'OK' if HAS_TESSERACT else 'MISSING (pip install pytesseract)'}")
    try:
        subprocess.run(["pdftotext", "-v"], capture_output=True, check=True)
        print(f"pdftotext        : OK")
    except (FileNotFoundError, subprocess.CalledProcessError):
        print(f"pdftotext        : MISSING — install poppler-utils")
        print("                   Ubuntu/Debian: sudo apt-get install poppler-utils")
        print("                   macOS:         brew install poppler")
    print("===========================================\n")


if __name__ == "__main__":
    PDF_FILE  = "./YH_HandBook.pdf"
    SQLITE_DB = "./steel_specifications_raw.db"

    run_diagnostics()

    if os.path.exists(PDF_FILE):
        process_pdf_document(PDF_FILE, SQLITE_DB)
    else:
        print(f"Error: Target file '{PDF_FILE}' was not found.")