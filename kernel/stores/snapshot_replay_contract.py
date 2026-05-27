"""Snapshot/replay store contract V1.

Defines digest-only pre/post snapshot manifests and replay reconstruction
receipts. This module does not inspect paths, write snapshots, or perform
rollback.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import re
from typing import Any, Mapping, Sequence

__all__ = [
    "SNAPSHOT_REPLAY_CONTRACT_VERSION",
    "SNAPSHOT_RECONSTRUCTION_POLICY_VERSION",
    "SnapshotManifest",
    "SnapshotReplayReconstructionReceipt",
    "compute_snapshot_manifest_hash",
    "compute_snapshot_reconstruction_hash",
    "reconstruct_snapshot_pair",
    "validate_snapshot_manifest",
]

SNAPSHOT_REPLAY_CONTRACT_VERSION = "snapshot_replay_contract_v1"
SNAPSHOT_RECONSTRUCTION_POLICY_VERSION = "snapshot_reconstruction_policy_v1"

_SNAPSHOT_KINDS = frozenset({"pre_execution", "post_execution"})
_SHA256_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")
_SECRET_KEY_PATTERN = re.compile(
    r"(?i)(api[_-]?key|auth|authorization|credential|password|private[_-]?key|secret|token)"
)
_FORBIDDEN_FIELD_NAMES = frozenset(
    {
        "path",
        "raw_path",
        "absolute_path",
        "content",
        "raw_content",
        "raw_bytes",
        "stdout",
        "stderr",
        "env",
        "environment",
        "secret",
        "token",
    }
)


@dataclass(frozen=True)
class SnapshotManifest:
    snapshot_manifest_id: str
    snapshot_replay_contract_version: str
    snapshot_id: str
    snapshot_kind: str
    task_id: str
    run_id: str
    snapshot_root_hash: str
    changed_path_digests: tuple[tuple[str, str], ...]
    artifact_manifest_hash: str
    wal_record_hash: str
    rollback_plan_hash: str
    created_at: str
    manifest_hash: str = ""

    def __post_init__(self) -> None:
        for field_name in ("snapshot_manifest_id", "snapshot_id", "task_id", "run_id", "created_at"):
            _require_nonempty_string(getattr(self, field_name), field_name)
        if self.snapshot_replay_contract_version != SNAPSHOT_REPLAY_CONTRACT_VERSION:
            raise ValueError("snapshot_replay_contract_version_invalid")
        if self.snapshot_kind not in _SNAPSHOT_KINDS:
            raise ValueError("snapshot_kind_invalid")
        for field_name in (
            "snapshot_root_hash",
            "artifact_manifest_hash",
            "wal_record_hash",
            "rollback_plan_hash",
        ):
            _require_sha256(getattr(self, field_name), field_name)
        object.__setattr__(
            self,
            "changed_path_digests",
            _normalize_changed_path_digests(self.changed_path_digests),
        )
        if self.manifest_hash:
            _require_sha256(self.manifest_hash, "manifest_hash")
        expected = compute_snapshot_manifest_hash(self)
        if self.manifest_hash and self.manifest_hash != expected:
            raise ValueError("manifest_hash_mismatch")
        object.__setattr__(self, "manifest_hash", expected)

    def as_dict(self) -> dict[str, object]:
        return _json_ready(asdict(self))


@dataclass(frozen=True)
class SnapshotReplayReconstructionReceipt:
    reconstruction_policy_version: str
    accepted: bool
    failures: tuple[str, ...]
    task_id: str
    run_id: str
    pre_snapshot_manifest_hash: str
    post_snapshot_manifest_hash: str
    changed_path_count: int
    replay_root_hash: str
    rollback_plan_hash: str
    reconstruction_hash: str = ""

    def __post_init__(self) -> None:
        if self.reconstruction_policy_version != SNAPSHOT_RECONSTRUCTION_POLICY_VERSION:
            raise ValueError("reconstruction_policy_version_invalid")
        if not isinstance(self.accepted, bool):
            raise ValueError("accepted_must_be_bool")
        object.__setattr__(self, "failures", _normalize_failures(self.failures))
        if self.accepted and self.failures:
            raise ValueError("accepted_reconstruction_cannot_have_failures")
        if not self.accepted and not self.failures:
            raise ValueError("rejected_reconstruction_requires_failures")
        _require_nonempty_string(self.task_id, "task_id")
        _require_nonempty_string(self.run_id, "run_id")
        for field_name in (
            "pre_snapshot_manifest_hash",
            "post_snapshot_manifest_hash",
            "replay_root_hash",
            "rollback_plan_hash",
        ):
            _require_sha256(getattr(self, field_name), field_name)
        if not isinstance(self.changed_path_count, int) or isinstance(self.changed_path_count, bool):
            raise ValueError("changed_path_count_must_be_int")
        if self.changed_path_count < 0:
            raise ValueError("changed_path_count_must_be_nonnegative")
        if self.reconstruction_hash:
            _require_sha256(self.reconstruction_hash, "reconstruction_hash")
        expected = compute_snapshot_reconstruction_hash(self)
        if self.reconstruction_hash and self.reconstruction_hash != expected:
            raise ValueError("reconstruction_hash_mismatch")
        object.__setattr__(self, "reconstruction_hash", expected)

    def as_dict(self) -> dict[str, object]:
        return _json_ready(asdict(self))


def validate_snapshot_manifest(manifest: SnapshotManifest | Mapping[str, object]) -> SnapshotManifest:
    if isinstance(manifest, Mapping):
        _validate_mapping_keys(manifest)
        manifest = SnapshotManifest(**dict(manifest))  # type: ignore[arg-type]
    if not isinstance(manifest, SnapshotManifest):
        raise ValueError("manifest_must_be_snapshot_manifest")
    if manifest.manifest_hash != compute_snapshot_manifest_hash(manifest):
        raise ValueError("manifest_hash_mismatch")
    return manifest


def reconstruct_snapshot_pair(
    pre_snapshot: SnapshotManifest,
    post_snapshot: SnapshotManifest,
) -> SnapshotReplayReconstructionReceipt:
    failures: list[str] = []
    try:
        validate_snapshot_manifest(pre_snapshot)
    except ValueError as exc:
        failures.append("pre_" + str(exc))
    try:
        validate_snapshot_manifest(post_snapshot)
    except ValueError as exc:
        failures.append("post_" + str(exc))
    if pre_snapshot.snapshot_kind != "pre_execution":
        failures.append("pre_snapshot_kind_mismatch")
    if post_snapshot.snapshot_kind != "post_execution":
        failures.append("post_snapshot_kind_mismatch")
    if pre_snapshot.task_id != post_snapshot.task_id or pre_snapshot.run_id != post_snapshot.run_id:
        failures.append("snapshot_identity_mismatch")
    if pre_snapshot.rollback_plan_hash != post_snapshot.rollback_plan_hash:
        failures.append("rollback_plan_hash_mismatch")
    replay_root_hash = _pair_root_hash(pre_snapshot, post_snapshot)
    return SnapshotReplayReconstructionReceipt(
        reconstruction_policy_version=SNAPSHOT_RECONSTRUCTION_POLICY_VERSION,
        accepted=not failures,
        failures=tuple(_dedupe(failures)),
        task_id=post_snapshot.task_id,
        run_id=post_snapshot.run_id,
        pre_snapshot_manifest_hash=pre_snapshot.manifest_hash,
        post_snapshot_manifest_hash=post_snapshot.manifest_hash,
        changed_path_count=len(post_snapshot.changed_path_digests),
        replay_root_hash=replay_root_hash,
        rollback_plan_hash=post_snapshot.rollback_plan_hash,
    )


def compute_snapshot_manifest_hash(manifest: SnapshotManifest | Mapping[str, object]) -> str:
    data = _manifest_dict(manifest)
    data.pop("manifest_hash", None)
    data.pop("created_at", None)
    return _sha256(_canonical_json(data))


def compute_snapshot_reconstruction_hash(
    receipt: SnapshotReplayReconstructionReceipt | Mapping[str, object],
) -> str:
    data = _receipt_dict(receipt)
    data.pop("reconstruction_hash", None)
    return _sha256(_canonical_json(data))


def _pair_root_hash(pre_snapshot: SnapshotManifest, post_snapshot: SnapshotManifest) -> str:
    return _sha256(
        _canonical_json(
            {
                "post_snapshot_root_hash": post_snapshot.snapshot_root_hash,
                "post_snapshot_manifest_hash": post_snapshot.manifest_hash,
                "pre_snapshot_root_hash": pre_snapshot.snapshot_root_hash,
                "pre_snapshot_manifest_hash": pre_snapshot.manifest_hash,
            }
        )
    )


def _manifest_dict(manifest: SnapshotManifest | Mapping[str, object]) -> dict[str, object]:
    if isinstance(manifest, SnapshotManifest):
        return manifest.as_dict()
    return _json_ready(dict(manifest))


def _receipt_dict(
    receipt: SnapshotReplayReconstructionReceipt | Mapping[str, object],
) -> dict[str, object]:
    if isinstance(receipt, SnapshotReplayReconstructionReceipt):
        return receipt.as_dict()
    return _json_ready(dict(receipt))


def _validate_mapping_keys(payload: Mapping[str, object]) -> None:
    forbidden = sorted(
        str(key)
        for key in payload
        if str(key) in _FORBIDDEN_FIELD_NAMES or _SECRET_KEY_PATTERN.search(str(key))
    )
    if forbidden:
        raise ValueError("snapshot_manifest_field_forbidden:" + ",".join(forbidden))


def _normalize_changed_path_digests(value: object) -> tuple[tuple[str, str], ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise ValueError("changed_path_digests_must_be_sequence")
    normalized: list[tuple[str, str]] = []
    seen: set[str] = set()
    for item in value:
        if not isinstance(item, Sequence) or isinstance(item, (str, bytes)) or len(item) != 2:
            raise ValueError("changed_path_digest_must_be_pair")
        path_digest = str(item[0])
        content_digest = str(item[1])
        _require_sha256(path_digest, "path_digest")
        _require_sha256(content_digest, "content_digest")
        if path_digest in seen:
            raise ValueError("path_digest_duplicate")
        seen.add(path_digest)
        normalized.append((path_digest, content_digest))
    return tuple(sorted(normalized))


def _normalize_failures(value: object) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise ValueError("failures_must_be_sequence")
    failures = tuple(str(item) for item in value)
    for failure in failures:
        _require_nonempty_string(failure, "failure")
    return tuple(_dedupe(failures))


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
