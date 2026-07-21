/* ─────────────────────────────────────────────────────────────────
   dashboard.js  —  SSE client + pipeline UI logic
   ───────────────────────────────────────────────────────────────── */

// ── State ──────────────────────────────────────────────────────────
const state = { adaptive: null, standard: null };
let activeSource = 'file'; // 'file' | 'huggingface'

// ── SSE connection — one persistent connection for all live updates ─
const evtSource = new EventSource('/stream');

evtSource.onmessage = (e) => {
  const msg = JSON.parse(e.data);

  switch (msg.type) {

    case 'threat':
      updateThreatBadge(msg.state);
      break;

    case 'progress':
      updateProgress(msg.mode, msg.current, msg.total);
      break;

    case 'done':
      // The full result also comes back via the fetch() response,
      // but we handle it here too so progress bar completes cleanly.
      updateProgress(msg.mode, msg.total || 100, msg.total || 100);
      break;

    case 'heartbeat':
      // keep-alive — nothing to do
      break;
  }
};

evtSource.onerror = () => {
  setThreatBadge('waiting', '🔌 Disconnected');
};

// ── Threat badge ────────────────────────────────────────────────────
function updateThreatBadge(threatState) {
  if (threatState === 1) {
    setThreatBadge('danger', '⚠️ HIGH THREAT DETECTED');
  } else {
    setThreatBadge('safe', '🟢 Network Clean');
  }
}

function setThreatBadge(cls, label) {
  const badge = document.getElementById('threatBadge');
  badge.className = 'threat-badge ' + cls;
  document.getElementById('threatLabel').textContent = label;
}

// ── Source tab switch ────────────────────────────────────────────────
function switchSource(src) {
  activeSource = src;

  document.getElementById('tabFile').classList.toggle('active', src === 'file');
  document.getElementById('tabHF').classList.toggle('active',   src === 'huggingface');
  document.getElementById('fileSection').style.display = src === 'file'          ? '' : 'none';
  document.getElementById('hfSection').style.display   = src === 'huggingface'   ? '' : 'none';

  if (src === 'file') {
    // Re-check file selection
    const hasFile = !!document.getElementById('fileInput').files[0];
    document.getElementById('adaptiveBtn').disabled = !hasFile;
    document.getElementById('standardBtn').disabled = !hasFile;
  } else {
    // HF always has a default dataset — enable immediately
    document.getElementById('adaptiveBtn').disabled = false;
    document.getElementById('standardBtn').disabled = false;
  }
}

// ── HuggingFace input live validation ────────────────────────────────
function onHFInput() {
  const val = document.getElementById('hfDataset').value.trim();
  const ok  = val.length > 0;
  document.getElementById('adaptiveBtn').disabled = !ok;
  document.getElementById('standardBtn').disabled = !ok;
}

// ── File picker ─────────────────────────────────────────────────────
document.getElementById('fileInput').addEventListener('change', function () {
  const name = this.files[0] ? this.files[0].name : 'No file selected';
  document.getElementById('fileNameDisplay').textContent = name;
  const hasFile = !!this.files[0];
  document.getElementById('adaptiveBtn').disabled = !hasFile;
  document.getElementById('standardBtn').disabled = !hasFile;
});

// ── Progress helpers ────────────────────────────────────────────────
function showProgress(mode) {
  document.getElementById('progressRow').style.display = 'flex';
  const item = document.getElementById(mode + 'ProgressItem');
  item.style.display = 'flex';
  updateProgress(mode, 0, 1);
}

function updateProgress(mode, current, total) {
  const pct = total ? Math.round((current / total) * 100) : 0;
  document.getElementById(mode + 'ProgressFill').style.width = pct + '%';
  document.getElementById(mode + 'ProgressPct').textContent = pct + '%';
}

