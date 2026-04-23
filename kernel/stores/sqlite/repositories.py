"""
Typed persistence adapters over the SQLite WAL substrate (first slice).

Constitutional anchors:
- v11 §22.1 / §22.2 (durability + ordering)
- v11 §22.6 (capability lifecycle + atomic consume)
- v11 §23.x (frozen schemas; first-slice subset)
- v11 §24.2 INV-004/005/012/013/026/022
- foundation §2 (layout), §8 (module mapping)

Scope lock:
- This module does not own policy. It provides thin typed INSERT adapters
  and one atomic UPDATE (capability consume) that must return exactly one
  winner on concurrent contention.
- No silent UPDATEs on append-only ledgers (audit/failure/drift/taint);
  the database triggers enforce append-only at the SQL layer.
- No file-content truth reconciliation here; git remains file-content
  truth (foundation §3 item 12).
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping, Sequence


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _jsonify(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


# ---------------------------------------------------------------------------
# Audit ledger (append-only)
# ---------------------------------------------------------------------------


class AuditRepository:
    """Append-only audit record writer with narrow deterministic readers.

    Every stage transition of the signable path must land here. The
    INV-026 trigger on `audit_records` guarantees that no UPDATE/DELETE
    can occur at the SQL layer; read helpers must stay deterministic and
    scoped to already-durable rows.
    """

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def list_capability_token_consumed_for_task(
        self, task_id: str
    ) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            """
            SELECT * FROM audit_records
             WHERE task_id = ?
               AND record_type = 'capability_token_consumed'
             ORDER BY sequence;
            """,
            (task_id,),
        ).fetchall()
        return [d for row in rows if (d := _row_to_dict(row)) is not None]

    def list_capability_token_revoked_for_task(
        self, task_id: str
    ) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            """
            SELECT * FROM audit_records
             WHERE task_id = ?
               AND record_type = 'capability_token_revoked'
             ORDER BY sequence;
            """,
            (task_id,),
        ).fetchall()
        return [d for row in rows if (d := _row_to_dict(row)) is not None]

    def append(
        self,
        *,
        audit_record_id: str,
        record_type: str,
        actor_identity: str,
        version_tuple_hash: str,
        task_id: str | None = None,
        root_revision_id: str | None = None,
        causality_ref: str | None = None,
        artifact_refs: Sequence[str] | None = None,
        taint_set: Sequence[str] | None = None,
        payload: Mapping[str, Any] | None = None,
        failure_bundle_id: str | None = None,
        replay_anchor_id: str | None = None,
        approval_id: str | None = None,
    ) -> int:
        cur = self._conn.cursor()
        # Sequence is a monotonic append counter scoped to this database
        # file. The UNIQUE index on `sequence` will raise if a concurrent
        # writer tries to reuse it; we retry inside a BEGIN IMMEDIATE
        # transaction (callers wrap this in their own txn boundary).
        row = cur.execute(
            "SELECT COALESCE(MAX(sequence), 0) FROM audit_records;"
        ).fetchone()
        next_seq = int(row[0]) + 1
        cur.execute(
            """
            INSERT INTO audit_records (
              audit_record_id, task_id, root_revision_id, record_type,
              causality_ref, actor_identity, artifact_refs,
              version_tuple_hash, taint_set_json, created_at,
              payload_json, failure_bundle_id, replay_anchor_id, approval_id,
              sequence
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                audit_record_id,
                task_id,
                root_revision_id,
                record_type,
                causality_ref,
                actor_identity,
                _jsonify(list(artifact_refs or [])),
                version_tuple_hash,
                _jsonify(list(taint_set or [])),
                _iso_now(),
                _jsonify(dict(payload or {})),
                failure_bundle_id,
                replay_anchor_id,
                approval_id,
                next_seq,
            ),
        )
        return next_seq


# ---------------------------------------------------------------------------
# Taint ledger (append-only; INV-022 no silent clearing)
# ---------------------------------------------------------------------------


class TaintRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def list_for_subject(self, subject_id: str) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            """
            SELECT * FROM taint_records
             WHERE subject_id = ?
             ORDER BY taint_record_id;
            """,
            (subject_id,),
        ).fetchall()
        return [d for row in rows if (d := _row_to_dict(row)) is not None]

    def append(
        self,
        *,
        taint_record_id: str,
        subject_id: str,
        taint_class: str,
        taint_state: str,
        source_ref: str,
        cleared_at: str | None = None,
        clearing_identity: str | None = None,
        clearing_reason: str | None = None,
    ) -> None:
        self._conn.execute(
            """
            INSERT INTO taint_records (
              taint_record_id, subject_id, taint_class, taint_state,
              source_ref, created_at, cleared_at, clearing_identity, clearing_reason
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                taint_record_id,
                subject_id,
                taint_class,
                taint_state,
                source_ref,
                _iso_now(),
                cleared_at,
                clearing_identity,
                clearing_reason,
            ),
        )


# ---------------------------------------------------------------------------
# Budget ledger (minimal durable transition records)
# ---------------------------------------------------------------------------


class BudgetRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def list_for_task(self, task_id: str) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            """
            SELECT * FROM budget_records
             WHERE task_id = ?
             ORDER BY rowid;
            """,
            (task_id,),
        ).fetchall()
        return [d for row in rows if (d := _row_to_dict(row)) is not None]

    def append(
        self,
        *,
        budget_record_id: str,
        task_id: str,
        budget_class: str,
        allocated_amount: int,
        consumed_amount: int,
        remaining_amount: int,
        budget_state: str,
        close_reason: str | None = None,
    ) -> None:
        created_at = _iso_now()
        self._conn.execute(
            """
            INSERT INTO budget_records (
              budget_record_id, task_id, budget_class, allocated_amount,
              consumed_amount, remaining_amount, budget_state, created_at,
              suspended_at, replenished_at, close_reason
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                budget_record_id,
                task_id,
                budget_class,
                allocated_amount,
                consumed_amount,
                remaining_amount,
                budget_state,
                created_at,
                created_at if budget_state == "suspended" else None,
                created_at if budget_state == "replenished" else None,
                close_reason,
            ),
        )


# ---------------------------------------------------------------------------
# Capability token ledger (issue + atomic single-use consume)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CapabilityConsumeResult:
    winner: bool
    reason: str


