"""Read-only replay browser for OS engine event history.

The browser projects durable SQLite job events into deterministic audit
summaries. It never mutates the database, executes jobs, launches browsers, or
touches networks.
"""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterator

from kernel.os_engine.database import UnsafePayloadError, stable_content_hash, validate_no_secret_like
from kernel.os_engine.job_projection import JobProjectionError, ProjectedJobState, project_job_state
from kernel.os_engine.schema_version import SCHEMA_CONTENT_HASH

__all__ = [
    "ReplayBrowserArtifact",
    "ReplayBrowserEvent",
    "ReplayBrowserFilter",
    "ReplayBrowserJobTrace",
    "ReplayBrowserSummary",
    "browse_os_engine_replay",
    "render_replay_browser_summary",
]


_REQUIRED_TABLES = frozenset({"schema_version", "jobs", "job_events", "artifacts"})
_MAX_JOB_LIMIT = 500


class ReplayBrowserDataError(RuntimeError):
    """Raised internally for fail-closed replay browser reads."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True, slots=True)
class ReplayBrowserFilter:
    job_id: str | None = None
    status: str | None = None
    limit: int = 50

    def __post_init__(self) -> None:
        if self.job_id is not None and not self.job_id.strip():
            raise ValueError("job_id_filter_must_be_nonempty")
        if self.status is not None and not self.status.strip():
            raise ValueError("status_filter_must_be_nonempty")
        if self.limit <= 0 or self.limit > _MAX_JOB_LIMIT:
            raise ValueError("limit_must_be_between_1_and_500")

    def as_dict(self) -> dict[str, object]:
        return {
            "job_id": self.job_id or "",
            "status": self.status or "",
            "limit": self.limit,
        }


@dataclass(frozen=True, slots=True)
class ReplayBrowserEvent:
    event_id: str
    job_id: str
    sequence: int
    event_type: str
    occurred_at: str
    reason_present: bool
    payload_hash: str
    content_hash: str
    content_hash_valid: bool

    def as_dict(self) -> dict[str, object]:
        return dict(sorted(asdict(self).items()))


@dataclass(frozen=True, slots=True)
class ReplayBrowserArtifact:
    artifact_id: str
    job_id: str
    artifact_type: str
    path_hash: str
    sha256: str
    size_bytes: int
    review_status: str
    quarantine_status: str
    local_only: bool
    safe_to_publish: bool
    content_hash: str
    content_hash_valid: bool

    def as_dict(self) -> dict[str, object]:
        return dict(sorted(asdict(self).items()))


@dataclass(frozen=True, slots=True)
class ReplayBrowserJobTrace:
    job_id: str
    job_type: str
    stored_status: str
    projected_status: str
    accepted: bool
    replay_classification: str
    failure_codes: tuple[str, ...]
    event_count: int
    artifact_count: int
    final_claim_allowed: bool
    job_content_hash_valid: bool
    event_chain_hash: str
    artifact_chain_hash: str
    projection_hash: str
    audit_hash: str
    events: tuple[ReplayBrowserEvent, ...]
    artifacts: tuple[ReplayBrowserArtifact, ...]

    def as_dict(self) -> dict[str, object]:
        return {
            "accepted": self.accepted,
            "artifact_chain_hash": self.artifact_chain_hash,
            "artifact_count": self.artifact_count,
            "artifacts": [artifact.as_dict() for artifact in self.artifacts],
            "audit_hash": self.audit_hash,
            "event_chain_hash": self.event_chain_hash,
            "event_count": self.event_count,
            "events": [event.as_dict() for event in self.events],
            "failure_codes": list(self.failure_codes),
            "final_claim_allowed": self.final_claim_allowed,
            "job_content_hash_valid": self.job_content_hash_valid,
            "job_id": self.job_id,
            "job_type": self.job_type,
            "projected_status": self.projected_status,
            "projection_hash": self.projection_hash,
            "replay_classification": self.replay_classification,
            "stored_status": self.stored_status,
        }

    def to_json(self) -> str:
        return json.dumps(self.as_dict(), sort_keys=True, separators=(",", ":"))


@dataclass(frozen=True, slots=True)
class ReplayBrowserSummary:
    summary_type: str
    root: str
    db_path: str
    filters: ReplayBrowserFilter
    accepted: bool
    failure_codes: tuple[str, ...]
    schema_hash: str
    journal_mode: str
    job_count: int
    event_count: int
    artifact_count: int
    returned_trace_count: int
    request_hash: str
    result_hash: str
    traces: tuple[ReplayBrowserJobTrace, ...]
    mutation_performed: bool = False
    deletion_performed: bool = False
    execution_performed: bool = False
    network_accessed: bool = False
    browser_launched: bool = False
    raw_secret_displayed: bool = False

    def as_dict(self) -> dict[str, object]:
        return {
            "accepted": self.accepted,
            "artifact_count": self.artifact_count,
            "browser_launched": self.browser_launched,
            "db_path": self.db_path,
            "deletion_performed": self.deletion_performed,
            "event_count": self.event_count,
            "execution_performed": self.execution_performed,
            "failure_codes": list(self.failure_codes),
            "filters": self.filters.as_dict(),
            "job_count": self.job_count,
            "journal_mode": self.journal_mode,
            "mutation_performed": self.mutation_performed,
            "network_accessed": self.network_accessed,
            "raw_secret_displayed": self.raw_secret_displayed,
            "request_hash": self.request_hash,
            "result_hash": self.result_hash,
            "returned_trace_count": self.returned_trace_count,
            "root": self.root,
            "schema_hash": self.schema_hash,
            "summary_type": self.summary_type,
            "traces": [trace.as_dict() for trace in self.traces],
        }

    def to_json(self) -> str:
        return json.dumps(self.as_dict(), sort_keys=True, separators=(",", ":"))


def browse_os_engine_replay(
    root: str | Path,
    filters: ReplayBrowserFilter | None = None,
    *,
    db_name: str = "os_engine.sqlite3",
) -> ReplayBrowserSummary:
    """Return deterministic read-only replay traces for the OS engine DB."""

    active_filters = filters or ReplayBrowserFilter()
    root_path, db_path = _resolve_db_path(root, db_name=db_name)
    request_hash = stable_content_hash(
        {
            "db_name": db_name,
            "filters": active_filters.as_dict(),
            "root": str(root_path),
            "summary_type": "os_engine_replay_browser_v1",
        }
    )

    if not db_path.exists():
        return _summary(
            root_path=root_path,
            db_path=db_path,
            filters=active_filters,
            accepted=False,
            failure_codes=("database_missing",),
            request_hash=request_hash,
        )

    try:
        with _readonly_connection(db_path) as connection:
            _require_schema(connection)
            schema_hash = _schema_hash(connection)
            journal_mode = _journal_mode(connection)
            counts = _table_counts(connection)
            traces = _read_traces(connection, filters=active_filters)
            failure_codes = _summary_failures(traces)
            if active_filters.job_id and not traces:
                failure_codes = tuple(sorted((*failure_codes, "job_not_found")))
            return _summary(
                root_path=root_path,
                db_path=db_path,
                filters=active_filters,
                accepted=not failure_codes,
                failure_codes=failure_codes,
                request_hash=request_hash,
                schema_hash=schema_hash,
                journal_mode=journal_mode,
                job_count=counts["jobs"],
                event_count=counts["job_events"],
                artifact_count=counts["artifacts"],
                traces=traces,
            )
    except ReplayBrowserDataError as exc:
        return _summary(
            root_path=root_path,
            db_path=db_path,
            filters=active_filters,
            accepted=False,
            failure_codes=(exc.code,),
            request_hash=request_hash,
        )
    except (sqlite3.Error, OSError):
        return _summary(
            root_path=root_path,
            db_path=db_path,
            filters=active_filters,
            accepted=False,
            failure_codes=("sqlite_read_failed",),
            request_hash=request_hash,
        )
    except (UnsafePayloadError, ValueError):
        return _summary(
            root_path=root_path,
            db_path=db_path,
            filters=active_filters,
            accepted=False,
            failure_codes=("unsafe_replay_payload",),
            request_hash=request_hash,
        )


def render_replay_browser_summary(summary: ReplayBrowserSummary) -> str:
    if not isinstance(summary, ReplayBrowserSummary):
        raise ValueError("summary_must_be_replay_browser_summary")
    return json.dumps(summary.as_dict(), indent=2, sort_keys=True) + "\n"


def _summary(
    *,
    root_path: Path,
    db_path: Path,
    filters: ReplayBrowserFilter,
    accepted: bool,
    failure_codes: tuple[str, ...],
    request_hash: str,
    schema_hash: str = "",
    journal_mode: str = "UNKNOWN",
    job_count: int = 0,
    event_count: int = 0,
    artifact_count: int = 0,
    traces: tuple[ReplayBrowserJobTrace, ...] = (),
) -> ReplayBrowserSummary:
    result_payload = {
        "accepted": accepted,
        "artifact_count": artifact_count,
        "db_path": str(db_path),
        "event_count": event_count,
        "failure_codes": list(failure_codes),
        "filters": filters.as_dict(),
        "job_count": job_count,
        "journal_mode": journal_mode,
        "request_hash": request_hash,
        "root": str(root_path),
        "schema_hash": schema_hash,
        "summary_type": "os_engine_replay_browser_v1",
        "traces": [trace.as_dict() for trace in traces],
    }
    result_hash = stable_content_hash(result_payload)
    return ReplayBrowserSummary(
        summary_type="os_engine_replay_browser_v1",
        root=str(root_path),
        db_path=str(db_path),
        filters=filters,
        accepted=accepted,
        failure_codes=tuple(sorted(set(failure_codes))),
        schema_hash=schema_hash,
        journal_mode=journal_mode,
        job_count=job_count,
        event_count=event_count,
        artifact_count=artifact_count,
        returned_trace_count=len(traces),
        request_hash=request_hash,
        result_hash=result_hash,
        traces=traces,
    )


def _resolve_db_path(root: str | Path, *, db_name: str) -> tuple[Path, Path]:
    if not db_name or "/" in db_name or "\\" in db_name:
        raise ReplayBrowserDataError("db_name_must_be_filename")
    raw_root = Path(root).expanduser()
    if raw_root.exists() and raw_root.is_symlink():
        raise ReplayBrowserDataError("runtime_root_symlink_rejected")
    if raw_root.exists() and not raw_root.is_dir():
        raise ReplayBrowserDataError("runtime_root_not_directory")
    root_path = raw_root.resolve(strict=False)
    db_path = (root_path / db_name).resolve(strict=False)
    if not db_path.is_relative_to(root_path):
        raise ReplayBrowserDataError("database_path_escapes_root")
    return root_path, db_path


@contextmanager
def _readonly_connection(db_path: Path) -> Iterator[sqlite3.Connection]:
    connection = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA query_only = ON")
        yield connection
    finally:
        connection.close()


def _require_schema(connection: sqlite3.Connection) -> None:
    tables = {
        str(row["name"])
        for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
    }
    if not _REQUIRED_TABLES.issubset(tables):
        raise ReplayBrowserDataError("required_tables_missing")


def _schema_hash(connection: sqlite3.Connection) -> str:
    row = connection.execute(
        "SELECT content_hash FROM schema_version ORDER BY version DESC LIMIT 1"
    ).fetchone()
    if row is None:
        raise ReplayBrowserDataError("schema_version_missing")
    value = str(row["content_hash"])
    if value != SCHEMA_CONTENT_HASH:
        raise ReplayBrowserDataError("schema_hash_mismatch")
    return value


def _journal_mode(connection: sqlite3.Connection) -> str:
    row = connection.execute("PRAGMA journal_mode").fetchone()
    return str(row[0]).upper() if row else "UNKNOWN"


def _table_counts(connection: sqlite3.Connection) -> dict[str, int]:
    return {
        table: int(connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
        for table in ("jobs", "job_events", "artifacts")
    }


def _read_traces(connection: sqlite3.Connection, *, filters: ReplayBrowserFilter) -> tuple[ReplayBrowserJobTrace, ...]:
    clauses: list[str] = []
    args: list[object] = []
    if filters.job_id:
        clauses.append("job_id = ?")
        args.append(filters.job_id)
    if filters.status:
        clauses.append("current_status = ?")
        args.append(filters.status.strip().lower())
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    rows = connection.execute(
        f"""
        SELECT *
        FROM jobs
        {where}
        ORDER BY created_at DESC, job_id ASC
        LIMIT ?
        """,
        (*args, filters.limit),
    ).fetchall()
    return tuple(_trace_from_job(connection, row) for row in rows)


def _trace_from_job(connection: sqlite3.Connection, row: sqlite3.Row) -> ReplayBrowserJobTrace:
    job_id = str(row["job_id"])
    failures: list[str] = []
    events: list[ReplayBrowserEvent] = []
    projection_inputs: list[dict[str, object]] = []
    for event_row in connection.execute(
        "SELECT * FROM job_events WHERE job_id = ? ORDER BY sequence",
        (job_id,),
    ).fetchall():
        event, projection_input = _event_from_row(event_row)
        events.append(event)
        projection_inputs.append(projection_input)
        if not event.content_hash_valid:
            failures.append("event_content_hash_mismatch")

    artifacts = tuple(
        _artifact_from_row(artifact_row)
        for artifact_row in connection.execute(
            "SELECT * FROM artifacts WHERE job_id = ? ORDER BY artifact_id",
            (job_id,),
        ).fetchall()
    )
    if any(not artifact.content_hash_valid for artifact in artifacts):
        failures.append("artifact_content_hash_mismatch")

    job_content_hash_valid = _job_content_hash_valid(row)
    if not job_content_hash_valid:
        failures.append("job_content_hash_mismatch")
    if not events:
        failures.append("missing_event_history")

    projection = _project_trace(projection_inputs)
    if projection is None:
        projected_status = ""
        projection_hash = ""
        final_claim_allowed = False
        failures.append("projection_failed")
    else:
        projected_status = projection.current_status
        projection_hash = projection.content_hash
        final_claim_allowed = projection.final_claim_allowed
        if str(row["current_status"]) != projection.current_status:
            failures.append("job_status_projection_mismatch")

    event_chain_hash = stable_content_hash(
        [
            {
                "content_hash": event.content_hash,
                "content_hash_valid": event.content_hash_valid,
                "event_id": event.event_id,
                "event_type": event.event_type,
                "payload_hash": event.payload_hash,
                "sequence": event.sequence,
            }
            for event in events
        ]
    )
    artifact_chain_hash = stable_content_hash(
        [
            {
                "artifact_id": artifact.artifact_id,
                "content_hash": artifact.content_hash,
                "content_hash_valid": artifact.content_hash_valid,
                "path_hash": artifact.path_hash,
                "sha256": artifact.sha256,
            }
            for artifact in artifacts
        ]
    )
    failure_codes = tuple(sorted(set(failures)))
    accepted = not failure_codes
    replay_classification = "exact_event_projection" if accepted else "diagnostic_rejected"
    audit_payload = {
        "accepted": accepted,
        "artifact_chain_hash": artifact_chain_hash,
        "event_chain_hash": event_chain_hash,
        "failure_codes": list(failure_codes),
        "job_id": job_id,
        "projection_hash": projection_hash,
        "replay_classification": replay_classification,
    }
    return ReplayBrowserJobTrace(
        job_id=job_id,
        job_type=str(row["job_type"]),
        stored_status=str(row["current_status"]),
        projected_status=projected_status,
        accepted=accepted,
        replay_classification=replay_classification,
        failure_codes=failure_codes,
        event_count=len(events),
        artifact_count=len(artifacts),
        final_claim_allowed=final_claim_allowed,
        job_content_hash_valid=job_content_hash_valid,
        event_chain_hash=event_chain_hash,
        artifact_chain_hash=artifact_chain_hash,
        projection_hash=projection_hash,
        audit_hash=stable_content_hash(audit_payload),
        events=tuple(events),
        artifacts=artifacts,
    )


def _event_from_row(row: sqlite3.Row) -> tuple[ReplayBrowserEvent, dict[str, object]]:
    try:
        payload = json.loads(str(row["payload_json"]))
    except json.JSONDecodeError as exc:
        raise ReplayBrowserDataError("malformed_event_payload") from exc
    if not isinstance(payload, dict):
        raise ReplayBrowserDataError("event_payload_must_be_object")
    reason = str(row["reason"]) if row["reason"] is not None else ""
    validate_no_secret_like(payload)
    if reason:
        validate_no_secret_like({"reason": reason})
    event_hash = stable_content_hash(
        {
            "event_type": str(row["event_type"]),
            "job_id": str(row["job_id"]),
            "payload": payload,
            "reason": reason,
            "sequence": int(row["sequence"]),
        }
    )
    stored_hash = str(row["content_hash"])
    event = ReplayBrowserEvent(
        event_id=str(row["event_id"]),
        job_id=str(row["job_id"]),
        sequence=int(row["sequence"]),
        event_type=str(row["event_type"]),
        occurred_at=str(row["occurred_at"]),
        reason_present=bool(reason),
        payload_hash=stable_content_hash(payload),
        content_hash=stored_hash,
        content_hash_valid=stored_hash == event_hash,
    )
    return event, {"job_id": event.job_id, "sequence": event.sequence, "event_type": event.event_type, "payload": payload, "reason": reason or None}


def _artifact_from_row(row: sqlite3.Row) -> ReplayBrowserArtifact:
    local_path = str(row["local_path"])
    validate_no_secret_like({"local_path": local_path})
    stored_hash = str(row["content_hash"])
    expected_hash = stable_content_hash(
        {
            "artifact_id": str(row["artifact_id"]),
            "artifact_type": str(row["artifact_type"]),
            "job_id": str(row["job_id"]),
            "local_only": bool(row["local_only"]),
            "local_path": local_path,
            "quarantine_reason": str(row["quarantine_reason"]) if row["quarantine_reason"] is not None else "",
            "quarantine_status": str(row["quarantine_status"]),
            "review_status": str(row["review_status"]),
            "safe_to_publish": bool(row["safe_to_publish"]),
            "sha256": str(row["sha256"]),
            "size_bytes": int(row["size_bytes"]),
        }
    )
    return ReplayBrowserArtifact(
        artifact_id=str(row["artifact_id"]),
        job_id=str(row["job_id"]),
        artifact_type=str(row["artifact_type"]),
        path_hash=stable_content_hash({"local_path": local_path}),
        sha256=str(row["sha256"]),
        size_bytes=int(row["size_bytes"]),
        review_status=str(row["review_status"]),
        quarantine_status=str(row["quarantine_status"]),
        local_only=bool(row["local_only"]),
        safe_to_publish=bool(row["safe_to_publish"]),
        content_hash=stored_hash,
        content_hash_valid=stored_hash == expected_hash,
    )


def _job_content_hash_valid(row: sqlite3.Row) -> bool:
    try:
        input_manifest = json.loads(str(row["input_manifest_json"]))
    except json.JSONDecodeError as exc:
        raise ReplayBrowserDataError("malformed_job_manifest") from exc
    if not isinstance(input_manifest, dict):
        raise ReplayBrowserDataError("job_manifest_must_be_object")
    validate_no_secret_like(input_manifest)
    expected = stable_content_hash(
        {
            "created_at": str(row["created_at"]),
            "dry_run": bool(row["dry_run"]),
            "human_review_required": bool(row["human_review_required"]),
            "input_manifest": input_manifest,
            "job_id": str(row["job_id"]),
            "job_type": str(row["job_type"]),
            "local_only": bool(row["local_only"]),
            "output_dir": str(row["output_dir"]),
            "source_git_commit": str(row["source_git_commit"]),
            "status": str(row["current_status"]),
        }
    )
    return str(row["content_hash"]) == expected


def _project_trace(events: list[dict[str, object]]) -> ProjectedJobState | None:
    try:
        return project_job_state(events)
    except JobProjectionError:
        return None


def _summary_failures(traces: tuple[ReplayBrowserJobTrace, ...]) -> tuple[str, ...]:
    failures: set[str] = set()
    for trace in traces:
        failures.update(trace.failure_codes)
    return tuple(sorted(failures))