// ── Run pipeline ────────────────────────────────────────────────────
async function runPipeline(mode) {
  let endpoint, form;

  if (activeSource === 'file') {
    const fileInput = document.getElementById('fileInput');
    if (!fileInput.files[0]) { alert('Please select a file first.'); return; }
    endpoint = '/run_' + mode;
    form = new FormData();
    form.append('file', fileInput.files[0]);

  } else {
    const dataset = document.getElementById('hfDataset').value.trim();
    const limit   = parseInt(document.getElementById('hfLimit').value) || 100;
    if (!dataset) { alert('Please enter a HuggingFace dataset name.'); return; }
    endpoint = '/run_' + mode + '_hf';
    form = new FormData();
    form.append('dataset_name', dataset);
    form.append('limit', limit);
  }

  const btn   = document.getElementById(mode + 'Btn');
  const panel = document.getElementById(mode + 'Content');

  const origLabel = btn.innerHTML;
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner"></span> Processing…';
  panel.innerHTML = '<div class="placeholder"><span class="spinner"></span>&nbsp; Encrypting packets…</div>';

  showProgress(mode);

  try {
    const res  = await fetch(endpoint, { method: 'POST', body: form });
    const data = await res.json();
    if (data.error) throw new Error(data.error);

    state[mode] = data;
    panel.innerHTML = mode === 'adaptive' ? renderAdaptive(data) : renderStandard(data);

  } catch (err) {
    panel.innerHTML = `<div class="placeholder" style="color:#e05c5c;">❌ ${err.message}</div>`;
  } finally {
    btn.disabled = false;
    btn.innerHTML = origLabel;
    checkCompareReady();
  }
}

// ── Render adaptive results ─────────────────────────────────────────
function renderAdaptive(d) {
  const tc   = d.tier_counts || {};
  const t1   = tc['Tier 1 (ChaCha20)'] || 0;
  const t2   = tc['Tier 2 (AES-CTR)']  || 0;
  const t3   = tc['Tier 3 (ECDH+AES)'] || 0;
  const n    = d.total_packets || 1;

  const rows = (d.packet_log || []).slice(0, 20).map(p => `
    <tr>
      <td>${p.id}</td>
      <td>${p.size_kb}</td>
      <td><span class="badge ${p.sensitive === 'YES' ? 'badge-yes' : 'badge-no'}">${p.sensitive}</span></td>
      <td><span class="badge ${cipherBadge(p.cipher)}">${p.cipher}</span></td>
      <td><span class="badge ${p.threat === 'HIGH' ? 'badge-threat' : 'badge-safe'}">${p.threat}</span></td>
      <td>${p.latency_ms}</td>
      <td>${p.energy_uj}</td>
    </tr>`).join('');

  return `
    <div class="stat-grid">
      <div class="stat">
        <div class="stat-label">Packets</div>
        <div class="stat-value">${d.total_packets}</div>
      </div>
      <div class="stat">
        <div class="stat-label">Total Energy</div>
        <div class="stat-value">${d.total_energy_uj}<span class="stat-unit">µJ</span></div>
        <div class="stat-sub">avg ${d.avg_energy_uj} µJ/pkt</div>
      </div>
      <div class="stat">
        <div class="stat-label">Total Latency</div>
        <div class="stat-value">${d.total_latency_ms}<span class="stat-unit">ms</span></div>
        <div class="stat-sub">avg ${d.avg_latency_ms} ms/pkt</div>
      </div>
    </div>

    <div class="tier-section">
      <div class="section-heading">Cipher Tier Distribution</div>
      ${tierBar('Tier 1 · ChaCha20', t1, n, 'bar-c20')}
      ${tierBar('Tier 2 · AES-CTR',  t2, n, 'bar-aes')}
      ${tierBar('Tier 3 · ECDH+AES', t3, n, 'bar-ecdh')}
    </div>

    <div class="log-section">
      <div class="section-heading">Packet Log (first 20)</div>
      <div class="table-wrap">
        <table>
          <thead><tr>
            <th>#</th><th>Size KB</th><th>Sensitive</th>
            <th>Cipher</th><th>Threat</th><th>Latency ms</th><th>Energy µJ</th>
          </tr></thead>
          <tbody>${rows}</tbody>
        </table>
      </div>
    </div>`;
}

