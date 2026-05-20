"""Bounded read models for the Sovereign Console Phase 1 shell."""

from __future__ import annotations

import json
import platform
import resource
import sqlite3
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator

JOB_LIMIT_DEFAULT = 100
EVENT_LIMIT_DEFAULT = 200
ARTIFACT_LIMIT_DEFAULT = 200
WARNING_LIMIT_DEFAULT = 200
SYNC_STALE_AFTER_MS = 2_000


@dataclass(frozen=True, slots=True)
class JobRow:
    job_id: str
    job_type: str
    status: str
    worker: str
    created_at: str
    runtime: str
    event_count: int
    artifact_count: int
    human_review_required: bool
    failure_reason: str = ""
    quarantine_reason: str = ""
    final_claim_allowed: bool | None = None

    def metadata(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "job_id": self.job_id,
            "job_type": self.job_type,
            "status": self.status,
            "worker": self.worker,
            "event_count": self.event_count,
            "artifact_count": self.artifact_count,
            "failure_reason": self.failure_reason,
            "quarantine_reason": self.quarantine_reason,
            "human_review_required": self.human_review_required,
        }
        if self.final_claim_allowed is not None:
            payload["final_claim_allowed"] = self.final_claim_allowed
        return payload


@dataclass(frozen=True, slots=True)
class EventRow:
    event_id: str
    job_id: str
    sequence: int
    event_type: str
    occurred_at: str
    reason: str = ""

    def line(self) -> str:
        reason = f" | {self.reason}" if self.reason else ""
        return f"{self.occurred_at} {self.event_type} job={self.job_id} seq={self.sequence}{reason}"


@dataclass(frozen=True, slots=True)
class RuntimeSnapshot:
    captured_at_ms: int
    runtime_status: str
    wal_status: str
    queue_depth: int
    workers: str
    memory_pressure: str
    warning_count: int
    next_required_action: str
    sync_stale: bool
    runtime_available: bool
    database_available: bool
    latest_jobs: tuple[JobRow, ...] = field(default_factory=tuple)
    latest_events: tuple[EventRow, ...] = field(default_factory=tuple)
    latest_artifacts_count: int = 0
    active_jobs: int = 0
    failed_jobs: int = 0
    quarantined_jobs: int = 0
    hfx_008_landing_summary: str = "Dry-run landing readiness report available"
    desktop_smoke_summary: str = "Headless desktop smoke path available"
    resource_warning_status: str = "No ResourceWarning observed"

    def age_ms(self, *, now_ms: int | None = None) -> int:
        now = int(time.time() * 1000) if now_ms is None else int(now_ms)
        return max(0, now - int(self.captured_at_ms))

    def is_sync_lost(self, *, now_ms: int | None = None, stale_after_ms: int = SYNC_STALE_AFTER_MS) -> bool:
        return (
            self.sync_stale
            or not self.runtime_available
            or not self.database_available
            or self.age_ms(now_ms=now_ms) > stale_after_ms
        )


