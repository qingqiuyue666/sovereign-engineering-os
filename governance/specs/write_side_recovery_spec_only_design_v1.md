Write-Side Recovery Spec-Only Design

⸻

Status: draft for human review

Canonical target filename: governance/specs/write_side_recovery_spec_only_design_v1.md

Verdict: SPEC_ONLY_COMPLETE

Frozen checkpoints:

* read-only-governance-layer-v1
    * target: 4656e8f03404c6bb39e7976c6165e3d7dc0314fb
* write-side-precondition-checker-v1
    * target: fd5788c7a4d3ed953fbc0295414ba7e6ad4f89f6
* write-side-precondition-ci-v1
    * target: 05c81541ad3d7deee20023843142f702937f6c3f

Authorization status:

* Restore execution: not authorized
* Write-side recovery: not authorized
* CLI expansion: not authorized
* Schema/migration changes: not authorized
* Daemon/server/queue: not authorized
* DB repair: not authorized

⸻

Scope Boundary

This document is a non-executable design artifact.

This document does not authorize implementation.

This document does not authorize restore execution.

This document does not authorize write-side recovery.

This document does not authorize CLI expansion.

This document does not authorize schema/migration.

This document does not authorize daemon/server/queue behavior.

This document does not authorize DB repair.

This document does not authorize production DB mutation.

1. Baseline Authority

The authority chain is fixed by three frozen checkpoints.

read-only-governance-layer-v1 is the read-only governance authority baseline and must not be weakened or reopened as a mutation path.

write-side-precondition-checker-v1 is the read-only checker checkpoint. It consumes already-rendered payloads and emits readiness plus authorization flags that remain false.

write-side-precondition-ci-v1 is the downstream CI checkpoint. It consumes the rendered checker output only and confirms the checker result without invoking upstream builders, checkers, aggregators, DB, CLI, restore, migration, daemon, server, or queue surfaces.

2. Non-Authorization Statement

This spec does not authorize restore execution.

This spec does not authorize write-side recovery implementation.

This spec does not authorize CLI expansion.

This spec does not authorize schema/migration.

This spec does not authorize daemon/server/queue.

This spec does not authorize DB repair.

3. Future Recovery Model

A future controlled write-side recovery model would have to proceed in this order:

1. Read-only source truth verification.
2. Read-only governance aggregate verification.
3. Read-only precondition checker verification.
4. Read-only precondition CI verification.
5. Restore dry-run readiness.
6. Dry-run plan rendering.
7. Human approval barrier.
8. Transaction planning.
9. Rollback model.
10. Before/after evidence model.
11. Controlled write-side candidate for separate authorization review.

Each stage must consume rendered, JSON-safe payloads where possible, fail closed on malformed or unsafe input, and preserve authorization flags as false until a later explicit authorization decision outside this spec.

4. Allowed Future Write Path

The only theoretically allowed future write path must satisfy all of the following:

1. Start from rendered governance and precondition payloads.
2. Pass every gate.
3. Include explicit human approval.
4. Include a successful deterministic dry-run.
5. Carry an idempotency key.
6. Define immutable before/after evidence references.
7. Declare a transaction boundary.
8. Define deterministic rollback.
9. Avoid schema migration.
10. Avoid DB repair.
11. Avoid hidden CLI execution.
12. Avoid daemon/server/queue execution.
13. Avoid bypassing the checker or CI consumer.
14. Avoid bypassing human approval.

This section does not authorize the path. It only defines the minimum theoretical gate stack.

5. Forbidden Write Paths

The following paths are forbidden:

1. Direct restore from RecoverySessionHost.
2. Direct restore from recovery gate.
3. Direct restore CLI.
4. Direct DB repository mutation.
5. Direct KernelUnitOfWork mutation outside the governed path.
6. Implicit schema migration.
7. DB repair.
8. Audit/evidence append without an envelope.
9. Background worker restore.
10. Runtime/orchestrator hidden restore.
11. Bypassing precondition checker or CI.
12. Bypassing human approval.

6. Dry-Run Model

The dry-run payload must include:

* dry_run_present
* dry_run_ok
* target_task_id
* projected_action
* projected_evidence_ref

Future documents may define:

* projected_before_snapshot_ref
* projected_after_snapshot_ref
* projected_repository_effects
* projected_transaction_boundary
* determinism_hash

Required fields must be non-empty and JSON-safe where applicable.

Refuse if the dry-run is absent, malformed, failed, target-mismatched, stale, nondeterministic, or missing projected evidence.

Dry-run must not:

* mutate state
* create files
* open write transactions
* append evidence
* call restore
* call hidden runtime surfaces

Dry-run may only render deterministic projected action and projected evidence references.

7. Idempotency Model

Idempotency fields:

* idempotency_key
* target_task_id
* operation_kind
* replay_status

The key must bind to exactly one target task and one operation kind.

Allowed replay statuses:

* new
* same_attempt_safe

