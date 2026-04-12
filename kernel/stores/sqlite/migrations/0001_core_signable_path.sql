-- Migration 0001: core signable-path schema (first-slice)
--
-- Constitutional anchors:
--   v11 §22.1 (WAL Durability and Recovery Contract)
--   v11 §22.2 (Seal Transaction Ordering Contract)
--   v11 §23.1..23.17, §23.19 (frozen schema pack; first-slice subset)
--   v11 §24.2 INV-004/005/026 (journal monotonicity, seal durability, audit append-only)
--
-- Scope:
--   Creates the minimum set of tables required to persist the first narrow
--   signable path and its supporting authority/taint/replay/audit ledgers.
--   Append-only tables enforce INV-026 via triggers (no UPDATE/DELETE).
--
-- Durability posture:
--   journal_mode = WAL is set by the DB opener; this migration does not
--   PRAGMA so it remains idempotent. The opener is responsible for
--   declaring WAL + synchronous=NORMAL-or-stricter before any mutation.

BEGIN;

-- -------------------------------------------------------------------------
-- 1) Truth spine: revisions, journal entries, snapshot roots
-- -------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS revisions (
  revision_id                     TEXT PRIMARY KEY,
  parent_revision_id              TEXT,
  project_id                      TEXT NOT NULL,
  task_id                         TEXT NOT NULL,
  state                           TEXT NOT NULL
                                    CHECK (state IN ('pending','sealed','abandoned')),
  root_hash                       TEXT NOT NULL,
  snapshot_root_id                TEXT NOT NULL,
  intent_id                       TEXT NOT NULL,
  originating_context_artifact_id TEXT NOT NULL,
  approval_id                     TEXT,
  logical_sequence_at_seal        INTEGER,
  version_tuple_hash              TEXT NOT NULL,
  taint_set_json                  TEXT NOT NULL DEFAULT '[]',
  created_at                      TEXT NOT NULL,
  sealed_at                       TEXT,
  abandonment_reason              TEXT,
  recovery_note                   TEXT
);

-- Sealed revisions are immutable (§23.1). Block UPDATE on any row whose
-- state is already 'sealed'. Pending -> sealed transition is a DELETE +
-- INSERT of a new row? No: the state column transitions in place. So we
-- guard against updates that would rewrite a *sealed* row.
CREATE TRIGGER IF NOT EXISTS revisions_sealed_immutable_update
BEFORE UPDATE ON revisions
FOR EACH ROW
WHEN OLD.state = 'sealed'
BEGIN
  SELECT RAISE(ABORT, 'revisions: sealed revision is immutable (INV-005/§23.1)');
END;

CREATE TRIGGER IF NOT EXISTS revisions_sealed_immutable_delete
BEFORE DELETE ON revisions
FOR EACH ROW
WHEN OLD.state = 'sealed'
BEGIN
  SELECT RAISE(ABORT, 'revisions: sealed revision is immutable (INV-005/§23.1)');
END;

CREATE TABLE IF NOT EXISTS journal_entries (
  journal_entry_id    TEXT PRIMARY KEY,
  logical_sequence    INTEGER NOT NULL UNIQUE,
  entry_type          TEXT NOT NULL,
  revision_id         TEXT NOT NULL,
  parent_revision_id  TEXT,
  project_id          TEXT NOT NULL,
  task_id             TEXT NOT NULL,
  causality_ref       TEXT,
  payload_hash        TEXT NOT NULL,
  version_tuple_hash  TEXT NOT NULL,
  taint_set_json      TEXT NOT NULL DEFAULT '[]',
  created_at          TEXT NOT NULL,
  barrier_status      TEXT,
  replay_class        TEXT,
  failure_bundle_id   TEXT,
  drift_event_id      TEXT
);

CREATE INDEX IF NOT EXISTS idx_journal_entries_sequence
  ON journal_entries (logical_sequence);

-- Journal entries are immutable (§23.2 / INV-004).
CREATE TRIGGER IF NOT EXISTS journal_entries_append_only_update
BEFORE UPDATE ON journal_entries
BEGIN
  SELECT RAISE(ABORT, 'journal_entries: append-only (INV-004/§23.2)');
END;

CREATE TRIGGER IF NOT EXISTS journal_entries_append_only_delete
BEFORE DELETE ON journal_entries
BEGIN
  SELECT RAISE(ABORT, 'journal_entries: append-only (INV-004/§23.2)');
