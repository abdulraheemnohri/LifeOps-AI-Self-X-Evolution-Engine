"""Background scheduler and bounded worker queue with job events, retries,
and crash recovery without duplicating completed side effects."""
import datetime
import queue
import threading
import uuid
from typing import Any, Callable, Dict, List, Optional

from lifeops.storage.models import ScheduledJob, JobEvent


class CronExpression:
    """Minimal 5-field cron parser (minute hour dom month dow) supporting
    numbers, '*', ranges, lists, and step values."""

    def __init__(self, expression: str):
        self.fields = expression.strip().split()
        if len(self.fields) != 5:
            raise ValueError(f"cron expression needs 5 fields, got '{expression}'")

    def _match(self, field: str, value: int) -> bool:
        if field == "*":
            return True
        for part in field.split(","):
            if part.startswith("*/"):
                step = int(part[2:])
                if step > 0 and value % step == 0:
                    return True
            elif "-" in part:
                lo, hi = part.split("-")
                if int(lo) <= value <= int(hi):
                    return True
            elif part.isdigit() and int(part) == value:
                return True
        return False

    def matches(self, dt: datetime.datetime) -> bool:
        f = self.fields
        dow = (dt.weekday() + 1) % 7  # cron: 0=Sunday
        return (self._match(f[0], dt.minute) and self._match(f[1], dt.hour)
                and self._match(f[2], dt.day) and self._match(f[3], dt.month)
                and self._match(f[4], dow))


JOB_HANDLERS: Dict[str, Callable[..., Dict[str, Any]]] = {}


def register_handler(name: str):
    def deco(fn):
        JOB_HANDLERS[name] = fn
        return fn
    return deco


@register_handler("noop")
def _handler_noop(**kwargs):
    return {"ok": True, "handler": "noop", **kwargs}


@register_handler("create_task")
def _handler_create_task(title: str = "Scheduled task", **kwargs):
    from lifeops.storage.database import get_engine, get_session_factory
    from lifeops.lifeops.tasks import TaskService
    db = get_session_factory(get_engine())()
    try:
        t = TaskService(db).create_task(title=title)
        return {"task_id": t.id, "title": t.title}
    finally:
        db.close()


@register_handler("daily_plan")
def _handler_daily_plan(**kwargs):
    from lifeops.storage.database import get_engine, get_session_factory
    from lifeops.lifeops.tasks import DailyPlannerEngine
    db = get_session_factory(get_engine())()
    try:
        return DailyPlannerEngine(db).generate_daily_plan()
    finally:
        db.close()


