"""
Validation service: produce §23.7 ValidationReceipt under C22.4 quarantine.

Constitutional anchors:
- v11 §22.4 Validation Quarantine Enforcement Contract
- v11 §23.7 ValidationReceipt
- v11 §24.1 AT-010 / AT-011
- v11 §24.2 INV-008 (validation cannot pollute host truth)
- foundation §6 step 6 (P1 validation path)

Phase-1 posture:
- The service does NOT actually execute a subprocess. It composes a
  declared `QuarantineRun` record describing a clean bounded-quarantine
  run (network_off, host_read_only, disposable_workspace, env scrubbed,
  no network attempts). The adapter contract in
  `validation/quarantine/runner_adapter.py` carries the hardware/posture
  declaration; `kernel/contracts/quarantine_rules.py` holds the
  admissibility + downgrade rules.
- The produced receipt is `pass` iff the quarantine classification is
  trusted and a caller-supplied static proposal check passed.
- Any quarantine drift (env scrub violation, network attempt, dirty
  exit) downgrades the receipt to `quarantined` and propagates taint
  (`policy_degraded` or `quarantine_breach_suspect`).
- The receipt's `taint_set` carries any propagated taint classes so
  that downstream review/approval surfaces cannot silently drop them
  (INV-022, §22.11).

Scope lock:
- This service owns receipt creation for phase-1 single-file text
  substitution patches only. Full build/semantic receipts are
  hardening-stage items.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Mapping, Sequence
from uuid import uuid4

from kernel.contracts.quarantine_rules import (
    QuarantineAdmissibilityError,
    QuarantineProposal,
    assert_proposal_admissible,
    classify_admissibility,
)
from kernel.schemas import load_schema
from kernel.stores.sqlite.repositories import (
    PatchProposalRepository,
    ValidationReceiptRepository,
)
from kernel.version.version_tuple import compose_version_tuple_hash
from validation.quarantine.runner_adapter import QuarantineRun, QuarantineState


class ValidationRejected(Exception):
    """Fail-closed rejection raised when validation cannot admit a receipt."""


@dataclass(frozen=True)
class StaticCheckResult:
    passed: bool
    input_hash: str
    diagnostics_hash: str


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _hash_str(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def _canonical_hash(payload: Mapping[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class ValidationService:
    def __init__(
        self,
        *,
        repository: ValidationReceiptRepository,
        patch_reader: PatchProposalRepository,
        audit_ledger: Any,
        validator_identity: str = "phase1_static_validator",
        validator_version: str = "phase1-slice1",
        version_tuple_overrides: Mapping[str, Any] | None = None,
    ) -> None:
        self._repo = repository
        self._patch_reader = patch_reader
        self._audit = audit_ledger
        self._validator_identity = validator_identity
        self._validator_version = validator_version
        self._vt_overrides = dict(version_tuple_overrides or {})
        self._schema = load_schema("validation_receipt")

    def validate(
        self,
        *,
        task_id: str,
        patch_proposal_id: str,
        run: QuarantineRun | None = None,
        static_result: StaticCheckResult | None = None,
    ) -> str:
        """Run the phase-1 validation pipeline and issue a ValidationReceipt.

        Caller contract:
        - `run` is the adapter-produced quarantine envelope. If omitted,
          the service synthesizes a clean phase-1 envelope for the tracer
          bullet.
        - `static_result` is the caller's static-analysis outcome. If
          omitted, the service treats the single-file text-substitution
          patch as trivially passing at the static layer (phase-1 default).
        """
        proposal = self._patch_reader.fetch(patch_proposal_id)
        if proposal is None:
            raise ValidationRejected(
                f"patch proposal not found: {patch_proposal_id}"
            )

        # Admissibility check against declared policy (§22.4 + adapter
        # declaration).
        quarantine_proposal = QuarantineProposal(
            validator_identity=self._validator_identity,
            validator_version=self._validator_version,
            requested_policy_keys=(
                "network_off",
                "host_read_only",
                "isolated_caches",
                "disposable_workspace",
                "secret_scrubbed_env",
            ),
            secret_bearing=False,
        )
        try:
            assert_proposal_admissible(quarantine_proposal)
        except QuarantineAdmissibilityError as exc:
            self._audit.append(
                record_type="validation_quarantine_admission_rejected",
                task_id=task_id,
                artifact_refs=[patch_proposal_id],
                payload={"reason": str(exc)},
            )
            raise ValidationRejected(str(exc)) from exc

        # Adapter run envelope.
        observed = run or self._phase1_default_run()
        static = static_result or StaticCheckResult(
            passed=True,
            input_hash=_hash_str(proposal["patch_group_hash"]),
            diagnostics_hash=_canonical_hash({"phase1_static": "noop"}),
        )

        admission = classify_admissibility(
            run=observed, proposal_passed_static=static.passed
        )

        # Compose the receipt. Taint propagation (§22.11) is explicit:
        # whatever taint the adapter classification produced is merged
        # into the receipt's taint_set along with the upstream proposal
        # taint.
        taint_set = list(proposal.get("taint_set", [])) + list(
            admission.trust.taint_to_propagate
        )

        receipt = {
            "validation_receipt_id": f"vr-{uuid4().hex}",
            "task_id": task_id,
            "root_revision_id": proposal["root_revision_id"],
            "receipt_type": "phase1_static_quarantine",
            "validator_identity": self._validator_identity,
            "validator_version": self._validator_version,
            "input_hash": static.input_hash,
            "result": admission.receipt_result,
            "diagnostics_hash": static.diagnostics_hash,
            "taint_set": taint_set,
            "created_at": _now_iso(),
            "version_tuple_hash": compose_version_tuple_hash(self._vt_overrides),
        }

        for field_name in self._schema["required"]:
            if field_name not in receipt:
                raise ValidationRejected(
                    f"validation receipt missing required field: {field_name}"
                )

        self._repo.insert(receipt)

        self._audit.append(
            record_type="validation_receipt_created",
            task_id=task_id,
            artifact_refs=[receipt["validation_receipt_id"], patch_proposal_id],
            payload={
                "result": receipt["result"],
                "trust_class": admission.trust.class_name,
                "trust_reason": admission.trust.reason,
                "quarantine_run_id": admission.quarantine_run_id,
                "final_state": admission.final_state.value,
                "taint_propagated": list(admission.trust.taint_to_propagate),
            },
        )
        return receipt["validation_receipt_id"]

    @staticmethod
    def _phase1_default_run() -> QuarantineRun:
        """A clean bounded-quarantine envelope for the tracer bullet.

        Not a runtime; this is a declared-posture record the service
        hands to `classify_admissibility`. Real runs will come from an
        actual quarantine adapter in a later hardening step.
        """
        return QuarantineRun(
            quarantine_run_id=f"qr-{uuid4().hex}",
            state=QuarantineState.EXITED_CLEAN,
            entered_at=_now_iso(),
            exited_at=_now_iso(),
            host_pollution_suspected=False,
            workspace_preserved_for_forensics=False,
            env_scrub_violations=(),
            network_attempts=(),
        )
