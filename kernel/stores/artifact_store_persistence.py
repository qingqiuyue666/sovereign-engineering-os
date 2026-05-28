"""File-backed artifact store persistence implementation V1.

Persists digest-addressed local artifact bytes and append-only manifest
records over the Artifact Store Contract V1. Each artifact manifest is bound to
the real WAL storage backend before the manifest record is appended.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
from typing import Any, Mapping, Sequence

from kernel.stores.artifact_store_contract import (
    ArtifactManifest,
    ArtifactVerificationReceipt,
    artifact_manifest_from_ingest,
    verify_artifact_manifest,
)
from kernel.stores.real_wal_storage import (
    FileBackedRealWalStorage,
    RealWalStorageError,
)

__all__ = [
    "ARTIFACT_STORE_PERSISTENCE_VERSION",
    "REAL_WAL_BINDING_STATUS",
    "ArtifactStorePersistenceError",
    "ArtifactStorePersistenceRecord",
    "ArtifactStoreReplayError",
    "ArtifactStoreReplayResult",
    "ArtifactWriteReceipt",
    "FileBackedArtifactStore",
    "compute_artifact_record_hash",
]

ARTIFACT_STORE_PERSISTENCE_VERSION = "artifact_store_persistence_v1"
REAL_WAL_BINDING_STATUS = "real_wal_storage_backend_v1_bound"

_ARTIFACT_RECORD_VERSION = "artifact_store_persistence_record_v1"
_DEFAULT_STORE_ID = "artifact-store-persistence-v1"
_PREFLIGHT_WAL_RECORD_HASH = "sha256:" + ("0" * 64)
_RECORD_KEYS = frozenset(
    {
        "artifact_record_version",
        "manifest",
        "metadata",
        "previous_record_hash",
        "real_wal_binding_status",
        "record_hash",
        "sequence",
        "store_id",
    }
)
_SHA256_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")
_SECRET_KEY_PATTERN = re.compile(
    r"(?i)(api[_-]?key|auth|authorization|credential|password|private[_-]?key|secret|token)"
)
_SECRET_VALUE_PATTERNS = (
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"(?i)\bbearer\s+[a-z0-9._~+/=-]{16,}"),
    re.compile(r"(?i)\bsk-[a-z0-9]{20,}"),
    re.compile(
        r"(?s)-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----"
    ),
)
_FORBIDDEN_METADATA_FIELDS = frozenset(
    {
        "args",
        "argv",
        "command",
        "command_line",
        "content",
        "cwd",
        "env",
        "environment",
        "executable",
        "executable_path",
        "path",
        "raw_bytes",
        "raw_content",
        "raw_log",
        "raw_stderr",
        "raw_stdout",
        "secret",
        "shell",
        "stderr",
        "stdout",
        "subprocess",
        "timeout",
        "url",
    }
)
_SECRET_PATH_PATTERN = re.compile(
    r"(?i)(^\.env$|\.env\.local|\.envrc|credential|id_rsa|id_dsa|id_ed25519|secret|token|password)"
)


class ArtifactStorePersistenceError(ValueError):
    """Raised when an artifact persistence request fails closed."""


class ArtifactStoreReplayError(ArtifactStorePersistenceError):
    """Raised when persisted artifact records cannot be replayed safely."""


@dataclass(frozen=True)
class ArtifactStorePersistenceRecord:
    artifact_record_version: str
    store_id: str
    sequence: int
    previous_record_hash: str | None
    manifest: ArtifactManifest
    metadata: dict[str, object]
    real_wal_binding_status: str
    record_hash: str = ""

    def __post_init__(self) -> None:
        if self.artifact_record_version != _ARTIFACT_RECORD_VERSION:
            raise ArtifactStoreReplayError("artifact_record_version_invalid")
        _require_nonempty_string(self.store_id, "store_id")
        if not isinstance(self.sequence, int) or isinstance(self.sequence, bool):
            raise ArtifactStoreReplayError("sequence_must_be_int")
        if self.sequence <= 0:
            raise ArtifactStoreReplayError("sequence_must_be_positive")
        if self.previous_record_hash is not None:
            _require_sha256(self.previous_record_hash, "previous_record_hash")
        if not isinstance(self.manifest, ArtifactManifest):
            raise ArtifactStoreReplayError("manifest_must_be_artifact_manifest")
        metadata = _normalize_metadata(self.metadata)
        object.__setattr__(self, "metadata", metadata)
        if self.real_wal_binding_status != REAL_WAL_BINDING_STATUS:
            raise ArtifactStoreReplayError("real_wal_binding_status_invalid")
        if self.record_hash:
            _require_sha256(self.record_hash, "record_hash")
        expected = compute_artifact_record_hash(self)
        if self.record_hash and self.record_hash != expected:
            raise ArtifactStoreReplayError("record_hash_mismatch")
        object.__setattr__(self, "record_hash", expected)

    def as_dict(self) -> dict[str, object]:
        return {
            "artifact_record_version": self.artifact_record_version,
            "manifest": self.manifest.as_dict(),
            "metadata": self.metadata,
            "previous_record_hash": self.previous_record_hash,
            "real_wal_binding_status": self.real_wal_binding_status,
            "record_hash": self.record_hash,
            "sequence": self.sequence,
            "store_id": self.store_id,
        }


@dataclass(frozen=True)
class ArtifactStoreReplayResult:
    accepted: bool
    rejection_reasons: tuple[str, ...]
    record_count: int
    first_sequence: int | None
    last_sequence: int | None
    last_record_hash: str | None
    replay_result_hash: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.accepted, bool):
            raise ArtifactStoreReplayError("accepted_must_be_bool")
        object.__setattr__(
            self,
            "rejection_reasons",
            _normalize_reasons(self.rejection_reasons),
        )
        if self.accepted and self.rejection_reasons:
            raise ArtifactStoreReplayError("accepted_replay_cannot_have_rejections")
        if not self.accepted and not self.rejection_reasons:
            raise ArtifactStoreReplayError("rejected_replay_requires_rejections")
        if not isinstance(self.record_count, int) or self.record_count < 0:
            raise ArtifactStoreReplayError("record_count_must_be_nonnegative_int")
        for field_name in ("first_sequence", "last_sequence"):
            value = getattr(self, field_name)
            if value is not None and (not isinstance(value, int) or value <= 0):
                raise ArtifactStoreReplayError(field_name + "_must_be_positive_int")
        if self.last_record_hash is not None:
            _require_sha256(self.last_record_hash, "last_record_hash")
        if self.replay_result_hash:
            _require_sha256(self.replay_result_hash, "replay_result_hash")
        expected = compute_artifact_replay_hash(self)
        if self.replay_result_hash and self.replay_result_hash != expected:
            raise ArtifactStoreReplayError("replay_result_hash_mismatch")
        object.__setattr__(self, "replay_result_hash", expected)

    def as_dict(self) -> dict[str, object]:
        return _json_ready(asdict(self))


@dataclass(frozen=True)
class ArtifactWriteReceipt:
    artifact_path: str
    manifest_log_path: str
    wal_path: str
    sequence: int
    manifest: ArtifactManifest
    metadata_hash: str
    wal_record_hash: str
    record_hash: str
    verification_hash: str

    def as_dict(self) -> dict[str, object]:
        return {
            "artifact_path": self.artifact_path,
            "manifest": self.manifest.as_dict(),
            "manifest_log_path": self.manifest_log_path,
            "metadata_hash": self.metadata_hash,
            "record_hash": self.record_hash,
            "sequence": self.sequence,
            "verification_hash": self.verification_hash,
            "wal_path": self.wal_path,
            "wal_record_hash": self.wal_record_hash,
        }


class FileBackedArtifactStore:
    """Local content-addressed artifact store with append-only manifests."""

    def __init__(
        self,
        root_path: str | Path,
        *,
        store_id: str = _DEFAULT_STORE_ID,
        manifest_log_path: str | Path | None = None,
        wal_path: str | Path | None = None,
    ) -> None:
        _require_nonempty_string(store_id, "store_id")
        self.root_path = _validate_root(Path(root_path))
        self.store_id = store_id
        self.manifest_log_path = _validate_child_path(
            self.root_path,
            Path(manifest_log_path)
            if manifest_log_path is not None
            else self.root_path / "artifact-manifests.jsonl",
            "manifest_log_path",
        )
        self.wal_path = _validate_child_path(
            self.root_path,
            Path(wal_path)
            if wal_path is not None
            else self.root_path / "artifact-store.real-wal.jsonl",
            "wal_path",
        )
        if self.manifest_log_path == self.wal_path:
            raise ArtifactStorePersistenceError("manifest_log_and_wal_must_be_distinct")

    def write_json_artifact(
        self,
        *,
        artifact_type: str,
        task_id: str,
        run_id: str,
        payload: Mapping[str, object],
        provenance_hash: str,
        metadata: Mapping[str, object] | None = None,
        created_at: str | None = None,
        retention_marker: str = "retain",
        quarantine_marker: str = "clean",
        local_only: bool = True,
    ) -> ArtifactWriteReceipt:
        content = _canonical_json(_normalize_metadata(payload)).encode("utf-8")
        return self.write_artifact(
            artifact_type=artifact_type,
            task_id=task_id,
            run_id=run_id,
            content=content,
            provenance_hash=provenance_hash,
            metadata=metadata,
            created_at=created_at,
            retention_marker=retention_marker,
            quarantine_marker=quarantine_marker,
            local_only=local_only,
        )

    def write_artifact(
        self,
        *,
        artifact_type: str,
        task_id: str,
        run_id: str,
        content: bytes,
        provenance_hash: str,
        metadata: Mapping[str, object] | None = None,
        created_at: str | None = None,
        retention_marker: str = "retain",
        quarantine_marker: str = "clean",
        local_only: bool = True,
    ) -> ArtifactWriteReceipt:
        _require_nonempty_string(task_id, "task_id")
        _require_nonempty_string(run_id, "run_id")
        if not isinstance(content, bytes):
            raise ArtifactStorePersistenceError("content_must_be_bytes")
        normalized_metadata = _normalize_metadata(metadata or {})
        metadata_hash = _sha256_json(normalized_metadata)
        content_sha256 = _sha256_bytes(content)
        occurred_at = _timestamp(created_at)
        self._initialize()
        with self.manifest_log_path.open("a+", encoding="utf-8", newline="") as handle:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            try:
                handle.seek(0)
                records = _records_from_text(handle.read(), store_id=self.store_id)
                replay = self._verify_records(records)
                if not replay.accepted:
                    raise ArtifactStoreReplayError(
                        "stored_artifact_replay_rejected:"
                        + ",".join(replay.rejection_reasons)
                    )
                preflight_manifest = artifact_manifest_from_ingest(
                    {
                        "artifact_type": artifact_type,
                        "content_sha256": content_sha256,
                        "created_at": occurred_at,
                        "local_only": local_only,
                        "provenance_hash": provenance_hash,
                        "quarantine_marker": quarantine_marker,
                        "retention_marker": retention_marker,
                        "run_id": run_id,
                        "size_bytes": len(content),
                        "task_id": task_id,
                        "wal_record_hash": _PREFLIGHT_WAL_RECORD_HASH,
                    }
                )
                artifact_path = self.artifact_path(preflight_manifest)
                if any(
                    record.manifest.artifact_id == preflight_manifest.artifact_id
                    for record in records
                ):
                    raise ArtifactStorePersistenceError("artifact_id_already_persisted")
                if artifact_path.exists():
                    raise ArtifactStorePersistenceError("artifact_path_already_exists")
                _write_file_atomic_no_overwrite(artifact_path, content)
                wal_payload_hash = _artifact_material_hash(
                    store_id=self.store_id,
                    manifest=preflight_manifest,
                    metadata_hash=metadata_hash,
                )
                wal_record_hash = self._append_real_wal_event(
                    manifest=preflight_manifest,
                    metadata_hash=metadata_hash,
                    payload_hash=wal_payload_hash,
                    created_at=occurred_at,
                )
                manifest = artifact_manifest_from_ingest(
                    {
                        "artifact_id": preflight_manifest.artifact_id,
                        "artifact_manifest_id": preflight_manifest.artifact_manifest_id,
                        "artifact_type": preflight_manifest.artifact_type,
                        "content_sha256": preflight_manifest.content_sha256,
                        "created_at": preflight_manifest.created_at,
                        "local_only": preflight_manifest.local_only,
                        "provenance_hash": preflight_manifest.provenance_hash,
                        "quarantine_marker": preflight_manifest.quarantine_marker,
                        "retention_marker": preflight_manifest.retention_marker,
                        "run_id": preflight_manifest.run_id,
                        "size_bytes": preflight_manifest.size_bytes,
                        "storage_relpath": preflight_manifest.storage_relpath,
                        "task_id": preflight_manifest.task_id,
                        "wal_record_hash": wal_record_hash,
                    }
                )
                verification = verify_artifact_manifest(
                    manifest,
                    observed_content_sha256=_sha256_file(artifact_path),
                    observed_size_bytes=artifact_path.stat().st_size,
                )
                if not verification.accepted:
                    raise ArtifactStoreReplayError(
                        "artifact_verification_rejected:"
                        + ",".join(verification.failures)
                    )
                sequence = len(records) + 1
                previous_record_hash = None if not records else records[-1].record_hash
                record = ArtifactStorePersistenceRecord(
                    artifact_record_version=_ARTIFACT_RECORD_VERSION,
                    store_id=self.store_id,
                    sequence=sequence,
                    previous_record_hash=previous_record_hash,
                    manifest=manifest,
                    metadata=normalized_metadata,
                    real_wal_binding_status=REAL_WAL_BINDING_STATUS,
                )
                handle.seek(0, os.SEEK_END)
                handle.write(_canonical_json(record.as_dict()))
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            finally:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        _fsync_parent(self.manifest_log_path)
        return ArtifactWriteReceipt(
            artifact_path=str(artifact_path),
            manifest_log_path=str(self.manifest_log_path),
            wal_path=str(self.wal_path),
            sequence=record.sequence,
            manifest=record.manifest,
            metadata_hash=metadata_hash,
            wal_record_hash=wal_record_hash,
            record_hash=record.record_hash,
            verification_hash=verification.verification_hash,
        )

    def read_records(self) -> tuple[ArtifactStorePersistenceRecord, ...]:
        records = _load_records(self.manifest_log_path, store_id=self.store_id)
        replay = self._verify_records(records)
        if not replay.accepted:
            raise ArtifactStoreReplayError(",".join(replay.rejection_reasons))
        return records

    def replay(self) -> ArtifactStoreReplayResult:
        try:
            records = _load_records(self.manifest_log_path, store_id=self.store_id)
        except ArtifactStoreReplayError as exc:
            return _rejected_replay((), (str(exc),))
        return self._verify_records(records)

    def list_manifests(
        self,
        *,
        artifact_type: str | None = None,
        task_id: str | None = None,
        run_id: str | None = None,
    ) -> tuple[ArtifactManifest, ...]:
        manifests = []
        for record in self.read_records():
            manifest = record.manifest
            if artifact_type is not None and manifest.artifact_type != artifact_type:
                continue
            if task_id is not None and manifest.task_id != task_id:
                continue
            if run_id is not None and manifest.run_id != run_id:
                continue
            manifests.append(manifest)
        return tuple(
            sorted(
                manifests,
                key=lambda item: (
                    item.artifact_id,
                    item.artifact_manifest_id,
                    item.manifest_hash,
                ),
            )
        )

    def get_manifest(self, artifact_id: str) -> ArtifactManifest:
        _require_nonempty_string(artifact_id, "artifact_id")
        for manifest in self.list_manifests():
            if manifest.artifact_id == artifact_id:
                return manifest
        raise ArtifactStorePersistenceError("artifact_not_found")

    def verify_artifact(self, artifact_id: str) -> ArtifactVerificationReceipt:
        manifest = self.get_manifest(artifact_id)
        artifact_path = self.artifact_path(manifest)
        return verify_artifact_manifest(
            manifest,
            observed_content_sha256=_sha256_file(artifact_path),
            observed_size_bytes=artifact_path.stat().st_size,
        )

    def artifact_path(self, manifest: ArtifactManifest) -> Path:
        if not isinstance(manifest, ArtifactManifest):
            raise ArtifactStorePersistenceError("manifest_must_be_artifact_manifest")
        return _validate_child_path(
            self.root_path,
            self.root_path / manifest.storage_relpath,
            "artifact_path",
        )

    def wal_binding_status(self) -> dict[str, object]:
        return {
            "available": True,
            "binding_mode": "file_backed_real_wal_storage_artifact_event_binding_v1",
            "blocker": "",
            "wal_path": str(self.wal_path),
        }

    def _append_real_wal_event(
        self,
        *,
        manifest: ArtifactManifest,
        metadata_hash: str,
        payload_hash: str,
        created_at: str,
    ) -> str:
        self.wal_path.parent.mkdir(parents=True, exist_ok=True)
        digest_bindings = {
            "artifact_content_hash": manifest.content_sha256,
            "artifact_id_hash": _sha256_text("artifact_id:" + manifest.artifact_id),
            "artifact_metadata_hash": metadata_hash,
            "artifact_store_hash": _sha256_text("store_id:" + self.store_id),
        }
        try:
            receipt = FileBackedRealWalStorage(self.wal_path).append(
                record_type="ARTIFACT_EVENT",
                task_id=manifest.task_id,
                run_id=manifest.run_id,
                payload_hash=payload_hash,
                digest_bindings=digest_bindings,
                created_at=created_at,
            )
        except RealWalStorageError as exc:
            raise ArtifactStoreReplayError("real_wal_append_failed:" + str(exc)) from exc
        return receipt.record_hash

    def _verify_records(
        self, records: Sequence[ArtifactStorePersistenceRecord]
    ) -> ArtifactStoreReplayResult:
        failures: list[str] = []
        previous_hash: str | None = None
        expected_sequence = 1
        seen_artifact_ids: set[str] = set()
        seen_manifest_ids: set[str] = set()
        seen_storage_paths: set[str] = set()
        wal_by_hash = self._wal_records_by_hash(records, failures)

        for record in records:
            if record.sequence != expected_sequence:
                failures.append("sequence_gap_detected")
            if record.previous_record_hash != previous_hash:
                failures.append("previous_record_hash_mismatch")
            if record.record_hash != compute_artifact_record_hash(record):
                failures.append("record_hash_mismatch")
            manifest = record.manifest
            if manifest.artifact_id in seen_artifact_ids:
                failures.append("duplicate_artifact_id")
            if manifest.artifact_manifest_id in seen_manifest_ids:
                failures.append("duplicate_artifact_manifest_id")
            if manifest.storage_relpath in seen_storage_paths:
                failures.append("duplicate_storage_relpath")
            seen_artifact_ids.add(manifest.artifact_id)
            seen_manifest_ids.add(manifest.artifact_manifest_id)
            seen_storage_paths.add(manifest.storage_relpath)
            self._verify_artifact_file(manifest, failures)
            self._verify_real_wal_binding(record, wal_by_hash, failures)
            previous_hash = record.record_hash
            expected_sequence += 1

        return ArtifactStoreReplayResult(
            accepted=not failures,
            rejection_reasons=tuple(_dedupe(failures)),
            record_count=len(records),
            first_sequence=None if not records else records[0].sequence,
            last_sequence=None if not records else records[-1].sequence,
            last_record_hash=None if not records else records[-1].record_hash,
        )

    def _verify_artifact_file(
        self, manifest: ArtifactManifest, failures: list[str]
    ) -> None:
        try:
            artifact_path = self.artifact_path(manifest)
            if not artifact_path.exists():
                failures.append("artifact_file_missing")
                return
            if artifact_path.is_symlink():
                failures.append("artifact_file_is_symlink")
                return
            if not artifact_path.is_file():
                failures.append("artifact_path_not_file")
                return
            receipt = verify_artifact_manifest(
                manifest,
                observed_content_sha256=_sha256_file(artifact_path),
                observed_size_bytes=artifact_path.stat().st_size,
            )
            if not receipt.accepted:
                failures.extend(receipt.failures)
        except (OSError, ValueError) as exc:
            failures.append("artifact_file_verification_failed:" + str(exc))

    def _verify_real_wal_binding(
        self,
        record: ArtifactStorePersistenceRecord,
        wal_by_hash: Mapping[str, object],
        failures: list[str],
    ) -> None:
        manifest = record.manifest
        wal_record = wal_by_hash.get(manifest.wal_record_hash)
        if wal_record is None:
            failures.append("real_wal_record_missing")
            return
        if getattr(wal_record, "record_type") != "ARTIFACT_EVENT":
            failures.append("real_wal_record_type_mismatch")
        if getattr(wal_record, "task_id") != manifest.task_id or getattr(wal_record, "run_id") != manifest.run_id:
            failures.append("real_wal_identity_mismatch")
        expected_payload_hash = _artifact_material_hash(
            store_id=self.store_id,
            manifest=manifest,
            metadata_hash=_sha256_json(record.metadata),
        )
        if getattr(wal_record, "payload_hash") != expected_payload_hash:
            failures.append("real_wal_payload_hash_mismatch")
        digest_bindings = dict(getattr(wal_record, "digest_bindings"))
        expected_bindings = {
            "artifact_content_hash": manifest.content_sha256,
            "artifact_id_hash": _sha256_text("artifact_id:" + manifest.artifact_id),
            "artifact_metadata_hash": _sha256_json(record.metadata),
            "artifact_store_hash": _sha256_text("store_id:" + self.store_id),
        }
        for name, expected in expected_bindings.items():
            if digest_bindings.get(name) != expected:
                failures.append("real_wal_digest_binding_mismatch:" + name)

    def _wal_records_by_hash(
        self,
        records: Sequence[ArtifactStorePersistenceRecord],
        failures: list[str],
    ) -> dict[str, object]:
        if not records:
            return {}
        if not self.wal_path.exists():
            failures.append("real_wal_file_missing")
            return {}
        if self.wal_path.is_symlink():
            failures.append("real_wal_path_is_symlink")
            return {}
        try:
            wal_records = FileBackedRealWalStorage(self.wal_path).read_records()
        except RealWalStorageError as exc:
            failures.append("real_wal_replay_failed:" + str(exc))
            return {}
        return {record.record_hash: record for record in wal_records}

    def _initialize(self) -> None:
        self.root_path.mkdir(parents=True, exist_ok=True)
        self.manifest_log_path.parent.mkdir(parents=True, exist_ok=True)
        self.wal_path.parent.mkdir(parents=True, exist_ok=True)
        if self.root_path.is_symlink():
            raise ArtifactStorePersistenceError("artifact_root_is_symlink")
        if self.manifest_log_path.exists() and not self.manifest_log_path.is_file():
            raise ArtifactStorePersistenceError("manifest_log_path_must_be_file")
        if self.wal_path.exists() and not self.wal_path.is_file():
            raise ArtifactStorePersistenceError("wal_path_must_be_file")


def compute_artifact_record_hash(
    record: ArtifactStorePersistenceRecord | Mapping[str, object]
) -> str:
    if isinstance(record, ArtifactStorePersistenceRecord):
        payload = {
            "artifact_manifest_id": record.manifest.artifact_manifest_id,
            "artifact_record_version": record.artifact_record_version,
            "manifest_hash": record.manifest.manifest_hash,
            "metadata_hash": _sha256_json(record.metadata),
            "previous_record_hash": record.previous_record_hash,
            "real_wal_binding_status": record.real_wal_binding_status,
            "sequence": record.sequence,
            "store_id": record.store_id,
            "wal_record_hash": record.manifest.wal_record_hash,
        }
    else:
        payload = dict(record)
        payload.pop("record_hash", None)
    return _sha256_json(payload)


def compute_artifact_replay_hash(
    result: ArtifactStoreReplayResult | Mapping[str, object]
) -> str:
    if isinstance(result, ArtifactStoreReplayResult):
        payload = result.as_dict()
    else:
        payload = dict(result)
    payload.pop("replay_result_hash", None)
    return _sha256_json(payload)


def _load_records(
    path: Path,
    *,
    store_id: str,
) -> tuple[ArtifactStorePersistenceRecord, ...]:
    if not path.exists():
        return ()
    if path.is_dir():
        raise ArtifactStoreReplayError("manifest_log_path_is_directory")
    if path.is_symlink():
        raise ArtifactStoreReplayError("manifest_log_path_is_symlink")
    with path.open("r", encoding="utf-8", newline="") as handle:
        return _records_from_text(handle.read(), store_id=store_id)


def _records_from_text(
    text: str,
    *,
    store_id: str,
) -> tuple[ArtifactStorePersistenceRecord, ...]:
    records: list[ArtifactStorePersistenceRecord] = []
    if text and not text.endswith("\n"):
        raise ArtifactStoreReplayError("partial_manifest_record_line")
    for index, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            raw = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ArtifactStoreReplayError(f"manifest_record_line_{index}_invalid_json") from exc
        if not isinstance(raw, Mapping):
            raise ArtifactStoreReplayError(f"manifest_record_line_{index}_must_be_object")
        if set(raw) != _RECORD_KEYS:
            raise ArtifactStoreReplayError(f"manifest_record_line_{index}_keys_invalid")
        manifest_payload = raw.get("manifest")
        if not isinstance(manifest_payload, Mapping):
            raise ArtifactStoreReplayError(f"manifest_record_line_{index}_manifest_required")
        manifest = artifact_manifest_from_ingest(manifest_payload)
        record = ArtifactStorePersistenceRecord(
            artifact_record_version=str(raw.get("artifact_record_version", "")),
            store_id=str(raw.get("store_id", "")),
            sequence=raw.get("sequence"),  # type: ignore[arg-type]
            previous_record_hash=(
                None
                if raw.get("previous_record_hash") is None
                else str(raw.get("previous_record_hash"))
            ),
            manifest=manifest,
            metadata=_raw_metadata(raw),
            real_wal_binding_status=str(raw.get("real_wal_binding_status", "")),
            record_hash=str(raw.get("record_hash", "")),
        )
        if record.store_id != store_id:
            raise ArtifactStoreReplayError("store_id_mismatch")
        records.append(record)
    return tuple(records)


def _raw_metadata(raw: Mapping[str, object]) -> dict[str, object]:
    metadata = raw.get("metadata")
    if not isinstance(metadata, Mapping):
        raise ArtifactStoreReplayError("metadata_must_be_mapping")
    return _normalize_metadata(metadata)


def _rejected_replay(
    records: Sequence[ArtifactStorePersistenceRecord],
    failures: Sequence[str],
) -> ArtifactStoreReplayResult:
    return ArtifactStoreReplayResult(
        accepted=False,
        rejection_reasons=tuple(failures),
        record_count=len(records),
        first_sequence=None if not records else records[0].sequence,
        last_sequence=None if not records else records[-1].sequence,
        last_record_hash=None if not records else records[-1].record_hash,
    )


def _artifact_material_hash(
    *,
    store_id: str,
    manifest: ArtifactManifest,
    metadata_hash: str,
) -> str:
    return _sha256_json(
        {
            "artifact_id": manifest.artifact_id,
            "artifact_manifest_id": manifest.artifact_manifest_id,
            "artifact_type": manifest.artifact_type,
            "content_sha256": manifest.content_sha256,
            "local_only": manifest.local_only,
            "metadata_hash": metadata_hash,
            "persistence_version": ARTIFACT_STORE_PERSISTENCE_VERSION,
            "provenance_hash": manifest.provenance_hash,
            "quarantine_marker": manifest.quarantine_marker,
            "retention_marker": manifest.retention_marker,
            "run_id": manifest.run_id,
            "size_bytes": manifest.size_bytes,
            "storage_relpath": manifest.storage_relpath,
            "store_id": store_id,
            "task_id": manifest.task_id,
        }
    )


def _write_file_atomic_no_overwrite(path: Path, data: bytes) -> None:
    if path.exists():
        raise ArtifactStorePersistenceError("artifact_path_already_exists")
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.parent.is_symlink():
        raise ArtifactStorePersistenceError("artifact_parent_is_symlink")
    temp_path = path.with_name("." + path.name + ".tmp-" + _sha256_bytes(data).split(":", 1)[1][:16])
    fd = os.open(temp_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        written = 0
        while written < len(data):
            count = os.write(fd, data[written:])
            if count <= 0:
                raise ArtifactStorePersistenceError("artifact_write_failed")
            written += count
        os.fsync(fd)
    finally:
        os.close(fd)
    try:
        if path.exists():
            raise ArtifactStorePersistenceError("artifact_path_already_exists")
        temp_path.rename(path)
        _fsync_parent(path)
    except Exception:
        try:
            temp_path.unlink()
        except OSError:
            pass
        raise


def _validate_root(root: Path) -> Path:
    if not str(root):
        raise ArtifactStorePersistenceError("artifact_root_required")
    raw = root.expanduser()
    if raw.exists() and raw.is_symlink():
        raise ArtifactStorePersistenceError("artifact_root_is_symlink")
    if raw.exists() and not raw.is_dir():
        raise ArtifactStorePersistenceError("artifact_root_must_be_directory")
    resolved = raw.resolve(strict=False)
    _reject_secret_or_git_path(resolved, "artifact_root")
    if resolved.parent.exists() and resolved.parent.is_symlink():
        raise ArtifactStorePersistenceError("artifact_root_parent_is_symlink")
    return resolved


def _validate_child_path(root: Path, path: Path, field_name: str) -> Path:
    raw = path.expanduser()
    resolved = raw.resolve(strict=False)
    _reject_secret_or_git_path(resolved, field_name)
    if resolved.exists() and resolved.is_symlink():
        raise ArtifactStorePersistenceError(field_name + "_is_symlink")
    if resolved.parent.exists() and resolved.parent.is_symlink():
        raise ArtifactStorePersistenceError(field_name + "_parent_is_symlink")
    if not resolved.is_relative_to(root):
        raise ArtifactStorePersistenceError(field_name + "_escapes_artifact_root")
    return resolved


def _reject_secret_or_git_path(path: Path, field_name: str) -> None:
    if ".git" in path.parts:
        raise ArtifactStorePersistenceError(field_name + "_cannot_enter_git")
    if any(_SECRET_PATH_PATTERN.fullmatch(part) for part in path.parts):
        raise ArtifactStorePersistenceError(field_name + "_secret_like")


def _normalize_metadata(value: object, *, path: tuple[str, ...] = ()) -> dict[str, object]:
    if not isinstance(value, Mapping):
        raise ArtifactStorePersistenceError("metadata_must_be_mapping")
    normalized: dict[str, object] = {}
    for key, item in value.items():
        key_text = str(key)
        if (
            key_text in _FORBIDDEN_METADATA_FIELDS
            or _SECRET_KEY_PATTERN.search(key_text)
        ):
            raise ArtifactStorePersistenceError(
                "metadata_field_forbidden:" + ".".join(path + (key_text,))
            )
        normalized[key_text] = _normalize_json_value(item, path=path + (key_text,))
    return dict(sorted(normalized.items()))


def _normalize_json_value(value: object, *, path: tuple[str, ...]) -> object:
    if isinstance(value, Mapping):
        return _normalize_metadata(value, path=path)
    if isinstance(value, tuple):
        return [_normalize_json_value(item, path=path + (str(index),)) for index, item in enumerate(value)]
    if isinstance(value, list):
        return [_normalize_json_value(item, path=path + (str(index),)) for index, item in enumerate(value)]
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, str):
        for pattern in _SECRET_VALUE_PATTERNS:
            if pattern.search(value):
                raise ArtifactStorePersistenceError("metadata_secret_value_forbidden")
        return value
    raise ArtifactStorePersistenceError("metadata_type_forbidden:" + type(value).__name__)


def _normalize_reasons(value: object) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise ArtifactStoreReplayError("rejection_reasons_must_be_sequence")
    reasons = tuple(str(item) for item in value)
    for reason in reasons:
        _require_nonempty_string(reason, "rejection_reason")
    return tuple(_dedupe(reasons))


def _canonical_json(payload: object) -> str:
    return json.dumps(
        _json_ready(payload),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )


def _json_ready(value: object) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_ready(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_json_ready(item) for item in value]
    if isinstance(value, list):
        return [_json_ready(item) for item in value]
    return value


def _sha256_bytes(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return "sha256:" + digest.hexdigest()


def _sha256_json(payload: object) -> str:
    return _sha256_text(_canonical_json(payload))


def _sha256_text(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def _timestamp(value: str | None) -> str:
    if value is None:
        return datetime.now(timezone.utc).isoformat(timespec="microseconds")
    _require_nonempty_string(value, "created_at")
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ArtifactStorePersistenceError("created_at_must_be_isoformat") from exc
    return value


def _require_nonempty_string(value: object, field_name: str) -> None:
    if not isinstance(value, str) or not value:
        raise ArtifactStorePersistenceError(field_name + "_required")


def _require_sha256(value: object, field_name: str) -> None:
    if not isinstance(value, str) or not _SHA256_PATTERN.fullmatch(value):
        raise ArtifactStoreReplayError(field_name + "_must_be_sha256")


def _fsync_parent(path: Path) -> None:
    try:
        fd = os.open(path.parent, os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _dedupe(values: Sequence[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value not in seen:
            result.append(value)
            seen.add(value)
    return tuple(result)
