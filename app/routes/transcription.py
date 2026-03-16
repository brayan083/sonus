import json
import threading
import uuid
from datetime import datetime
from pathlib import Path

from flask import Blueprint, Response, jsonify, redirect, render_template, request, send_file, url_for

import transcriber
from config import (
    AVAILABLE_LANGUAGES, AVAILABLE_MODELS, EXTENSIONES_PERMITIDAS,
    TRANSCRIPT_DIR, UPLOAD_DIR, load_settings,
)
from jobs import cleanup_old_jobs, is_valid_job_id, job_cancel_events, job_filenames, job_progress, jobs
from utils import format_duration, format_srt_time

bp = Blueprint("transcription", __name__)


def _cleanup_upload(job_id: str):
    for ext in EXTENSIONES_PERMITIDAS | {".webm"}:
        p = UPLOAD_DIR / f"{job_id}{ext}"
        if p.exists():
            p.unlink()
            break


def _run_transcription(job_id: str, audio_path: str, original_filename: str,
                       modelo: str = "large-v3-turbo", idioma: str = "es"):
    short_id = job_id[:8]
    cancel_event = job_cancel_events.get(job_id)
    print(f"\n[{short_id}] Iniciando transcripcion: {original_filename}")
    print(f"[{short_id}] Modelo: {modelo} | Idioma: {idioma}")
    try:
        total_duration = transcriber.get_duration(audio_path)
        if total_duration:
            print(f"[{short_id}] Duracion del audio: {format_duration(total_duration)}")

        segmentos = []

        def on_segment(seg):
            segmentos.append(seg)
            if total_duration and total_duration > 0:
                pct = min(99, int(seg["end"] / total_duration * 100))
                job_progress[job_id] = pct
                print(f"[{short_id}] {pct}% -- segmento {len(segmentos)} ({format_duration(seg['end'])} / {format_duration(total_duration)})")

        if modelo == "whisper-api":
            from config import load_settings as _load_cfg
            api_key = _load_cfg().get("openai_api_key", "")
            if not api_key:
                raise ValueError("No se ha configurado la API key de OpenAI. Ve a Configuración para agregarla.")
            transcriber.transcribir_api(audio_path, api_key, idioma=idioma, on_segment=on_segment, cancel_event=cancel_event)
        else:
            transcriber.transcribir_stream(audio_path, on_segment, modelo=modelo, idioma=idioma, cancel_event=cancel_event)

        raw_count = len(segmentos)
        segmentos = transcriber.limpiar_segmentos(segmentos)
        print(f"[{short_id}] Limpieza: {raw_count} -> {len(segmentos)} segmentos")

        duracion = segmentos[-1]["end"] if segmentos else 0
        data = {
            "job_id":       job_id,
            "filename":     original_filename,
            "date":         datetime.now().strftime("%d/%m/%Y %H:%M"),
            "duration_sec": duracion,
            "segment_count": len(segmentos),
            "model":        modelo,
            "language":     idioma,
            "segments":     segmentos,
        }
        out = TRANSCRIPT_DIR / f"{job_id}.json"
        with open(out, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        job_progress[job_id] = 100
        jobs[job_id] = "done"
        print(f"[{short_id}] Completado -- {len(segmentos)} segmentos, {format_duration(duracion)}")
        _cleanup_upload(job_id)
        cleanup_old_jobs()
    except transcriber.TranscriptionCancelled:
        jobs[job_id] = "cancelled"
        print(f"[{short_id}] Cancelado por el usuario")
        _cleanup_upload(job_id)
    except Exception as e:
        jobs[job_id] = f"error: {e}"
        print(f"[{short_id}] Error: {e}")
        _cleanup_upload(job_id)
    finally:
        job_cancel_events.pop(job_id, None)
        job_filenames.pop(job_id, None)


@bp.route("/upload", methods=["POST"])
def upload():
    archivo = request.files.get("video")
    if not archivo or not archivo.filename:
        return "No se recibio ningun archivo.", 400

    ext = Path(archivo.filename).suffix.lower()
    if ext not in EXTENSIONES_PERMITIDAS:
        return f"Formato no soportado: {ext}", 400

    cfg = load_settings()
    modelo = request.form.get("model", cfg["model"])
    idioma = request.form.get("language", cfg["language"])
    if modelo not in AVAILABLE_MODELS:
        modelo = cfg["model"]
    if idioma not in AVAILABLE_LANGUAGES:
        idioma = cfg["language"]

    job_id = uuid.uuid4().hex
    upload_path = UPLOAD_DIR / f"{job_id}{ext}"
    archivo.save(str(upload_path))

    jobs[job_id] = "processing"
    job_cancel_events[job_id] = threading.Event()
    job_filenames[job_id] = archivo.filename
    t = threading.Thread(
        target=_run_transcription,
        args=(job_id, str(upload_path), archivo.filename, modelo, idioma),
        daemon=True,
    )
    t.start()

    return redirect(url_for("transcription.result", job_id=job_id))


@bp.route("/cancel/<job_id>", methods=["POST"])
def cancel(job_id: str):
    if not is_valid_job_id(job_id):
        return jsonify({"ok": False, "error": "not_found"})
    ev = job_cancel_events.get(job_id)
    if ev:
        ev.set()
        return jsonify({"ok": True})
    return jsonify({"ok": False, "error": "not_cancellable"})


@bp.route("/active-jobs")
def active_jobs():
    active = [
        {"job_id": jid, "progress": job_progress.get(jid, 0), "filename": job_filenames.get(jid, "")}
        for jid, st in jobs.items() if st == "processing"
    ]
    return jsonify(active)


@bp.route("/status/<job_id>")
def status(job_id: str):
    if not is_valid_job_id(job_id):
        return jsonify({"status": "not_found", "progress": 0})
    estado = jobs.get(job_id, "not_found")
    progress = job_progress.get(job_id, 0)
    return jsonify({"status": estado, "progress": progress})


@bp.route("/result/<job_id>")
def result(job_id: str):
    if not is_valid_job_id(job_id):
        return "Job no encontrado.", 404
    return render_template("result.html", job_id=job_id, active="transcribe")


@bp.route("/download/<job_id>")
def download(job_id: str):
    if not is_valid_job_id(job_id):
        return "Job no encontrado.", 404
    path = TRANSCRIPT_DIR / f"{job_id}.json"
    if not path.exists():
        return "Transcripcion no encontrada.", 404
    data = json.loads(path.read_text())

    fmt = request.args.get("format", "json")
    base_name = Path(data.get("filename", "transcripcion")).stem
    segments = data.get("segments", [])

    if fmt == "txt":
        lines = [seg["text"] for seg in segments]
        content = "\n".join(lines)
        return Response(content, mimetype="text/plain",
                        headers={"Content-Disposition": f'attachment; filename="{base_name}.txt"'})

    if fmt == "srt":
        srt_lines = []
        for i, seg in enumerate(segments, 1):
            start = format_srt_time(seg["start"])
            end = format_srt_time(seg["end"])
            srt_lines.append(f"{i}\n{start} --> {end}\n{seg['text']}\n")
        content = "\n".join(srt_lines)
        return Response(content, mimetype="text/plain",
                        headers={"Content-Disposition": f'attachment; filename="{base_name}.srt"'})

    filename = base_name + ".json"
    return send_file(str(path), as_attachment=True, download_name=filename)
