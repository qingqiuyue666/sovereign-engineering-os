"""Snapshot / replay reconstruction implementation V1.

This module reconstructs deterministic local state from the persisted real WAL,
artifact store, and optional durable queue records. It does not execute work,
repair stores, perform rollback, or open network/provider/browser surfaces.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
from typing import Any, Mapping, Sequence

from kernel.runtime.durable_job_queue import (
    DurableJobQueue,
    DurableJobQueueReplayError,
    DurableJobQueueRecord,
)
from kernel.stores.artifact_store_persistence import (
    ArtifactStorePersistenceRecord,
    ArtifactStoreReplayError,
    FileBackedArtifactStore,
)
from kernel.stores.real_wal_storage import (
    FileBackedRealWalStorage,
    RealWalStorageError,
)
from kernel.stores.real_wal_storage_contract import RealWalStorageRecord
from kernel.stores.snapshot_replay_contract import (
    SNAPSHOT_REPLAY_CONTRACT_VERSION,
    SnapshotManifest,
    validate_snapshot_manifest,
)

__all__ = [
    "SNAPSHOT_REPLAY_INPUT_MANIFEST_VERSION",
    "SNAPSHOT_REPLAY_RECONSTRUCTION_IMPLEMENTATION_VERSION",
    "SNAPSHOT_REPLAY_OUTPUT_RECEIPT_VERSION",
    "SnapshotReplayInputManifest",
    "SnapshotReplayOutputReceipt",
    "SnapshotReplayReconstructionError",
    "FileBackedSnapshotReplayReconstructor",
    "compute_snapshot_replay_input_manifest_hash",
    "compute_snapshot_replay_output_receipt_hash",
]

SNAPSHOT_REPLAY_RECONSTRUCTION_IMPLEMENTATION_VERSION = (
    "snapshot_replay_reconstruction_implementation_v1"
)
SNAPSHOT_REPLAY_INPUT_MANIFEST_VERSION = "snapshot_replay_input_manifest_v1"
SNAPSHOT_REPLAY_OUTPUT_RECEIPT_VERSION = "snapshot_replay_output_receipt_v1"
DEFAULT_ROLLBACK_PLAN_HASH = "sha256:" + hashlib.sha256(
    b"rollback_plan:out_of_scope_for_snapshot_replay_reconstruction_v1"
).hexdigest()
ZERO_HASH = "sha256:" + ("0" * 64)

_SNAPSHOT_KINDS = frozenset({"pre_execution", "post_execution"})
_SHA256_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")
_SECRET_KEY_PATTERN = re.compile(
    r"(?i)(api[_-]?key|auth|authorization|credential|password|private[_-]?key|secret|token)"
)
_SECRET_PATH_PATTERN = re.compile(
    r"(?i)(^\.env$|\.env\.local|\.envrc|credential|id_rsa|id_dsa|id_ed25519|secret|token|password)"
)


class SnapshotReplayReconstructionError(ValueError):
    """Raised when snapshot/replay reconstruction fails closed."""


@dataclass(frozen=True)
class SnapshotReplayInputManifest:
    input_manifest_version: str
    task_id: str
    run_id: str
    snapshot_kind: str
    wal_source_relpath: str
    artifact_store_relpath: str
    queue_source_relpath: str
    queue_id: str
    expected_wal_record_hashes: tuple[str, ...]
    expected_artifact_record_hashes: tuple[str, ...]
    expected_queue_record_hashes: tuple[str, ...]
    expected_snapshot_root_hash: str
    created_at: str
    input_manifest_hash: str = ""

    def __post_init__(self) -> None:
        if self.input_manifest_version != SNAPSHOT_REPLAY_INPUT_MANIFEST_VERSION:
            raise SnapshotReplayReconstructionError("input_manifest_version_invalid")
        _require_nonempty_string(self.task_id, "task_id")
        _require_nonempty_string(self.run_id, "run_id")
        if self.snapshot_kind not in _SNAPSHOT_KINDS:
            raise SnapshotReplayReconstructionError("snapshot_kind_invalid")
        _validate_relpath_text(
            self.wal_source_relpath,
            "wal_source_relpath",
            allow_empty=False,
        )
        _validate_relpath_text(
            self.artifact_store_relpath,
            "artifact_store_relpath",
            allow_empty=True,
        )
        _validate_relpath_text(
            self.queue_source_relpath,
            "queue_source_relpath",
            allow_empty=True,
        )
        if bool(self.queue_source_relpath) != bool(self.queue_id):
            raise SnapshotReplayReconstructionError("queue_source_requires_queue_id")
        if self.queue_id:
            _require_nonempty_string(self.queue_id, "queue_id")
        object.__setattr__(
            self,
            "expected_wal_record_hashes",
            _normalize_digest_tuple(
                self.expected_wal_record_hashes,
                "expected_wal_record_hashes",
                require_nonempty=True,
            ),
        )
        object.__setattr__(
            self,
            "expected_artifact_record_hashes",
            _normalize_digest_tuple(
                self.expected_artifact_record_hashes,
                "expected_artifact_record_hashes",
            ),
        )
        object.__setattr__(
            self,
            "expected_queue_record_hashes",
            _normalize_digest_tuple(
                self.expected_queue_record_hashes,
                "expected_queue_record_hashes",
            ),
        )
        _require_sha256(
            self.expected_snapshot_root_hash,
            "expected_snapshot_root_hash",
        )
        _require_nonempty_string(self.created_at, "created_at")
        if self.input_manifest_hash:
            _require_sha256(self.input_manifest_hash, "input_manifest_hash")
        expected = compute_snapshot_replay_input_manifest_hash(self)
        if self.input_manifest_hash and self.input_manifest_hash != expected:
            raise SnapshotReplayReconstructionError("input_manifest_hash_mismatch")
        object.__setattr__(self, "input_manifest_hash", expected)

    def as_dict(self) -> dict[str, object]:
        return _json_ready(asdict(self))


@dataclass(frozen=True)
class SnapshotReplayOutputReceipt:
    output_receipt_version: str
    accepted: bool
    failures: tuple[str, ...]
    task_id: str
    run_id: str
    input_manifest_hash: str
    expected_snapshot_root_hash: str
    observed_snapshot_root_hash: str
    snapshot_id: str
    snapshot_manifest_hash: str
    snapshot_manifest_relpath: str
    observed_at: str
    receipt_hash: str = ""

    def __post_init__(self) -> None:
        if self.output_receipt_version != SNAPSHOT_REPLAY_OUTPUT_RECEIPT_VERSION:
            raise SnapshotReplayReconstructionError("output_receipt_version_invalid")
        if not isinstance(self.accepted, bool):
            raise SnapshotReplayReconstructionError("accepted_must_be_bool")
        object.__setattr__(self, "failures", _normalize_failures(self.failures))
        if self.accepted and self.failures:
            raise SnapshotReplayReconstructionError(
                "accepted_receipt_cannot_have_failures"
            )
        if not self.accepted and not self.failures:
            raise SnapshotReplayReconstructionError(
                "rejected_receipt_requires_failures"
            )
        _require_nonempty_string(self.task_id, "task_id")
        _require_nonempty_string(self.run_id, "run_id")
        _require_nonempty_string(self.snapshot_id, "snapshot_id")
        for field_name in (
            "input_manifest_hash",
            "expected_snapshot_root_hash",
            "observed_snapshot_root_hash",
            "snapshot_manifest_hash",
        ):
            _require_sha256(getattr(self, field_name), field_name)
        if self.accepted:
            _validate_relpath_text(
                self.snapshot_manifest_relpath,
                "snapshot_manifest_relpath",
                allow_empty=False,
            )
            if self.snapshot_manifest_hash == ZERO_HASH:
                raise SnapshotReplayReconstructionError(
                    "accepted_receipt_requires_snapshot_manifest_hash"
                )
        elif self.snapshot_manifest_relpath:
            _validate_relpath_text(
                self.snapshot_manifest_relpath,
                "snapshot_manifest_relpath",
                allow_empty=False,
            )
        _require_nonempty_string(self.observed_at, "observed_at")
        if self.receipt_hash:
            _require_sha256(self.receipt_hash, "receipt_hash")
        expected = compute_snapshot_replay_output_receipt_hash(self)
        if self.receipt_hash and self.receipt_hash != expected:
            raise SnapshotReplayReconstructionError("receipt_hash_mismatch")
        object.__setattr__(self, "receipt_hash", expected)

    def as_dict(self) -> dict[str, object]:
        return _json_ready(asdict(self))


@dataclass(frozen=True)
class _CollectedState:
    failures: tuple[str, ...]
    wal_record_hashes: tuple[str, ...]
    artifact_record_hashes: tuple[str, ...]
    queue_record_hashes: tuple[str, ...]
    snapshot_root_hash: str
    wal_source_hash: str
    artifact_source_hash: str
    queue_source_hash: str
    last_wal_record_hash: str
    changed_path_digests: tuple[tuple[str, str], ...]
    identities: tuple[tuple[str, str, str], ...]


class FileBackedSnapshotReplayReconstructor:
    """Deterministic local snapshot/replay reconstructor over persisted stores."""

    def __init__(
        self,
        *,
        runtime_root: str | Path,
        wal_source_relpath: str,
        artifact_store_relpath: str | None = None,
        queue_source_relpath: str | None = None,
        queue_id: str | None = None,
        snapshot_store_relpath: str = "snapshot-replay",
        artifact_store_id: str = "artifact-store-persistence-v1",
    ) -> None:
        self.runtime_root = _validate_runtime_root(Path(runtime_root))
        self.wal_source_relpath = _validate_relpath_text(
            wal_source_relpath,
            "wal_source_relpath",
            allow_empty=False,
        )
        self.artifact_store_relpath = _validate_relpath_text(
            artifact_store_relpath or "",
            "artifact_store_relpath",
            allow_empty=True,
        )
        self.queue_source_relpath = _validate_relpath_text(
            queue_source_relpath or "",
            "queue_source_relpath",
            allow_empty=True,
        )
        self.queue_id = queue_id or ""
        if bool(self.queue_source_relpath) != bool(self.queue_id):
            raise SnapshotReplayReconstructionError("queue_source_requires_queue_id")
        if self.queue_id:
            _require_nonempty_string(self.queue_id, "queue_id")
        self.snapshot_store_relpath = _validate_relpath_text(
            snapshot_store_relpath,
            "snapshot_store_relpath",
            allow_empty=False,
        )
        _require_nonempty_string(artifact_store_id, "artifact_store_id")
        self.artifact_store_id = artifact_store_id

    def build_input_manifest(
        self,
        *,
        task_id: str,
        run_id: str,
        snapshot_kind: str = "post_execution",
        created_at: str | None = None,
    ) -> SnapshotReplayInputManifest:
        _require_nonempty_string(task_id, "task_id")
        _require_nonempty_string(run_id, "run_id")
        if snapshot_kind not in _SNAPSHOT_KINDS:
            raise SnapshotReplayReconstructionError("snapshot_kind_invalid")
        state = self._collect_state()
        failures = list(state.failures)
        failures.extend(_identity_failures(state.identities, task_id=task_id, run_id=run_id))
        if failures:
            raise SnapshotReplayReconstructionError(
                "source_replay_rejected:" + ",".join(_dedupe(failures))
            )
        return SnapshotReplayInputManifest(
            input_manifest_version=SNAPSHOT_REPLAY_INPUT_MANIFEST_VERSION,
            task_id=task_id,
            run_id=run_id,
            snapshot_kind=snapshot_kind,
            wal_source_relpath=self.wal_source_relpath,
            artifact_store_relpath=self.artifact_store_relpath,
            queue_source_relpath=self.queue_source_relpath,
            queue_id=self.queue_id,
            expected_wal_record_hashes=state.wal_record_hashes,
            expected_artifact_record_hashes=state.artifact_record_hashes,
            expected_queue_record_hashes=state.queue_record_hashes,
            expected_snapshot_root_hash=state.snapshot_root_hash,
            created_at=_timestamp(created_at),
        )

    def capture_snapshot(
        self,
        *,
        task_id: str,
        run_id: str,
        snapshot_kind: str = "post_execution",
        rollback_plan_hash: str = DEFAULT_ROLLBACK_PLAN_HASH,
        created_at: str | None = None,
        observed_at: str | None = None,
    ) -> SnapshotReplayOutputReceipt:
        input_manifest = self.build_input_manifest(
            task_id=task_id,
            run_id=run_id,
            snapshot_kind=snapshot_kind,
            created_at=created_at,
        )
        return self.replay_and_persist(
            input_manifest,
            rollback_plan_hash=rollback_plan_hash,
            snapshot_created_at=created_at,
            observed_at=observed_at,
        )

    def replay_and_persist(
        self,
        input_manifest: SnapshotReplayInputManifest | Mapping[str, object],
        *,
        rollback_plan_hash: str = DEFAULT_ROLLBACK_PLAN_HASH,
        snapshot_created_at: str | None = None,
        observed_at: str | None = None,
    ) -> SnapshotReplayOutputReceipt:
        manifest, parse_failures = _coerce_input_manifest(input_manifest)
        if manifest is None:
            receipt = self._rejected_receipt_for_invalid_input(
                input_manifest,
                parse_failures=parse_failures,
                observed_at=observed_at,
            )
            self._persist_receipt(receipt)
            return receipt

        _require_sha256(rollback_plan_hash, "rollback_plan_hash")
        state = self._collect_state()
        failures = list(state.failures)
        failures.extend(
            _identity_failures(
                state.identities,
                task_id=manifest.task_id,
                run_id=manifest.run_id,
            )
        )
        failures.extend(
            _compare_hash_sequence(
                "wal",
                manifest.expected_wal_record_hashes,
                state.wal_record_hashes,
            )
        )
        failures.extend(
            _compare_hash_sequence(
                "artifact",
                manifest.expected_artifact_record_hashes,
                state.artifact_record_hashes,
            )
        )
        failures.extend(
            _compare_hash_sequence(
                "queue",
                manifest.expected_queue_record_hashes,
                state.queue_record_hashes,
            )
        )
        if state.snapshot_root_hash != ZERO_HASH and (
            state.snapshot_root_hash != manifest.expected_snapshot_root_hash
        ):
            failures.append("snapshot_root_hash_mismatch")

        if failures:
            receipt = SnapshotReplayOutputReceipt(
                output_receipt_version=SNAPSHOT_REPLAY_OUTPUT_RECEIPT_VERSION,
                accepted=False,
                failures=tuple(_dedupe(failures)),
                task_id=manifest.task_id,
                run_id=manifest.run_id,
                input_manifest_hash=manifest.input_manifest_hash,
                expected_snapshot_root_hash=manifest.expected_snapshot_root_hash,
                observed_snapshot_root_hash=state.snapshot_root_hash,
                snapshot_id="untrusted-replay-rejected",
                snapshot_manifest_hash=ZERO_HASH,
                snapshot_manifest_relpath="",
                observed_at=_timestamp(observed_at),
            )
            self._persist_receipt(receipt)
            return receipt

        snapshot_id = _snapshot_id(state.snapshot_root_hash)
        snapshot_manifest = SnapshotManifest(
            snapshot_manifest_id="snapshot-manifest-" + snapshot_id,
            snapshot_replay_contract_version=SNAPSHOT_REPLAY_CONTRACT_VERSION,
            snapshot_id=snapshot_id,
            snapshot_kind=manifest.snapshot_kind,
            task_id=manifest.task_id,
            run_id=manifest.run_id,
            snapshot_root_hash=state.snapshot_root_hash,
            changed_path_digests=state.changed_path_digests,
            artifact_manifest_hash=state.artifact_source_hash,
            wal_record_hash=state.last_wal_record_hash,
            rollback_plan_hash=rollback_plan_hash,
            created_at=_timestamp(snapshot_created_at),
        )
        validate_snapshot_manifest(snapshot_manifest)
        snapshot_relpath = (
            self.snapshot_store_relpath
            + "/manifests/"
            + snapshot_id
            + ".json"
        )
        try:
            self._persist_input_manifest(manifest)
            self._write_json_atomic_same_ok(
                snapshot_relpath,
                snapshot_manifest.as_dict(),
                equivalence_excluded_keys=("created_at",),
            )
        except SnapshotReplayReconstructionError as exc:
            receipt = SnapshotReplayOutputReceipt(
                output_receipt_version=SNAPSHOT_REPLAY_OUTPUT_RECEIPT_VERSION,
                accepted=False,
                failures=("snapshot_manifest_write_failed:" + str(exc),),
                task_id=manifest.task_id,
                run_id=manifest.run_id,
                input_manifest_hash=manifest.input_manifest_hash,
                expected_snapshot_root_hash=manifest.expected_snapshot_root_hash,
                observed_snapshot_root_hash=state.snapshot_root_hash,
                snapshot_id="untrusted-replay-rejected",
                snapshot_manifest_hash=ZERO_HASH,
                snapshot_manifest_relpath="",
                observed_at=_timestamp(observed_at),
            )
            self._persist_receipt(receipt)
            return receipt

        receipt = SnapshotReplayOutputReceipt(
            output_receipt_version=SNAPSHOT_REPLAY_OUTPUT_RECEIPT_VERSION,
            accepted=True,
            failures=(),
            task_id=manifest.task_id,
            run_id=manifest.run_id,
            input_manifest_hash=manifest.input_manifest_hash,
            expected_snapshot_root_hash=manifest.expected_snapshot_root_hash,
            observed_snapshot_root_hash=state.snapshot_root_hash,
            snapshot_id=snapshot_id,
            snapshot_manifest_hash=snapshot_manifest.manifest_hash,
            snapshot_manifest_relpath=snapshot_relpath,
            observed_at=_timestamp(observed_at),
        )
        self._persist_receipt(receipt)
        return receipt

    def _collect_state(self) -> _CollectedState:
        failures: list[str] = []
        wal_records = self._read_wal_records(failures)
        artifact_records = self._read_artifact_records(failures)
        queue_records = self._read_queue_records(failures)

        identities = tuple(
            sorted(
                (
                    *(
                        ("wal", record.task_id, record.run_id)
                        for record in wal_records
                    ),
                    *(
                        (
                            "artifact",
                            record.manifest.task_id,
                            record.manifest.run_id,
                        )
                        for record in artifact_records
                    ),
                    *(
                        ("queue", record.event.task_id, record.event.run_id)
                        for record in queue_records
                    ),
                )
            )
        )
        wal_hashes = tuple(record.record_hash for record in wal_records)
        artifact_hashes = tuple(record.record_hash for record in artifact_records)
        queue_hashes = tuple(record.record_hash for record in queue_records)
        wal_source_hash = _sha256_json(
            tuple(_wal_record_material(record) for record in wal_records)
        )
        artifact_source_hash = _sha256_json(
            tuple(_artifact_record_material(record) for record in artifact_records)
        )
        queue_source_hash = _sha256_json(
            tuple(_queue_record_material(record) for record in queue_records)
        )
        changed_path_digests = (
            (_source_path_digest("wal", self.wal_source_relpath), wal_source_hash),
            (
                _source_path_digest("artifact", self.artifact_store_relpath),
                artifact_source_hash,
            ),
            (_source_path_digest("queue", self.queue_source_relpath), queue_source_hash),
        )
        if failures:
            snapshot_root_hash = ZERO_HASH
        else:
            snapshot_root_hash = _sha256_json(
                {
                    "artifact_record_hashes": artifact_hashes,
                    "artifact_source_hash": artifact_source_hash,
                    "implementation_version": (
                        SNAPSHOT_REPLAY_RECONSTRUCTION_IMPLEMENTATION_VERSION
                    ),
                    "queue_record_hashes": queue_hashes,
                    "queue_source_hash": queue_source_hash,
                    "wal_record_hashes": wal_hashes,
                    "wal_source_hash": wal_source_hash,
                }
            )
        return _CollectedState(
            failures=tuple(_dedupe(failures)),
            wal_record_hashes=wal_hashes,
            artifact_record_hashes=artifact_hashes,
            queue_record_hashes=queue_hashes,
            snapshot_root_hash=snapshot_root_hash,
            wal_source_hash=wal_source_hash,
            artifact_source_hash=artifact_source_hash,
            queue_source_hash=queue_source_hash,
            last_wal_record_hash=wal_hashes[-1] if wal_hashes else ZERO_HASH,
            changed_path_digests=tuple(sorted(changed_path_digests)),
            identities=identities,
        )

    def _read_wal_records(self, failures: list[str]) -> tuple[RealWalStorageRecord, ...]:
        wal_path = self._resolve_relpath(self.wal_source_relpath, "wal_source_relpath")
        if not wal_path.exists():
            failures.append("wal_file_missing")
            return ()
        if wal_path.is_symlink():
            failures.append("wal_file_is_symlink")
            return ()
        if not wal_path.is_file():
            failures.append("wal_source_not_file")
            return ()
        try:
            return FileBackedRealWalStorage(wal_path).read_records()
        except RealWalStorageError as exc:
            failures.append("wal_replay_rejected:" + str(exc))
            return ()

    def _read_artifact_records(
        self,
        failures: list[str],
    ) -> tuple[ArtifactStorePersistenceRecord, ...]:
        if not self.artifact_store_relpath:
            return ()
        artifact_root = self._resolve_relpath(
            self.artifact_store_relpath,
            "artifact_store_relpath",
        )
        try:
            return FileBackedArtifactStore(
                artifact_root,
                store_id=self.artifact_store_id,
            ).read_records()
        except ArtifactStoreReplayError as exc:
            failures.append("artifact_replay_rejected:" + str(exc))
            return ()

    def _read_queue_records(
        self,
        failures: list[str],
    ) -> tuple[DurableJobQueueRecord, ...]:
        if not self.queue_source_relpath:
            return ()
        queue_path = self._resolve_relpath(
            self.queue_source_relpath,
            "queue_source_relpath",
        )
        try:
            return DurableJobQueue(path=queue_path, queue_id=self.queue_id).records
        except DurableJobQueueReplayError as exc:
            failures.append("queue_replay_rejected:" + str(exc))
            return ()

    def _resolve_relpath(self, relpath: str, field_name: str) -> Path:
        _validate_relpath_text(relpath, field_name, allow_empty=False)
        candidate = self.runtime_root / relpath
        current = self.runtime_root
        for part in PurePosixPath(relpath).parts:
            current = current / part
            if current.exists() and current.is_symlink():
                raise SnapshotReplayReconstructionError(field_name + "_is_symlink")
        resolved = candidate.resolve(strict=False)
        if not resolved.is_relative_to(self.runtime_root):
            raise SnapshotReplayReconstructionError(field_name + "_escapes_runtime_root")
        return resolved

    def _persist_input_manifest(self, manifest: SnapshotReplayInputManifest) -> None:
        relpath = (
            self.snapshot_store_relpath
            + "/inputs/"
            + manifest.input_manifest_hash.removeprefix("sha256:")
            + ".json"
        )
        self._write_json_atomic_same_ok(
            relpath,
            manifest.as_dict(),
            equivalence_excluded_keys=("created_at",),
        )

    def _persist_receipt(self, receipt: SnapshotReplayOutputReceipt) -> None:
        relpath = (
            self.snapshot_store_relpath
            + "/receipts/"
            + receipt.receipt_hash.removeprefix("sha256:")
            + ".json"
        )
        self._write_json_atomic_same_ok(
            relpath,
            receipt.as_dict(),
            equivalence_excluded_keys=("observed_at",),
        )

    def _write_json_atomic_same_ok(
        self,
        relpath: str,
        payload: Mapping[str, object],
        *,
        equivalence_excluded_keys: tuple[str, ...] = (),
    ) -> None:
        path = self._resolve_relpath(relpath, "snapshot_write_relpath")
        data = (_canonical_json(payload) + "\n").encode("utf-8")
        if path.exists():
            if path.is_symlink():
                raise SnapshotReplayReconstructionError("snapshot_write_target_is_symlink")
            if not path.is_file():
                raise SnapshotReplayReconstructionError("snapshot_write_target_not_file")
            if path.read_bytes() == data:
                return
            if equivalence_excluded_keys and _same_except_keys(
                path,
                payload,
                equivalence_excluded_keys,
            ):
                return
            raise SnapshotReplayReconstructionError("snapshot_write_target_mismatch")
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.parent.is_symlink():
            raise SnapshotReplayReconstructionError("snapshot_write_parent_is_symlink")
        temp_path = path.with_name(
            "." + path.name + ".tmp-" + _sha256_bytes(data).removeprefix("sha256:")[:16]
        )
        fd = os.open(temp_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        try:
            written = 0
            while written < len(data):
                count = os.write(fd, data[written:])
                if count <= 0:
                    raise SnapshotReplayReconstructionError("snapshot_write_failed")
                written += count
            os.fsync(fd)
        finally:
            os.close(fd)
        try:
            if path.exists():
                raise SnapshotReplayReconstructionError("snapshot_write_target_exists")
            temp_path.rename(path)
            _fsync_parent(path)
        except Exception:
            try:
                temp_path.unlink()
            except OSError:
                pass
            raise

    def _rejected_receipt_for_invalid_input(
        self,
        input_manifest: SnapshotReplayInputManifest | Mapping[str, object],
        *,
        parse_failures: tuple[str, ...],
        observed_at: str | None,
    ) -> SnapshotReplayOutputReceipt:
        raw = _json_ready(dict(input_manifest)) if isinstance(input_manifest, Mapping) else {}
        input_hash = _safe_input_hash(raw)
        return SnapshotReplayOutputReceipt(
            output_receipt_version=SNAPSHOT_REPLAY_OUTPUT_RECEIPT_VERSION,
            accepted=False,
            failures=tuple("input_manifest_invalid:" + failure for failure in parse_failures),
            task_id=_safe_identity(raw, "task_id"),
            run_id=_safe_identity(raw, "run_id"),
            input_manifest_hash=input_hash,
            expected_snapshot_root_hash=_safe_digest(raw, "expected_snapshot_root_hash"),
            observed_snapshot_root_hash=ZERO_HASH,
            snapshot_id="untrusted-replay-rejected",
            snapshot_manifest_hash=ZERO_HASH,
            snapshot_manifest_relpath="",
            observed_at=_timestamp(observed_at),
        )


def compute_snapshot_replay_input_manifest_hash(
    manifest: SnapshotReplayInputManifest | Mapping[str, object],
) -> str:
    data = _manifest_dict(manifest)
    data.pop("input_manifest_hash", None)
    data.pop("created_at", None)
    return _sha256_json(data)


def compute_snapshot_replay_output_receipt_hash(
    receipt: SnapshotReplayOutputReceipt | Mapping[str, object],
) -> str:
    data = _receipt_dict(receipt)
    data.pop("receipt_hash", None)
    data.pop("observed_at", None)
    return _sha256_json(data)


def _coerce_input_manifest(
    value: SnapshotReplayInputManifest | Mapping[str, object],
) -> tuple[SnapshotReplayInputManifest | None, tuple[str, ...]]:
    if isinstance(value, SnapshotReplayInputManifest):
        return value, ()
    if not isinstance(value, Mapping):
        return None, ("input_manifest_must_be_mapping",)
    try:
        return SnapshotReplayInputManifest(**dict(value)), ()
    except (TypeError, ValueError) as exc:
        return None, (str(exc),)


def _compare_hash_sequence(
    label: str,
    expected: tuple[str, ...],
    observed: tuple[str, ...],
) -> tuple[str, ...]:
    if expected == observed:
        return ()
    failures: list[str] = []
    expected_set = set(expected)
    observed_set = set(observed)
    if sorted(expected) == sorted(observed):
        failures.append(label + "_non_deterministic_ordering")
    missing = tuple(item for item in expected if item not in observed_set)
    extra = tuple(item for item in observed if item not in expected_set)
    if missing:
        failures.append(label + "_record_missing")
    if extra:
        failures.append(label + "_unexpected_record")
    if not missing and not extra:
        failures.append(label + "_record_hash_mismatch")
    return tuple(failures)


def _identity_failures(
    identities: Sequence[tuple[str, str, str]],
    *,
    task_id: str,
    run_id: str,
) -> tuple[str, ...]:
    failures: list[str] = []
    for source, observed_task_id, observed_run_id in identities:
        if observed_task_id != task_id or observed_run_id != run_id:
            failures.append(source + "_identity_mismatch")
    return tuple(_dedupe(failures))


def _wal_record_material(record: RealWalStorageRecord) -> dict[str, object]:
    return {
        "digest_bindings": list(record.digest_bindings),
        "payload_hash": record.payload_hash,
        "previous_hash": record.previous_hash,
        "record_hash": record.record_hash,
        "record_type": record.record_type,
        "run_id": record.run_id,
        "sequence": record.sequence,
        "task_id": record.task_id,
        "wal_record_id": record.wal_record_id,
        "wal_storage_contract_version": record.wal_storage_contract_version,
    }


def _artifact_record_material(record: ArtifactStorePersistenceRecord) -> dict[str, object]:
    return {
        "artifact_id": record.manifest.artifact_id,
        "artifact_manifest_id": record.manifest.artifact_manifest_id,
        "artifact_record_version": record.artifact_record_version,
        "content_sha256": record.manifest.content_sha256,
        "manifest_hash": record.manifest.manifest_hash,
        "metadata_hash": _sha256_json(record.metadata),
        "previous_record_hash": record.previous_record_hash,
        "record_hash": record.record_hash,
        "run_id": record.manifest.run_id,
        "sequence": record.sequence,
        "store_id": record.store_id,
        "task_id": record.manifest.task_id,
        "wal_record_hash": record.manifest.wal_record_hash,
    }


def _queue_record_material(record: DurableJobQueueRecord) -> dict[str, object]:
    return {
        "event_hash": record.event.event_hash,
        "event_type": record.event.event_type,
        "job_id": record.event.job_id,
        "payload_hash": record.event.payload_hash,
        "queue_event_id": record.event.queue_event_id,
        "queue_id": record.queue_id,
        "queue_record_version": record.queue_record_version,
        "record_hash": record.record_hash,
        "run_id": record.event.run_id,
        "sequence": record.event.sequence,
        "task_id": record.event.task_id,
        "wal_record_hash": record.event.wal_record_hash,
    }


def _manifest_dict(
    manifest: SnapshotReplayInputManifest | Mapping[str, object],
) -> dict[str, object]:
    if isinstance(manifest, SnapshotReplayInputManifest):
        return manifest.as_dict()
    return _json_ready(dict(manifest))


def _receipt_dict(
    receipt: SnapshotReplayOutputReceipt | Mapping[str, object],
) -> dict[str, object]:
    if isinstance(receipt, SnapshotReplayOutputReceipt):
        return receipt.as_dict()
    return _json_ready(dict(receipt))


def _safe_input_hash(payload: Mapping[str, object]) -> str:
    try:
        return _sha256_json(payload)
    except SnapshotReplayReconstructionError:
        return ZERO_HASH


def _safe_digest(payload: Mapping[str, object], field_name: str) -> str:
    value = payload.get(field_name)
    if isinstance(value, str) and _SHA256_PATTERN.fullmatch(value):
        return value
    return ZERO_HASH


def _safe_identity(payload: Mapping[str, object], field_name: str) -> str:
    value = payload.get(field_name)
    if isinstance(value, str) and value:
        if _SECRET_KEY_PATTERN.search(value):
            return "unknown"
        return value
    return "unknown"


def _same_except_keys(
    path: Path,
    payload: Mapping[str, object],
    excluded_keys: tuple[str, ...],
) -> bool:
    try:
        existing = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    if not isinstance(existing, Mapping):
        return False
    existing_payload = dict(existing)
    candidate_payload = dict(payload)
    for key in excluded_keys:
        existing_payload.pop(key, None)
        candidate_payload.pop(key, None)
    return _canonical_json(existing_payload) == _canonical_json(candidate_payload)


def _snapshot_id(snapshot_root_hash: str) -> str:
    _require_sha256(snapshot_root_hash, "snapshot_root_hash")
    return "snapshot-" + snapshot_root_hash.removeprefix("sha256:")[:32]


def _source_path_digest(label: str, relpath: str) -> str:
    return _sha256_json({"source": label, "source_relpath": relpath})


def _validate_runtime_root(root: Path) -> Path:
    raw = root.expanduser()
    if not str(raw):
        raise SnapshotReplayReconstructionError("runtime_root_required")
    if raw.exists() and raw.is_symlink():
        raise SnapshotReplayReconstructionError("runtime_root_is_symlink")
    if raw.exists() and not raw.is_dir():
        raise SnapshotReplayReconstructionError("runtime_root_must_be_directory")
    resolved = raw.resolve(strict=False)
    _reject_secret_or_git_path(resolved, "runtime_root")
    return resolved


def _validate_relpath_text(value: str, field_name: str, *, allow_empty: bool) -> str:
    if not isinstance(value, str):
        raise SnapshotReplayReconstructionError(field_name + "_must_be_string")
    if not value:
        if allow_empty:
            return ""
        raise SnapshotReplayReconstructionError(field_name + "_required")
    if "\\" in value:
        raise SnapshotReplayReconstructionError(field_name + "_must_use_posix_separators")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts:
        raise SnapshotReplayReconstructionError(field_name + "_must_be_relative")
    _reject_secret_or_git_path(Path(*path.parts), field_name)
    return str(path)


def _reject_secret_or_git_path(path: Path, field_name: str) -> None:
    if ".git" in path.parts:
        raise SnapshotReplayReconstructionError(field_name + "_cannot_enter_git")
    if any(_SECRET_PATH_PATTERN.fullmatch(part) for part in path.parts):
        raise SnapshotReplayReconstructionError(field_name + "_secret_like")


def _normalize_digest_tuple(
    value: object,
    field_name: str,
    *,
    require_nonempty: bool = False,
) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise SnapshotReplayReconstructionError(field_name + "_must_be_sequence")
    normalized = tuple(str(item) for item in value)
    if require_nonempty and not normalized:
        raise SnapshotReplayReconstructionError(field_name + "_required")
    seen: set[str] = set()
    for item in normalized:
        _require_sha256(item, field_name)
        if item in seen:
            raise SnapshotReplayReconstructionError(field_name + "_duplicate")
        seen.add(item)
    return normalized


def _normalize_failures(value: object) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise SnapshotReplayReconstructionError("failures_must_be_sequence")
    failures = tuple(str(item) for item in value)
    for failure in failures:
        _require_nonempty_string(failure, "failure")
    return tuple(_dedupe(failures))


def _timestamp(value: str | None) -> str:
    if value is None:
        return datetime.now(timezone.utc).isoformat(timespec="microseconds")
    _require_nonempty_string(value, "timestamp")
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise SnapshotReplayReconstructionError("timestamp_must_be_isoformat") from exc
    return value


def _require_nonempty_string(value: object, field_name: str) -> None:
    if not isinstance(value, str) or not value:
        raise SnapshotReplayReconstructionError(field_name + "_required")


def _require_sha256(value: object, field_name: str) -> None:
    if not isinstance(value, str) or not _SHA256_PATTERN.fullmatch(value):
        raise SnapshotReplayReconstructionError(field_name + "_must_be_sha256")


def _canonical_json(payload: object) -> str:
    return json.dumps(
        _json_ready(payload),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )


def _json_ready(value: object) -> Any:
    if isinstance(value, Mapping):
        result: dict[str, object] = {}
        for key, item in value.items():
            key_text = str(key)
            if _SECRET_KEY_PATTERN.search(key_text):
                raise SnapshotReplayReconstructionError(
                    "json_field_secret_like:" + key_text
                )
            result[key_text] = _json_ready(item)
        return result
    if isinstance(value, tuple):
        return [_json_ready(item) for item in value]
    if isinstance(value, list):
        return [_json_ready(item) for item in value]
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    raise SnapshotReplayReconstructionError(
        "json_value_type_forbidden:" + type(value).__name__
    )


def _sha256_json(payload: object) -> str:
    return _sha256_text(_canonical_json(payload))


def _sha256_text(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def _sha256_bytes(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


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
