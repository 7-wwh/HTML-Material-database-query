/**
 * Yick Hoe Steel Material Database Query Engine
 * Radial category wheel → subcategory cards → data table
 */

let db = null;
let databaseRegistry = [];   // raw array from databases.json
let categoryMap = {};        // { "Plates": [ {name, file, description?}, ... ], ... }
let SQLInstance = null;
let activeCategory = null;
let activeDB = null;

// ─── DOM refs ────────────────────────────────────────────────────────────────
const el = {
    landingView:        document.getElementById('landing-view'),
    subcategoryView:    document.getElementById('subcategory-view'),
    tableView:          document.getElementById('table-view'),
    wheelCanvas:        document.getElementById('wheel-canvas'),
    wheelCenterLabel:   document.getElementById('wheel-center-label'),
    wheelCenterName:    document.getElementById('wheel-center-name'),
    subHeader:          document.getElementById('sub-header'),
    subGrid:            document.getElementById('sub-grid'),
    breadcrumb:         document.getElementById('breadcrumb'),
    bcCategory:         document.getElementById('bc-category'),
    bcDb:               document.getElementById('bc-db'),
    btnBackHome:        document.getElementById('btn-back-home'),
    btnBackSub:         document.getElementById('btn-back-sub'),
    tableSelect:        document.getElementById('table-select'),
    thicknessFilter:    document.getElementById('thickness-filter'),
    thicknessContainer: document.getElementById('thickness-filter-container'),
    multiplier:         document.getElementById('quantity-multiplier'),
    toggleConsole:      document.getElementById('toggle-console'),
    sqlConsole:         document.getElementById('sql-console'),
    runSqlBtn:          document.getElementById('run-sql-btn'),
    activeQueryText:    document.getElementById('active-query-text'),
    tableHeaders:       document.getElementById('table-headers'),
    tableBody:          document.getElementById('table-body'),
    engineStatus:       document.getElementById('engine-status'),
    queryTime:          document.getElementById('query-time'),
    dbDescription:      document.getElementById('db-description'),
};

// ─── Boot ─────────────────────────────────────────────────────────────────────
async function bootApp() {
    updateEngineStatus('Loading registry…', 'amber');
    try {
        const resp = await fetch('./database/databases.json');
        if (!resp.ok) throw new Error('Could not load database/databases.json');
        databaseRegistry = await resp.json();

        // Build category map from { category, items[] } structure
        categoryMap = {};
        for (const entry of databaseRegistry) {
            const cat = entry.category || 'Uncategorised';
            if (!categoryMap[cat]) categoryMap[cat] = [];
            // Support both flat entries and entries with items[]
            if (entry.items && Array.isArray(entry.items)) {
                categoryMap[cat].push(...entry.items.map(it => ({ ...it, _parentDescription: entry.description })));
            } else {
                categoryMap[cat].push(entry);
            }
        }

        SQLInstance = await initSqlJs({
            locateFile: f => `https://cdnjs.cloudflare.com/ajax/libs/sql.js/1.10.3/${f}`
        });

        updateEngineStatus('Ready', 'green');
        initWheelEvents();
        initTableControls();
        showLanding();

    } catch (err) {
        updateEngineStatus('Boot failure', 'red');
        console.error(err);
    }
}

// ─── View transitions ─────────────────────────────────────────────────────────
function showLanding() {
    el.landingView.style.display     = 'flex';
    el.subcategoryView.style.display = 'none';
    el.tableView.style.display       = 'none';
    el.breadcrumb.dataset.depth      = '0';
    drawWheel(-1);
}

function showSubcategory(categoryName) {
    activeCategory = categoryName;
    el.landingView.style.display     = 'none';
    el.subcategoryView.style.display = 'flex';
    el.tableView.style.display       = 'none';

    el.bcCategory.textContent        = categoryName;
    el.breadcrumb.dataset.depth      = '1';

    const items = categoryMap[categoryName] || [];
    el.subHeader.textContent = categoryName;
    el.subGrid.innerHTML = items.map(item => `
        <button class="sub-card" data-file="${item.file}" aria-label="Load ${item.name}">
            <span class="sub-card-name">${item.name}</span>
            ${item.description ? `<span class="sub-card-desc">${item.description}</span>` : ''}
            <span class="sub-card-file">${item.file}</span>
        </button>
    `).join('');

    el.subGrid.querySelectorAll('.sub-card').forEach(btn => {
        btn.addEventListener('click', () => loadDatabase(btn.dataset.file));
    });
}

