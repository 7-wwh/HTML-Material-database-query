# Plumber — PDF-to-SQLite Steel Specification Pipeline

Extracts dimensional specification tables from the **YH Handbook** PDF and stores them in a structured, searchable SQLite database. The handbook contains steel product specifications (mild steel, stainless steel, alloy steel, non-ferrous metals) across ~260 pages of mixed-format tables.

---

## Build Process (Pipeline Architecture)

All versions follow the same core pipeline; what changes between versions is *how* each stage is implemented.

```
PDF Input
    │
    ▼
┌─────────────────────────────┐
│ 1. Preprocessing            │  DRM stripping, OCR (v3+)
└─────────────────────────────┘
    │
    ▼
┌─────────────────────────────┐
│ 2. Page Text Extraction     │  pdfplumber → pdftotext -layout → pytesseract
└─────────────────────────────┘
    │
    ▼
┌─────────────────────────────┐
│ 3. Page Skip Classification │  TOC, formula pages (v5+)
└─────────────────────────────┘
    │
    ▼
┌─────────────────────────────┐
│ 4. Table Extraction         │  Camelot → pdfplumber → layout-text parser (v3+)
└─────────────────────────────┘
    │
    ▼
┌─────────────────────────────┐
│ 5. Header Compression       │  Multi-level hierarchical header flattening
└─────────────────────────────┘
    │
    ▼
┌─────────────────────────────┐
│ 6. Taxonomoy Classification │  Material/category/subcategory detection
└─────────────────────────────┘
    │
    ▼
┌─────────────────────────────┐
│ 7. Table Naming & Consolid. │  Group tables with matching schemas
└─────────────────────────────┘
    │
    ▼
┌─────────────────────────────┐
│ 8. SQLite Insert & Indexing │  Create/append cat_* tables, register metadata
└─────────────────────────────┘
    │
    ▼
SQLite Database (.db)
```

---

## Version History & Key Differences

### Plumber.py (Latest, 852 lines) — pdfplumber-only + images
- **Engine**: pdfplumber only (two strategies: lines → text)
- **No Camelot, no OCR, no DRM bypass, no pdftotext**
- **Taxonomy**: Full taxonomy with page-number heuristics (same as v1)
- **Table naming**: `cat_{prefix}` with versioned variants
- **New feature**: Image extraction via PyMuPDF (fitz) — stores PDF images to disk + `pdf_images` table
- **DB**: Includes `pdf_chunks` populated with overlapping chunks; `documents` table
- **Output**: `YH_HandBook.db`
- **Standard detection**: Removed KS/STKM from `_detect_standard()`

### Plumber_6.py (1090 lines) — Raw content-driven (no taxonomy)
- **Engine**: Camelot → pdfplumber → layout-text parser (full fallback chain)
- **Taxonomy**: **Removed entirely.** Tables are named directly from PDF header text via `_derive_table_title_from_headers()`
- **Simplified registry**: No material/category/subcategory columns — stores `raw_table_title` and `table_name` only
- **Resume/checkpoint**: `get_or_create_document()` — can resume from last completed page on re-run
- **Extraction**: `clean_extracted_table_raw()` — minimal cleaning, no header compression, no forward-fill
- **Output**: `steel_specifications_raw.db`
- **Schema**: `pdf_pages` gains `extraction_status` column; registry loses taxonomy columns
- **Cross-page continuity**: Improved — iterates through all tables on the page, not just the first

### Plumber_5.py (1510 lines) — Feature-complete, most fixes
- **5 specific fixes**:
  1. `pdftotext -layout` for text extraction (fixes CenturyGothic spacing artifacts)
  2. Page content classifier — skip TOC dividers and formula/derivation pages
  3. Fuzzy column matching with 80% positional threshold (reduces fragmented `_v2…_vN` tables)
  4. Layout-text fallback parser — recovers ~30-50 additional table pages
  5. Deduplication guard — prevents re-indexing same file
- **Taxonomy**: `TableClassifier` class, `_MATERIAL_SIGNALS` content-based detection (no hardcoded page numbers)
- **Full preprocessing**: DRM bypass, OCR (ocrmypdf + pytesseract), restriction removal
- **Output**: `steel_specifications_v5.db`

### Plumber_4.py (1355 lines) — Content-based taxonomy, cross-page continuity
- **Taxonomy refactored**: Removed hardcoded page-number heuristics; replaced with `_MATERIAL_SIGNALS` regex patterns
- **`TableClassifier`**: Per-document instance (no global state leaking)
- **Cross-page continuity**: Merges tables that span across pages
- **Header compression**: Arbitrary-depth recursive multi-level merge
- **Camelot accuracy**: Raised from 60 → 75 (fewer misaligned cells)
- **`pdf_chunks`**: Created but **not populated** (schema placeholder)
- **Output**: `steel_specifications.db`

### Plumber_3.py (1134 lines) — Camelot primary engine, OCR, DRM bypass
- **Major engine change**: Camelot (lattice + stream) as primary, pdfplumber as fallback
- **New preprocessing**: pdfminer DRM monkeypatch, pikepdf/pypdf restriction removal, ocrmypdf OCR for scanned PDFs, pytesseract page-text fallback
- **Forward-fill**: `forward_fill_merged_cells()` for spanning/merged cells
- **Critical fix**: Header matching changed from `set()` to exact list comparison (set() ignored column order, corrupting INSERTs)
- **Registry**: Gains `extraction_strategy` column
- **Standard detection**: Extracted into `_detect_standard()` helper
- **Entry**: `process_pdf_document()` + `run_diagnostics()`

