# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this project does

Flask web app ("Sonus") that transcribes audio/video files using Whisper (local or API) and generates AI summaries using Ollama or Gemini. Background threads handle heavy work, results are polled via JS.

## Running the app

```bash
cd app
python app.py
```

App runs on `http://localhost:5001` by default (configurable via `FLASK_PORT` in `.env`).

## Context docs

Before making changes, read the relevant files in `context/` for detailed documentation:

- `context/architecture.md` — Project structure, data flow, key patterns
- `context/routes.md` — All HTTP endpoints by blueprint (general, transcription, summary)
- `context/data-models.md` — JSON schemas for transcriptions, summaries, settings + in-memory state
- `context/frontend.md` — Templates, CSS design tokens, component classes, JS patterns, branding
- `context/ai-services.md` — Whisper engines, AI providers, summary types, prompt structure
- `context/jobs.md` — Background job lifecycle, cancellation, cleanup, polling
- `context/roadmap.md` — Implemented features, stubs, potential improvements

## Key design decisions

- **No database** — All persistence is JSON files in `app/data/`. In-memory dicts track active jobs (lost on restart).
- **Supported formats** — `.mp4 .mp3 .m4a .wav .mov .mkv .webm`
- **Default model/language** — `large-v3-turbo`, Spanish (`es`). Configurable in settings.
- **API keys** — Loaded from `.env`, never persisted to `settings.json`.
