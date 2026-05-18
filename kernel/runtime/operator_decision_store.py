"""Durable local store for operator decision ledger entries."""

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
from kernel.runtime.operator_decision_ledger import (
    OperatorDecisionLedger,
    OperatorDecisionLedgerEntry,
    build_ledger_entry,
    validate_ledger_entry,
)
from kernel.runtime.operator_decision_snapshot import (
    OperatorDecisionLedgerSnapshot,
    build_ledger_snapshot,
)

__all__ = [
    "OperatorDecisionAppendReceipt",
    "OperatorDecisionStoreVerificationReceipt",
    "OperatorDecisionStore",
]

_POLICY_VERSION = "operator-decision-store-v1"
_CODE_VERSION = "0.1.0"
_RECORD_TYPE = "operator_decision_ledger_entry"
_GENESIS_HASH = "sha256:" + ("0" * 64)

_RECORD_FIELDS = frozenset(
    {
        "record_type",
        "store_id",
        "entry",
        "entry_content_hash",
        "record_sequence",
        "previous_record_hash",
        "record_hash",
        "policy_version",
        "code_version",
        "observed_at",
    }
)
_ENTRY_FIELDS = frozenset(
    {
        "entry_id",
        "session_id",
        "run_id",
        "task_id",
        "operator_action",
        "review_session_hash",
        "approval_receipt_hash",
        "rejection_receipt_hash",
        "rollback_plan_hash",
        "previous_entry_hash",
        "sequence_number",
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
class OperatorDecisionAppendReceipt:
    """Deterministic receipt for one durable decision-store append."""

    store_id: str
    record_sequence: int
    entry_id: str
    entry_content_hash: str
    previous_record_hash: str | None
    record_hash: str
    decision_chain_head: str
    policy_version: str = _POLICY_VERSION
    code_version: str = _CODE_VERSION
    content_hash: str = ""
    observed_at: str = ""

    def deterministic_material(self) -> dict[str, object]:
        return {
            "code_version": self.code_version,
            "decision_chain_head": self.decision_chain_head,
            "entry_content_hash": self.entry_content_hash,
            "entry_id": self.entry_id,
            "policy_version": self.policy_version,
            "previous_record_hash": self.previous_record_hash,
            "record_hash": self.record_hash,
            "record_sequence": self.record_sequence,
            "store_id": self.store_id,
        }

    def as_dict(self) -> dict[str, object]:
        payload = self.deterministic_material()
        payload["content_hash"] = self.content_hash
        payload["observed_at"] = self.observed_at
        return payload


@dataclass(frozen=True)
class OperatorDecisionStoreVerificationReceipt:
    """Deterministic receipt for a complete durable decision-store check."""

    store_id: str
    total_records: int
    decision_chain_head: str
    snapshot_hash: str
    valid: bool
    reasons: tuple[str, ...]
    policy_version: str = _POLICY_VERSION
    code_version: str = _CODE_VERSION
    content_hash: str = ""
    observed_at: str = ""

    def deterministic_material(self) -> dict[str, object]:
        return {
            "code_version": self.code_version,
            "decision_chain_head": self.decision_chain_head,
            "policy_version": self.policy_version,
            "reasons": list(self.reasons),
            "snapshot_hash": self.snapshot_hash,
            "store_id": self.store_id,
            "total_records": self.total_records,
            "valid": self.valid,
        }

    def as_dict(self) -> dict[str, object]:
        payload = self.deterministic_material()
        payload["content_hash"] = self.content_hash
        payload["observed_at"] = self.observed_at
        return payload


class OperatorDecisionStore:
    """Append-only JSONL store for operator decision ledger entries."""

    def __init__(self, path: str | Path, *, store_id: str) -> None:
        if not strict_nonempty_string(store_id):
            raise ValueError("store_id_must_be_nonempty_string")
        self.path = Path(path)
        self.store_id = store_id

    def append_entry(self, entry: OperatorDecisionLedgerEntry) -> OperatorDecisionAppendReceipt:
        """Validate and append one ledger entry to the durable store."""

        if not validate_ledger_entry(entry):
            raise ValueError("ledger_entry_validation_failed")
        records = self._load_records()
        entries = [_entry_from_payload(record["entry"]) for record in records]
        ledger = _ledger_from_entries(entries)
        ledger.append(entry)

        record = _build_record(
            store_id=self.store_id,
            entry=entry,
            record_sequence=len(records) + 1,
            previous_record_hash=records[-1]["record_hash"] if records else None,
        )
        _validate_record(record, store_id=self.store_id, expected_sequence=len(records) + 1)
        self._write_records(tuple(records + [record]))

        receipt = OperatorDecisionAppendReceipt(
            store_id=self.store_id,
            record_sequence=record["record_sequence"],
            entry_id=entry.entry_id,
            entry_content_hash=entry.content_hash,
            previous_record_hash=record["previous_record_hash"],
            record_hash=record["record_hash"],
            decision_chain_head=ledger.decision_chain_head,
            content_hash="",
            observed_at=_observed_at(None),
        )
        return _with_append_hash(receipt)

    def load_entries(self) -> tuple[OperatorDecisionLedgerEntry, ...]:
        """Load entries from disk and validate complete store integrity."""

        records = self._load_records()
        entries = tuple(_entry_from_payload(record["entry"]) for record in records)
        _ledger_from_entries(entries)
        return entries

    def rebuild_ledger(self) -> OperatorDecisionLedger:
        """Reconstruct the in-memory ledger through existing append validation."""

        return _ledger_from_entries(self.load_entries())

    def export_snapshot(self) -> OperatorDecisionLedgerSnapshot:
        """Build a deterministic snapshot from the rebuilt durable ledger."""

        return build_ledger_snapshot(ledger_id=self.store_id, ledger=self.rebuild_ledger())

    def verify_store(
        self,
        *,
        observed_at: str | None = None,
    ) -> OperatorDecisionStoreVerificationReceipt:
        """Return a deterministic verification receipt for the full store."""

        observed = _observed_at(observed_at)
        try:
            ledger = self.rebuild_ledger()
            snapshot = build_ledger_snapshot(ledger_id=self.store_id, ledger=ledger)
            receipt = OperatorDecisionStoreVerificationReceipt(
                store_id=self.store_id,
                total_records=ledger.total_entries,
                decision_chain_head=ledger.decision_chain_head,
                snapshot_hash=snapshot.content_hash,
                valid=True,
                reasons=(),
                content_hash="",
                observed_at=observed,
            )
        except ValueError as exc:
            receipt = OperatorDecisionStoreVerificationReceipt(
                store_id=self.store_id,
                total_records=0,
                decision_chain_head=_GENESIS_HASH,
                snapshot_hash=_GENESIS_HASH,
                valid=False,
                reasons=(str(exc),),
                content_hash="",
                observed_at=observed,
            )
        return _with_verification_hash(receipt)

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
    entry: OperatorDecisionLedgerEntry,
    record_sequence: int,
    previous_record_hash: str | None,
) -> dict[str, Any]:
    record: dict[str, Any] = {
        "record_type": _RECORD_TYPE,
        "store_id": store_id,
        "entry": entry.as_dict(),
        "entry_content_hash": entry.content_hash,
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
    if record["record_type"] != _RECORD_TYPE:
        raise ValueError("record_type_mismatch")
    if record["store_id"] != store_id:
        raise ValueError("store_id_mismatch")
    if record["policy_version"] != _POLICY_VERSION:
        raise ValueError("policy_version_mismatch")
    if record["code_version"] != _CODE_VERSION:
        raise ValueError("code_version_mismatch")
    if record["record_sequence"] != expected_sequence:
        raise ValueError("record_sequence_mismatch")
    if not strict_nonempty_string(record["observed_at"]):
        raise ValueError("observed_at_must_be_nonempty_string")
    if record["previous_record_hash"] is not None and not strict_digest(record["previous_record_hash"]):
        raise ValueError("previous_record_hash_must_be_valid_digest")
    if not strict_digest(record["entry_content_hash"]):
        raise ValueError("entry_content_hash_must_be_valid_digest")
    if not strict_digest(record["record_hash"]):
        raise ValueError("record_hash_must_be_valid_digest")

    entry = _entry_from_payload(record["entry"])
    if entry.content_hash != record["entry_content_hash"]:
        raise ValueError("entry_content_hash_mismatch")
    expected_hash = digest_payload(_record_hash_material(record))
    if record["record_hash"] != expected_hash:
        raise ValueError("record_hash_mismatch")


def _record_hash_material(record: dict[str, Any]) -> dict[str, object]:
    entry = _entry_from_payload(record["entry"])
    return {
        "code_version": record["code_version"],
        "entry": entry.deterministic_material(),
        "entry_content_hash": record["entry_content_hash"],
        "policy_version": record["policy_version"],
        "previous_record_hash": record["previous_record_hash"],
        "record_sequence": record["record_sequence"],
        "record_type": record["record_type"],
        "store_id": record["store_id"],
    }


def _entry_from_payload(payload: Any) -> OperatorDecisionLedgerEntry:
    if not isinstance(payload, dict):
        raise ValueError("entry_payload_must_be_object")
    _reject_forbidden_fields(payload)
    if set(payload) != _ENTRY_FIELDS:
        raise ValueError("entry_fields_mismatch")
    entry = build_ledger_entry(
        entry_id=payload["entry_id"],
        session_id=payload["session_id"],
        run_id=payload["run_id"],
        task_id=payload["task_id"],
        operator_action=payload["operator_action"],
        review_session_hash=payload["review_session_hash"],
        approval_receipt_hash=payload["approval_receipt_hash"],
        rejection_receipt_hash=payload["rejection_receipt_hash"],
        rollback_plan_hash=payload["rollback_plan_hash"],
        previous_entry_hash=payload["previous_entry_hash"],
        sequence_number=payload["sequence_number"],
        policy_version=payload["policy_version"],
        code_version=payload["code_version"],
        observed_at=payload["observed_at"],
    )
    if entry.content_hash != payload["content_hash"]:
        raise ValueError("entry_content_hash_mismatch")
    return entry


def _ledger_from_entries(
    entries: tuple[OperatorDecisionLedgerEntry, ...] | list[OperatorDecisionLedgerEntry],
) -> OperatorDecisionLedger:
    ledger = OperatorDecisionLedger()
    for entry in entries:
        ledger.append(entry)
    return ledger


def _with_append_hash(receipt: OperatorDecisionAppendReceipt) -> OperatorDecisionAppendReceipt:
    return OperatorDecisionAppendReceipt(
        store_id=receipt.store_id,
        record_sequence=receipt.record_sequence,
        entry_id=receipt.entry_id,
        entry_content_hash=receipt.entry_content_hash,
        previous_record_hash=receipt.previous_record_hash,
        record_hash=receipt.record_hash,
        decision_chain_head=receipt.decision_chain_head,
        policy_version=receipt.policy_version,
        code_version=receipt.code_version,
        content_hash=digest_payload(receipt.deterministic_material()),
        observed_at=receipt.observed_at,
    )


def _with_verification_hash(
    receipt: OperatorDecisionStoreVerificationReceipt,
) -> OperatorDecisionStoreVerificationReceipt:
    return OperatorDecisionStoreVerificationReceipt(
        store_id=receipt.store_id,
        total_records=receipt.total_records,
        decision_chain_head=receipt.decision_chain_head,
        snapshot_hash=receipt.snapshot_hash,
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
