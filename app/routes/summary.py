import json
import os
import tempfile
import threading
import uuid
from datetime import datetime
from pathlib import Path

from flask import Blueprint, Response, jsonify, redirect, render_template, request, url_for

import ai_service
import file_parser
from config import (
    AVAILABLE_LANGUAGES, SUMMARY_DIR, TRANSCRIPT_DIR, load_settings,
)
from jobs import is_valid_job_id, summary_jobs
from utils import format_duration

bp = Blueprint("summary", __name__)


def _run_summary(summary_id: str, job_id: str, data: dict,
                 summary_type: str, length: str, language: str,
                 summary_name: str = "", attachments_text: str = ""):
    short_id = summary_id[:8]
    filename = data.get("filename", "?")
    print(f"\n[{short_id}] Generando resumen: {filename}")
    print(f"[{short_id}] Tipo: {summary_type} | Extension: {length} | Idioma: {language}")
    if attachments_text:
        print(f"[{short_id}] Con material de apoyo ({len(attachments_text)} caracteres)")
    try:
        cfg = load_settings()
        full_text = " ".join(seg["text"] for seg in data.get("segments", []))

        def on_progress(msg):
            print(f"[{short_id}] {msg}")
            summary_jobs[summary_id] = f"processing:{msg}"

        if ai_service.needs_chunking(full_text, attachments_text):
            print(f"[{short_id}] Texto largo detectado, usando resumen por chunks...")
            result = ai_service.summarize_chunked(
                full_text, summary_type, length, language, cfg,
                attachments_text=attachments_text, on_progress=on_progress,
            )
        else:
            prompt = ai_service.build_prompt(summary_type, length, language, full_text, attachments_text)
            result = ai_service.summarize(prompt, cfg)
        provider = cfg.get("ai_provider", "ollama")
        provider_model = cfg.get("gemini_model", "") if provider == "gemini" else cfg.get("ollama_model", "")

        summary_data = {
            "summary_id":   summary_id,
            "job_id":       job_id,
            "filename":     data.get("filename", ""),
            "summary_name": summary_name or f"Resumen - {data.get('filename', '')}",
            "ai_provider":  provider,
            "ai_model":     provider_model,
            "date":         datetime.now().strftime("%d/%m/%Y %H:%M"),
            "summary_type": summary_type,
            "length":       length,
            "language":     language,
            "summary":      result,
        }
        out = SUMMARY_DIR / f"{job_id}_summary_{summary_id}.json"
        with open(out, "w", encoding="utf-8") as f:
            json.dump(summary_data, f, ensure_ascii=False, indent=2)

        summary_jobs[summary_id] = "done"
        print(f"[{short_id}] Resumen generado ({len(result)} caracteres)")
    except Exception as e:
        summary_jobs[summary_id] = f"error: {e}"
        print(f"[{short_id}] Error: {e}")


def _run_multi_summary(summary_id: str, job_ids: list[str], all_data: list[dict],
                       summary_type: str, length: str, language: str,
                       summary_name: str = "", attachments_text: str = ""):
    short_id = summary_id[:8]
    names = ", ".join(d.get("filename", "?") for d in all_data)
    print(f"\n[{short_id}] Generando resumen multi ({len(all_data)} partes): {names}")
    if attachments_text:
        print(f"[{short_id}] Con material de apoyo ({len(attachments_text)} caracteres)")
    try:
        cfg = load_settings()
        prompt = ai_service.build_multi_prompt(summary_type, length, language, all_data, attachments_text)
        result = ai_service.summarize(prompt, cfg)
        provider = cfg.get("ai_provider", "ollama")
        provider_model = cfg.get("gemini_model", "") if provider == "gemini" else cfg.get("ollama_model", "")

        summary_data = {
            "summary_id":   summary_id,
            "job_ids":      job_ids,
            "filenames":    [d.get("filename", "") for d in all_data],
            "filename":     " + ".join(d.get("filename", "") for d in all_data),
            "summary_name": summary_name or f"Resumen - {len(all_data)} transcripciones",
            "ai_provider":  provider,
            "ai_model":     provider_model,
            "date":         datetime.now().strftime("%d/%m/%Y %H:%M"),
            "summary_type": summary_type,
            "length":       length,
            "language":     language,
            "summary":      result,
        }
        out = SUMMARY_DIR / f"multi_summary_{summary_id}.json"
        with open(out, "w", encoding="utf-8") as f:
            json.dump(summary_data, f, ensure_ascii=False, indent=2)

        summary_jobs[summary_id] = "done"
        print(f"[{short_id}] Resumen multi generado ({len(result)} caracteres)")
    except Exception as e:
        summary_jobs[summary_id] = f"error: {e}"
        print(f"[{short_id}] Error: {e}")