class CapabilityRepository:
    """Capability token persistence and atomic consume gate (C22.6).

    The atomic consume is the primary AT-018 / INV-012 enforcement point.
    `UPDATE ... WHERE consumed_at IS NULL` is atomic under SQLite's
    transaction serialization; the row count determines the winner.
    """

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def list_for_task(self, task_id: str) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            """
            SELECT * FROM capability_tokens
             WHERE bound_task_id = ?
             ORDER BY rowid;
            """,
            (task_id,),
        ).fetchall()
        return [d for row in rows if (d := _row_to_dict(row)) is not None]

    def insert(self, token: Mapping[str, Any]) -> None:
        # Caller is expected to have schema-validated the token upstream.
        self._conn.execute(
            """
            INSERT INTO capability_tokens (
              capability_token_id, subject_identity, capability_name,
              scope_hash, issued_at, expires_at, issuer_identity,
              token_mac_or_signature, version_tuple_hash, single_use_flag,
              consumed_at, revoked_at, revocation_reason,
              bound_task_id, bound_root_revision_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                token["capability_token_id"],
                token["subject_identity"],
                token["capability_name"],
                token["scope_hash"],
                token["issued_at"],
                token["expires_at"],
                token["issuer_identity"],
                token["token_mac_or_signature"],
                token["version_tuple_hash"],
                1 if token.get("single_use_flag", True) else 0,
                token.get("consumed_at"),
                token.get("revoked_at"),
                token.get("revocation_reason"),
                token.get("bound_task_id"),
                token.get("bound_root_revision_id"),
            ),
        )

    def fetch(self, capability_token_id: str) -> sqlite3.Row | None:
        return self._conn.execute(
            "SELECT * FROM capability_tokens WHERE capability_token_id = ?;",
            (capability_token_id,),
        ).fetchone()

    def revoke(self, capability_token_id: str, reason: str) -> bool:
        # Revocation is an authority-bearing mutation; it is intentionally
        # UPDATE (not append-only) on the `capability_tokens` row because
        # §23.13 treats consumed_at/revoked_at as optional on-row columns.
        # Each revocation MUST also emit an AuditRecord at the service
        # layer; this repository does not synthesize audit.
        cur = self._conn.execute(
            """
            UPDATE capability_tokens
               SET revoked_at = ?, revocation_reason = ?
             WHERE capability_token_id = ?
               AND revoked_at IS NULL;
            """,
            (_iso_now(), reason, capability_token_id),
        )
        return cur.rowcount == 1

    def atomic_consume(
        self, capability_token_id: str
    ) -> CapabilityConsumeResult:
        """Attempt exactly-one-winner consumption of a single-use token.

        Returns `winner=True` iff this call was the unique consumer.
        Losing contenders (second consume, or revoked/expired state) get
        `winner=False` with a deterministic `reason`.
        """
        cur = self._conn.cursor()
        # Atomic single-use consume. The WHERE clause enforces:
        # - token exists
        # - not already consumed
        # - not revoked
        # - single_use_flag = 1 (multi-use consume is a separate path; not
        #   admitted by phase-1 skeleton)
        cur.execute(
            """
            UPDATE capability_tokens
               SET consumed_at = ?
             WHERE capability_token_id = ?
               AND single_use_flag = 1
               AND consumed_at IS NULL
               AND revoked_at IS NULL
               AND expires_at > ?;
            """,
            (_iso_now(), capability_token_id, _iso_now()),
        )
        if cur.rowcount == 1:
            return CapabilityConsumeResult(winner=True, reason="consumed")

        # Classify the loser deterministically.
        row = self.fetch(capability_token_id)
        if row is None:
            return CapabilityConsumeResult(winner=False, reason="unknown_token")
        if row["revoked_at"] is not None:
            return CapabilityConsumeResult(winner=False, reason="revoked")
        if row["consumed_at"] is not None:
            return CapabilityConsumeResult(winner=False, reason="already_consumed")
        if row["single_use_flag"] != 1:
            return CapabilityConsumeResult(winner=False, reason="not_single_use")
        if row["expires_at"] <= _iso_now():
            return CapabilityConsumeResult(winner=False, reason="expired")
        return CapabilityConsumeResult(winner=False, reason="race_lost")


# ---------------------------------------------------------------------------
# Intent anchor (minimal durable causal record; AUDIT-003)
# ---------------------------------------------------------------------------


class IntentAnchorRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def insert(self, *, intent_id: str, task_id: str, state: str) -> None:
        self._conn.execute(
            """
            INSERT INTO intent_anchor_records (intent_id, task_id, state, created_at)
            VALUES (?, ?, ?, ?);
            """,
            (intent_id, task_id, state, _iso_now()),
        )

    def fetch(self, intent_id: str) -> dict[str, Any] | None:
        """Read-only lookup of a durable ``intent_anchor_records`` row.

        Returns the row as a dict or ``None`` when absent. Used by
        ``RevisionSealService.seal_revision`` to verify that the supplied
        ``intent_id`` names a real durable row (AUDIT-003 / §22.1) rather
        than accepting any non-empty string.
        """
        row = self._conn.execute(
            "SELECT * FROM intent_anchor_records WHERE intent_id = ?;",
            (intent_id,),
        ).fetchone()
        return _row_to_dict(row)


# ---------------------------------------------------------------------------
# Generic artifact writers (thin, schema-validated upstream)
# ---------------------------------------------------------------------------


def _row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return {k: row[k] for k in row.keys()}


def _unjsonify(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (dict, list)):
        return value
    return json.loads(value)


class ContextArtifactRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def insert(self, artifact: Mapping[str, Any]) -> None:
        self._conn.execute(
            """
            INSERT INTO context_artifacts (
              context_artifact_id, task_id, root_revision_id, repo_graph_version,
              symbol_index_version, candidate_file_ids, symbol_frontier_ids,
              memory_item_ids, packing_policy_version, hard_budget_tokens,
              effective_budget_tokens, actual_tokens, truncation_reason,
              deferred_retrieval_items, provenance_refs, taint_set_json,
              content_hash, created_at, version_tuple_hash
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                artifact["context_artifact_id"],
                artifact["task_id"],
                artifact["root_revision_id"],
                artifact["repo_graph_version"],
                artifact["symbol_index_version"],
                _jsonify(artifact["candidate_file_ids"]),
                _jsonify(artifact["symbol_frontier_ids"]),
                _jsonify(artifact["memory_item_ids"]),
                artifact["packing_policy_version"],
                artifact["hard_budget_tokens"],
                artifact["effective_budget_tokens"],
                artifact["actual_tokens"],
                artifact.get("truncation_reason"),
                _jsonify(artifact["deferred_retrieval_items"]),
                _jsonify(artifact["provenance_refs"]),
                _jsonify(artifact["taint_set"]),
                artifact["content_hash"],
                artifact["created_at"],
                artifact["version_tuple_hash"],
            ),
        )

    def fetch(self, context_artifact_id: str) -> dict[str, Any] | None:
        row = self._conn.execute(
            "SELECT * FROM context_artifacts WHERE context_artifact_id = ?;",
            (context_artifact_id,),
        ).fetchone()
        d = _row_to_dict(row)
        if d is None:
            return None
        d["candidate_file_ids"] = _unjsonify(d.get("candidate_file_ids")) or []
        d["symbol_frontier_ids"] = _unjsonify(d.get("symbol_frontier_ids")) or []
        d["memory_item_ids"] = _unjsonify(d.get("memory_item_ids")) or []
        d["deferred_retrieval_items"] = _unjsonify(
            d.get("deferred_retrieval_items")
        ) or []
        d["provenance_refs"] = _unjsonify(d.get("provenance_refs")) or []
        d["taint_set"] = _unjsonify(d.get("taint_set_json")) or []
        return d

    def exists_for(self, task_id: str, root_revision_id: str) -> bool:
        row = self._conn.execute(
            """
            SELECT 1 FROM context_artifacts
             WHERE task_id = ? AND root_revision_id = ? LIMIT 1;
            """,
            (task_id, root_revision_id),
        ).fetchone()
        return row is not None


class InferenceArtifactRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def insert(self, artifact: Mapping[str, Any]) -> None:
        self._conn.execute(
            """
            INSERT INTO inference_artifacts (
              inference_artifact_id, task_id, root_revision_id, context_artifact_id,
              worker_run_id, worker_profile, model_route_id, output_hash,
              provenance_refs, taint_set_json, created_at, version_tuple_hash,
              token_usage_json, latency_ms, fallback_route_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                artifact["inference_artifact_id"],
                artifact["task_id"],
                artifact["root_revision_id"],
                artifact["context_artifact_id"],
                artifact["worker_run_id"],
                artifact["worker_profile"],
                artifact["model_route_id"],
                artifact["output_hash"],
                _jsonify(artifact["provenance_refs"]),
                _jsonify(artifact["taint_set"]),
                artifact["created_at"],
                artifact["version_tuple_hash"],
                _jsonify(artifact.get("token_usage", {})),
                artifact.get("latency_ms"),
                artifact.get("fallback_route_id"),
            ),
        )

    def fetch(self, inference_artifact_id: str) -> dict[str, Any] | None:
        row = self._conn.execute(
            "SELECT * FROM inference_artifacts WHERE inference_artifact_id = ?;",
            (inference_artifact_id,),
        ).fetchone()
        d = _row_to_dict(row)
        if d is None:
            return None
        d["provenance_refs"] = _unjsonify(d.get("provenance_refs")) or []
        d["taint_set"] = _unjsonify(d.get("taint_set_json")) or []
        d["token_usage"] = _unjsonify(d.get("token_usage_json")) or {}
        return d

    def exists_for(self, task_id: str, root_revision_id: str) -> bool:
        row = self._conn.execute(
            """
            SELECT 1 FROM inference_artifacts
             WHERE task_id = ? AND root_revision_id = ? LIMIT 1;
            """,
            (task_id, root_revision_id),
        ).fetchone()
        return row is not None


# ---------------------------------------------------------------------------
# PatchProposal / ValidationReceipt / ReviewArtifact / ApprovalArtifact
# ---------------------------------------------------------------------------


class PatchProposalRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def insert(self, artifact: Mapping[str, Any]) -> None:
        self._conn.execute(
            """
            INSERT INTO patch_proposals (
              patch_proposal_id, task_id, root_revision_id, inference_artifact_id,
              target_file_ids, patch_group_hash, side_effect_class_proposal,
              capability_requirements, taint_set_json, created_at, version_tuple_hash
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                artifact["patch_proposal_id"],
                artifact["task_id"],
                artifact["root_revision_id"],
                artifact["inference_artifact_id"],
                _jsonify(artifact["target_file_ids"]),
                artifact["patch_group_hash"],
                artifact["side_effect_class_proposal"],
                _jsonify(artifact["capability_requirements"]),
                _jsonify(artifact["taint_set"]),
                artifact["created_at"],
                artifact["version_tuple_hash"],
            ),
        )

    def fetch(self, patch_proposal_id: str) -> dict[str, Any] | None:
        row = self._conn.execute(
            "SELECT * FROM patch_proposals WHERE patch_proposal_id = ?;",
            (patch_proposal_id,),
        ).fetchone()
        d = _row_to_dict(row)
        if d is None:
            return None
        d["target_file_ids"] = _unjsonify(d.get("target_file_ids")) or []
        d["capability_requirements"] = _unjsonify(
            d.get("capability_requirements")
        ) or []
        d["taint_set"] = _unjsonify(d.get("taint_set_json")) or []
        return d


class ValidationReceiptRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def insert(self, artifact: Mapping[str, Any]) -> None:
        self._conn.execute(
            """
            INSERT INTO validation_receipts (
              validation_receipt_id, task_id, root_revision_id, receipt_type,
              validator_identity, validator_version, input_hash, result,
              diagnostics_hash, taint_set_json, created_at, version_tuple_hash,
              invalidated_at, invalidation_reason
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                artifact["validation_receipt_id"],
                artifact["task_id"],
                artifact["root_revision_id"],
                artifact["receipt_type"],
                artifact["validator_identity"],
                artifact["validator_version"],
                artifact["input_hash"],
                artifact["result"],
                artifact["diagnostics_hash"],
                _jsonify(artifact["taint_set"]),
                artifact["created_at"],
                artifact["version_tuple_hash"],
                artifact.get("invalidated_at"),
                artifact.get("invalidation_reason"),
            ),
        )

    def fetch(self, validation_receipt_id: str) -> dict[str, Any] | None:
        row = self._conn.execute(
            "SELECT * FROM validation_receipts WHERE validation_receipt_id = ?;",
            (validation_receipt_id,),
        ).fetchone()
        d = _row_to_dict(row)
        if d is None:
            return None
        d["taint_set"] = _unjsonify(d.get("taint_set_json")) or []
        return d

    def list_active_for_task_root(
        self, task_id: str, root_revision_id: str
    ) -> list[dict[str, Any]]:
        """Return live (non-invalidated) receipts bound to a (task, root).

        Phase-1 incremental invalidation (AT-017 / INV-017): callers use
        this to identify receipts whose upstream patch hash may have
        drifted.
        """
        rows = self._conn.execute(
            """
            SELECT * FROM validation_receipts
             WHERE task_id = ?
               AND root_revision_id = ?
               AND invalidated_at IS NULL;
            """,
            (task_id, root_revision_id),
        ).fetchall()
        out: list[dict[str, Any]] = []
        for r in rows:
            d = _row_to_dict(r)
            if d is None:
                continue
            d["taint_set"] = _unjsonify(d.get("taint_set_json")) or []
            out.append(d)
        return out

    def mark_invalidated(
        self,
        *,
        validation_receipt_id: str,
        invalidation_reason: str,
        invalidated_at: str | None = None,
    ) -> bool:
        """Mark a receipt invalidated. Returns True iff exactly one row updated.

        Idempotent by design: a row already invalidated is not
        re-mutated, and rowcount will be zero (the caller must treat that
        as "no-op"). Callers must emit the audit/drift record only on a
        `True` return to avoid duplicate evidence emission.
        """
        ts = invalidated_at or _iso_now()
        cur = self._conn.cursor()
        cur.execute(
            """
            UPDATE validation_receipts
               SET invalidated_at = ?, invalidation_reason = ?
             WHERE validation_receipt_id = ?
               AND invalidated_at IS NULL;
            """,
            (ts, invalidation_reason, validation_receipt_id),
        )
        return cur.rowcount == 1


class ReviewArtifactRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def list_for_task_root(
        self, task_id: str, root_revision_id: str
    ) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            """
            SELECT * FROM review_artifacts
             WHERE task_id = ?
               AND root_revision_id = ?
             ORDER BY rowid;
            """,
            (task_id, root_revision_id),
        ).fetchall()
        results: list[dict[str, Any]] = []
        for row in rows:
            d = _row_to_dict(row)
            if d is None:
                continue
            d["rendering_provenance"] = _unjsonify(d.get("rendering_provenance")) or {}
            d["taint_set"] = _unjsonify(d.get("taint_set_json")) or []
            results.append(d)
        return results

    def insert(self, artifact: Mapping[str, Any]) -> None:
        self._conn.execute(
            """
            INSERT INTO review_artifacts (
              review_artifact_id, task_id, root_revision_id, patch_proposal_id,
              diff_hash, semantic_impact_hash, risk_class, rendering_provenance,
              taint_set_json, created_at, version_tuple_hash
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                artifact["review_artifact_id"],
                artifact["task_id"],
                artifact["root_revision_id"],
                artifact["patch_proposal_id"],
                artifact["diff_hash"],
                artifact.get("semantic_impact_hash"),
                artifact["risk_class"],
                _jsonify(artifact["rendering_provenance"]),
                _jsonify(artifact["taint_set"]),
                artifact["created_at"],
                artifact["version_tuple_hash"],
            ),
        )

    def fetch(self, review_artifact_id: str) -> dict[str, Any] | None:
        row = self._conn.execute(
            "SELECT * FROM review_artifacts WHERE review_artifact_id = ?;",
            (review_artifact_id,),
        ).fetchone()
        d = _row_to_dict(row)
        if d is None:
            return None
        d["rendering_provenance"] = _unjsonify(d.get("rendering_provenance")) or {}
        d["taint_set"] = _unjsonify(d.get("taint_set_json")) or []
        return d


class ApprovalArtifactRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def insert(self, artifact: Mapping[str, Any]) -> None:
        self._conn.execute(
            """
            INSERT INTO approval_artifacts (
              approval_id, task_id, originating_root_revision_id,
              reviewed_patch_hash, reviewed_context_artifact_id,
              required_receipt_ids, approval_scope, approver_identity,
              approval_state, policy_version, created_at, expires_at,
              version_tuple_hash, invalidated_at, invalidation_reason,
              conflict_group_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                artifact["approval_id"],
                artifact["task_id"],
                artifact["originating_root_revision_id"],
                artifact["reviewed_patch_hash"],
                artifact["reviewed_context_artifact_id"],
                _jsonify(artifact["required_receipt_ids"]),
                artifact["approval_scope"],
                artifact["approver_identity"],
                artifact["approval_state"],
                artifact["policy_version"],
                artifact["created_at"],
                artifact["expires_at"],
                artifact["version_tuple_hash"],
                artifact.get("invalidated_at"),
                artifact.get("invalidation_reason"),
                artifact.get("conflict_group_id"),
            ),
        )

    def fetch(self, approval_id: str) -> dict[str, Any] | None:
        row = self._conn.execute(
            "SELECT * FROM approval_artifacts WHERE approval_id = ?;",
            (approval_id,),
        ).fetchone()
        d = _row_to_dict(row)
        if d is None:
            return None
        d["required_receipt_ids"] = _unjsonify(d.get("required_receipt_ids")) or []
        return d

    def mark_state(
        self, *, approval_id: str, new_state: str
    ) -> None:
        # Approval state is an on-row mutation per §23.11; the invariant
        # that's load-bearing is that this transition is audit-logged at
        # the service layer and that a passing barrier was evaluated.
        self._conn.execute(
            """
            UPDATE approval_artifacts
               SET approval_state = ?
             WHERE approval_id = ?;
            """,
            (new_state, approval_id),
        )

    def list_live_referencing_receipt(
        self, validation_receipt_id: str
    ) -> list[dict[str, Any]]:
        """Return non-invalidated approvals whose required_receipt_ids
        contains the given validation_receipt_id.

        Phase-1 incremental invalidation cascade (AT-017 / INV-017): when
        a receipt is invalidated, every approval gated on it must be
        invalidated too. Narrow-path approvals carry at most a handful of
        required receipt ids; we filter in-process after a SQL LIKE
        pre-filter to keep the query index-friendly but correct.
        """
        # The pre-filter catches the JSON-encoded form; the in-process
        # list check is the correctness guarantee.
        like_needle = f"%{validation_receipt_id}%"
        rows = self._conn.execute(
            """
            SELECT * FROM approval_artifacts
             WHERE required_receipt_ids LIKE ?
               AND invalidated_at IS NULL;
            """,
            (like_needle,),
        ).fetchall()
        out: list[dict[str, Any]] = []
        for r in rows:
            d = _row_to_dict(r)
            if d is None:
                continue
            ids = _unjsonify(d.get("required_receipt_ids")) or []
            if validation_receipt_id in ids:
                d["required_receipt_ids"] = list(ids)
                out.append(d)
        return out

    def mark_invalidated(
        self,
        *,
        approval_id: str,
        invalidation_reason: str,
        invalidated_at: str | None = None,
    ) -> bool:
        """Mark an approval invalidated. Returns True iff exactly one row updated.

        Sets `approval_state='invalidated'` atomically with
        `invalidated_at`/`invalidation_reason`. The WHERE clause excludes
        rows that are already invalidated so cascade callers are
        idempotent and emit evidence exactly once.
        """
        ts = invalidated_at or _iso_now()
        cur = self._conn.cursor()
        cur.execute(
            """
            UPDATE approval_artifacts
               SET approval_state = 'invalidated',
                   invalidated_at = ?,
                   invalidation_reason = ?
             WHERE approval_id = ?
               AND invalidated_at IS NULL;
            """,
            (ts, invalidation_reason, approval_id),
        )
        return cur.rowcount == 1


# ---------------------------------------------------------------------------
# Revision / JournalEntry / SnapshotRoot (truth spine)
# ---------------------------------------------------------------------------


class RevisionRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def insert_pending(self, artifact: Mapping[str, Any]) -> None:
        self._conn.execute(
            """
            INSERT INTO revisions (
              revision_id, parent_revision_id, project_id, task_id, state,
              root_hash, snapshot_root_id, intent_id,
              originating_context_artifact_id, approval_id,
              logical_sequence_at_seal, version_tuple_hash, taint_set_json,
              created_at, sealed_at, abandonment_reason, recovery_note
            ) VALUES (?, ?, ?, ?, 'pending', ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL, NULL);
            """,
            (
                artifact["revision_id"],
                artifact.get("parent_revision_id"),
                artifact["project_id"],
                artifact["task_id"],
                artifact["root_hash"],
                artifact["snapshot_root_id"],
                artifact["intent_id"],
                artifact["originating_context_artifact_id"],
                artifact.get("approval_id"),
                artifact.get("logical_sequence_at_seal"),
                artifact["version_tuple_hash"],
                _jsonify(artifact.get("taint_set", [])),
                artifact["created_at"],
            ),
        )

    def transition_to_sealed(
        self,
        *,
        revision_id: str,
        sealed_at: str,
        logical_sequence_at_seal: int,
        approval_id: str,
    ) -> None:
        # This is the §22.2 step 7: transition revision state from
        # pending to sealed. It is the only legal mutation of a
        # revisions row other than the initial pending insert; sealed
        # rows are immutable by trigger.
        cur = self._conn.cursor()
        cur.execute(
            """
            UPDATE revisions
               SET state = 'sealed',
                   sealed_at = ?,
                   logical_sequence_at_seal = ?,
                   approval_id = ?
             WHERE revision_id = ? AND state = 'pending';
            """,
            (sealed_at, logical_sequence_at_seal, approval_id, revision_id),
        )
        if cur.rowcount != 1:
            raise RuntimeError(
                f"revision {revision_id!r} could not transition pending->sealed "
                f"(rowcount={cur.rowcount})"
            )

    def fetch(self, revision_id: str) -> dict[str, Any] | None:
        row = self._conn.execute(
            "SELECT * FROM revisions WHERE revision_id = ?;",
            (revision_id,),
        ).fetchone()
        d = _row_to_dict(row)
        if d is None:
            return None
        d["taint_set"] = _unjsonify(d.get("taint_set_json")) or []
        return d

    def has_sealed(self, revision_id: str) -> bool:
        row = self._conn.execute(
            "SELECT 1 FROM revisions WHERE revision_id = ? AND state = 'sealed';",
            (revision_id,),
        ).fetchone()
        return row is not None


class SnapshotRootRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def insert(self, artifact: Mapping[str, Any]) -> None:
        self._conn.execute(
            """
            INSERT INTO snapshot_roots (
              snapshot_root_id, revision_id, root_hash, file_manifest_hash,
              artifact_manifest_hash, parent_snapshot_root_id,
              version_tuple_hash, created_at, storage_locator,
              compaction_generation
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                artifact["snapshot_root_id"],
                artifact["revision_id"],
                artifact["root_hash"],
                artifact["file_manifest_hash"],
                artifact["artifact_manifest_hash"],
                artifact.get("parent_snapshot_root_id"),
                artifact["version_tuple_hash"],
                artifact["created_at"],
                artifact.get("storage_locator"),
                artifact.get("compaction_generation"),
            ),
        )

    def fetch(self, snapshot_root_id: str) -> dict[str, Any] | None:
        row = self._conn.execute(
            "SELECT * FROM snapshot_roots WHERE snapshot_root_id = ?;",
            (snapshot_root_id,),
        ).fetchone()
        return _row_to_dict(row)


