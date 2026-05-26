"""Real WAL storage contract V1.

This module defines the deterministic record shape and replay validation for
future local append-only WAL storage. It is deliberately contract-only: no file
mutation, no SQLite coupling, no subprocess, no CLI, and no broad runtime import.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import re
from typing import Any, Mapping, Sequence

__all__ = [
    "REAL_WAL_STORAGE_CONTRACT_VERSION",
    "REAL_WAL_STORAGE_REPLAY_POLICY_VERSION",
    "REAL_WAL_STORAGE_RECORD_TYPES",
    "REAL_WAL_FORBIDDEN_FIELD_NAMES",
    "REAL_WAL_EXECUTION_MATERIAL_FIELD_NAMES",
    "RealWalStorageRecord",
    "RealWalStorageReplayResult",
    "compute_real_wal_storage_record_hash",
    "compute_real_wal_storage_replay_result_hash",
    "parse_real_wal_storage_record_line",
    "real_wal_storage_record_from_mapping",
    "replay_real_wal_storage_records",
    "serialize_real_wal_storage_record_line",
    "validate_real_wal_storage_record",
]

REAL_WAL_STORAGE_CONTRACT_VERSION = "real_wal_storage_contract_v1"
REAL_WAL_STORAGE_REPLAY_POLICY_VERSION = "real_wal_storage_replay_policy_v1"

REAL_WAL_STORAGE_RECORD_TYPES = frozenset(
    {
        "MINIMAL_CONTROLLED_EXECUTION",
        "QUEUE_EVENT",
        "ARTIFACT_EVENT",
        "SNAPSHOT_EVENT",
        "APPROVAL_EVENT",
        "FAILURE_BUNDLE_EVENT",
        "WORKER_REGISTRY_EVENT",
        "WATCHDOG_EVENT",
        "OPERATOR_CONSOLE_EVENT",
        "REPLAY_EVENT",
        "INSTALL_HEALTH_EVENT",
        "AI_ROUTER_EVENT",
        "DCC_MEDIA_EVENT",
        "SYSTEM_ACCEPTANCE_EVENT",
    }
)

REAL_WAL_FORBIDDEN_FIELD_NAMES = frozenset(
    {
        "stdout",
        "stderr",
        "raw_stdout",
        "raw_stderr",
        "stdout_text",
        "stderr_text",
        "raw_output",
        "raw_log",
        "command_line",
        "secret",
        "credential",
        "token",
        "password",
        "private_key",
        "api_key",
        "env",
        "environment",
    }
)

REAL_WAL_EXECUTION_MATERIAL_FIELD_NAMES = frozenset(
    {
        "argv",
        "args",
        "cwd",
        "workdir",
        "path",
        "executable",
        "executable_path",
        "timeout",
        "shell",
        "command",
    }
)

_RECORD_FIELDS = frozenset(
    {
        "wal_record_id",
        "wal_storage_contract_version",
        "sequence",
        "previous_hash",
        "record_type",
        "task_id",
        "run_id",
        "payload_hash",
        "digest_bindings",
        "created_at",
        "record_hash",
    }
)
_SHA256_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")
_BINDING_NAME_PATTERN = re.compile(r"^[a-z][a-z0-9_]{0,95}$")
_SECRET_KEY_PATTERN = re.compile(
    r"(?i)(api[_-]?key|auth|authorization|credential|password|private[_-]?key|secret|token)"
)
_UNSET = object()


@dataclass(frozen=True)
class RealWalStorageRecord:
    wal_record_id: str
    wal_storage_contract_version: str
    sequence: int
    previous_hash: str | None
    record_type: str
    task_id: str
    run_id: str
    payload_hash: str
    digest_bindings: tuple[tuple[str, str], ...]
    created_at: str
    record_hash: str = ""

    def __post_init__(self) -> None:
        _require_nonempty_string(self.wal_record_id, "wal_record_id")
        if self.wal_storage_contract_version != REAL_WAL_STORAGE_CONTRACT_VERSION:
            raise ValueError("wal_storage_contract_version_invalid")
        if not isinstance(self.sequence, int) or isinstance(self.sequence, bool):
            raise ValueError("sequence_must_be_int")
        if self.sequence <= 0:
            raise ValueError("sequence_must_be_positive")
        if self.previous_hash is not None:
            _require_sha256(self.previous_hash, "previous_hash")
        if self.record_type not in REAL_WAL_STORAGE_RECORD_TYPES:
            raise ValueError("record_type_invalid")
        _require_nonempty_string(self.task_id, "task_id")
        _require_nonempty_string(self.run_id, "run_id")
        _require_sha256(self.payload_hash, "payload_hash")
        object.__setattr__(
            self,
            "digest_bindings",
            _normalize_digest_bindings(self.digest_bindings),
        )
        _require_nonempty_string(self.created_at, "created_at")
        if self.record_hash:
            _require_sha256(self.record_hash, "record_hash")
        expected = compute_real_wal_storage_record_hash(self)
        if self.record_hash and self.record_hash != expected:
            raise ValueError("record_hash_mismatch")
        object.__setattr__(self, "record_hash", expected)

    def as_dict(self) -> dict[str, object]:
        return _json_ready(asdict(self))


@dataclass(frozen=True)
class RealWalStorageReplayResult:
    replay_policy_version: str
    accepted: bool
    rejection_reasons: tuple[str, ...]
    record_count: int
    first_sequence: int | None
    last_sequence: int | None
    last_record_hash: str | None
    replay_result_hash: str = ""

    def __post_init__(self) -> None:
        if self.replay_policy_version != REAL_WAL_STORAGE_REPLAY_POLICY_VERSION:
            raise ValueError("replay_policy_version_invalid")
        if not isinstance(self.accepted, bool):
            raise ValueError("accepted_must_be_bool")
        object.__setattr__(
            self,
            "rejection_reasons",
            _normalize_rejection_reasons(self.rejection_reasons),
        )
        if self.accepted and self.rejection_reasons:
            raise ValueError("accepted_replay_cannot_have_rejections")
        if not self.accepted and not self.rejection_reasons:
            raise ValueError("rejected_replay_requires_rejections")
        if self.record_count < 0:
            raise ValueError("record_count_must_be_nonnegative")
        for field_name in ("first_sequence", "last_sequence"):
            value = getattr(self, field_name)
            if value is not None and (not isinstance(value, int) or value <= 0):
                raise ValueError(field_name + "_must_be_positive_int")
        if self.last_record_hash is not None:
            _require_sha256(self.last_record_hash, "last_record_hash")
        if self.replay_result_hash:
            _require_sha256(self.replay_result_hash, "replay_result_hash")
        expected = compute_real_wal_storage_replay_result_hash(self)
        if self.replay_result_hash and self.replay_result_hash != expected:
            raise ValueError("replay_result_hash_mismatch")
        object.__setattr__(self, "replay_result_hash", expected)

    def as_dict(self) -> dict[str, object]:
        return _json_ready(asdict(self))


def real_wal_storage_record_from_mapping(payload: Mapping[str, object]) -> RealWalStorageRecord:
    _validate_mapping_keys(payload)
    try:
        return RealWalStorageRecord(
            wal_record_id=str(payload["wal_record_id"]),
            wal_storage_contract_version=str(payload["wal_storage_contract_version"]),
            sequence=payload["sequence"],  # type: ignore[arg-type]
            previous_hash=(
                payload["previous_hash"]
                if payload["previous_hash"] is None
                else str(payload["previous_hash"])
            ),
            record_type=str(payload["record_type"]),
            task_id=str(payload["task_id"]),
            run_id=str(payload["run_id"]),
            payload_hash=str(payload["payload_hash"]),
            digest_bindings=payload["digest_bindings"],  # type: ignore[arg-type]
            created_at=str(payload["created_at"]),
            record_hash=str(payload.get("record_hash", "")),
        )
    except KeyError as exc:
        raise ValueError(f"{exc.args[0]}_required") from exc


def validate_real_wal_storage_record(
    record: RealWalStorageRecord,
    *,
    expected_sequence: int | None = None,
    expected_previous_hash: str | None | object = _UNSET,
) -> None:
    if not isinstance(record, RealWalStorageRecord):
        raise ValueError("record_must_be_real_wal_storage_record")
    if expected_sequence is not None and record.sequence != expected_sequence:
        raise ValueError("sequence_gap_detected")
    if expected_previous_hash is not _UNSET and record.previous_hash != expected_previous_hash:
        raise ValueError("previous_hash_mismatch")
    if record.record_hash != compute_real_wal_storage_record_hash(record):
        raise ValueError("record_hash_mismatch")


def replay_real_wal_storage_records(
    records: Sequence[RealWalStorageRecord],
) -> RealWalStorageReplayResult:
    failures: list[str] = []
    previous_hash: str | None = None
    expected_sequence = 1
    first_sequence: int | None = None
    last_sequence: int | None = None
    last_record_hash: str | None = None

    for record in records:
        if first_sequence is None:
            first_sequence = record.sequence
        last_sequence = record.sequence
        try:
            validate_real_wal_storage_record(
                record,
                expected_sequence=expected_sequence,
                expected_previous_hash=previous_hash,
            )
        except ValueError as exc:
            failures.append(str(exc))
        previous_hash = record.record_hash
        last_record_hash = record.record_hash
        expected_sequence += 1

    return RealWalStorageReplayResult(
        replay_policy_version=REAL_WAL_STORAGE_REPLAY_POLICY_VERSION,
        accepted=not failures,
        rejection_reasons=tuple(_dedupe(failures)),
        record_count=len(records),
        first_sequence=first_sequence,
        last_sequence=last_sequence,
        last_record_hash=last_record_hash,
    )


def serialize_real_wal_storage_record_line(record: RealWalStorageRecord) -> str:
    validate_real_wal_storage_record(record)
    return _canonical_json(record.as_dict()) + "\n"


def parse_real_wal_storage_record_line(line: str) -> RealWalStorageRecord:
    if not isinstance(line, str):
        raise ValueError("wal_record_line_must_be_string")
    if not line.endswith("\n"):
        raise ValueError("partial_record_line")
    try:
        payload = json.loads(line)
    except json.JSONDecodeError as exc:
        raise ValueError("malformed_json") from exc
    if not isinstance(payload, Mapping):
        raise ValueError("record_json_must_be_object")
    return real_wal_storage_record_from_mapping(payload)


def compute_real_wal_storage_record_hash(record: RealWalStorageRecord | Mapping[str, object]) -> str:
    data = _record_dict(record)
    data.pop("record_hash", None)
    data.pop("created_at", None)
    return _sha256(_canonical_json(data))


def compute_real_wal_storage_replay_result_hash(
    result: RealWalStorageReplayResult | Mapping[str, object],
) -> str:
    data = _result_dict(result)
    data.pop("replay_result_hash", None)
    return _sha256(_canonical_json(data))


def _record_dict(record: RealWalStorageRecord | Mapping[str, object]) -> dict[str, object]:
    if isinstance(record, RealWalStorageRecord):
        return record.as_dict()
    return _json_ready(dict(record))


def _result_dict(result: RealWalStorageReplayResult | Mapping[str, object]) -> dict[str, object]:
    if isinstance(result, RealWalStorageReplayResult):
        return result.as_dict()
    return _json_ready(dict(result))


def _validate_mapping_keys(payload: Mapping[str, object]) -> None:
    keys = {str(key) for key in payload}
    forbidden = sorted(
        key
        for key in keys
        if key in REAL_WAL_FORBIDDEN_FIELD_NAMES
        or key in REAL_WAL_EXECUTION_MATERIAL_FIELD_NAMES
        or _SECRET_KEY_PATTERN.search(key)
    )
    if forbidden:
        raise ValueError("wal_record_field_forbidden:" + ",".join(forbidden))
    extra = sorted(keys - _RECORD_FIELDS)
    if extra:
        raise ValueError("wal_record_field_unknown:" + ",".join(extra))


def _normalize_digest_bindings(value: object) -> tuple[tuple[str, str], ...]:
    if isinstance(value, Mapping):
        items = tuple((str(key), str(item)) for key, item in value.items())
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        items = tuple(_binding_pair(item) for item in value)
    else:
        raise ValueError("digest_bindings_must_be_mapping_or_sequence")
    normalized: list[tuple[str, str]] = []
    seen: set[str] = set()
    for name, digest in items:
        if not _BINDING_NAME_PATTERN.fullmatch(name):
            raise ValueError("digest_binding_name_invalid")
        if name in REAL_WAL_FORBIDDEN_FIELD_NAMES or name in REAL_WAL_EXECUTION_MATERIAL_FIELD_NAMES:
            raise ValueError("digest_binding_name_forbidden")
        if _SECRET_KEY_PATTERN.search(name):
            raise ValueError("digest_binding_name_secret_like")
        if name in seen:
            raise ValueError("digest_binding_name_duplicate")
        _require_sha256(digest, "digest_binding:" + name)
        seen.add(name)
        normalized.append((name, digest))
    return tuple(sorted(normalized))


def _binding_pair(item: object) -> tuple[str, str]:
    if not isinstance(item, Sequence) or isinstance(item, (str, bytes)) or len(item) != 2:
        raise ValueError("digest_binding_must_be_pair")
    return str(item[0]), str(item[1])


def _normalize_rejection_reasons(value: object) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise ValueError("rejection_reasons_must_be_sequence")
    reasons = tuple(str(item) for item in value)
    for reason in reasons:
        _require_nonempty_string(reason, "rejection_reason")
    return tuple(_dedupe(reasons))


def _require_nonempty_string(value: object, field_name: str) -> None:
    if not isinstance(value, str) or not value:
        raise ValueError(field_name + "_required")


def _require_sha256(value: object, field_name: str) -> None:
    if not isinstance(value, str) or not _SHA256_PATTERN.fullmatch(value):
        raise ValueError(field_name + "_must_be_sha256")


def _canonical_json(payload: Mapping[str, object]) -> str:
    return json.dumps(_json_ready(payload), sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _json_ready(value: object) -> Any:
    if isinstance(value, tuple):
        return [_json_ready(item) for item in value]
    if isinstance(value, list):
        return [_json_ready(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _json_ready(item) for key, item in value.items()}
    return value


def _sha256(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def _dedupe(values: Sequence[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value not in seen:
            result.append(value)
            seen.add(value)
    return tuple(result)