function showTableView(dbMeta) {
    activeDB = dbMeta;
    el.landingView.style.display     = 'none';
    el.subcategoryView.style.display = 'none';
    el.tableView.style.display       = 'flex';

    el.bcCategory.textContent        = activeCategory;
    el.bcDb.textContent              = dbMeta.name;
    el.breadcrumb.dataset.depth      = '2';
    el.dbDescription.textContent     = dbMeta.description || dbMeta._parentDescription || '';
    el.tableSelect.disabled          = true;
    el.tableSelect.innerHTML         = '<option>Reading catalog…</option>';

    discoverTables();
}

// ─── Database loading ─────────────────────────────────────────────────────────
async function loadDatabase(file) {
    // Find in registry — search flat entries and nested items
    let dbMeta = databaseRegistry.find(d => d.file === file);
    if (!dbMeta) {
        // Search inside items arrays
        for (const entry of databaseRegistry) {
            if (entry.items) {
                const found = entry.items.find(it => it.file === file);
                if (found) { dbMeta = { ...found, _parentDescription: entry.description }; break; }
            }
        }
    }
    if (!dbMeta) return;

    updateEngineStatus('Fetching…', 'amber');
    try {
        const resp = await fetch(`./database/${file}`);
        if (!resp.ok) throw new Error(`Could not fetch ${file}: ${resp.statusText}`);
        const buf = await resp.arrayBuffer();

        if (db) db.close();
        db = new SQLInstance.Database(new Uint8Array(buf));

        updateEngineStatus('Online (in-memory)', 'green');
        showTableView(dbMeta);

    } catch (err) {
        updateEngineStatus('Load error', 'red');
        renderError(err.message);
    }
}

// ─── Table discovery ──────────────────────────────────────────────────────────
function discoverTables() {
    try {
        const res = db.exec("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name;");
        if (!res.length || !res[0].values.length) {
            el.tableSelect.innerHTML = '<option>No tables found</option>';
            return;
        }
        const names = res[0].values.map(r => r[0]);
        el.tableSelect.innerHTML = names.map(n =>
            `<option value="${n}">${n.replace(/_/g, ' ')}</option>`
        ).join('');
        el.tableSelect.disabled = false;
        triggerAutoQuery();
    } catch (err) {
        renderError(`Schema discovery failed: ${err.message}`);
    }
}

// ─── Auto query ───────────────────────────────────────────────────────────────
function triggerAutoQuery() {
    if (!db || !el.tableSelect.value) return;
    const table = el.tableSelect.value;

    let columns = [];
    try {
        const meta = db.exec(`PRAGMA table_info(${table});`);
        if (meta.length) columns = meta[0].values.map(c => c[1]);
    } catch (e) { /* ignore */ }

    const thicknessCol = columns.find(c => c.toLowerCase().includes('thickness'));
    if (thicknessCol) {
        el.thicknessContainer.style.display = 'block';
        const min = parseFloat(el.thicknessFilter.value) || 0;
        executeSQL(`SELECT * FROM ${table} WHERE ${thicknessCol} >= ${min} LIMIT 50;`);
    } else {
        el.thicknessContainer.style.display = 'none';
        executeSQL(`SELECT * FROM ${table} LIMIT 50;`);
    }
}

// ─── SQL execution ────────────────────────────────────────────────────────────
function executeSQL(sql) {
    el.activeQueryText.textContent = sql;
    const t0 = performance.now();
    try {
        const res = db.exec(sql);
        const ms  = performance.now() - t0;
        if (res.length) {
            const rows = res[0].values.map(row => {
                const obj = {};
                res[0].columns.forEach((col, i) => obj[col] = row[i]);
                return obj;
            });
            renderTable(rows, ms);
        } else {
            renderTable([], ms);
        }
    } catch (err) {
        renderError(err.message);
    }
}

