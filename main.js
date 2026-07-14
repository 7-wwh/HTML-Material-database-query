/**
 * Serverless Steel Handbook Query Engine - Frontend Pipeline Controller
 * Coordinates DOM binding states with underlying SQLite WASM Web Worker.
 */

// Configuration definition for sql.js-httpvfs
const workerConfig = {
    from: "inline",
    config: {
        serverMode: "chunk",
        requestChunkSize: 1024, // Matches the 1KB page chunk optimization
        databaseLength: 512000, // Approximate binary offset boundary fallback
        baseUrl: "./",
        files: [
            {
                name: "handbook_steel.db",
                url: "./handbook_steel.db"
            }
        ]
    }
};

let dbWorker = null;
let isWorkerReady = false;

// DOM Element Registry
const elements = {
    status: document.getElementById('engine-status'),
    latency: document.getElementById('query-time'),
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
 * Bootstraps the Web Worker engine and binds communication routing ports.
 */
function initEngineWorker() {
    try {
        // Instantiate official sql.js-httpvfs worker target binary
        dbWorker = new Worker('./sqlite.worker.js');

        // Dispatch operational settings context configurations
        dbWorker.postMessage({ type: 'init', config: workerConfig });

        dbWorker.onmessage = function (event) {
            const msg = event.data;

            switch (msg.type) {
                case 'ready':
                    isWorkerReady = true;
                    updateEngineStatus('Online (HTTP-VFS Active)', 'text-emerald-400', 'bg-emerald-400');
                    enableControls();
                    triggerAutoQuery();
                    break;

                case 'result':
                    renderQueryPayload(msg.results, msg.duration);
                    break;

                case 'error':
                    renderErrorState(msg.error);
                    break;
            }
        };
    } catch (err) {
        updateEngineStatus('Worker Initialization Failure', 'text-rose-500', 'bg-rose-500');
        console.error("Critical structural worker crash:", err);
    }
}

/**
 * Builds automated queries using dynamic parameterized sanitization barriers.
 */
function triggerAutoQuery() {
    if (!isWorkerReady) return;

    const currentTable = elements.tableSelect.value;
    const minThickness = parseFloat(elements.thicknessFilter.value) || 0;

    let sqlQuery = "";

    // Switch schema context maps matching the 4 core database structures
    switch (currentTable) {
        case 'plates_imperial':
            sqlQuery = `SELECT id, thickness_inch, thickness_mm, unit_weight_kg_sqft, w_4x8, w_5x10, w_8x20 FROM plates_imperial WHERE thickness_mm >= ${minThickness} ORDER BY thickness_mm ASC LIMIT 50;`;
            break;
        case 'plates_metric':
            sqlQuery = `SELECT id, thickness_mm, unit_weight_m_kg, w_3x6, w_4x8, w_5x10 FROM plates_metric WHERE thickness_mm >= ${minThickness} ORDER BY thickness_mm ASC LIMIT 50;`;
            break;
        case 'cold_rolled_sheets':
            sqlQuery = `SELECT id, gauge_no, ref_thickness_mm, nominal_thickness_mm, size_ft, weight_lb, weight_kg FROM cold_rolled_sheets WHERE nominal_thickness_mm >= ${minThickness} ORDER BY nominal_thickness_mm ASC LIMIT 50;`;
            break;
        case 'galvanised_sheets':
            sqlQuery = `SELECT id, thickness_mm, z18_kg_pc, z18_pcs_mt, z27_kg_pc, z27_pcs_mt FROM galvanised_sheets WHERE thickness_mm >= ${minThickness} ORDER BY thickness_mm ASC LIMIT 50;`;
            break;
    }

    executeSQL(sqlQuery);
}

/**
 * Dispatches the raw or built SQL queries directly across the operational worker thread.
 */
function executeSQL(sqlString) {
    elements.activeQueryText.textContent = sqlString;
    elements.status.querySelector('span').classList.add('animate-pulse');

    const startTime = performance.now();
    dbWorker.postMessage({
        type: 'query',
        sql: sqlString,
        meta: { startTime }
    });
}

/**
 * Renders the SQL query outputs into the browser DOM layout.
 */
function renderQueryPayload(dataRows, duration) {
    // Update processing latency metrics
    elements.latency.textContent = `${duration ? duration.toFixed(2) : '--'} ms`;
    elements.status.querySelector('span').classList.remove('animate-pulse');

    if (!dataRows || dataRows.length === 0) {
        elements.tableHeaders.innerHTML = `<th class="px-4 py-3 text-slate-400">Zero Results</th>`;
        elements.tableBody.innerHTML = `<tr><td class="px-4 py-6 text-center text-slate-500 text-xs">No entries match the specified filter metrics.</td></tr>`;
        return;
    }

    const multiplier = parseFloat(elements.multiplier.value) || 1;
    const columnKeys = Object.keys(dataRows[0]);

    // Build Table Header Components
    elements.tableHeaders.innerHTML = columnKeys
        .map(key => `<th class="px-4 py-3 font-semibold tracking-wide text-slate-200 uppercase text-xs">${key}</th>`)
        .join('');

    // Build Content Rows & Apply Calculation Utility Multipliers (v0.3.0 Engine Integration)
    elements.tableBody.innerHTML = dataRows.map((row, index) => {
        const stripedClass = index % 2 === 0 ? 'bg-slate-800/40' : 'bg-slate-800/80';
        return `
            <tr class="${stripedClass} hover:bg-slate-700/50 transition-colors">
                ${columnKeys.map(key => {
            let cellVal = row[key];

            // Apply programmatic calculations to weight fields if batch volume inputs exist
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
 * Safely processes and displays processing failure vectors across the UI.
 */
function renderErrorState(errorMessage) {
    elements.status.querySelector('span').classList.remove('animate-pulse');
    elements.tableHeaders.innerHTML = `<th class="px-4 py-3 text-rose-400 font-bold">Query Execution Syntax Failure</th>`;
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
    elements.tableSelect.addEventListener('change', () => {
        triggerAutoQuery();
    });

    elements.thicknessFilter.addEventListener('input', () => {
        triggerAutoQuery();
    });

    elements.multiplier.addEventListener('input', () => {
        triggerAutoQuery();
    });

    // Console bypass mechanics toggle switch
    elements.toggleConsole.addEventListener('change', (e) => {
        const isChecked = e.target.checked;
        elements.sqlConsole.disabled = !isChecked;
        elements.runSqlBtn.disabled = !isChecked;

        if (isChecked) {
            elements.sqlConsole.classList.remove('text-slate-400');
            elements.sqlConsole.classList.add('text-emerald-400');
        } else {
            elements.sqlConsole.classList.remove('text-emerald-400');
            elements.sqlConsole.classList.add('text-slate-400');
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

// Fire system baseline runtime triggers on interface payload initialization
document.addEventListener('DOMContentLoaded', initEngineWorker);