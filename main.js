/**
 * Yick Hoe Steel Material Database Query Engine - Frontend Controller
 * Coordinates DOM binding states with underlying in-memory SQL.js instance.
 */

// Global SQL.js database instance
let db = null;
let dbRegistry = [];

// DOM Element Registry
const elements = {
    status: document.getElementById('engine-status'),
    latency: document.getElementById('query-time'),
    dbSelect: document.getElementById('db-select'),
    tableSelect: document.getElementById('table-select'),
    thicknessFilter: document.getElementById('thickness-filter'),
    multiplier: document.getElementById('quantity-multiplier'),
    toggleConsole: document.getElementById('toggle-console'),
    sqlConsole: document.getElementById('sql-console'),
    runSqlBtn: document.getElementById('run-sql-btn'),
    activeQueryText: document.getElementById('active-query-text'),
    tableHeaders: document.getElementById('table-headers'),
    tableBody: document.getElementById('table-body')
};

/**
 * Initializes the SQL.js instance and loads the database registry.
 */
async function initEngine() {
    try {
        updateEngineStatus('Initializing Engine...', 'text-amber-400', 'bg-amber-400');

        // Initialize SQL.js
        const SQL = await initSqlJs({
            locateFile: filename => `https://cdnjs.cloudflare.com/ajax/libs/sql.js/1.10.3/${filename}`
        });
        window.SQL = SQL; // Expose for scope

        // Fetch the registry
        const regResponse = await fetch('./database/databases.json');
        dbRegistry = await regResponse.json();

        // Populate DB select
        elements.dbSelect.innerHTML = dbRegistry.map(db => `<option value="${db.id}">${db.name}</option>`).join('');

        enableControls();
        loadDatabase(dbRegistry[0].id);

    } catch (err) {
        updateEngineStatus('Initialization Failure', 'text-rose-500', 'bg-rose-500');
        renderErrorState(err.message);
        console.error("Critical database initialization error:", err);
    }
}

/**
 * Loads a specific database file.
 */
async function loadDatabase(dbId) {
    try {
        const dbInfo = dbRegistry.find(d => d.id === dbId);
        if (!dbInfo) throw new Error("Database not found");

        updateEngineStatus('Loading Database...', 'text-amber-400', 'bg-amber-400');

        // Fetch the local database file
        const response = await fetch(`./database/${dbInfo.file}`);
        if (!response.ok) throw new Error(`Failed to load database: ${response.statusText}`);
        
        const buffer = await response.arrayBuffer();
        
        // Initialize/Replace the in-memory database
        if (db) db.close();
        db = new window.SQL.Database(new Uint8Array(buffer));
        
        updateEngineStatus('Online (In-Memory)', 'text-emerald-400', 'bg-emerald-400');
        
        // Discover tables
        const tables = db.exec("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")[0].values.map(v => v[0]);
        elements.tableSelect.innerHTML = tables.map(t => `<option value="${t}">${t}</option>`).join('');
        
        triggerAutoQuery();
    } catch (err) {
        updateEngineStatus('Database Load Failure', 'text-rose-500', 'bg-rose-500');
        renderErrorState(err.message);
    }
}

/**
 * Builds automated queries and executes them.
 */
function triggerAutoQuery() {
    if (!db) return;

    const currentTable = elements.tableSelect.value;
    if (!currentTable) return;

    const sqlQuery = `SELECT * FROM ${currentTable} LIMIT 50;`;

    executeSQL(sqlQuery);
}

/**
 * Executes SQL directly against the in-memory DB.
 */
function executeSQL(sqlString) {
    elements.activeQueryText.textContent = sqlString;
    const startTime = performance.now();

    try {
        const results = db.exec(sqlString);
        const endTime = performance.now();
        
        if (results.length > 0) {
            const columns = results[0].columns;
            const values = results[0].values;
            const dataRows = values.map(row => {
                const obj = {};
                columns.forEach((col, i) => obj[col] = row[i]);
                return obj;
            });
            renderQueryPayload(dataRows, endTime - startTime);
        } else {
            renderQueryPayload([], endTime - startTime);
        }
    } catch (err) {
        renderErrorState(err.message);
    }
}

/**
 * Renders the SQL query outputs into the browser DOM layout.
 */
function renderQueryPayload(dataRows, duration) {
    elements.latency.textContent = `${duration ? duration.toFixed(2) : '--'} ms`;

    if (!dataRows || dataRows.length === 0) {
        elements.tableHeaders.innerHTML = `<th class="px-4 py-3 text-slate-400">Zero Results</th>`;
        elements.tableBody.innerHTML = `<tr><td class="px-4 py-6 text-center text-slate-500 text-xs">No entries match the query.</td></tr>`;
        return;
    }

    const columnKeys = Object.keys(dataRows[0]);

    elements.tableHeaders.innerHTML = columnKeys
        .map(key => `<th class="px-4 py-3 font-semibold tracking-wide text-slate-200 uppercase text-xs">${key}</th>`)
        .join('');

    elements.tableBody.innerHTML = dataRows.map((row, index) => {
        const stripedClass = index % 2 === 0 ? 'bg-slate-800/40' : 'bg-slate-800/80';
        return `
            <tr class="${stripedClass} hover:bg-slate-700/50 transition-colors">
                ${columnKeys.map(key => `<td class="px-4 py-3 text-sm font-mono text-slate-300 border-t border-slate-700/60">${row[key] ?? '-'}</td>`).join('')}
            </tr>
        `;
    }).join('');
}

/**
 * Displays error state.
 */
function renderErrorState(errorMessage) {
    elements.tableHeaders.innerHTML = `<th class="px-4 py-3 text-rose-400 font-bold">Query Execution Failure</th>`;
    elements.tableBody.innerHTML = `
        <tr>
            <td class="px-4 py-6 text-left text-rose-300 font-mono text-xs bg-rose-950/20 border border-rose-900/40 rounded-lg">
                ${errorMessage}
            </td>
        </tr>
    `;
}

/**
 * Event Listener Declarations & Bindings
 */
function enableControls() {
    elements.dbSelect.addEventListener('change', (e) => loadDatabase(e.target.value));
    elements.tableSelect.addEventListener('change', triggerAutoQuery);

    elements.toggleConsole.addEventListener('change', (e) => {
        const isChecked = e.target.checked;
        elements.sqlConsole.disabled = !isChecked;
        elements.runSqlBtn.disabled = !isChecked;
    });

    elements.runSqlBtn.addEventListener('click', () => {
        const rawSql = elements.sqlConsole.value.trim();
        if (rawSql) executeSQL(rawSql);
    });
}

function updateEngineStatus(text, textColorClass, dotColorClass) {
    elements.status.className = `inline-flex items-center font-semibold ${textColorClass}`;
    elements.status.innerHTML = `<span class="w-2 h-2 rounded-full ${dotColorClass} mr-1.5"></span>${text}`;
}

document.addEventListener('DOMContentLoaded', initEngine);
