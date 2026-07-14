/**
 * Yick Hoe Steel Material Database Query Engine - Dynamic Engine Driver
 * Handles lazy loading databases from JSON configurations and auto-discovering table schemas.
 */

let db = null;
let databaseRegistry = [];
let SQLInstance = null;

// DOM Element Registry
const elements = {
    status: document.getElementById('engine-status'),
    latency: document.getElementById('query-time'),
    dbSelect: document.getElementById('db-select'),
    dbDescription: document.getElementById('db-description'),
    tableSelect: document.getElementById('table-select'),
    thicknessFilter: document.getElementById('thickness-filter'),
    thicknessContainer: document.getElementById('thickness-filter-container'),
    multiplier: document.getElementById('quantity-multiplier'),
    toggleConsole: document.getElementById('toggle-console'),
    sqlConsole: document.getElementById('sql-console'),
    runSqlBtn: document.getElementById('run-sql-btn'),
    activeQueryText: document.getElementById('active-query-text'),
    tableHeaders: document.getElementById('table-headers'),
    tableBody: document.getElementById('table-body')
};

/**
 * Global App Bootstrapper
 */
async function bootApp() {
    try {
        updateEngineStatus('Loading Registry...', 'text-amber-400', 'bg-amber-400');
        
        // Load configurations
        const response = await fetch('./database/databases.json');
        if (!response.ok) throw new Error("Could not find database/databases.json config file.");
        databaseRegistry = await response.json();

        // Initialize WebAssembly engine context ahead of time
        SQLInstance = await initSqlJs({
            locateFile: filename => `https://cdnjs.cloudflare.com/ajax/libs/sql.js/1.10.3/${filename}`
        });

        populateDatabaseDropdown();
        enableControls();
        
        // Auto-load the primary option if config array isn't empty
        if (databaseRegistry.length > 0) {
            elements.dbSelect.value = databaseRegistry[0].file;
            handleDatabaseChange();
        }
    } catch (err) {
        updateEngineStatus('Boot Failure', 'text-rose-500', 'bg-rose-500');
        renderErrorState(err.message);
    }
}

/**
 * Fills choices into DB Dropdown selection menu
 */
function populateDatabaseDropdown() {
    elements.dbSelect.innerHTML = databaseRegistry.map(item => 
        `<option value="${item.file}">${item.name}</option>`
    ).join('');
}

/**
 * Fires when user drops down and swaps database tracks
 */
async function handleDatabaseChange() {
    const selectedFile = elements.dbSelect.value;
    const dbMeta = databaseRegistry.find(item => item.file === selectedFile);
    
    if (dbMeta) {
        elements.dbDescription.textContent = dbMeta.description || '';
    }

    if (!selectedFile) return;

    try {
        updateEngineStatus('Fetching DB Box...', 'text-amber-400', 'bg-amber-400');
        elements.tableSelect.disabled = true;
        elements.tableSelect.innerHTML = '<option>Reading catalog index...</option>';

        // Fetch selected SQLite binary
        const response = await fetch(`./database/${selectedFile}`);
        if (!response.ok) throw new Error(`Could not download the target database file: ${response.statusText}`);
        const buffer = await response.arrayBuffer();

        // Load into RAM via WebAssembly pipeline
        db = new SQLInstance.Database(new Uint8Array(buffer));
        updateEngineStatus('Online (In-Memory)', 'text-emerald-400', 'bg-emerald-400');

        discoverDatabaseTables();
    } catch (err) {
        updateEngineStatus('Read Error', 'text-rose-500', 'bg-rose-500');
        renderErrorState(err.message);
    }
}

/**
 * Queries sqlite_master structure to find user data tables automatically
 */
function discoverDatabaseTables() {
    try {
        const query = "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name ASC;";
        const results = db.exec(query);

        if (results.length === 0 || results[0].values.length === 0) {
            elements.tableSelect.innerHTML = '<option value="">No working tables found</option>';
            return;
        }

        const tableNames = results[0].values.map(row => row[0]);
        elements.tableSelect.innerHTML = tableNames.map(name => 
            `<option value="${name}">${name.replace(/_/g, ' ')}</option>`
        ).join('');
        
        elements.tableSelect.disabled = false;
        triggerAutoQuery();
    } catch (err) {
        renderErrorState(`Failed to parse table structures: ${err.message}`);
    }
}