### Plumber_2.py (993 lines) — Identical to v1
- Code identical to Plumber_1.py; preserved as a checkpoint.

### Plumber_1.py (993 lines) — First working version
- **Engine**: pdfplumber only
- **Taxonomy**: Global `CURRENT_MATERIAL_CONTEXT` state variable
- **Table matching**: `set()` equality (order-insensitive, bug: could mix up column order on INSERT)
- **Table naming**: `cat_{prefix}` / `cat_{prefix}_v2` etc.
- **DB features**: FTS5 full-text search, overlapping text chunks for future RAG
- **No images, no OCR, no Camelot**

---

## Common Features (All Versions)

- **SQLite schema**: `documents`, `pdf_pages`, `pdf_chunks`, `extracted_tables_registry`, `pdf_errors`, `pdf_pages_fts` (FTS5 virtual table)
- **Column sanitization**: `sanitize_identifier()` converts raw headers to safe SQLite identifiers
- **Header deduplication**: `sanitize_column_headers()` handles duplicate column names
- **Rectangularization**: `clean_extracted_table()` pads/shortens rows to uniform width
- **Page tracking**: Every data row gets `page_number` appended as the last column

---

## Supporting Files

### merge_split_cells.py
Post-processing script that merges text cells incorrectly split across adjacent columns. Uses heuristic detection (alphanumeric boundary chars, case consistency, space ratio) and iteratively merges until no more splits are found (max 15 passes per table). Operates on `cat_*` tables.

### .gitignore
Ignores `.db`, `.pdf`, `__pycache__/`, `*.pyc` — keeps the repo clean of generated artifacts.

### images/
Output directory for extracted images (used only by `Plumber.py`).

---

---

## Author's Learnings (3-Day Post-Mortem)

### Verdict: It does not work reliably

After 3 days of iterative development across 7 versions, the fundamental conclusion is that **purely script-based PDF table extraction is not viable for complex engineering datasheets** like the YH Handbook. Every page has a different layout, column alignment, header depth, and formatting. Without human or AI intervention at each extraction step, the output is too noisy to trust.

### Root Cause: Header extraction failure

The single biggest reason for failure is the **inability to reliably extract the correct column and row headers**. In steel specification tables, the headers carry all the semantic meaning — "Depth (mm)", "Width (mm)", "Thickness (mm)", "Weight (kg/m)", grade designators like "S45C", standard codes like "JIS G 3101". When the parser misaligns or mislabels a single column, the entire table becomes useless. No amount of post-processing or fuzzy matching can fix a fundamentally misparsed structure.

### SQLite vs. NoSQL — wrong tool for this job

SQLite (relational) forces a **fixed rectangular grid**: every row must have the same columns. Engineering datasheets are not rectangular:

- They have **sub-tables** (e.g., a flange table nested inside a pipe table)
- They have **cross-references** (e.g., a weight formula that references a beam dimension on another page)
- They have **merged cells**, **blank spanning rows**, **hierarchical headers** 3+ levels deep
- Column count and meaning **change between adjacent rows**

A document/NoSQL model (MongoDB, or even a graph DB) would handle this far better — allowing nested documents, variable schemas per row, and flexible cross-references. The rigid `CREATE TABLE (col1 TEXT, col2 TEXT, ...)` model is fundamentally mismatched to the input data.

### What would actually work

A hybrid approach combining:

1. **Computer vision / layout ML** (e.g., LayoutLM, table-transformer) to detect table boundaries, column regions, and header hierarchies
2. **LLM-based cell classification** to label what each column actually represents
3. **NoSQL / document storage** to preserve the variable-depth structure without forcing rectangularity
4. **Human-in-the-loop verification** on the extracted header row before bulk row import

Pure rule-based PDF parsing (Camelot, pdfplumber, pdftotext) reaches its ceiling fast when the input is as heterogeneous as a multi-hundred-page engineering catalog.

## Quick Reference

| File | Lines | Engine | Taxonomy | OCR/DRM | Page Skip | Continuity | Resume | Output DB |
|------|-------|--------|----------|---------|-----------|------------|--------|-----------|
| `Plumber.py` | 852 | pdfplumber only | Full + page nums | No | No | No | No | `YH_HandBook.db` |
| `Plumber_6.py` | 1090 | Camelot → pdfplumber → layout | **None** (raw) | Yes | Yes | Yes | Yes | `steel_specifications_raw.db` |
| `Plumber_5.py` | 1510 | Camelot → pdfplumber → layout | Full (content-based) | Yes | Yes | Yes | Guard only | `steel_specifications_v5.db` |
| `Plumber_4.py` | 1355 | Camelot → pdfplumber | Full (content-based) | Yes | No | Yes | No | `steel_specifications.db` |
| `Plumber_3.py` | 1134 | Camelot → pdfplumber | Full (page nums) | Yes | No | No | No | `steel_specifications.db` |
| `Plumber_2.py` | 993 | pdfplumber only | Full (page nums) | No | No | No | No | `YH_HandBook.db` |
| `Plumber_1.py` | 993 | pdfplumber only | Full (page nums) | No | No | No | No | `YH_HandBook.db` |
