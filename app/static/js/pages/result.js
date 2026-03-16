const jobId = document.currentScript.dataset.jobId;

function fmt(sec) {
  const h = Math.floor(sec / 3600).toString().padStart(2,'0');
  const m = Math.floor((sec % 3600) / 60).toString().padStart(2,'0');
  const s = Math.floor(sec % 60).toString().padStart(2,'0');
  return `${h}:${m}:${s}`;
}

const progressTrack = document.getElementById('progressTrack');
const progressFill  = document.getElementById('progressFill');
const progressPct   = document.getElementById('progressPct');
const progressLabel = document.getElementById('progressLabel');
const tbody         = document.getElementById('tbody');
const processingEl  = document.getElementById('processing');

function showError(msg) {
  processingEl.style.display = 'none';
  const err = document.getElementById('error');
  err.textContent = `Error: ${msg}`;
  err.style.display = 'block';
}

function showResult(data) {
  const segments = data.segments || [];
  const duracion = data.duration_sec || 0;

  const filename = data.filename || '';
  const model = data.model || '';

  document.getElementById('stats').innerHTML = `
    ${filename ? `<h2 class="result-title">${filename}</h2>` : ''}
    <div class="stat-cards">
      <div class="stat-card">
        <span class="stat-label">Segmentos</span>
        <span class="stat-value">${segments.length}</span>
      </div>
      <div class="stat-card">
        <span class="stat-label">Duracion</span>
        <span class="stat-value">${fmt(duracion)}</span>
      </div>
      ${model ? `<div class="stat-card">
        <span class="stat-label">Modelo</span>
        <span class="stat-value" style="font-size:0.95rem;">${model}</span>
      </div>` : ''}
    </div>
  `;

  segments.forEach((seg, i) => {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td class="idx">${i + 1}</td>
      <td class="time">${fmt(seg.start)}</td>
      <td class="time">${fmt(seg.end)}</td>
      <td class="text-cell">${seg.text}</td>
    `;
    tbody.appendChild(tr);
  });

  processingEl.style.display = 'none';
  document.getElementById('result').style.display = 'flex';
}

// ── Cancel ──
async function cancelJob() {
  const btn = document.getElementById('cancelBtn');
  btn.disabled = true;
  btn.textContent = 'Cancelando…';
  try {
    await fetch(`/cancel/${jobId}`, { method: 'POST' });
  } catch(e) {}
}

// ── Try to load finished result directly ──
async function tryLoadResult() {
  try {
    const dataRes = await fetch(`/download/${jobId}?format=json`);
    if (dataRes.ok) {
      const data = await dataRes.json();
      if (data.segments) {
        showResult(data);
        return true;
      }
    }
  } catch(e) {}
  return false;
}

// ── Handle status check ──
async function checkStatus() {
  const res = await fetch(`/status/${jobId}`);
  const d = await res.json();

  if (d.status === 'done' || d.status === 'not_found') {
    // Job done or server restarted — try loading the JSON file
    if (await tryLoadResult()) return true;
    if (d.status === 'not_found') {
      showError('Transcripción no encontrada.');
      return true;
    }
  }

  if (d.status === 'cancelled') {
    processingEl.style.display = 'none';
    const err = document.getElementById('error');
    err.innerHTML = '<div class="card" style="text-align:center; padding:2rem;"><p style="font-size:1.1rem; margin-bottom:1rem;">Transcripción cancelada</p><a href="/" class="btn btn-primary">⬆️ &nbsp;Nueva transcripción</a></div>';
    err.style.display = 'block';
    return true;
  }

  if (d.status.startsWith('error')) {
    showError(d.status.replace('error: ', ''));
    return true;
  }

  if (d.progress > 0) {
    progressTrack.classList.remove('indeterminate');
    progressFill.style.width = d.progress + '%';
    progressPct.textContent = d.progress + '%';
    progressLabel.textContent = `Transcribiendo… ${d.progress}%`;
  }
  return false;
}

// ── Initial check + poll ──
(async function init() {
  try {
    if (await checkStatus()) return;
  } catch(e) {}
  // Still processing — start polling
  let pollTimer = setInterval(async () => {
    try {
      if (await checkStatus()) clearInterval(pollTimer);
    } catch(e) {}
  }, 1500);
})();
