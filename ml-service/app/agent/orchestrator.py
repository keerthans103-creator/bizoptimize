"""
Job orchestration: planner -> executor -> verifier, with a genuine
replan-on-failure loop (not a retry of the same action) and a human-
approval gate before any risky action executes.

In-memory job store, not Redis/Postgres -- there's no Redis provisioned,
and job state here is short-lived/session-scoped, not something worth a
new persistence dependency for. Real limitation, stated plainly: job state
does not survive a process restart. Acceptable for this feature's current
scope; a Postgres-backed job table via the existing backend is the natural
next step if this becomes more than a demo.

Jobs run on a small ThreadPoolExecutor. This is safe on a single-gunicorn-
worker service specifically because the workload is I/O-bound (waiting on
Gemini API calls) -- the GIL releases during those waits, so a background
thread doing agent work doesn't stop the worker's main thread from still
answering /health and other requests concurrently. This would NOT be true
for CPU-bound background work.

Concurrency note on job state: mutations happen on a background thread,
reads happen on Flask request threads. Dict-level access (create/lookup)
goes through a lock; field-level reads during to_dict() rely on CPython's
GIL making individual attribute/list reads atomic. That's adequate for a
status-polling endpoint (a slightly-stale snapshot is fine) but would not
be adequate if this ever needed strict consistency guarantees.
"""
import logging
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field

from app.agent import executor, planner, sandbox, verifier

logger = logging.getLogger(__name__)

MAX_CONCURRENT_JOBS = 2
MAX_REPLANS_PER_STEP = 2
JOB_RETENTION_SECONDS = 60 * 60  # purge job state older than this on each new job

_pool = ThreadPoolExecutor(max_workers=MAX_CONCURRENT_JOBS, thread_name_prefix="agent-job")
_jobs = {}
_jobs_lock = threading.Lock()


@dataclass
class StepRecord:
    message_id: str
    description: str
    action: str
    risky: bool
    status: str = "pending"  # pending|executing|verifying|passed|failed|replanned
    result: dict = None
    verification: dict = None
    attempts: int = 0

    def to_dict(self):
        return {
            "message_id": self.message_id,
            "description": self.description,
            "action": self.action,
            "risky": self.risky,
            "status": self.status,
            "result": self.result,
            "verification": self.verification,
            "attempts": self.attempts,
        }


@dataclass
class JobState:
    job_id: str
    task_text: str
    status: str = "planning"
    steps: list = field(default_factory=list)
    error: str = None
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    approval_event: threading.Event = field(default_factory=threading.Event)
    approved: bool = False
    rejected: bool = False

    def to_dict(self):
        return {
            "job_id": self.job_id,
            "task_text": self.task_text,
            "status": self.status,
            "error": self.error,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "steps": [s.to_dict() for s in self.steps],
        }


def _purge_old_jobs_locked():
    cutoff = time.time() - JOB_RETENTION_SECONDS
    stale = [jid for jid, job in _jobs.items() if job.updated_at < cutoff]
    for jid in stale:
        del _jobs[jid]


def create_job(task_text: str) -> str:
    with _jobs_lock:
        _purge_old_jobs_locked()
        job_id = uuid.uuid4().hex
        _jobs[job_id] = JobState(job_id=job_id, task_text=task_text)

    _pool.submit(_run_job, job_id)
    return job_id


def get_job(job_id: str):
    with _jobs_lock:
        job = _jobs.get(job_id)
        return job.to_dict() if job else None


def approve_job(job_id: str) -> bool:
    with _jobs_lock:
        job = _jobs.get(job_id)
        if job is None or job.status != "awaiting_approval":
            return False
        job.approved = True
    job.approval_event.set()
    return True


def reject_job(job_id: str) -> bool:
    with _jobs_lock:
        job = _jobs.get(job_id)
        if job is None or job.status != "awaiting_approval":
            return False
        job.rejected = True
    job.approval_event.set()
    return True


def _touch(job: JobState, status: str = None):
    if status:
        job.status = status
    job.updated_at = time.time()


def _run_job(job_id: str):
    with _jobs_lock:
        job = _jobs[job_id]

    try:
        inbox = sandbox.seed_inbox()
        unread = sandbox.list_unread(inbox)

        _touch(job, "planning")
        plan = planner.create_initial_plan(job.task_text, unread)
        job.steps = [
            StepRecord(
                message_id=s["message_id"],
                description=s.get("description", ""),
                action=s["action"],
                risky=s["action"] in executor.RISKY_ACTIONS,
            )
            for s in plan
        ]
        _touch(job)

        # One job-level approval gate covering every risky step, requested
        # once before the first one executes. Approval covers the action
        # *type* (send_reply) for this job, not one gate per message --
        # nobody wants to click approve N times for one job, and a step
        # that gets replanned into send_reply is still covered by this
        # same gate since it's the same job.
        if any(s.risky for s in job.steps):
            _touch(job, "awaiting_approval")
            job.approval_event.wait()
            if job.rejected:
                _touch(job, "rejected")
                return

        _touch(job, "executing")
        for step in job.steps:
            _run_step(job, inbox, step)
            if job.status == "failed":
                return

        _touch(job, "completed")

    except Exception as exc:  # noqa: BLE001 -- background thread has no
        # caller to propagate to; record the failure on the job instead of
        # letting it vanish silently inside the thread pool.
        logger.exception("Agent job %s crashed", job_id)
        job.error = str(exc)
        _touch(job, "failed")


def _run_step(job: JobState, inbox: list, step: StepRecord):
    message = sandbox.get_message(inbox, step.message_id)

    for attempt in range(MAX_REPLANS_PER_STEP + 1):
        step.attempts = attempt + 1
        step.status = "executing"
        _touch(job)

        result = executor.execute_step(
            inbox, step.action, step.message_id, reason=step.description
        )
        step.result = result

        step.status = "verifying"
        _touch(job)

        if step.action == "send_reply":
            verification = verifier.verify_reply(message, result.get("reply_text", ""))
        elif step.action == "flag_for_review":
            verification = verifier.verify_flag(message)
        else:
            verification = {"passed": False, "reason": f"no verifier for action {step.action}"}
        step.verification = verification

        if verification.get("passed"):
            step.status = "passed"
            _touch(job)
            return

        if attempt >= MAX_REPLANS_PER_STEP:
            step.status = "failed"
            job.error = (
                f"Step for {step.message_id} failed verification after "
                f"{attempt + 1} attempts: {verification.get('reason')}"
            )
            _touch(job, "failed")
            return

        step.status = "replanned"
        _touch(job)
        revised = planner.replan_step(
            message, result.get("reply_text", ""), verification.get("reason", "")
        )
        step.action = revised.get("action", step.action)
        step.description = revised.get("description", step.description)
