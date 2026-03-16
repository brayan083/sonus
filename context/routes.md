# Routes

## General Blueprint (`routes/general.py`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Index page — upload form with model/language selectors |
| GET | `/history` | List all transcriptions from `data/transcripciones/` sorted by mtime desc |
| GET | `/summaries` | List all summaries from `data/summary/` sorted by mtime desc |
| POST | `/rename/<job_id>` | Rename a transcription — JSON body `{"name": "..."}` |
| POST | `/delete` | Delete transcriptions — JSON body `{"job_ids": ["..."]}` |
| GET/POST | `/settings` | View/save settings (model, language, AI provider config) |

## Transcription Blueprint (`routes/transcription.py`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/upload` | Upload file, start transcription thread, redirect to result page |
| GET | `/status/<job_id>` | Poll job status — returns `{"status": "processing"|"done"|"error:..."|"cancelled"|"not_found", "progress": 0-100}` |
| GET | `/result/<job_id>` | Render result page (polls status via JS) |
| POST | `/cancel/<job_id>` | Cancel a running transcription — returns `{"ok": true/false}` |
| GET | `/active-jobs` | List currently processing jobs — returns `[{"job_id", "progress", "filename"}]` |
| GET | `/download/<job_id>?format=json|txt|srt` | Download transcription in chosen format |

## Summary Blueprint (`routes/summary.py`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/summarize` | Redirects to `/history` |
| GET/POST | `/summarize/<job_id>` | Single transcription summary form / submit |
| GET/POST | `/summarize_multi?ids=...` | Multi-transcription summary (up to 5) form / submit |
| GET | `/summary_status/<summary_id>` | Poll summary job status — returns `{"status": "..."}` |
| GET | `/summary_result/<summary_id>?job_id=...` | Render summary result page |
| GET | `/summary_download/<summary_id>?format=json|txt` | Download summary |
| POST | `/rename_summary/<summary_id>` | Rename summary — JSON body `{"name": "..."}` |
| POST | `/delete_summaries` | Delete summaries — JSON body `{"summary_ids": ["..."]}` |
