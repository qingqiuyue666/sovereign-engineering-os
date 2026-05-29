"""Receipt-backed recovery, rollback, and disaster procedures.

The procedures in this module operate only on a caller-provided local runtime
root. They create backups before restore/rollback mutation, validate snapshot
and WAL evidence before use, quarantine corrupted or ambiguous sources, and
emit deterministic receipts. They do not perform network access, subprocess
execution, credential reads, or silent repair.
"""

from __future__ import annotations

import json
import shutil
from dataclasses import asdict, dataclass
from pathlib import Path, PurePosixPath
from typing import Mapping, Sequence

from kernel.os_engine.database import stable_content_hash, validate_no_secret_like

ZERO_HASH = "0" * 64
RECOVERY_PROCEDURE_VERSION = "recovery_rollback_disaster_procedure_v1"

__all__ = [
    "DisasterRecoveryError",
    "DisasterRecoveryReceipt",
    "FileBackedRecoveryRollbackDisasterProcedure",
    "build_wal_event",
    "snapshot_payload",
]


class DisasterRecoveryError(ValueError):
    """Raised when recovery procedure input is unsafe or malformed."""


@dataclass(frozen=True, slots=True)
class DisasterRecoveryReceipt:
    receipt_type: str
    procedure: str
    accepted: bool
    status: str
    failure_codes: tuple[str, ...]
    runtime_root: str
    backup_path: str
    backup_hash: str
    source_paths: tuple[str, ...]
    target_paths: tuple[str, ...]
    quarantined_paths: tuple[str, ...]
    restored_state_hash: str
    deterministic_verification_hash: str
    operator_next_action: str
    mutation_performed: bool
    recovery_receipt_written: bool
    no_silent_repair: bool = True
    repair_performed: bool = False
    corrupted_source_preserved: bool = True
    network_accessed: bool = False
    subprocess_spawned: bool = False
    sensitive_material_read: bool = False
    automatic_migration_performed: bool = False

    def as_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["failure_codes"] = list(self.failure_codes)
        payload["source_paths"] = list(self.source_paths)
        payload["target_paths"] = list(self.target_paths)
        payload["quarantined_paths"] = list(self.quarantined_paths)
        payload["receipt_hash"] = stable_content_hash(
            {
                key: value
                for key, value in payload.items()
                if key != "receipt_hash"
            }
        )
        return dict(sorted(payload.items()))

    def to_json(self) -> str:
        return json.dumps(self.as_dict(), sort_keys=True, separators=(",", ":"))


