'use strict';

let useIndex = false;

window.addEventListener('DOMContentLoaded', () => {
  checkDb();
  loadServerInfo();
  setMode(false);
});

// ── Symbol helpers ─────────────────────────────────────────
function setSym(s) {
  document.getElementById('symInput').value = s;
  document.querySelectorAll('.chip').forEach(c =>
    c.classList.toggle('active', c.textContent.trim() === s)
  );
}

function getSym() {
  return (document.getElementById('symInput').value || 'BTC').toUpperCase();
}

// ── Mode toggle ────────────────────────────────────────────
function setMode(on) {
  useIndex = on;
  const off = document.getElementById('modeOff');
  const onB = document.getElementById('modeOn');
  off.className = 'mode-btn' + (!on ? ' active-off' : '');
  onB.className = 'mode-btn' + (on  ? ' active-on'  : '');
}

// ── DB connection check ────────────────────────────────────
function checkDb() {
  fetch('/api/server-info')
    .then(r => r.json())
    .then(d => {
      const dot  = document.getElementById('connDot');
      const txt  = document.getElementById('connText');
      if (d.status === 'ok') {
        dot.classList.add('online');
        txt.textContent = 'Connected';
      } else {
        txt.textContent = 'Error';
      }
    })
    .catch(() => {
      document.getElementById('connText').textContent = 'Offline';
    });
}

// ── Single benchmark ───────────────────────────────────────
async function runBenchmark() {
  const sym = getSym();
  const btn = document.getElementById('runBtn');
  btn.textContent = 'Running…'; btn.disabled = true;

  try {
    const r    = await post('/api/benchmark', { symbol: sym, use_index: useIndex });
    const data = r.data;
    renderMetrics(data);
    renderExplain(data, sym);
    toast(`${data.elapsed_ms} ms · ${data.rows_returned} rows returned`);
  } catch (e) {
    toast(e.message, 'err');
  } finally {
    btn.textContent = 'Run Query'; btn.disabled = false;
  }
}

// ── Compare both phases ────────────────────────────────────
async function runCompare() {
  const sym = getSym();
  toast('Running both phases…');
  try {
    const r = await post('/api/compare', { symbol: sym });
    renderMetrics(useIndex ? r.after : r.before);
    renderExplain(useIndex ? r.after : r.before, sym);
    renderSpeedup(r);
    toast(`${r.speedup}× faster · Before: ${r.before.elapsed_ms} ms · After: ${r.after.elapsed_ms} ms`, 'ok');
  } catch (e) {
    toast(e.message, 'err');
  }
}

// ── Render metrics ─────────────────────────────────────────
function renderMetrics(d) {
  const lat = d.elapsed_ms;
  setEl('mLatency', lat, lat < 20 ? 'fast' : 'slow');
  setBar('fLatency', Math.min(lat / 600 * 100, 100),
    lat < 20 ? 'var(--green)' : lat < 100 ? 'var(--amber)' : 'var(--red)');

  const rows = d.rows_scanned;
  setEl('mRows', rows.toLocaleString(), rows > 50000 ? 'slow' : 'fast');
  setBar('fRows', rows / 100000 * 100,
    rows > 50000 ? 'var(--red)' : 'var(--green)');

  setEl('mReturned', d.rows_returned.toLocaleString());

  const good = ['ref','range','eq_ref','const'].includes(d.scan_type);
  const st = document.getElementById('mScanType');
  st.textContent = d.scan_type;
  st.className   = 'metric-val type-val ' + (good ? 'good' : 'bad');
  document.getElementById('mScanDesc').textContent = good
    ? 'Index used — fast' : 'Full table scan — slow';
}

function setEl(id, val, cls) {
  const el = document.getElementById(id);
  el.textContent = val;
  if (cls) el.className = 'metric-val ' + cls;
}

function setBar(id, pct, color) {
  const el = document.getElementById(id);
  el.style.width    = pct + '%';
  el.style.background = color;
}

// ── Render EXPLAIN ─────────────────────────────────────────
function renderExplain(d, sym) {
  document.getElementById('eSymbol').textContent = sym;

  const good = ['ref','range','eq_ref','const'].includes(d.scan_type);
  const badge = document.getElementById('eBadge');
  badge.textContent = good ? 'Index used' : 'Full table scan';
  badge.className   = 'badge ' + (good ? 'good' : 'bad');

  const e = d.explain;
  document.getElementById('explainBody').innerHTML = `
    <tr>
      <td>${e.id || 1}</td>
      <td>${e.select_type || 'SIMPLE'}</td>
      <td>${e.table || 'market_records'}</td>
      <td class="${good ? 'td-good' : 'td-bad'}">${e.type || d.scan_type}</td>
      <td>${e.possible_keys || 'NULL'}</td>
      <td>${e.key || 'NULL'}</td>
      <td>${e.key_len || 'NULL'}</td>
      <td>${e.ref || 'NULL'}</td>
      <td>${(e.rows || d.rows_scanned).toLocaleString()}</td>
      <td>${e.Extra || ''}</td>
    </tr>`;
}

