"""Replay engine — main replay engine orchestrator.

Coordinates replay anchor creation, snapshot binding, version tuple
validation, evidence binding, receipt generation, and failure handling.

v1 — contract-only. No actual replay execution. No network.
"""

from __future__ import annotations

import hashlib
from typing import Any, Dict, List, Optional

from .replay_anchor import ReplayAnchor
from .replay_snapshot import ReplaySnapshot
from .replay_version_tuple import ReplayVersionTuple
from .replay_mismatch import ReplayMismatch, MismatchReport
from .replay_receipt import (
    ReplayReceipt, ReplayReadinessReceipt, ReplayFailureReceipt,
    produce_replay_receipt, produce_readiness_receipt, produce_failure_receipt,
)
from .replay_evidence_binding import ReplayEvidenceBinding
from .replay_canonical_hash import ReplayCanonicalHash
from .replay_failures import ReplayFailure, ReplayFailures
from .replay_modes import ReplayModes
from .replay_security import ReplaySecurity


class ReplayEngine:
    """Real replay engine runtime — v1 contract-only.

    Validates replay requests, binds evidence, produces deterministic
    receipts, and captures failures. No actual replay execution.
    """

    def __init__(self) -> None:
        self._failures = ReplayFailures()
        self._mismatch_reports: List[MismatchReport] = []
        self._receipts: List[ReplayReceipt] = []

    def create_anchor(
        self,
        input_snapshot_hash: str,
        policy_version: str,
        code_version: str,
        environment_fingerprint: str,
        *,
        evidence_vault_binding: str = "",
    ) -> ReplayAnchor:
        try:
            anchor = ReplayAnchor.create(
                input_snapshot_hash=input_snapshot_hash,
                policy_version=policy_version,
                code_version=code_version,
                environment_fingerprint=environment_fingerprint,
                evidence_vault_binding=evidence_vault_binding,
            )
            return anchor
        except ValueError as exc:
            self._failures.record(ReplayFailure.create(
                anchor_id="",
                failure_code="REPLAY_ANCHOR_INVALID",
                failure_reason=str(exc),
            ))
            raise

    def bind_snapshot(
        self, snapshot_hash: str, artifact_count: int, evidence_source: str,
    ) -> ReplaySnapshot:
        return ReplaySnapshot.create(
            snapshot_hash=snapshot_hash,
            artifact_count=artifact_count,
            evidence_source=evidence_source,
        )

    def validate_version_tuple(
        self, policy_version: str, code_version: str, environment_fingerprint: str,
    ) -> ReplayVersionTuple:
        vt = ReplayVersionTuple.create(
            policy_version=policy_version,
            code_version=code_version,
            environment_fingerprint=environment_fingerprint,
        )
        if not vt.is_valid:
            self._failures.record(ReplayFailure.create(
                anchor_id="",
                failure_code="REPLAY_VERSION_MISMATCH",
                failure_reason="version_tuple_invalid",
            ))
        return vt

    def bind_evidence(self, anchor_id: str, evidence_ids: List[str]) -> ReplayEvidenceBinding:
        try:
            return ReplayEvidenceBinding.create(anchor_id=anchor_id, evidence_ids=evidence_ids)
        except ValueError as exc:
            self._failures.record(ReplayFailure.create(
                anchor_id=anchor_id,
                failure_code="REPLAY_BINDING_INVALID",
                failure_reason=str(exc),
            ))
            raise

    def check_readiness(
        self,
        anchor: ReplayAnchor,
        snapshot: ReplaySnapshot,
        version_tuple: ReplayVersionTuple,
        mode: str,
        evidence_binding: Optional[ReplayEvidenceBinding] = None,
    ) -> ReplayReadinessReceipt:
        gates: Dict[str, bool] = {
            "anchor_valid": bool(anchor.anchor_id and anchor.canonical_hash),
            "snapshot_valid": bool(snapshot.snapshot_id and snapshot.snapshot_hash),
            "version_tuple_valid": version_tuple.is_valid,
            "mode_valid": ReplayModes.validate(mode)["valid"],
            "no_network": ReplaySecurity.validate_no_network({}),
            "no_secrets": ReplaySecurity.validate_no_secrets({}),
        }
        if evidence_binding:
            gates["evidence_binding_valid"] = evidence_binding.is_valid

        return produce_readiness_receipt(
            anchor_id=anchor.anchor_id,
            snapshot_id=snapshot.snapshot_id,
            version_tuple_id=version_tuple.tuple_id,
            gates=gates,
        )

    def produce_receipt(
        self,
        anchor: ReplayAnchor,
        snapshot: ReplaySnapshot,
        version_tuple: ReplayVersionTuple,
        mode: str,
        evidence_binding: Optional[ReplayEvidenceBinding] = None,
    ) -> ReplayReceipt:
        ReplayModes.enforce(mode)

        if not version_tuple.is_valid:
            self._failures.record(ReplayFailure.create(
                anchor_id=anchor.anchor_id,
                failure_code="REPLAY_VERSION_MISMATCH",
                failure_reason="version_tuple_invalid",
            ))
            raise ValueError("version_tuple_invalid")

        evidence_valid = evidence_binding.is_valid if evidence_binding else True

        receipt = produce_replay_receipt(
            anchor_id=anchor.anchor_id,
            snapshot_id=snapshot.snapshot_id,
            version_tuple_id=version_tuple.tuple_id,
            status="ready",
            mode=mode,
            evidence_binding_valid=evidence_valid,
        )
        self._receipts.append(receipt)
        return receipt

    def record_failure(
        self, anchor_id: str, failure_code: str, failure_reason: str,
        *, evidence_corrupted: bool = False,
    ) -> ReplayFailure:
        failure = ReplayFailure.create(
            anchor_id=anchor_id,
            failure_code=failure_code,
            failure_reason=failure_reason,
            evidence_corrupted=evidence_corrupted,
        )
        self._failures.record(failure)
        return failure

    def produce_failure_receipt(
        self, anchor_id: str, failure_reason: str, failure_code: str,
        *, evidence_corrupted: bool = False,
    ) -> ReplayFailureReceipt:
        self.record_failure(
            anchor_id=anchor_id,
            failure_code=failure_code,
            failure_reason=failure_reason,
            evidence_corrupted=evidence_corrupted,
        )
        return produce_failure_receipt(
            anchor_id=anchor_id,
            failure_reason=failure_reason,
            failure_code=failure_code,
            evidence_corrupted=evidence_corrupted,
        )

    def add_mismatch(
        self, anchor_id: str, field: str, expected_hash: str, actual_hash: str,
    ) -> ReplayMismatch:
        mismatch = ReplayMismatch.create(
            anchor_id=anchor_id,
            field=field,
            expected_hash=expected_hash,
            actual_hash=actual_hash,
        )
        report = MismatchReport(anchor_id)
        report.add(mismatch)
        self._mismatch_reports.append(report)
        return mismatch

    def has_failures(self) -> bool:
        return self._failures.has_failures()

    def fail_closed(self) -> bool:
        return self._failures.fail_closed()

    def failure_summary(self) -> Dict[str, Any]:
        return self._failures.to_dict()

    def mismatch_summary(self) -> List[Dict[str, Any]]:
        return [r.to_dict() for r in self._mismatch_reports]

    def receipt_count(self) -> int:
        return len(self._receipts)

    def engine_hash(self) -> str:
        parts = [
            self._failures.aggregate_hash(),
            str(len(self._receipts)),
        ]
        for r in self._mismatch_reports:
            parts.append(r.aggregate_hash())
        for r in self._receipts:
            parts.append(r.canonical_hash)
        return ReplayCanonicalHash.canonical_hash(*parts)

    def reset(self) -> None:
        self._failures = ReplayFailures()
        self._mismatch_reports = []
        self._receipts = []
