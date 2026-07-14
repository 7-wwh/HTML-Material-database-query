/**
 * Yick Hoe Steel Material Database Query Engine - Frontend Controller
 * Coordinates DOM binding states with underlying in-memory SQL.js instance.
 */

// Global SQL.js database instance
let db = null;

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
 * Returns whether the given table has a thickness column for filtering.
 */
function tableHasThicknessFilter(tableName) {
    return [
        'plates_imperial',
        'plates_metric',
        'chequered_plates_mm',
        'chequered_plates_inch',
        'cold_rolled_sheets_weights',
        'galvanised_sheet_weights',
        'electrolytic_galvanised_weights'
    ].includes(tableName);
}

/**
 * Builds the SQL SELECT query for the given table and optional thickness filter.
 */
function buildQuery(tableName, minThickness) {
    const noFilterTables = ['steel_specs', 'cold_rolled_standards', 'hot_dip_galvanised_standards'];

    const queries = {
        'plates_imperial': `
            SELECT id, thickness_in AS thickness_inch, thickness_mm, unit_weight_kg_ft2,
                   size_4x8_ft AS w_4x8, size_5x10_ft AS w_5x10, size_5x20_ft AS w_5x20,
                   size_5x30_ft AS w_5x30, size_6x20_ft AS w_6x20, size_6x24_ft AS w_6x24,
                   size_6x30_ft AS w_6x30, size_8x30_ft AS w_8x30
            FROM plates_imperial
            WHERE thickness_mm >= ${minThickness}
            ORDER BY thickness_mm ASC LIMIT 50
        `,
        'plates_metric': `
            SELECT id, thickness_mm, unit_weight_kg_m2 AS unit_weight_m_kg,
                   size_3x6_ft AS w_3x6, size_4x8_ft AS w_4x8, size_4x10_ft AS w_4x10,
                   size_4x16_ft AS w_4x16, size_4x20_ft AS w_4x20, size_5x10_ft AS w_5x10,
                   size_5x20_ft AS w_5x20, size_5x30_ft AS w_5x30, size_5x40_ft AS w_5x40,
                   size_6x30_ft AS w_6x30, size_6x40_ft AS w_6x40
            FROM plates_metric
            WHERE thickness_mm >= ${minThickness}
            ORDER BY thickness_mm ASC LIMIT 50
        `,
        'chequered_plates_mm': `
            SELECT id, thickness_mm, unit_weight_kg_m2,
                   size_914x1829_mm, size_914x3658_mm, size_1219x2438_mm,
                   size_1219x3048_mm, size_1219x4877_mm, size_1219x6096_mm,
                   size_1524x3048_mm, size_1524x6096_mm
            FROM chequered_plates_mm
            WHERE thickness_mm >= ${minThickness}
            ORDER BY thickness_mm ASC LIMIT 50
        `,
        'chequered_plates_inch': `
            SELECT id, thickness_in AS thickness_inch, unit_weight_lb_ft2,
                   size_3x6_ft, size_3x12_ft, size_4x8_ft, size_4x10_ft,
                   size_4x16_ft, size_4x20_ft, size_5x10_ft, size_5x20_ft
            FROM chequered_plates_inch
            WHERE thickness_in >= ${minThickness}
            ORDER BY thickness_in ASC LIMIT 50
        `,
        'cold_rolled_sheets_weights': `
            SELECT id, gauge_references, thickness_nominal_mm AS ref_thickness_mm,
                   size_ft, weight_lb_pce AS weight_lb, weight_kg_pce AS weight_kg,
                   pcs_per_metric_ton AS pcs_per_mton
            FROM cold_rolled_sheets_weights
            WHERE thickness_nominal_mm >= ${minThickness}
            ORDER BY thickness_nominal_mm ASC LIMIT 50
        `,
        'cold_rolled_standards': `
            SELECT id, application, std_ks, std_jis, std_astm, std_bs,
                   std_din_1623, std_din_1624, std_posco
            FROM cold_rolled_standards
            ORDER BY id ASC LIMIT 50
        `,
        'galvanised_sheet_weights': `
            SELECT id, thickness_mm, coating_grade, weight_kg_pc, weight_lb_pc,
                   pcs_per_mt, size, standard
            FROM galvanised_sheet_weights
            WHERE thickness_mm >= ${minThickness}
            ORDER BY thickness_mm ASC LIMIT 50
        `,
        'hot_dip_galvanised_standards': `
            SELECT id, application, std_ks, std_jis, std_astm, std_bs,
                   std_din_part1, std_din_part2
            FROM hot_dip_galvanised_standards
            ORDER BY id ASC LIMIT 50
        `,
        'electrolytic_galvanised_weights': `
            SELECT id, thickness_mm, weight_kg_sht, size
            FROM electrolytic_galvanised_weights
            WHERE thickness_mm >= ${minThickness}
            ORDER BY thickness_mm ASC LIMIT 50
        `,
        'steel_specs': `
            SELECT id, classification, specification, grade,
                   c_max_pct, mn_max_pct, si_max_pct, p_max_pct, s_max_pct,
                   tensile_strength_min, tensile_strength_max, yield_strength_min,
                   elongation_test, bend_angle, bend_radius
            FROM steel_specs
            ORDER BY id ASC LIMIT 50
        `
    };

    return queries[tableName] || '';
}

/**
 * Initializes the SQL.js instance and loads the database.
 */
async function initEngine() {
    try {
        updateEngineStatus('Initializing Engine...', 'text-amber-400', 'bg-amber-400');

        // Initialize SQL.js
        const SQL = await initSqlJs({
            locateFile: filename => `https://cdnjs.cloudflare.com/ajax/libs/sql.js/1.10.3/${filename}`
        });

        // Fetch the local database file
        const response = await fetch('./database/handbook_steel.db');
        if (!response.ok) throw new Error(`Failed to load database: ${response.statusText}`);
        
        const buffer = await response.arrayBuffer();
        
        // Initialize the in-memory database
        db = new SQL.Database(new Uint8Array(buffer));
        
        updateEngineStatus('Online (In-Memory)', 'text-emerald-400', 'bg-emerald-400');
        enableControls();
        triggerAutoQuery();
    } catch (err) {
        updateEngineStatus('Initialization Failure', 'text-rose-500', 'bg-rose-500');
        renderErrorState(err.message);
        console.error("Critical database initialization error:", err);
    }
}

/**
 * Shows/hides the thickness filter based on the selected table.
 */
function updateFilterVisibility() {
    const table = elements.tableSelect.value;
    const hasFilter = tableHasThicknessFilter(table);
    const container = elements.thicknessFilter.closest('div');
    if (container) {
        container.style.display = hasFilter ? 'block' : 'none';
    }
}

/**
 * Builds automated queries and executes them.
 */
function triggerAutoQuery() {
    if (!db) return;

    const currentTable = elements.tableSelect.value;
    const minThickness = parseFloat(elements.thicknessFilter.value) || 0;

    updateFilterVisibility();

    const sqlQuery = buildQuery(currentTable, minThickness);
    if (!sqlQuery) {
        renderErrorState(`Unknown table: "${currentTable}".`);
        return;
    }

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
        
        // Process results (SQL.js returns an array of result sets)
        if (results.length > 0) {
            // Convert result set to array of objects
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

document.addEventListener('DOMContentLoaded', initEngine);
