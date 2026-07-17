# JSON Mapping — Structured Steel Specification Index

Converts the YH Handbook `.docx` export into a searchable JSON document database. Unlike the Plumber's SQLite approach (which failed due to rigid rectangular schemas), this JSON structure preserves the variable-width, nested nature of engineering datasheets and enables O(1) lookups via pre-built indexes.

---

## File Overview

| File | Purpose |
|------|---------|
| `build_index.py` | Reads the raw docx JSON, parses all 262 tables, builds indexes, writes final `YH_HandBook.json` |
| `YH_HandBook.json` | Final output — 6-key structured document with full search capability (~MB) |

---

## JSON Structure

```
YH_HandBook.json
├── document_info          Metadata (source file, counts)
├── content                Original paragraphs + tables in reading order
├── tables                 Parsed tables keyed by index (262 tables)
├── index                  Size/name lookup → {table_id, row_id}
├── index_by_section       Section browsing → tables + available sizes
└── search_index           Flat search entries (69,982 items)
```

### `document_info`

```json
{
  "filename": "YH_HandBook.docx",
  "total_paragraphs": 7161,
  "total_tables": 262,
  "total_search_entries": 69982
}
```

### `tables` — The Core Data

Each table is parsed from the docx with multi-level headers joined into unique column names. Rows are stored as key-value dicts:

```json
"173": {
  "section": "SPECIFICATIONS / SLIP-ON FLANGES (BS 10)",
  "headers": [
    "Nominal Pipe Size",
    "Outside Diameter OD",
    "STD", "STD_2", "XS", "XS_2",
    "Centre to Face",
    "Approx. Weight",
    "Approx. Weight_2"
  ],
  "num_rows": 17,
  "num_cols": 9,
  "rows": [
    {
      "Nominal Pipe Size": "1",
      "Outside Diameter OD": "33.4",
      "STD": "26.6",
      "STD_2": "3.4",
      "XS": "24.4",
      "XS_2": "4.5",
      "Centre to Face": "25.4",
      "Approx. Weight": "0.0998",
      "Approx. Weight_2": "0.129"
    },
    {
      "Nominal Pipe Size": "1¼",
      "Outside Diameter OD": "42.2",
      "STD": "35.0",
      "STD_2": "3.6",
      "XS": "32.4",
      "XS_2": "4.9",
      "Centre to Face": "31.8",
      "Approx. Weight": "0.169",
      "Approx. Weight_2": "0.223"
    }
  ]
}
```

Key design decisions:
- **Headers joined** from multi-level rows: e.g., a "Thickness" header under a "STD" parent becomes `"STD"` and `"STD_2"` (for the sub-header "T"). Duplicate names get `_2`, `_3` suffixes.
- **Rows are dicts**, not arrays — enables keyed access without remembering column position.
- **Section path preserved** via `section` (e.g. `"SPECIFICATIONS / SLIP-ON FLANGES (BS 10)"`) — built by tracking Heading 1/2/3 and all-caps headings in the docx.

Other table examples:

**Flat Bars** — a grid where width × thickness gives weight:
```json
"247": {
  "headers": ["Width", "Thickness", "Thickness_2", ..., "Thickness_11"],
  "rows": [
    {"Width": "1/2", "Thickness": "0.12", "Thickness_2": "0.24", ...},
    {"Width": "5/8", "Thickness": "0.15", "Thickness_2": "0.30", ...}
  ]
}
```

**Chemical Analysis** — standard comparison table:
```json
"2": {
  "headers": ["Quality", "Grade", "Tensile strength", "Tensile strength_2", "Tensile strength_3", "Min. yield stress", ...],
  "rows": [
    {"Quality": "JIS G 3106", "Grade": "SM 50", "Tensile strength": "72500/88500", ...}
  ]
}
```

### `index` — Fast Size/Name Lookup

Maps every unique leftmost column value to the exact `{table_id, row_id}` it appears in. This makes dimensional lookups O(1):

```json
"152": [
  {"t": 0, "r": 16},   // TOC reference
  {"t": 24, "r": 15},  // Row 15 in table 24
  {"t": 24, "r": 31},
  {"t": 27, "r": 40},
  {"t": 128, "r": 4},
  {"t": 128, "r": 5},
  {"t": 128, "r": 6},
  {"t": 129, "r": 4},
  {"t": 129, "r": 5},
  {"t": 129, "r": 6}
]
```

- Builds aliases for the second column (e.g. mm values alongside inch values)
- 3,678 unique keys covering every size, grade, and designation in the handbook
- To resolve: `tables[str(t)]["rows"][r]` gives you the full row instantly

### `index_by_section` — Section Browsing

Groups table IDs by section path, with pre-computed sorted size lists:

```json
"SPECIFICATIONS / SLIP-ON FLANGES (BS 10)": {
  "tables": [171, 172, 173, 174, 175],
  "sizes": ["1", "10", "12", "14", "16", "18", "1¼", "1½", "2", "2½", ...]
}
```

- 117 sections covering the full handbook
- Enables dropdown/category browsing without scanning all tables

### `content` — Original Reading Order

7161 items preserving the original document flow (paragraphs + tables interleaved). Used for:
- Full-text search across the entire handbook
- Displaying surrounding context for a matched table
- Building the section hierarchy

### `search_index` — Flat Search Entries

69,982 entries that mirror `content` but in a flat format optimized for text search:
```json
[
  {"type": "paragraph", "paragraph_index": 0, "text": "HANDBOOK"},
  {"type": "paragraph", "paragraph_index": 44, "text": "CONTENTS"},
  ...
]
```

---

## How This Enables Fast Query

| Query Type | Data Structure | Speed |
|-----------|---------------|-------|
| "Find all specs for size 152" | `index["152"]` → hash lookup → `tables[t]["rows"][r]` | O(1) |
| "Show all flanges sections" | `index_by_section` keys filtered by keyword | O(n) over 117 keys |
| "List available sizes for I-Beams" | `index_by_section["I-BEAMS"]["sizes"]` | O(1) |
| "Search text for 'tensile strength'" | Linear scan over `search_index` or `content` | O(n) over 70k items |
| "Get full row data for a size" | `tables[str(t)]["rows"][r]` — dict access by column name | O(1) |

The document model (dicts per row, flexible column counts) avoids the SQLite problem where every row must conform to a single rigid schema. A flat bar table with 12 "Thickness" columns and a flange table with 9 named columns coexist without issue.

---

## Build Pipeline

```
.docx export → JSON (raw docx structure)
                    │
                    ▼
           build_index.py
                    │
          ┌─────────┼─────────┐
          ▼         ▼         ▼
       tables    index    index_by_section
    (262 parsed  (3678    (117 sections
      tables)     keys)    with sizes)
```

`build_index.py`:
1. Loads the raw docx JSON
2. Tracks section hierarchy by scanning for Heading 1/2/3 and all-caps paragraphs
3. Parses each table: identifies header rows (detects unit rows), joins multi-level headers into unique column names, forward-fills blank leftmost cells
4. Builds the `index` by leftmost column value (plus mm alias from the second column)
5. Builds `index_by_section` grouping tables under their section paths
6. Writes the final compact JSON