END;

CREATE TABLE IF NOT EXISTS snapshot_roots (
  snapshot_root_id         TEXT PRIMARY KEY,
  revision_id              TEXT NOT NULL,
  root_hash                TEXT NOT NULL,
  file_manifest_hash       TEXT NOT NULL,
  artifact_manifest_hash   TEXT NOT NULL,
  parent_snapshot_root_id  TEXT,
  version_tuple_hash       TEXT NOT NULL,
  created_at               TEXT NOT NULL,
  storage_locator          TEXT,
  compaction_generation    INTEGER
);

-- -------------------------------------------------------------------------
-- 2) Signable-path artifacts
-- -------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS context_artifacts (
  context_artifact_id     TEXT PRIMARY KEY,
  task_id                 TEXT NOT NULL,
  root_revision_id        TEXT NOT NULL,
  repo_graph_version      TEXT NOT NULL,
  symbol_index_version    TEXT NOT NULL,
  candidate_file_ids      TEXT NOT NULL, -- JSON array
  symbol_frontier_ids     TEXT NOT NULL,
  memory_item_ids         TEXT NOT NULL, -- MUST be '[]' in phase 1 (foundation §3 item 11)
  packing_policy_version  TEXT NOT NULL,
  hard_budget_tokens      INTEGER NOT NULL,
  effective_budget_tokens INTEGER NOT NULL,
  actual_tokens           INTEGER NOT NULL,
  truncation_reason       TEXT,
  deferred_retrieval_items TEXT NOT NULL,
  provenance_refs         TEXT NOT NULL,
  taint_set_json          TEXT NOT NULL DEFAULT '[]',
  content_hash            TEXT NOT NULL,
  created_at              TEXT NOT NULL,
  version_tuple_hash      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS inference_artifacts (
  inference_artifact_id TEXT PRIMARY KEY,
  task_id               TEXT NOT NULL,
  root_revision_id      TEXT NOT NULL,
  context_artifact_id   TEXT NOT NULL,
  worker_run_id         TEXT NOT NULL,
  worker_profile        TEXT NOT NULL,
  model_route_id        TEXT NOT NULL,
  output_hash           TEXT NOT NULL,
  provenance_refs       TEXT NOT NULL,
  taint_set_json        TEXT NOT NULL DEFAULT '[]',
  created_at            TEXT NOT NULL,
  version_tuple_hash    TEXT NOT NULL,
  token_usage_json      TEXT,
  latency_ms            INTEGER,
  fallback_route_id     TEXT
);

CREATE TABLE IF NOT EXISTS patch_proposals (
  patch_proposal_id          TEXT PRIMARY KEY,
  task_id                    TEXT NOT NULL,
  root_revision_id           TEXT NOT NULL,
  inference_artifact_id      TEXT NOT NULL,
  target_file_ids            TEXT NOT NULL, -- JSON array; phase-1 length MUST be 1
  patch_group_hash           TEXT NOT NULL,
  side_effect_class_proposal TEXT NOT NULL,
  capability_requirements    TEXT NOT NULL,
  taint_set_json             TEXT NOT NULL DEFAULT '[]',
  created_at                 TEXT NOT NULL,
  version_tuple_hash         TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS validation_receipts (
  validation_receipt_id TEXT PRIMARY KEY,
  task_id               TEXT NOT NULL,
  root_revision_id      TEXT NOT NULL,
  receipt_type          TEXT NOT NULL,
  validator_identity    TEXT NOT NULL,
  validator_version     TEXT NOT NULL,
  input_hash            TEXT NOT NULL,
  result                TEXT NOT NULL CHECK (result IN ('pass','fail','quarantined')),
  diagnostics_hash      TEXT NOT NULL,
  taint_set_json        TEXT NOT NULL DEFAULT '[]',
  created_at            TEXT NOT NULL,
  version_tuple_hash    TEXT NOT NULL,
  invalidated_at        TEXT,
  invalidation_reason   TEXT
);

CREATE TABLE IF NOT EXISTS review_artifacts (
  review_artifact_id   TEXT PRIMARY KEY,
  task_id              TEXT NOT NULL,
  root_revision_id     TEXT NOT NULL,
  patch_proposal_id    TEXT NOT NULL,
  diff_hash            TEXT NOT NULL,
  semantic_impact_hash TEXT,
  risk_class           TEXT NOT NULL,
  rendering_provenance TEXT NOT NULL, -- JSON
  taint_set_json       TEXT NOT NULL DEFAULT '[]',
  created_at           TEXT NOT NULL,
  version_tuple_hash   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS approval_artifacts (
  approval_id                   TEXT PRIMARY KEY,
  task_id                       TEXT NOT NULL,
  originating_root_revision_id  TEXT NOT NULL,
  reviewed_patch_hash           TEXT NOT NULL,
  reviewed_context_artifact_id  TEXT NOT NULL,
  required_receipt_ids          TEXT NOT NULL,
  approval_scope                TEXT NOT NULL,
  approver_identity             TEXT NOT NULL,
  approval_state                TEXT NOT NULL
    CHECK (approval_state IN ('pending','approved','rejected','expired','invalidated')),
  policy_version                TEXT NOT NULL,
  created_at                    TEXT NOT NULL,
  expires_at                    TEXT NOT NULL,
  version_tuple_hash            TEXT NOT NULL,
  invalidated_at                TEXT,
  invalidation_reason           TEXT,
  conflict_group_id             TEXT
);

-- -------------------------------------------------------------------------
-- 3) Authority ledger: capability tokens (single-use consume gate)
-- -------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS capability_tokens (
  capability_token_id     TEXT PRIMARY KEY,
  subject_identity        TEXT NOT NULL,
  capability_name         TEXT NOT NULL,
  scope_hash              TEXT NOT NULL,
  issued_at               TEXT NOT NULL,
  expires_at              TEXT NOT NULL,
  issuer_identity         TEXT NOT NULL,
  token_mac_or_signature  TEXT NOT NULL,
  version_tuple_hash      TEXT NOT NULL,
  single_use_flag         INTEGER NOT NULL CHECK (single_use_flag IN (0,1)),
  consumed_at             TEXT,
  revoked_at              TEXT,
  revocation_reason       TEXT,
  bound_task_id           TEXT,
  bound_root_revision_id  TEXT
);

-- Single-use consume gate: INV-012 / AT-018.
-- A UNIQUE partial index on (capability_token_id) WHERE consumed_at IS NOT NULL
-- is redundant (PK is unique). But to prove exactly-one-consumption race
-- resolution we rely on: UPDATE ... SET consumed_at = ? WHERE consumed_at IS NULL
-- returning rowcount == 1 for the winner. See capability_service.py.

-- -------------------------------------------------------------------------
-- 4) Replay anchor (§23.12)
-- -------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS replay_anchors (
  replay_anchor_id             TEXT PRIMARY KEY,
  root_revision_id             TEXT NOT NULL,
  project_id                   TEXT NOT NULL,
  task_id                      TEXT NOT NULL,
  replay_class_claim           TEXT NOT NULL
    CHECK (replay_class_claim IN ('exact','diagnostic','semantic','degraded','unreplayable')),
  required_artifact_ids        TEXT NOT NULL,
  version_tuple_hash           TEXT NOT NULL,
  environment_fingerprint_hash TEXT NOT NULL,
  created_at                   TEXT NOT NULL,
  degradation_reason           TEXT,
  unreplayable_reason          TEXT
);

-- -------------------------------------------------------------------------
-- 5) Append-only evidence ledgers: audit, failure, drift, taint
-- -------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS audit_records (
  audit_record_id     TEXT PRIMARY KEY,
  task_id             TEXT,
  root_revision_id    TEXT,
  record_type         TEXT NOT NULL,
  causality_ref       TEXT,
  actor_identity      TEXT NOT NULL,
  artifact_refs       TEXT NOT NULL, -- JSON array
  version_tuple_hash  TEXT NOT NULL,
  taint_set_json      TEXT NOT NULL DEFAULT '[]',
  created_at          TEXT NOT NULL,
  payload_json        TEXT,
  failure_bundle_id   TEXT,
  replay_anchor_id    TEXT,
  approval_id         TEXT,
  sequence            INTEGER NOT NULL -- monotonic append order
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_audit_records_sequence
  ON audit_records (sequence);

-- INV-026 audit append-only enforcement.
CREATE TRIGGER IF NOT EXISTS audit_records_append_only_update
BEFORE UPDATE ON audit_records
BEGIN
  SELECT RAISE(ABORT, 'audit_records: append-only (INV-026/§23.14)');
END;

CREATE TRIGGER IF NOT EXISTS audit_records_append_only_delete
BEFORE DELETE ON audit_records
BEGIN
  SELECT RAISE(ABORT, 'audit_records: append-only (INV-026/§23.14)');
END;

CREATE TABLE IF NOT EXISTS failure_bundles (
  failure_bundle_id           TEXT PRIMARY KEY,
  task_id                     TEXT,
  root_revision_id            TEXT,
  failure_class               TEXT NOT NULL,
  cause_hash                  TEXT NOT NULL,
  evidence_refs               TEXT NOT NULL,
  taint_set_json              TEXT NOT NULL DEFAULT '[]',
  created_at                  TEXT NOT NULL,
  incident_id                 TEXT,
  retained_for_forensics_flag INTEGER,
  recovery_action_ref         TEXT
);

CREATE TRIGGER IF NOT EXISTS failure_bundles_append_only_update
BEFORE UPDATE ON failure_bundles
BEGIN
  SELECT RAISE(ABORT, 'failure_bundles: append-only (§23.15)');
END;

CREATE TRIGGER IF NOT EXISTS failure_bundles_append_only_delete
BEFORE DELETE ON failure_bundles
BEGIN
  SELECT RAISE(ABORT, 'failure_bundles: append-only (§23.15)');
END;

CREATE TABLE IF NOT EXISTS drift_event_records (
  drift_event_id          TEXT PRIMARY KEY,
  task_id                 TEXT,
  root_revision_id        TEXT,
  drift_class             TEXT NOT NULL,
  detected_at             TEXT NOT NULL,
  affected_artifact_ids   TEXT NOT NULL,
  consequence_class       TEXT NOT NULL,
  approval_id             TEXT,
  replay_anchor_id        TEXT,
  required_reconciliation_action TEXT
);

CREATE TRIGGER IF NOT EXISTS drift_event_records_append_only_update
BEFORE UPDATE ON drift_event_records
BEGIN
  SELECT RAISE(ABORT, 'drift_event_records: append-only (§23.19)');
END;

CREATE TRIGGER IF NOT EXISTS drift_event_records_append_only_delete
BEFORE DELETE ON drift_event_records
BEGIN
  SELECT RAISE(ABORT, 'drift_event_records: append-only (§23.19)');
END;

CREATE TABLE IF NOT EXISTS taint_records (
  taint_record_id    TEXT PRIMARY KEY,
  subject_id         TEXT NOT NULL,
  taint_class        TEXT NOT NULL,
  taint_state        TEXT NOT NULL,
  source_ref         TEXT NOT NULL,
  created_at         TEXT NOT NULL,
  cleared_at         TEXT,
  clearing_identity  TEXT,
  clearing_reason    TEXT
);

-- Taint records are append-only. Clearing creates a *new* record with a
-- new taint_record_id; silent in-place clearing is forbidden (INV-022).
CREATE TRIGGER IF NOT EXISTS taint_records_append_only_update
BEFORE UPDATE ON taint_records
BEGIN
  SELECT RAISE(ABORT, 'taint_records: append-only; clearing requires new record (INV-022/§23.17)');
END;

CREATE TRIGGER IF NOT EXISTS taint_records_append_only_delete
BEFORE DELETE ON taint_records
BEGIN
  SELECT RAISE(ABORT, 'taint_records: append-only (INV-022/§23.17)');
END;

-- -------------------------------------------------------------------------
-- 6) Budget ledger (schema continuity; phase-1 minimal generation)
-- -------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS budget_records (
  budget_record_id  TEXT PRIMARY KEY,
  task_id           TEXT NOT NULL,
  budget_class      TEXT NOT NULL,
  allocated_amount  INTEGER NOT NULL,
  consumed_amount   INTEGER NOT NULL,
  remaining_amount  INTEGER NOT NULL,
  budget_state      TEXT NOT NULL,
  created_at        TEXT NOT NULL,
  suspended_at     TEXT,
  replenished_at    TEXT,
  close_reason      TEXT
);

-- -------------------------------------------------------------------------
-- 7) Intent causal anchor (minimal durable record, foundation §6 / AUDIT-003)
-- -------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS intent_anchor_records (
  intent_id    TEXT PRIMARY KEY,
  task_id      TEXT NOT NULL,
  state        TEXT NOT NULL,
  created_at   TEXT NOT NULL
);

COMMIT;
