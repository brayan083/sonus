import json

from flask import Blueprint, jsonify, redirect, render_template, request, url_for

import ai_service
from config import (
    AVAILABLE_LANGUAGES, AVAILABLE_MODELS, EXTENSIONES_PERMITIDAS,
    SUMMARY_DIR, TRANSCRIPT_DIR, UPLOAD_DIR,
    get_installed_models, load_settings, save_settings,
)
from jobs import is_valid_job_id, job_progress, jobs
from utils import format_duration

bp = Blueprint("general", __name__)


@bp.route("/")
def index():
    cfg = load_settings()
    return render_template("index.html", active="transcribe",
                           models=get_installed_models(), languages=AVAILABLE_LANGUAGES,
                           current_model=cfg["model"], current_language=cfg["language"])


@bp.route("/history")
def history():
    transcripciones = []
    for json_file in sorted(TRANSCRIPT_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        data = json.loads(json_file.read_text())
        if "segments" not in data:
            continue
        job_id = json_file.stem
        transcripciones.append({
            "job_id":     job_id,
            "filename":   data.get("filename", "--"),
            "date":       data.get("date", "--"),
            "duration":   format_duration(data.get("duration_sec", 0)),
            "segments":   data.get("segment_count", len(data.get("segments", []))),
            "model":      data.get("model", "--"),
        })
    return render_template("history.html", transcripciones=transcripciones, active="history")


@bp.route("/summaries")
def summaries():
    resumenes = []
    for json_file in sorted(SUMMARY_DIR.glob("*_summary_*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        data = json.loads(json_file.read_text())
        summary_id = data.get("summary_id", "")
        stype = data.get("summary_type", "general")
        length_labels = {"short": "Corto", "medium": "Medio", "detailed": "Detallado"}
        lang_labels = {"es": "Español", "en": "Inglés", "fr": "Francés", "de": "Alemán",
                       "pt": "Portugués", "it": "Italiano", "ja": "Japonés", "zh": "Chino"}
        resumenes.append({
            "summary_id": summary_id,
            "summary_name": data.get("summary_name", data.get("filename", "--")),
            "date":       data.get("date", "--"),
            "summary_type": ai_service.SUMMARY_TYPES.get(stype, stype),
            "ai_model":   data.get("ai_model", "--"),
            "length":     length_labels.get(data.get("length", ""), data.get("length", "--")),
            "language":   lang_labels.get(data.get("language", ""), data.get("language", "--")),
            "is_multi":   "job_ids" in data,
        })
    return render_template("summary_history.html", resumenes=resumenes, active="summaries")


@bp.route("/rename/<job_id>", methods=["POST"])
def rename_transcription(job_id: str):
    if not is_valid_job_id(job_id):
        return jsonify({"ok": False}), 404
    path = TRANSCRIPT_DIR / f"{job_id}.json"
    if not path.exists():
        return jsonify({"ok": False}), 404
    data = json.loads(path.read_text())
    new_name = (request.get_json() or {}).get("name", "").strip()
    if not new_name:
        return jsonify({"ok": False}), 400
    data["filename"] = new_name
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    return jsonify({"ok": True})


@bp.route("/delete", methods=["POST"])
def delete_transcriptions():
    data = request.get_json()
    job_ids = [jid for jid in data.get("job_ids", []) if is_valid_job_id(jid)]
    deleted = []
    for job_id in job_ids:
        path = TRANSCRIPT_DIR / f"{job_id}.json"
        if path.exists():
            path.unlink()
            deleted.append(job_id)
        for ext in EXTENSIONES_PERMITIDAS | {".webm"}:
            upload_path = UPLOAD_DIR / f"{job_id}{ext}"
            if upload_path.exists():
                upload_path.unlink()
                break
        jobs.pop(job_id, None)
        job_progress.pop(job_id, None)
    return jsonify({"deleted": deleted})


@bp.route("/settings", methods=["GET", "POST"])
def settings():
    if request.method == "POST":
        modelo = request.form.get("model", "large-v3-turbo")
        idioma = request.form.get("language", "es")
        if modelo not in AVAILABLE_MODELS:
            modelo = "large-v3-turbo"
        if idioma not in AVAILABLE_LANGUAGES:
            idioma = "es"
        save_settings({
            "model": modelo, "language": idioma,
            "ai_provider": request.form.get("ai_provider", "ollama"),
            "ollama_url": request.form.get("ollama_url", "http://localhost:11434"),
            "ollama_model": request.form.get("ollama_model", "llama3.2"),
            "gemini_api_key": request.form.get("gemini_api_key", ""),
            "gemini_model": request.form.get("gemini_model", "gemini-2.5-pro"),
            "openai_api_key": request.form.get("openai_api_key", ""),
        })
        return redirect(url_for("general.settings", saved="1"))
    cfg = load_settings()
    return render_template("settings.html", active="settings",
                           models=get_installed_models(), languages=AVAILABLE_LANGUAGES,
                           current_model=cfg["model"], current_language=cfg["language"],
                           current_ai_provider=cfg.get("ai_provider", "ollama"),
                           current_ollama_url=cfg.get("ollama_url", "http://localhost:11434"),
                           current_ollama_model=cfg.get("ollama_model", "llama3.2"),
                           current_gemini_api_key=cfg.get("gemini_api_key", ""),
                           current_gemini_model=cfg.get("gemini_model", "gemini-2.5-pro"),
                           gemini_models=ai_service.GEMINI_MODELS,
                           current_openai_api_key=cfg.get("openai_api_key", ""))
