"""File-backed real WAL storage implementation V1.

Persists contract-valid ``RealWalStorageRecord`` lines to an explicit local
JSONL file. The backend stores only digest-bound metadata, validates the full
hash chain before every append, and fails closed on malformed or tampered WAL
content.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
from typing import Mapping, Sequence

from kernel.stores.real_wal_storage_contract import (
    REAL_WAL_STORAGE_CONTRACT_VERSION,
    REAL_WAL_STORAGE_REPLAY_POLICY_VERSION,
    RealWalStorageRecord,
    RealWalStorageReplayResult,
    parse_real_wal_storage_record_line,
    replay_real_wal_storage_records,
    serialize_real_wal_storage_record_line,
    validate_real_wal_storage_record,
)

__all__ = [
    "FileBackedRealWalStorage",
    "RealWalStorageAppendReceipt",
    "RealWalStorageCorruptionError",
    "RealWalStorageError",
]


class RealWalStorageError(ValueError):
    """Raised when the durable WAL storage request violates the boundary."""


class RealWalStorageCorruptionError(RealWalStorageError):
    """Raised when existing WAL contents fail closed during replay."""


@dataclass(frozen=True)
class RealWalStorageAppendReceipt:
    wal_path: str
    sequence: int
    record_hash: str
    previous_hash: str | None
    replay_result_hash: str

    def as_dict(self) -> dict[str, object]:
        return {
            "wal_path": self.wal_path,
            "sequence": self.sequence,
            "record_hash": self.record_hash,
            "previous_hash": self.previous_hash,
            "replay_result_hash": self.replay_result_hash,
        }


class FileBackedRealWalStorage:
    """Append-only JSONL WAL store for real WAL storage records."""

    def __init__(self, wal_path: str | Path) -> None:
        self.wal_path = Path(wal_path)
        if not self.wal_path.parent.exists():
            raise RealWalStorageError("wal_parent_directory_missing")
        if self.wal_path.exists() and not self.wal_path.is_file():
            raise RealWalStorageError("wal_path_must_be_file")
        self._ensure_file()

    def append(
        self,
        *,
        record_type: str,
        task_id: str,
        run_id: str,
        payload_hash: str,
        digest_bindings: Mapping[str, str] | Sequence[tuple[str, str]],
        created_at: str | None = None,
    ) -> RealWalStorageAppendReceipt:
        records = self.read_records()
        sequence = 1 if not records else records[-1].sequence + 1
        previous_hash = None if not records else records[-1].record_hash
        record = RealWalStorageRecord(
            wal_record_id=_wal_record_id(
                sequence=sequence,
                previous_hash=previous_hash,
                record_type=record_type,
                task_id=task_id,
                run_id=run_id,
                payload_hash=payload_hash,
                digest_bindings=digest_bindings,
            ),
            wal_storage_contract_version=REAL_WAL_STORAGE_CONTRACT_VERSION,
            sequence=sequence,
            previous_hash=previous_hash,
            record_type=record_type,
            task_id=task_id,
            run_id=run_id,
            payload_hash=payload_hash,
            digest_bindings=digest_bindings,
            created_at=created_at or _now(),
        )
        return self.append_record(record)

    def append_record(
        self, record: RealWalStorageRecord
    ) -> RealWalStorageAppendReceipt:
        records = self.read_records()
        expected_sequence = 1 if not records else records[-1].sequence + 1
        expected_previous_hash = None if not records else records[-1].record_hash
        try:
            validate_real_wal_storage_record(
                record,
                expected_sequence=expected_sequence,
                expected_previous_hash=expected_previous_hash,
            )
        except ValueError as exc:
            raise RealWalStorageError(str(exc)) from exc

        _append_line_durably(
            self.wal_path, serialize_real_wal_storage_record_line(record)
        )
        replay = self.replay()
        if not replay.accepted:
            raise RealWalStorageCorruptionError(
                "wal_replay_rejected_after_append:"
                + ",".join(replay.rejection_reasons)
            )
        return RealWalStorageAppendReceipt(
            wal_path=str(self.wal_path),
            sequence=record.sequence,
            record_hash=record.record_hash,
            previous_hash=record.previous_hash,
            replay_result_hash=replay.replay_result_hash,
        )

    def read_records(self) -> tuple[RealWalStorageRecord, ...]:
        records, parse_failures = self._parse_records()
        if parse_failures:
            raise RealWalStorageCorruptionError(",".join(parse_failures))
        replay = replay_real_wal_storage_records(records)
        if not replay.accepted:
            raise RealWalStorageCorruptionError(
                ",".join(replay.rejection_reasons)
            )
        return records

    def replay(self) -> RealWalStorageReplayResult:
        records, parse_failures = self._parse_records()
        if parse_failures:
            return _rejected_replay(records, parse_failures)
        return replay_real_wal_storage_records(records)

    def _parse_records(
        self,
    ) -> tuple[tuple[RealWalStorageRecord, ...], tuple[str, ...]]:
        records: list[RealWalStorageRecord] = []
        failures: list[str] = []
        with self.wal_path.open("r", encoding="utf-8", newline="") as handle:
            for line_number, line in enumerate(handle, start=1):
                try:
                    records.append(parse_real_wal_storage_record_line(line))
                except ValueError as exc:
                    failures.append(f"wal_line_{line_number}:{exc}")
                    break
        return tuple(records), tuple(failures)

    def _ensure_file(self) -> None:
        if self.wal_path.exists():
            return
        fd = os.open(
            self.wal_path,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL,
            0o600,
        )
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
        _fsync_parent(self.wal_path)


def _rejected_replay(
    records: Sequence[RealWalStorageRecord],
    failures: Sequence[str],
) -> RealWalStorageReplayResult:
    return RealWalStorageReplayResult(
        replay_policy_version=REAL_WAL_STORAGE_REPLAY_POLICY_VERSION,
        accepted=False,
        rejection_reasons=tuple(failures),
        record_count=len(records),
        first_sequence=None if not records else records[0].sequence,
        last_sequence=None if not records else records[-1].sequence,
        last_record_hash=None if not records else records[-1].record_hash,
    )


def _append_line_durably(path: Path, line: str) -> None:
    data = line.encode("utf-8")
    fd = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
    try:
        written = 0
        while written < len(data):
            count = os.write(fd, data[written:])
            if count <= 0:
                raise RealWalStorageError("wal_append_write_failed")
            written += count
        os.fsync(fd)
    finally:
        os.close(fd)
    _fsync_parent(path)


def _fsync_parent(path: Path) -> None:
    try:
        fd = os.open(path.parent, os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _wal_record_id(
    *,
    sequence: int,
    previous_hash: str | None,
    record_type: str,
    task_id: str,
    run_id: str,
    payload_hash: str,
    digest_bindings: object,
) -> str:
    digest = _sha256(
        _canonical_json(
            {
                "sequence": sequence,
                "previous_hash": previous_hash,
                "record_type": record_type,
                "task_id": task_id,
                "run_id": run_id,
                "payload_hash": payload_hash,
                "digest_bindings": _json_ready(digest_bindings),
            }
        )
    )
    return "real-wal-record-" + digest.removeprefix("sha256:")[:32]


def _canonical_json(payload: Mapping[str, object]) -> str:
    return json.dumps(
        _json_ready(payload),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )


def _json_ready(value: object) -> object:
    if isinstance(value, Mapping):
        return {str(key): _json_ready(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_json_ready(item) for item in value]
    if isinstance(value, list):
        return [_json_ready(item) for item in value]
    return value


def _sha256(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")
