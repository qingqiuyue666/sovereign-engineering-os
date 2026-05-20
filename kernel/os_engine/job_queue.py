"""Brokerless asynchronous local job queue for the Sovereign OS engine."""

from __future__ import annotations

import asyncio
import json
import tempfile
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any, Protocol

JsonScalar = str | int | float | bool | None
JsonValue = JsonScalar | list["JsonValue"] | dict[str, "JsonValue"]


class JobQueueError(RuntimeError):
    """Base exception for queue admission and transition failures."""


class UnknownJobTypeError(JobQueueError):
    """Raised when a job references a worker type outside the registry."""


class InvalidJobTransitionError(JobQueueError):
    """Raised when the queue is asked to violate the finite-state machine."""


class JobStatus(StrEnum):
    CREATED = "created"
    ADMITTED = "admitted"
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    QUARANTINED = "quarantined"

    @property
    def terminal(self) -> bool:
        return self in {self.SUCCEEDED, self.FAILED, self.QUARANTINED}


FSM_TRANSITIONS: dict[JobStatus, frozenset[JobStatus]] = {
    JobStatus.CREATED: frozenset({JobStatus.ADMITTED}),
    JobStatus.ADMITTED: frozenset({JobStatus.PENDING}),
    JobStatus.PENDING: frozenset({JobStatus.RUNNING}),
    JobStatus.RUNNING: frozenset({JobStatus.SUCCEEDED, JobStatus.FAILED, JobStatus.QUARANTINED}),
    JobStatus.SUCCEEDED: frozenset(),
    JobStatus.FAILED: frozenset(),
    JobStatus.QUARANTINED: frozenset(),
}


@dataclass(slots=True)
class Job:
    id: str
    type: str
    status: JobStatus
    inputs: dict[str, JsonValue]
    created_at: datetime
    max_runtime: float
    memory_limit_mb: int
    updated_at: datetime | None = None
    error: str | None = None
    metadata: dict[str, JsonValue] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        *,
        job_type: str,
        inputs: dict[str, JsonValue],
        max_runtime: float,
        memory_limit_mb: int,
    ) -> "Job":
        now = datetime.now(UTC)
        return cls(
            id=f"job_{uuid.uuid4().hex}",
            type=job_type,
            status=JobStatus.CREATED,
            inputs=inputs,
            created_at=now,
            updated_at=now,
            max_runtime=max_runtime,
            memory_limit_mb=memory_limit_mb,
        )

    def transition_to(self, target: JobStatus) -> None:
        allowed = FSM_TRANSITIONS[self.status]
        if target not in allowed:
            raise InvalidJobTransitionError(f"invalid transition {self.status.value} -> {target.value}")
        self.status = target
        self.updated_at = datetime.now(UTC)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type,
            "status": self.status.value,
            "inputs": self.inputs,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "max_runtime": self.max_runtime,
            "memory_limit_mb": self.memory_limit_mb,
            "error": self.error,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "Job":
        return cls(
            id=str(payload["id"]),
            type=str(payload["type"]),
            status=JobStatus(str(payload["status"])),
            inputs=dict(payload.get("inputs", {})),
            created_at=datetime.fromisoformat(str(payload["created_at"])),
            updated_at=(
                datetime.fromisoformat(str(payload["updated_at"]))
                if payload.get("updated_at") is not None
                else None
            ),
            max_runtime=float(payload["max_runtime"]),
            memory_limit_mb=int(payload["memory_limit_mb"]),
            error=payload.get("error"),
            metadata=dict(payload.get("metadata", {})),
        )


@dataclass(frozen=True, slots=True)
class JobEvent:
    job_id: str
    previous_status: str | None
    new_status: str
    message: str
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, JsonValue] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "previous_status": self.previous_status,
            "new_status": self.new_status,
            "message": self.message,
            "created_at": self.created_at.isoformat(),
            "metadata": self.metadata,
        }


class JobStore(Protocol):
    async def save_job(self, job: Job) -> None:
        ...

    async def load_job(self, job_id: str) -> Job | None:
        ...

    async def list_jobs(self) -> list[Job]:
        ...

    async def append_event(self, event: JobEvent) -> None:
        ...