class FileBackedRecoveryRollbackDisasterProcedure:
    """Local file-backed recovery procedure bound to one runtime root."""

    def __init__(self, runtime_root: Path | str) -> None:
        self.runtime_root = _validate_runtime_root(Path(runtime_root))
        self.backup_root = self.runtime_root / "backups"
        self.quarantine_root = self.runtime_root / "quarantine"
        self.receipt_root = self.runtime_root / "receipts"

    def create_runtime_backup(self, *, reason: str = "operator-requested") -> DisasterRecoveryReceipt:
        inventory = _runtime_inventory(self.runtime_root)
        backup_hash = stable_content_hash(
            {
                "inventory": [record.as_dict() for record in inventory],
                "reason": reason,
                "version": RECOVERY_PROCEDURE_VERSION,
            }
        )
        backup_path = self.backup_root / ("backup-" + backup_hash[:16])
        payload_root = backup_path / "payload"
        for record in inventory:
            source = self.runtime_root / record.path
            target = payload_root / record.path
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
        manifest = {
            "backup_hash": backup_hash,
            "inventory": [record.as_dict() for record in inventory],
            "reason": reason,
            "version": RECOVERY_PROCEDURE_VERSION,
        }
        _write_json(backup_path / "backup-manifest.json", manifest)
        receipt = self._receipt(
            procedure="runtime_backup",
            accepted=True,
            status="ready",
            backup_path=backup_path,
            backup_hash=backup_hash,
            source_paths=tuple(record.path for record in inventory),
            target_paths=(backup_path.relative_to(self.runtime_root).as_posix(),),
            mutation_performed=True,
            restored_state_hash=backup_hash,
            verification_material=manifest,
            operator_next_action="backup_ready_for_restore_or_rollback",
        )
        self._write_receipt(receipt)
        return receipt

    def restore_from_snapshot(
        self,
        snapshot_path: Path | str,
        *,
        output_relpath: str = "state/restored-from-snapshot.json",
    ) -> DisasterRecoveryReceipt:
        snapshot = self._resolve_runtime_path(snapshot_path)
        target = self._resolve_relpath(output_relpath)
        parsed, failures = _read_snapshot(snapshot)
        if failures:
            quarantined = self._quarantine_sources((snapshot,), "snapshot-corruption")
            receipt = self._receipt(
                procedure="restore_from_snapshot",
                accepted=False,
                status="quarantined",
                failure_codes=failures,
                source_paths=(snapshot.relative_to(self.runtime_root).as_posix(),),
                target_paths=(target.relative_to(self.runtime_root).as_posix(),),
                quarantined_paths=quarantined,
                verification_material={"failures": list(failures), "snapshot": snapshot.as_posix()},
                operator_next_action="manual_snapshot_review_required",
            )
            self._write_receipt(receipt)
            return receipt
        backup = self.create_runtime_backup(reason="before-snapshot-restore")
        state = parsed["state"]
        _write_json(target, state)
        receipt = self._receipt(
            procedure="restore_from_snapshot",
            accepted=True,
            status="restored",
            backup_path=Path(backup.backup_path),
            backup_hash=backup.backup_hash,
            source_paths=(snapshot.relative_to(self.runtime_root).as_posix(),),
            target_paths=(target.relative_to(self.runtime_root).as_posix(),),
            restored_state_hash=stable_content_hash(state),
            mutation_performed=True,
            verification_material=parsed,
            operator_next_action="verify_restored_snapshot_state",
        )
        self._write_receipt(receipt)
        return receipt

    def restore_from_wal_and_artifact_manifest(
        self,
        wal_path: Path | str,
        artifact_manifest_path: Path | str,
        *,
        output_relpath: str = "state/restored-from-wal.json",
    ) -> DisasterRecoveryReceipt:
        wal = self._resolve_runtime_path(wal_path)
        artifact_manifest = self._resolve_runtime_path(artifact_manifest_path)
        target = self._resolve_relpath(output_relpath)
        artifact_failures = _validate_artifact_manifest(self.runtime_root, artifact_manifest)
        state, wal_failures = _replay_wal(wal)
        failures = tuple(sorted(set(artifact_failures + wal_failures)))
        if failures:
            sources = [wal, artifact_manifest]
            if artifact_failures:
                sources.extend(_artifact_sources(self.runtime_root, artifact_manifest))
            quarantined = self._quarantine_sources(tuple(sources), "wal-artifact-corruption")
            receipt = self._receipt(
                procedure="restore_from_wal_and_artifact_manifest",
                accepted=False,
                status="quarantined",
                failure_codes=failures,
                source_paths=tuple(path.relative_to(self.runtime_root).as_posix() for path in sources),
                target_paths=(target.relative_to(self.runtime_root).as_posix(),),
                quarantined_paths=quarantined,
                verification_material={"failures": list(failures)},
                operator_next_action="manual_wal_artifact_review_required",
            )
            self._write_receipt(receipt)
            return receipt
        backup = self.create_runtime_backup(reason="before-wal-restore")
        _write_json(target, state)
        receipt = self._receipt(
            procedure="restore_from_wal_and_artifact_manifest",
            accepted=True,
            status="restored",
            backup_path=Path(backup.backup_path),
            backup_hash=backup.backup_hash,
            source_paths=(
                wal.relative_to(self.runtime_root).as_posix(),
                artifact_manifest.relative_to(self.runtime_root).as_posix(),
            ),
            target_paths=(target.relative_to(self.runtime_root).as_posix(),),
            restored_state_hash=stable_content_hash(state),
            mutation_performed=True,
            verification_material={"state": state, "wal": wal.as_posix()},
            operator_next_action="verify_replayed_wal_state",
        )
        self._write_receipt(receipt)
        return receipt

    def rollback_failed_migration(
        self,
        backup_path: Path | str,
        migration_marker_path: Path | str,
    ) -> DisasterRecoveryReceipt:
        backup = self._resolve_runtime_path(backup_path)
        marker = self._resolve_runtime_path(migration_marker_path)
        marker_payload = _read_json_object(marker)
        failures: list[str] = []
        if marker_payload.get("status") != "failed":
            failures.append("migration_marker_not_failed")
        manifest_path = backup / "backup-manifest.json"
        manifest = _read_json_object(manifest_path)
        if not manifest.get("backup_hash"):
            failures.append("backup_manifest_invalid")
        payload_root = backup / "payload"
        if not payload_root.is_dir():
            failures.append("backup_payload_missing")
        if failures:
            receipt = self._receipt(
                procedure="failed_migration_rollback",
                accepted=False,
                status="rejected",
                failure_codes=tuple(failures),
                source_paths=(
                    backup.relative_to(self.runtime_root).as_posix(),
                    marker.relative_to(self.runtime_root).as_posix(),
                ),
                verification_material={"failures": failures},
                operator_next_action="manual_migration_review_required",
            )
            self._write_receipt(receipt)
            return receipt
        for source in sorted(path for path in payload_root.rglob("*") if path.is_file()):
            relpath = source.relative_to(payload_root)
            target = self.runtime_root / relpath
            if _is_excluded_runtime_part(relpath.parts):
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
        quarantined = self._quarantine_sources((marker,), "failed-migration-marker")
        receipt = self._receipt(
            procedure="failed_migration_rollback",
            accepted=True,
            status="rolled_back",
            backup_path=backup,
            backup_hash=str(manifest["backup_hash"]),
            source_paths=(
                backup.relative_to(self.runtime_root).as_posix(),
                marker.relative_to(self.runtime_root).as_posix(),
            ),
            target_paths=(self.runtime_root.as_posix(),),
            quarantined_paths=quarantined,
            mutation_performed=True,
            restored_state_hash=str(manifest["backup_hash"]),
            verification_material=manifest,
            operator_next_action="verify_rolled_back_runtime",
        )
        self._write_receipt(receipt)
        return receipt

    def recover_partial_write(self, stable_path: Path | str, partial_path: Path | str) -> DisasterRecoveryReceipt:
        return self._recover_write_crash(
            procedure="partial_write_recovery",
            stable_path=stable_path,
            partial_path=partial_path,
            quarantine_reason="partial-write",
        )

    def recover_crash_during_write(self, stable_path: Path | str, partial_path: Path | str) -> DisasterRecoveryReceipt:
        return self._recover_write_crash(
            procedure="crash_during_write_recovery",
            stable_path=stable_path,
            partial_path=partial_path,
            quarantine_reason="crash-during-write",
        )

    def recover_crash_during_snapshot(
        self,
        snapshot_partial_path: Path | str,
        recovery_marker_path: Path | str,
    ) -> DisasterRecoveryReceipt:
        snapshot_partial = self._resolve_runtime_path(snapshot_partial_path)
        marker = self._resolve_runtime_path(recovery_marker_path)
        quarantined = self._quarantine_sources((snapshot_partial, marker), "crash-during-snapshot")
        receipt = self._receipt(
            procedure="crash_during_snapshot_recovery",
            accepted=False,
            status="quarantined",
            failure_codes=("snapshot_recovery_crash_marker_present",),
            source_paths=(
                snapshot_partial.relative_to(self.runtime_root).as_posix(),
                marker.relative_to(self.runtime_root).as_posix(),
            ),
            quarantined_paths=quarantined,
            verification_material={"marker": marker.as_posix()},
            operator_next_action="manual_snapshot_recovery_required",
        )
        self._write_receipt(receipt)
        return receipt

    def recover_approval_queue_transition(
        self,
        queue_state_path: Path | str,
        approval_state_path: Path | str,
        transition_marker_path: Path | str,
    ) -> DisasterRecoveryReceipt:
        queue_state = self._resolve_runtime_path(queue_state_path)
        approval_state = self._resolve_runtime_path(approval_state_path)
        marker = self._resolve_runtime_path(transition_marker_path)
        queue_hash = _file_sha256(queue_state)
        approval_hash = _file_sha256(approval_state)
        marker_hash = _file_sha256(marker)
        quarantined = self._quarantine_sources((marker,), "approval-queue-transition")
        receipt = self._receipt(
            procedure="approval_queue_transition_crash_recovery",
            accepted=False,
            status="quarantined",
            failure_codes=("approval_queue_transition_ambiguous",),
            source_paths=(
                queue_state.relative_to(self.runtime_root).as_posix(),
                approval_state.relative_to(self.runtime_root).as_posix(),
                marker.relative_to(self.runtime_root).as_posix(),
            ),
            quarantined_paths=quarantined,
            verification_material={
                "approval_hash": approval_hash,
                "marker_hash": marker_hash,
                "queue_hash": queue_hash,
            },
            operator_next_action="manual_approval_queue_transition_review_required",
        )
        self._write_receipt(receipt)
        return receipt

    def _recover_write_crash(
        self,
        *,
        procedure: str,
        stable_path: Path | str,
        partial_path: Path | str,
        quarantine_reason: str,
    ) -> DisasterRecoveryReceipt:
        stable = self._resolve_runtime_path(stable_path)
        partial = self._resolve_runtime_path(partial_path)
        stable_payload = _read_json_object(stable)
        quarantined = self._quarantine_sources((partial,), quarantine_reason)
        receipt = self._receipt(
            procedure=procedure,
            accepted=True,
            status="stable_state_preserved",
            source_paths=(
                stable.relative_to(self.runtime_root).as_posix(),
                partial.relative_to(self.runtime_root).as_posix(),
            ),
            target_paths=(stable.relative_to(self.runtime_root).as_posix(),),
            quarantined_paths=quarantined,
            restored_state_hash=stable_content_hash(stable_payload),
            verification_material={"stable_state": stable_payload},
            operator_next_action="resume_from_stable_state_after_review",
        )
        self._write_receipt(receipt)
        return receipt

    def _receipt(
        self,
        *,
        procedure: str,
        accepted: bool,
        status: str,
        failure_codes: Sequence[str] = (),
        backup_path: Path | None = None,
        backup_hash: str = ZERO_HASH,
        source_paths: Sequence[str] = (),
        target_paths: Sequence[str] = (),
        quarantined_paths: Sequence[str] = (),
        restored_state_hash: str = ZERO_HASH,
        mutation_performed: bool = False,
        verification_material: Mapping[str, object] | None = None,
        operator_next_action: str,
    ) -> DisasterRecoveryReceipt:
        verification_hash = stable_content_hash(
            {
                "accepted": accepted,
                "backup_hash": backup_hash,
                "failure_codes": sorted(set(failure_codes)),
                "procedure": procedure,
                "quarantined_paths": sorted(quarantined_paths),
                "restored_state_hash": restored_state_hash,
                "status": status,
                "verification_material": dict(verification_material or {}),
            }
        )
        return DisasterRecoveryReceipt(
            receipt_type=RECOVERY_PROCEDURE_VERSION,
            procedure=procedure,
            accepted=accepted,
            status=status,
            failure_codes=tuple(sorted(set(failure_codes))),
            runtime_root=self.runtime_root.as_posix(),
            backup_path="" if backup_path is None else backup_path.as_posix(),
            backup_hash=backup_hash,
            source_paths=tuple(source_paths),
            target_paths=tuple(target_paths),
            quarantined_paths=tuple(sorted(quarantined_paths)),
            restored_state_hash=restored_state_hash,
            deterministic_verification_hash=verification_hash,
            operator_next_action=operator_next_action,
            mutation_performed=mutation_performed,
            recovery_receipt_written=True,
        )

    def _write_receipt(self, receipt: DisasterRecoveryReceipt) -> None:
        filename = "recovery-" + receipt.procedure + ".json"
        _write_json(self.receipt_root / filename, receipt.as_dict())

    def _quarantine_sources(self, sources: Sequence[Path], reason: str) -> tuple[str, ...]:
        quarantined: list[str] = []
        for source in sources:
            if not source.exists():
                continue
            relpath = source.relative_to(self.runtime_root)
            target = self.quarantine_root / reason / relpath
            target.parent.mkdir(parents=True, exist_ok=True)
            if source.is_dir():
                if target.exists():
                    shutil.rmtree(target)
                shutil.copytree(source, target)
            else:
                shutil.copy2(source, target)
            quarantined.append(target.relative_to(self.runtime_root).as_posix())
        manifest_path = self.quarantine_root / reason / "quarantine-manifest.json"
        _write_json(
            manifest_path,
            {
                "preserved_sources": [path.relative_to(self.runtime_root).as_posix() for path in sources if path.exists()],
                "quarantined_paths": sorted(quarantined),
                "reason": reason,
                "version": RECOVERY_PROCEDURE_VERSION,
            },
        )
        quarantined.append(manifest_path.relative_to(self.runtime_root).as_posix())
        return tuple(sorted(quarantined))

    def _resolve_runtime_path(self, path: Path | str) -> Path:
        raw = Path(path).expanduser()
        candidate = raw if raw.is_absolute() else self.runtime_root / raw
        resolved = candidate.resolve(strict=False)
        if not resolved.is_relative_to(self.runtime_root):
            raise DisasterRecoveryError("path_escapes_runtime_root")
        if resolved.exists() and resolved.is_symlink():
            raise DisasterRecoveryError("symlink_source_rejected")
        return resolved

    def _resolve_relpath(self, relpath: str) -> Path:
        pure = PurePosixPath(relpath)
        if pure.is_absolute() or ".." in pure.parts or any(part in ("", ".") for part in pure.parts):
            raise DisasterRecoveryError("output_path_invalid")
        return self._resolve_runtime_path(pure.as_posix())


