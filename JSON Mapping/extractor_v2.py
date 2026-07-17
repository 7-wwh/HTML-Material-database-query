"""
docx_tables_to_json.py
======================
Extracts tables from a .docx file with high accuracy and outputs a
Firestore-ready JSON structure.

Features:
 - Merged cell (colspan/rowspan) resolution via XML parsing
 - Multi-row header detection with unit-row merging
 - Left-column value inheritance for merged "group" rows
 - Section heading context (H1 → H2 → H3 ancestry chain)
 - Unique, deduplicated column names
 - Per-table Firestore collection path derived from section + table index
 - Full index by leftmost value + section index for fast Firestore queries
 - Compact JSON output  (no indentation flag available via --pretty)

Usage:
    python docx_tables_to_json.py INPUT.docx OUTPUT.json [--pretty]
"""

import argparse
import json
import os
import re
import sys
from copy import deepcopy
from zipfile import ZipFile

# ── lxml preferred; fall back to stdlib ElementTree ──
try:
    from lxml import etree as ET
    LXML = True
except ImportError:
    import xml.etree.ElementTree as ET
    LXML = False

# Word XML namespaces
NS = {
    "w":  "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "w14": "http://schemas.microsoft.com/office/word/2010/wordml",
    "r":  "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
}

def ns(tag: str) -> str:
    """Expand a prefixed tag like w:tbl to its Clark notation."""
    prefix, local = tag.split(":")
    return f"{{{NS[prefix]}}}{local}"


# ──────────────────────────────────────────────
# XML helpers
# ──────────────────────────────────────────────

def get_text(elem) -> str:
    """Collect all w:t text under elem, respecting w:delText exclusion."""
    parts = []
    for t in elem.iter(ns("w:t")):
        parts.append(t.text or "")
    return " ".join(parts).strip()


def get_attr(elem, attr: str, default=None):
    """Fetch a w: namespace attribute value."""
    return elem.get(ns(f"w:{attr}"), default)


# ──────────────────────────────────────────────
# Cell grid builder (handles merges)
# ──────────────────────────────────────────────