@bp.route("/summarize_multi", methods=["GET", "POST"])
def summarize_multi():
    ids = request.args.getlist("ids") if request.method == "GET" else request.form.getlist("ids")
    if not ids or len(ids) > 5:
        return redirect(url_for("general.history"))

    # Load all transcription data in order
    all_data = []
    for jid in ids:
        if not is_valid_job_id(jid):
            return f"Job {jid} no encontrado.", 404
        path = TRANSCRIPT_DIR / f"{jid}.json"
        if not path.exists():
            return f"Transcripcion {jid} no encontrada.", 404
        all_data.append(json.loads(path.read_text()))

    cfg = load_settings()

    if request.method == "POST":
        summary_type = request.form.get("summary_type", "general")
        length = request.form.get("length", "medium")
        language = request.form.get("language", cfg["language"])
        summary_name = request.form.get("summary_name", "").strip()

        # Process attached files
        attachments_text = ""
        uploaded = request.files.getlist("attachments")
        temp_paths = []
        for f in uploaded:
            if f and f.filename:
                ext = Path(f.filename).suffix.lower()
                if ext in file_parser.ALLOWED_EXTENSIONS:
                    tmp = tempfile.NamedTemporaryFile(suffix=ext, delete=False)
                    f.save(tmp.name)
                    tmp.close()
                    temp_paths.append(tmp.name)
        if temp_paths:
            attachments_text = file_parser.extract_from_files(temp_paths)
            for p in temp_paths:
                os.unlink(p)

        summary_id = uuid.uuid4().hex
        summary_jobs[summary_id] = "processing"
        t = threading.Thread(
            target=_run_multi_summary,
            args=(summary_id, ids, all_data, summary_type, length, language, summary_name, attachments_text),
            daemon=True,
        )
        t.start()
        return redirect(url_for("summary.summary_result", summary_id=summary_id))

    transcripciones = []
    for d in all_data:
        transcripciones.append({
            "job_id": d.get("job_id", ""),
            "filename": d.get("filename", "--"),
            "segments": d.get("segment_count", len(d.get("segments", []))),
            "duration": format_duration(d.get("duration_sec", 0)),
        })

    provider = cfg.get("ai_provider", "ollama")
    provider_label = "Gemini" if provider == "gemini" else "Ollama"
    provider_model = cfg.get("gemini_model", "") if provider == "gemini" else cfg.get("ollama_model", "")
    return render_template("summarize_multi.html", active="summarize",
                           transcripciones=transcripciones,
                           summary_types=ai_service.SUMMARY_TYPES,
                           languages=AVAILABLE_LANGUAGES,
                           current_language=cfg["language"],
                           ai_provider=provider,
                           provider_label=provider_label,
                           provider_model=provider_model,
                           ollama_url=cfg.get("ollama_url", "http://localhost:11434"))


@bp.route("/summarize")
def summarize_index():
    return redirect(url_for("general.history"))


