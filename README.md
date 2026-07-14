# Serverless Steel Handbook Query Engine

Deployment: GitHub Pages
Database: SQL.js (In-Memory SQLite)
Driver: CDN-loaded sql-wasm.js / sql-wasm.wasm

An ultra-lightweight, zero-cost, online-first database query engine built specifically to search, filter, and calculate technical specifications and physical weights from the Yick Hoe Steel Handbook (Pages 167-175).

This architecture eliminates local browser CORS and sandboxing restrictions by utilizing public Content Delivery Networks (CDNs) for the heavy engine files (sql-wasm.js and sql-wasm.wasm), loading the compiled database directly from your GitHub Pages host, and offering visual source handbook reference page downloads.

## How It Works (Online CDN & Assets Pipeline)

This streamlined workflow operates completely in-browser without requiring you to store massive binary engines in your repository:

```text
+------------------ Client Browser ---------------+           +--- CDN & GitHub Pages ---+
|                                                 |           |                          |
|  [ User Interface (HTML5/CSS/JS) ]              |           |                          |
|         │                                       |           |                          |
|         ▼ (Loads runtime from CDN)              |           |                          |
|   Fetches sql-wasm.js / wasm engine <───────────┼───────────┼── [ cdnjs.com (CDN) ]    |
|         │                                       |           |                          |
|         ▼ (Loads database on startup)           |           |                          |
|   Reads database/plates.db <────────────┼───────────┼── [ GitHub Pages CDN ]   |
|         │                                       |           | (Database/ folder)       |
|         ▼ (Initializes Engine)                  |           |                          |
|  [ SQL.js Database Instance (RAM) ]             |           |                          |
|         │                                       |           |                          |
|         ▼ (User queries or views source)        |           |                          |
|  Executes query or displays / downloads image <─┼───────────┼── [ page/ folder ]       |
|         │                                       |           |   (Source page PNGs)     |
|         ▼ (Parses result / renders source)      |           |                          |
|  [ HTML UI Updates (DOM Table & Page Viewer) ]  |           |                          |
|                                                 |           |                          |
+-------------------------------------------------+           +--------------------------+
```

*   **External Engine Bootstrapping:** The index.html file loads the SQL.js library from cdnjs. When initializing, the script points directly to the CDN hosting of sql-wasm.wasm, initializing the WebAssembly SQLite interpreter on the client side.
*   **Database Load:** On page initialization, the browser performs an asynchronous fetch request to grab the database from the `./Database/plates.db` path.
*   **Binary Processing:** The database is parsed as an ArrayBuffer and loaded into memory.
*   **Reference Page Engine:** When a user selects a table, the UI automatically links to the corresponding original handbook scan located inside the `page/` folder. This allows the user to cross-reference the raw scanned data directly on the screen or download it instantly as a high-quality PNG.

## Repository File Tree

Your repository is structured cleanly with specific folders allocated for database files and source materials:

```text
├── index.html               # Main user interface, query controller, and calculator
├── Database/                # Directory containing all available .db files
│   └── plates.db            # The compiled and optimized SQLite database file
└── README.md                # Project documentation
```

## Deployment Steps

Since browsers block binary loading on local file-system access (file://), this setup is optimized to be deployed directly onto GitHub Pages for user testing.

1.  **Prepare the Database:** Ensure your optimized `plates.db` file is placed into the `Database/` folder.
2.  **Commit to GitHub:** Push your `index.html`, `Database/`, and `README.md` to your GitHub Repository.
3.  **Enable GitHub Pages:** In your repository, go to Settings -> Pages. Select your main branch and hit Save.
4.  **Test Live:** Access your URL to search database properties.

## Version Tracker

- [x] v0.1.0 — CDN Architecture Transition, Database Configuration and Compiler Script (build_db.py)
- [x] v0.1.1 — Integrated database/ and page/ folder structures to support static page downloads
- [x] v0.1.2 — Removed raw database schemas pending final confirmation
- [ ] v0.2.0 — Live index.html Interface with dynamic handbook source viewer and page downloads
- [ ] v0.3.0 — Interactive table selectors and real-time search filters
- [ ] v0.4.0 — Multiplying calculator tool to calculate batch weights dynamically