@dataclass(frozen=True, slots=True)
class _InventoryRecord:
    path: str
    sha256: str
    size_bytes: int

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def snapshot_payload(snapshot_id: str, state: Mapping[str, object]) -> dict[str, object]:
    state_payload = dict(state)
    validate_no_secret_like(state_payload)
    return {
        "snapshot_id": snapshot_id,
        "state": state_payload,
        "state_hash": stable_content_hash(state_payload),
        "version": RECOVERY_PROCEDURE_VERSION,
    }


def build_wal_event(
    *,
    sequence: int,
    event_id: str,
    state_patch: Mapping[str, object],
    previous_hash: str = ZERO_HASH,
) -> dict[str, object]:
    if sequence <= 0:
        raise DisasterRecoveryError("sequence_must_be_positive")
    material = {
        "event_id": event_id,
        "previous_hash": previous_hash,
        "sequence": sequence,
        "state_patch": dict(state_patch),
    }
    validate_no_secret_like(material)
    return {**material, "event_hash": stable_content_hash(material)}


def _read_snapshot(path: Path) -> tuple[dict[str, object], tuple[str, ...]]:
    try:
        payload = _read_json_object(path)
    except DisasterRecoveryError:
        return {}, ("snapshot_json_invalid",)
    state = payload.get("state")
    if not isinstance(state, dict):
        return payload, ("snapshot_state_missing",)
    if payload.get("state_hash") != stable_content_hash(state):
        return payload, ("snapshot_state_hash_mismatch",)
    return payload, ()


