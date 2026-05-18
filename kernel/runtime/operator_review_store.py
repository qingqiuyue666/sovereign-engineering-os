"""Durable local store for operator review sessions and receipts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import tempfile
from typing import Any

from kernel.audit.hashchain import canonical_json, digest_payload
from kernel.runtime._strict_validation import strict_digest, strict_nonempty_string
from kernel.runtime.operator_review_receipt import (
    ApprovalReceipt,
    RejectionReceipt,
    build_approval_receipt,
    build_rejection_receipt,
    validate_approval_receipt,
    validate_rejection_receipt,
)
from kernel.runtime.operator_review_session import (
    OperatorReviewSession,
    build_operator_review_session,
    validate_review_session_material,
)

__all__ = [
    "OperatorReviewAppendReceipt",
    "OperatorReviewHistory",
    "OperatorReviewStoreVerificationReceipt",
    "OperatorReviewStore",
]

_POLICY_VERSION = "operator-review-store-v1"
_CODE_VERSION = "0.1.0"
_SESSION_RECORD_TYPE = "operator_review_session"
_APPROVAL_RECORD_TYPE = "operator_approval_receipt"
_REJECTION_RECORD_TYPE = "operator_rejection_receipt"
_GENESIS_HASH = "sha256:" + ("0" * 64)

_RECORD_FIELDS = frozenset(
    {
        "record_type",
        "store_id",
        "payload",
        "payload_content_hash",
        "record_sequence",
        "previous_record_hash",
        "record_hash",
        "policy_version",
        "code_version",
        "observed_at",
    }
)
_SESSION_FIELDS = frozenset(
    {
        "session_id",
        "run_id",
        "task_id",
        "review_packet_hash",
        "promotion_receipt_hash",
        "promotion_decision",
        "promotion_accepted",
        "rollback_plan_hash",
        "operator_action",
        "decision_reason_code",
        "policy_version",
        "code_version",
        "content_hash",
        "observed_at",
    }
)
_APPROVAL_FIELDS = frozenset(
    {
        "session_id",
        "run_id",
        "task_id",
        "review_packet_hash",
        "promotion_receipt_hash",
        "operator_action",
        "approval_scope",
        "approval_reason_code",
        "approved_for_next_stage",
        "production_autonomy_enabled",
        "live_execution_enabled",
        "policy_version",
        "code_version",
        "content_hash",
        "observed_at",
    }
)
_REJECTION_FIELDS = frozenset(
    {
        "session_id",
        "run_id",
        "task_id",
        "review_packet_hash",
        "promotion_receipt_hash",
        "operator_action",
        "rejection_reason_code",
        "rollback_plan_hash",
        "approved_for_next_stage",
        "production_autonomy_enabled",
        "live_execution_enabled",
        "policy_version",
        "code_version",
        "content_hash",
        "observed_at",
    }
)
_FORBIDDEN_FIELD_MARKERS = (
    "raw_prompt",
    "raw_response",
    "raw_provider_response",
    "raw_exception",
    "raw_traceback",
    "env",
    "secret",
    "credential",
    "token",
    "api_key",
    "password",
    "private_key",
    "authorization",
)


@dataclass(frozen=True)
class OperatorReviewAppendReceipt:
    """Deterministic receipt for one review-store append."""

    store_id: str
    record_type: str
    record_sequence: int
    session_id: str
    payload_content_hash: str
    previous_record_hash: str | None
    record_hash: str
    policy_version: str = _POLICY_VERSION
    code_version: str = _CODE_VERSION
    content_hash: str = ""
    observed_at: str = ""

    def deterministic_material(self) -> dict[str, object]:
        return {
            "code_version": self.code_version,
            "payload_content_hash": self.payload_content_hash,
            "policy_version": self.policy_version,
            "previous_record_hash": self.previous_record_hash,
            "record_hash": self.record_hash,
            "record_sequence": self.record_sequence,
            "record_type": self.record_type,
            "session_id": self.session_id,
            "store_id": self.store_id,
        }

    def as_dict(self) -> dict[str, object]:
        payload = self.deterministic_material()
        payload["content_hash"] = self.content_hash
        payload["observed_at"] = self.observed_at
        return payload


@dataclass(frozen=True)
class OperatorReviewHistory:
    """Rebuilt read-only review history."""

    store_id: str
    sessions: tuple[OperatorReviewSession, ...]
    approval_receipts: tuple[ApprovalReceipt, ...]
    rejection_receipts: tuple[RejectionReceipt, ...]
    policy_version: str = _POLICY_VERSION
    code_version: str = _CODE_VERSION
    content_hash: str = ""

    def deterministic_material(self) -> dict[str, object]:
        return {
            "approval_receipt_hashes": [receipt.content_hash for receipt in self.approval_receipts],
            "code_version": self.code_version,
            "policy_version": self.policy_version,
            "rejection_receipt_hashes": [receipt.content_hash for receipt in self.rejection_receipts],
            "session_hashes": [session.content_hash for session in self.sessions],
            "store_id": self.store_id,
        }


@dataclass(frozen=True)
class OperatorReviewStoreVerificationReceipt:
    """Deterministic receipt for a complete review-store check."""

    store_id: str
    total_records: int
    session_count: int
    approval_count: int
    rejection_count: int
    review_history_hash: str
    valid: bool
    reasons: tuple[str, ...]
    policy_version: str = _POLICY_VERSION
    code_version: str = _CODE_VERSION
    content_hash: str = ""
    observed_at: str = ""

    def deterministic_material(self) -> dict[str, object]:
        return {
            "approval_count": self.approval_count,
            "code_version": self.code_version,
            "policy_version": self.policy_version,
            "reasons": list(self.reasons),
            "rejection_count": self.rejection_count,
            "review_history_hash": self.review_history_hash,
            "session_count": self.session_count,
            "store_id": self.store_id,
            "total_records": self.total_records,
            "valid": self.valid,
        }

    def as_dict(self) -> dict[str, object]:
        payload = self.deterministic_material()
        payload["content_hash"] = self.content_hash
        payload["observed_at"] = self.observed_at
        return payload


class OperatorReviewStore:
    """Append-only JSONL store for operator review sessions and receipts."""

    def __init__(self, path: str | Path, *, store_id: str) -> None:
        if not strict_nonempty_string(store_id):
            raise ValueError("store_id_must_be_nonempty_string")
        self.path = Path(path)
        self.store_id = store_id

    def append_session(self, session: OperatorReviewSession) -> OperatorReviewAppendReceipt:
        if not validate_review_session_material(session):
            raise ValueError("review_session_validation_failed")
        history = self.rebuild_review_history()
        if session.session_id in {existing.session_id for existing in history.sessions}:
            raise ValueError("duplicate_review_session")
        return self._append_payload(_SESSION_RECORD_TYPE, session)

    def append_approval(self, receipt: ApprovalReceipt) -> OperatorReviewAppendReceipt:
        if not validate_approval_receipt(receipt):
            raise ValueError("approval_receipt_validation_failed")
        history = self.rebuild_review_history()
        _validate_receipt_against_history(receipt, history, final_action="approved")
        return self._append_payload(_APPROVAL_RECORD_TYPE, receipt)

    def append_rejection(self, receipt: RejectionReceipt) -> OperatorReviewAppendReceipt:
        if not validate_rejection_receipt(receipt):
            raise ValueError("rejection_receipt_validation_failed")
        history = self.rebuild_review_history()
        _validate_receipt_against_history(receipt, history, final_action="rejected")
        return self._append_payload(_REJECTION_RECORD_TYPE, receipt)

    def load_sessions(self) -> tuple[OperatorReviewSession, ...]:
        return self.rebuild_review_history().sessions

    def load_approval_receipts(self) -> tuple[ApprovalReceipt, ...]:
        return self.rebuild_review_history().approval_receipts

    def load_rejection_receipts(self) -> tuple[RejectionReceipt, ...]:
        return self.rebuild_review_history().rejection_receipts

    def rebuild_review_history(self) -> OperatorReviewHistory:
        records = self._load_records()
        sessions: list[OperatorReviewSession] = []
        approvals: list[ApprovalReceipt] = []
        rejections: list[RejectionReceipt] = []
        seen_sessions: set[str] = set()
        final_sessions: dict[str, str] = {}

        for record in records:
            record_type = record["record_type"]
            if record_type == _SESSION_RECORD_TYPE:
                session = _session_from_payload(record["payload"])
                if session.session_id in seen_sessions:
                    raise ValueError("duplicate_review_session")
                seen_sessions.add(session.session_id)
                sessions.append(session)
            elif record_type == _APPROVAL_RECORD_TYPE:
                approval = _approval_from_payload(record["payload"])
                history = _history(self.store_id, sessions, approvals, rejections)
                _validate_receipt_against_history(approval, history, final_action="approved")
                final_sessions[approval.session_id] = "approved"
                approvals.append(approval)
            elif record_type == _REJECTION_RECORD_TYPE:
                rejection = _rejection_from_payload(record["payload"])
                history = _history(self.store_id, sessions, approvals, rejections)
                _validate_receipt_against_history(rejection, history, final_action="rejected")
                final_sessions[rejection.session_id] = "rejected"
                rejections.append(rejection)
            else:
                raise ValueError("record_type_mismatch")

        return _history(self.store_id, sessions, approvals, rejections)

    def verify_store(
        self,
        *,
        observed_at: str | None = None,
    ) -> OperatorReviewStoreVerificationReceipt:
        observed = _observed_at(observed_at)
        try:
            records = self._load_records()
            history = self.rebuild_review_history()
            receipt = OperatorReviewStoreVerificationReceipt(
                store_id=self.store_id,
                total_records=len(records),
                session_count=len(history.sessions),
                approval_count=len(history.approval_receipts),
                rejection_count=len(history.rejection_receipts),
                review_history_hash=history.content_hash,
                valid=True,
                reasons=(),
                content_hash="",
                observed_at=observed,
            )
        except ValueError as exc:
            receipt = OperatorReviewStoreVerificationReceipt(
                store_id=self.store_id,
                total_records=0,
                session_count=0,
                approval_count=0,
                rejection_count=0,
                review_history_hash=_GENESIS_HASH,
                valid=False,
                reasons=(str(exc),),
                content_hash="",
                observed_at=observed,
            )
        return _with_verification_hash(receipt)

    def _append_payload(
        self,
        record_type: str,
        payload_obj: OperatorReviewSession | ApprovalReceipt | RejectionReceipt,
    ) -> OperatorReviewAppendReceipt:
        records = self._load_records()
        record = _build_record(
            store_id=self.store_id,
            record_type=record_type,
            payload=payload_obj.as_dict(),
            payload_content_hash=payload_obj.content_hash,
            record_sequence=len(records) + 1,
            previous_record_hash=records[-1]["record_hash"] if records else None,
        )
        _validate_record(record, store_id=self.store_id, expected_sequence=len(records) + 1)
        self._write_records(tuple(records + [record]))
        receipt = OperatorReviewAppendReceipt(
            store_id=self.store_id,
            record_type=record_type,
            record_sequence=record["record_sequence"],
            session_id=payload_obj.session_id,
            payload_content_hash=payload_obj.content_hash,
            previous_record_hash=record["previous_record_hash"],
            record_hash=record["record_hash"],
            content_hash="",
            observed_at=_observed_at(None),
        )
        return _with_append_hash(receipt)

    def _load_records(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        raw = self.path.read_text(encoding="utf-8")
        if raw == "":
            return []
        if not raw.endswith("\n"):
            raise ValueError("partial_final_record")
        records: list[dict[str, Any]] = []
        previous_hash: str | None = None
        for index, line in enumerate(raw.splitlines(), start=1):
            if not line.strip():
                raise ValueError(f"blank_record_at_sequence_{index}")
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"malformed_json_record_{index}") from exc
            _validate_record(record, store_id=self.store_id, expected_sequence=index)
            if record["previous_record_hash"] != previous_hash:
                raise ValueError(f"previous_record_hash_mismatch_at_sequence_{index}")
            previous_hash = record["record_hash"]
            records.append(record)
        return records

    def _write_records(self, records: tuple[dict[str, Any], ...]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = "".join(canonical_json(record) + "\n" for record in records)
        temp_name: str | None = None
        try:
            with tempfile.NamedTemporaryFile(
                "w",
                encoding="utf-8",
                dir=self.path.parent,
                prefix=f".{self.path.name}.",
                suffix=".tmp",
                delete=False,
            ) as handle:
                temp_name = handle.name
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            Path(temp_name).replace(self.path)
            directory_fd = os.open(self.path.parent, os.O_RDONLY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        except Exception:
            if temp_name is not None:
                temp_path = Path(temp_name)
                if temp_path.exists():
                    temp_path.unlink()
            raise


def _build_record(
    *,
    store_id: str,
    record_type: str,
    payload: dict[str, object],
    payload_content_hash: str,
    record_sequence: int,
    previous_record_hash: str | None,
) -> dict[str, Any]:
    record: dict[str, Any] = {
        "record_type": record_type,
        "store_id": store_id,
        "payload": payload,
        "payload_content_hash": payload_content_hash,
        "record_sequence": record_sequence,
        "previous_record_hash": previous_record_hash,
        "policy_version": _POLICY_VERSION,
        "code_version": _CODE_VERSION,
        "observed_at": _observed_at(None),
    }
    record["record_hash"] = digest_payload(_record_hash_material(record))
    return record


def _validate_record(record: Any, *, store_id: str, expected_sequence: int) -> None:
    if not isinstance(record, dict):
        raise ValueError("record_must_be_object")
    _reject_forbidden_fields(record)
    if set(record) != _RECORD_FIELDS:
        raise ValueError("record_fields_mismatch")
    if record["record_type"] not in {_SESSION_RECORD_TYPE, _APPROVAL_RECORD_TYPE, _REJECTION_RECORD_TYPE}:
        raise ValueError("record_type_mismatch")
    if record["store_id"] != store_id:
        raise ValueError("store_id_mismatch")
    if record["policy_version"] != _POLICY_VERSION:
        raise ValueError("policy_version_mismatch")
    if record["code_version"] != _CODE_VERSION:
        raise ValueError("code_version_mismatch")
    if record["record_sequence"] != expected_sequence:
        raise ValueError("record_sequence_mismatch")
    if record["previous_record_hash"] is not None and not strict_digest(record["previous_record_hash"]):
        raise ValueError("previous_record_hash_must_be_valid_digest")
    if not strict_digest(record["payload_content_hash"]):
        raise ValueError("payload_content_hash_must_be_valid_digest")
    if not strict_digest(record["record_hash"]):
        raise ValueError("record_hash_must_be_valid_digest")
    if not strict_nonempty_string(record["observed_at"]):
        raise ValueError("observed_at_must_be_nonempty_string")
    payload_hash = _payload_content_hash(record["record_type"], record["payload"])
    if payload_hash != record["payload_content_hash"]:
        raise ValueError("payload_content_hash_mismatch")
    if record["record_hash"] != digest_payload(_record_hash_material(record)):
        raise ValueError("record_hash_mismatch")


def _record_hash_material(record: dict[str, Any]) -> dict[str, object]:
    return {
        "code_version": record["code_version"],
        "payload": _payload_deterministic_material(record["record_type"], record["payload"]),
        "payload_content_hash": record["payload_content_hash"],
        "policy_version": record["policy_version"],
        "previous_record_hash": record["previous_record_hash"],
        "record_sequence": record["record_sequence"],
        "record_type": record["record_type"],
        "store_id": record["store_id"],
    }


def _payload_content_hash(record_type: str, payload: Any) -> str:
    if record_type == _SESSION_RECORD_TYPE:
        return _session_from_payload(payload).content_hash
    if record_type == _APPROVAL_RECORD_TYPE:
        return _approval_from_payload(payload).content_hash
    if record_type == _REJECTION_RECORD_TYPE:
        return _rejection_from_payload(payload).content_hash
    raise ValueError("record_type_mismatch")


def _payload_deterministic_material(record_type: str, payload: Any) -> dict[str, object]:
    if record_type == _SESSION_RECORD_TYPE:
        return _session_from_payload(payload).deterministic_material()
    if record_type == _APPROVAL_RECORD_TYPE:
        return _approval_from_payload(payload).deterministic_material()
    if record_type == _REJECTION_RECORD_TYPE:
        return _rejection_from_payload(payload).deterministic_material()
    raise ValueError("record_type_mismatch")


def _session_from_payload(payload: Any) -> OperatorReviewSession:
    if not isinstance(payload, dict):
        raise ValueError("session_payload_must_be_object")
    _reject_forbidden_fields(payload)
    if set(payload) != _SESSION_FIELDS:
        raise ValueError("session_fields_mismatch")
    session = build_operator_review_session(
        session_id=payload["session_id"],
        run_id=payload["run_id"],
        task_id=payload["task_id"],
        review_packet_hash=payload["review_packet_hash"],
        promotion_receipt_hash=payload["promotion_receipt_hash"],
        promotion_decision=payload["promotion_decision"],
        promotion_accepted=payload["promotion_accepted"],
        rollback_plan_hash=payload["rollback_plan_hash"],
        operator_action=payload["operator_action"],
        decision_reason_code=payload["decision_reason_code"],
        policy_version=payload["policy_version"],
        code_version=payload["code_version"],
        observed_at=payload["observed_at"],
    )
    if session.content_hash != payload["content_hash"]:
        raise ValueError("session_content_hash_mismatch")
    return session


def _approval_from_payload(payload: Any) -> ApprovalReceipt:
    if not isinstance(payload, dict):
        raise ValueError("approval_payload_must_be_object")
    _reject_forbidden_fields(payload)
    if set(payload) != _APPROVAL_FIELDS:
        raise ValueError("approval_fields_mismatch")
    receipt = build_approval_receipt(
        session_id=payload["session_id"],
        run_id=payload["run_id"],
        task_id=payload["task_id"],
        review_packet_hash=payload["review_packet_hash"],
        promotion_receipt_hash=payload["promotion_receipt_hash"],
        approval_scope=payload["approval_scope"],
        approval_reason_code=payload["approval_reason_code"],
        approved_for_next_stage=payload["approved_for_next_stage"],
        policy_version=payload["policy_version"],
        code_version=payload["code_version"],
        observed_at=payload["observed_at"],
    )
    if receipt.deterministic_material() != {
        key: payload[key] for key in receipt.deterministic_material()
    }:
        raise ValueError("approval_payload_material_mismatch")
    if receipt.content_hash != payload["content_hash"]:
        raise ValueError("approval_content_hash_mismatch")
    return receipt


def _rejection_from_payload(payload: Any) -> RejectionReceipt:
    if not isinstance(payload, dict):
        raise ValueError("rejection_payload_must_be_object")
    _reject_forbidden_fields(payload)
    if set(payload) != _REJECTION_FIELDS:
        raise ValueError("rejection_fields_mismatch")
    receipt = build_rejection_receipt(
        session_id=payload["session_id"],
        run_id=payload["run_id"],
        task_id=payload["task_id"],
        review_packet_hash=payload["review_packet_hash"],
        promotion_receipt_hash=payload["promotion_receipt_hash"],
        rejection_reason_code=payload["rejection_reason_code"],
        rollback_plan_hash=payload["rollback_plan_hash"],
        policy_version=payload["policy_version"],
        code_version=payload["code_version"],
        observed_at=payload["observed_at"],
    )
    if receipt.deterministic_material() != {
        key: payload[key] for key in receipt.deterministic_material()
    }:
        raise ValueError("rejection_payload_material_mismatch")
    if receipt.content_hash != payload["content_hash"]:
        raise ValueError("rejection_content_hash_mismatch")
    return receipt


def _validate_receipt_against_history(
    receipt: ApprovalReceipt | RejectionReceipt,
    history: OperatorReviewHistory,
    *,
    final_action: str,
) -> None:
    sessions_by_id = {session.session_id: session for session in history.sessions}
    if receipt.session_id not in sessions_by_id:
        raise ValueError("receipt_session_not_found")
    if any(existing.session_id == receipt.session_id for existing in history.approval_receipts):
        raise ValueError("duplicate_approval_for_session")
    if any(existing.session_id == receipt.session_id for existing in history.rejection_receipts):
        raise ValueError("approval_after_rejection" if final_action == "approved" else "duplicate_rejection_for_session")
    session = sessions_by_id[receipt.session_id]
    if receipt.run_id != session.run_id or receipt.task_id != session.task_id:
        raise ValueError("receipt_session_identity_mismatch")
    if receipt.review_packet_hash != session.review_packet_hash:
        raise ValueError("receipt_review_packet_hash_mismatch")
    if receipt.promotion_receipt_hash != session.promotion_receipt_hash:
        raise ValueError("receipt_promotion_receipt_hash_mismatch")
    if final_action == "rejected" and any(
        existing.session_id == receipt.session_id for existing in history.approval_receipts
    ):
        raise ValueError("rejection_after_approval")


def _history(
    store_id: str,
    sessions: list[OperatorReviewSession],
    approvals: list[ApprovalReceipt],
    rejections: list[RejectionReceipt],
) -> OperatorReviewHistory:
    history = OperatorReviewHistory(
        store_id=store_id,
        sessions=tuple(sessions),
        approval_receipts=tuple(approvals),
        rejection_receipts=tuple(rejections),
        content_hash="",
    )
    return OperatorReviewHistory(
        store_id=history.store_id,
        sessions=history.sessions,
        approval_receipts=history.approval_receipts,
        rejection_receipts=history.rejection_receipts,
        policy_version=history.policy_version,
        code_version=history.code_version,
        content_hash=digest_payload(history.deterministic_material()),
    )


def _with_append_hash(receipt: OperatorReviewAppendReceipt) -> OperatorReviewAppendReceipt:
    return OperatorReviewAppendReceipt(
        store_id=receipt.store_id,
        record_type=receipt.record_type,
        record_sequence=receipt.record_sequence,
        session_id=receipt.session_id,
        payload_content_hash=receipt.payload_content_hash,
        previous_record_hash=receipt.previous_record_hash,
        record_hash=receipt.record_hash,
        policy_version=receipt.policy_version,
        code_version=receipt.code_version,
        content_hash=digest_payload(receipt.deterministic_material()),
        observed_at=receipt.observed_at,
    )


def _with_verification_hash(
    receipt: OperatorReviewStoreVerificationReceipt,
) -> OperatorReviewStoreVerificationReceipt:
    return OperatorReviewStoreVerificationReceipt(
        store_id=receipt.store_id,
        total_records=receipt.total_records,
        session_count=receipt.session_count,
        approval_count=receipt.approval_count,
        rejection_count=receipt.rejection_count,
        review_history_hash=receipt.review_history_hash,
        valid=receipt.valid,
        reasons=receipt.reasons,
        policy_version=receipt.policy_version,
        code_version=receipt.code_version,
        content_hash=digest_payload(receipt.deterministic_material()),
        observed_at=receipt.observed_at,
    )


def _reject_forbidden_fields(value: Any) -> None:
    if isinstance(value, dict):
        for key, nested in value.items():
            lowered = str(key).lower()
            if any(marker in lowered for marker in _FORBIDDEN_FIELD_MARKERS):
                raise ValueError("forbidden_field_present")
            _reject_forbidden_fields(nested)
    elif isinstance(value, list):
        for nested in value:
            _reject_forbidden_fields(nested)


def _observed_at(value: str | None) -> str:
    if value is None:
        return datetime.now(timezone.utc).isoformat()
    if not strict_nonempty_string(value):
        raise ValueError("observed_at_must_be_nonempty_string")
    return value