// ── Render standard results ─────────────────────────────────────────
function renderStandard(d) {
  const rows = (d.packet_log || []).slice(0, 20).map(p => `
    <tr>
      <td>${p.id}</td>
      <td>${p.size_kb}</td>
      <td><span class="badge badge-t3">${p.cipher}</span></td>
      <td>${p.latency_ms}</td>
      <td>${p.energy_uj}</td>
    </tr>`).join('');

  return `
    <div class="stat-grid">
      <div class="stat">
        <div class="stat-label">Packets</div>
        <div class="stat-value">${d.total_packets}</div>
      </div>
      <div class="stat">
        <div class="stat-label">Total Energy</div>
        <div class="stat-value">${d.total_energy_uj}<span class="stat-unit">µJ</span></div>
        <div class="stat-sub">avg ${d.avg_energy_uj} µJ/pkt</div>
      </div>
      <div class="stat">
        <div class="stat-label">Total Latency</div>
        <div class="stat-value">${d.total_latency_ms}<span class="stat-unit">ms</span></div>
        <div class="stat-sub">avg ${d.avg_latency_ms} ms/pkt</div>
      </div>
    </div>

    <div class="tier-section">
      <div class="section-heading">Cipher Used (always Tier 3)</div>
      ${tierBar('Tier 3 · ECDH+AES', d.total_packets, d.total_packets, 'bar-ecdh')}
    </div>

    <div class="log-section">
      <div class="section-heading">Packet Log (first 20)</div>
      <div class="table-wrap">
        <table>
          <thead><tr>
            <th>#</th><th>Size KB</th><th>Cipher</th>
            <th>Latency ms</th><th>Energy µJ</th>
          </tr></thead>
          <tbody>${rows}</tbody>
        </table>
      </div>
    </div>`;
}

// ── Compare ─────────────────────────────────────────────────────────
async function runCompare() {
  const section = document.getElementById('compareSection');
  section.style.display = 'none';

  try {
    const res = await fetch('/compare_data');
    const d   = await res.json();
    if (d.error) throw new Error(d.error);

    // Summary cards
    document.getElementById('compareCards').innerHTML = `
      <div class="cmp-card">
        <div class="cmp-label">Energy Saved</div>
        <div class="cmp-val green">${d.energy_saved_uj}</div>
        <div class="cmp-unit">µJ total</div>
      </div>
      <div class="cmp-card">
        <div class="cmp-label">Energy Reduction</div>
        <div class="cmp-val green">${d.energy_saving_pct}%</div>
        <div class="cmp-unit">less energy consumed</div>
      </div>
      <div class="cmp-card">
        <div class="cmp-label">Latency Saved</div>
        <div class="cmp-val green">${d.latency_saved_ms}</div>
        <div class="cmp-unit">ms total</div>
      </div>
      <div class="cmp-card">
        <div class="cmp-label">Speed Improvement</div>
        <div class="cmp-val green">${d.latency_saving_pct}%</div>
        <div class="cmp-unit">faster overall</div>
      </div>`;

    // Side-by-side table
    const a = d.adaptive, s = d.standard;
    document.getElementById('sideTableBody').innerHTML = `
      <tr>
        <td>Total Packets</td>
        <td>${a.total_packets}</td>
        <td>${s.total_packets}</td>
        <td>—</td>
      </tr>
      <tr>
        <td>Total Energy (µJ)</td>
        <td class="winner">${a.total_energy_uj}</td>
        <td class="loser">${s.total_energy_uj}</td>
        <td class="winner">− ${d.energy_saved_uj} µJ &nbsp;(${d.energy_saving_pct}%)</td>
      </tr>
      <tr>
        <td>Avg Energy / Packet (µJ)</td>
        <td class="winner">${a.avg_energy_uj}</td>
        <td class="loser">${s.avg_energy_uj}</td>
        <td class="winner">${d.energy_saving_pct}% less</td>
      </tr>
      <tr>
        <td>Total Latency (ms)</td>
        <td class="winner">${a.total_latency_ms}</td>
        <td class="loser">${s.total_latency_ms}</td>
        <td class="winner">− ${d.latency_saved_ms} ms &nbsp;(${d.latency_saving_pct}%)</td>
      </tr>
      <tr>
        <td>Avg Latency / Packet (ms)</td>
        <td class="winner">${a.avg_latency_ms}</td>
        <td class="loser">${s.avg_latency_ms}</td>
        <td class="winner">${d.latency_saving_pct}% faster</td>
      </tr>
      <tr>
        <td>Cipher Strategy</td>
        <td>KNN + Q-Learning (3 tiers)</td>
        <td>Always ECDH+AES</td>
        <td>—</td>
      </tr>`;

    // Verdict
    const tc = a.tier_counts || {};
    const t1 = tc['Tier 1 (ChaCha20)'] || 0;
    const t2 = tc['Tier 2 (AES-CTR)']  || 0;
    const t3 = tc['Tier 3 (ECDH+AES)'] || 0;
    const n  = a.total_packets || 1;
    document.getElementById('verdictText').innerHTML =
      `✅ <strong>Adaptive encryption saved ${d.energy_saving_pct}% energy and was ` +
      `${d.latency_saving_pct}% faster</strong> vs always-on heavy encryption.<br><br>` +
      `Out of <strong>${n}</strong> packets — ` +
      `<strong>${t1}</strong> used lightweight ChaCha20 (Tier 1), ` +
      `<strong>${t2}</strong> used AES-CTR (Tier 2), and ` +
      `<strong>${t3}</strong> used ECDH+AES (Tier 3) only when sensitivity or live ` +
      `network threat demanded it.`;

    section.style.display = 'block';
    section.scrollIntoView({ behavior: 'smooth' });

  } catch (err) {
    alert('Comparison error: ' + err.message);
  }
}

