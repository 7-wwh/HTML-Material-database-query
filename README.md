# Engineering Datasheet Query Engine

**Status:** Active development — hybrid JSON index + Firestore architecture
**Hosting:** GitHub Pages (static) + Firestore (live data)
**Data Source:** YH Handbook (260+ page steel engineering catalog)

Converts complex engineering datasheets from PDF → structured JSON → searchable web interface. After discovering that rule-based PDF-to-SQLite extraction is unreliable for heterogeneous engineering tables, the project pivoted to a document-based model: JSON as the master archive, Firestore for live online queries.

## Architecture

```text
                     GitHub Pages (static)
                             │
                ┌────────────┴────────────┐
                │                         │
        catalogue.json              index.html
        (directory tree,            (viewer UI)
         search metadata)
                │                         │
                ▼                         ▼
         User browses               User searches
         categories                 or filters
                │                         │
                └────────┬───────────────┘
                         │
                         ▼
                    Firestore
               (full datasheet content)
                         │
                         ▼
               Returns single document
               → rendered as HTML table
```

- **JSON index** lives on GitHub Pages (free, fast, version-controlled). Contains the directory tree, search metadata, and category structure. Small download (~50 KB).
- **Firestore** stores the full engineering datasheets. Only fetched when a user clicks a specific component. Single-document reads minimize Firestore quota usage.
- **Browser** renders everything as interactive HTML tables.

## Repository File Tree

```text
├── index.html              # Main viewer UI
├── Plumber/                # PDF extraction experiments (archive)
│   ├── Plumber_1.py .. Plumber_6.py
│   ├── Plumber.py
│   └── README.md
├── JSON Mapping/           # JSON-based extraction pipeline
│   ├── build_index.py      # Builds structured JSON index from docx
│   ├── YH_HandBook.json    # Master JSON (~10 MB)
│   └── README.md
├── database/               # Legacy SQLite databases
│   └── databases.json
├── page/                   # Source page images
│   ├── page_167.png
│   └── ...
└── README.md
```

## Repository File Tree

```text
├── index.html                   # Dynamic multi-DB frontend UI and engine driver
├── build_db.py                  # Python script parsing raw handbook data into SQLite
├── database/                    # Directory containing database assets
│   ├── databases.json           # Broadmost registry of all available databases
│   ├── handbook_steel.db        # Core plates and sheets handbook database
│   └── structural_sections.db   # (Optional example) Additional structural database
├── page/                        # Directory containing original source page images
│   ├── page_167.png             # Source image for Imperial Plates (Page 167)
│   ├── page_168.png             # Source image for Metric Plates (Page 168)
│   ├── page_172.png             # Source image for Cold Rolled Sheets (Page 172)
│   └── page_175.png             # Source image for Galvanised Sheets (Page 175)
└── README.md                    # Project documentation
```

## Pull Requests

Contributions are welcome. The JSON schema in `JSON Mapping/` and the Firestore ingestion pipeline are the active development areas.

## Project Timeline & Development History

### Phase 1: Conception (Day 1)
- **Draft idea**: Understand the problem — engineers need to query steel specification tables. Identify **GitHub Pages** as the hosting platform (zero-cost static hosting).
- **Quick prototype**: Build basic `index.html` + `main.js` that fetches small data from a `.db` file. Everything works perfectly for a small test case.

### Phase 2: Architecture Crossroad
Two competing approaches were considered:
1. **Split PDF into pages** → each page becomes its own `.db` file → frontend picks which `.db` to load
2. **Entire PDF → one large `.db`** → single unified query across all data

**Chosen: Path 2** — the ability to query everything together was deemed more important than the simplicity of per-page isolation.

### Phase 3: The Monolithic DB Attempt (FAIL)
- Attempted to extract the entire YH Handbook into a single `.db` using Python scripts (`Plumber/`)
- **Why it failed**:
  - AI agents could not produce a well-structured `.db` in a single attempt (cost/complexity issues)
  - Even custom Python scripts (`pdfplumber`, `Camelot`, `pdftotext`) could not reliably extract and classify tables due to extreme page-to-page layout variance
  - The rigid rectangular schema of SQLite (fixed columns per row) is fundamentally mismatched to engineering datasheets with merged cells, sub-tables, and hierarchical headers

