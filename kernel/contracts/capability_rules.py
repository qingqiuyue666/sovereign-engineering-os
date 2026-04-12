"""
Capability Token Lifecycle contract rules (C22.6).

Constitutional anchors:
- v11 §22.6 Capability Token Lifecycle Contract (full body)
- v11 §23.13 CapabilityToken schema
- v11 §24.1 AT-018
- v11 §24.2 INV-012 / INV-013
- foundation §8 module mapping, §17 capability-security invariant closure

This module holds the *pure rules*: schema/signature/time/revocation/
scope/binding checks. It does not touch SQLite (that is the
`CapabilityRepository` / `CapabilityService` responsibility). It does not
touch audit (that is the service responsibility).

Verification rules implemented (foundation §17 minimum closure subset):
- INV-CAP-ONLY-KERNEL-ISSUED  (issuer is trusted under active policy)
- INV-CAP-VERIFY-BEFORE-EFFECT (entry point used by orchestrator)
- INV-CAP-SINGLE-USE-MEANS-SINGLE-USE (delegated to atomic consume gate)
- INV-CAP-NO-DRIFT-CARRYOVER (bound_task/root match checks here)
- INV-CAP-REVOCATION-WINS    (revocation check runs before consume)
- INV-CAP-NO-CROSS-CLASS-ESCALATION (capability_name vs action_class)
- INV-CAP-CRASH-AMBIGUITY-FAILS-CLOSED (paired with WAL recovery)
- INV-CAP-UI-STATE-IS-NOT-AUTHORITY (orchestrator/signoff gate pair)

Fail-closed posture: any verification failure raises
`CapabilityVerificationError`. Silent `return False` paths are forbidden
because they invite callers to "soft" around denials.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Mapping


#: The declared capability registry for phase 1. Only these names are
#: admissible; any other name is rejected as "unknown capability".
#: This mirrors foundation §17 and constrains §22.6 to the narrow first
#: slice rather than a speculative capability surface.
CAPABILITY_REGISTRY: frozenset[str] = frozenset(
    {
        "read_repository_snapshot",
        "invoke_inference",
        "propose_patch",
        "run_validation_quarantine",
        "render_review",
        "grant_approval",
        "seal_revision",
        "append_evidence",
    }
)


#: Mapping of capability name -> admissible action classes. A capability
#: named `X` may only be used for action classes listed here. This is
#: INV-CAP-NO-CROSS-CLASS-ESCALATION.
ACTION_CLASS_MAP: Mapping[str, frozenset[str]] = {
    "read_repository_snapshot": frozenset({"read_repository_snapshot"}),
    "invoke_inference": frozenset({"invoke_inference"}),
    "propose_patch": frozenset({"propose_patch"}),
    "run_validation_quarantine": frozenset({"run_validation_quarantine"}),
    "render_review": frozenset({"render_review"}),
    "grant_approval": frozenset({"grant_approval"}),
    "seal_revision": frozenset({"seal_revision"}),
    "append_evidence": frozenset({"append_evidence"}),
}


#: Set of issuer identities trusted under active policy. In phase 1 the
#: only admissible issuer is the kernel itself; any other issuer is
#: rejected as an authority-escalation attempt.
TRUSTED_ISSUERS: frozenset[str] = frozenset({"kernel"})


class CapabilityVerificationError(Exception):
    """Fail-closed rejection of a capability token."""


@dataclass(frozen=True)
class VerificationContext:
    action_class: str
    task_id: str | None
    root_revision_id: str | None


def _parse_iso(ts: str) -> datetime:
    # Accept both 'Z' and '+00:00' suffixes.
    if ts.endswith("Z"):
        ts = ts[:-1] + "+00:00"
    return datetime.fromisoformat(ts)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def verify_token_structure(token: Mapping[str, object]) -> None:
    required = {
        "capability_token_id",
        "subject_identity",
        "capability_name",
        "scope_hash",
        "issued_at",
        "expires_at",
        "issuer_identity",
        "token_mac_or_signature",
        "version_tuple_hash",
        "single_use_flag",
    }
    missing = required - set(token)
    if missing:
        raise CapabilityVerificationError(
            f"capability token missing required fields: {sorted(missing)}"
        )


def verify_token(
    token: Mapping[str, object],
    *,
    context: VerificationContext,
    now: datetime | None = None,
) -> None:
    """Run the full phase-1 verification rule set on `token`.

    This function covers pre-consume checks only. The atomic consume
    (INV-012) lives in the repository layer and must be called
    immediately after this function returns (under the same DB
    transaction) to satisfy INV-CAP-CRASH-AMBIGUITY-FAILS-CLOSED.
    """
    now = now or _now()

    # 1) Structure.
    verify_token_structure(token)

    # 2) Issuer trust (INV-CAP-ONLY-KERNEL-ISSUED).
    issuer = str(token["issuer_identity"])
    if issuer not in TRUSTED_ISSUERS:
        raise CapabilityVerificationError(
            f"issuer {issuer!r} is not trusted under active policy"
        )

    # 3) Registry admissibility.
    cap_name = str(token["capability_name"])
    if cap_name not in CAPABILITY_REGISTRY:
        raise CapabilityVerificationError(
            f"capability {cap_name!r} not in active registry"
        )

    # 4) Action-class admissibility (INV-CAP-NO-CROSS-CLASS-ESCALATION).
    allowed = ACTION_CLASS_MAP.get(cap_name, frozenset())
    if context.action_class not in allowed:
        raise CapabilityVerificationError(
            f"capability {cap_name!r} not admissible for action class "
            f"{context.action_class!r}"
        )

    # 5) Time bounds.
    try:
        issued_at = _parse_iso(str(token["issued_at"]))
        expires_at = _parse_iso(str(token["expires_at"]))
    except ValueError as exc:
        raise CapabilityVerificationError(
            f"capability token timestamps unparseable: {exc}"
        ) from exc
    if now < issued_at:
        raise CapabilityVerificationError("capability token not yet valid")
    if now >= expires_at:
        raise CapabilityVerificationError("capability token expired")

    # 6) Revocation (INV-CAP-REVOCATION-WINS).
    revoked_at = token.get("revoked_at")
    if revoked_at not in (None, ""):
        raise CapabilityVerificationError("capability token revoked")

    # 7) Single-use already consumed.
    if token.get("single_use_flag", True) and token.get("consumed_at") not in (
        None,
        "",
    ):
        raise CapabilityVerificationError(
            "single-use capability token already consumed"
        )

    # 8) Binding checks (INV-CAP-NO-DRIFT-CARRYOVER).
    bound_task = token.get("bound_task_id")
    if bound_task not in (None, "") and bound_task != context.task_id:
        raise CapabilityVerificationError(
            f"token bound to task {bound_task!r}, not {context.task_id!r}"
        )
    bound_root = token.get("bound_root_revision_id")
    if (
        bound_root not in (None, "")
        and context.root_revision_id is not None
        and bound_root != context.root_revision_id
    ):
        raise CapabilityVerificationError(
            f"token bound to root {bound_root!r}, not "
            f"{context.root_revision_id!r}"
        )

    # 9) MAC / signature presence check.
    # Phase-1 posture: we enforce that a non-empty token_mac_or_signature
    # is present. Actual crypto verification is a hardening-stage item
    # bound to `capability_service.verify_signature`; the skeleton here
    # refuses to admit missing/empty signatures.
    sig = token.get("token_mac_or_signature")
    if not isinstance(sig, str) or not sig:
        raise CapabilityVerificationError(
            "capability token missing MAC or signature"
        )
