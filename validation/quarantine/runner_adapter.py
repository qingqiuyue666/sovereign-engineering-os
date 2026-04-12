"""
Validation quarantine runner adapter (skeleton with declared phase-1 posture).

Constitutional anchors:
- v11 §22.4 Validation Quarantine Enforcement Contract
- v11 §23.7 / §23.8 / §23.9 ValidationReceipt / BuildReceipt / SemanticReceipt
- v11 §24.1 AT-010 / AT-011
- v11 §24.2 INV-008 (validation cannot pollute host truth)
- foundation §3 item 13 (macOS quarantine guarantee classification)
- foundation §8 module mapping for runner adapter

Declared phase-1 quarantine posture (this is the honest surface):
- **isolation strategy**: local macOS runner with policy-governed
  constraints (disposable workspace + isolated caches + env scrubbing).
  This is NOT a full container-equivalence claim.
- **guarantee level**: `BOUNDED_QUARANTINE`. Declared via
  `QUARANTINE_GUARANTEE_LEVEL` below so any receipt consumer can read
  the posture without heuristics.
- **receipt posture**: any quarantine uncertainty or breach suspicion
  forces taint propagation (`quarantine_breach_suspect`) and a receipt
  trust downgrade. This is enforced by `classify_receipt_trust`.
- **hardware envelope**: MacBook Pro M5 Max, 64GB unified memory, 2TB
  internal + optional external SSD, local-first execution. This is
  declared here so any caller reading the runner adapter can read the
  exact hardware boundary the posture assumes (foundation hardware
  boundary statement in task brief).

Scope lock:
- This skeleton does not actually execute validation. It declares the
  posture object, offers `classify_receipt_trust`, and defines the
  typed `QuarantineRun` enter/exit callbacks that a future real
  adapter must satisfy. Full wiring to a runner binary is a hardening
  step and is out of scope for the first signable slice.
- AT-012 anti-swap watermark enforcement is explicitly deferred under
  foundation §11 / Section 14. This adapter does not claim anti-swap
  behavior.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Mapping, Sequence


class QuarantineGuaranteeLevel(str, Enum):
    BOUNDED_QUARANTINE = "bounded_quarantine"
    CONTAINER_EQUIVALENT = "container_equivalent"  # not claimed in phase 1
    UNKNOWN = "unknown"


class QuarantineState(str, Enum):
    PREPARED = "prepared"
    ENTERED = "entered"
    EXECUTING = "executing"
    EXITED_CLEAN = "exited_clean"
    EXITED_FAILED = "exited_failed"
    EXITED_TAINTED = "exited_tainted"
    PRESERVED_FOR_FORENSICS = "preserved_for_forensics"
    DESTROYED = "destroyed"


#: Declared phase-1 posture constants. Callers read these to decide how
#: much trust to attach to a receipt produced by this runner.
QUARANTINE_GUARANTEE_LEVEL = QuarantineGuaranteeLevel.BOUNDED_QUARANTINE
QUARANTINE_HARDWARE_ENVELOPE = (
    "Apple MacBook Pro M5 Max, 64GB unified memory, "
    "2TB internal storage, optional external SSD, local-first execution"
)
QUARANTINE_POLICY_DECLARATION = {
    "network_off": True,
    "host_read_only": True,
    "isolated_caches": True,
    "disposable_workspace": True,
    "bounded_resources": True,
    "secret_scrubbed_env": True,
    "enter_exit_audit_required": True,
}


@dataclass(frozen=True)
class QuarantineRun:
    """Typed record of a quarantine run envelope.

    The runner must populate this structure and hand it back to the
    caller so that the caller can (1) decide receipt trust class, and
    (2) emit the enter/exit audit records mandated by §22.4.
    """

    quarantine_run_id: str
    state: QuarantineState
    entered_at: str
    exited_at: str | None
    host_pollution_suspected: bool
    workspace_preserved_for_forensics: bool
    env_scrub_violations: Sequence[str]
    network_attempts: Sequence[str]


@dataclass(frozen=True)
class ReceiptTrust:
    """Trust classification attached to a ValidationReceipt produced here."""

    class_name: str  # "trusted", "downgraded", "invalid"
    reason: str
    taint_to_propagate: tuple[str, ...]


def classify_receipt_trust(run: QuarantineRun) -> ReceiptTrust:
    """Apply the §22.4 + foundation §3.13 downgrade rules.

    Rules:
    - any host pollution suspicion -> INVALID + taint
      `quarantine_breach_suspect` on the receipt.
    - any env-scrub violation or network attempt -> DOWNGRADED + taint
      `policy_degraded`.
    - clean exit -> TRUSTED. No taint.
    """
    if run.host_pollution_suspected:
        return ReceiptTrust(
            class_name="invalid",
            reason="host pollution suspected in quarantine run",
            taint_to_propagate=("quarantine_breach_suspect",),
        )
    if run.env_scrub_violations or run.network_attempts:
        return ReceiptTrust(
            class_name="downgraded",
            reason=(
                f"quarantine policy drift: "
                f"env_scrub_violations={list(run.env_scrub_violations)}, "
                f"network_attempts={list(run.network_attempts)}"
            ),
            taint_to_propagate=("policy_degraded",),
        )
    if run.state is not QuarantineState.EXITED_CLEAN:
        return ReceiptTrust(
            class_name="invalid",
            reason=f"quarantine run did not exit cleanly (state={run.state.value})",
            taint_to_propagate=("quarantine_breach_suspect",),
        )
    return ReceiptTrust(
        class_name="trusted",
        reason="clean exit",
        taint_to_propagate=(),
    )


def declared_posture() -> Mapping[str, object]:
    """Return the declared phase-1 posture as a plain mapping.

    Exposed so the sign-off gate can read and audit the posture surface
    without importing runtime state.
    """
    return {
        "guarantee_level": QUARANTINE_GUARANTEE_LEVEL.value,
        "hardware_envelope": QUARANTINE_HARDWARE_ENVELOPE,
        "policy": dict(QUARANTINE_POLICY_DECLARATION),
        "at_012_anti_swap": "deferred (foundation §11 / Section 14)",
    }
