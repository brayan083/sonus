const socket = io();
const recordBtn = document.getElementById('recordBtn');
const micIcon = document.getElementById('micIcon');
const stopIcon = document.getElementById('stopIcon');
const rtStatus = document.getElementById('rtStatus');
const transcript = document.getElementById('transcript');
const visualizer = document.getElementById('visualizer');
const audioCanvas = document.getElementById('audioCanvas');
const timerEl = document.getElementById('timer');
const copyBtn = document.getElementById('copyBtn');
const clearBtn = document.getElementById('clearBtn');
const saveBtn = document.getElementById('saveBtn');
const langSelect = document.getElementById('rtLanguage');
const intervalSelect = document.getElementById('rtInterval');
const modelSelect = document.getElementById('rtModel');
const sourceSelect = document.getElementById('rtSource');

let mediaRecorder = null;
let audioContext = null;
let analyser = null;
let animFrameId = null;
let timerInterval = null;
let seconds = 0;
let isRecording = false;
let chunkInterval = null;
let hasContent = false;
let segments = [];
let elapsedAtChunkStart = 0;

// --- Recording ---
recordBtn.addEventListener('click', async () => {
  if (isRecording) {
    stopRecording();
  } else {
    await startRecording();
  }
});

let mixCtx = null; // AudioContext used for mixing streams

async function getAudioStream() {
  const source = sourceSelect.value;

  if (source === 'screen' || source === 'both') {
    const displayStream = await navigator.mediaDevices.getDisplayMedia({
      video: true,
      audio: true,
    });
    displayStream.getVideoTracks().forEach(t => t.stop());
    const screenAudioTracks = displayStream.getAudioTracks();
    if (screenAudioTracks.length === 0) {
      throw new Error('No se seleccionó audio. Asegúrate de marcar "Compartir audio" en el diálogo.');
    }

    if (source === 'both') {
      const micStream = await navigator.mediaDevices.getUserMedia({ audio: true });
      // Mix both streams using Web Audio API
      mixCtx = new AudioContext();
      const dest = mixCtx.createMediaStreamDestination();
      mixCtx.createMediaStreamSource(new MediaStream(screenAudioTracks)).connect(dest);
      mixCtx.createMediaStreamSource(micStream).connect(dest);
      // Store original streams so we can stop them later
      dest.stream._sourceStreams = [displayStream, micStream];
      return dest.stream;
    }

    return new MediaStream(screenAudioTracks);
  }

  return await navigator.mediaDevices.getUserMedia({ audio: true });
}

async function startRecording() {
  try {
    const stream = await getAudioStream();
    isRecording = true;

    // UI updates
    recordBtn.classList.add('recording');
    micIcon.style.display = 'none';
    stopIcon.style.display = 'block';
    rtStatus.textContent = 'Grabando...';
    rtStatus.classList.add('active');
    visualizer.style.display = 'flex';
    timerEl.style.display = 'block';

    // Clear placeholder
    const placeholder = transcript.querySelector('.rt-placeholder');
    if (placeholder) placeholder.remove();

    // Audio visualization
    audioContext = new AudioContext();
    const source = audioContext.createMediaStreamSource(stream);
    analyser = audioContext.createAnalyser();
    analyser.fftSize = 256;
    source.connect(analyser);
    drawVisualizer();

    // Timer
    seconds = 0;
    updateTimer();
    timerInterval = setInterval(() => { seconds++; updateTimer(); }, 1000);

    // MediaRecorder — send chunks at interval
    mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm;codecs=opus' });
    let chunks = [];

    mediaRecorder.ondataavailable = (e) => {
      if (e.data.size > 0) chunks.push(e.data);
    };

    mediaRecorder.onstop = () => {
      if (chunks.length > 0) {
        sendChunk(new Blob(chunks, { type: 'audio/webm' }), elapsedAtChunkStart);
        chunks = [];
      }
    };

    elapsedAtChunkStart = 0;
    mediaRecorder.start();

    // Periodically stop/restart to send chunks
    const interval = parseInt(intervalSelect.value, 10);
    chunkInterval = setInterval(() => {
      if (mediaRecorder && mediaRecorder.state === 'recording') {
        mediaRecorder.stop();
        // Restart after a brief pause
        setTimeout(() => {
          if (isRecording && mediaRecorder) {
            elapsedAtChunkStart = seconds;
            chunks = [];
            mediaRecorder.start();
          }
        }, 100);
      }
    }, interval);

  } catch (err) {
    rtStatus.textContent = 'Error: no se pudo acceder al micrófono';
    console.error('Mic error:', err);
  }
}