def build_cell_grid(tbl_elem):
    """
    Parse a w:tbl element and return a 2-D list of strings.
    Merged cells are expanded so every logical cell appears in the grid.

    Returns:
        grid      : list[list[str]]  – row-major 2-D array of cell text
        num_cols  : int
    """
    # First pass: collect raw rows and their merge hints
    raw_rows = []
    for tr in tbl_elem.findall(ns("w:tr")):
        raw_cells = []
        for tc in tr.findall(ns("w:tc")):
            text = get_text(tc)
            text = re.sub(r'\s+', ' ', text).strip()

            # span info
            tcPr = tc.find(ns("w:tcPr"))
            colspan = 1
            vmerge_restart = False
            vmerge_continue = False
            if tcPr is not None:
                gridSpan = tcPr.find(ns("w:gridSpan"))
                if gridSpan is not None:
                    colspan = int(get_attr(gridSpan, "val") or 1)
                vMerge = tcPr.find(ns("w:vMerge"))
                if vMerge is not None:
                    val = get_attr(vMerge, "val") or ""
                    if val == "restart":
                        vmerge_restart = True
                    else:
                        vmerge_continue = True  # blank val = continuation

            raw_cells.append({
                "text": text,
                "colspan": colspan,
                "vmerge_restart": vmerge_restart,
                "vmerge_continue": vmerge_continue,
            })
        raw_rows.append(raw_cells)

    if not raw_rows:
        return [], 0

    # Second pass: expand into flat grid, respecting colspan & vmerge
    # We need to know max_cols first
    # A rough upper bound:
    max_cols = max(sum(c["colspan"] for c in row) for row in raw_rows) if raw_rows else 0

    # grid[r][c] = text string (None = occupied by a span)
    grid = [[None] * max_cols for _ in range(len(raw_rows))]
    occupied = [[False] * max_cols for _ in range(len(raw_rows))]

    # Track last text per column for vmerge continuation
    last_text_per_col = [""] * max_cols

    for ri, raw_cells in enumerate(raw_rows):
        ci = 0  # column cursor
        cell_iter = iter(raw_cells)
        for cell in cell_iter:
            # Skip columns occupied by a row/colspan from above
            while ci < max_cols and occupied[ri][ci]:
                ci += 1
            if ci >= max_cols:
                break

            colspan = cell["colspan"]
            text = cell["text"]

            if cell["vmerge_continue"]:
                # Inherit from the row above
                text = last_text_per_col[ci]
                # Mark the colspan columns as occupied but store inherited text
                for dc in range(colspan):
                    if ci + dc < max_cols:
                        grid[ri][ci + dc] = text
                        last_text_per_col[ci + dc] = text
                        # Mark future rows if they too will vmerge (handled on their own turn)
                ci += colspan
                continue

            # Normal cell or vmerge restart
            for dc in range(colspan):
                col = ci + dc
                if col < max_cols:
                    grid[ri][col] = text
                    last_text_per_col[col] = text
                    if cell["vmerge_restart"]:
                        # Mark rows below as occupied until a non-continue vmerge
                        for future_ri in range(ri + 1, len(raw_rows)):
                            # peek at the corresponding raw cell in that row
                            # (we can't easily do this without the second pass, so
                            #  we rely on vmerge_continue marking above)
                            pass  # handled by vmerge_continue branch above

            ci += colspan

    # Strip trailing None columns
    # Replace any remaining None with ""
    result = []
    for row in grid:
        result.append([v if v is not None else "" for v in row])

    # Trim uniform empty columns on the right
    if result:
        while max_cols > 0 and all(row[max_cols - 1] == "" for row in result):
            max_cols -= 1
            result = [row[:max_cols] for row in result]

    return result, max_cols


# ──────────────────────────────────────────────
# Header detection helpers
# ──────────────────────────────────────────────

UNIT_RE = re.compile(
    r'^(in|mm|cm|ft|m|lb/ft|kg/m|kN|MPa|N/mm2|psi|ksi|kPa|'
    r'in2|in3|in4|cm2|cm3|cm4|%|—|–|-|yes|no|n/?a)$', re.I)

HEADER_KEYWORDS = [
    'size', 'specif', 'wall', 'unit', 'section', 'grade', 'quality',
    'composition', 'tensile', 'classification', 'standard', 'other test',
    'scope', 'application', 'chemical', 'property', 'type', 'nominal',
    'description', 'material', 'thickness', 'weight', 'width', 'height',
    'length', 'diameter', 'pressure', 'temperature', 'strength', 'class',
    'schedule', 'rating', 'alloy', 'temper', 'condition', 'item',
]


def looks_like_unit_row(row: list[str]) -> bool:
    """
    Return True if the row appears to be a units/sub-header row directly
    under a label row.  We are strict: most cells must be blank or named
    units (in, mm, psi, …).  Pure-numeric cells do NOT qualify as a units
    row because they are data.
    """
    if not row:
        return False
    checked = [v.strip() for v in row if v.strip()]
    if not checked:
        return True   # entirely blank row — could be a spacer
    hits = sum(1 for v in checked if UNIT_RE.match(v))
    # ≥60 % must be recognised unit tokens (blank cells are already excluded)
    return hits / len(checked) >= 0.6


