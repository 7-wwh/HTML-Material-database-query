# Serverless Steel Handbook Query Engine

**Deployment:** GitHub Pages  
**Database:** SQLite WASM  
**Driver:** sql.js-httpvfs

An ultra-lightweight, zero-cost, serverless database query engine built specifically to search, filter, and calculate technical specifications and physical weights from the Yick Hoe Steel Handbook (Pages 167-175).

Rather than executing queries on an active, expensive server-side Python environment, this application processes SQL directly inside the client's browser using WebAssembly.

## How It Works (The VFS & Range Request Pipeline)

Standard server-client databases require fetching the entire database or hosting an API server. This project leverages SQLite WebAssembly coupled with an HTTP Virtual File System (HTTP-VFS) to execute queries with sub-millisecond network overhead.

```text
+------------------ Client Browser ---------------+           +---- GitHub Pages CDN ----+
|                                                 |           |                          |
|  [ User Interface (HTML5/JS) ]                  |           |                          |
|         │                                       |           |                          |
|         ▼ (SQL Query String)                    |           |                          |
|  [ SQLite WASM Engine ]                         |           |                          |
|         │                                       |           |                          |
|         ▼ (Translated to Page Offsets)          |           |                          |
|  [ HTTP Virtual File System (VFS) ]             |           |                          |
|         │                                       |           |                          |
|         ▼ (Fetch with 'Range' Header)           |           |                          |
|    "GET /databases/handbook_steel.db"           |           |                          |
|     Headers: { Range: "bytes=5120-6143" } ──────┼──────────>│                          |
|                                                 |           |   [ handbook_steel.db ]  |
|                                                 |<──────────┼── (Slices exact 1 KB)    |
|         │ (Parses Chunk Binary)                 |           |                          |
|         ▼                                       |           |                          |
|  [ HTML UI Updates (DOM) ]                      |           |                          |
|                                                 |           |                          |
+-------------------------------------------------+           +--------------------------+
```

## Architectural Breakdown

*   **index.html & main.js:** Acts as the User Interface manager. It sends user input (the SQL query) to the Web Worker.
*   **sqlite.worker.js:** A background script (Web Worker) that runs in a separate thread. This prevents your website UI from freezing during complex calculations.
*   **sql-wasm.wasm:** The core SQLite database engine compiled into a binary format that the browser can execute at near-native speeds.
*   **handbook_steel.db:** The data file. It is never fully downloaded. The VFS driver (running inside the Worker) requests only the small byte chunks (pages) required to resolve a query.

### Performance Logic
*   **Page Partitioning:** The database is structured in fixed $1024$ byte pages.
*   **Binary Search Traversals (B-Trees):** SQLite queries the indexes first, resolving exactly which database page holds the records.
*   **HTTP Range Requests:** The custom JS driver fires a GET fetch containing a target byte range (e.g., bytes=12288-13312).
*   **Instant Payload Slicing:** GitHub Pages CDN parses the range header and returns only that $1\text{ KB}$ chunk. The user's machine processes the data instantly without pulling down the rest of the database.

## Repository File Tree

```text
├── index.html               # Main UI, responsive viewport, tables, and search controls
├── main.js                  # Frontend WASM initialization and dynamic SQL query binding
├── build_db.py              # Python script parsing raw data into an optimized SQLite file
├── handbook_steel.db        # The optimized, indexed SQLite database file
├── sql-wasm.wasm            # Compiled SQLite WebAssembly binary
├── sqlite.worker.js         # Dedicated worker isolating database CPU cycles from the main UI thread
└── README.md                # Project documentation
```

## Database Schemas

The database compiles into four master tables directly structured from your technical handbook.

### 1. plates_imperial (JIS Standard Plates)
Holds physical specifications of classic JIS Imperial-grade steel plates.

