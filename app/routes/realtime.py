import json
import tempfile
import os
import uuid
from datetime import datetime

from flask import Blueprint, jsonify, render_template, request

from config import TRANSCRIPT_DIR
from transcriber import _cargar_fw_modelo

bp = Blueprint("realtime", __name__)

ALL_RT_MODELS = {
    "large-v3-turbo": "Turbo (rápido)",
    "large-v3": "Large v3 (preciso)",
    "medium": "Medium",
    "small": "Small (ligero)",
    "base": "Base (muy ligero)",
}

# Map model names to their huggingface repo patterns
_MODEL_REPO_PATTERNS = {
    "large-v3-turbo": "faster-whisper-large-v3-turbo",
    "large-v3": "faster-whisper-large-v3",
    "medium": "faster-whisper-medium",
    "small": "faster-whisper-small",
    "base": "faster-whisper-base",
}


def _get_installed_models() -> dict:
    """Return only models that are downloaded locally."""
    try:
        from huggingface_hub import scan_cache_dir
        cache = scan_cache_dir()
        cached_repos = {repo.repo_id.lower() for repo in cache.repos}
    except Exception:
        return ALL_RT_MODELS

    installed = {}
    for model_id, label in ALL_RT_MODELS.items():
        pattern = _MODEL_REPO_PATTERNS[model_id].lower()
        if any(pattern in repo for repo in cached_repos):
            installed[model_id] = label

    return installed if installed else {"large-v3-turbo": ALL_RT_MODELS["large-v3-turbo"]}


@bp.route("/realtime")
def realtime_page():
    installed = _get_installed_models()
    return render_template("realtime.html", active="realtime", rt_models=installed)


@bp.route("/realtime/save", methods=["POST"])
def save_realtime():
    """Save a realtime transcription to the transcriptions directory."""
    data = request.get_json()
    segs = data.get("segments", [])
    if not segs:
        return jsonify({"ok": False, "error": "empty"}), 400

    job_id = uuid.uuid4().hex
    now = datetime.now()
    transcript_data = {
        "filename": f"Grabación {now.strftime('%Y-%m-%d %H:%M')}",
        "model": data.get("model", "large-v3-turbo"),
        "language": data.get("language", "es"),
        "date": now.isoformat(),
        "duration_str": data.get("duration", "00:00"),
        "segments": [
            {"start": s.get("start", 0), "end": s.get("end", 0), "text": s.get("text", "")}
            for s in segs
        ],
    }

    out = TRANSCRIPT_DIR / f"{job_id}.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(transcript_data, f, ensure_ascii=False, indent=2)

    return jsonify({"ok": True, "job_id": job_id})


def register_socketio_events(socketio):
    @socketio.on("audio_chunk")
    def handle_audio_chunk(data):
        """Receive audio chunk from browser, transcribe, and emit text back."""
        audio_bytes = data.get("audio")
        language = data.get("language", "es")
        model_name = data.get("model", "large-v3-turbo")
        time_offset = data.get("timeOffset", 0)
        if not audio_bytes:
            return

        # Validate model name
        if model_name not in ALL_RT_MODELS:
            model_name = "large-v3-turbo"

        tmp = tempfile.NamedTemporaryFile(suffix=".webm", delete=False)
        try:
            tmp.write(audio_bytes)
            tmp.close()

            model = _cargar_fw_modelo(model_name)
            lang = None if language == "auto" else language
            segments, _ = model.transcribe(tmp.name, language=lang, beam_size=1, best_of=1)

            for seg in segments:
                text = seg.text.strip()
                if text:
                    socketio.emit("transcription", {
                        "text": text,
                        "start": seg.start,
                        "end": seg.end,
                        "timeOffset": time_offset,
                    })
        except Exception as e:
            socketio.emit("transcription_error", {"error": str(e)})
        finally:
            os.unlink(tmp.name)

    @socketio.on("stop_realtime")
    def handle_stop():
        """Client signals recording stopped."""
        socketio.emit("realtime_stopped")
