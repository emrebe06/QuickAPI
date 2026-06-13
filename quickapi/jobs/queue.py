from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import UTC, datetime
from threading import Lock
from time import perf_counter
from typing import Any, Callable
from uuid import uuid4


TERMINAL_STATES = {"done", "failed", "cancelled"}


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


@dataclass
class JobRecord:
    id: str
    name: str
    status: str = "queued"
    created_at: str = field(default_factory=now_iso)
    started_at: str | None = None
    finished_at: str | None = None
    duration_ms: float | None = None
    result: Any = None
    error: dict[str, Any] | None = None
    future: Future | None = field(default=None, repr=False)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "status": self.status,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "duration_ms": self.duration_ms,
            "result": self.result if self.status == "done" else None,
            "error": self.error,
        }


class JobQueue:
    def __init__(self, max_workers: int = 4, max_history: int = 1000):
        self.max_workers = max_workers
        self.max_history = max_history
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="quickapi-job")
        self._jobs: dict[str, JobRecord] = {}
        self._lock = Lock()

    def submit(self, func: Callable[..., Any], *args, name: str | None = None, **kwargs) -> JobRecord:
        record = JobRecord(id=uuid4().hex, name=name or getattr(func, "__name__", "job"))
        with self._lock:
            self._jobs[record.id] = record
            self._trim_locked()
        future = self._executor.submit(self._run, record.id, func, args, kwargs)
        record.future = future
        return record

    def get(self, job_id: str) -> JobRecord | None:
        with self._lock:
            return self._jobs.get(job_id)

    def list(self) -> list[dict[str, Any]]:
        with self._lock:
            return [job.to_dict() for job in sorted(self._jobs.values(), key=lambda item: item.created_at, reverse=True)]

    def cancel(self, job_id: str) -> JobRecord | None:
        with self._lock:
            record = self._jobs.get(job_id)
            if record is None:
                return None
            if record.status in TERMINAL_STATES:
                return record
            if record.future and record.future.cancel():
                record.status = "cancelled"
                record.finished_at = now_iso()
            else:
                record.error = {"message": "Job is already running and cannot be interrupted safely."}
            return record

    def shutdown(self):
        self._executor.shutdown(wait=False, cancel_futures=True)

    def _run(self, job_id: str, func: Callable[..., Any], args: tuple[Any, ...], kwargs: dict[str, Any]):
        start = perf_counter()
        with self._lock:
            record = self._jobs[job_id]
            record.status = "running"
            record.started_at = now_iso()
        try:
            result = func(*args, **kwargs)
            with self._lock:
                record.result = result
                record.status = "done"
        except Exception as exc:
            with self._lock:
                record.status = "failed"
                record.error = {"type": exc.__class__.__name__, "message": str(exc)}
        finally:
            with self._lock:
                record.finished_at = now_iso()
                record.duration_ms = round((perf_counter() - start) * 1000, 3)

    def _trim_locked(self):
        if len(self._jobs) <= self.max_history:
            return
        removable = [job for job in self._jobs.values() if job.status in TERMINAL_STATES]
        removable.sort(key=lambda item: item.created_at)
        for job in removable[: max(0, len(self._jobs) - self.max_history)]:
            self._jobs.pop(job.id, None)