class WorkerQueue:
    """Bounded in-process worker pool. Jobs are persisted first, executed by
    workers, and completion is recorded in job_events so a restart can recover
    without re-running finished work (idempotent via event check)."""

    def __init__(self, session_factory, concurrency: int = 2, queue_limit: int = 100,
                 retry_count: int = 2, poll_interval: float = 0.2):
        self.session_factory = session_factory
        self.concurrency = max(1, concurrency)
        self.retry_count = retry_count
        self.poll_interval = poll_interval
        self._q: "queue.Queue[str]" = queue.Queue(maxsize=queue_limit)
        self._threads: List[threading.Thread] = []
        self._stop = threading.Event()
        self._lock = threading.Lock()

    def _emit(self, job_id: str, event_type: str, details: Dict[str, Any]):
        db = self.session_factory()
        try:
            db.add(JobEvent(job_id=job_id, event_type=event_type, details=details))
            db.commit()
        finally:
            db.close()

    def enqueue(self, job_id: str) -> bool:
        try:
            self._q.put_nowait(job_id)
            self._emit(job_id, "queued", {})
            return True
        except queue.Full:
            self._emit(job_id, "enqueue_rejected_queue_full", {})
            return False

    def submit_action(self, name: str, action: Dict[str, Any]) -> str:
        """Create a scheduled_jobs row for an ad-hoc background action and enqueue it."""
        job_id = f"job_{uuid.uuid4().hex[:12]}"
        db = self.session_factory()
        try:
            db.add(ScheduledJob(id=job_id, name=name, cron_expression="",
                                 action=action, enabled=True))
            db.commit()
        finally:
            db.close()
        self.enqueue(job_id)
        return job_id

    def execute_job(self, job_id: str) -> Dict[str, Any]:
        db = self.session_factory()
        try:
            job = db.get(ScheduledJob, job_id)
            if not job:
                return {"status": "not_found"}
            # Idempotency guard: skip if already completed (recovery-safe).
            done = db.query(JobEvent).filter_by(job_id=job_id, event_type="completed").first()
            if done:
                self._emit(job_id, "skipped_already_done", {})
                return {"status": "skipped"}
            handler_name = job.action.get("handler", "noop")
            kwargs = {k: v for k, v in job.action.items() if k != "handler"}
            attempt, result = 0, None
            while attempt <= self.retry_count:
                try:
                    handler = JOB_HANDLERS.get(handler_name)
                    if handler is None:
                        raise KeyError(f"no handler '{handler_name}'")
                    result = handler(**kwargs)
                    break
                except Exception as exc:
                    attempt += 1
                    self._emit(job_id, "retry", {"attempt": attempt, "error": str(exc)})
                    result = {"status": "failed", "error": str(exc)}
            status = "failed" if isinstance(result, dict) and result.get("status") == "failed" else "completed"
            job.last_run_at = datetime.datetime.utcnow()
            db.commit()
            self._emit(job_id, status, {"result": result})
            return {"status": status, "result": result}
        finally:
            db.close()

    def _worker_loop(self):
        while not self._stop.is_set():
            try:
                job_id = self._q.get(timeout=self.poll_interval)
            except queue.Empty:
                continue
            try:
                self.execute_job(job_id)
            finally:
                self._q.task_done()

    def start(self):
        with self._lock:
            if self._threads:
                return
            self._stop.clear()
            for i in range(self.concurrency):
                t = threading.Thread(target=self._worker_loop, name=f"lifeops-worker-{i}", daemon=True)
                t.start()
                self._threads.append(t)

    def stop(self, timeout: float = 2.0):
        self._stop.set()
        for t in self._threads:
            t.join(timeout=timeout)
        with self._lock:
            self._threads = []

    def recover_pending(self) -> int:
        """On startup, re-enqueue jobs that were queued but never completed."""
        db = self.session_factory()
        count = 0
        try:
            jobs = db.query(ScheduledJob).filter_by(enabled=True).all()
            for job in jobs:
                has_complete = db.query(JobEvent).filter_by(job_id=job.id, event_type="completed").first()
                was_queued = db.query(JobEvent).filter_by(job_id=job.id, event_type="queued").first()
                if was_queued and not has_complete and not job.cron_expression:
                    if self.enqueue(job.id):
                        count += 1
            return count
        finally:
            db.close()

    def stats(self) -> Dict[str, Any]:
        return {"concurrency": self.concurrency, "workers": len(self._threads),
                "queued": self._q.qsize(), "running": len(self._threads) > 0}


class Scheduler:
    """Lightweight tick loop that fires cron-matching scheduled jobs once per minute bucket."""

    def __init__(self, session_factory, worker: WorkerQueue, tick_seconds: float = 30.0):
        self.session_factory = session_factory
        self.worker = worker
        self.tick_seconds = tick_seconds
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self._last_fired: Dict[str, str] = {}

    def _tick(self):
        now = datetime.datetime.utcnow()
        bucket = now.strftime("%Y-%m-%d %H:%M")
        db = self.session_factory()
        try:
            jobs = db.query(ScheduledJob).filter(ScheduledJob.enabled == True).all()  # noqa: E712
            for job in jobs:
                if not job.cron_expression:
                    continue
                try:
                    cron = CronExpression(job.cron_expression)
                except ValueError:
                    continue
                if cron.matches(now) and self._last_fired.get(job.id) != bucket:
                    self._last_fired[job.id] = bucket
                    job.last_run_at = now
                    db.add(JobEvent(job_id=job.id, event_type="fired", details={"bucket": bucket}))
                    db.commit()
                    self.worker.enqueue(job.id)
        finally:
            db.close()

    def start(self):
        if self._thread:
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, name="lifeops-scheduler", daemon=True)
        self._thread.start()

    def _loop(self):
        while not self._stop.wait(self.tick_seconds):
            try:
                self._tick()
            except Exception:
                pass

    def stop(self):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2.0)
            self._thread = None
