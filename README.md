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

## Project History

```
v0.1 — Quick prototype
  └── index.html + main.js fetching small .db (proved concept)

v0.1.1 — Monolithic DB attempt (FAILED)
  ├── Plumber pipeline: PDF → single .db
  └── PDF layout variance × SQLite rigid schema

v0.2 — Multi-DB pivot
  ├── Split PDF sections → multiple .db files
  └── SQL.js + databases.json manifest

v0.3 — JSON generation (breakthrough)
  ├── .docx → .json pipeline (no table-boundary issues)
  ├── build_index.py: multi-level header parser, forward-fill, section tracking
  └── Document model > relational for engineering data

v0.4 (active) — Hybrid JSON + Firestore
  ├── GitHub Pages: catalogue.json (~50 KB, instant load)
  └── Firestore: full datasheet content, single-doc reads

v0.5 (planned) — UI split
  ├── Login (simple encryption)
  ├── Landing (category → sub-directory drill-down)
  └── Main Page (side-by-side comparison, source PDFs, cross-datasheet queries)

v0.6 (planned) — Public launch V1 → iterate → V2
```

## Architecture Decisions

**Why not pure SQLite?** Engineering datasheets have variable column counts, merged cells, sub-tables, and hierarchical headers. SQLite's rigid rectangular schema (fixed columns per row) cannot represent this without forcing everything into a lowest-common-denominator grid that loses semantic meaning.

**Why not pure Firestore?** The JSON index on GitHub Pages eliminates downloading or querying the entire dataset on every visit. The 10 MB master JSON stays in the repo; the browser only loads the ~50 KB catalogue index. A hybrid keeps the UI instant while Firestore handles live data on demand.

**Firestore free tier** (per Google Cloud project):

| Resource | Limit |
|----------|-------|
| Stored data | 1 GiB |
| Document reads | 50,000/day |
| Document writes | 20,000/day |
| Document deletes | 20,000/day |
| Data transfer | 10 GiB/month |

~1-5 reads per user session. More than sufficient for an engineering catalogue viewer.

## Roadmap

- [ ] **v0.4.0a** — Set up Firestore project, configure security rules, establish schema
- [ ] **v0.4.0b** — Write ingestion script to push JSON datasheets into Firestore collections
- [ ] **v0.4.0c** — Build GitHub Pages frontend: fetch catalogue.json → display directory tree → on click, fetch Firestore doc → render as HTML table
- [ ] **v0.4.0d** — Enhance doc→JSON pipeline: page number extraction, cross-document references, data sorting
- [ ] **v0.4.0e** — Search & filter: text search across catalogue, category filtering, material/standard filters
- [ ] **v0.5.0** — UI split: login, landing with category drill-down, comparison view
- [ ] **v0.6.0** — Launch V1, iterate toward V2
