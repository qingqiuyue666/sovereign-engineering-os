"""Read-only artifact ledger visibility helpers.

The viewer reads local JSON artifact records and emits redacted summaries. It
does not mutate, delete, execute, launch browsers, access networks, or reveal
raw secret-like fields.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence
import json

__all__ = [
    "ArtifactLedgerFilter",
    "ArtifactLedgerEntry",
    "ArtifactLedgerSummary",
    "list_artifact_ledger",
    "render_artifact_ledger_summary",
]


_REDACTED = "[REDACTED]"
_SECRET_KEY_PARTS = (
    "api_key",
    "credential",
    "password",
    "raw_prompt",
    "raw_response",
    "secret",
    "token",
)
_SUPPORTED_SUFFIX = ".json"
_MAX_PREVIEW_KEYS = 24


@dataclass(frozen=True)
class ArtifactLedgerFilter:
    task_id: str | None = None
    run_id: str | None = None
    milestone: str | None = None
    artifact_kind: str | None = None


@dataclass(frozen=True)
class ArtifactLedgerEntry:
    relative_path: str
    artifact_kind: str
    task_id: str
    run_id: str
    milestone: str
    receipt_id: str
    failure_id: str
    replay_id: str
    size_bytes: int
    redacted_preview: dict[str, object]

    def as_dict(self) -> dict[str, object]:
        return {
            "relative_path": self.relative_path,
            "artifact_kind": self.artifact_kind,
            "task_id": self.task_id,
            "run_id": self.run_id,
            "milestone": self.milestone,
            "receipt_id": self.receipt_id,
            "failure_id": self.failure_id,
            "replay_id": self.replay_id,
            "size_bytes": self.size_bytes,
            "redacted_preview": self.redacted_preview,
        }


@dataclass(frozen=True)
class ArtifactLedgerSummary:
    root: str
    filters: ArtifactLedgerFilter
    entries: tuple[ArtifactLedgerEntry, ...]
    total_entries: int
    receipt_entries: int
    failure_bundle_entries: int
    replay_manifest_entries: int
    mutation_performed: bool = False
    deletion_performed: bool = False
    raw_secret_displayed: bool = False
    execution_performed: bool = False
    network_accessed: bool = False

    def as_dict(self) -> dict[str, object]:
        return {
            "summary_type": "artifact_ledger_viewer_v1",
            "root": self.root,
            "filters": {
                "task_id": self.filters.task_id or "",
                "run_id": self.filters.run_id or "",
                "milestone": self.filters.milestone or "",
                "artifact_kind": self.filters.artifact_kind or "",
            },
            "total_entries": self.total_entries,
            "receipt_entries": self.receipt_entries,
            "failure_bundle_entries": self.failure_bundle_entries,
            "replay_manifest_entries": self.replay_manifest_entries,
            "entries": [entry.as_dict() for entry in self.entries],
            "mutation_performed": self.mutation_performed,
            "deletion_performed": self.deletion_performed,
            "raw_secret_displayed": self.raw_secret_displayed,
            "execution_performed": self.execution_performed,
            "network_accessed": self.network_accessed,
        }


def list_artifact_ledger(
    root: Path | str,
    filters: ArtifactLedgerFilter | None = None,
) -> ArtifactLedgerSummary:
    """Read local JSON artifact records and return redacted summary metadata."""

    root_path = Path(root)
    if not root_path.exists():
        raise ValueError("artifact_ledger_root_missing")
    if not root_path.is_dir():
        raise ValueError("artifact_ledger_root_not_directory")

    active_filters = filters or ArtifactLedgerFilter()
    entries = tuple(
        entry
        for entry in _iter_entries(root_path)
        if _matches_filters(entry, active_filters)
    )
    return ArtifactLedgerSummary(
        root=root_path.as_posix(),
        filters=active_filters,
        entries=entries,
        total_entries=len(entries),
        receipt_entries=sum(1 for entry in entries if entry.artifact_kind == "receipt"),
        failure_bundle_entries=sum(
            1 for entry in entries if entry.artifact_kind == "failure_bundle"
        ),
        replay_manifest_entries=sum(
            1 for entry in entries if entry.artifact_kind == "replay_manifest"
        ),
    )


def render_artifact_ledger_summary(summary: ArtifactLedgerSummary) -> str:
    if not isinstance(summary, ArtifactLedgerSummary):
        raise ValueError("summary_must_be_artifact_ledger_summary")
    return json.dumps(summary.as_dict(), indent=2, sort_keys=True) + "\n"


def _iter_entries(root_path: Path) -> tuple[ArtifactLedgerEntry, ...]:
    entries: list[ArtifactLedgerEntry] = []
    for path in sorted(root_path.rglob("*"), key=lambda candidate: candidate.as_posix()):
        if not path.is_file() or path.suffix != _SUPPORTED_SUFFIX:
            continue
        payload = _read_json_object(path)
        if payload is None:
            continue
        entries.append(_entry_from_payload(root_path, path, payload))
    return tuple(entries)


def _read_json_object(path: Path) -> dict[str, object] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict):
        return None
    return payload


def _entry_from_payload(
    root_path: Path,
    path: Path,
    payload: Mapping[str, object],
) -> ArtifactLedgerEntry:
    relative_path = path.relative_to(root_path).as_posix()
    return ArtifactLedgerEntry(
        relative_path=relative_path,
        artifact_kind=_artifact_kind(relative_path, payload),
        task_id=_field(payload, ("task_id", "task")),
        run_id=_field(payload, ("run_id", "run")),
        milestone=_field(payload, ("milestone", "milestone_id", "milestone_name")),
        receipt_id=_field(payload, ("receipt_id", "record_id")),
        failure_id=_field(payload, ("failure_id", "failure_bundle_id")),
        replay_id=_field(payload, ("replay_id", "replay_manifest_id")),
        size_bytes=path.stat().st_size,
        redacted_preview=_redacted_preview(payload),
    )


def _artifact_kind(relative_path: str, payload: Mapping[str, object]) -> str:
    lowered_path = relative_path.lower()
    type_text = " ".join(
        str(payload.get(key, ""))
        for key in ("artifact_kind", "artifact_type", "receipt_type", "manifest_type")
    ).lower()
    combined = f"{lowered_path} {type_text}"
    if "failure_bundle" in combined or "failure-bundle" in combined:
        return "failure_bundle"
    if "replay_manifest" in combined or "replay-manifest" in combined:
        return "replay_manifest"
    if "receipt" in combined:
        return "receipt"
    return "artifact"


def _field(payload: Mapping[str, object], keys: Sequence[str]) -> str:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str):
            return value
    metadata = payload.get("metadata")
    if isinstance(metadata, dict):
        for key in keys:
            value = metadata.get(key)
            if isinstance(value, str):
                return value
    return ""


def _redacted_preview(payload: Mapping[str, object]) -> dict[str, object]:
    preview: dict[str, object] = {}
    for key in sorted(payload)[:_MAX_PREVIEW_KEYS]:
        preview[key] = _redact_value(key, payload[key])
    return preview


def _redact_value(key: str, value: object) -> object:
    if _is_secret_key(key):
        return _REDACTED
    if isinstance(value, dict):
        return {
            str(child_key): _redact_value(str(child_key), child_value)
            for child_key, child_value in sorted(value.items())
        }
    if isinstance(value, list):
        return [_redact_value(key, item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def _is_secret_key(key: str) -> bool:
    lowered = key.lower()
    return any(part in lowered for part in _SECRET_KEY_PARTS)


def _matches_filters(entry: ArtifactLedgerEntry, filters: ArtifactLedgerFilter) -> bool:
    return (
        (filters.task_id is None or entry.task_id == filters.task_id)
        and (filters.run_id is None or entry.run_id == filters.run_id)
        and (filters.milestone is None or entry.milestone == filters.milestone)
        and (
            filters.artifact_kind is None
            or entry.artifact_kind == filters.artifact_kind
        )
    )
