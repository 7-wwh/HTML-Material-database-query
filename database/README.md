# Structural Steel Handbook — Document Parsing & Firestore Pipeline

Parses 267 tables from the Yick Hoe structural steel handbook PDF into structured documents (one per data row), organizes them into a hierarchical category tree, and uploads them to Firestore.

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
        │  Schema-driven row extraction: 133 leaf definitions
        │  → 45 active collections, 1671 documents
        │
        ├── firestore_export/<collection>.ndjson
        │
        ▼
 organize_export.py  +  firestore_structure.txt
        │  Maps flat NDJSON files into a hierarchical category tree
        │
        ├── firestore_organized/<category>/<subcategory>/<collection>.ndjson
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

## Project Layout

```
database/
├── README.md                        This file
├── parse_tables.py                  Main parser (872 lines, 12 parser modes)
├── schemas.py                       133 leaf schema definitions (45 active)
├── organize_export.py               Organizes NDJSON into category tree
├── upload_to_firestore.py           Uploads to Firestore
├── firestore_structure.txt          Hierarchical category tree definition
├── layout_reference.txt             Parser status tracker
├── raw_handbook.json                267 extracted tables
├── YH_HandBook_unrestricted.pdf     Source PDF
├── directory.json                   Page-to-leaf index
├── firestore_export/                45 flat NDJSON files (flat layout)
├── firestore_organized/             45 NDJSON files in category tree
└── html_output/                    Generated HTML pages
```

### `firestore_organized/` — Category Tree

```
firestore_organized/
├── api_pipes.ndjson
├── hot_formed_hollow_sections.ndjson
├── gauge_table.ndjson
├── i_beams/
│   ├── safe_loads/
│   │   ├── slenderness_and_geometry_ratio_allowable_stress.ndjson
│   │   ├── stanchios_and_struts_allowable_stress.ndjson
│   │   └── safe_loads_for_grade_43_steel.ndjson
│   └── Dimensions_and_values/
│       ├── universal_beams_and_columns.ndjson
│       ├── light_beam_and_joist.ndjson
│       └── bearing_pile.ndjson
├── steel_piles/
│   ├── frodingham_steel_sheet_piling.ndjson
│   ├── larssen_steel_sheet_piling.ndjson
│   └── dimensions_and_properties/
│       ├── u_type.ndjson
│       └── z_type.ndjson
├── cold_formed_hollow_sections/
│   ├── square_metric.ndjson
│   ├── rectangular_metric.ndjson
│   ├── square_imperial.ndjson
│   └── rectangular_imperial.ndjson
├── pipes/
│   ├── bs_welded_steel_pipes.ndjson
│   ├── carbon_steel_for_general_structural.ndjson
│   ├── carbon_steel_for_scaffolding.ndjson
│   └── carbon_steel_for_ordinary_piping.ndjson
├── channels/
│   ├── plain_channels.ndjson
│   ├── lipped_channels.ndjson
│   ├── din_1026_channels.ndjson
│   ├── u_channels.ndjson
│   └── inch_series.ndjson
├── z_purlins/
│   └── z_purlins_high_tensile_galvanised.ndjson
├── c_purlins/
│   └── c_purlins_high_tensile_galvanised.ndjson
├── angles/
│   ├── equal_angles.ndjson
│   └── unequal_angles.ndjson
├── bars/
│   ├── flat_bars.ndjson
│   ├── bulb_flats.ndjson
│   └── square_deformed_and_round_bars.ndjson
├── plates/
│   ├── chequered_plates.ndjson
│   └── galvanised_steel_sheets_dimensions.ndjson
├── stainless_steel_products/
│   ├── round_bars_stainless.ndjson
│   ├── welded_channels_stainless.ndjson
│   └── sheets_plates_weights.ndjson
├── machinery_steel_products/
│   ├── carbon_steel_machinery.ndjson
│   ├── chromium_and_crmo_steels.ndjson
│   ├── nickel_chromium_steels.ndjson
│   └── cold_finished_free_cutting_steel.ndjson
└── non_ferrous_metals/
    ├── copper_round_hex_square_bars.ndjson
    ├── brass_round_hex_square_bars.ndjson
    └── brass_sheets.ndjson
```


## Schema-Driven Parsing

Rather than storing raw page grids, the pipeline decomposes each table into per-row documents. Two files work together:

- **`schemas.py`** — defines 133 `LeafSchema` objects (45 currently active), organized by `PageGroup` with shared structure for related tables (e.g. all I-beam dimension tables, all pipe spec tables)
- **`parse_tables.py`** — applies the schemas: reads `raw_handbook.json`, matches each page to its schema, extracts rows, and writes NDJSON

### `LeafSchema` fields

