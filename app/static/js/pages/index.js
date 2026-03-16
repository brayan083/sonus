const fileInput = document.getElementById('fileInput');
const fileInfo  = document.getElementById('fileInfo');
const submitBtn = document.getElementById('submitBtn');
const dropArea  = document.getElementById('dropArea');
const form      = document.getElementById('uploadForm');

function formatBytes(b) {
  if (b < 1024 * 1024) return (b / 1024).toFixed(1) + ' KB';
  return (b / (1024 * 1024)).toFixed(1) + ' MB';
}

fileInput.addEventListener('change', () => {
  const f = fileInput.files[0];
  if (f) {
    fileInfo.textContent = `📄 ${f.name}  (${formatBytes(f.size)})`;
    fileInfo.classList.add('visible');
    submitBtn.disabled = false;
  }
});

dropArea.addEventListener('dragover', (e) => { e.preventDefault(); dropArea.classList.add('dragover'); });
dropArea.addEventListener('dragleave', () => dropArea.classList.remove('dragover'));
dropArea.addEventListener('drop', (e) => {
  e.preventDefault();
  dropArea.classList.remove('dragover');
  fileInput.files = e.dataTransfer.files;
  fileInput.dispatchEvent(new Event('change'));
});

// Update device label when model changes
const modelSelect = document.querySelector('select[name="model"]');
const deviceLabel = document.getElementById('deviceLabel');
if (modelSelect && deviceLabel) {
  modelSelect.addEventListener('change', () => {
    deviceLabel.textContent = modelSelect.value === 'whisper-api' ? 'OpenAI Cloud' : 'Apple MPS';
  });
  deviceLabel.textContent = modelSelect.value === 'whisper-api' ? 'OpenAI Cloud' : 'Apple MPS';
}

form.addEventListener('submit', () => {
  submitBtn.disabled = true;
  submitBtn.textContent = 'Subiendo...';
  if (window.startJobPolling) window.startJobPolling();
});

// Check for active transcription jobs — polls only while jobs are active
(function pollActiveJobs() {
  const banner = document.getElementById('activeJobsBanner');
  let intervalId = null;

  async function check() {
    try {
      const res = await fetch('/active-jobs');
      const active = await res.json();
      if (active.length > 0) {
        const items = active.map(j => {
          const name = j.filename || 'archivo';
          const pct = j.progress > 0 ? ` (${j.progress}%)` : '';
          return `<a href="/result/${j.job_id}" class="btn btn-secondary" style="margin:0.25rem;">🔄 ${name}${pct}</a>`;
        }).join('');
        banner.innerHTML = `<div class="card" style="padding:1rem; text-align:center;">
          <p style="margin-bottom:0.5rem; font-weight:500;">Transcripción en progreso</p>${items}</div>`;
        banner.style.display = 'block';
        startPolling();
      } else {
        banner.style.display = 'none';
        stopPolling();
      }
    } catch(e) {}
  }

  function startPolling() {
    if (!intervalId) intervalId = setInterval(check, 2000);
  }

  function stopPolling() {
    if (intervalId) { clearInterval(intervalId); intervalId = null; }
  }

  // Expose globally so the upload form can kick off polling
  window.startJobPolling = () => { check(); startPolling(); };

  check();
})();