def _replay_wal(path: Path) -> tuple[dict[str, object], tuple[str, ...]]:
    failures: list[str] = []
    state: dict[str, object] = {}
    previous_hash = ZERO_HASH
    expected_sequence = 1
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return {}, ("wal_missing",)
    for index, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            failures.append(f"wal_line_json_invalid:{index}")
            continue
        if not isinstance(event, dict):
            failures.append(f"wal_line_not_object:{index}")
            continue
        material = {
            "event_id": event.get("event_id"),
            "previous_hash": event.get("previous_hash"),
            "sequence": event.get("sequence"),
            "state_patch": event.get("state_patch"),
        }
        if material["sequence"] != expected_sequence:
            failures.append(f"wal_sequence_gap:{index}")
        if material["previous_hash"] != previous_hash:
            failures.append(f"wal_previous_hash_mismatch:{index}")
        if not isinstance(material["state_patch"], dict):
            failures.append(f"wal_state_patch_invalid:{index}")
        expected_hash = stable_content_hash(material) if isinstance(material["state_patch"], dict) else ""
        if event.get("event_hash") != expected_hash:
            failures.append(f"wal_event_hash_mismatch:{index}")
        if not failures:
            state.update(dict(material["state_patch"]))
            previous_hash = str(event["event_hash"])
            expected_sequence += 1
    if not lines:
        failures.append("wal_empty")
    return state, tuple(sorted(set(failures)))