| Field | Purpose | Example |
|---|---|---|
| `page_type` | Unique key and output filename | `"universal_beams_and_columns"` |
| `pages` | Which handbook page(s) this schema applies to | `[37, 38, 39, 40]` |
| `section_pattern` | Regex extracting the row identifier from the joined cell text | `r"^(\d+(?:[¼½¾⅛])?)\s*"` |
| `skip_header_rows` | Number of leading rows to ignore (multi-level table headers) | `5` |
| `footer_pattern` | Regex — any row with a matching cell is skipped | `r"YICK HOE\|Tolerance"` |
| `value_count` | How many space-delimited tokens to expect per row | `8` |
| `columns` | Ordered list of `ColumnDef(name, type, unit)` | see below |

`value_count` must equal `len(columns)`. A mismatch drops or misaligns fields.

### Parser modes

`parse_tables.py` contains 12 distinct parser modes to handle the handbook's varied table layouts:

| Mode | Used for | Approach |
|---|---|---|
| `token_split` | Standard tables | Concatenate cells → split → match section key |
| `machinery` | JIS G4051/G4104 etc | Alternating JIS/AISI grade rows with chemical + mechanical ranges |
| `gauge_table` | SWG/BWG/BG/USG | Multi-row headers with gauge number identification |
| `scaffolding` | JIS G3444 | Multiple measurement columns per row |
| `dimensions` | Sheet/plate dimensions | Fractional and metric dimension pairs |
| *(plus 7 more specialized modes)* | | |

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

`parse_numeric` handles three tricky formats in the raw data:

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

Row 8 has no `"x"` in its joined text, so `section_pattern` returns no match. But `previous_section` is `"30 x 15"` (set by row 7), so the parser treats it as a continuation: the full line becomes the rest value, is split into tokens, and mapped to the same columns.

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

Each active schema produces an NDJSON file at `firestore_export/<page_type>.ndjson`. Every line is a complete document with typed fields, ready for Firestore upload. 45 active collections produce **1671 documents** total.

## Category Tree Organization

The `firestore_structure.txt` file defines a hierarchical category mapping from handbook page ranges to logical groups. The `organize_export.py` script copies each NDJSON file from `firestore_export/` into the corresponding subfolder under `firestore_organized/`, creating a browsable tree:

```
firestore_organized/
├── api_pipes/                  ← Top-level product group
├── pipes/
│   └── carbon_steel_for_general_structural/
├── i_beams/
│   └── Dimensions_and_values/
│       └── universal_beams_and_columns/
└── ...
```

Files whose leaf category is a single entry (`api_pipes`, `hot_formed_hollow_sections`, `gauge_table`) are placed at the root — they are top-level product groups with no further sub-categorization.

## Requirements

- Python 3.10+
- `pip install firebase-admin`
- Firebase service account key at `firebase-key.json` in the project root

## Scripts

### `parse_tables.py`

Reads `raw_handbook.json`, applies all 133 schemas from `schemas.py`, and writes NDJSON to `firestore_export/`.

```bash
python3 parse_tables.py
```

Output: 45 NDJSON files in `firestore_export/`

### `organize_export.py`

Copies NDJSON files from `firestore_export/` into the category tree defined by `firestore_structure.txt`.

```bash
python3 organize_export.py
```

Output: `firestore_organized/` with hierarchical subfolder structure.

### `upload_to_firestore_ndjson.py`

Uploads parsed NDJSON files to Firestore. Each document is a single data row mapped to its schema's typed fields.

```bash
python3 upload_to_firestore_ndjson.py --file firestore_export/beam_dimensions.ndjson
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
| Schema definitions | `schemas.py` | 133 `LeafSchema` objects (45 active): section patterns, columns, value counts |
| Parsed NDJSON | `firestore_export/*.ndjson` | 45 files, 1671 documents — one per data row |
| Organized NDJSON | `firestore_organized/**/*.ndjson` | Same 45 files in hierarchical category tree |
| Firestore | 45 collections, 1671 documents | Live queryable, one doc per row |
| HTML | `html_output/page_XXX.html` | Standalone display page (legacy) |

## Firestore Schema

```
Collection: universal_beams_and_columns
  Document: p037_w6x12_0
    section:      "W6x12"
    weight_lb_ft: 12.0
    weight_kg_m:  17.86
    depth_mm:     152.4
    ...
    page:         37
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
- **Dagger characters** — `†‡` stripped from numeric values
- **Smart quotes** — `'` and `'` stripped from numeric values

## Notes

- Multi-column cells from the PDF extraction are merged into single strings — the parser relies on whitespace-delimited tokens
- Each schema must have `value_count == len(columns)` — mismatches silently drop or misalign fields
- PDF extraction used Python pdfplumber. The raw output is committed to enable full reproducibility.
- Firestore project: `online-material-query-yh`
- 88 of 133 leaf schemas remain skipped (pages with tables not yet parsed) — tracked in `layout_reference.txt`
