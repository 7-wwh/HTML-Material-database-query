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

Rather than storing raw page grids, the pipeline decomposes each table into per-row documents. Two files work together:

- **`schemas.py`** — defines 39 `TableSchema` objects, one per table type (e.g. universal beam dimensions, pipe specs, channel properties)
- **`parse_tables.py`** — applies the schemas: reads `raw_handbook.json`, matches each page to its schema, extracts rows, and writes NDJSON

### `TableSchema` fields

| Field | Purpose | Example |
|---|---|---|
| `page_type` | Unique key and output filename | `"cs_pipe_sgp"` |
| `pages` | Which handbook page(s) this schema applies to | `[122]` |
| `section_pattern` | Regex extracting the row identifier from the joined cell text | `r"^(\d+(?:[¼½¾⅛])?)\s*"` |
| `skip_header_rows` | Number of leading rows to ignore (multi-level table headers) | `5` |
| `footer_pattern` | Regex — any row with a matching cell is skipped | `r"YICK HOE\|Tolerance"` |
| `value_count` | How many space-delimited tokens to expect per row | `8` |
| `columns` | Ordered list of `ColumnDef(name, type, unit)` | see below |

`value_count` must equal `len(columns)`. A mismatch drops or misaligns fields.

### How the parser works (`process_page` → `parse_row`)

For each page, the parser iterates over every row and calls `parse_row`, which runs this sequence:

```
1. Footer check?           row matches footer_pattern → skip
2. Join cells:             " ".join(cells) → one string
3. Extract section:        match section_pattern against joined string
   └─ matched?             → extract section name, rest = remaining text
   └─ not matched +        → section = previous_section, rest = full line
      previous_section set    (continuation row — no section name needed)
   └─ not matched + no        → skip (can't identify this row)
      previous_section
4. Fix merged decimals:    re.sub(r'\d\.\d{3}(?=\d)') → insert space
5. Split tokens:           rest.split() → list of strings
6. Validate token count:   len(tokens) < value_count → skip
7. Map to columns:         tokens[:value_count] → positional column mapping
8. Parse numerics:         "float" columns → parse_numeric(value)
9. Emit document:          {"section": "...", "od_mm": 10.5, ...}
```

`parse_numeric` handles three tricky formats that appear in the raw data:

- **European decimal comma** — `4,5` → `4.5`. A comma with 1–4 trailing digits is treated as decimal separator; other commas (thousands separators) are stripped.
- **Tolerance markers** — `±1,5` → `1.5`. The `±` character and trailing `*` are stripped before conversion.
- **Placeholder values** — `--` fails `float()` and is returned as-is (the string `"--"`).

### Step-by-step example

Schema `cs_pipe_sgp` targets page 122. Raw row 5 from the PDF extraction:

```
cells = ["6", "1/8", "10.5 0.413 2.0 0.079 0.282 0.419 25 360"]
```

The parser joins the cells:

```
"6 1/8 10.5 0.413 2.0 0.079 0.282 0.419 25 360"
```

The section pattern `^(\d+(?:\s+(?:\d*[¼½¾⅛]|\d+/\d+|\d+))?)` matches `"6 1/8"` — a nominal-mm/inch pair with a slash fraction. The rest is:

```
"10.5 0.413 2.0 0.079 0.282 0.419 25 360"
```

8 tokens, mapping to the 8 `ColumnDef`s:

| Index | Column | Value |
|---|---|---|
| 0 | `od_mm` | `10.5` |
| 1 | `od_in` | `0.413` |
| 2 | `wall_mm` | `2.0` |
| 3 | `wall_in` | `0.079` |
| 4 | `weight_lb_ft` | `0.282` |
| 5 | `weight_kg_m` | `0.419` |
| 6 | `test_pressure_kg` | `25` |
| 7 | `test_pressure_psi` | `360` |

Final document:

```json
{"section": "6 1/8", "_section_slug": "6_18", "od_mm": 10.5, "od_in": 0.413,
 "wall_mm": 2.0, "wall_in": 0.079, "weight_lb_ft": 0.282, "weight_kg_m": 0.419,
 "test_pressure_kg": 25.0, "test_pressure_psi": 360.0, "page": 122}
```

### Continuation rows

Many handbook tables split a single section across two rows. The first row has the section name; the second contains additional metric/imperial pairs. For example, DIN channel page 130:

```
Row 7:  "30 x 15  30 15 4 4.5 4.5 2 2.21 1.74 ..."  ← section="30 x 15"
Row 8:  "30 30 33 5 7 7 3.5 5.44 4.27 0.174 ..."    ← no section, continues row 7
```

Row 8 has no `"x"` in its joined text, so `section_pattern` returns no match. But `previous_section` is `"30 x 15"` (set by row 7), so the parser treats it as a continuation: the full line becomes the rest value, is split into tokens, and mapped to the same 19 columns.

### Schema diversity

Schemas vary widely to match the handbook's heterogeneous tables:

| Schema | Section pattern | Matches | `value_count` |
|---|---|---|---|
| `beam_dimensions` | `W\d+\s+\d+(?:\s*x\s*\d+(?:/\d+)?)?` | `W4 4 x 4 (102 x 102)` | 14 |
| `din_channel` | `\d+(?:\.\d+)?\s*x\s*\d+(?:\.\d+)?` | `30 x 15`, `50 x 25` | 19 |
| `cs_pipe_light_aa` | `(?:\d*[¼½¾⅛]|\d+(?:/\d+)?)` | `½`, `1¼`, `2½`, `5` | 8 |
| `cs_pipe_sgp` | `\d+(?:\s+(?:[¼½¾⅛]|\d+/\d+|\d+))?` | `6 1/8`, `8 ¼`, `10 3/8`, `25 1` | 8 |
| `u_channel_inch` | `C\d+(?:\.\d+)?\s*x\s*\d+(?:\.\d+)?` | `C3 x 4.1`, `C12 x 20.7` | 12 |
| `z_purlin` | `SZ \d+-\d+` | `SZ 100-16`, `SZ 250-25` | 7 |
| `c_purlin` | `SC\d+-\d+` | `SC100-16`, `SC200-25` | 6 |
| `cs_pipe_stk` | `\d{2,}(?:\.\d+)?` | `21.7`, `114.3`, `216.3` | 6 |

Note the `cs_pipe_stk` pattern requires **two or more leading digits** (`\d{2,}`). This prevents wall-thickness continuation rows like `2.3` from being falsely matched as new sections.

### Page-to-schema routing

`get_schema_for_page(page_num)` scans `ALL_SCHEMAS` (a flat list) and returns the first schema whose `pages` list includes the page number. If multiple schemas target the same page, only the first match is used. Each page should be claimed by exactly one schema.

The `process_all_pages` function iterates every page in `raw_handbook.json`, routes it, and collects all documents by `page_type`:

```python
for page_data in raw_data["tables"]:
    schema = get_schema_for_page(page_data["page"])
    if schema is None:
        continue
    docs = process_page(page_data, schema)
    docs_by_group.setdefault(schema.page_type, []).extend(docs)
```

### Output

Each schema produces an NDJSON file at `firestore_export/<page_type>.ndjson`. Every line is a complete document with typed fields, ready for Firestore upload. 39 schemas produce **~2000 documents** total.

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