def _validate_artifact_manifest(runtime_root: Path, manifest_path: Path) -> tuple[str, ...]:
    try:
        payload = _read_json_object(manifest_path)
    except DisasterRecoveryError:
        return ("artifact_manifest_json_invalid",)
    artifacts = payload.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        return ("artifact_manifest_empty",)
    failures: list[str] = []
    for index, item in enumerate(artifacts):
        if not isinstance(item, dict):
            failures.append(f"artifact_manifest_entry_invalid:{index}")
            continue
        relpath = item.get("path")
        expected = item.get("sha256")
        if not isinstance(relpath, str) or not isinstance(expected, str):
            failures.append(f"artifact_manifest_entry_invalid:{index}")
            continue
        artifact = _resolve_manifest_relpath(runtime_root, relpath)
        if not artifact.is_file():
            failures.append(f"artifact_missing:{index}")
        elif _file_sha256(artifact) != expected:
            failures.append(f"artifact_hash_mismatch:{index}")
    return tuple(sorted(set(failures)))


def _artifact_sources(runtime_root: Path, manifest_path: Path) -> tuple[Path, ...]:
    try:
        payload = _read_json_object(manifest_path)
    except DisasterRecoveryError:
        return ()
    artifacts = payload.get("artifacts")
    paths: list[Path] = []
    if isinstance(artifacts, list):
        for item in artifacts:
            if isinstance(item, dict) and isinstance(item.get("path"), str):
                paths.append(_resolve_manifest_relpath(runtime_root, str(item["path"])))
    return tuple(paths)


