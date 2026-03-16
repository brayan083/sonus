import json
import os
import subprocess

import torch
import whisper
from faster_whisper import WhisperModel
from openai import OpenAI

DEVICE = "mps" if torch.backends.mps.is_available() else "cpu"

# --- Post-processing config ---
# Segments shorter than this (seconds) with generic filler text are removed
NOISE_MAX_DURATION = 2.0
NOISE_WORDS = {"x.", "bien.", "y acá...", "y acá.", "x", "bien"}
# Gap threshold (seconds) to merge nearby short segments
MERGE_GAP = 0.5
MERGE_MAX_TEXT_LEN = 30
# faster-whisper uses ctranslate2 — MPS not supported, use cpu or cuda
FW_DEVICE = "cpu"

_model_cache = {}
_fw_model_cache = {}


def cargar_modelo(modelo: str = "large-v3-turbo"):
    if modelo not in _model_cache:
        _model_cache[modelo] = whisper.load_model(modelo, device=DEVICE)
    return _model_cache[modelo]


def get_duration(audio_path: str) -> float | None:
    """Return audio duration in seconds using ffprobe."""
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_streams", audio_path],
            capture_output=True, text=True, timeout=10,
        )
        info = json.loads(out.stdout)
        for stream in info.get("streams", []):
            if "duration" in stream:
                return float(stream["duration"])
    except Exception:
        pass
    return None


def transcribir(audio_path: str, modelo: str = "large-v3-turbo", idioma: str = "es") -> list[dict]:
    model = cargar_modelo(modelo)
    resultado = model.transcribe(audio_path, language=idioma, verbose=True)
    return [
        {"start": seg["start"], "end": seg["end"], "text": seg["text"].strip()}
        for seg in resultado["segments"]
    ]


def _cargar_fw_modelo(modelo: str = "large-v3-turbo") -> WhisperModel:
    if modelo not in _fw_model_cache:
        _fw_model_cache[modelo] = WhisperModel(modelo, device=FW_DEVICE, compute_type="int8")
    return _fw_model_cache[modelo]


def limpiar_segmentos(segments: list[dict]) -> list[dict]:
    """Clean transcription segments by merging duplicates, removing noise, and joining nearby short segments."""
    if not segments:
        return segments

    # 1. Merge consecutive segments with identical text
    merged = [segments[0].copy()]
    for seg in segments[1:]:
        if seg["text"] == merged[-1]["text"]:
            merged[-1]["end"] = seg["end"]
        else:
            merged.append(seg.copy())

    # 2. Filter short segments with generic/noise text
    filtered = []
    for seg in merged:
        duration = seg["end"] - seg["start"]
        if duration <= NOISE_MAX_DURATION and seg["text"].lower().strip() in NOISE_WORDS:
            continue
        filtered.append(seg)

    # 3. Remove segments with empty text or only punctuation
    cleaned = [seg for seg in filtered if seg["text"].strip().strip(".,;:!?¿¡")]

    # 4. Merge nearby short segments (gap < MERGE_GAP and both texts short)
    if not cleaned:
        return cleaned
    result = [cleaned[0].copy()]
    for seg in cleaned[1:]:
        prev = result[-1]
        gap = seg["start"] - prev["end"]
        if gap < MERGE_GAP and len(prev["text"]) <= MERGE_MAX_TEXT_LEN and len(seg["text"]) <= MERGE_MAX_TEXT_LEN:
            result[-1]["end"] = seg["end"]
            result[-1]["text"] = prev["text"] + " " + seg["text"]
        else:
            result.append(seg.copy())

    return result


class TranscriptionCancelled(Exception):
    pass


def transcribir_stream(audio_path: str, on_segment, modelo: str = "large-v3-turbo", idioma: str = "es", cancel_event=None) -> list[dict]:
    """Transcribe using faster-whisper which yields segments as they are produced."""
    model = _cargar_fw_modelo(modelo)
    segments_out = []
    lang = None if idioma == "auto" else idioma
    segments, _ = model.transcribe(audio_path, language=lang, beam_size=5)
    for seg in segments:
        if cancel_event and cancel_event.is_set():
            raise TranscriptionCancelled()
        s = {"start": seg.start, "end": seg.end, "text": seg.text.strip()}
        segments_out.append(s)
        on_segment(s)
    return segments_out


def _split_audio_chunks(audio_path: str, max_size_mb: int = 24) -> list[tuple[str, float]]:
    """Split audio into chunks under max_size_mb using ffmpeg. Returns list of (chunk_path, start_seconds)."""
    import math
    import tempfile

    file_size = os.path.getsize(audio_path)
    max_bytes = max_size_mb * 1024 * 1024

    if file_size <= max_bytes:
        return [(audio_path, 0.0)]

    duration = get_duration(audio_path)
    if not duration:
        raise ValueError("No se pudo obtener la duración del audio para dividirlo.")

    num_chunks = math.ceil(file_size / max_bytes)
    chunk_duration = duration / num_chunks
    chunks = []
    tmp_dir = tempfile.mkdtemp(prefix="whisper_chunks_")

    for i in range(num_chunks):
        start = i * chunk_duration
        chunk_path = os.path.join(tmp_dir, f"chunk_{i:03d}.mp3")
        cmd = [
            "ffmpeg", "-y", "-i", audio_path,
            "-ss", str(start), "-t", str(chunk_duration),
            "-vn", "-acodec", "libmp3lame", "-q:a", "2",
            chunk_path,
        ]
        subprocess.run(cmd, capture_output=True, timeout=120)
        if os.path.exists(chunk_path):
            chunks.append((chunk_path, start))

    return chunks


def transcribir_api(audio_path: str, api_key: str, idioma: str = "es", on_segment=None, cancel_event=None) -> list[dict]:
    """Transcribe using OpenAI Whisper API, splitting large files into chunks."""
    client = OpenAI(api_key=api_key)
    lang = None if idioma == "auto" else idioma
    chunks = _split_audio_chunks(audio_path)
    segments_out = []

    try:
        for chunk_path, time_offset in chunks:
            if cancel_event and cancel_event.is_set():
                raise TranscriptionCancelled()
            with open(chunk_path, "rb") as f:
                response = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=f,
                    response_format="verbose_json",
                    timestamp_granularities=["segment"],
                    **({"language": lang} if lang else {}),
                )
            for seg in response.segments:
                if cancel_event and cancel_event.is_set():
                    raise TranscriptionCancelled()
                s = {
                    "start": seg.start + time_offset,
                    "end": seg.end + time_offset,
                    "text": seg.text.strip(),
                }
                segments_out.append(s)
                if on_segment:
                    on_segment(s)
    finally:
        # Clean up temp chunks
        for chunk_path, _ in chunks:
            if chunk_path != audio_path and os.path.exists(chunk_path):
                os.unlink(chunk_path)
        # Remove temp dir if it was created
        if chunks and chunks[0][0] != audio_path:
            import shutil
            shutil.rmtree(os.path.dirname(chunks[0][0]), ignore_errors=True)

    return segments_out
