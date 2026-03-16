# Data Models

All data is stored as JSON files on disk. No database.

## Transcription (`data/transcripciones/{job_id}.json`)

```json
{
  "job_id": "a1a9767bbb6b4ba3abc4bd8b57dba033",
  "filename": "clase1_POO.mp4",
  "date": "15/03/2026 10:30",
  "duration_sec": 3542.5,
  "segment_count": 187,
  "model": "large-v3-turbo",
  "language": "es",
  "segments": [
    {"start": 0.0, "end": 4.2, "text": "Bienvenidos a la clase de hoy."},
    {"start": 4.2, "end": 9.1, "text": "Vamos a ver programación orientada a objetos."}
  ]
}
```

## Single Summary (`data/summary/{job_id}_summary_{summary_id}.json`)

```json
{
  "summary_id": "98b268b351954abe89daa5a9c3cf0ab8",
  "job_id": "ce12e9a63f24401793b6e9ea25159586",
  "filename": "clase1_POO.mp4",
  "summary_name": "Resumen - clase1_POO.mp4",
  "ai_provider": "gemini",
  "ai_model": "gemini-2.0-flash",
  "date": "15/03/2026 11:00",
  "summary_type": "general",
  "length": "medium",
  "language": "es",
  "summary": "## Resumen\n\nEl contenido trata sobre..."
}
```

## Multi Summary (`data/summary/multi_summary_{summary_id}.json`)

Same as single but with `job_ids` (list) and `filenames` (list) instead of `job_id`:

```json
{
  "summary_id": "...",
  "job_ids": ["id1", "id2"],
  "filenames": ["parte1.mp4", "parte2.mp4"],
  "filename": "parte1.mp4 + parte2.mp4",
  ...
}
```

## Settings (`data/settings.json`)

```json
{
  "model": "whisper-api",
  "language": "es",
  "ai_provider": "gemini",
  "ollama_url": "http://localhost:11434",
  "ollama_model": "llama3.2",
  "gemini_model": "gemini-2.0-flash"
}
```

API keys (`gemini_api_key`, `openai_api_key`) are loaded from `.env` environment variables, never saved to `settings.json`.

## In-Memory State (`jobs.py`)

These dicts exist only while the server is running:

| Dict | Type | Purpose |
|------|------|---------|
| `jobs` | `{job_id: status_str}` | Transcription job status: `"processing"`, `"done"`, `"cancelled"`, `"error: ..."` |
| `job_progress` | `{job_id: int}` | Transcription progress 0-100 |
| `summary_jobs` | `{summary_id: status_str}` | Summary job status |
| `job_cancel_events` | `{job_id: threading.Event}` | For cancellation signaling |
| `job_filenames` | `{job_id: str}` | Original filename of active transcriptions |

Job IDs are validated as 32-char hex strings (`uuid4().hex`).