// ─── Render table ─────────────────────────────────────────────────────────────
function renderTable(rows, ms) {
    el.queryTime.textContent = ms ? `${ms.toFixed(2)} ms` : '-- ms';

    if (!rows.length) {
        el.tableHeaders.innerHTML = `<th class="px-4 py-3 text-slate-400">No results</th>`;
        el.tableBody.innerHTML    = `<tr><td class="px-4 py-6 text-center text-slate-500 text-xs">No entries match the current filter.</td></tr>`;
        return;
    }

    const mult = parseFloat(el.multiplier.value) || 1;
    const keys = Object.keys(rows[0]);

    el.tableHeaders.innerHTML = keys.map(k =>
        `<th class="px-4 py-3 font-semibold tracking-wide text-slate-200 uppercase text-xs">${k}</th>`
    ).join('');

    el.tableBody.innerHTML = rows.map((row, i) => {
        const stripe = i % 2 === 0 ? 'bg-slate-800/40' : 'bg-slate-800/80';
        return `<tr class="${stripe} hover:bg-slate-700/50 transition-colors">
            ${keys.map(k => {
                let v = row[k];
                if (mult > 1 && typeof v === 'number' && k !== 'id' && !k.includes('thickness') && !k.includes('pcs')) {
                    v = `${(v * mult).toFixed(2)} <span class="text-[10px] text-amber-400 font-medium block">Total (${mult}x)</span>`;
                } else if (typeof v === 'number' && !k.includes('id')) {
                    v = v.toFixed(2);
                }
                return `<td class="px-4 py-3 text-sm font-mono text-slate-300 border-t border-slate-700/60">${v ?? '-'}</td>`;
            }).join('')}
        </tr>`;
    }).join('');
}

function renderError(msg) {
    el.tableHeaders.innerHTML = `<th class="px-4 py-3 text-rose-400 font-bold">Error</th>`;
    el.tableBody.innerHTML    = `<tr><td class="px-4 py-6 font-mono text-xs text-rose-300 bg-rose-950/20 border border-rose-900/40 rounded-lg">${msg}</td></tr>`;
}

// ─── Wheel drawing ────────────────────────────────────────────────────────────
const COLORS_LIGHT = ['#B5D4F4','#9FE1CB','#F5C4B3','#F4C0D1','#FAC775','#C0DD97','#D3D1C7','#CECBF6','#F0997B','#5DCAA5','#85B7EB','#97C459'];
const COLORS_DARK  = ['#0C447C','#085041','#993C1D','#72243E','#633806','#27500A','#444441','#3C3489','#712B13','#0F6E56','#185FA5','#3B6D11'];

let hoveredSegment = -1;

function drawWheel(hovered) {
    const canvas = el.wheelCanvas;
    if (!canvas) return;
    const ctx    = canvas.getContext('2d');
    const W = canvas.width, H = canvas.height;
    const cx = W / 2, cy = H / 2;
    const outerR = W * 0.46, innerR = W * 0.16, gap = 0.022;
    const cats = Object.keys(categoryMap);
    const n    = cats.length;
    if (!n) return;
    const arc    = (2 * Math.PI) / n;
    const isDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    const colors = isDark ? COLORS_DARK : COLORS_LIGHT;
    const textColor = isDark ? '#E6F1FB' : '#042C53';

    ctx.clearRect(0, 0, W, H);

    cats.forEach((cat, i) => {
        const isHov = i === hovered;
        const r     = isHov ? outerR + 9 : outerR;
        const start = -Math.PI / 2 + i * arc + gap;
        const end   = -Math.PI / 2 + (i + 1) * arc - gap;

        ctx.beginPath();
        ctx.moveTo(cx, cy);
        ctx.arc(cx, cy, r, start, end);
        ctx.closePath();
        ctx.fillStyle   = colors[i % colors.length];
        ctx.globalAlpha = isHov ? 1 : 0.80;
        ctx.fill();
        ctx.globalAlpha = 1;

        const mid  = -Math.PI / 2 + (i + 0.5) * arc;
        const labR = (r + innerR) / 2;
        const lx   = cx + labR * Math.cos(mid);
        const ly   = cy + labR * Math.sin(mid);

        ctx.save();
        ctx.translate(lx, ly);
        ctx.rotate(mid + Math.PI / 2);
        ctx.fillStyle    = textColor;
        ctx.font         = `${isHov ? '500' : '400'} 11px sans-serif`;
        ctx.textAlign    = 'center';
        ctx.textBaseline = 'middle';
        const words = cat.split(' ');
        words.forEach((w, wi) => ctx.fillText(w, 0, (wi - (words.length - 1) / 2) * 13));
        ctx.restore();
    });
}

