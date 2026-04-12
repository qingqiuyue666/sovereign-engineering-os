"""
Capability service: issuance, verification, consumption (C22.6 / §23.13).

Constitutional anchors:
- v11 §22.6 Capability Token Lifecycle Contract
- v11 §23.13 CapabilityToken
- v11 §24.1 AT-018
- v11 §24.2 INV-012 / INV-013
- foundation §6 step 4 (P0 capability gate bootstrap + context wiring)
- foundation §17 (first-slice capability-security invariant closure)

This service is the single point of truth for capability token
verification and consumption in phase 1. It composes:
  - `contracts.capability_rules` for pure rule evaluation
  - `stores.sqlite.repositories.CapabilityRepository` for durable state
  - `evidence.append_only_ledger.AuditLedger` for audit emission

It does not touch any other plane. No network calls, no model calls, no
filesystem beyond SQLite, no background threads.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping
from uuid import uuid4

from kernel.contracts.capability_rules import (
    CapabilityVerificationError,
    VerificationContext,
    verify_token,
)
from kernel.stores.sqlite.repositories import (
    CapabilityConsumeResult,
    CapabilityRepository,
)
from kernel.version.version_tuple import compose_version_tuple_hash


class CapabilityDenied(Exception):
    """Raised when capability verification or consumption fails closed."""


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class CapabilityService:
    def __init__(
        self,
        *,
        repository: CapabilityRepository,
        audit_ledger: Any,
        version_tuple_overrides: Mapping[str, Any] | None = None,
    ) -> None:
        self._repo = repository
        self._audit = audit_ledger
        self._vt_overrides = dict(version_tuple_overrides or {})

    # ------------------------------------------------------------------
    # issuance
    # ------------------------------------------------------------------

    def issue_token(
        self,
        *,
        subject_identity: str,
        capability_name: str,
        scope_hash: str,
        issued_at: str,
        expires_at: str,
        single_use: bool = True,
        bound_task_id: str | None = None,
        bound_root_revision_id: str | None = None,
    ) -> dict[str, Any]:
        """Issue a phase-1 capability token.

        Phase-1 posture: tokens are issued by the kernel itself. The MAC
        is a placeholder deterministic marker (`kernel:phase1`) rather
        than a real signature. The signature field is REQUIRED by
        `capability_rules.verify_token_structure` and must be non-empty;
        real crypto verification is a hardening-stage item.
        """
        token = {
            "capability_token_id": f"cap-{uuid4().hex}",
            "subject_identity": subject_identity,
            "capability_name": capability_name,
            "scope_hash": scope_hash,
            "issued_at": issued_at,
            "expires_at": expires_at,
            "issuer_identity": "kernel",
            "token_mac_or_signature": "kernel:phase1",
            "version_tuple_hash": compose_version_tuple_hash(self._vt_overrides),
            "single_use_flag": bool(single_use),
            "bound_task_id": bound_task_id,
            "bound_root_revision_id": bound_root_revision_id,
        }
        self._repo.insert(token)
        self._audit.append(
            record_type="capability_token_issued",
            task_id=bound_task_id,
            artifact_refs=[token["capability_token_id"]],
            payload={
                "capability_name": capability_name,
                "single_use": bool(single_use),
                "bound_root_revision_id": bound_root_revision_id,
            },
        )
        return token

    # ------------------------------------------------------------------
    # verification (C22.6 pre-effect gate)
    # ------------------------------------------------------------------

    def verify_for_action(
        self,
        *,
        token: Mapping[str, Any],
        action_class: str,
        task_id: str | None,
        root_revision_id: str | None,
    ) -> None:
        """Run §22.6 verification rules. Raises `CapabilityDenied` on failure.

        This is called by the orchestrator at every stage-admission gate
        BEFORE any effect-bearing action runs. Audit emission on failure
        is mandatory (INV-013 audit-query-proof).
        """
        context = VerificationContext(
            action_class=action_class,
            task_id=task_id,
            root_revision_id=root_revision_id,
        )
        try:
            verify_token(token, context=context)
        except CapabilityVerificationError as exc:
            self._audit.append(
                record_type="capability_verification_rejected",
                task_id=task_id,
                artifact_refs=[str(token.get("capability_token_id", ""))],
                payload={
                    "action_class": action_class,
                    "reason": str(exc),
                    "root_revision_id": root_revision_id,
                },
            )
            raise CapabilityDenied(str(exc)) from exc

    # ------------------------------------------------------------------
    # consumption (INV-012 single-use gate)
    # ------------------------------------------------------------------

    def consume(
        self,
        *,
        capability_token_id: str,
        task_id: str | None,
    ) -> CapabilityConsumeResult:
        """Atomically consume a single-use token.

        Must be invoked under the same transaction domain as the
        effect-bearing action that relies on the consume succeeding, so
        that crash ambiguity resolves fail-closed
        (INV-CAP-CRASH-AMBIGUITY-FAILS-CLOSED). This method only owns
        the consume step; the caller owns the transaction boundary.
        """
        result = self._repo.atomic_consume(capability_token_id)
        if result.winner:
            self._audit.append(
                record_type="capability_token_consumed",
                task_id=task_id,
                artifact_refs=[capability_token_id],
                payload={"result": "winner"},
            )
        else:
            self._audit.append(
                record_type="capability_token_consume_rejected",
                task_id=task_id,
                artifact_refs=[capability_token_id],
                payload={"result": "loser", "reason": result.reason},
            )
            raise CapabilityDenied(
                f"capability consume rejected: {result.reason}"
            )
        return result
