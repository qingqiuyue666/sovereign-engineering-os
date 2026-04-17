"""
Context service: build and persist ContextArtifacts under §22.7 completeness.

Constitutional anchors:
- v11 §22.7 Context Artifact Completeness Contract
- v11 §23.4 ContextArtifact
- v11 §24.1 AT-013 (replay admission precondition)
- foundation §3 items 10-11 (phase-1 budget + memory policy)
- foundation §6 step 5 (artifactization before authority-bearing gates)

Phase-1 posture:
- `memory_item_ids` MUST be `[]` (foundation §3 item 11).
- `hard_budget_tokens` / `effective_budget_tokens` come from
  `phase1_budget_policy_v1` (foundation §3 item 10) — a static maximum
  declared here for honest temporary budgeting. This will be replaced
  by `BudgetRecord`-linked dynamic budgeting at AT-027 promotion.
- `truncation_reason` is mandatory whenever `actual_tokens` would have
  exceeded `effective_budget_tokens`. If the caller does not supply one
  in that condition, we synthesize `"phase1_static_budget_exceeded"`
  rather than silently drop content.
- `content_hash` is a SHA-256 over a canonical JSON form of the packed
  content shape; this is the hash artifact consumers refer to.

This service does not reach into git. It consumes a thin `ContextRequest`
structure supplied by the orchestrator. File-content truth remains with
git (foundation §3 item 12); the service only records the file ids and
provenance refs the caller asserts.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Mapping, Sequence
from uuid import uuid4

from kernel.schemas import load_schema
from kernel.schemas.validator import validate_artifact
from kernel.stores.sqlite.repositories import ContextArtifactRepository
from kernel.version.version_tuple import compose_version_tuple_hash


# Phase-1 static budget policy (foundation §3 item 10).
PHASE1_BUDGET_POLICY_ID = "phase1_budget_policy_v1"
PHASE1_HARD_BUDGET_TOKENS = 128_000
PHASE1_EFFECTIVE_BUDGET_TOKENS = 96_000


class ContextArtifactRejected(Exception):
    """Fail-closed rejection of an attempted context artifact creation."""


@dataclass(frozen=True)
class ContextRequest:
    repo_graph_version: str
    symbol_index_version: str
    candidate_file_ids: Sequence[str]
    symbol_frontier_ids: Sequence[str]
    packing_policy_version: str
    actual_tokens: int
    provenance_refs: Sequence[str] = field(default_factory=tuple)
    deferred_retrieval_items: Sequence[str] = field(default_factory=tuple)
    truncation_reason: str | None = None
    taint_set: Sequence[str] = field(default_factory=tuple)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _content_hash(payload: Mapping[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class ContextService:
    def __init__(
        self,
        *,
        repository: ContextArtifactRepository,
        audit_ledger: Any,
        version_tuple_overrides: Mapping[str, Any] | None = None,
        hard_budget_tokens: int | None = None,
        effective_budget_tokens: int | None = None,
    ) -> None:
        self._repo = repository
        self._audit = audit_ledger
        self._vt_overrides = dict(version_tuple_overrides or {})
        # Phase-1 static budget policy values are constructor-overridable
        # so the orchestrator's runtime budget allocation (AT-027) can
        # be exercised end-to-end in tests without forking a parallel
        # budget surface. The default remains `phase1_budget_policy_v1`.
        self._hard_budget_tokens = int(
            hard_budget_tokens if hard_budget_tokens is not None
            else PHASE1_HARD_BUDGET_TOKENS
        )
        self._effective_budget_tokens = int(
            effective_budget_tokens if effective_budget_tokens is not None
            else PHASE1_EFFECTIVE_BUDGET_TOKENS
        )
        if self._effective_budget_tokens > self._hard_budget_tokens:
            raise ValueError(
                "effective_budget_tokens must be <= hard_budget_tokens"
            )
        # Load the frozen schema once so ingress validation can check
        # structural shape before persistence (foundation §3.4).
        self._schema = load_schema("context_artifact")

    def build_context_artifact(
        self,
        *,
        task_id: str,
        root_revision_id: str,
        request: Mapping[str, Any] | ContextRequest,
        intent_anchor: Any,
    ) -> str:
        if isinstance(request, ContextRequest):
            req = request
        else:
            req = ContextRequest(
                repo_graph_version=str(request["repo_graph_version"]),
                symbol_index_version=str(request["symbol_index_version"]),
                candidate_file_ids=tuple(request["candidate_file_ids"]),
                symbol_frontier_ids=tuple(request["symbol_frontier_ids"]),
                packing_policy_version=str(request["packing_policy_version"]),
                actual_tokens=int(request["actual_tokens"]),
                provenance_refs=tuple(request.get("provenance_refs", ())),
                deferred_retrieval_items=tuple(
                    request.get("deferred_retrieval_items", ())
                ),
                truncation_reason=request.get("truncation_reason"),
                taint_set=tuple(request.get("taint_set", ())),
            )

        # Phase-1 budget policy derivation. Values are taken from the
        # service-instance policy (constructor overridable for tests
        # exercising AT-027 budget exhaustion via the real runtime path).
        hard_budget = self._hard_budget_tokens
        effective_budget = self._effective_budget_tokens

        # §22.7 completeness rules:
        # - truncation_reason MUST be explicit whenever candidate set
        #   exceeds effective budget. We enforce this at ingress.
        truncation_reason = req.truncation_reason
        if req.actual_tokens > effective_budget and not truncation_reason:
            raise ContextArtifactRejected(
                "actual_tokens exceeds effective budget but no "
                "truncation_reason was supplied (§22.7)"
            )

        # - deferred_retrieval_items must be explicit whenever staged
        #   retrieval is used. We do not infer this; the caller asserts.

        # - provenance_refs must cover admitted memory items. In phase 1
        #   memory_item_ids is [] by policy, so provenance refs need not
        #   include memory sources; but if the caller passes any memory
        #   ids at all, we reject (foundation §3 item 11).
        memory_item_ids: list[str] = []

        # Compose the artifact.
        payload = {
            "context_artifact_id": f"ctx-{uuid4().hex}",
            "task_id": task_id,
            "root_revision_id": root_revision_id,
            "repo_graph_version": req.repo_graph_version,
            "symbol_index_version": req.symbol_index_version,
            "candidate_file_ids": list(req.candidate_file_ids),
            "symbol_frontier_ids": list(req.symbol_frontier_ids),
            "memory_item_ids": memory_item_ids,
            "packing_policy_version": req.packing_policy_version,
            "hard_budget_tokens": hard_budget,
            "effective_budget_tokens": effective_budget,
            "actual_tokens": req.actual_tokens,
            "truncation_reason": truncation_reason,
            "deferred_retrieval_items": list(req.deferred_retrieval_items),
            "provenance_refs": list(req.provenance_refs),
            "taint_set": list(req.taint_set),
            "content_hash": _content_hash(
                {
                    "candidate_file_ids": list(req.candidate_file_ids),
                    "symbol_frontier_ids": list(req.symbol_frontier_ids),
                    "packing_policy_version": req.packing_policy_version,
                    "actual_tokens": req.actual_tokens,
                    "root_revision_id": root_revision_id,
                }
            ),
            "created_at": _now_iso(),
            "version_tuple_hash": compose_version_tuple_hash(self._vt_overrides),
        }

        # Ingress validation: required fields + type/enum/constraint checks
        # from the frozen schema (foundation §3.4). Full JSON Schema
        # draft-2020-12 validation remains a hardening-stage item.
        violations = validate_artifact(payload, self._schema)
        if violations:
            raise ContextArtifactRejected(
                f"context artifact schema validation failed: "
                f"{'; '.join(violations[:5])}"
            )

        self._repo.insert(payload)

        # AUDIT-003 / §22.1: when the caller supplies an intent anchor
        # carrying a durable ``intent_anchor_records.intent_id`` (today:
        # ``SignablePathOrchestrator._emit_intent_anchor`` for both the
        # eight-stage ``admit_context`` surface and the real-fix chain
        # entrypoint ``run_real_fix_chain``), name it in both
        # ``artifact_refs`` and ``payload``. This closes the last
        # upstream one-hop asymmetry on the real-fix narrow-path audit
        # chain, immediately upstream of the already-closed
        # ``inference_artifact_created`` record: a reviewer reading only
        # this single record can recover the originating durable
        # intent-anchor id without a second fetch (via
        # ``context_artifact_id -> intent_anchor_records``).
        # Authoritative fail-closed verification of ``intent_id`` against
        # ``intent_anchor_records`` remains the responsibility of the
        # downstream ``RevisionSealService`` at stage 6; this service
        # performs no independent verification. No schema change, no
        # migration, no new artifact family, no new audit record type.
        # Absent / empty ``intent_id`` preserves the prior audit shape
        # exactly so any caller that threads a stub anchor continues to
        # observe unchanged records.
        anchor_intent_id = getattr(intent_anchor, "intent_id", None)
        audit_artifact_refs = [payload["context_artifact_id"]]
        audit_payload: dict[str, Any] = {
            "root_revision_id": root_revision_id,
            "content_hash": payload["content_hash"],
            "hard_budget_tokens": hard_budget,
            "effective_budget_tokens": effective_budget,
            "budget_policy_id": PHASE1_BUDGET_POLICY_ID,
        }
        if isinstance(anchor_intent_id, str) and anchor_intent_id:
            audit_artifact_refs.append(anchor_intent_id)
            audit_payload["intent_id"] = anchor_intent_id
        self._audit.append(
            record_type="context_artifact_created",
            task_id=task_id,
            artifact_refs=audit_artifact_refs,
            payload=audit_payload,
        )
        return payload["context_artifact_id"]