// ── Reset ───────────────────────────────────────────────────────────
function resetAll() {
  state.adaptive = state.standard = null;

  ['adaptive', 'standard'].forEach(m => {
    document.getElementById(m + 'Content').innerHTML =
      `<div class="placeholder">Run the ${m} pipeline to see results here.</div>`;
    document.getElementById(m + 'ProgressItem').style.display = 'none';
    updateProgress(m, 0, 1);
  });

  document.getElementById('progressRow').style.display   = 'none';
  document.getElementById('compareSection').style.display = 'none';

  const fi = document.getElementById('fileInput');
  fi.value = '';
  document.getElementById('fileNameDisplay').textContent = 'No file selected';

  // Reset HF inputs to defaults
  document.getElementById('hfDataset').value = 'ai4privacy/pii-masking-300k';
  document.getElementById('hfLimit').value   = '100';

  // Disable run buttons (file mode needs a new file selected)
  switchSource('file');

  checkCompareReady();
  fetch('/reset', { method: 'POST' });
}

// ── Helpers ─────────────────────────────────────────────────────────
function checkCompareReady() {
  const ready = state.adaptive !== null && state.standard !== null;
  document.getElementById('compareBtn').disabled = !ready;
  const hint = document.getElementById('compareHint');
  hint.textContent = ready
    ? '✅ Both pipelines complete — click Compare.'
    : 'Run both pipelines to enable comparison.';
  hint.className = 'compare-hint' + (ready ? ' ready' : '');
}

function tierBar(label, count, total, cls) {
  const pct = total ? Math.round((count / total) * 100) : 0;
  return `
    <div class="tier-row">
      <span class="tier-label">${label}</span>
      <div class="bar-track">
        <div class="bar-fill ${cls}" style="width:${pct}%"></div>
      </div>
      <span class="tier-count">${count}</span>
    </div>`;
}

function cipherBadge(cipher) {
  if (cipher.includes('ChaCha20')) return 'badge-t1';
  if (cipher.includes('AES-CTR'))  return 'badge-t2';
  return 'badge-t3';
}