def row_looks_like_labels(row: list[str]) -> bool:
    """
    Return True if a row appears to contain column labels (not data values).
    Heuristics:
      - Most cells are non-numeric text
      - Cells contain typical header keywords
      - Values tend to be short descriptive phrases
    """
    if not row:
        return False
    non_empty = [v.strip() for v in row if v.strip()]
    if not non_empty:
        return False

    # Count how many cells look like labels (non-purely-numeric, not units)
    label_hits = 0
    for v in non_empty:
        is_pure_number = bool(re.match(r'^[\d\.\,\/\-\s\(\)]+$', v))
        is_unit = bool(UNIT_RE.match(v))
        has_kw = any(kw in v.lower() for kw in HEADER_KEYWORDS)
        is_title_case = bool(re.match(r'^[A-Z][a-zA-Z\s\(\)\/\-]+$', v))
        is_allcaps_word = v.isupper() and len(v) >= 3
        if has_kw or (not is_pure_number and not is_unit and (is_title_case or is_allcaps_word)):
            label_hits += 1

    return label_hits / len(non_empty) >= 0.5


def detect_header_rows(grid: list[list[str]]) -> int:
    """
    Return the number of leading rows to treat as headers (0–3).
    Row 0 is a header only if it genuinely looks like column labels.
    Subsequent rows are added only if they look like units sub-headers.
    """
    if not grid:
        return 0

    if not row_looks_like_labels(grid[0]):
        # Row 0 looks like data — no header detected, generate synthetic names later
        return 0

    # Row 0 is a header.  Check row 1 for a units sub-row only.
    # We cap at 2 total header rows to avoid pulling data rows in.
    if len(grid) > 1 and looks_like_unit_row(grid[1]):
        return 2
    return 1


# ──────────────────────────────────────────────
# Column name builder
# ──────────────────────────────────────────────

def build_col_names(header_rows: list[list[str]], num_cols: int) -> list[str]:
    """
    Combine multi-row headers into unique column names.
    Skips blank-header repeat values to avoid noise.
    """
    col_names = []
    freq: dict[str, int] = {}

    for ci in range(num_cols):
        parts = []
        seen_parts: set[str] = set()
        for hr in header_rows:
            val = hr[ci].strip().replace('\n', ' ').replace('\t', ' ') if ci < len(hr) else ""
            val = re.sub(r'\s+', ' ', val).strip()
            if val and val not in seen_parts:
                parts.append(val)
                seen_parts.add(val)
        name = " / ".join(parts) if parts else f"col_{ci + 1}"
        name = re.sub(r'\s+', ' ', name).strip()

        # Deduplicate
        base = name
        if base in freq:
            freq[base] += 1
            name = f"{base}_{freq[base]}"
        else:
            freq[base] = 1
        col_names.append(name)

    return col_names


# ──────────────────────────────────────────────
# Section heading tracker
# ──────────────────────────────────────────────

class SectionTracker:
    """
    Walk body paragraphs and tables in document order, tracking H1/H2/H3
    and all-caps paragraph headings to build a section path for each table.
    """

    HEADING_STYLES = {
        "heading 1": 1,
        "heading 2": 2,
        "heading 3": 3,
        "heading1":  1,
        "heading2":  2,
        "heading3":  3,
        "title":     0,
    }

    def __init__(self):
        self._levels: list[str] = ["", "", "", ""]  # index = heading level 0-3

    def update(self, style: str, text: str) -> None:
        style_key = style.strip().lower()
        level = self.HEADING_STYLES.get(style_key)

        if level is not None:
            # Clear all deeper levels
            for i in range(level + 1, 4):
                self._levels[i] = ""
            self._levels[level] = text
            return

        # All-caps heuristic for documents without formal heading styles
        if (text.isupper() and len(text) >= 6
                and not text.startswith("*")
                and not re.search(r'\d', text[:8])
                and not text.endswith(":")
                and not text.endswith(")")):
            clean = re.sub(r'\s+\d+$', '', text).strip()
            if clean:
                if len(clean) > 14:
                    self._levels[1] = clean
                    self._levels[2] = ""
                    self._levels[3] = ""
                else:
                    self._levels[2] = clean
                    self._levels[3] = ""

    def path(self) -> list[str]:
        return [v for v in self._levels if v]

    def section_str(self) -> str:
        return " / ".join(self.path())


# ──────────────────────────────────────────────
# Paragraph style extractor
# ──────────────────────────────────────────────