/**
 * Dynamically builds a simple automated fallback query
 */
function triggerAutoQuery() {
    if (!db || !elements.tableSelect.value) return;

    const tableName = elements.tableSelect.value;
    
    // Auto-discover schema columns using SQLite PRAGMA configuration
    let columns = [];
    try {
        const structuralMeta = db.exec(`PRAGMA table_info(${tableName});`);
        if (structuralMeta.length > 0) {
            columns = structuralMeta[0].values.map(col => col[1]); // col[1] holds column names
        }
    } catch(e) { console.error("Pragma parsing dropped", e); }

    // Toggle thickness row filter view conditionally if a matching key string is detected
    const filterKey = columns.find(c => c.toLowerCase().includes('thickness'));
    if (filterKey) {
        elements.thicknessContainer.style.display = 'block';
        const minVal = parseFloat(elements.thicknessFilter.value) || 0;
        executeSQL(`SELECT * FROM ${tableName} WHERE ${filterKey} >= ${minVal} LIMIT 50;`);
    } else {
        elements.thicknessContainer.style.display = 'none';
        executeSQL(`SELECT * FROM ${tableName} LIMIT 50;`);
    }
}

/**
 * Executes standard SQL queries securely inside the WebAssembly pipeline context
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
 * Appends output elements into visual container arrays for user layout viewing
 */
function renderQueryPayload(dataRows, duration) {
    elements.latency.textContent = `${duration ? duration.toFixed(2) : '--'} ms`;

    if (!dataRows || dataRows.length === 0) {
        elements.tableHeaders.innerHTML = `<th class="px-4 py-3 text-slate-400">Zero Results</th>`;
        elements.tableBody.innerHTML = `<tr><td class="px-4 py-6 text-center text-slate-500 text-xs">No entries match the specified filter metrics.</td></tr>`;
        return;
    }

    const multiplier = parseFloat(elements.multiplier.value) || 1;
    const columnKeys = Object.keys(dataRows[0]);

    elements.tableHeaders.innerHTML = columnKeys
        .map(key => `<th class="px-4 py-3 font-semibold tracking-wide text-slate-200 uppercase text-xs">${key}</th>`)
        .join('');

    elements.tableBody.innerHTML = dataRows.map((row, index) => {
        const stripedClass = index % 2 === 0 ? 'bg-slate-800/40' : 'bg-slate-800/80';
        return `
            <tr class="${stripedClass} hover:bg-slate-700/50 transition-colors">
                ${columnKeys.map(key => {
                    let cellVal = row[key];

                    if (multiplier > 1 && typeof cellVal === 'number' && key !== 'id' && !key.includes('thickness') && !key.includes('pcs')) {
                        cellVal = `${(cellVal * multiplier).toFixed(2)} <span class="text-[10px] text-amber-400 font-medium block">Total (${multiplier}x)</span>`;
                    } else if (typeof cellVal === 'number' && !key.includes('id')) {
                        cellVal = cellVal.toFixed(2);
                    }

                    return `<td class="px-4 py-3 text-sm font-mono text-slate-300 border-t border-slate-700/60">${cellVal ?? '-'}</td>`;
                }).join('')}
            </tr>
        `;
    }).join('');
}

/**
 * Standard visual interface for showing syntax errors cleanly
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
 * Attaches browser input event listeners securely
 */
function enableControls() {
    elements.dbSelect.addEventListener('change', handleDatabaseChange);
    elements.tableSelect.addEventListener('change', triggerAutoQuery);
    elements.thicknessFilter.addEventListener('input', triggerAutoQuery);
    elements.multiplier.addEventListener('input', triggerAutoQuery);

    elements.toggleConsole.addEventListener('change', (e) => {
        const isChecked = e.target.checked;
        elements.sqlConsole.disabled = !isChecked;
        elements.runSqlBtn.disabled = !isChecked;

        if (isChecked) {
            elements.sqlConsole.classList.add('text-emerald-400');
        } else {
            elements.sqlConsole.classList.remove('text-emerald-400');
            triggerAutoQuery();
        }
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

document.addEventListener('DOMContentLoaded', bootApp);