class ReadModelProvider:
    """Read-only provider for small SQLite snapshots."""

    def __init__(
        self,
        *,
        runtime_root: Path,
        job_limit: int = JOB_LIMIT_DEFAULT,
        event_limit: int = EVENT_LIMIT_DEFAULT,
    ) -> None:
        if job_limit <= 0 or event_limit <= 0:
            raise ValueError("read model limits must be positive")
        self.runtime_root = runtime_root.expanduser().resolve()
        self.db_path = self.runtime_root / "os_engine.sqlite3"
        self.job_limit = int(job_limit)
        self.event_limit = int(event_limit)

    def snapshot_runtime_status(self) -> RuntimeSnapshot:
        captured_at_ms = _now_ms()
        if not self.db_path.exists():
            return _unavailable_snapshot(captured_at_ms, database_available=False)
        try:
            with self._readonly_connection() as connection:
                wal_status = _read_wal_status(connection)
                jobs = self._latest_jobs(connection, limit=self.job_limit)
                events = self._latest_events(connection, limit=self.event_limit)
                queue_depth = _bounded_status_count(
                    connection,
                    statuses=("admitted", "pending", "running", "requires_human_review"),
                    limit=self.job_limit,
                )
                active_jobs = _bounded_status_count(connection, statuses=("running",), limit=self.job_limit)
                failed_jobs = _bounded_status_count(connection, statuses=("failed",), limit=self.job_limit)
                quarantined_jobs = _bounded_status_count(connection, statuses=("quarantined",), limit=self.job_limit)
                warning_count = _bounded_status_count(
                    connection,
                    statuses=("failed", "quarantined", "requires_human_review"),
                    limit=WARNING_LIMIT_DEFAULT,
                )
                latest_artifacts_count = _bounded_artifact_count(connection, limit=ARTIFACT_LIMIT_DEFAULT)
            return RuntimeSnapshot(
                captured_at_ms=captured_at_ms,
                runtime_status="Available",
                wal_status=wal_status,
                queue_depth=queue_depth,
                workers="Registry read-only",
                memory_pressure=_memory_pressure_label(),
                warning_count=warning_count,
                next_required_action=_next_required_action(warning_count=warning_count, queue_depth=queue_depth),
                sync_stale=False,
                runtime_available=True,
                database_available=True,
                latest_jobs=tuple(jobs),
                latest_events=tuple(events),
                latest_artifacts_count=latest_artifacts_count,
                active_jobs=active_jobs,
                failed_jobs=failed_jobs,
                quarantined_jobs=quarantined_jobs,
            )
        except sqlite3.Error:
            return _unavailable_snapshot(captured_at_ms, database_available=False)

    def snapshot_selected_job(self, job_id: str) -> RuntimeSnapshot:
        captured_at_ms = _now_ms()
        if not job_id or not self.db_path.exists():
            return _unavailable_snapshot(captured_at_ms, database_available=self.db_path.exists())
        try:
            with self._readonly_connection() as connection:
                row = connection.execute(
                    """
                    SELECT job_id, job_type, created_at, current_status, human_review_required
                    FROM jobs
                    WHERE job_id = ?
                    LIMIT 1
                    """,
                    (job_id,),
                ).fetchone()
                if row is None:
                    return _unavailable_snapshot(captured_at_ms, database_available=True)
                selected = self._job_row_from_sql(connection, row)
                events = self._events_for_job(connection, job_id=job_id, limit=self.event_limit)
            return RuntimeSnapshot(
                captured_at_ms=captured_at_ms,
                runtime_status="Available",
                wal_status="WAL",
                queue_depth=0,
                workers="Registry read-only",
                memory_pressure=_memory_pressure_label(),
                warning_count=0,
                next_required_action="Inspect selected job",
                sync_stale=False,
                runtime_available=True,
                database_available=True,
                latest_jobs=(selected,),
                latest_events=tuple(events),
                latest_artifacts_count=selected.artifact_count,
                active_jobs=1 if selected.status == "Running" else 0,
                failed_jobs=1 if selected.status == "Failed" else 0,
                quarantined_jobs=1 if selected.status == "Quarantined" else 0,
            )
        except sqlite3.Error:
            return _unavailable_snapshot(captured_at_ms, database_available=False)

    @contextmanager
    def _readonly_connection(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(f"file:{self.db_path}?mode=ro", uri=True)
        try:
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA query_only = ON")
            yield connection
        finally:
            connection.close()

    def _latest_jobs(self, connection: sqlite3.Connection, *, limit: int) -> list[JobRow]:
        rows = connection.execute(
            """
            SELECT job_id, job_type, created_at, current_status, human_review_required
            FROM jobs
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (int(limit),),
        ).fetchall()
        return [self._job_row_from_sql(connection, row) for row in rows]

    def _job_row_from_sql(self, connection: sqlite3.Connection, row: sqlite3.Row) -> JobRow:
        job_id = str(row["job_id"])
        event_count = _count_for_job(connection, table="job_events", id_column="job_id", job_id=job_id)
        artifact_count = _count_for_job(connection, table="artifacts", id_column="job_id", job_id=job_id)
        worker = _latest_event_payload_value(
            connection,
            job_id=job_id,
            event_type="WorkerSelected",
            payload_key="worker_name",
        )
        failure_reason = _latest_event_reason(connection, job_id=job_id, event_type="JobFailed")
        quarantine_reason = _latest_event_reason(connection, job_id=job_id, event_type="JobQuarantined")
        return JobRow(
            job_id=job_id,
            job_type=str(row["job_type"]),
            status=_strict_status_label(str(row["current_status"])),
            worker=worker or "",
            created_at=str(row["created_at"]),
            runtime=_runtime_label(connection, job_id=job_id, created_at=str(row["created_at"])),
            event_count=event_count,
            artifact_count=artifact_count,
            human_review_required=bool(row["human_review_required"]),
            failure_reason=failure_reason or "",
            quarantine_reason=quarantine_reason or "",
        )

    def _latest_events(self, connection: sqlite3.Connection, *, limit: int) -> list[EventRow]:
        rows = connection.execute(
            """
            SELECT event_id, job_id, sequence, event_type, occurred_at, reason
            FROM job_events
            ORDER BY occurred_at DESC, sequence DESC
            LIMIT ?
            """,
            (int(limit),),
        ).fetchall()
        return [_event_row_from_sql(row) for row in rows]

    def _events_for_job(self, connection: sqlite3.Connection, *, job_id: str, limit: int) -> list[EventRow]:
        rows = connection.execute(
            """
            SELECT event_id, job_id, sequence, event_type, occurred_at, reason
            FROM job_events
            WHERE job_id = ?
            ORDER BY sequence DESC
            LIMIT ?
            """,
            (job_id, int(limit)),
        ).fetchall()
        return [_event_row_from_sql(row) for row in reversed(rows)]


def fake_phase1_snapshot(*, stale: bool = False) -> RuntimeSnapshot:
    captured_at_ms = _now_ms() - (SYNC_STALE_AFTER_MS + 500 if stale else 0)
    jobs = (
        JobRow(
            job_id="job_hfx_008_landing",
            job_type="hfx_landing_chain",
            status="Dry Run Complete",
            worker="landing-readiness",
            created_at="2026-05-20T09:00:00+00:00",
            runtime="00:02:18",
            event_count=5,
            artifact_count=2,
            human_review_required=False,
            final_claim_allowed=False,
        ),
        JobRow(
            job_id="job_context_pack_review",
            job_type="context_pack",
            status="Requires Human Review",
            worker="context-pack-worker",
            created_at="2026-05-20T09:04:00+00:00",
            runtime="00:00:44",
            event_count=4,
            artifact_count=1,
            human_review_required=True,
            final_claim_allowed=False,
        ),
    )
    events = (
        EventRow("evt_demo_001", "job_hfx_008_landing", 1, "JobCreated", "2026-05-20T09:00:00+00:00"),
        EventRow("evt_demo_002", "job_hfx_008_landing", 2, "WorkerSelected", "2026-05-20T09:00:01+00:00"),
        EventRow("evt_demo_003", "job_hfx_008_landing", 3, "ArtifactRecorded", "2026-05-20T09:01:10+00:00"),
        EventRow("evt_demo_004", "job_context_pack_review", 4, "HumanReviewRequested", "2026-05-20T09:05:00+00:00"),
        EventRow("evt_demo_005", "job_hfx_008_landing", 5, "JobSucceeded", "2026-05-20T09:02:18+00:00"),
        EventRow("evt_demo_006", "job_materialize_guard", 3, "MaterializationBlocked", "2026-05-20T09:06:00+00:00"),
        EventRow("evt_demo_007", "job_review_ok", 5, "ReviewApproved", "2026-05-20T09:07:00+00:00"),
        EventRow("evt_demo_008", "job_review_stop", 5, "ReviewRejected", "2026-05-20T09:08:00+00:00"),
        EventRow("evt_demo_009", "job_quarantine", 4, "JobQuarantined", "2026-05-20T09:09:00+00:00"),
    )
    return RuntimeSnapshot(
        captured_at_ms=captured_at_ms,
        runtime_status="Available",
        wal_status="WAL",
        queue_depth=1,
        workers="2 registered",
        memory_pressure=_memory_pressure_label(),
        warning_count=1,
        next_required_action="Review gated context pack",
        sync_stale=stale,
        runtime_available=not stale,
        database_available=not stale,
        latest_jobs=jobs,
        latest_events=events,
        latest_artifacts_count=3,
        active_jobs=0,
        failed_jobs=0,
        quarantined_jobs=1,
    )


def _event_row_from_sql(row: sqlite3.Row) -> EventRow:
    return EventRow(
        event_id=str(row["event_id"]),
        job_id=str(row["job_id"]),
        sequence=int(row["sequence"]),
        event_type=str(row["event_type"]),
        occurred_at=str(row["occurred_at"]),
        reason=str(row["reason"] or ""),
    )


def _now_ms() -> int:
    return int(time.time() * 1000)


def _unavailable_snapshot(captured_at_ms: int, *, database_available: bool) -> RuntimeSnapshot:
    return RuntimeSnapshot(
        captured_at_ms=captured_at_ms,
        runtime_status="Unavailable",
        wal_status="Unknown",
        queue_depth=0,
        workers="Unknown",
        memory_pressure=_memory_pressure_label(),
        warning_count=1,
        next_required_action="Reconnect local runtime projection",
        sync_stale=True,
        runtime_available=False,
        database_available=database_available,
    )


def _read_wal_status(connection: sqlite3.Connection) -> str:
    row = connection.execute("PRAGMA journal_mode").fetchone()
    value = str(row[0]).upper() if row else "UNKNOWN"
    return value


def _bounded_status_count(connection: sqlite3.Connection, *, statuses: tuple[str, ...], limit: int) -> int:
    placeholders = ",".join("?" for _ in statuses)
    rows = connection.execute(
        f"""
        SELECT COUNT(job_id)
        FROM (
            SELECT job_id
            FROM jobs
            WHERE current_status IN ({placeholders})
            ORDER BY created_at DESC
            LIMIT ?
        )
        """,
        (*statuses, int(limit)),
    ).fetchone()
    return int(rows[0]) if rows else 0


def _bounded_artifact_count(connection: sqlite3.Connection, *, limit: int) -> int:
    rows = connection.execute(
        """
        SELECT COUNT(artifact_id)
        FROM (
            SELECT artifact_id
            FROM artifacts
            ORDER BY updated_at DESC
            LIMIT ?
        )
        """,
        (int(limit),),
    ).fetchone()
    return int(rows[0]) if rows else 0


def _count_for_job(connection: sqlite3.Connection, *, table: str, id_column: str, job_id: str) -> int:
    if table not in {"job_events", "artifacts"} or id_column != "job_id":
        raise ValueError("unsupported bounded job count")
    row = connection.execute(
        f"""
        SELECT COUNT({id_column})
        FROM (
            SELECT {id_column}
            FROM {table}
            WHERE {id_column} = ?
            LIMIT ?
        )
        """,
        (job_id, EVENT_LIMIT_DEFAULT),
    ).fetchone()
    return int(row[0]) if row else 0


def _latest_event_payload_value(
    connection: sqlite3.Connection,
    *,
    job_id: str,
    event_type: str,
    payload_key: str,
) -> str:
    row = connection.execute(
        """
        SELECT payload_json
        FROM job_events
        WHERE job_id = ? AND event_type = ?
        ORDER BY sequence DESC
        LIMIT 1
        """,
        (job_id, event_type),
    ).fetchone()
    if row is None:
        return ""
    try:
        payload = json.loads(str(row["payload_json"]))
    except json.JSONDecodeError:
        return ""
    value = payload.get(payload_key) if isinstance(payload, dict) else ""
    return str(value) if value is not None else ""


def _latest_event_reason(connection: sqlite3.Connection, *, job_id: str, event_type: str) -> str:
    row = connection.execute(
        """
        SELECT reason
        FROM job_events
        WHERE job_id = ? AND event_type = ?
        ORDER BY sequence DESC
        LIMIT 1
        """,
        (job_id, event_type),
    ).fetchone()
    return str(row["reason"] or "") if row else ""


def _runtime_label(connection: sqlite3.Connection, *, job_id: str, created_at: str) -> str:
    row = connection.execute(
        """
        SELECT occurred_at
        FROM job_events
        WHERE job_id = ?
        ORDER BY sequence DESC
        LIMIT 1
        """,
        (job_id,),
    ).fetchone()
    if row is None:
        return "00:00:00"
    return f"{created_at} -> {row['occurred_at']}"


def _strict_status_label(raw_status: str) -> str:
    normalized = raw_status.strip().lower()
    mapping = {
        "created": "Not Started",
        "admitted": "Pending",
        "pending": "Pending",
        "running": "Running",
        "succeeded": "Succeeded",
        "failed": "Failed",
        "quarantined": "Quarantined",
        "requires_human_review": "Requires Human Review",
        "cancelled": "Blocked: Missing Resource",
    }
    return mapping.get(normalized, raw_status.strip() or "Not Started")


def _memory_pressure_label() -> str:
    usage = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    rss_mb = float(usage) / (1024 * 1024) if platform.system() == "Darwin" else float(usage) / 1024
    if rss_mb >= 1_024:
        return f"High ({rss_mb:.0f} MB)"
    if rss_mb >= 512:
        return f"Elevated ({rss_mb:.0f} MB)"
    return f"Nominal ({rss_mb:.0f} MB)"


def _next_required_action(*, warning_count: int, queue_depth: int) -> str:
    if warning_count:
        return "Inspect warnings"
    if queue_depth:
        return "Monitor queued work"
    return "Observe runtime"