def get_para_style(para_elem) -> str:
    pPr = para_elem.find(ns("w:pPr"))
    if pPr is None:
        return "Normal"
    pStyle = pPr.find(ns("w:pStyle"))
    if pStyle is None:
        return "Normal"
    return get_attr(pStyle, "val") or "Normal"


# ──────────────────────────────────────────────
# Main extraction
# ──────────────────────────────────────────────

def extract_tables(docx_path: str) -> dict:
    with ZipFile(docx_path) as zf:
        with zf.open("word/document.xml") as f:
            raw = f.read()

    # Parse XML
    if LXML:
        root = ET.fromstring(raw)
    else:
        raw_str = raw.decode("utf-8")
        # Strip namespace prefixes that confuse stdlib
        raw_str = re.sub(r'\sxmlns:\w+="[^"]*"', '', raw_str)
        raw_str = re.sub(r'<(\w+):', '<', raw_str)
        raw_str = re.sub(r'</(\w+):', '</', raw_str)
        root = ET.fromstring(raw_str)

    body = root.find(f".//{ns('w:body')}")
    if body is None:
        raise ValueError("No w:body found in document.xml")

    tracker = SectionTracker()
    tables_out: dict[str, dict] = {}
    table_idx = 0

    for child in body:
        tag = child.tag

        if tag == ns("w:p"):
            style = get_para_style(child)
            text = get_text(child)
            text = re.sub(r'\s+', ' ', text).strip()
            if text:
                tracker.update(style, text)

        elif tag == ns("w:tbl"):
            section_str = tracker.section_str()
            grid, num_cols = build_cell_grid(child)

            if not grid or num_cols == 0:
                table_idx += 1
                continue

            # Detect headers
            header_count = detect_header_rows(grid)
            header_rows = grid[:header_count]
            data_rows_raw = grid[header_count:]

            if header_count == 0:
                # No header detected — generate synthetic names
                col_names = [f"col_{i + 1}" for i in range(num_cols)]
            else:
                col_names = build_col_names(header_rows, num_cols)

            # Parse data rows with left-column value inheritance
            parsed_rows: list[dict] = []
            last_leftmost = ""

            for row in data_rows_raw:
                cells = list(row) + [""] * max(0, num_cols - len(row))

                # Left-column inheritance
                leftmost_val = cells[0].strip() if cells else ""
                if leftmost_val:
                    last_leftmost = leftmost_val
                elif last_leftmost:
                    cells[0] = last_leftmost
                else:
                    # Completely blank leading cell with no history — skip
                    continue

                # Skip entirely blank rows
                if not any(c.strip() for c in cells):
                    continue

                row_dict: dict[str, str] = {}
                for ci, col_name in enumerate(col_names):
                    val = cells[ci] if ci < len(cells) else ""
                    val = re.sub(r'\s+', ' ', val).strip()
                    row_dict[col_name] = val

                parsed_rows.append(row_dict)

            # Build a Firestore-friendly collection ID from section + index
            section_slug = re.sub(r'[^a-zA-Z0-9_-]', '_', section_str)[:80]
            collection_id = f"table_{table_idx:04d}" + (f"_{section_slug}" if section_slug else "")

            tables_out[str(table_idx)] = {
                "table_idx":     table_idx,
                "section":       section_str,
                "collection_id": collection_id,
                "headers":       col_names,
                "num_rows":      len(parsed_rows),
                "num_cols":      num_cols,
                "rows":          parsed_rows,
            }

            table_idx += 1

    return tables_out


# ──────────────────────────────────────────────
# Index builders
# ──────────────────────────────────────────────