### Phase 4: Pivot — Multi-DB by Sections
Split the PDF into logical sections, each section → its own `.db` file. Each `.db` is smaller, more focused, and easier to verify. The frontend dynamically loads the correct `.db` based on user selection using SQL.js + a manifest (`databases.json`). This is the architecture reflected in the current codebase.

### Phase 5: JSON Generation (Breakthrough)
An experimental branch explored converting `.docs` files directly to **`.json`** instead of `.db`. Results:
- **Very reliable** extraction (no table-boundary detection needed — docx has native table structure)
- **Very fast queries** (JSON parse + filter in-memory)
- **Docx is the wrong source** — the real bottleneck is PDF extraction, not the storage format

### Phase 6: Active Branch — Hybrid JSON Index + Firestore

After evaluating JSON (simple, fast, free) vs Firestore (online, scalable, queryable), the chosen architecture is **both**:

- **JSON index** on GitHub Pages — lightweight catalogue (~50 KB), instant load, version-controlled directory of all components
- **Firestore** for live datasheet content — single-document reads per component, minimal quota usage, no re-deploy needed for updates

**Firestore free tier limits** (per Google Cloud project):
| Resource | Limit |
|----------|-------|
| Stored data | 1 GiB |
| Document reads | 50,000/day |
| Document writes | 20,000/day |
| Document deletes | 20,000/day |
| Data transfer | 10 GiB/month |

For an engineering datasheet viewer, this is more than sufficient: a user browsing components would consume ~1-5 reads per session.

**Why not pure SQLite?** SQLite's rigid rectangular schema (fixed columns per row) cannot handle engineering tables with variable column counts, merged cells, sub-tables, and hierarchical headers. SQLite is excellent for transactional data but fundamentally mismatched to heterogeneous datasheets.

**Why not pure Firestore?** The JSON index on GitHub Pages eliminates the need to download or query the entire dataset on every visit. The 10 MB master JSON stays in the repo; the browser only loads the ~50 KB catalogue index.

### Phase 7: Future Roadmap

- [ ] **v0.4.0a** — Set up Firestore project, configure security rules, establish schema
- [ ] **v0.4.0b** — Write ingestion script to push JSON datasheets into Firestore collections
- [ ] **v0.4.0c** — Build GitHub Pages frontend: fetch catalogue.json → display directory tree → on click, fetch Firestore doc → render as HTML table
- [ ] **v0.4.0d** — Enhance doc→JSON pipeline: page number extraction, cross-document references, data sorting
- [ ] **v0.4.0e** — Search & filter: text search across catalogue, category filtering, material/standard filters
- [ ] **v0.5.0** — Split UI: **Login** (simple encryption), **Landing** (category selection → sub-directory drill-down), **Main Page** (compare components side-by-side, show source PDFs, cross-datasheet queries)
- [ ] **v0.6.0** — **Launch V1**, gather feedback, iterate toward V2

### Version Tracker

- [x] **v0.1.0** — Quick prototype: basic `index.html` + `main.js` fetching small `.db` data. Proved the concept works.
- [x] **v0.1.1** — Monolithic DB attempt: Plumber pipeline to extract entire YH Handbook into one `.db`. **FAILED** — page layout variance too extreme for rule-based parsing.
- [x] **v0.2.0** — Pivot to multi-DB by sections. SQL.js in-browser engine + `databases.json` manifest for dynamic `.db` loading.
- [x] **v0.2.1** — JSON dynamic manifest engine with multi-DB lazy loading and dynamic tables UI.
- [x] **v0.3.0** — `.docs` → `.json` generation. Proved document-based format is far more reliable than relational tables for this data.
- [x] **v0.3.1** — `JSON Mapping/build_index.py`: full table parser with multi-level header joining, forward-fill, section hierarchy tracking, and leftmost-column index for O(1) lookups.
- [ ] **v0.4.0** — Hybrid architecture: JSON catalogue index (GitHub Pages) + Firestore datasheet content. First online queryable engineering database.
- [ ] **v0.5.0** — Full UI split: login, category browser, comparison mode, cross-datasheet search.
- [ ] **v0.6.0** — Public launch V1.