class WorkerAdapterLike(Protocol):
    async def preflight(self, job: Job, context: object) -> None:
        ...

    async def admit(self, job: Job, context: object) -> None:
        ...

    async def run(self, job: Job, context: object) -> object:
        ...

    async def collect_artifacts(self, job: Job, result: object, context: object) -> object:
        ...

    async def cleanup(self, job: Job, result: object | None, context: object) -> None:
        ...


class WorkerRegistryLike(Protocol):
    def has_type(self, job_type: str) -> bool:
        ...

    def get(self, job_type: str) -> WorkerAdapterLike:
        ...


class InMemoryJobStore:
    def __init__(self) -> None:
        self._jobs: dict[str, Job] = {}
        self._events: list[JobEvent] = []
        self._lock = asyncio.Lock()

    async def save_job(self, job: Job) -> None:
        async with self._lock:
            self._jobs[job.id] = Job.from_dict(job.to_dict())

    async def load_job(self, job_id: str) -> Job | None:
        async with self._lock:
            job = self._jobs.get(job_id)
            return Job.from_dict(job.to_dict()) if job is not None else None

    async def list_jobs(self) -> list[Job]:
        async with self._lock:
            return [Job.from_dict(job.to_dict()) for job in self._jobs.values()]

    async def append_event(self, event: JobEvent) -> None:
        async with self._lock:
            self._events.append(event)


