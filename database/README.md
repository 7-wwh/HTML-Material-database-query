# Structural Steel Handbook — Document Parsing & Firestore Pipeline

Parses 267 tables from the Yick Hoe structural steel handbook PDF into structured documents (one per data row), uploads them to Firestore, and provides tools to query and render individual pages.

## Pipeline

```
YH_HandBook_unrestricted.pdf
        │
        ▼ (PDF extraction — done externally)
        │
 raw_handbook.json              267 tables, each with {page, rows}
        │
        ▼
 parse_tables.py  +  schemas.py
        │  Schema-driven row extraction: 39 table-type definitions
        │  → one NDJSON file per schema (e.g. beam_dimensions.ndjson)
        │
        ├── ndjson_output/<schema>.ndjson    One doc per data row
        │
        ▼
 upload_to_firestore_ndjson.py
        │
        ▼
       Firestore (online-material-query-yh)
        │
        ├── pull_page_table.py       Print to terminal
        └── page_to_html.py          Generate standalone HTML
```

## Schema-Driven Parsing

Rather than storing raw page grids, the pipeline decomposes each table into per-row documents using a schema definition in `schemas.py`. Each schema describes:

- **Pages** — which handbook page(s) the schema applies to
- **Section pattern** — a regex that identifies the start of a new data row (the "section name") from the joined cell text
- **Skip header rows** — how many rows at the top of the page are headers
- **Footer pattern** — a regex that marks a row as footer (skipped)
- **Columns** — an ordered list of typed fields (name + unit)
- **`value_count`** — the expected number of space-delimited tokens after the section name

A row is parsed by extracting the section name via the section pattern, splitting the remainder into `value_count` tokens, and mapping them positionally to the column definitions. Continuation rows (rows without a section name) use the previous row's section.

39 schemas cover the full handbook, producing **~2000 documents** total.

## Requirements

- Python 3.10+
- `pip install firebase-admin`
- Firebase service account key at `firebase-key.json` in the project root

## Scripts

### `parse_tables.py`

Reads `raw_handbook.json`, applies all 39 schemas from `schemas.py`, and writes one NDJSON file per schema group.

```bash
python3 parse_tables.py
```

Output files: `ndjson_output/<schema_type>.ndjson`

### `upload_to_firestore_ndjson.py`

Uploads parsed NDJSON files to Firestore. Each document is a single data row mapped to its schema's typed fields.

```bash
python3 upload_to_firestore_ndjson.py --file ndjson_output/beam_dimensions.ndjson
python3 upload_to_firestore_ndjson.py --all        # upload everything
```

### `pull_page_table.py`

Pulls a page from Firestore and prints it as a pipe-delimited table to the terminal. Scans all collections for the given page number.

```bash
python3 pull_page_table.py --page 62
```

### `page_to_html.py`

Fetches a page from Firestore and generates a standalone HTML file styled like the original handbook — dark navy header with gold accents, warm paper background, serif body font. Opens in browser automatically.

```bash
python3 page_to_html.py --page 62          # generate + open
python3 page_to_html.py --page 34 --no-open  # generate only
```

Output files: `html_output/page_XXX.html`

## Data Flow

| Stage | Format | Description |
|-------|--------|-------------|
| Source PDF | `YH_HandBook_unrestricted.pdf` | Original scanned handbook |
| Raw JSON | `raw_handbook.json` | 267 pages with `{page, rows}` — rows are arrays of strings (merged multi-column cells) |
| Schema definitions | `schemas.py` | 39 `TableSchema` objects: section patterns, columns, value counts |
| Parsed NDJSON | `ndjson_output/*.ndjson` | One file per schema, each line a typed document (one per data row) |
| Firestore | 24 collections, ~2000 documents | Live queryable, one doc per row |
| HTML | `html_output/page_XXX.html` | Standalone display page (legacy) |

## Firestore Schema

```
Collection: beam_dimensions
  Document: p014_w6x12_0
    section:      "W6x12"
    weight_lb_ft: 12.0
    weight_kg_m:  17.86
    depth_mm:     152.4
    ...
    page:         14
```

Each document corresponds to a single data row from the handbook. Fields are typed: `float` values are parsed (handling European decimal commas, `--` markers, and stripped tolerance symbols).

## Edge Cases Handled

- **European decimal commas** — `4,5` is parsed as `4.5` (comma between digits converted to period)
- **Unicode fractions** — pipe nominal sizes like `½`, `1¼`, `6 ⅛` are recognised as section identifiers
- **Slash fractions** — inch-series designations like `1/8`, `3/8` are captured
- **Merged decimal numbers** — raw extraction artifacts like `2.9536.5` are auto-split into `2.953 6.5`
- **Continuation rows** — rows without a section name inherit the previous section
- **Tolerance markers** — `±` and trailing `*` are stripped before numeric parsing
- **Footer text** — "Applicable Tolerances", "YICK HOE", and other page-level footnotes are filtered out
- **Multi-table pages** — pages with multiple tables (e.g. pipe specs + cement lining) are handled by separate schemas

## Notes

- Multi-column cells from the PDF extraction are merged into single strings — the parser relies on whitespace-delimited tokens
- Each schema must have `value_count == len(columns)` — mismatches silently drop or misalign fields
- PDF extraction used Python pdfplumber. The raw output is committed to enable full reproducibility.
- Firestore project: `online-material-query-yh`
