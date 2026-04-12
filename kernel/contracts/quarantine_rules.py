"""
Validation Quarantine Enforcement contract rules (C22.4).

Constitutional anchors:
- v11 §22.4 Validation Quarantine Enforcement Contract
- v11 §24.1 AT-010 / AT-011
- v11 §24.2 INV-008 (validation cannot pollute host truth)
- foundation §3 item 13 (macOS quarantine guarantee classification)
- foundation §6 step 6 (P1 validation quarantine + receipt path)

This module holds the *pure rules* for deciding whether a proposed
quarantine run is admissible against the declared policy, and whether
an observed run admits a trusted, downgraded, or invalid
ValidationReceipt. The runner adapter
(`validation/quarantine/runner_adapter.py`) owns the posture
declaration; this module owns the admissibility comparison.

Scope lock:
- No filesystem or subprocess work. The service layer invokes the
  adapter and hands the observed `QuarantineRun` to
  `classify_admissibility`.
- `classify_admissibility` is the single rule set; no silent soft-pass
  branches.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

from validation.quarantine.runner_adapter import (
    QUARANTINE_GUARANTEE_LEVEL,
    QUARANTINE_POLICY_DECLARATION,
    QuarantineGuaranteeLevel,
    QuarantineRun,
    QuarantineState,
    ReceiptTrust,
    classify_receipt_trust,
)


class QuarantineAdmissibilityError(Exception):
    """Raised when a quarantine proposal violates the declared policy."""


@dataclass(frozen=True)
class QuarantineProposal:
    """Thin description of a proposed quarantine run.

    The `validator_identity` / `validator_version` fields become part of
    the produced ValidationReceipt for replay provenance.
    """

    validator_identity: str
    validator_version: str
    requested_policy_keys: Sequence[str]
    secret_bearing: bool = False


def assert_proposal_admissible(proposal: QuarantineProposal) -> None:
    """Fail-closed check that the proposed run is admissible under the
    currently declared posture.

    Rules:
    - the declared guarantee level MUST be BOUNDED_QUARANTINE or stricter.
      Phase-1 declared posture is BOUNDED_QUARANTINE; any relaxation to
      UNKNOWN is rejected at admission time (foundation §3 item 13).
    - every requested policy key must be present in the declaration and
      explicitly `True`. A missing or `False` key forbids admission.
    - secret-bearing runs are forbidden in phase 1 (no secret-bearing
      capability is admitted on the narrow path).
    """
    if QUARANTINE_GUARANTEE_LEVEL is QuarantineGuaranteeLevel.UNKNOWN:
        raise QuarantineAdmissibilityError(
            "quarantine guarantee level is UNKNOWN; admission forbidden"
        )

    for key in proposal.requested_policy_keys:
        if key not in QUARANTINE_POLICY_DECLARATION:
            raise QuarantineAdmissibilityError(
                f"quarantine policy key {key!r} not declared"
            )
        if not QUARANTINE_POLICY_DECLARATION[key]:
            raise QuarantineAdmissibilityError(
                f"quarantine policy key {key!r} is not enabled in declaration"
            )

    if proposal.secret_bearing:
        raise QuarantineAdmissibilityError(
            "secret-bearing quarantine runs are forbidden on phase-1 narrow path"
        )


@dataclass(frozen=True)
class QuarantineAdmissionResult:
    """Outcome of post-run classification (C22.4 required checks)."""

    receipt_result: str  # "pass" | "fail" | "quarantined"
    trust: ReceiptTrust
    quarantine_run_id: str
    final_state: QuarantineState


def classify_admissibility(
    *,
    run: QuarantineRun,
    proposal_passed_static: bool,
) -> QuarantineAdmissionResult:
    """Apply §22.4 downgrade rules to an observed `QuarantineRun`.

    Rules:
    - Any trust downgrade to 'invalid' -> receipt result MUST be
      `quarantined` and the receipt MUST NOT be consumed as a pass.
    - A 'downgraded' trust class becomes `quarantined` result at
      phase-1 narrow path (barrier does not accept quarantined results
      as passing receipts; see `barrier_rules.REASON_RECEIPT_NOT_PASS`).
    - A 'trusted' run produces `pass` iff the static proposal check
      also passed; otherwise `fail`.
    """
    trust = classify_receipt_trust(run)
    if trust.class_name == "invalid":
        receipt_result = "quarantined"
    elif trust.class_name == "downgraded":
        receipt_result = "quarantined"
    else:
        receipt_result = "pass" if proposal_passed_static else "fail"

    return QuarantineAdmissionResult(
        receipt_result=receipt_result,
        trust=trust,
        quarantine_run_id=run.quarantine_run_id,
        final_state=run.state,
    )