@bp.route("/summarize/<job_id>", methods=["GET", "POST"])
def summarize(job_id: str):
    if not is_valid_job_id(job_id):
        return "Job no encontrado.", 404
    path = TRANSCRIPT_DIR / f"{job_id}.json"
    if not path.exists():
        return "Transcripcion no encontrada.", 404
    data = json.loads(path.read_text())
    cfg = load_settings()

    if request.method == "POST":
        summary_type = request.form.get("summary_type", "general")
        length = request.form.get("length", "medium")
        language = request.form.get("language", cfg["language"])
        summary_name = request.form.get("summary_name", "").strip()

        # Process attached files
        attachments_text = ""
        uploaded = request.files.getlist("attachments")
        temp_paths = []
        for f in uploaded:
            if f and f.filename:
                ext = Path(f.filename).suffix.lower()
                if ext in file_parser.ALLOWED_EXTENSIONS:
                    tmp = tempfile.NamedTemporaryFile(suffix=ext, delete=False)
                    f.save(tmp.name)
                    tmp.close()
                    temp_paths.append(tmp.name)
        if temp_paths:
            attachments_text = file_parser.extract_from_files(temp_paths)
            for p in temp_paths:
                os.unlink(p)

        summary_id = uuid.uuid4().hex
        summary_jobs[summary_id] = "processing"
        t = threading.Thread(
            target=_run_summary,
            args=(summary_id, job_id, data, summary_type, length, language, summary_name, attachments_text),
            daemon=True,
        )
        t.start()
        return redirect(url_for("summary.summary_result", summary_id=summary_id, job_id=job_id))

    provider = cfg.get("ai_provider", "ollama")
    provider_label = "Gemini" if provider == "gemini" else "Ollama"
    provider_model = cfg.get("gemini_model", "") if provider == "gemini" else cfg.get("ollama_model", "")
    return render_template("summarize.html", active="summarize",
                           job_id=job_id,
                           filename=data.get("filename", "--"),
                           segments=data.get("segment_count", len(data.get("segments", []))),
                           duration=format_duration(data.get("duration_sec", 0)),
                           summary_types=ai_service.SUMMARY_TYPES,
                           languages=AVAILABLE_LANGUAGES,
                           current_language=cfg["language"],
                           ai_provider=provider,
                           provider_label=provider_label,
                           provider_model=provider_model,
                           ollama_url=cfg.get("ollama_url", "http://localhost:11434"))


@bp.route("/summary_status/<summary_id>")
def summary_status(summary_id: str):
    if not is_valid_job_id(summary_id):
        return jsonify({"status": "not_found"})
    estado = summary_jobs.get(summary_id)
    if not estado:
        if list(SUMMARY_DIR.glob(f"*_summary_{summary_id}.json")):
            estado = "done"
        else:
            estado = "not_found"
    # Extract progress message from "processing:message" format
    resp = {"status": estado}
    if estado and estado.startswith("processing:"):
        resp["status"] = "processing"
        resp["message"] = estado.split(":", 1)[1]
    return jsonify(resp)


@bp.route("/summary_result/<summary_id>")
def summary_result(summary_id: str):
    if not is_valid_job_id(summary_id):
        return "Resumen no encontrado.", 404
    job_id = request.args.get("job_id", "")
    return render_template("summary_result.html", summary_id=summary_id,
                           job_id=job_id, active="summarize")


@bp.route("/summary_download/<summary_id>")
def summary_download(summary_id: str):
    if not is_valid_job_id(summary_id):
        return "Resumen no encontrado.", 404
    matches = list(SUMMARY_DIR.glob(f"*_summary_{summary_id}.json"))
    if not matches:
        return "Resumen no encontrado.", 404
    data = json.loads(matches[0].read_text())
    fmt = request.args.get("format", "json")
    base_name = Path(data.get("filename", "resumen")).stem + "_resumen"

    if fmt == "txt":
        return Response(data["summary"], mimetype="text/plain",
                        headers={"Content-Disposition": f'attachment; filename="{base_name}.txt"'})

    return Response(json.dumps(data, ensure_ascii=False, indent=2),
                    mimetype="application/json",
                    headers={"Content-Disposition": f'attachment; filename="{base_name}.json"'})


@bp.route("/rename_summary/<summary_id>", methods=["POST"])
def rename_summary(summary_id: str):
    if not is_valid_job_id(summary_id):
        return jsonify({"ok": False}), 404
    matches = list(SUMMARY_DIR.glob(f"*_summary_{summary_id}.json"))
    if not matches:
        return jsonify({"ok": False}), 404
    path = matches[0]
    data = json.loads(path.read_text())
    new_name = (request.get_json() or {}).get("name", "").strip()
    if not new_name:
        return jsonify({"ok": False}), 400
    data["summary_name"] = new_name
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    return jsonify({"ok": True})


@bp.route("/delete_summaries", methods=["POST"])
def delete_summaries():
    data = request.get_json() or {}
    ids = [sid for sid in data.get("summary_ids", []) if is_valid_job_id(sid)]
    deleted = []
    for sid in ids:
        matches = list(SUMMARY_DIR.glob(f"*_summary_{sid}.json"))
        for path in matches:
            path.unlink()
            deleted.append(sid)
        summary_jobs.pop(sid, None)
    return jsonify({"deleted": deleted})
