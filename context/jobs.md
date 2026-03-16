# Job System

## Overview

All heavy operations (transcription, summarization) run in background `daemon=True` threads. State is tracked in in-memory dicts defined in `jobs.py`. Everything is lost on server restart.

## Job Lifecycle

### Transcription Jobs

```
Upload → jobs[id] = "processing" → thread runs → jobs[id] = "done" | "error: ..." | "cancelled"
```

1. `POST /upload` creates `job_id` (uuid4 hex), sets `jobs[id] = "processing"`
2. Creates `threading.Event` in `job_cancel_events[id]`
3. Stores original filename in `job_filenames[id]`
4. Starts daemon thread running `_run_transcription()`
5. Thread updates `job_progress[id]` (0-100) as segments arrive
6. On completion: saves JSON, cleans upload file, sets status to `"done"`
7. On cancel: sets status to `"cancelled"`, cleans upload
8. On error: sets status to `"error: {message}"`
9. Always: removes cancel event and filename from dicts

### Summary Jobs

```
Form submit → summary_jobs[id] = "processing" → thread runs → summary_jobs[id] = "done" | "error: ..."
```

Simpler than transcription: no progress tracking, no cancellation support.

## Cancellation

- Only transcription jobs support cancellation
- `POST /cancel/{job_id}` sets the `threading.Event`
- Transcriber checks `cancel_event.is_set()` between segments
- Raises `TranscriptionCancelled` exception

## Cleanup

`cleanup_old_jobs()` runs after each successful transcription. Keeps only the last 200 non-processing jobs in the `jobs` dict to prevent memory growth.

## Status Polling

Frontend polls these endpoints:
- `/status/{job_id}` → `{"status": "...", "progress": 0-100}` (transcription)
- `/summary_status/{summary_id}` → `{"status": "..."}` (summary)

Summary status has a fallback: if `summary_jobs` dict doesn't have the ID but a matching file exists on disk, returns `"done"` (handles server restart case).

## Job ID Format

All job IDs are 32-character hex strings (`uuid.uuid4().hex`). Validated by regex `^[0-9a-f]{32}$` via `is_valid_job_id()`.