Refuse on:

* missing key
* empty key
* target mismatch
* operation mismatch
* collision
* ambiguous prior attempt
* unsafe replay
* stale attempt
* any status outside the allowed set

8. Evidence Model

The evidence model requires:

* before snapshot
* projected after snapshot
* immutable evidence references
* audit/evidence envelope describing the projected operation

Refuse if snapshots are:

* missing
* mutable
* incomplete
* target-mismatched
* nondeterministic
* not JSON-safe

No evidence append is authorized by this spec. Any future append requires separate write-path authorization and must occur only inside the governed transaction model.

9. Transaction and Rollback Model

Any future write must be bounded by an explicit transaction.

The existing transaction semantics provide the conceptual minimum:

* success commits
* expected governance rejection may preserve rejection evidence by declared policy
* unexpected failure rolls back

A future design must define:

* affected repositories
* expected rejection policy
* rollback behavior
* no-partial-commit guarantees

Silent continuation after failed mutation is forbidden.

10. Human Approval Model

Human approval must include:

* actor identity
* scope
* reason
* created_at
* target task
* freshness policy

Approval must be:

* explicit
* attributable
* current
* scoped to the proposed operation
* bound to the dry-run plan

Refuse if approval is:

* absent
* ambiguous
* stale
* unauthenticated
* unscoped
* target-mismatched
* not tied to the rendered plan and idempotency key

11. Schema and Runtime Boundary

No schema migration.

No DB repair.

No daemon/server/queue.

No hidden CLI.

No upstream runtime calls in handoff layers.

The schema posture is read-only verification only. A future path may inspect schema identity and migration state, but must refuse if migration or repair would be required.

12. Refusal Taxonomy

Source Truth Gate

* source_truth_invalid
* baseline_tag_unresolved
* baseline_commit_mismatch
* working_tree_dirty

Governance Gate

* governance_invalid
* governance_not_ready
* restore hazard
* durable hazard
* CLI hazard
* runtime hazard
* JSON-safety hazard

Target Task Gate

* target_task_invalid
* target_task_not_ready
* duplicate lifecycle evidence
* malformed lifecycle evidence
* missing lifecycle evidence

Evidence/Replay Gate

* evidence_replay_invalid
* evidence_replay_not_ready

Approval/Review Gate

* approval_review_invalid
* approval_review_not_ready

Human Approval Gate

* human_approval_invalid
* human_approval_missing
* stale approval
* ambiguous approval
* unscoped approval

Dry-Run Gate

* dry_run_invalid
* dry_run_missing
* dry_run_failed
* dry_run_target_mismatch

Idempotency Gate

* idempotency_invalid
* idempotency_missing
* idempotency_replay_risk

Evidence Snapshot Gate

* evidence_snapshot_invalid
* evidence_snapshot_missing

Transaction/Rollback Gate

* transaction_invalid
* transaction_missing
* rollback_missing

Schema/Runtime Gate

* schema_runtime_invalid
* schema_migration_required
* db_repair_required
* runtime_boundary_violation

Operator Boundary Gate

* operator_confirmation_invalid
* cli_confirmation_missing

CI Gate

* invalid_ci_payload
* readiness_flag_not_ready
* authorization_flag_true
* checker_not_ready

13. Candidate Future Implementation Stages

These stages are candidate sequencing only and do not authorize implementation.

Stage R0: Spec Adoption

* docs-only
* no code
* no tests
* no restore
* no write-side execution

Stage R1: Restore Dry-Run Readiness Surface

* read-only only
* no mutation
* no file creation
* no write transaction

Stage R2: Restore Dry-Run Plan Renderer

* rendered payload only
* deterministic output
* no file creation
* no DB mutation

Stage R3: Dry-Run CI Consumer

* downstream-only
* no upstream calls
* no restore
* no write-side execution

Stage R4: Write-Side Execution Design Review

* design-only
* no implementation authority

Stage R5: Controlled Restore Implementation

* only after separate authorization
* not authorized by this spec

14. Adoption Rule

This artifact may only become repository-governed after human review.

If committed later, it must be committed as documentation only.

Any PR adopting it must not include production code, tests, schema, migration, CLI, restore, daemon/server/queue, DB repair, or DB mutation changes.

Adoption does not authorize implementation.

15. Next-Step Constraint

The only allowed next step after this spec is documentation-only consolidation or continued human review.

Implementation remains unauthorized.

Restore remains unauthorized.

Write-side recovery remains unauthorized.

CLI expansion remains unauthorized.

Schema/migration remains unauthorized.

Daemon/server/queue remains unauthorized.

DB repair remains unauthorized.

16. Final Decision

Verdict: SPEC_ONLY_COMPLETE

Keep this as spec-only, or at most adopt it as a docs-only governance spec artifact.

Do not implement restore, CLI expansion, schema/migration, daemon/server/queue, DB repair, or write-side recovery from this design.
