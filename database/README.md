# Structural Steel Handbook — Firestore Pipeline

Extracts 267 tables from the Yick Hoe structural steel handbook PDF, uploads them to Firestore (one collection per category), and provides tools to query and render individual pages.

## Pipeline

```
YH_HandBook_unrestricted.pdf
        │
        ▼ (PDF extraction — done externally)
        │
 raw_handbook.json         267 tables, each with {page, rows}
        │
        ▼
 recategorize_for_firestore.py
        │
        ├── firestore_export/<collection>.ndjson    Per-category NDJSON
        └── firestore_export/category_map.json      Page → collection reference
        │
        ▼
 upload_to_firestore.py
        │
        ▼
       Firestore (online-material-query-yh)
        │  Collections: i_beams, steel_piles, ms_angles, ...
        │  Documents:   page_014, page_062, ...
        │
        ├── pull_page_table.py       Print to terminal
        └── page_to_html.py          Generate standalone HTML
```

## Requirements

- Python 3.10+
- `pip install firebase-admin`
- Firebase service account key at `firebase-key.json` in the project root

## Scripts

### `recategorize_for_firestore.py`

Reads `raw_handbook.json` and groups pages into categories using `directory.json` (the reference hierarchy). Outputs one NDJSON file per Firestore collection and a `category_map.json`.

```bash
python3 recategorize_for_firestore.py
```

### `upload_to_firestore.py`

Uploads one NDJSON file (or all) to Firestore. Each page becomes a document with fields: `title`, `page`, `headers`, `rows`.

```bash
python3 upload_to_firestore.py --file firestore_export/i_beams.ndjson
python3 upload_to_firestore.py --all        # upload everything
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
| NDJSON | `firestore_export/*.ndjson` | One file per collection, each line a Firestore document |
| Category map | `firestore_export/category_map.json` | `{page: {collection, title}}` for reverse lookup |
| Firestore | 24 collections, 267 documents | Live queryable, one doc per page |
| HTML | `html_output/page_XXX.html` | Standalone display page |

## Firestore Schema

```
Collection: i_beams
  Document: page_014
    title:   "I-Beams"
    page:    14
    headers: [["Design Formulae for Beams"], ["Section", "Moment of Inertia", ...]]
    rows:    [["W6x12", "0.456", ...], ...]
```

The `rows` field stores the raw cell arrays. `headers` is an array of header-row arrays (multi-level headers preserved as separate rows).

## Notes

- Multi-column cells from the PDF extraction are merged into single strings — the HTML tool cannot perfectly reconstruct the original column layout.
- PDF extraction used Python pdfplumber. The raw output is committed to enable full reproducibility.
- Firestore project: `online-material-query-yh`
