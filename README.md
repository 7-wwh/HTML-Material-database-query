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

## Version Tracker

- [x] v0.1.0 — CDN Architecture Transition, Database Configuration and Compiler Script (build_db.py)
- [x] v0.1.1 — Integrated database/ and page/ folder structures to support static page downloads
- [x] v0.1.2 — Removed raw database schemas pending final confirmation
- [x] v0.2.0 — Developed JSON dynamic manifest engine with multi-DB lazy loading and dynamic tables UI