function stopRecording() {
  isRecording = false;

  if (chunkInterval) { clearInterval(chunkInterval); chunkInterval = null; }
  if (timerInterval) { clearInterval(timerInterval); timerInterval = null; }
  if (animFrameId) { cancelAnimationFrame(animFrameId); animFrameId = null; }

  if (mediaRecorder && mediaRecorder.state !== 'inactive') {
    mediaRecorder.stop();
  }

  // Stop all tracks (including source streams from mixed mode)
  if (mediaRecorder && mediaRecorder.stream) {
    if (mediaRecorder.stream._sourceStreams) {
      mediaRecorder.stream._sourceStreams.forEach(s => s.getTracks().forEach(t => t.stop()));
    }
    mediaRecorder.stream.getTracks().forEach(t => t.stop());
  }

  if (mixCtx) { mixCtx.close(); mixCtx = null; }
  if (audioContext) { audioContext.close(); audioContext = null; }

  recordBtn.classList.remove('recording');
  micIcon.style.display = 'block';
  stopIcon.style.display = 'none';
  rtStatus.textContent = 'Grabación detenida';
  rtStatus.classList.remove('active');
  visualizer.style.display = 'none';
  timerEl.style.display = 'none';

  socket.emit('stop_realtime');
}

function sendChunk(blob, chunkStartTime) {
  blob.arrayBuffer().then(buf => {
    socket.emit('audio_chunk', {
      audio: buf,
      language: langSelect.value,
      model: modelSelect.value,
      timeOffset: chunkStartTime,
    });
    rtStatus.textContent = isRecording ? 'Procesando audio...' : 'Procesando último fragmento...';
  });
}

// --- Socket events ---
socket.on('transcription', (data) => {
  const placeholder = transcript.querySelector('.rt-placeholder');
  if (placeholder) placeholder.remove();

  // Store segment with absolute timestamps
  segments.push({
    start: data.start + (data.timeOffset || 0),
    end: data.end + (data.timeOffset || 0),
    text: data.text,
  });

  const span = document.createElement('span');
  span.className = 'rt-segment new';
  span.textContent = data.text + ' ';
  transcript.appendChild(span);
  transcript.scrollTop = transcript.scrollHeight;

  hasContent = true;
  copyBtn.disabled = false;
  clearBtn.disabled = false;
  saveBtn.disabled = false;

  rtStatus.textContent = isRecording ? 'Grabando...' : 'Presiona para grabar';

  setTimeout(() => span.classList.remove('new'), 400);
});

socket.on('transcription_error', (data) => {
  console.error('Transcription error:', data.error);
});

socket.on('realtime_stopped', () => {
  rtStatus.textContent = 'Presiona para grabar';
});

// --- Visualizer ---
function drawVisualizer() {
  if (!analyser) return;
  const ctx = audioCanvas.getContext('2d');
  const bufLen = analyser.frequencyBinCount;
  const data = new Uint8Array(bufLen);

  function draw() {
    animFrameId = requestAnimationFrame(draw);
    analyser.getByteFrequencyData(data);

    ctx.clearRect(0, 0, audioCanvas.width, audioCanvas.height);
    const barW = (audioCanvas.width / bufLen) * 2.5;
    let x = 0;
    for (let i = 0; i < bufLen; i++) {
      const h = (data[i] / 255) * audioCanvas.height;
      const accent = getComputedStyle(document.documentElement).getPropertyValue('--accent').trim() || '#7c3aed';
      ctx.fillStyle = accent;
      ctx.globalAlpha = 0.7;
      ctx.fillRect(x, audioCanvas.height - h, barW, h);
      x += barW + 1;
      if (x > audioCanvas.width) break;
    }
    ctx.globalAlpha = 1;
  }
  draw();
}

// --- Timer ---
function updateTimer() {
  const m = String(Math.floor(seconds / 60)).padStart(2, '0');
  const s = String(seconds % 60).padStart(2, '0');
  timerEl.textContent = `${m}:${s}`;
}

// --- Actions ---
copyBtn.addEventListener('click', () => {
  const text = transcript.innerText.trim();
  if (text) {
    navigator.clipboard.writeText(text).then(() => {
      copyBtn.textContent = 'Copiado!';
      setTimeout(() => { copyBtn.textContent = 'Copiar'; }, 1500);
    });
  }
});

clearBtn.addEventListener('click', () => {
  transcript.innerHTML = '<p class="rt-placeholder">El texto aparecerá aquí mientras hablas...</p>';
  hasContent = false;
  segments = [];
  copyBtn.disabled = true;
  clearBtn.disabled = true;
  saveBtn.disabled = true;
});

saveBtn.addEventListener('click', async () => {
  if (segments.length === 0) return;

  saveBtn.disabled = true;
  saveBtn.textContent = 'Guardando...';

  try {
    const res = await fetch('/realtime/save', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        segments,
        language: langSelect.value,
        model: modelSelect.value,
        duration: timerEl.textContent,
      }),
    });
    const result = await res.json();
    if (result.ok) {
      saveBtn.textContent = 'Guardado!';
      setTimeout(() => { saveBtn.textContent = 'Guardar'; saveBtn.disabled = false; }, 2000);
    } else {
      saveBtn.textContent = 'Error';
      setTimeout(() => { saveBtn.textContent = 'Guardar'; saveBtn.disabled = false; }, 2000);
    }
  } catch (e) {
    console.error('Save error:', e);
    saveBtn.textContent = 'Error';
    setTimeout(() => { saveBtn.textContent = 'Guardar'; saveBtn.disabled = false; }, 2000);
  }
});
