# Architecture

## Project Structure

```
whisper-bray/
├── app/
│   ├── app.py              # Flask entry point, blueprint registration, error handlers
│   ├── config.py           # Paths, constants, settings load/save
│   ├── jobs.py             # In-memory job state (dicts for status, progress, cancellation)
│   ├── transcriber.py      # Whisper wrapper (local + API), segment cleaning
│   ├── ai_service.py       # AI summarization (Ollama + Gemini providers)
│   ├── utils.py            # format_duration, format_srt_time helpers
│   ├── routes/
│   │   ├── __init__.py     # Exports all_blueprints list
│   │   ├── general.py      # Index, history, summaries, settings, delete/rename
│   │   ├── transcription.py # Upload, status polling, result, download, cancel
│   │   └── summary.py      # Summarize (single + multi), summary status/result/download/rename/delete
│   ├── templates/          # Jinja2 templates (all extend base.html)
│   ├── static/
│   │   ├── css/base.css    # Design system variables + shared components
│   │   ├── css/pages/      # Per-page CSS files
│   │   └── js/
│   │       ├── theme.js    # Dark/light theme toggle
│   │       └── pages/      # Per-page JS files
│   └── data/
│       ├── settings.json   # Persisted user settings (no API keys)
│       ├── uploads/        # Temporary uploaded files (cleaned after transcription)
│       ├── transcripciones/ # Transcription JSON results
│       └── summary/        # Summary JSON results
├── .env                    # API keys (GEMINI_API_KEY, OPENAI_API_KEY), Flask config
├── requirements.txt
└── CLAUDE.md
```

## Data Flow

### Transcription Flow
1. User uploads file via `POST /upload` with model + language options
2. File saved to `data/uploads/{job_id}{ext}`
3. Background thread starts → `transcriber.transcribir_stream()` (faster-whisper) or `transcriber.transcribir_api()` (OpenAI API)
4. Segments emitted via `on_segment` callback → updates `job_progress` dict
5. On completion: segments cleaned via `limpiar_segmentos()`, saved as `data/transcripciones/{job_id}.json`, upload deleted
6. Frontend polls `GET /status/{job_id}` until `"done"` → redirects to show result

### Summarization Flow
1. User picks a transcription (or up to 5 for multi-summary) → `GET /summarize/{job_id}` or `GET /summarize_multi?ids=...`
2. On form submit `POST`: background thread builds prompt via `ai_service.build_prompt()` / `build_multi_prompt()`
3. Calls `ai_service.summarize()` → routes to Ollama or Gemini based on settings
4. Result saved as `data/summary/{job_id}_summary_{summary_id}.json` (or `multi_summary_{id}.json`)
5. Frontend polls `GET /summary_status/{summary_id}` until `"done"`

## Key Patterns

- **No database**: All persistence is JSON files on disk. In-memory dicts (`jobs`, `job_progress`, `summary_jobs`) track active work but are lost on restart.
- **Background threads**: All heavy work (transcription, summarization) runs in `daemon=True` threads.
- **Cancellation**: Transcription jobs support cancellation via `threading.Event` stored in `job_cancel_events`.
- **Blueprint organization**: Routes split into 3 blueprints (general, transcription, summary).
- **Settings**: Loaded from `data/settings.json` merged with env vars. API keys only come from `.env`, never persisted to JSON.
