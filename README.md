# Serverless Steel Handbook Query Engine

**Deployment:** GitHub Pages
**Database:** SQL.js (In-Memory SQLite Multi-Database Engine)
**Driver:** CDN-loaded sql-wasm.js / sql-wasm.wasm
**Index Registry:** `database/databases.json`

An ultra-lightweight, zero-cost, online-first database query engine built specifically to search, filter, and calculate technical specifications and physical weights from the Yick Hoe Steel Handbook (Pages 167-175).

This expanded architecture features an in-browser index manager that reads a central JSON manifest on startup. This allows users to choose from various distinct steel databases on demand, which then mounts selected `.db` files into client memory dynamically.

## How It Works (Dynamic Multi-DB Pipeline)

This modular pipeline allows the system to remain highly scalable:

```text
+------------------ Client Browser ---------------+           +--- CDN & GitHub Pages ---+
|                                                 |           |                          |
|  [ User Interface (HTML5/CSS/JS) ]              |           |                          |
|         │                                       |           |                          |
|         ▼ (Pre-flight Load)                     |           |                          |
|   Fetches databases.json registry <─────────────┼───────────┼── [ database/databases.json ]
|         │                                       |           |   (Index of available DBs)
|         ▼ (User selects target DB)              |           |                          |
|   Fetches target .db file into RAM <────────────┼───────────┼── [ database/plates.db ] 
|         │                                       |           |   [ database/specs.db ]  
|         ▼ (Discovers schema via sqlite_master)  |           |                          |
|  [ SQL.js Database Instance (RAM) ]             |           |                          |
|         │                                       |           |                          |
|         ▼ (User queries or views source)        |           |                          |
|  Executes query or displays reference source <──┼───────────┼── [ page/ folder ]       |
|         │                                       |           |   (Source page PNGs)     |
|         ▼ (Parses result / renders source)      |           |                          |
|  [ HTML UI Updates (DOM Table & Page Viewer) ]  |           |                          |
|                                                 |           |                          |
+-------------------------------------------------+           +--------------------------+
```

*   **Manifest Pre-flight:** On startup, `index.html` reads `database/databases.json` to dynamically build cards or selection panels representing your different steel databases.
*   **WebAssembly Bootstrapping:** The SQL.js runtime is fetched from cdnjs, loading `sql-wasm.wasm` inside the client environment.
*   **Lazy DB Mount:** When a user clicks a database choice, the client fires a fetch request for that specific `.db` file path, loads the binary buffer into client RAM, and disposes of the previous database context to keep memory footprints low.
*   **Dynamic Schema Discovery:** The application queries the `sqlite_master` table to automatically identify tables and columns, allowing the search UI to adapt dynamically regardless of unconfirmed schemas.
*   **Visual Reference Sourcing:** The UI displays the associated handbook scan from the `page/` folder, with a dedicated button to download the original PNG page for offline viewing.

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

## Deployment Steps

1.  **Compile Databases:** Run your Python compiler scripts to output your SQLite `.db` binaries, and save them in the `database/` folder.
2.  **Edit Registry:** Ensure any new database files are registered in `database/databases.json` with matching reference images in the `page/` folder.
3.  **Commit to GitHub:** Push your clean file tree online to your repository.
4.  **Host Live:** Activate GitHub Pages under Repository Settings to view your serverless steel portal.

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

### Phase 5: Split Branch — JSON Generation (Promising)
An experimental branch explored converting `.docs` files directly to **`.json`** instead of `.db`. Results:
- **Very reliable** extraction (no table-boundary detection needed)
- **Very fast queries** (JSON parse + filter in-memory)
- This proved that a document-based format is better suited than relational tables for this data

### Phase 6: Active Branch — Firestore Online Database
Building on the JSON insight, the current active direction moves to **Firestore** (Google's serverless NoSQL document database). Benefits:
- **Multiple queries across datasets** — not constrained by loading one `.db` at a time
- **Document model** — each table/spec can have its own schema, handles merged cells and sub-tables natively
- **Online, always up-to-date** — no need to re-deploy GitHub Pages for data changes

### Phase 7: Future Roadmap

- [ ] **Step 1** — Set up Firestore database and configure access
- [ ] **Step 2** — Create script to ingest JSON data into Firestore collections
- [ ] **Step 3** — Successfully store and read data from Firestore via the frontend
- [ ] **Step 4** — Enhance doc→JSON script for better header/page-number extraction and data sorting
- [ ] **Step 5** — Build enhanced query layer: cross-datasheet lookups, pagination, filtering
- [ ] **Step 6** — Split UI into 3 sections: **Login** (`index.html`, simple encryption), **Landing** (main category selection → sub-directory query), **Main Page** (compare data, show related PDFs, cross-datasheet queries)
- [ ] **Step 7** — **Launch V1**, iterate on feedback, launch **V2**

### Version Tracker

- [x] **v0.1.0** — Quick prototype: basic `index.html` + `main.js` fetching small `.db` data. Proved the concept works.
- [x] **v0.1.1** — Monolithic DB attempt: Plumber pipeline to extract entire YH Handbook into one `.db`. **FAILED** — page layout variance too extreme for rule-based parsing.
- [x] **v0.2.0** — Pivot to multi-DB by sections. SQL.js in-browser engine + `databases.json` manifest for dynamic `.db` loading.
- [x] **v0.2.1** — JSON dynamic manifest engine with multi-DB lazy loading and dynamic tables UI.
- [x] **v0.3.0** — Split branch: `.docs` → `.json` generation. Proved document-based format is far more reliable than relational tables for this data.
- [ ] **v0.4.0** — Active branch: Firestore online database. Cross-dataset queries, NoSQL document model, no re-deploy needed for data changes.
