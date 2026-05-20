"""Append-only SQLite job event log for the OS engine v3 core."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any

from kernel.os_engine.database import OSDatabase, canonical_json, stable_content_hash, utc_now_iso, validate_no_secret_like
from kernel.os_engine.event_types import ALLOWED_EVENT_TYPES, REASON_REQUIRED_EVENT_TYPES, JobEventType
from kernel.os_engine.job_projection import JobProjectionError, project_job_state


class EventLogError(RuntimeError):
    """Base exception for event log append and replay failures."""


class UnknownEventTypeError(EventLogError):
    """Raised when a caller attempts to append an unknown event."""


class EventPayloadError(EventLogError):
    """Raised when an event payload fails closed."""


@dataclass(frozen=True, slots=True)
class JobEventRecord:
    event_id: str
    job_id: str
    sequence: int
    event_type: str
    occurred_at: str
    payload: dict[str, Any]
    reason: str | None
    content_hash: str

    def to_dict(self) -> dict[str, Any]:
        return dict(sorted(asdict(self).items()))

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))


class EventLog:
    """Durable append-only job events with deterministic replay validation."""

    def __init__(self, database: OSDatabase) -> None:
        self.database = database
        self.database.initialize()

    def append_event(
        self,
        *,
        job_id: str,
        event_type: str | JobEventType,
        payload: dict[str, Any] | None = None,
        reason: str | None = None,
    ) -> JobEventRecord:
        event_type_value = _normalize_event_type(event_type)
        if not job_id or not isinstance(job_id, str):
            raise EventPayloadError("job_id is required")
        payload = _validate_payload({} if payload is None else payload)
        if event_type_value in REASON_REQUIRED_EVENT_TYPES and not reason:
            raise EventPayloadError(f"{event_type_value} requires reason")
        if reason is not None:
            validate_no_secret_like({"reason": reason})
        if event_type_value == JobEventType.JOB_CREATED.value:
            self._validate_job_created_payload(payload)
        if event_type_value == JobEventType.JOB_SUCCEEDED.value and not _success_has_evidence(payload):
            raise EventPayloadError("JobSucceeded requires artifact or completion evidence")

        self.database.initialize()
        with self.database.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            rows = connection.execute(
                "SELECT * FROM job_events WHERE job_id = ? ORDER BY sequence",
                (job_id,),
            ).fetchall()
            existing = [_record_from_row(row) for row in rows]
            if event_type_value == JobEventType.JOB_CREATED.value and existing:
                raise EventLogError(f"job already exists in event log: {job_id}")
            if event_type_value != JobEventType.JOB_CREATED.value and not existing:
                raise EventLogError(f"cannot append {event_type_value} without JobCreated")
            sequence = (existing[-1].sequence + 1) if existing else 1
            occurred_at = utc_now_iso()
            event_hash = _event_content_hash(
                job_id=job_id,
                sequence=sequence,
                event_type=event_type_value,
                payload=payload,
                reason=reason,
            )
            event_id = f"evt_{event_hash[:32]}"
            candidate = JobEventRecord(
                event_id=event_id,
                job_id=job_id,
                sequence=sequence,
                event_type=event_type_value,
                occurred_at=occurred_at,
                payload=payload,
                reason=reason,
                content_hash=event_hash,
            )
            try:
                projected = project_job_state([*existing, candidate])
            except JobProjectionError as exc:
                raise EventLogError(str(exc)) from exc

            if event_type_value == JobEventType.JOB_CREATED.value:
                self._insert_job(connection, job_id=job_id, payload=payload, status=projected.current_status)
            connection.execute(
                """
                INSERT INTO job_events(
                    event_id,
                    job_id,
                    sequence,
                    event_type,
                    occurred_at,
                    payload_json,
                    reason,
                    content_hash
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    candidate.event_id,
                    candidate.job_id,
                    candidate.sequence,
                    candidate.event_type,
                    candidate.occurred_at,
                    canonical_json(candidate.payload),
                    candidate.reason,
                    candidate.content_hash,
                ),
            )
            self._update_job_projection(connection, job_id=job_id, status=projected.current_status)
            return candidate

    def get_events(self, job_id: str) -> list[JobEventRecord]:
        self.database.initialize()
        with self.database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM job_events WHERE job_id = ? ORDER BY sequence",
                (job_id,),
            ).fetchall()
        return [_record_from_row(row) for row in rows]

    def get_all_events(self) -> list[JobEventRecord]:
        self.database.initialize()
        with self.database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM job_events ORDER BY job_id, sequence",
            ).fetchall()
        return [_record_from_row(row) for row in rows]

    def _insert_job(self, connection: Any, *, job_id: str, payload: dict[str, Any], status: str) -> None:
        input_manifest = payload.get("input_manifest", payload)
        if not isinstance(input_manifest, dict):
            raise EventPayloadError("input_manifest must be a JSON object")
        output_dir = str(payload.get("output_dir", ""))
        row_hash = stable_content_hash(
            {
                "created_at": payload.get("created_at", ""),
                "dry_run": bool(payload.get("dry_run", False)),
                "human_review_required": bool(payload.get("human_review_required", False)),
                "input_manifest": input_manifest,
                "job_id": job_id,
                "job_type": str(payload["job_type"]),
                "local_only": bool(payload.get("local_only", True)),
                "output_dir": output_dir,
                "source_git_commit": str(payload.get("source_git_commit", "")),
                "status": status,
            }
        )
        connection.execute(
            """
            INSERT INTO jobs(
                job_id,
                job_type,
                created_at,
                current_status,
                input_manifest_json,
                output_dir,
                human_review_required,
                dry_run,
                source_git_commit,
                local_only,
                content_hash
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                job_id,
                str(payload["job_type"]),
                str(payload.get("created_at") or utc_now_iso()),
                status,
                canonical_json(input_manifest),
                output_dir,
                int(bool(payload.get("human_review_required", False))),
                int(bool(payload.get("dry_run", False))),
                str(payload.get("source_git_commit", "")),
                int(bool(payload.get("local_only", True))),
                row_hash,
            ),
        )

    def _update_job_projection(self, connection: Any, *, job_id: str, status: str) -> None:
        row = connection.execute(
            "SELECT * FROM jobs WHERE job_id = ?",
            (job_id,),
        ).fetchone()
        if row is None:
            raise EventLogError(f"job row missing for projection update: {job_id}")
        input_manifest = json.loads(str(row["input_manifest_json"]))
        row_hash = stable_content_hash(
            {
                "created_at": str(row["created_at"]),
                "dry_run": bool(row["dry_run"]),
                "human_review_required": bool(row["human_review_required"]),
                "input_manifest": input_manifest,
                "job_id": job_id,
                "job_type": str(row["job_type"]),
                "local_only": bool(row["local_only"]),
                "output_dir": str(row["output_dir"]),
                "source_git_commit": str(row["source_git_commit"]),
                "status": status,
            }
        )
        connection.execute(
            "UPDATE jobs SET current_status = ?, content_hash = ? WHERE job_id = ?",
            (status, row_hash, job_id),
        )

    @staticmethod
    def _validate_job_created_payload(payload: dict[str, Any]) -> None:
        job_type = payload.get("job_type")
        if not isinstance(job_type, str) or not job_type.strip():
            raise EventPayloadError("JobCreated requires job_type")
        input_manifest = payload.get("input_manifest", payload)
        if not isinstance(input_manifest, dict):
            raise EventPayloadError("JobCreated input_manifest must be a JSON object")


def _normalize_event_type(event_type: str | JobEventType) -> str:
    value = event_type.value if isinstance(event_type, JobEventType) else str(event_type)
    if value not in ALLOWED_EVENT_TYPES:
        raise UnknownEventTypeError(f"unknown event type: {value}")
    return value


def _validate_payload(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise EventPayloadError("event payload must be a JSON object")
    validate_no_secret_like(payload)
    canonical_json(payload)
    return dict(payload)


def _success_has_evidence(payload: dict[str, Any]) -> bool:
    return bool(
        payload.get("artifact_id")
        or payload.get("artifact_ids")
        or payload.get("completion_evidence")
        or payload.get("completion_record")
    )


def _event_content_hash(
    *,
    job_id: str,
    sequence: int,
    event_type: str,
    payload: dict[str, Any],
    reason: str | None,
) -> str:
    return stable_content_hash(
        {
            "event_type": event_type,
            "job_id": job_id,
            "payload": payload,
            "reason": reason or "",
            "sequence": sequence,
        }
    )


def _record_from_row(row: Any) -> JobEventRecord:
    payload = json.loads(str(row["payload_json"]))
    return JobEventRecord(
        event_id=str(row["event_id"]),
        job_id=str(row["job_id"]),
        sequence=int(row["sequence"]),
        event_type=str(row["event_type"]),
        occurred_at=str(row["occurred_at"]),
        payload=payload,
        reason=str(row["reason"]) if row["reason"] is not None else None,
        content_hash=str(row["content_hash"]),
    )