class JournalEntryRepository:
    """Append-only journal writer.

    INV-004: logical_sequence is strictly monotonic. The UNIQUE index on
    `logical_sequence` enforces this at the SQL layer. We allocate the
    next sequence inside the same transaction to keep atomicity.
    """

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def list_for_revision(self, revision_id: str) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            """
            SELECT * FROM journal_entries
             WHERE revision_id = ?
             ORDER BY logical_sequence;
            """,
            (revision_id,),
        ).fetchall()
        out: list[dict[str, Any]] = []
        for row in rows:
            d = _row_to_dict(row)
            if d is None:
                continue
            d["taint_set"] = _unjsonify(d.get("taint_set_json")) or []
            out.append(d)
        return out

    def append(self, *, artifact: Mapping[str, Any]) -> int:
        cur = self._conn.cursor()
        row = cur.execute(
            "SELECT COALESCE(MAX(logical_sequence), 0) FROM journal_entries;"
        ).fetchone()
        next_seq = int(row[0]) + 1
        cur.execute(
            """
            INSERT INTO journal_entries (
              journal_entry_id, logical_sequence, entry_type, revision_id,
              parent_revision_id, project_id, task_id, causality_ref,
              payload_hash, version_tuple_hash, taint_set_json, created_at,
              barrier_status, replay_class, failure_bundle_id, drift_event_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                artifact["journal_entry_id"],
                next_seq,
                artifact["entry_type"],
                artifact["revision_id"],
                artifact.get("parent_revision_id"),
                artifact["project_id"],
                artifact["task_id"],
                artifact.get("causality_ref"),
                artifact["payload_hash"],
                artifact["version_tuple_hash"],
                _jsonify(artifact.get("taint_set", [])),
                artifact["created_at"],
                artifact.get("barrier_status"),
                artifact.get("replay_class"),
                artifact.get("failure_bundle_id"),
                artifact.get("drift_event_id"),
            ),
        )
        return next_seq


# ---------------------------------------------------------------------------
# FailureBundle (append-only)
# ---------------------------------------------------------------------------


class FailureBundleRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def list_for_task_root(
        self, task_id: str, root_revision_id: str
    ) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            """
            SELECT * FROM failure_bundles
             WHERE task_id = ?
               AND root_revision_id = ?
             ORDER BY rowid;
            """,
            (task_id, root_revision_id),
        ).fetchall()
        return [d for row in rows if (d := _row_to_dict(row)) is not None]

    def append(self, *, artifact: Mapping[str, Any]) -> None:
        self._conn.execute(
            """
            INSERT INTO failure_bundles (
              failure_bundle_id, task_id, root_revision_id, failure_class,
              cause_hash, evidence_refs, taint_set_json, created_at,
              incident_id, retained_for_forensics_flag, recovery_action_ref
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                artifact["failure_bundle_id"],
                artifact.get("task_id"),
                artifact.get("root_revision_id"),
                artifact["failure_class"],
                artifact["cause_hash"],
                _jsonify(artifact.get("evidence_refs", [])),
                _jsonify(artifact.get("taint_set", [])),
                artifact["created_at"],
                artifact.get("incident_id"),
                1 if artifact.get("retained_for_forensics_flag") else 0,
                artifact.get("recovery_action_ref"),
            ),
        )