*   **Primary Key & Indexes:** Sorted and indexed via `thickness_mm`
*   **Fields:**
    *   `id` (INTEGER, PK)
    *   `thickness_inch` (TEXT) — e.g., "1/16", "1/8", "1/2"
    *   `thickness_mm` (REAL) — e.g., $1.59$, $3.18$, $12.70$
    *   `unit_weight_kg_sqft` (REAL) — Unit mass scale in $\text{kg/ft}^2$
    *   `w_4x8` to `w_8x30` (REAL) — Precalculated plate sheet weights across standardized dimensions

### 2. plates_metric (JIS Metric Plates)
Covers metric standard plate mass properties.

*   **Fields:**
    *   `id` (INTEGER, PK)
    *   `thickness_mm` (REAL) — Range: $1.2\text{ mm}$ to $150.0\text{ mm}$
    *   `unit_weight_m_kg` (REAL) — Structural density in $\text{kg/m}^2$
    *   `w_3x6` to `w_6x40` (REAL) — Sheet weights corresponding to respective sizing arrays

### 3. cold_rolled_sheets (JIS G3141 Commercial Cold Rolled Sheets)
Standard reference specs for thinner high-finish steel sheeting.

*   **Fields:**
    *   `id` (INTEGER, PK)
    *   `gauge_no` (TEXT) — Gauge designations (e.g., "30 SWG", "28 BWG", "22 USG")
    *   `ref_thickness_mm` (REAL)
    *   `nominal_thickness_mm` (REAL) — Indexed search value
    *   `size_ft` (TEXT) — Dimension limits
    *   `weight_lb` (REAL), `weight_kg` (REAL), `pcs_per_mton` (REAL)

### 4. galvanised_sheets (JIS G3302 Hot Dip Galvanised Sheets)
Coated sheet data with variable zinc weight parameters.

*   **Fields:**
    *   `id` (INTEGER, PK)
    *   `thickness_mm` (REAL) — Structural thickness
    *   `z18_kg_pc`, `z18_lb_pc`, `z18_pcs_mt` (REAL) — Mass parameters for Class Z18 zinc coatings
    *   `z22_z25_kg_pc`, `z22_z25_lb_pc`, `z22_z25_pcs_mt` (REAL) — Mass parameters for Class Z22/Z25 zinc coatings
    *   `z27_kg_pc`, `z27_lb_pc`, `z27_pcs_mt` (REAL) — Mass parameters for Class Z27 zinc coatings

## Setup & Local Execution

**IMPORTANT:** Modern web browsers block WebAssembly execution and Web Worker multithreading when files are launched locally from a `file://` protocol. You must serve this repository via an active local HTTP server to preview it locally.

### 1. Build and Optimize the Database
Execute the Python builder script to process raw data, configure SQLite parameters, and apply indexing models:
`python build_db.py`

### 2. Fetch the WebAssembly Dependencies
Download the target runtime modules from the official `sql.js-httpvfs` CDN delivery network and place them in the root of your project:
*   Web Worker Driver: `sqlite.worker.js`
*   Wasm Compiled Binary: `sql-wasm.wasm`

### 3. Start a Local Server
Run a light web server directly from your workspace directory:
*   **Using Python:** `python -m http.server 8000`
    *   Open your browser to `http://localhost:8000`.
*   **Using Node.js:** `npx serve .`

## GitHub Pages Deployment

1.  Commit and push all project files, including your compiled `handbook_steel.db` and downloaded `.wasm`/`.js` binaries to your repository on GitHub.
2.  In your repository settings, navigate to the **Pages** menu on the left sidebar.
3.  Select the **main** branch (with directory root /) as your Build and Deployment source.
4.  Hit **Save**. Within moments, your secure, serverless database query portal will be live at `https://<your-username>.github.io/<your-repo-name>/`.

## Version Tracker

- [x] v0.1.0 — Conceptual Database Design, Parser Compilation (build_db.py), Schema Layout.
- [ ] v0.2.0 — HTML Canvas Layout, Multi-table SQL dynamic search, parameterized injection safety barriers.
- [ ] v0.3.0 — Steel property calculation utility integration (dynamically multiplying row weights by customizable volumetric counts).
- [ ] v0.4.0 — CSS styling (responsive design grids, dark/light modes) and visual progress indicators for slow network throttles.
