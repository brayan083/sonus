const checkAll = document.getElementById('checkAll');
const bulkBar = document.getElementById('bulkBar');
const selectedCount = document.getElementById('selectedCount');

function getChecked() {
  return [...document.querySelectorAll('.row-check:checked')];
}

function updateBulkBar() {
  const checked = getChecked();
  selectedCount.textContent = checked.length;
  bulkBar.classList.toggle('visible', checked.length > 0);
  document.querySelectorAll('#historyBody tr').forEach(tr => {
    const cb = tr.querySelector('.row-check');
    tr.classList.toggle('selected', cb && cb.checked);
  });
  checkAll.indeterminate = checked.length > 0 && checked.length < document.querySelectorAll('.row-check').length;
  checkAll.checked = checked.length === document.querySelectorAll('.row-check').length;

  // Show summarize button only for 1-5 selections
  const btn = document.getElementById('btnSummarize');
  if (btn) btn.style.display = (checked.length >= 1 && checked.length <= 5) ? '' : 'none';
}

checkAll.addEventListener('change', () => {
  document.querySelectorAll('.row-check').forEach(cb => cb.checked = checkAll.checked);
  updateBulkBar();
});

document.getElementById('historyBody').addEventListener('change', e => {
  if (e.target.classList.contains('row-check')) updateBulkBar();
});

function clearSelection() {
  document.querySelectorAll('.row-check').forEach(cb => cb.checked = false);
  checkAll.checked = false;
  updateBulkBar();
}

function openDeleteModal() {
  const n = getChecked().length;
  document.querySelector('#deleteModalText strong').textContent = n;
  document.getElementById('deleteModal').classList.add('visible');
}

function closeDeleteModal() {
  document.getElementById('deleteModal').classList.remove('visible');
}

async function confirmDelete() {
  const ids = getChecked().map(cb => cb.value);
  closeDeleteModal();
  const res = await fetch('/delete', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ job_ids: ids })
  });
  if (res.ok) {
    ids.forEach(id => {
      const row = document.querySelector(`tr[data-job-id="${id}"]`);
      if (row) row.remove();
    });
    clearSelection();
    if (!document.querySelector('#historyBody tr')) location.reload();
  }
}

// Inline rename on double-click
document.getElementById('historyBody').addEventListener('dblclick', e => {
  const cell = e.target.closest('.name-cell');
  if (!cell) return;
  const span = cell.querySelector('.name-text');
  const input = cell.querySelector('.name-input');
  span.style.display = 'none';
  input.style.display = '';
  input.focus();
  input.select();

  function save() {
    const newName = input.value.trim();
    if (newName && newName !== span.textContent) {
      span.textContent = newName;
      fetch(`/rename/${cell.dataset.jobId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: newName })
      });
    }
    input.style.display = 'none';
    span.style.display = '';
  }

  input.addEventListener('blur', save, { once: true });
  input.addEventListener('keydown', e => {
    if (e.key === 'Enter') { e.preventDefault(); input.blur(); }
    if (e.key === 'Escape') { input.value = span.textContent; input.blur(); }
  });
});

// Close modal on backdrop click
document.getElementById('deleteModal').addEventListener('click', e => {
  if (e.target === e.currentTarget) closeDeleteModal();
});

// ── Multi-summarize with ordering ──────────────────────
function goSummarizeMulti() {
  const checked = getChecked();
  if (checked.length === 0 || checked.length > 5) return;

  if (checked.length === 1) {
    // Single transcription — go directly to existing summarize page
    window.location.href = '/summarize/' + checked[0].value;
    return;
  }

  // Multiple — show ordering modal
  const list = document.getElementById('orderList');
  list.innerHTML = '';
  checked.forEach(cb => {
    const tr = cb.closest('tr');
    const name = tr.querySelector('.name-text').textContent;
    const date = tr.querySelectorAll('td')[2].textContent.trim();
    const li = document.createElement('li');
    li.dataset.jobId = cb.value;
    li.innerHTML = `
      <span class="drag-handle">⠿</span>
      <span class="order-name">${name}</span>
      <span class="order-date">${date}</span>
      <div class="order-arrows">
        <button class="btn-arrow" onclick="moveItem(this,-1)" title="Subir">▲</button>
        <button class="btn-arrow" onclick="moveItem(this,1)" title="Bajar">▼</button>
      </div>`;
    list.appendChild(li);
  });
  document.getElementById('orderModal').classList.add('visible');
}

function moveItem(btn, dir) {
  const li = btn.closest('li');
  const list = li.parentElement;
  const items = [...list.children];
  const idx = items.indexOf(li);
  const target = idx + dir;
  if (target < 0 || target >= items.length) return;
  if (dir === -1) list.insertBefore(li, items[target]);
  else list.insertBefore(items[target], li);
}

function closeOrderModal() {
  document.getElementById('orderModal').classList.remove('visible');
}

function confirmOrder() {
  const items = [...document.querySelectorAll('#orderList li')];
  const ids = items.map(li => li.dataset.jobId);
  const params = new URLSearchParams();
  ids.forEach(id => params.append('ids', id));
  window.location.href = '/summarize_multi?' + params.toString();
}

// Close order modal on backdrop click
document.addEventListener('click', e => {
  const modal = document.getElementById('orderModal');
  if (modal && e.target === modal) closeOrderModal();
});