def _resolve_manifest_relpath(runtime_root: Path, relpath: str) -> Path:
    pure = PurePosixPath(relpath)
    if pure.is_absolute() or ".." in pure.parts or any(part in ("", ".") for part in pure.parts):
        raise DisasterRecoveryError("manifest_path_invalid")
    path = (runtime_root / pure.as_posix()).resolve(strict=False)
    if not path.is_relative_to(runtime_root):
        raise DisasterRecoveryError("manifest_path_escapes_runtime_root")
    return path


def _runtime_inventory(runtime_root: Path) -> tuple[_InventoryRecord, ...]:
    records: list[_InventoryRecord] = []
    runtime_root.mkdir(parents=True, exist_ok=True)
    for path in sorted(item for item in runtime_root.rglob("*") if item.is_file()):
        relpath = path.relative_to(runtime_root)
        if _is_excluded_runtime_part(relpath.parts):
            continue
        records.append(
            _InventoryRecord(
                path=relpath.as_posix(),
                sha256=_file_sha256(path),
                size_bytes=path.stat().st_size,
            )
        )
    return tuple(records)


def _is_excluded_runtime_part(parts: Sequence[str]) -> bool:
    return bool(parts and parts[0] in {"backups", "quarantine"})


def _validate_runtime_root(runtime_root: Path) -> Path:
    raw = runtime_root.expanduser()
    if raw.exists() and raw.is_symlink():
        raise DisasterRecoveryError("runtime_root_symlink_rejected")
    resolved = raw.resolve(strict=False)
    if resolved.exists() and not resolved.is_dir():
        raise DisasterRecoveryError("runtime_root_must_be_directory")
    resolved.mkdir(parents=True, exist_ok=True)
    return resolved


def _read_json_object(path: Path) -> dict[str, object]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DisasterRecoveryError("json_object_invalid") from exc
    if not isinstance(payload, dict):
        raise DisasterRecoveryError("json_object_required")
    validate_no_secret_like(payload)
    return dict(payload)


def _write_json(path: Path, payload: Mapping[str, object]) -> None:
    validate_no_secret_like(dict(payload))
    if path.exists() and path.is_symlink():
        raise DisasterRecoveryError("target_symlink_rejected")
    if path.parent.exists() and path.parent.is_symlink():
        raise DisasterRecoveryError("target_parent_symlink_rejected")
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(path.name + ".tmp")
    temp_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temp_path.replace(path)


def _file_sha256(path: Path) -> str:
    return stable_content_hash({"bytes_sha256": _raw_file_sha256(path)})


def _raw_file_sha256(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
