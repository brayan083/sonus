import re
import threading

_VALID_JOB_ID = re.compile(r"^[0-9a-f]{32}$")

# In-memory state
jobs: dict[str, str] = {}
job_progress: dict[str, int] = {}
summary_jobs: dict[str, str] = {}
job_cancel_events: dict[str, threading.Event] = {}
job_filenames: dict[str, str] = {}


def is_valid_job_id(job_id: str) -> bool:
    return bool(_VALID_JOB_ID.match(job_id))


def cleanup_old_jobs():
    stale = [jid for jid, status in jobs.items() if status != "processing"]
    if len(stale) > 200:
        for jid in stale[:len(stale) - 200]:
            jobs.pop(jid, None)
            job_progress.pop(jid, None)
