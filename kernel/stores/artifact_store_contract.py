"""Artifact store contract V1.

Defines digest-addressed artifact manifests and verification receipts without
reading files, writing storage, ingesting binaries, or coupling to runtime code.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import re
from pathlib import PurePosixPath
from typing import Any, Mapping, Sequence

__all__ = [
    "ARTIFACT_STORE_CONTRACT_VERSION",
    "ARTIFACT_STORE_VERIFY_POLICY_VERSION",
    "ARTIFACT_TYPES",
    "ArtifactManifest",
    "ArtifactVerificationReceipt",
    "artifact_manifest_from_ingest",
    "compute_artifact_manifest_hash",
    "compute_artifact_verification_hash",
    "verify_artifact_manifest",
]

ARTIFACT_STORE_CONTRACT_VERSION = "artifact_store_contract_v1"
ARTIFACT_STORE_VERIFY_POLICY_VERSION = "artifact_store_verify_policy_v1"

ARTIFACT_TYPES = frozenset(
    {
        "audit_json",
        "audit_markdown",
        "failure_bundle",
        "operator_report",
        "replay_report",
        "snapshot_manifest",
        "wal_export",
        "worker_receipt",
        "media_manifest",
        "config_health_report",
    }
)

_SHA256_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")
_STORAGE_RELPATH_PATTERN = re.compile(r"^[a-f0-9]{2}/[a-f0-9]{62}/[a-z0-9_.-]{1,128}$")
_SECRET_KEY_PATTERN = re.compile(
    r"(?i)(api[_-]?key|auth|authorization|credential|password|private[_-]?key|secret|token)"
)
_FORBIDDEN_FIELD_NAMES = frozenset(
    {
        "content",
        "raw_content",
        "raw_bytes",
        "raw_log",
        "raw_stdout",
        "raw_stderr",
        "stdout",
        "stderr",
        "env",
        "environment",
        "secret",
        "token",
        "password",
        "credential",
    }
)


@dataclass(frozen=True)
class ArtifactManifest:
    artifact_manifest_id: str
    artifact_store_contract_version: str
    artifact_id: str
    artifact_type: str
    task_id: str
    run_id: str
    content_sha256: str
    size_bytes: int
    storage_relpath: str
    wal_record_hash: str
    provenance_hash: str
    retention_marker: str
    quarantine_marker: str
    local_only: bool
    created_at: str
    manifest_hash: str = ""

    def __post_init__(self) -> None:
        for field_name in ("artifact_manifest_id", "artifact_id", "task_id", "run_id", "created_at"):
            _require_nonempty_string(getattr(self, field_name), field_name)
        if self.artifact_store_contract_version != ARTIFACT_STORE_CONTRACT_VERSION:
            raise ValueError("artifact_store_contract_version_invalid")
        if self.artifact_type not in ARTIFACT_TYPES:
            raise ValueError("artifact_type_invalid")
        _require_sha256(self.content_sha256, "content_sha256")
        if not isinstance(self.size_bytes, int) or isinstance(self.size_bytes, bool):
            raise ValueError("size_bytes_must_be_int")
        if self.size_bytes < 0:
            raise ValueError("size_bytes_must_be_nonnegative")
        _validate_storage_relpath(self.storage_relpath, self.content_sha256)
        for field_name in ("wal_record_hash", "provenance_hash"):
            _require_sha256(getattr(self, field_name), field_name)
        if self.retention_marker not in {"retain", "candidate_for_gc"}:
            raise ValueError("retention_marker_invalid")
        if self.quarantine_marker not in {"clean", "quarantined"}:
            raise ValueError("quarantine_marker_invalid")
        if not isinstance(self.local_only, bool):
            raise ValueError("local_only_must_be_bool")
        if self.manifest_hash:
            _require_sha256(self.manifest_hash, "manifest_hash")
        expected = compute_artifact_manifest_hash(self)
        if self.manifest_hash and self.manifest_hash != expected:
            raise ValueError("manifest_hash_mismatch")
        object.__setattr__(self, "manifest_hash", expected)

    def as_dict(self) -> dict[str, object]:
        return _json_ready(asdict(self))


@dataclass(frozen=True)
class ArtifactVerificationReceipt:
    verify_policy_version: str
    artifact_manifest_id: str
    accepted: bool
    failures: tuple[str, ...]
    expected_content_sha256: str
    observed_content_sha256: str
    expected_size_bytes: int
    observed_size_bytes: int
    quarantine_required: bool
    manifest_hash: str
    verification_hash: str = ""

    def __post_init__(self) -> None:
        if self.verify_policy_version != ARTIFACT_STORE_VERIFY_POLICY_VERSION:
            raise ValueError("verify_policy_version_invalid")
        _require_nonempty_string(self.artifact_manifest_id, "artifact_manifest_id")
        if not isinstance(self.accepted, bool):
            raise ValueError("accepted_must_be_bool")
        object.__setattr__(self, "failures", _normalize_failures(self.failures))
        if self.accepted and self.failures:
            raise ValueError("accepted_verification_cannot_have_failures")
        if not self.accepted and not self.failures:
            raise ValueError("rejected_verification_requires_failures")
        for field_name in ("expected_content_sha256", "observed_content_sha256", "manifest_hash"):
            _require_sha256(getattr(self, field_name), field_name)
        for field_name in ("expected_size_bytes", "observed_size_bytes"):
            value = getattr(self, field_name)
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise ValueError(field_name + "_must_be_nonnegative_int")
        if not isinstance(self.quarantine_required, bool):
            raise ValueError("quarantine_required_must_be_bool")
        if self.verification_hash:
            _require_sha256(self.verification_hash, "verification_hash")
        expected = compute_artifact_verification_hash(self)
        if self.verification_hash and self.verification_hash != expected:
            raise ValueError("verification_hash_mismatch")
        object.__setattr__(self, "verification_hash", expected)

    def as_dict(self) -> dict[str, object]:
        return _json_ready(asdict(self))


def artifact_manifest_from_ingest(payload: Mapping[str, object]) -> ArtifactManifest:
    _validate_mapping_keys(payload)
    content_sha256 = str(payload["content_sha256"])
    artifact_id = str(payload.get("artifact_id") or _artifact_id(content_sha256))
    storage_relpath = str(payload.get("storage_relpath") or _storage_relpath(content_sha256, artifact_id))
    return ArtifactManifest(
        artifact_manifest_id=str(payload.get("artifact_manifest_id") or "artifact-manifest-" + artifact_id),
        artifact_store_contract_version=str(
            payload.get("artifact_store_contract_version") or ARTIFACT_STORE_CONTRACT_VERSION
        ),
        artifact_id=artifact_id,
        artifact_type=str(payload["artifact_type"]),
        task_id=str(payload["task_id"]),
        run_id=str(payload["run_id"]),
        content_sha256=content_sha256,
        size_bytes=payload["size_bytes"],  # type: ignore[arg-type]
        storage_relpath=storage_relpath,
        wal_record_hash=str(payload["wal_record_hash"]),
        provenance_hash=str(payload["provenance_hash"]),
        retention_marker=str(payload.get("retention_marker") or "retain"),
        quarantine_marker=str(payload.get("quarantine_marker") or "clean"),
        local_only=bool(payload.get("local_only", True)),
        created_at=str(payload["created_at"]),
        manifest_hash=str(payload.get("manifest_hash", "")),
    )


def verify_artifact_manifest(
    manifest: ArtifactManifest,
    *,
    observed_content_sha256: str,
    observed_size_bytes: int,
) -> ArtifactVerificationReceipt:
    if not isinstance(manifest, ArtifactManifest):
        raise ValueError("manifest_must_be_artifact_manifest")
    failures: list[str] = []
    if manifest.manifest_hash != compute_artifact_manifest_hash(manifest):
        failures.append("manifest_hash_mismatch")
    if observed_content_sha256 != manifest.content_sha256:
        failures.append("content_sha256_mismatch")
    if observed_size_bytes != manifest.size_bytes:
        failures.append("size_bytes_mismatch")
    if manifest.quarantine_marker == "quarantined":
        failures.append("artifact_quarantined")
    return ArtifactVerificationReceipt(
        verify_policy_version=ARTIFACT_STORE_VERIFY_POLICY_VERSION,
        artifact_manifest_id=manifest.artifact_manifest_id,
        accepted=not failures,
        failures=tuple(failures),
        expected_content_sha256=manifest.content_sha256,
        observed_content_sha256=observed_content_sha256,
        expected_size_bytes=manifest.size_bytes,
        observed_size_bytes=observed_size_bytes,
        quarantine_required=bool(failures),
        manifest_hash=manifest.manifest_hash,
    )


def compute_artifact_manifest_hash(manifest: ArtifactManifest | Mapping[str, object]) -> str:
    data = _manifest_dict(manifest)
    data.pop("manifest_hash", None)
    data.pop("created_at", None)
    return _sha256(_canonical_json(data))


def compute_artifact_verification_hash(
    receipt: ArtifactVerificationReceipt | Mapping[str, object],
) -> str:
    data = _verification_dict(receipt)
    data.pop("verification_hash", None)
    return _sha256(_canonical_json(data))


def _manifest_dict(manifest: ArtifactManifest | Mapping[str, object]) -> dict[str, object]:
    if isinstance(manifest, ArtifactManifest):
        return manifest.as_dict()
    return _json_ready(dict(manifest))


def _verification_dict(
    receipt: ArtifactVerificationReceipt | Mapping[str, object],
) -> dict[str, object]:
    if isinstance(receipt, ArtifactVerificationReceipt):
        return receipt.as_dict()
    return _json_ready(dict(receipt))


def _validate_mapping_keys(payload: Mapping[str, object]) -> None:
    forbidden = sorted(
        str(key)
        for key in payload
        if str(key) in _FORBIDDEN_FIELD_NAMES or _SECRET_KEY_PATTERN.search(str(key))
    )
    if forbidden:
        raise ValueError("artifact_manifest_field_forbidden:" + ",".join(forbidden))


def _validate_storage_relpath(storage_relpath: object, content_sha256: str) -> None:
    _require_nonempty_string(storage_relpath, "storage_relpath")
    path = PurePosixPath(str(storage_relpath))
    if path.is_absolute() or ".." in path.parts:
        raise ValueError("storage_relpath_must_be_relative")
    if not _STORAGE_RELPATH_PATTERN.fullmatch(str(storage_relpath)):
        raise ValueError("storage_relpath_not_digest_addressed")
    digest = content_sha256.removeprefix("sha256:")
    expected_prefix = digest[:2] + "/" + digest[2:]
    if not str(storage_relpath).startswith(expected_prefix + "/"):
        raise ValueError("storage_relpath_digest_mismatch")


def _artifact_id(content_sha256: str) -> str:
    _require_sha256(content_sha256, "content_sha256")
    return "artifact-" + content_sha256.removeprefix("sha256:")[:24]


def _storage_relpath(content_sha256: str, artifact_id: str) -> str:
    digest = content_sha256.removeprefix("sha256:")
    return digest[:2] + "/" + digest[2:] + "/" + artifact_id + ".json"


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
