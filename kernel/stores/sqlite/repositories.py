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
    """Append-only audit record writer.

    Every stage transition of the signable path must land here. The
    INV-026 trigger on `audit_records` guarantees that no UPDATE/DELETE
    can occur at the SQL layer, so this adapter only exposes `append`.
    """

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

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

    def revoke(self, capability_token_id: str, reason: str) -> None:
        # Revocation is an authority-bearing mutation; it is intentionally
        # UPDATE (not append-only) on the `capability_tokens` row because
        # §23.13 treats consumed_at/revoked_at as optional on-row columns.
        # Each revocation MUST also emit an AuditRecord at the service
        # layer; this repository does not synthesize audit.
        self._conn.execute(
            """
            UPDATE capability_tokens
               SET revoked_at = ?, revocation_reason = ?
             WHERE capability_token_id = ?
               AND revoked_at IS NULL;
            """,
            (_iso_now(), reason, capability_token_id),
        )

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


# ---------------------------------------------------------------------------
# Generic artifact writers (thin, schema-validated upstream)
# ---------------------------------------------------------------------------


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