def build_indexes(tables: dict) -> tuple[dict, dict]:
    """
    index          : leftmost-value → list of {t, r} pointers
    index_by_section : section → {tables: [...], sizes: [...]}
    """
    index: dict[str, list[dict]] = {}
    index_by_section: dict[str, dict] = {}

    for tidx_str, tdata in tables.items():
        tidx = int(tidx_str)
        headers = tdata["headers"]
        if not headers:
            continue

        leftmost_key = headers[0]
        mm_key = headers[1] if len(headers) > 1 else None
        if mm_key == leftmost_key:
            mm_key = None

        for row_idx, row in enumerate(tdata["rows"]):
            key = row.get(leftmost_key, "").strip()
            if not key:
                continue
            index.setdefault(key, []).append({"t": tidx, "r": row_idx})

            # Secondary alias (e.g. mm equivalent)
            if mm_key:
                mm_val = row.get(mm_key, "").strip()
                if mm_val and mm_val != key:
                    index.setdefault(mm_val, []).append({"t": tidx, "r": row_idx})

        # Section index
        sec = tdata["section"]
        if sec:
            entry = index_by_section.setdefault(sec, {"tables": [], "sizes": {}})
            entry["tables"].append(tidx)
            for row in tdata["rows"]:
                lv = row.get(leftmost_key, "").strip()
                if lv:
                    entry["sizes"][lv] = True

    # Finalise section index
    for sec in index_by_section:
        index_by_section[sec]["sizes"] = sorted(index_by_section[sec]["sizes"].keys())
        index_by_section[sec]["tables"] = sorted(set(index_by_section[sec]["tables"]))

    return index, index_by_section


# ──────────────────────────────────────────────
# Firestore batch format
# ──────────────────────────────────────────────

def to_firestore_batches(tables: dict) -> list[dict]:
    """
    Returns a list of Firestore-batch-ready documents.
    Each document maps to one table row.

    Format:
        {
          "collection": "<collection_id>",
          "doc_id":     "<row_index_padded>",
          "fields":     { col: val, ... },
          "meta": {
            "table_idx": int,
            "section":   str,
            "row_idx":   int
          }
        }
    """
    docs = []
    for tidx_str, tdata in tables.items():
        cid = tdata["collection_id"]
        for ri, row in enumerate(tdata["rows"]):
            docs.append({
                "collection": cid,
                "doc_id":     f"{ri:06d}",
                "fields":     row,
                "meta": {
                    "table_idx": tdata["table_idx"],
                    "section":   tdata["section"],
                    "row_idx":   ri,
                },
            })
    return docs


# ──────────────────────────────────────────────
# CLI entry point
# ──────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Extract tables from a .docx file → Firestore-ready JSON"
    )
    parser.add_argument("input",  help="Path to the .docx file")
    parser.add_argument("output", help="Path for the output .json file")
    parser.add_argument("--pretty", action="store_true",
                        help="Pretty-print JSON (larger file, easier to inspect)")
    args = parser.parse_args()

    if not os.path.isfile(args.input):
        print(f"ERROR: Input file not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    print(f"Extracting tables from: {args.input}", flush=True)
    tables = extract_tables(args.input)
    print(f"  → {len(tables)} tables found", flush=True)

    total_rows = sum(t["num_rows"] for t in tables.values())
    print(f"  → {total_rows} total data rows", flush=True)

    index, index_by_section = build_indexes(tables)
    print(f"  → {len(index)} index keys, {len(index_by_section)} sections", flush=True)

    firestore_docs = to_firestore_batches(tables)
    print(f"  → {len(firestore_docs)} Firestore documents", flush=True)

    output = {
        "meta": {
            "source_file":     os.path.basename(args.input),
            "total_tables":    len(tables),
            "total_data_rows": total_rows,
            "total_sections":  len(index_by_section),
        },
        "tables":            tables,
        "index":             index,
        "index_by_section":  index_by_section,
        "firestore_docs":    firestore_docs,
    }

    indent = 2 if args.pretty else None
    print(f"Writing JSON → {args.output}", flush=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=indent)

    size = os.path.getsize(args.output)
    print(f"Done. Output: {args.output} ({size:,} bytes / {size/1024/1024:.1f} MB)")


if __name__ == "__main__":
    main()