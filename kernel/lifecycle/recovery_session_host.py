"""
P0-9 phase 1 — RecoverySessionHost.

Constitutional anchors:
- v11 §22.1 WAL Durability and Recovery Contract
- v11 §22.5 Replay admission boundary
- v11 §22.10 invariant binding
- foundation §6 (P0 sealing + crash-window proofs)

A bounded in-process owner of a live `SessionOrchestrator` instance
and a pre-built `RecoveryGate`. This is the smallest correct runtime
boundary at which `restore_task_from_snapshot` is meaningful: a
restored task lives in the host-owned orchestrator's `_tasks` dict
and remains available for follow-on admission against the same
instance for the host's lifetime.

P0-8 proved that a one-shot `recovery_cli restore` subcommand would
be ephemeral and misleading — restored orchestrator memory
disappears when the CLI process exits. P0-9 introduces a host that
keeps the orchestrator alive across restore + admission so the
restore has a continuable runtime effect.

This module is NOT a daemon, web server, async runtime, queue, IPC,
scheduler, or background worker. It is a synchronous in-process
owner of three references and a closed flag.

Out of scope (delegated):
- DB connection ownership: caller responsibility (release via
  ``close_callback``).
- Repository / service wiring: caller responsibility.
- Recovery policy: lives in `RecoveryGate` / `TaskRecoveryClassifier`.
- Restore safety: lives in
  `SignablePathOrchestrator.restore_task_from_snapshot` (the gate's
  final authority).
- Artifact integrity: lives in `StageArtifactExistenceResolver`.
- Schema, migration, or audit ``record_type`` additions: not
  introduced here.

This class does not import `SignablePathOrchestrator`. The owned
runtime is protocol-typed via `SessionOrchestrator` so the host
stays a thin runtime boundary rather than a wiring graph.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping, Optional, Protocol, Union

from kernel.lifecycle.recovery_gate import RecoveryGate, RecoveryGateResult
from kernel.lifecycle.stage_types import Stage
from kernel.lifecycle.task_recovery import (
    RecoveryClass,
    TaskLifecycleSnapshot,
)


# Tables required by every repository wired by
# ``build_recovery_session_host_from_sqlite``. Sourced directly from
# ``kernel/stores/sqlite/migrations/0001_core_signable_path.sql`` and
# the table names embedded in the SELECT/INSERT statements of the
# corresponding repository in ``kernel/stores/sqlite/repositories.py``.
_REQUIRED_RECOVERY_SESSION_HOST_TABLES: frozenset[str] = frozenset(
    {
        "audit_records",
        "budget_records",
        "capability_tokens",
        "context_artifacts",
        "inference_artifacts",
        "intent_anchor_records",
        "patch_proposals",
        "validation_receipts",
        "review_artifacts",
        "approval_artifacts",
        "revisions",
        "snapshot_roots",
        "journal_entries",
        "replay_anchors",
        "taint_records",
        "drift_event_records",
        "failure_bundles",
    }
)


# P0-12 — schema identity contract.
#
# Required column sets per factory-wired table. Sourced directly from
# ``kernel/stores/sqlite/migrations/0001_core_signable_path.sql``. The
# factory's read-only validator inspects ``PRAGMA table_info(<table>)``
# for each entry and refuses to construct a host when any required
# column is absent. Column lists mirror the migration exactly — the
# validator is a schema-identity check, not a "minimum useful subset"
# heuristic.
_REQUIRED_RECOVERY_SESSION_HOST_COLUMNS: dict[str, frozenset[str]] = {
    "revisions": frozenset(
        {
            "revision_id",
            "parent_revision_id",
            "project_id",
            "task_id",
            "state",
            "root_hash",
            "snapshot_root_id",
            "intent_id",
            "originating_context_artifact_id",
            "approval_id",
            "logical_sequence_at_seal",
            "version_tuple_hash",
            "taint_set_json",
            "created_at",
            "sealed_at",
            "abandonment_reason",
            "recovery_note",
        }
    ),
    "journal_entries": frozenset(
        {
            "journal_entry_id",
            "logical_sequence",
            "entry_type",
            "revision_id",
            "parent_revision_id",
            "project_id",
            "task_id",
            "causality_ref",
            "payload_hash",
            "version_tuple_hash",
            "taint_set_json",
            "created_at",
            "barrier_status",
            "replay_class",
            "failure_bundle_id",
            "drift_event_id",
        }
    ),
    "snapshot_roots": frozenset(
        {
            "snapshot_root_id",
            "revision_id",
            "root_hash",
            "file_manifest_hash",
            "artifact_manifest_hash",
            "parent_snapshot_root_id",
            "version_tuple_hash",
            "created_at",
            "storage_locator",
            "compaction_generation",
        }
    ),
    "context_artifacts": frozenset(
        {
            "context_artifact_id",
            "task_id",
            "root_revision_id",
            "repo_graph_version",
            "symbol_index_version",
            "candidate_file_ids",
            "symbol_frontier_ids",
            "memory_item_ids",
            "packing_policy_version",
            "hard_budget_tokens",
            "effective_budget_tokens",
            "actual_tokens",
            "truncation_reason",
            "deferred_retrieval_items",
            "provenance_refs",
            "taint_set_json",
            "content_hash",
            "created_at",
            "version_tuple_hash",
        }
    ),
    "inference_artifacts": frozenset(
        {
            "inference_artifact_id",
            "task_id",
            "root_revision_id",
            "context_artifact_id",
            "worker_run_id",
            "worker_profile",
            "model_route_id",
            "output_hash",
            "provenance_refs",
            "taint_set_json",
            "created_at",
            "version_tuple_hash",
            "token_usage_json",
            "latency_ms",
            "fallback_route_id",
        }
    ),
    "patch_proposals": frozenset(
        {
            "patch_proposal_id",
            "task_id",
            "root_revision_id",
            "inference_artifact_id",
            "target_file_ids",
            "patch_group_hash",
            "side_effect_class_proposal",
            "capability_requirements",
            "taint_set_json",
            "created_at",
            "version_tuple_hash",
        }
    ),
    "validation_receipts": frozenset(
        {
            "validation_receipt_id",
            "task_id",
            "root_revision_id",
            "receipt_type",
            "validator_identity",
            "validator_version",
            "input_hash",
            "result",
            "diagnostics_hash",
            "taint_set_json",
            "created_at",
            "version_tuple_hash",
            "invalidated_at",
            "invalidation_reason",
        }
    ),
    "review_artifacts": frozenset(
        {
            "review_artifact_id",
            "task_id",
            "root_revision_id",
            "patch_proposal_id",
            "diff_hash",
            "semantic_impact_hash",
            "risk_class",
            "rendering_provenance",
            "taint_set_json",
            "created_at",
            "version_tuple_hash",
        }
    ),
    "approval_artifacts": frozenset(
        {
            "approval_id",
            "task_id",
            "originating_root_revision_id",
            "reviewed_patch_hash",
            "reviewed_context_artifact_id",
            "required_receipt_ids",
            "approval_scope",
            "approver_identity",
            "approval_state",
            "policy_version",
            "created_at",
            "expires_at",
            "version_tuple_hash",
            "invalidated_at",
            "invalidation_reason",
            "conflict_group_id",
        }
    ),
    "capability_tokens": frozenset(
        {
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
            "consumed_at",
            "revoked_at",
            "revocation_reason",
            "bound_task_id",
            "bound_root_revision_id",
        }
    ),
    "replay_anchors": frozenset(
        {
            "replay_anchor_id",
            "root_revision_id",
            "project_id",
            "task_id",
            "replay_class_claim",
            "required_artifact_ids",
            "version_tuple_hash",
            "environment_fingerprint_hash",
            "created_at",
            "degradation_reason",
            "unreplayable_reason",
        }
    ),
    "audit_records": frozenset(
        {
            "audit_record_id",
            "task_id",
            "root_revision_id",
            "record_type",
            "causality_ref",
            "actor_identity",
            "artifact_refs",
            "version_tuple_hash",
            "taint_set_json",
            "created_at",
            "payload_json",
            "failure_bundle_id",
            "replay_anchor_id",
            "approval_id",
            "sequence",
        }
    ),
    "failure_bundles": frozenset(
        {
            "failure_bundle_id",
            "task_id",
            "root_revision_id",
            "failure_class",
            "cause_hash",
            "evidence_refs",
            "taint_set_json",
            "created_at",
            "incident_id",
            "retained_for_forensics_flag",
            "recovery_action_ref",
        }
    ),
    "drift_event_records": frozenset(
        {
            "drift_event_id",
            "task_id",
            "root_revision_id",
            "drift_class",
            "detected_at",
            "affected_artifact_ids",
            "consequence_class",
            "approval_id",
            "replay_anchor_id",
            "required_reconciliation_action",
        }
    ),
    "taint_records": frozenset(
        {
            "taint_record_id",
            "subject_id",
            "taint_class",
            "taint_state",
            "source_ref",
            "created_at",
            "cleared_at",
            "clearing_identity",
            "clearing_reason",
        }
    ),
    "budget_records": frozenset(
        {
            "budget_record_id",
            "task_id",
            "budget_class",
            "allocated_amount",
            "consumed_amount",
            "remaining_amount",
            "budget_state",
            "created_at",
            "suspended_at",
            "replenished_at",
            "close_reason",
        }
    ),
    "intent_anchor_records": frozenset(
        {
            "intent_id",
            "task_id",
            "state",
            "created_at",
        }
    ),
}


# P0-12 — required append-only / immutability triggers. Sourced directly
# from ``kernel/stores/sqlite/migrations/0001_core_signable_path.sql``.
# Their absence means INV-004 / INV-005 / INV-026 / §23.15 / §23.17 /
# §23.19 enforcement is silently disabled — a wired host over such a DB
# would accept writes the constitution forbids. The factory must refuse.
_REQUIRED_RECOVERY_SESSION_HOST_TRIGGERS: frozenset[str] = frozenset(
    {
        "revisions_sealed_immutable_update",
        "revisions_sealed_immutable_delete",
        "journal_entries_append_only_update",
        "journal_entries_append_only_delete",
        "audit_records_append_only_update",
        "audit_records_append_only_delete",
        "failure_bundles_append_only_update",
        "failure_bundles_append_only_delete",
        "drift_event_records_append_only_update",
        "drift_event_records_append_only_delete",
        "taint_records_append_only_update",
        "taint_records_append_only_delete",
    }
)


# P0-12 — required critical indexes. Sourced directly from
# ``kernel/stores/sqlite/migrations/0001_core_signable_path.sql``. The
# audit-sequence index is UNIQUE and is the substrate for monotonic
# append order; the journal-sequence index supports recovery readers.
_REQUIRED_RECOVERY_SESSION_HOST_INDEXES: frozenset[str] = frozenset(
    {
        "idx_journal_entries_sequence",
        "idx_audit_records_sequence",
    }
)


# P0-13 — required critical-index uniqueness. Sourced directly from
# ``kernel/stores/sqlite/migrations/0001_core_signable_path.sql``:
# ``idx_audit_records_sequence`` is declared UNIQUE and is the
# substrate for monotonic audit append order; a same-name non-unique
# impostor would silently allow duplicate sequence values without
# tripping the existence-only check from P0-12.
# ``idx_journal_entries_sequence`` is a normal (non-unique) index.
_REQUIRED_RECOVERY_SESSION_HOST_INDEX_UNIQUENESS: dict[str, bool] = {
    "idx_audit_records_sequence": True,
    "idx_journal_entries_sequence": False,
}


# P0-13 — required append-only / immutability trigger SQL invariants.
# Sourced directly from
# ``kernel/stores/sqlite/migrations/0001_core_signable_path.sql``. A
# trigger with the correct name but a no-op body (e.g. ``SELECT 1;``)
# satisfies the existence-only check from P0-12 yet silently disables
# the constitutional invariant the trigger enforces. The factory
# checks for invariant snippets — not full DDL equality — so that
# normal SQLite normalization (whitespace, case, ``IF NOT EXISTS``
# stripping) does not produce false positives.
#
# Snippets are matched after lower-casing both the trigger SQL and
# each snippet; whitespace inside snippets must therefore appear
# verbatim (a single space) in the trigger SQL after SQLite's own
# normalization. The migration uses single spaces, which SQLite
# preserves in ``sqlite_master.sql``.
_REQUIRED_RECOVERY_SESSION_HOST_TRIGGER_SQL_CONTAINS: dict[
    str, tuple[str, ...]
] = {
    "audit_records_append_only_update": (
        "BEFORE UPDATE ON audit_records",
        "RAISE(ABORT",
        "audit_records: append-only",
    ),
    "audit_records_append_only_delete": (
        "BEFORE DELETE ON audit_records",
        "RAISE(ABORT",
        "audit_records: append-only",
    ),
    "journal_entries_append_only_update": (
        "BEFORE UPDATE ON journal_entries",
        "RAISE(ABORT",
        "journal_entries: append-only",
    ),
    "journal_entries_append_only_delete": (
        "BEFORE DELETE ON journal_entries",
        "RAISE(ABORT",
        "journal_entries: append-only",
    ),
    "revisions_sealed_immutable_update": (
        "BEFORE UPDATE ON revisions",
        "WHEN OLD.state = 'sealed'",
        "RAISE(ABORT",
        "revisions: sealed revision is immutable",
    ),
    "revisions_sealed_immutable_delete": (
        "BEFORE DELETE ON revisions",
        "WHEN OLD.state = 'sealed'",
        "RAISE(ABORT",
        "revisions: sealed revision is immutable",
    ),
    "failure_bundles_append_only_update": (
        "BEFORE UPDATE ON failure_bundles",
        "RAISE(ABORT",
        "failure_bundles: append-only",
    ),
    "failure_bundles_append_only_delete": (
        "BEFORE DELETE ON failure_bundles",
        "RAISE(ABORT",
        "failure_bundles: append-only",
    ),
    "drift_event_records_append_only_update": (
        "BEFORE UPDATE ON drift_event_records",
        "RAISE(ABORT",
        "drift_event_records: append-only",
    ),
    "drift_event_records_append_only_delete": (
        "BEFORE DELETE ON drift_event_records",
        "RAISE(ABORT",
        "drift_event_records: append-only",
    ),
    "taint_records_append_only_update": (
        "BEFORE UPDATE ON taint_records",
        "RAISE(ABORT",
        "taint_records: append-only",
    ),
    "taint_records_append_only_delete": (
        "BEFORE DELETE ON taint_records",
        "RAISE(ABORT",
        "taint_records: append-only",
    ),
}


# P0-14 — operator-readable / machine-readable factory error reason codes.
#
# Stable string constants surfaced via
# ``RecoverySessionHostFactoryError.reason_code``. Exposed at module level
# so future operator surfaces (CLI, dashboards, integration tests) can
# branch on a stable identifier rather than parse human-readable strings.
# These values are part of the factory's public failure contract and
# must not be renamed without a coordinated downstream change.
#
# Defined here — alongside the other factory schema-identity constants
# and ABOVE ``_validate_factory_schema_ready`` — so the validator's
# reason-code references resolve to a definition that lexically precedes
# its first use, matching operator-surface readability expectations for
# P0-14.
_FACTORY_ERROR_DEFAULT = "factory_error"
_FACTORY_ERROR_MISSING_DB_FILE = "missing_db_file"
_FACTORY_ERROR_OPEN_ERROR = "open_error"
_FACTORY_ERROR_SCHEMA_METADATA_READ_ERROR = "schema_metadata_read_error"
_FACTORY_ERROR_MISSING_REQUIRED_TABLES = "missing_required_tables"
_FACTORY_ERROR_MISSING_REQUIRED_COLUMNS = "missing_required_columns"
_FACTORY_ERROR_MISSING_REQUIRED_TRIGGERS = "missing_required_triggers"
_FACTORY_ERROR_INVALID_TRIGGER_BODY = "invalid_trigger_body"
_FACTORY_ERROR_MISSING_REQUIRED_INDEXES = "missing_required_indexes"
_FACTORY_ERROR_UNEXPECTED_INDEX_BINDING = "unexpected_index_binding"
_FACTORY_ERROR_INDEX_METADATA_UNAVAILABLE = "index_metadata_unavailable"
_FACTORY_ERROR_WRONG_INDEX_UNIQUENESS = "wrong_index_uniqueness"
_FACTORY_ERROR_WIRING_ERROR = "wiring_error"


class RecoverySessionHostClosed(RuntimeError):
    """Raised when a public `RecoverySessionHost` operation is
    attempted after `close()` has run.

    Subclass of `RuntimeError` so existing broad-except sites do not
    need to learn a new exception type to fail closed; specific
    callers can still catch this class directly to distinguish
    closed-host errors from other runtime conditions.
    """


class SessionOrchestrator(Protocol):
    """Minimal protocol the host requires of the owned orchestrator.

    Avoids a hard import of `SignablePathOrchestrator` so this module
    does not bind to runtime composition. Concrete callers pass
    their `SignablePathOrchestrator` instance directly; the gate's
    `restore_if_allowed` keeps final authority over restore safety
    via `restore_task_from_snapshot`.
    """

    def restore_task_from_snapshot(
        self,
        *,
        snapshot: TaskLifecycleSnapshot,
        recovery_class: RecoveryClass,
    ) -> None: ...

    def current_stage(self, task_id: str) -> Optional[Stage]: ...


class RecoverySessionHost:
    """Bounded in-process owner of a live orchestrator + RecoveryGate.

    Constructor contract:
    - ``recovery_gate``: a fully composed `RecoveryGate` (e.g. built
      via `build_standard_recovery_gate`). The host does not
      construct gates.
    - ``orchestrator``: a live `SessionOrchestrator` instance the
      caller has already wired against the durable substrate. The
      host does not construct orchestrators, repositories, services,
      or DB connections.
    - ``close_callback``: optional zero-arg callable invoked exactly
      once on the first `close()`. Typical use is releasing the
      caller-owned SQLite connection. Exceptions from the callback
      propagate; the host is still marked closed so a subsequent
      `close()` is a no-op.

    Public surface:
    - ``orchestrator`` (property): the owned live instance, for
      callers that want to continue admission after restore.
    - ``evaluate_task(task_id)``: read-only verdict via the gate.
    - ``restore_task(task_id)``: gate's `restore_if_allowed` against
      the owned orchestrator. Restore exceptions
      (`OrchestratorRejected`, integrity-guard failures inside
      `restore_task_from_snapshot`) propagate unchanged.
    - ``current_stage(task_id)``: pass-through to the orchestrator.
    - ``close()``: idempotent host shutdown.
    - ``closed`` (property): boolean state.

    All public operations except `close()` and `closed` raise
    `RecoverySessionHostClosed` after the host has been closed. The
    host writes no durable rows itself; any durable side effect is
    the responsibility of the wrapped orchestrator's existing
    admission boundary (`KernelUnitOfWork`).
    """

    __slots__ = (
        "_gate",
        "_orchestrator",
        "_close_callback",
        "_closed",
    )

    def __init__(
        self,
        *,
        recovery_gate: RecoveryGate,
        orchestrator: SessionOrchestrator,
        close_callback: Optional[Callable[[], None]] = None,
    ) -> None:
        self._gate = recovery_gate
        self._orchestrator = orchestrator
        self._close_callback = close_callback
        self._closed = False

    @property
    def closed(self) -> bool:
        return self._closed

    def _check_open(self) -> None:
        if self._closed:
            raise RecoverySessionHostClosed(
                "RecoverySessionHost is closed"
            )

    @property
    def orchestrator(self) -> SessionOrchestrator:
        self._check_open()
        return self._orchestrator

    def evaluate_task(self, task_id: str) -> RecoveryGateResult:
        self._check_open()
        return self._gate.evaluate(task_id)

    def restore_task(self, task_id: str) -> RecoveryGateResult:
        self._check_open()
        return self._gate.restore_if_allowed(
            task_id=task_id,
            orchestrator=self._orchestrator,
        )

    def current_stage(self, task_id: str) -> Optional[Stage]:
        self._check_open()
        return self._orchestrator.current_stage(task_id)

    def close(self) -> None:
        if self._closed:
            return
        # Mark closed before invoking the callback so a callback
        # exception still leaves the host closed and a subsequent
        # close() is a no-op (callback runs exactly once even on
        # error, never twice).
        self._closed = True
        if self._close_callback is not None:
            self._close_callback()


def _validate_factory_schema_ready(
    conn: sqlite3.Connection, *, db_path: Path
) -> None:
    """Read-only schema identity check for the recovery factory.

    P0-11 verified that every required table exists. P0-12 widened the
    contract to schema identity (tables + columns + named triggers +
    named indexes). P0-13 widens it again so a same-name impostor
    cannot smuggle past existence-only checks:

    - every required table exists (P0-11 baseline)
    - every required column on every factory-wired table exists
    - every required append-only / immutability trigger exists
    - every required trigger's body contains the constitutional
      invariant snippets sourced from migration 0001
    - every required critical index exists
    - every required critical index has the expected uniqueness
      (e.g. ``idx_audit_records_sequence`` MUST remain UNIQUE)

    Inspects ``sqlite_master``, ``PRAGMA table_info``, and
    ``PRAGMA index_list`` only — never writes, never creates tables,
    never calls ``apply_migrations``, never repairs malformed schema.
    Any deviation raises `RecoverySessionHostFactoryError` so the
    factory fails closed before constructing repositories, services,
    the orchestrator, or the gate.

    SQL safety: PRAGMA does not parameterize the table name, so the
    validator iterates only over the names declared in the private
    ``_REQUIRED_RECOVERY_SESSION_HOST_COLUMNS`` constant or resolved
    via ``sqlite_master.tbl_name`` and re-validated against
    ``_REQUIRED_RECOVERY_SESSION_HOST_TABLES``. Arbitrary external
    table names are never substituted into the PRAGMA call.
    """
    try:
        table_rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table';"
        ).fetchall()
    except sqlite3.Error as exc:
        raise RecoverySessionHostFactoryError(
            f"recovery session host factory failed to read sqlite "
            f"table metadata for {db_path}: {exc}",
            reason_code=_FACTORY_ERROR_SCHEMA_METADATA_READ_ERROR,
            details={
                "db_path": str(db_path),
                "phase": "tables",
                "error_type": exc.__class__.__name__,
            },
        ) from exc
    present_tables = {row[0] for row in table_rows}
    missing_tables = (
        _REQUIRED_RECOVERY_SESSION_HOST_TABLES - present_tables
    )
    if missing_tables:
        raise RecoverySessionHostFactoryError(
            f"recovery session host factory refused to construct host: "
            f"SQLite database at {db_path} is missing required schema "
            f"table(s): {sorted(missing_tables)!r}",
            reason_code=_FACTORY_ERROR_MISSING_REQUIRED_TABLES,
            details={
                "db_path": str(db_path),
                "missing_tables": sorted(missing_tables),
            },
        )

    # Column existence per factory-wired table. Column names sourced
    # from migration 0001; never accept external table names here.
    for table_name in sorted(_REQUIRED_RECOVERY_SESSION_HOST_COLUMNS):
        required_columns = _REQUIRED_RECOVERY_SESSION_HOST_COLUMNS[
            table_name
        ]
        try:
            info_rows = conn.execute(
                f"PRAGMA table_info({table_name});"
            ).fetchall()
        except sqlite3.Error as exc:
            raise RecoverySessionHostFactoryError(
                f"recovery session host factory failed to read column "
                f"metadata for table {table_name!r} in {db_path}: {exc}",
                reason_code=_FACTORY_ERROR_SCHEMA_METADATA_READ_ERROR,
                details={
                    "db_path": str(db_path),
                    "phase": "columns",
                    "table": table_name,
                    "error_type": exc.__class__.__name__,
                },
            ) from exc
        # PRAGMA table_info returns rows of (cid, name, type, notnull,
        # dflt_value, pk).
        present_columns = {row[1] for row in info_rows}
        missing_columns = required_columns - present_columns
        if missing_columns:
            raise RecoverySessionHostFactoryError(
                f"recovery session host factory refused to construct "
                f"host: SQLite database at {db_path} table "
                f"{table_name!r} is missing required column(s): "
                f"{sorted(missing_columns)!r}",
                reason_code=_FACTORY_ERROR_MISSING_REQUIRED_COLUMNS,
                details={
                    "db_path": str(db_path),
                    "table": table_name,
                    "missing_columns": sorted(missing_columns),
                },
            )

    # Append-only / immutability triggers — existence first, then
    # invariant-snippet check on each trigger body so that a same-name
    # no-op impostor (e.g. ``BEGIN SELECT 1; END``) cannot satisfy the
    # P0-12 existence-only contract.
    try:
        trigger_rows = conn.execute(
            "SELECT name, sql FROM sqlite_master WHERE type = 'trigger';"
        ).fetchall()
    except sqlite3.Error as exc:
        raise RecoverySessionHostFactoryError(
            f"recovery session host factory failed to read sqlite "
            f"trigger metadata for {db_path}: {exc}",
            reason_code=_FACTORY_ERROR_SCHEMA_METADATA_READ_ERROR,
            details={
                "db_path": str(db_path),
                "phase": "triggers",
                "error_type": exc.__class__.__name__,
            },
        ) from exc
    present_triggers = {row[0] for row in trigger_rows}
    trigger_sql_map: dict[str, str] = {
        row[0]: (row[1] or "") for row in trigger_rows
    }
    missing_triggers = (
        _REQUIRED_RECOVERY_SESSION_HOST_TRIGGERS - present_triggers
    )
    if missing_triggers:
        raise RecoverySessionHostFactoryError(
            f"recovery session host factory refused to construct host: "
            f"SQLite database at {db_path} is missing required "
            f"append-only trigger(s): {sorted(missing_triggers)!r}",
            reason_code=_FACTORY_ERROR_MISSING_REQUIRED_TRIGGERS,
            details={
                "db_path": str(db_path),
                "missing_triggers": sorted(missing_triggers),
            },
        )

    # P0-13 — required trigger body invariant snippets.
    for trigger_name in sorted(
        _REQUIRED_RECOVERY_SESSION_HOST_TRIGGER_SQL_CONTAINS
    ):
        snippets = _REQUIRED_RECOVERY_SESSION_HOST_TRIGGER_SQL_CONTAINS[
            trigger_name
        ]
        raw_sql = trigger_sql_map.get(trigger_name, "")
        normalized_sql = " ".join(raw_sql.split()).lower()
        for snippet in snippets:
            normalized_snippet = " ".join(snippet.split()).lower()
            if normalized_snippet not in normalized_sql:
                raise RecoverySessionHostFactoryError(
                    f"recovery session host factory refused to construct "
                    f"host: SQLite database at {db_path} trigger "
                    f"{trigger_name!r} body is missing required invariant "
                    f"snippet {snippet!r}",
                    reason_code=_FACTORY_ERROR_INVALID_TRIGGER_BODY,
                    details={
                        "db_path": str(db_path),
                        "trigger": trigger_name,
                        "missing_snippet": snippet,
                    },
                )

    # Critical indexes — existence first, then uniqueness.
    try:
        index_rows = conn.execute(
            "SELECT name, tbl_name FROM sqlite_master "
            "WHERE type = 'index';"
        ).fetchall()
    except sqlite3.Error as exc:
        raise RecoverySessionHostFactoryError(
            f"recovery session host factory failed to read sqlite "
            f"index metadata for {db_path}: {exc}",
            reason_code=_FACTORY_ERROR_SCHEMA_METADATA_READ_ERROR,
            details={
                "db_path": str(db_path),
                "phase": "indexes",
                "error_type": exc.__class__.__name__,
            },
        ) from exc
    present_indexes = {row[0] for row in index_rows}
    index_table_map: dict[str, str] = {row[0]: row[1] for row in index_rows}
    missing_indexes = (
        _REQUIRED_RECOVERY_SESSION_HOST_INDEXES - present_indexes
    )
    if missing_indexes:
        raise RecoverySessionHostFactoryError(
            f"recovery session host factory refused to construct host: "
            f"SQLite database at {db_path} is missing required "
            f"critical index(es): {sorted(missing_indexes)!r}",
            reason_code=_FACTORY_ERROR_MISSING_REQUIRED_INDEXES,
            details={
                "db_path": str(db_path),
                "missing_indexes": sorted(missing_indexes),
            },
        )

    # P0-13 — required-index uniqueness check. Uses PRAGMA index_list,
    # which is the SQLite metadata authority for "is this index UNIQUE".
    # The parent-table name is resolved from sqlite_master.tbl_name and
    # then re-validated against the required-tables allowlist before
    # being substituted into the PRAGMA call, so an arbitrary tbl_name
    # is never passed to PRAGMA.
    for required_index in sorted(
        _REQUIRED_RECOVERY_SESSION_HOST_INDEX_UNIQUENESS
    ):
        expected_unique = (
            _REQUIRED_RECOVERY_SESSION_HOST_INDEX_UNIQUENESS[required_index]
        )
        table_name = index_table_map.get(required_index)
        if (
            table_name is None
            or table_name not in _REQUIRED_RECOVERY_SESSION_HOST_TABLES
        ):
            raise RecoverySessionHostFactoryError(
                f"recovery session host factory refused to construct "
                f"host: SQLite database at {db_path} required index "
                f"{required_index!r} is attached to unexpected table "
                f"{table_name!r}",
                reason_code=_FACTORY_ERROR_UNEXPECTED_INDEX_BINDING,
                details={
                    "db_path": str(db_path),
                    "index": required_index,
                    "actual_table": table_name,
                },
            )
        try:
            list_rows = conn.execute(
                f"PRAGMA index_list({table_name});"
            ).fetchall()
        except sqlite3.Error as exc:
            raise RecoverySessionHostFactoryError(
                f"recovery session host factory failed to read index "
                f"metadata for table {table_name!r} in {db_path}: {exc}",
                reason_code=_FACTORY_ERROR_SCHEMA_METADATA_READ_ERROR,
                details={
                    "db_path": str(db_path),
                    "phase": "index_list",
                    "table": table_name,
                    "error_type": exc.__class__.__name__,
                },
            ) from exc
        # PRAGMA index_list returns rows of (seq, name, unique, origin,
        # partial). We only need name + unique flag.
        actual_unique: Optional[bool] = None
        for row in list_rows:
            if row[1] == required_index:
                actual_unique = bool(row[2])
                break
        if actual_unique is None:
            raise RecoverySessionHostFactoryError(
                f"recovery session host factory refused to construct "
                f"host: SQLite database at {db_path} could not resolve "
                f"uniqueness for required index {required_index!r}",
                reason_code=_FACTORY_ERROR_INDEX_METADATA_UNAVAILABLE,
                details={
                    "db_path": str(db_path),
                    "index": required_index,
                    "table": table_name,
                },
            )
        if actual_unique != expected_unique:
            raise RecoverySessionHostFactoryError(
                f"recovery session host factory refused to construct "
                f"host: SQLite database at {db_path} index "
                f"{required_index!r} has wrong uniqueness: expected "
                f"unique={expected_unique}, actual unique={actual_unique}",
                reason_code=_FACTORY_ERROR_WRONG_INDEX_UNIQUENESS,
                details={
                    "db_path": str(db_path),
                    "index": required_index,
                    "expected_unique": expected_unique,
                    "actual_unique": actual_unique,
                },
            )


class RecoverySessionHostFactoryError(RuntimeError):
    """Raised when `build_recovery_session_host_from_sqlite` cannot
    produce a host.

    Subclass of `RuntimeError` so existing broad-except sites do not
    need to learn a new exception type to fail closed; specific
    callers (operators, integration tests) can still catch this class
    directly to distinguish factory-construction failures (missing DB
    file, repository wiring failure) from other runtime conditions.

    The factory raises this exception strictly BEFORE returning a
    host — successful construction returns the host and never
    raises. If construction fails after the SQLite connection is
    opened, the factory closes that connection before raising so the
    operator never inherits a leaked file handle.

    P0-14 — operator error surface. The exception carries two stable
    machine-readable fields alongside the existing human-readable
    message, so operator surfaces can branch on a stable identifier
    rather than parse strings:

    - ``reason_code``: stable string from the
      ``_FACTORY_ERROR_*`` constants (default
      ``"factory_error"``).
    - ``details``: a plain ``dict`` of supplementary fields (e.g.
      ``db_path``, ``missing_tables``, ``error_type``). Always a real
      ``dict`` — never ``None`` — and copied from the caller-supplied
      mapping so post-construction caller mutation cannot affect the
      raised exception.

    Backwards compatibility:
    - ``RecoverySessionHostFactoryError("plain failure")`` still works
      and ``str(exc)`` still returns ``"plain failure"``.
    - The default ``reason_code`` is ``"factory_error"`` and the
      default ``details`` is an empty ``dict``.
    """

    def __init__(
        self,
        message: str,
        *,
        reason_code: str = _FACTORY_ERROR_DEFAULT,
        details: Optional[Mapping[str, object]] = None,
    ) -> None:
        super().__init__(message)
        self.reason_code = reason_code
        self.details: dict[str, object] = (
            dict(details) if details is not None else {}
        )


@dataclass(frozen=True)
class RecoverySessionHostFactoryResult:
    """Non-exception operator result for factory construction."""

    ok: bool
    host: RecoverySessionHost | None
    reason_code: str | None
    message: str | None
    details: dict[str, object]

    def __post_init__(self) -> None:
        object.__setattr__(self, "details", dict(self.details))


def build_recovery_session_host_from_sqlite(
    *,
    db_path: Union[str, Path],
) -> RecoverySessionHost:
    """Construct a `RecoverySessionHost` over an existing SQLite DB file.

    P0-10 phase 1 — the smallest correct production-side construction
    boundary for `RecoverySessionHost`. Until P0-10 the host could only
    be wired by tests; this factory promotes it to "production code has
    one standard operator construction boundary" without introducing a
    daemon, async runtime, queue, web server, IPC, scheduler, or
    background worker.

    Behavior:

    - The ``db_path`` MUST point at an existing SQLite database file.
      The factory checks ``Path(db_path).is_file()`` before opening,
      and raises `RecoverySessionHostFactoryError` when the path does
      not exist. The factory NEVER creates a new database file as a
      side effect of a typo (mirrors `recovery_cli.main`'s P0-6
      operator-boundary semantics).
    - After opening the connection and before constructing any
      repository, service, orchestrator, or gate, the factory runs a
      read-only schema readiness check
      (``_validate_factory_schema_ready``) against ``sqlite_master``.
      If any required table is missing — empty file, malformed DB,
      pre-migration DB, or wrong DB — the factory closes the opened
      connection and raises `RecoverySessionHostFactoryError`.
    - The factory does NOT call `apply_migrations`. The caller is
      responsible for having initialized schema before construction.
      The schema readiness check inspects metadata only; it never
      creates tables.
    - The factory composes the same production classes used by the
      narrow signable path: kernel-level repositories, the
      `AppendOnlyLedger`, the eight signable-path services, the
      `BudgetGovernor`, a `SignablePathOrchestrator`, and the standard
      `RecoveryGate` built via `build_standard_recovery_gate`.
    - The factory writes NO durable rows during construction. It does
      NOT call `RecoveryGate.restore_if_allowed`. It does NOT call
      `restore_task_from_snapshot`. It does NOT auto-restore any task.
    - The factory owns the SQLite connection it opens. The returned
      host's `close()` releases the connection through
      `close_callback`. If construction fails after the connection
      is opened, the factory closes it before raising.

    The InferenceService is intentionally constructed without a real
    `ModelAdapter` because the factory's purpose is recovery
    evaluation / restore — not new inference. The service falls back
    to its in-module `_NullAdapter`, which raises
    `model_adapter_not_configured` if a caller mistakenly attempts
    `admit_inference` against this host. This matches the
    "evaluate / restore" scope of P0-10 phase 1.
    """
    # Imports are local to keep `RecoverySessionHost` itself a thin
    # runtime boundary: the host class continues to bind only the
    # protocol-typed `SessionOrchestrator`, while the factory pulls in
    # the production wiring graph only when an operator constructs a
    # host through it.
    from kernel.evidence.append_only_ledger import AppendOnlyLedger
    from kernel.lifecycle.recovery_gate import (
        build_standard_recovery_gate,
    )
    from kernel.lifecycle.signable_path_orchestrator import (
        SignablePathOrchestrator,
    )
    from kernel.services.approval_service import ApprovalService
    from kernel.services.budget_governor import BudgetGovernor
    from kernel.services.capability_service import CapabilityService
    from kernel.services.context_service import ContextService
    from kernel.services.evidence_service import EvidenceService
    from kernel.services.inference_service import InferenceService
    from kernel.services.patch_proposal_service import (
        PatchProposalService,
    )
    from kernel.services.review_service import ReviewService
    from kernel.services.revision_seal_service import RevisionSealService
    from kernel.services.validation_service import ValidationService
    from kernel.stores.sqlite.repositories import (
        ApprovalArtifactRepository,
        AuditRepository,
        BudgetRepository,
        CapabilityRepository,
        ContextArtifactRepository,
        DriftEventRecordRepository,
        FailureBundleRepository,
        InferenceArtifactRepository,
        IntentAnchorRepository,
        JournalEntryRepository,
        PatchProposalRepository,
        ReplayAnchorRepository,
        ReviewArtifactRepository,
        RevisionRepository,
        SnapshotRootRepository,
        TaintRepository,
        ValidationReceiptRepository,
    )
    from kernel.stores.sqlite.wal_recovery import open_connection

    path = Path(db_path)
    if not path.is_file():
        raise RecoverySessionHostFactoryError(
            f"database file does not exist: {path}",
            reason_code=_FACTORY_ERROR_MISSING_DB_FILE,
            details={"db_path": str(path)},
        )

    try:
        conn = open_connection(path)
    except Exception as exc:
        raise RecoverySessionHostFactoryError(
            f"failed to open SQLite connection at {path}: {exc}",
            reason_code=_FACTORY_ERROR_OPEN_ERROR,
            details={
                "db_path": str(path),
                "error_type": exc.__class__.__name__,
            },
        ) from exc

    # Read-only schema readiness check. Runs immediately after the
    # connection is opened and before any repository/service/
    # orchestrator/gate is constructed. Fails closed when required
    # tables are missing — never applies migrations, never creates
    # schema. If the check fails, close the connection so the operator
    # never inherits a leaked file handle.
    try:
        _validate_factory_schema_ready(conn, db_path=path)
    except RecoverySessionHostFactoryError:
        try:
            conn.close()
        except Exception:
            pass
        raise
    except Exception as exc:
        try:
            conn.close()
        except Exception:
            pass
        raise RecoverySessionHostFactoryError(
            f"recovery session host factory schema validation failed "
            f"for {path}: {exc}",
            reason_code=_FACTORY_ERROR_SCHEMA_METADATA_READ_ERROR,
            details={
                "db_path": str(path),
                "error_type": exc.__class__.__name__,
            },
        ) from exc

    try:
        audit_repo = AuditRepository(conn)
        budget_repo = BudgetRepository(conn)
        cap_repo = CapabilityRepository(conn)
        ctx_repo = ContextArtifactRepository(conn)
        inf_repo = InferenceArtifactRepository(conn)
        intent_repo = IntentAnchorRepository(conn)
        pp_repo = PatchProposalRepository(conn)
        vr_repo = ValidationReceiptRepository(conn)
        rv_repo = ReviewArtifactRepository(conn)
        ap_repo = ApprovalArtifactRepository(conn)
        rev_repo = RevisionRepository(conn)
        snap_repo = SnapshotRootRepository(conn)
        je_repo = JournalEntryRepository(conn)
        ra_repo = ReplayAnchorRepository(conn)
        taint_repo = TaintRepository(conn)
        drift_repo = DriftEventRecordRepository(conn)
        failure_repo = FailureBundleRepository(conn)

        audit_ledger = AppendOnlyLedger(
            repository=audit_repo,
            actor_identity="recovery_session_host_factory",
        )

        cap_svc = CapabilityService(
            repository=cap_repo,
            audit_ledger=audit_ledger,
        )
        ctx_svc = ContextService(
            repository=ctx_repo,
            audit_ledger=audit_ledger,
        )
        budget_governor = BudgetGovernor(
            audit_ledger=audit_ledger,
            budget_repository=budget_repo,
        )
        # The InferenceService falls back to `_NullAdapter` when no
        # adapter is wired. P0-10 phase 1 is recovery evaluation /
        # restore only — the factory deliberately does not select a
        # real model adapter here.
        inf_svc = InferenceService(
            repository=inf_repo,
            audit_ledger=audit_ledger,
            context_reader=ctx_repo,
            budget_governor=budget_governor,
            failure_bundle_repository=failure_repo,
        )
        pp_svc = PatchProposalService(
            repository=pp_repo,
            inference_reader=inf_repo,
            audit_ledger=audit_ledger,
        )
        val_svc = ValidationService(
            repository=vr_repo,
            patch_reader=pp_repo,
            audit_ledger=audit_ledger,
            taint_repository=taint_repo,
        )
        rv_svc = ReviewService(
            repository=rv_repo,
            patch_reader=pp_repo,
            receipt_reader=vr_repo,
            audit_ledger=audit_ledger,
        )
        ap_svc = ApprovalService(
            repository=ap_repo,
            patch_reader=pp_repo,
            receipt_reader=vr_repo,
            review_reader=rv_repo,
            audit_ledger=audit_ledger,
        )
        seal_svc = RevisionSealService(
            revision_repo=rev_repo,
            snapshot_repo=snap_repo,
            journal_repo=je_repo,
            approval_repo=ap_repo,
            patch_reader=pp_repo,
            approval_service=ap_svc,
            audit_ledger=audit_ledger,
            intent_anchor_reader=intent_repo,
        )
        evidence_svc = EvidenceService(
            replay_anchor_repo=ra_repo,
            revision_repo=rev_repo,
            context_repo=ctx_repo,
            inference_repo=inf_repo,
            approval_repo=ap_repo,
            taint_repo=taint_repo,
            budget_repo=budget_repo,
            drift_repo=drift_repo,
            failure_repo=failure_repo,
            journal_repo=je_repo,
            review_repo=rv_repo,
            capability_repo=cap_repo,
            audit_repo=audit_repo,
            audit_ledger=audit_ledger,
        )

        orchestrator = SignablePathOrchestrator(
            capability_service=cap_svc,
            context_service=ctx_svc,
            inference_service=inf_svc,
            patch_proposal_service=pp_svc,
            validation_service=val_svc,
            review_service=rv_svc,
            approval_service=ap_svc,
            revision_seal_service=seal_svc,
            evidence_service=evidence_svc,
            audit_ledger=audit_ledger,
            budget_governor=budget_governor,
            context_repository=ctx_repo,
            intent_anchor_repository=intent_repo,
            connection=conn,
        )

        recovery_gate = build_standard_recovery_gate(
            audit_repository=audit_repo,
            intent_anchor_repository=intent_repo,
            context_repository=ctx_repo,
            inference_repository=inf_repo,
            patch_proposal_repository=pp_repo,
            validation_receipt_repository=vr_repo,
            review_repository=rv_repo,
            approval_repository=ap_repo,
            revision_repository=rev_repo,
            replay_anchor_repository=ra_repo,
        )
    except Exception as exc:
        try:
            conn.close()
        except Exception:
            pass
        raise RecoverySessionHostFactoryError(
            f"recovery session host factory wiring failed: {exc}",
            reason_code=_FACTORY_ERROR_WIRING_ERROR,
            details={
                "db_path": str(path),
                "error_type": exc.__class__.__name__,
            },
        ) from exc

    return RecoverySessionHost(
        recovery_gate=recovery_gate,
        orchestrator=orchestrator,
        close_callback=conn.close,
    )


def try_build_recovery_session_host_from_sqlite(
    *,
    db_path: str | Path,
) -> RecoverySessionHostFactoryResult:
    """Return an operator-readable result for factory construction.

    Catches only `RecoverySessionHostFactoryError`; unexpected defects
    propagate so programming errors are not converted into recoverable
    operator failures.
    """
    try:
        host = build_recovery_session_host_from_sqlite(db_path=db_path)
    except RecoverySessionHostFactoryError as exc:
        return RecoverySessionHostFactoryResult(
            ok=False,
            host=None,
            reason_code=exc.reason_code,
            message=str(exc),
            details=dict(exc.details),
        )
    return RecoverySessionHostFactoryResult(
        ok=True,
        host=host,
        reason_code=None,
        message=None,
        details={},
    )
