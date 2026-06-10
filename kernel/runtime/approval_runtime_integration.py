"""Approval runtime integration V1.

This module turns the existing approval runtime contract into a local,
file-backed gate for the human-invoked WAL-gated preflight path. It persists
approval evidence, binds approval issuance and consumption to the real WAL, and
fails closed before the preflight wrapper can proceed.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
from typing import Any, Callable, Mapping

from kernel.execution.minimal_controlled_wal_adapter_contract import (
    MinimalControlledWalAdapterRecord,
)
from kernel.execution.minimal_controlled_wal_gated_preflight_api import (
    MinimalControlledWalGatedPreflightApiResponse,
    run_human_invoked_minimal_controlled_wal_gated_preflight,
)
from kernel.runtime.approval_runtime_contract import (
    ApprovalRuntimeAdmissionReceipt,
    ApprovalRuntimeDecision,
    ApprovalRuntimeRequest,
    admit_approval_runtime_decision,
    build_approval_runtime_decision,
    build_approval_runtime_request,
    validate_approval_runtime_admission_receipt,
    validate_approval_runtime_decision,
    validate_approval_runtime_request,
)
from kernel.stores.artifact_store_persistence import (
    ArtifactStorePersistenceError,
    FileBackedArtifactStore,
)
from kernel.stores.real_wal_storage import (
    FileBackedRealWalStorage,
    RealWalStorageError,
)

__all__ = [
    "APPROVAL_RUNTIME_INTEGRATION_VERSION",
    "APPROVAL_RUNTIME_EXECUTION_SCOPE",
    "ApprovalRuntimeIntegratedReceipt",
    "ApprovalRuntimeConsumptionReceipt",
    "ApprovalRuntimeGatedPreflightResponse",
    "ApprovalRuntimeIntegrationError",
    "FileBackedApprovalRuntimeIntegration",
    "run_approval_gated_minimal_controlled_wal_preflight",
    "compute_integrated_approval_receipt_hash",
    "compute_approval_consumption_receipt_hash",
    "compute_approval_gated_preflight_response_hash",
]

APPROVAL_RUNTIME_INTEGRATION_VERSION = "approval_runtime_integration_v1"
APPROVAL_RUNTIME_EXECUTION_SCOPE = "manual_next_stage_only"
ZERO_HASH = "sha256:" + ("0" * 64)

_SHA256_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")
_SECRET_KEY_PATTERN = re.compile(
    r"(?i)(api[_-]?key|auth|authorization|credential|password|private[_-]?key|secret|token)"
)
_SECRET_PATH_PATTERN = re.compile(
    r"(?i)(^\.env$|\.env\.local|\.envrc|credential|id_rsa|id_dsa|id_ed25519|secret|token|password)"
)
_GATED_PAYLOAD_ALLOWED_EXTRA_FIELDS = frozenset(
    {
        "approval_admission_hash",
        "approval_scope",
    }
)
_CALLER_APPROVAL_FIELDS = frozenset(
    {
        "approved_for_wal_gated_preflight",
        "approval_token_id",
    }
)


class ApprovalRuntimeIntegrationError(ValueError):
    """Raised when approval runtime integration fails closed."""


@dataclass(frozen=True)
class ApprovalRuntimeIntegratedReceipt:
    integration_version: str
    approval_id: str
    task_id: str
    run_id: str
    approval_scope: str
    approval_request_hash: str
    approval_decision_hash: str
    approval_admission_hash: str
    approval_wal_record_hash: str
    approval_artifact_record_hash: str
    artifact_manifest_hash: str
    snapshot_reconstruction_hash: str
    expires_at: str
    issued_at: str
    receipt_hash: str = ""

    def __post_init__(self) -> None:
        if self.integration_version != APPROVAL_RUNTIME_INTEGRATION_VERSION:
            raise ApprovalRuntimeIntegrationError("integration_version_invalid")
        for field_name in ("approval_id", "task_id", "run_id", "issued_at", "expires_at"):
            _require_nonempty_string(getattr(self, field_name), field_name)
        if self.approval_scope != APPROVAL_RUNTIME_EXECUTION_SCOPE:
            raise ApprovalRuntimeIntegrationError("approval_scope_invalid")
        for field_name in (
            "approval_request_hash",
            "approval_decision_hash",
            "approval_admission_hash",
            "approval_wal_record_hash",
            "approval_artifact_record_hash",
            "artifact_manifest_hash",
            "snapshot_reconstruction_hash",
        ):
            _require_sha256(getattr(self, field_name), field_name)
        _parse_timestamp(self.issued_at, "issued_at")
        _parse_timestamp(self.expires_at, "expires_at")
        _install_or_verify_hash(
            self,
            "receipt_hash",
            compute_integrated_approval_receipt_hash,
        )

    def as_dict(self) -> dict[str, object]:
        return _json_ready(asdict(self))


@dataclass(frozen=True)
class ApprovalRuntimeConsumptionReceipt:
    integration_version: str
    accepted: bool
    failures: tuple[str, ...]
    approval_id: str
    approval_admission_hash: str
    task_id: str
    run_id: str
    preflight_id: str
    approval_scope: str
    consumption_wal_record_hash: str
    consumed_at: str
    receipt_hash: str = ""

    def __post_init__(self) -> None:
        if self.integration_version != APPROVAL_RUNTIME_INTEGRATION_VERSION:
            raise ApprovalRuntimeIntegrationError("integration_version_invalid")
        if not isinstance(self.accepted, bool):
            raise ApprovalRuntimeIntegrationError("accepted_must_be_bool")
        object.__setattr__(self, "failures", _normalize_failures(self.failures))
        if self.accepted and self.failures:
            raise ApprovalRuntimeIntegrationError("accepted_consumption_has_failures")
        if not self.accepted and not self.failures:
            raise ApprovalRuntimeIntegrationError("rejected_consumption_requires_failures")
        for field_name in ("approval_id", "task_id", "run_id", "preflight_id", "approval_scope", "consumed_at"):
            _require_nonempty_string(getattr(self, field_name), field_name)
        if self.approval_scope != APPROVAL_RUNTIME_EXECUTION_SCOPE:
            raise ApprovalRuntimeIntegrationError("approval_scope_invalid")
        _require_sha256(self.approval_admission_hash, "approval_admission_hash")
        _require_sha256(self.consumption_wal_record_hash, "consumption_wal_record_hash")
        _parse_timestamp(self.consumed_at, "consumed_at")
        _install_or_verify_hash(
            self,
            "receipt_hash",
            compute_approval_consumption_receipt_hash,
        )

    def as_dict(self) -> dict[str, object]:
        return _json_ready(asdict(self))


@dataclass(frozen=True)
class ApprovalRuntimeGatedPreflightResponse:
    integration_version: str
    accepted: bool
    execution_may_proceed: bool
    rejection_reasons: tuple[str, ...]
    approval_consumption_receipt_hash: str
    preflight_api_response_hash: str
    task_id: str
    run_id: str
    preflight_id: str
    response_hash: str = ""

    def __post_init__(self) -> None:
        if self.integration_version != APPROVAL_RUNTIME_INTEGRATION_VERSION:
            raise ApprovalRuntimeIntegrationError("integration_version_invalid")
        if not isinstance(self.accepted, bool):
            raise ApprovalRuntimeIntegrationError("accepted_must_be_bool")
        if not isinstance(self.execution_may_proceed, bool):
            raise ApprovalRuntimeIntegrationError("execution_may_proceed_must_be_bool")
        object.__setattr__(
            self,
            "rejection_reasons",
            _normalize_failures(self.rejection_reasons),
        )
        if self.accepted and self.rejection_reasons:
            raise ApprovalRuntimeIntegrationError("accepted_response_has_rejections")
        if not self.accepted and not self.rejection_reasons:
            raise ApprovalRuntimeIntegrationError("rejected_response_requires_rejections")
        if self.execution_may_proceed != self.accepted:
            raise ApprovalRuntimeIntegrationError("execution_may_proceed_must_match_accepted")
        for field_name in (
            "approval_consumption_receipt_hash",
            "preflight_api_response_hash",
        ):
            _require_sha256(getattr(self, field_name), field_name)
        for field_name in ("task_id", "run_id", "preflight_id"):
            _require_nonempty_string(getattr(self, field_name), field_name)
        _install_or_verify_hash(
            self,
            "response_hash",
            compute_approval_gated_preflight_response_hash,
        )

    def as_dict(self) -> dict[str, object]:
        return _json_ready(asdict(self))


class FileBackedApprovalRuntimeIntegration:
    """Local approval receipt store bound to real WAL and safe artifact evidence."""

    def __init__(
        self,
        *,
        runtime_root: str | Path,
        approval_store_relpath: str = "approval-runtime",
        approval_wal_relpath: str = "approval-runtime/approval.real-wal.jsonl",
        artifact_store_relpath: str = "artifact-store",
        artifact_store_id: str = "artifact-store-persistence-v1",
    ) -> None:
        self.runtime_root = _validate_runtime_root(Path(runtime_root))
        self.approval_store_relpath = _validate_relpath_text(
            approval_store_relpath,
            "approval_store_relpath",
            allow_empty=False,
        )
        self.approval_wal_relpath = _validate_relpath_text(
            approval_wal_relpath,
            "approval_wal_relpath",
            allow_empty=False,
        )
        self.artifact_store_relpath = _validate_relpath_text(
            artifact_store_relpath,
            "artifact_store_relpath",
            allow_empty=False,
        )
        _require_nonempty_string(artifact_store_id, "artifact_store_id")
        self.artifact_store_id = artifact_store_id

    def issue_approval(
        self,
        *,
        request_payload: Mapping[str, object],
        decision_payload: Mapping[str, object],
        expires_at: str,
        issued_at: str | None = None,
        operator_receipt_hash: str | None = None,
    ) -> ApprovalRuntimeIntegratedReceipt:
        issued = _timestamp(issued_at)
        expiry = _timestamp(expires_at)
        if _parse_timestamp(expiry, "expires_at") <= _parse_timestamp(issued, "issued_at"):
            raise ApprovalRuntimeIntegrationError("approval_expires_at_must_be_after_issued_at")

        request = build_approval_runtime_request(request_payload, created_at=issued)
        decision = build_approval_runtime_decision(decision_payload, decided_at=issued)
        if decision.operator_action != "approved":
            raise ApprovalRuntimeIntegrationError("approval_issue_requires_approved_decision")
        if decision.approval_scope != APPROVAL_RUNTIME_EXECUTION_SCOPE:
            raise ApprovalRuntimeIntegrationError("approval_scope_mismatch")

        issue_wal_hash = self._append_approval_wal(
            task_id=request.task_id,
            run_id=request.run_id,
            payload={
                "event": "approval_issued",
                "approval_decision_hash": decision.decision_hash,
                "approval_request_hash": request.request_hash,
                "approval_scope": decision.approval_scope,
                "expires_at": expiry,
                "integration_version": APPROVAL_RUNTIME_INTEGRATION_VERSION,
            },
            digest_bindings={
                "approval_request_hash": request.request_hash,
                "approval_decision_hash": decision.decision_hash,
                "approval_scope_hash": _sha256_text(decision.approval_scope),
                "approval_expires_at_hash": _sha256_text(expiry),
                "approval_artifact_manifest_hash": request.artifact_manifest_hash,
                "approval_snapshot_reconstruction_hash": (
                    request.snapshot_reconstruction_hash
                ),
            },
            created_at=issued,
        )
        admission = admit_approval_runtime_decision(
            request,
            decision,
            wal_record_hash=issue_wal_hash,
            operator_receipt_hash=operator_receipt_hash,
            admitted_at=issued,
        )
        if not admission.accepted:
            raise ApprovalRuntimeIntegrationError("approval_admission_not_accepted")

        artifact_record_hash = self._write_approval_artifact(
            request=request,
            decision=decision,
            admission=admission,
            expires_at=expiry,
            issued_at=issued,
        )
        integrated = ApprovalRuntimeIntegratedReceipt(
            integration_version=APPROVAL_RUNTIME_INTEGRATION_VERSION,
            approval_id=_approval_id(admission.admission_hash),
            task_id=request.task_id,
            run_id=request.run_id,
            approval_scope=decision.approval_scope,
            approval_request_hash=request.request_hash,
            approval_decision_hash=decision.decision_hash,
            approval_admission_hash=admission.admission_hash,
            approval_wal_record_hash=issue_wal_hash,
            approval_artifact_record_hash=artifact_record_hash,
            artifact_manifest_hash=request.artifact_manifest_hash,
            snapshot_reconstruction_hash=request.snapshot_reconstruction_hash,
            expires_at=expiry,
            issued_at=issued,
        )
        self._write_json_no_overwrite(
            self._approval_relpath(admission.admission_hash),
            {
                "admission": admission.as_dict(),
                "decision": decision.as_dict(),
                "integrated_receipt": integrated.as_dict(),
                "request": request.as_dict(),
            },
        )
        return integrated

    def revoke_approval(
        self,
        approval_admission_hash: str,
        *,
        task_id: str,
        run_id: str,
        reason_code: str,
        revoked_at: str | None = None,
    ) -> ApprovalRuntimeConsumptionReceipt:
        _require_sha256(approval_admission_hash, "approval_admission_hash")
        _require_nonempty_string(reason_code, "reason_code")
        revoked = _timestamp(revoked_at)
        wal_hash = self._append_approval_wal(
            task_id=task_id,
            run_id=run_id,
            payload={
                "event": "approval_revoked",
                "approval_admission_hash": approval_admission_hash,
                "reason_code": reason_code,
            },
            digest_bindings={
                "approval_admission_hash": approval_admission_hash,
                "approval_revocation_reason_hash": _sha256_text(reason_code),
            },
            created_at=revoked,
        )
        receipt = ApprovalRuntimeConsumptionReceipt(
            integration_version=APPROVAL_RUNTIME_INTEGRATION_VERSION,
            accepted=False,
            failures=("approval_revoked",),
            approval_id=_approval_id(approval_admission_hash),
            approval_admission_hash=approval_admission_hash,
            task_id=task_id,
            run_id=run_id,
            preflight_id="revocation",
            approval_scope=APPROVAL_RUNTIME_EXECUTION_SCOPE,
            consumption_wal_record_hash=wal_hash,
            consumed_at=revoked,
        )
        self._write_json_no_overwrite(
            self._revocation_relpath(approval_admission_hash),
            {
                "reason_code": reason_code,
                "revocation_receipt": receipt.as_dict(),
            },
        )
        return receipt

    def consume_for_preflight(
        self,
        *,
        approval_admission_hash: str,
        task_id: str,
        run_id: str,
        preflight_id: str,
        approval_scope: str,
        consumed_at: str | None = None,
    ) -> ApprovalRuntimeConsumptionReceipt:
        observed = _timestamp(consumed_at)
        _require_sha256(approval_admission_hash, "approval_admission_hash")
        _require_nonempty_string(task_id, "task_id")
        _require_nonempty_string(run_id, "run_id")
        _require_nonempty_string(preflight_id, "preflight_id")
        _require_nonempty_string(approval_scope, "approval_scope")

        failures: list[str] = []
        approval = self._read_approval(approval_admission_hash, failures)
        if approval is not None:
            integrated = approval["integrated_receipt"]
            admission = approval["admission"]
            if approval_scope != APPROVAL_RUNTIME_EXECUTION_SCOPE:
                failures.append("approval_scope_mismatch")
            if integrated.task_id != task_id or integrated.run_id != run_id:
                failures.append("approval_identity_mismatch")
            if integrated.approval_scope != approval_scope:
                failures.append("approval_scope_mismatch")
            if admission.accepted is not True:
                failures.append("approval_not_accepted")
            if self._path_exists(self._revocation_relpath(approval_admission_hash)):
                failures.append("approval_revoked")
            if self._path_exists(self._consumption_relpath(approval_admission_hash)):
                failures.append("approval_reused")
            if _parse_timestamp(integrated.expires_at, "expires_at") <= _parse_timestamp(
                observed,
                "consumed_at",
            ):
                failures.append("approval_expired")

        accepted = not failures
        wal_hash = self._append_approval_wal(
            task_id=task_id,
            run_id=run_id,
            payload={
                "accepted": accepted,
                "approval_admission_hash": approval_admission_hash,
                "event": "approval_consumed" if accepted else "approval_rejected",
                "failures": tuple(_dedupe(failures)),
                "preflight_id": preflight_id,
            },
            digest_bindings={
                "approval_admission_hash": approval_admission_hash,
                "approval_consumption_attempt_hash": _sha256_json(
                    {
                        "accepted": accepted,
                        "approval_admission_hash": approval_admission_hash,
                        "failures": tuple(_dedupe(failures)),
                        "preflight_id": preflight_id,
                    }
                ),
            },
            created_at=observed,
        )
        receipt = ApprovalRuntimeConsumptionReceipt(
            integration_version=APPROVAL_RUNTIME_INTEGRATION_VERSION,
            accepted=accepted,
            failures=tuple(_dedupe(failures)),
            approval_id=_approval_id(approval_admission_hash),
            approval_admission_hash=approval_admission_hash,
            task_id=task_id,
            run_id=run_id,
            preflight_id=preflight_id,
            approval_scope=approval_scope
            if approval_scope == APPROVAL_RUNTIME_EXECUTION_SCOPE
            else APPROVAL_RUNTIME_EXECUTION_SCOPE,
            consumption_wal_record_hash=wal_hash,
            consumed_at=observed,
        )
        if accepted:
            self._write_json_no_overwrite(
                self._consumption_relpath(approval_admission_hash),
                receipt.as_dict(),
            )
        else:
            self._write_json_no_overwrite(
                self._rejection_relpath(receipt.receipt_hash),
                receipt.as_dict(),
            )
        return receipt

    def _read_approval(
        self,
        approval_admission_hash: str,
        failures: list[str],
    ) -> dict[str, object] | None:
        path = self._resolve_relpath(
            self._approval_relpath(approval_admission_hash),
            "approval_receipt_relpath",
        )
        if not path.exists():
            failures.append("approval_missing")
            return None
        if path.is_symlink():
            failures.append("approval_receipt_is_symlink")
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(payload, Mapping):
                raise ApprovalRuntimeIntegrationError("approval_receipt_must_be_mapping")
            request = ApprovalRuntimeRequest(**dict(payload["request"]))  # type: ignore[arg-type]
            decision = ApprovalRuntimeDecision(**dict(payload["decision"]))  # type: ignore[arg-type]
            admission = ApprovalRuntimeAdmissionReceipt(**dict(payload["admission"]))  # type: ignore[arg-type]
            integrated = ApprovalRuntimeIntegratedReceipt(
                **dict(payload["integrated_receipt"])  # type: ignore[arg-type]
            )
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            failures.append("approval_receipt_invalid:" + str(exc))
            return None
        if not validate_approval_runtime_request(request):
            failures.append("approval_request_invalid")
        if not validate_approval_runtime_decision(decision):
            failures.append("approval_decision_invalid")
        if not validate_approval_runtime_admission_receipt(admission):
            failures.append("approval_admission_invalid")
        if integrated.approval_admission_hash != approval_admission_hash:
            failures.append("approval_admission_hash_mismatch")
        if integrated.approval_request_hash != request.request_hash:
            failures.append("approval_request_hash_mismatch")
        if integrated.approval_decision_hash != decision.decision_hash:
            failures.append("approval_decision_hash_mismatch")
        if integrated.approval_wal_record_hash != admission.wal_record_hash:
            failures.append("approval_wal_record_hash_mismatch")
        return {
            "admission": admission,
            "decision": decision,
            "integrated_receipt": integrated,
            "request": request,
        }

    def _write_approval_artifact(
        self,
        *,
        request: ApprovalRuntimeRequest,
        decision: ApprovalRuntimeDecision,
        admission: ApprovalRuntimeAdmissionReceipt,
        expires_at: str,
        issued_at: str,
    ) -> str:
        artifact_root = self._resolve_relpath(
            self.artifact_store_relpath,
            "artifact_store_relpath",
        )
        try:
            receipt = FileBackedArtifactStore(
                artifact_root,
                store_id=self.artifact_store_id,
            ).write_json_artifact(
                artifact_type="audit_json",
                task_id=request.task_id,
                run_id=request.run_id,
                payload={
                    "approval_admission_hash": admission.admission_hash,
                    "approval_decision_hash": decision.decision_hash,
                    "approval_expires_at": expires_at,
                    "approval_id": _approval_id(admission.admission_hash),
                    "approval_request_hash": request.request_hash,
                    "approval_scope": decision.approval_scope,
                    "approval_wal_record_hash": admission.wal_record_hash,
                    "artifact_manifest_hash": request.artifact_manifest_hash,
                    "snapshot_reconstruction_hash": request.snapshot_reconstruction_hash,
                },
                provenance_hash=_sha256_json(
                    {
                        "admission_hash": admission.admission_hash,
                        "decision_hash": decision.decision_hash,
                        "issued_at": issued_at,
                        "request_hash": request.request_hash,
                    }
                ),
                metadata={"source": APPROVAL_RUNTIME_INTEGRATION_VERSION},
                created_at=issued_at,
            )
        except ArtifactStorePersistenceError as exc:
            raise ApprovalRuntimeIntegrationError(
                "approval_artifact_write_failed:" + str(exc)
            ) from exc
        return receipt.record_hash

    def _append_approval_wal(
        self,
        *,
        task_id: str,
        run_id: str,
        payload: Mapping[str, object],
        digest_bindings: Mapping[str, str],
        created_at: str,
    ) -> str:
        wal_path = self._resolve_relpath(self.approval_wal_relpath, "approval_wal_relpath")
        wal_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            receipt = FileBackedRealWalStorage(wal_path).append(
                record_type="APPROVAL_EVENT",
                task_id=task_id,
                run_id=run_id,
                payload_hash=_sha256_json(payload),
                digest_bindings=digest_bindings,
                created_at=created_at,
            )
        except RealWalStorageError as exc:
            raise ApprovalRuntimeIntegrationError(
                "approval_wal_append_failed:" + str(exc)
            ) from exc
        return receipt.record_hash

    def _path_exists(self, relpath: str) -> bool:
        return self._resolve_relpath(relpath, "approval_state_relpath").exists()

    def _approval_relpath(self, approval_admission_hash: str) -> str:
        return (
            self.approval_store_relpath
            + "/approvals/"
            + approval_admission_hash.removeprefix("sha256:")
            + ".json"
        )

    def _consumption_relpath(self, approval_admission_hash: str) -> str:
        return (
            self.approval_store_relpath
            + "/consumptions/"
            + approval_admission_hash.removeprefix("sha256:")
            + ".json"
        )

    def _revocation_relpath(self, approval_admission_hash: str) -> str:
        return (
            self.approval_store_relpath
            + "/revocations/"
            + approval_admission_hash.removeprefix("sha256:")
            + ".json"
        )

    def _rejection_relpath(self, receipt_hash: str) -> str:
        return (
            self.approval_store_relpath
            + "/rejections/"
            + receipt_hash.removeprefix("sha256:")
            + ".json"
        )

    def _write_json_no_overwrite(
        self,
        relpath: str,
        payload: Mapping[str, object],
    ) -> None:
        path = self._resolve_relpath(relpath, "approval_write_relpath")
        data = (_canonical_json(payload) + "\n").encode("utf-8")
        if path.exists():
            if path.is_symlink():
                raise ApprovalRuntimeIntegrationError("approval_write_target_is_symlink")
            if not path.is_file():
                raise ApprovalRuntimeIntegrationError("approval_write_target_not_file")
            if path.read_bytes() == data:
                return
            raise ApprovalRuntimeIntegrationError("approval_write_target_mismatch")
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.parent.is_symlink():
            raise ApprovalRuntimeIntegrationError("approval_write_parent_is_symlink")
        temp_path = path.with_name(
            "." + path.name + ".tmp-" + _sha256_bytes(data).removeprefix("sha256:")[:16]
        )
        try:
            fd = os.open(temp_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except OSError as exc:
            raise ApprovalRuntimeIntegrationError("approval_write_temp_open_failed") from exc
        try:
            try:
                written = 0
                while written < len(data):
                    count = os.write(fd, data[written:])
                    if count <= 0:
                        raise ApprovalRuntimeIntegrationError("approval_write_failed")
                    written += count
                os.fsync(fd)
            finally:
                os.close(fd)
            if path.exists():
                raise ApprovalRuntimeIntegrationError("approval_write_target_exists")
            temp_path.rename(path)
            _fsync_parent(path)
        except Exception:
            try:
                temp_path.unlink()
            except OSError:
                pass
            raise

    def _resolve_relpath(self, relpath: str, field_name: str) -> Path:
        _validate_relpath_text(relpath, field_name, allow_empty=False)
        candidate = self.runtime_root / relpath
        current = self.runtime_root
        for part in PurePosixPath(relpath).parts:
            current = current / part
            if current.exists() and current.is_symlink():
                raise ApprovalRuntimeIntegrationError(field_name + "_is_symlink")
        resolved = candidate.resolve(strict=False)
        if not resolved.is_relative_to(self.runtime_root):
            raise ApprovalRuntimeIntegrationError(field_name + "_escapes_runtime_root")
        return resolved


def run_approval_gated_minimal_controlled_wal_preflight(
    payload: Mapping[str, object],
    approval_runtime: FileBackedApprovalRuntimeIntegration,
    append_callable: Callable[[MinimalControlledWalAdapterRecord], object],
    *,
    observed_at: str | None = None,
) -> ApprovalRuntimeGatedPreflightResponse:
    if not isinstance(approval_runtime, FileBackedApprovalRuntimeIntegration):
        raise ApprovalRuntimeIntegrationError("approval_runtime_required")
    if not callable(append_callable):
        raise ApprovalRuntimeIntegrationError("append_callable_required")
    data = _validated_gated_payload(payload)
    consumption = approval_runtime.consume_for_preflight(
        approval_admission_hash=str(data["approval_admission_hash"]),
        task_id=str(data["task_id"]),
        run_id=str(data["run_id"]),
        preflight_id=str(data["preflight_id"]),
        approval_scope=str(data["approval_scope"]),
        consumed_at=observed_at,
    )
    if not consumption.accepted:
        return ApprovalRuntimeGatedPreflightResponse(
            integration_version=APPROVAL_RUNTIME_INTEGRATION_VERSION,
            accepted=False,
            execution_may_proceed=False,
            rejection_reasons=consumption.failures,
            approval_consumption_receipt_hash=consumption.receipt_hash,
            preflight_api_response_hash=ZERO_HASH,
            task_id=str(data["task_id"]),
            run_id=str(data["run_id"]),
            preflight_id=str(data["preflight_id"]),
        )

    forwarded = dict(data)
    forwarded.pop("approval_admission_hash", None)
    forwarded.pop("approval_scope", None)
    forwarded["approved_for_wal_gated_preflight"] = True
    forwarded["approval_token_id"] = consumption.approval_id
    preflight = run_human_invoked_minimal_controlled_wal_gated_preflight(
        forwarded,
        append_callable,
    )
    return _response_from_preflight(consumption, preflight)


def compute_integrated_approval_receipt_hash(
    receipt: ApprovalRuntimeIntegratedReceipt | Mapping[str, object],
) -> str:
    return _hash_dataclass_or_mapping(receipt, "receipt_hash")


def compute_approval_consumption_receipt_hash(
    receipt: ApprovalRuntimeConsumptionReceipt | Mapping[str, object],
) -> str:
    return _hash_dataclass_or_mapping(receipt, "receipt_hash")


def compute_approval_gated_preflight_response_hash(
    response: ApprovalRuntimeGatedPreflightResponse | Mapping[str, object],
) -> str:
    return _hash_dataclass_or_mapping(response, "response_hash")


def _validated_gated_payload(payload: Mapping[str, object]) -> dict[str, object]:
    if not isinstance(payload, Mapping):
        raise ApprovalRuntimeIntegrationError("gated_preflight_payload_must_be_mapping")
    data = dict(payload)
    for field_name in ("approval_admission_hash", "approval_scope", "task_id", "run_id", "preflight_id"):
        if field_name not in data:
            raise ApprovalRuntimeIntegrationError(field_name + "_required")
    _require_sha256(data["approval_admission_hash"], "approval_admission_hash")
    _require_nonempty_string(data["approval_scope"], "approval_scope")
    if set(data).intersection(_CALLER_APPROVAL_FIELDS):
        raise ApprovalRuntimeIntegrationError("caller_supplied_approval_flag_forbidden")
    for field_name in ("human_invoked", "single_run_scope"):
        if data.get(field_name) is not True:
            raise ApprovalRuntimeIntegrationError(field_name + "_required_true")
    return data


def _response_from_preflight(
    consumption: ApprovalRuntimeConsumptionReceipt,
    preflight: MinimalControlledWalGatedPreflightApiResponse,
) -> ApprovalRuntimeGatedPreflightResponse:
    return ApprovalRuntimeGatedPreflightResponse(
        integration_version=APPROVAL_RUNTIME_INTEGRATION_VERSION,
        accepted=preflight.accepted,
        execution_may_proceed=preflight.execution_may_proceed,
        rejection_reasons=preflight.rejection_reasons
        if not preflight.accepted
        else (),
        approval_consumption_receipt_hash=consumption.receipt_hash,
        preflight_api_response_hash=preflight.api_response_hash,
        task_id=preflight.task_id,
        run_id=preflight.run_id,
        preflight_id=preflight.preflight_id,
    )


def _hash_dataclass_or_mapping(value: object, hash_field: str) -> str:
    data = value.as_dict() if hasattr(value, "as_dict") else _json_ready(dict(value))  # type: ignore[arg-type]
    data.pop(hash_field, None)
    return _sha256_json(data)


def _install_or_verify_hash(target: object, field_name: str, hash_fn: object) -> None:
    expected = hash_fn(target)  # type: ignore[operator]
    current = getattr(target, field_name)
    if current:
        _require_sha256(current, field_name)
        if current != expected:
            raise ApprovalRuntimeIntegrationError(field_name + "_mismatch")
        return
    object.__setattr__(target, field_name, expected)


def _approval_id(approval_admission_hash: str) -> str:
    _require_sha256(approval_admission_hash, "approval_admission_hash")
    return "approval-" + approval_admission_hash.removeprefix("sha256:")[:32]


def _validate_runtime_root(root: Path) -> Path:
    raw = root.expanduser()
    if not str(raw):
        raise ApprovalRuntimeIntegrationError("runtime_root_required")
    if raw.exists() and raw.is_symlink():
        raise ApprovalRuntimeIntegrationError("runtime_root_is_symlink")
    if raw.exists() and not raw.is_dir():
        raise ApprovalRuntimeIntegrationError("runtime_root_must_be_directory")
    resolved = raw.resolve(strict=False)
    _reject_secret_or_git_path(resolved, "runtime_root")
    return resolved


def _validate_relpath_text(value: str, field_name: str, *, allow_empty: bool) -> str:
    if not isinstance(value, str):
        raise ApprovalRuntimeIntegrationError(field_name + "_must_be_string")
    if not value:
        if allow_empty:
            return ""
        raise ApprovalRuntimeIntegrationError(field_name + "_required")
    if "\\" in value:
        raise ApprovalRuntimeIntegrationError(field_name + "_must_use_posix_separators")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts:
        raise ApprovalRuntimeIntegrationError(field_name + "_must_be_relative")
    _reject_secret_or_git_path(Path(*path.parts), field_name)
    return str(path)


def _reject_secret_or_git_path(path: Path, field_name: str) -> None:
    if ".git" in path.parts:
        raise ApprovalRuntimeIntegrationError(field_name + "_cannot_enter_git")
    if any(_SECRET_PATH_PATTERN.fullmatch(part) for part in path.parts):
        raise ApprovalRuntimeIntegrationError(field_name + "_secret_like")


def _normalize_failures(value: object) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)) or isinstance(value, (str, bytes)):
        raise ApprovalRuntimeIntegrationError("failures_must_be_sequence")
    failures = tuple(str(item) for item in value)
    for failure in failures:
        _require_nonempty_string(failure, "failure")
    return tuple(_dedupe(failures))


def _timestamp(value: str | None) -> str:
    if value is None:
        return datetime.now(timezone.utc).isoformat(timespec="microseconds")
    _require_nonempty_string(value, "timestamp")
    _parse_timestamp(value, "timestamp")
    return value


def _parse_timestamp(value: str, field_name: str) -> datetime:
    _require_nonempty_string(value, field_name)
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ApprovalRuntimeIntegrationError(field_name + "_must_be_isoformat") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _require_nonempty_string(value: object, field_name: str) -> None:
    if not isinstance(value, str) or not value:
        raise ApprovalRuntimeIntegrationError(field_name + "_required")
    if _SECRET_KEY_PATTERN.search(value):
        raise ApprovalRuntimeIntegrationError(field_name + "_secret_like")


def _require_sha256(value: object, field_name: str) -> None:
    if not isinstance(value, str) or not _SHA256_PATTERN.fullmatch(value):
        raise ApprovalRuntimeIntegrationError(field_name + "_must_be_sha256")


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
            if _SECRET_KEY_PATTERN.search(key_text) and not key_text.endswith("_hash"):
                raise ApprovalRuntimeIntegrationError("json_field_secret_like:" + key_text)
            result[key_text] = _json_ready(item)
        return result
    if isinstance(value, tuple):
        return [_json_ready(item) for item in value]
    if isinstance(value, list):
        return [_json_ready(item) for item in value]
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    raise ApprovalRuntimeIntegrationError(
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


def _dedupe(values: tuple[str, ...] | list[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value not in seen:
            result.append(value)
            seen.add(value)
    return tuple(result)