// ── Render speedup ─────────────────────────────────────────
function renderSpeedup(r) {
  const card = document.getElementById('speedupCard');
  card.style.display = 'flex';
  document.getElementById('speedupNum').textContent = r.speedup + '×';
  document.getElementById('sBefore').textContent    = r.before.elapsed_ms;
  document.getElementById('sAfter').textContent     = r.after.elapsed_ms;
  document.getElementById('sRowsBefore').textContent = r.before.rows_scanned.toLocaleString();
  document.getElementById('sRowsAfter').textContent  = r.after.rows_scanned.toLocaleString();

  const maxMs = Math.max(r.before.elapsed_ms, r.after.elapsed_ms, 1);
  const hB    = Math.max(r.before.elapsed_ms / maxMs * 70, 4);
  const hA    = Math.max(r.after.elapsed_ms  / maxMs * 70, 4);

  document.getElementById('speedupBars').innerHTML = `
    <div class="speedup-bar-wrap">
      <div class="speedup-bar-val">${r.before.elapsed_ms} ms</div>
      <div class="speedup-bar-fill b" id="_bB" style="height:0px"></div>
      <div class="speedup-bar-lbl">No Index</div>
    </div>
    <div class="speedup-bar-wrap">
      <div class="speedup-bar-val">${r.after.elapsed_ms} ms</div>
      <div class="speedup-bar-fill a" id="_bA" style="height:0px"></div>
      <div class="speedup-bar-lbl">B-Tree Index</div>
    </div>`;

  requestAnimationFrame(() => setTimeout(() => {
    document.getElementById('_bB').style.height = hB + 'px';
    document.getElementById('_bA').style.height = hA + 'px';
  }, 60));
}

// ── Server info ────────────────────────────────────────────
async function loadServerInfo() {
  try {
    const r = await fetch('/api/server-info').then(x => x.json());
    if (r.status !== 'ok') return;

    const v  = r.variables || {};
    const ts = r.table_stats || {};

    const bp = parseInt(v.innodb_buffer_pool_size || 0);
    document.getElementById('svrPool').textContent =
      bp >= 1073741824 ? (bp / 1073741824).toFixed(1) + ' GB'
                       : Math.round(bp / 1048576) + ' MB';

    document.getElementById('svrConn').textContent = v.max_connections || '—';
    document.getElementById('svrVer').textContent  = v.version || '8.0';

    const dMB = (ts.DATA_LENGTH  / 1048576).toFixed(1);
    const iMB = (ts.INDEX_LENGTH / 1048576).toFixed(1);
    document.getElementById('svrSize').textContent = `${dMB} MB / ${iMB} MB`;

    // Index tags
    const seen = new Set();
    const tags = (r.indexes || [])
      .filter(ix => { if (seen.has(ix.Key_name)) return false; seen.add(ix.Key_name); return true; })
      .map(ix => `<span class="idx-tag">${ix.Key_name} (${ix.Column_name})</span>`)
      .join('');
    document.getElementById('indexTags').innerHTML = tags || 'No indexes';

    // Audit log
    renderAudit(r.audit_log || []);

  } catch (e) {
    console.warn('Server info error', e);
  }
}

// ── Audit log ──────────────────────────────────────────────
function renderAudit(rows) {
  const tbody = document.getElementById('auditBody');
  if (!rows.length) {
    tbody.innerHTML = '<tr><td colspan="7" class="empty-row">No audit entries yet. Trigger fires on price updates.</td></tr>';
    return;
  }
  tbody.innerHTML = rows.map(r => {
    const delta = ((r.new_price - r.old_price) / Math.max(r.old_price, 0.000001) * 100).toFixed(2);
    const cls   = parseFloat(delta) >= 0 ? 'delta-pos' : 'delta-neg';
    const sign  = parseFloat(delta) >= 0 ? '+' : '';
    const fmt   = n => Number(n).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 6 });
    return `<tr>
      <td>${r.log_id}</td>
      <td><strong>${r.symbol}</strong></td>
      <td>$${fmt(r.old_price)}</td>
      <td>$${fmt(r.new_price)}</td>
      <td class="${cls}">${sign}${delta}%</td>
      <td>${r.changed_at}</td>
      <td>${r.changed_by || 'system'}</td>
    </tr>`;
  }).join('');
}

// ── Helpers ────────────────────────────────────────────────
async function post(url, body) {
  const r = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  const d = await r.json();
  if (d.status !== 'ok') throw new Error(d.message || 'Unknown error');
  return d;
}

function toast(msg, type = '') {
  const el = document.getElementById('toast');
  el.textContent = msg;
  el.className   = 'toast show ' + type;
  clearTimeout(el._t);
  el._t = setTimeout(() => el.classList.remove('show'), 4500);
}

document.getElementById('symInput').addEventListener('input', function () {
  document.querySelectorAll('.chip').forEach(c =>
    c.classList.toggle('active', c.textContent.trim() === this.value.toUpperCase())
  );
});