function getSegmentAt(mx, my) {
    const canvas = el.wheelCanvas;
    const W = canvas.width, H = canvas.height;
    const cx = W / 2, cy = H / 2;
    const outerR = W * 0.46, innerR = W * 0.16;
    const dx = mx - cx, dy = my - cy;
    const dist = Math.sqrt(dx * dx + dy * dy);
    if (dist < innerR || dist > outerR + 12) return -1;
    let angle = Math.atan2(dy, dx) + Math.PI / 2;
    if (angle < 0) angle += 2 * Math.PI;
    const cats = Object.keys(categoryMap);
    return Math.floor(angle / ((2 * Math.PI) / cats.length)) % cats.length;
}

function initWheelEvents() {
    const canvas = el.wheelCanvas;

    canvas.addEventListener('mousemove', e => {
        const r   = canvas.getBoundingClientRect();
        const idx = getSegmentAt(e.clientX - r.left, e.clientY - r.top);
        if (idx === hoveredSegment) return;
        hoveredSegment = idx;
        drawWheel(idx);
        const cats = Object.keys(categoryMap);
        if (idx >= 0) {
            const count = categoryMap[cats[idx]].length;
            el.wheelCenterLabel.textContent = `${count} table${count !== 1 ? 's' : ''}`;
            el.wheelCenterName.textContent  = cats[idx];
        } else {
            el.wheelCenterLabel.textContent = 'Select a category';
            el.wheelCenterName.textContent  = '';
        }
    });

    canvas.addEventListener('mouseleave', () => {
        hoveredSegment = -1;
        drawWheel(-1);
        el.wheelCenterLabel.textContent = 'Select a category';
        el.wheelCenterName.textContent  = '';
    });

    canvas.addEventListener('click', e => {
        const r   = canvas.getBoundingClientRect();
        const idx = getSegmentAt(e.clientX - r.left, e.clientY - r.top);
        if (idx < 0) return;
        showSubcategory(Object.keys(categoryMap)[idx]);
    });

    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => drawWheel(hoveredSegment));
}

// ─── Breadcrumb + table controls ─────────────────────────────────────────────
function initTableControls() {
    el.btnBackHome.addEventListener('click', showLanding);
    el.btnBackSub.addEventListener('click',  () => showSubcategory(activeCategory));

    el.tableSelect.addEventListener('change', triggerAutoQuery);
    el.thicknessFilter.addEventListener('input', triggerAutoQuery);
    el.multiplier.addEventListener('input', triggerAutoQuery);

    el.toggleConsole.addEventListener('change', e => {
        const on = e.target.checked;
        el.sqlConsole.disabled = !on;
        el.runSqlBtn.disabled  = !on;
        el.sqlConsole.classList.toggle('text-emerald-400', on);
        if (!on) triggerAutoQuery();
    });

    el.runSqlBtn.addEventListener('click', () => {
        const sql = el.sqlConsole.value.trim();
        if (sql) executeSQL(sql);
    });
}

// ─── Status helper ────────────────────────────────────────────────────────────
function updateEngineStatus(text, color) {
    const map = {
        amber: ['text-amber-400', 'bg-amber-400'],
        green: ['text-emerald-400', 'bg-emerald-400'],
        red:   ['text-rose-500',   'bg-rose-500'],
    };
    const [tc, dc] = map[color] || map.amber;
    el.engineStatus.className = `inline-flex items-center font-semibold ${tc}`;
    el.engineStatus.innerHTML = `<span class="w-2 h-2 rounded-full ${dc} mr-1.5"></span>${text}`;
}

// ─── Entry point ──────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', bootApp);