class DriftEventRecordRepository:
    """Append-only drift event record writer (§23.19).

    Drift events are emitted when governing upstream inputs for a
    current-path artifact change underneath it (upstream patch drift,
    receipt invalidation cascade, etc.). The SQL trigger enforces
    append-only (no UPDATE, no DELETE); this adapter exposes insert and
    the narrow task/root read surface needed by evidence closure.
    """

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def list_for_task_root(
        self, task_id: str, root_revision_id: str
    ) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            """
            SELECT * FROM drift_event_records
             WHERE task_id = ?
               AND root_revision_id = ?
             ORDER BY rowid;
            """,
            (task_id, root_revision_id),
        ).fetchall()
        results: list[dict[str, Any]] = []
        for row in rows:
            d = _row_to_dict(row)
            if d is None:
                continue
            d["affected_artifact_ids"] = (
                _unjsonify(d.get("affected_artifact_ids")) or []
            )
            results.append(d)
        return results

    def insert(self, record: Mapping[str, Any]) -> None:
        self._conn.execute(
            """
            INSERT INTO drift_event_records (
              drift_event_id, task_id, root_revision_id, drift_class,
              detected_at, affected_artifact_ids, consequence_class,
              approval_id, replay_anchor_id, required_reconciliation_action
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                record["drift_event_id"],
                record.get("task_id"),
                record.get("root_revision_id"),
                record["drift_class"],
                record["detected_at"],
                _jsonify(list(record["affected_artifact_ids"])),
                record["consequence_class"],
                record.get("approval_id"),
                record.get("replay_anchor_id"),
                record.get("required_reconciliation_action"),
            ),
        )


class ReplayAnchorRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def insert(self, anchor: Mapping[str, Any]) -> None:
        self._conn.execute(
            """
            INSERT INTO replay_anchors (
              replay_anchor_id, root_revision_id, project_id, task_id,
              replay_class_claim, required_artifact_ids, version_tuple_hash,
              environment_fingerprint_hash, created_at,
              degradation_reason, unreplayable_reason
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                anchor["replay_anchor_id"],
                anchor["root_revision_id"],
                anchor["project_id"],
                anchor["task_id"],
                anchor["replay_class_claim"],
                _jsonify(anchor["required_artifact_ids"]),
                anchor["version_tuple_hash"],
                anchor["environment_fingerprint_hash"],
                anchor["created_at"],
                anchor.get("degradation_reason"),
                anchor.get("unreplayable_reason"),
            ),
        )

    def fetch(self, replay_anchor_id: str) -> dict[str, Any] | None:
        row = self._conn.execute(
            "SELECT * FROM replay_anchors WHERE replay_anchor_id = ?;",
            (replay_anchor_id,),
        ).fetchone()
        d = _row_to_dict(row)
        if d is None:
            return None
        d["required_artifact_ids"] = (
            _unjsonify(d.get("required_artifact_ids")) or []
        )
        return d
