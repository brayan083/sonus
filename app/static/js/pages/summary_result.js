const summaryId = document.currentScript.dataset.summaryId;
const processingEl = document.getElementById('processing');

function showError(msg) {
  processingEl.style.display = 'none';
  const err = document.getElementById('error');
  err.textContent = `Error: ${msg}`;
  err.style.display = 'block';
}

function renderMarkdown(text) {
  const lines = text.split('\n');
  const result = [];
  let inList = false;
  let listTag = '';

  function flush() {
    if (inList) {
      result.push(`</${listTag}>`);
      inList = false;
      listTag = '';
    }
  }

  function inline(t) {
    return t
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*(.+?)\*/g, '<em>$1</em>')
      .replace(/`(.+?)`/g, '<code>$1</code>');
  }

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const trimmed = line.trim();

    // Empty line
    if (!trimmed) {
      flush();
      continue;
    }

    // Headings (handles ###Text, ### **Text**, etc.)
    const hMatch = trimmed.match(/^(#{1,4})\s*(.+)$/);
    if (hMatch) {
      flush();
      const level = hMatch[1].length;
      // Strip wrapping bold/italic from heading text
      let hText = hMatch[2].replace(/^\*\*(.+?)\*\*$/, '$1').replace(/^\*(.+?)\*$/, '$1').trim();
      result.push(`<h${level}>${inline(hText)}</h${level}>`);
      continue;
    }

    // Bold line acting as section header (e.g. **Conceptos:**)
    const boldHeader = trimmed.match(/^\*\*(.+?)\*\*:?\s*$/);
    if (boldHeader && !inList) {
      flush();
      // Check if the bold content itself starts with ### (e.g. **### Title**)
      const innerH = boldHeader[1].match(/^(#{1,4})\s*(.+)$/);
      if (innerH) {
        result.push(`<h${innerH[1].length}>${inline(innerH[2])}</h${innerH[1].length}>`);
      } else {
        result.push(`<h3>${inline(boldHeader[1])}</h3>`);
      }
      continue;
    }

    // Unordered list items (-, *, •)
    const ulMatch = trimmed.match(/^[-*•]\s+(.+)$/);
    if (ulMatch) {
      if (!inList || listTag !== 'ul') {
        flush();
        result.push('<ul>');
        inList = true;
        listTag = 'ul';
      }
      result.push(`<li>${inline(ulMatch[1])}</li>`);
      continue;
    }

    // Ordered list items
    const olMatch = trimmed.match(/^\d+[.)]\s+(.+)$/);
    if (olMatch) {
      if (!inList || listTag !== 'ol') {
        flush();
        result.push('<ol>');
        inList = true;
        listTag = 'ol';
      }
      result.push(`<li>${inline(olMatch[1])}</li>`);
      continue;
    }

    // Lines starting with * as bullet (e.g. "* Text")
    const starBullet = trimmed.match(/^\*\s+(.+)$/);
    if (starBullet) {
      if (!inList || listTag !== 'ul') {
        flush();
        result.push('<ul>');
        inList = true;
        listTag = 'ul';
      }
      result.push(`<li>${inline(starBullet[1])}</li>`);
      continue;
    }

    // Regular paragraph
    flush();
    result.push(`<p>${inline(trimmed)}</p>`);
  }

  flush();
  return result.join('\n');
}

function showResult(data) {
  const meta = document.getElementById('summaryMeta');
  const types = { general: 'Resumen general', class_notes: 'Apuntes de clase', study_guide: 'Guía de estudio', combined: 'Combinado' };
  const lengths = { short: 'Corto', medium: 'Medio', detailed: 'Detallado' };
  document.getElementById('summaryTitle').textContent = data.summary_name || data.filename || '';
  meta.innerHTML = `
    <span class="tag">${types[data.summary_type] || data.summary_type}</span>
    <span class="tag">${lengths[data.length] || data.length}</span>
  `;
  document.getElementById('summaryContent').innerHTML = renderMarkdown(data.summary);
  processingEl.style.display = 'none';
  document.getElementById('result').style.display = 'flex';
}

function copySummary() {
  const text = document.getElementById('summaryContent').textContent;
  navigator.clipboard.writeText(text).then(() => {
    const msg = document.getElementById('copiedMsg');
    msg.classList.add('visible');
    setTimeout(() => msg.classList.remove('visible'), 2000);
  });
}

let pollTimer = setInterval(async () => {
  try {
    const res = await fetch(`/summary_status/${summaryId}`);
    const d = await res.json();

    if (d.message) {
      document.getElementById('processingText').textContent = d.message;
    }

    if (d.status === 'done') {
      clearInterval(pollTimer);
      const dataRes = await fetch(`/summary_download/${summaryId}?format=json`);
      const data = await dataRes.json();
      showResult(data);
      return;
    }

    if (d.status.startsWith('error')) {
      clearInterval(pollTimer);
      showError(d.status.replace('error: ', ''));
      return;
    }
  } catch(e) {
    // Network error — keep polling
  }
}, 2000);