class JsonFileJobStore:
    """Small local JSON store; persistence is kept storage-agnostic and brokerless."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.events_path = path.with_suffix(".events.jsonl")
        self._lock = asyncio.Lock()
        self._jobs: dict[str, Job] | None = None

    async def save_job(self, job: Job) -> None:
        async with self._lock:
            await self._ensure_loaded()
            assert self._jobs is not None
            self._jobs[job.id] = Job.from_dict(job.to_dict())
            await asyncio.to_thread(self._write_snapshot)

    async def load_job(self, job_id: str) -> Job | None:
        async with self._lock:
            await self._ensure_loaded()
            assert self._jobs is not None
            job = self._jobs.get(job_id)
            return Job.from_dict(job.to_dict()) if job is not None else None

    async def list_jobs(self) -> list[Job]:
        async with self._lock:
            await self._ensure_loaded()
            assert self._jobs is not None
            return [Job.from_dict(job.to_dict()) for job in self._jobs.values()]

    async def append_event(self, event: JobEvent) -> None:
        payload = json.dumps(event.to_dict(), sort_keys=True)
        await asyncio.to_thread(self._append_event_sync, payload)

    async def _ensure_loaded(self) -> None:
        if self._jobs is not None:
            return
        payload = await asyncio.to_thread(self._read_snapshot)
        self._jobs = {job.id: job for job in payload}

    def _read_snapshot(self) -> list[Job]:
        if not self.path.exists():
            return []
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        if not isinstance(raw, list):
            raise JobQueueError(f"job store must contain a JSON list: {self.path}")
        return [Job.from_dict(item) for item in raw]

    def _write_snapshot(self) -> None:
        assert self._jobs is not None
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = [job.to_dict() for job in self._jobs.values()]
        encoded = json.dumps(payload, indent=2, sort_keys=True)
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=str(self.path.parent),
            delete=False,
        ) as handle:
            handle.write(encoded)
            handle.write("\n")
            tmp_name = handle.name
        Path(tmp_name).replace(self.path)

    def _append_event_sync(self, payload: str) -> None:
        self.events_path.parent.mkdir(parents=True, exist_ok=True)
        with self.events_path.open("a", encoding="utf-8") as handle:
            handle.write(payload)
            handle.write("\n")


class JobQueueManager:
    """Async FIFO queue that runs only explicitly registered worker adapters."""

    def __init__(
        self,
        *,
        registry: WorkerRegistryLike,
        context: object,
        store: JobStore | None = None,
        max_concurrent: int = 1,
    ) -> None:
        if max_concurrent < 1:
            raise ValueError("max_concurrent must be >= 1")
        self.registry = registry
        self.context = context
        self.store = store or InMemoryJobStore()
        self.max_concurrent = max_concurrent
        self.pending: asyncio.Queue[str] = asyncio.Queue()
        self.events: asyncio.Queue[JobEvent] = asyncio.Queue()
        self._workers: list[asyncio.Task[None]] = []
        self._stopping = asyncio.Event()
        self._admission_lock = asyncio.Lock()

    async def start(self) -> None:
        self._stopping.clear()
        await self._rehydrate_local_jobs()
        self._workers = [
            asyncio.create_task(self._worker_loop(worker_id), name=f"job-queue-worker-{worker_id}")
            for worker_id in range(self.max_concurrent)
        ]

    async def stop(self) -> None:
        self._stopping.set()
        for worker in self._workers:
            worker.cancel()
        if self._workers:
            await asyncio.gather(*self._workers, return_exceptions=True)
        self._workers.clear()

    async def submit(
        self,
        *,
        job_type: str,
        inputs: dict[str, JsonValue],
        max_runtime: float,
        memory_limit_mb: int,
    ) -> Job:
        if not self.registry.has_type(job_type):
            raise UnknownJobTypeError(f"unregistered job type blocked: {job_type}")
        if max_runtime <= 0:
            raise ValueError("max_runtime must be positive")
        if memory_limit_mb <= 0:
            raise ValueError("memory_limit_mb must be positive")

        async with self._admission_lock:
            job = Job.create(
                job_type=job_type,
                inputs=inputs,
                max_runtime=max_runtime,
                memory_limit_mb=memory_limit_mb,
            )
            adapter = self.registry.get(job_type)
            await adapter.preflight(job, self.context)
            await adapter.admit(job, self.context)
            await self.store.save_job(job)
            await self._transition(job, JobStatus.ADMITTED, "admitted by registered worker")
            await self._transition(job, JobStatus.PENDING, "queued for execution")
            await self.pending.put(job.id)
            return Job.from_dict(job.to_dict())

    async def list_jobs(self) -> list[Job]:
        return await self.store.list_jobs()

    async def _rehydrate_local_jobs(self) -> None:
        jobs = await self.store.list_jobs()
        for job in jobs:
            if job.status == JobStatus.PENDING:
                await self.pending.put(job.id)
            elif job.status == JobStatus.RUNNING:
                await self._transition(job, JobStatus.QUARANTINED, "stale running job quarantined on boot")

    async def _worker_loop(self, worker_id: int) -> None:
        while not self._stopping.is_set():
            job_id = await self.pending.get()
            try:
                await self._execute(job_id, worker_id=worker_id)
            finally:
                self.pending.task_done()

    async def _execute(self, job_id: str, *, worker_id: int) -> None:
        job = await self.store.load_job(job_id)
        if job is None:
            return
        if job.status != JobStatus.PENDING:
            return
        adapter = self.registry.get(job.type)
        result: object | None = None
        await self._transition(job, JobStatus.RUNNING, f"worker {worker_id} started")
        try:
            result = await adapter.run(job, self.context)
            quarantined = bool(getattr(result, "quarantined", False))
            succeeded = bool(getattr(result, "succeeded", False))
            if succeeded and not quarantined:
                await adapter.collect_artifacts(job, result, self.context)
                await self._transition(job, JobStatus.SUCCEEDED, "worker completed successfully")
            elif quarantined:
                await self._transition(job, JobStatus.QUARANTINED, "worker quarantined by watchdog")
            else:
                await self._transition(job, JobStatus.FAILED, "worker returned failure")
        except Exception as exc:
            job.error = str(exc)
            await self._transition(job, JobStatus.QUARANTINED, f"worker exception: {exc}")
        finally:
            try:
                await adapter.cleanup(job, result, self.context)
            except Exception:
                pass

    async def _transition(self, job: Job, target: JobStatus, message: str) -> None:
        previous = job.status
        job.transition_to(target)
        await self.store.save_job(job)
        event = JobEvent(
            job_id=job.id,
            previous_status=previous.value if previous else None,
            new_status=target.value,
            message=message,
        )
        await self.store.append_event(event)
        await self.events.put(event)
