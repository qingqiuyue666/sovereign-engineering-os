# Write-Side Recovery Preconditions Governance Artifact
---
Status: draft for human review
Canonical target filename for later: `governance/preconditions/write_side_recovery_preconditions_v1.md`
Baseline tag: `read-only-governance-layer-v1`
Baseline commit: `4656e8f03404c6bb39e7976c6165e3d7dc0314fb`
Verdict: `WRITE_SIDE_PRECONDITIONS_ONLY`
Authorization status:
- Restore execution: not authorized
- Write-side recovery: not authorized
- CLI execution surface: not authorized
- Schema/migration: not authorized
- Daemon/server/queue: not authorized
---
## Scope Boundary
This document defines preconditions only.
This document does not authorize implementation.
This document is not a restore plan.
This document is not a CLI plan.
This document is not a schema/migration plan.
This document is not a daemon/server/queue plan.
This document is not an audit-log sink plan.
This document is not a dashboard/reporting sink plan.
## Terminology
Write-side recovery: any recovery behavior that mutates persistent state, durable artifacts, audit evidence, task lifecycle state, database rows, repository contents, or other authoritative system state.
Restore execution: any action that rehydrates, resumes, reconstructs, applies, or advances task state beyond read-only evaluation or dry-run reporting.
Persistence-mutating behavior: any insert, update, delete, schema mutation, migration, repair, audit append, evidence append, or durable state transition.
Read-only precondition checker: a non-mutating checker that consumes already-rendered readiness payloads and returns pass/fail without writing, restoring, migrating, calling CLI execution surfaces, mutating DB state, creating files, spawning background runtime, or calling upstream runtime from CI/contract handoff layers.
Human approval barrier: an explicit, attributable, scoped, current operator approval that must exist before any future mutating behavior is eligible for consideration.
Dry-run: a non-mutating evaluation that produces a deterministic projected outcome and evidence envelope without applying any write, restore, migration, repair, or runtime side effect.
Idempotency key: a stable operation identity that prevents duplicate execution, replay ambiguity, or accidental repeated mutation.
Immutable evidence snapshot: a non-mutating before/after evidence record that is stable, attributable, and not silently rewritten.
Fail-closed: refusal by default whenever required inputs are missing, malformed, ambiguous, unsafe, stale, or not ready.
Upstream runtime call: any call into model runtimes, external services, live execution engines, daemonized workers, queues, servers, or other runtime systems outside already-rendered contract payloads.
CI/contract handoff layer: a read-only boundary that validates rendered contract payloads for CI or governance readiness without reaching back into upstream runtime systems.
## 1. Purpose
This artifact defines mandatory gates before any future persistence-mutating recovery behavior is eligible for consideration.
It does not authorize restore execution, write-side recovery, CLI execution, schema or migration changes, audit-log sinks, dashboard/reporting sinks, daemon/server/queue workers, or production database mutation through a new recovery surface.
All listed preconditions are hard gates. Failure of any required gate requires refusal.
## 2. Baseline and Authority
- Frozen baseline tag: `read-only-governance-layer-v1`
- Tag target: `4656e8f03404c6bb39e7976c6165e3d7dc0314fb`
- Read-only governance layer status: frozen v1
- Write-side preconditions audit verdict: `WRITE_SIDE_PRECONDITIONS_ONLY`
- Restore execution: not authorized
- Write-side recovery: not authorized
- CLI execution surface: not authorized
- Schema/migration changes: not authorized
- Daemon/server/queue workers: not authorized
The frozen read-only governance layer is the authority baseline. Future work must not weaken, bypass, or reopen the frozen read-only layer as a path to mutation.
## 3. Current Write-Capable Surfaces
Existing write-capable or write-adjacent surfaces:
- SQLite repositories: insert, append, narrow update, and persistence adapters.
- Unit of Work: explicit transaction boundary with commit and rollback semantics.
- Migration runner / migration SQL: schema initialization and migration tracking.
- Append-only ledger: audit evidence append surface.
- Approval service: approval artifact issuance and approval barrier audit records.
- Review service: review artifact creation and review audit records.
- Revision seal service: revision, snapshot, journal, seal transition, and seal audit writes.
- Evidence service: replay anchor persistence and evidence closure audit.
- Recovery gate restore path: read-side evaluation with optional in-memory restore delegation.
- Recovery session host restore path: host-level restore delegation.
- Recovery CLI: current read-only evaluation and restore dry-run only.
- Recovery session host CLI: current read-only factory-check and evaluate only.
- Signable path orchestrator restore/admission paths: production admission writes and in-memory restore.
- Replay classifier: replay anchor payload source, not direct persistence.
## 4. Surface Classification
| Surface | Classification | Recovery Use Status |
|---|---|---|
| SQLite repositories | already production write path | requires all preconditions before recovery use |
| Unit of Work | already production write path | mandatory boundary for any future write eligibility |
| Migration runner / migration SQL | already production initialization path | forbidden for next-stage recovery path |
| Append-only ledger | already production write path | required evidence model; no new sink authorized |
| Approval service | already production write path | requires approval/review gates before recovery use |
| Review service | already production write path | requires approval/review gates before recovery use |
| Revision seal service | already production write path | not a restore executor; requires strict transaction gates |
| Evidence service | already production write path | requires evidence/replay gates before recovery use |
| Recovery gate restore path | future candidate write path | forbidden for next stage |
| Recovery session host restore path | future candidate write path | forbidden for next stage |
| Recovery CLI | read-only operator surface today | CLI expansion forbidden |
| Recovery session host CLI | read-only operator surface today | CLI expansion forbidden |
| Signable path orchestrator admission paths | already production write path | not a recovery runner |
| Signable path orchestrator restore path | future candidate write path | forbidden for next stage |
| Replay classifier | payload source, not direct persistence | requires preconditions before persistence use |
## 5. Required Preconditions
All preconditions below must pass before any future persistence-mutating recovery behavior is eligible for consideration.
1. Frozen baseline tag must resolve to `4656e8f03404c6bb39e7976c6165e3d7dc0314fb`.
2. HEAD/tag source truth must be verified before any source-dependent operation.
3. Working tree must be clean when source truth matters.
4. Global governance readiness aggregate must be ready.
5. Target task lifecycle snapshot contract must be ready.
6. Evidence/replay readiness must be ready.
7. Approval/review readiness must be ready.
8. Explicit human approval barrier must exist.
9. Dry-run mode must exist and pass before any mutating mode is eligible.
10. Idempotency key / replay protection must exist.
11. Immutable before/after evidence snapshots must be available.
12. Explicit transaction boundary must be defined.
13. Deterministic rollback/failure semantics must be defined.
14. Silent schema migration must be impossible.
15. Implicit DB repair must be impossible.
16. CLI execution must require explicit confirmation.
17. Restore must not proceed unless governance aggregate is ready.
18. Write behavior must refuse if read-only governance aggregate is not ready.
19. Write behavior must refuse if target DB, schema, tag, or readiness cannot be resolved.
20. Daemon/server/queue behavior must be absent.
21. Upstream runtime calls must be absent inside CI/contract handoff layers.
## 6. Absolute Prohibitions
1. No restore execution as the next immediate step.
2. No write-side recovery as the next immediate step.
3. No daemon/server/queue write worker.
4. No automatic schema migration in a recovery path.
5. No auto-repair DB on read.
6. No hidden CLI command.
7. No write without audit/evidence envelope.
8. No write without deterministic rollback semantics.
9. No write without explicit operator approval.
10. No production DB writes through a new recovery surface until all preconditions are executable and passing.
## 7. Required Gate Model
| Gate | Purpose | Required Inputs | Pass Condition | Fail-Closed Condition |
|---|---|---|---|---|
| Source Truth Gate | Anchor the operation to the frozen baseline. | Frozen tag, tag target, HEAD, repository status. | Tag and source truth resolve exactly and required cleanliness holds. | Refuse if tag, HEAD, or working tree state is unresolved or mismatched. |
| Read-Only Governance Gate | Preserve frozen governance readiness. | Rendered governance aggregate payload. | Aggregate is ready, JSON-safe, and free of restore/durable/CLI hazards. | Refuse if aggregate is missing, malformed, not ready, or unsafe. |
| Target Task Gate | Prove target lifecycle state is contract-ready. | Rendered task lifecycle snapshot contract/readiness payload. | Target snapshot contract is ready and bounded. | Refuse on malformed, missing, duplicate, mixed, or not-ready lifecycle evidence. |
| Evidence/Replay Gate | Prove evidence/replay readiness before mutation eligibility. | Rendered evidence/replay readiness payload. | Evidence/replay readiness is ready and operator-safe. | Refuse if replay readiness is missing, degraded beyond policy, malformed, or unsafe. |
| Approval/Review Gate | Prove approval/review barriers are satisfied. | Rendered approval/review readiness payload. | Approval/review readiness is ready and barrier-safe. | Refuse if approval, review, revision, seal, or barrier evidence is missing or not ready. |
| Human Approval Gate | Require explicit operator authorization. | Operator identity, approval record, target, scope, reason. | Approval is explicit, current, scoped, and attributable. | Refuse if approval is absent, implicit, stale, ambiguous, or unauthenticated. |
| Dry-Run Gate | Require non-mutating preview before mutation eligibility. | Dry-run result, target, projected actions, projected evidence envelope. | Dry-run succeeds and matches the requested target/scope. | Refuse if dry-run is absent, failed, stale, partial, or mismatched. |
| Idempotency Gate | Prevent duplicate or replayed mutation. | Idempotency key, target identity, prior attempt evidence. | Key is unique for the target/action or safely resumes the same attempt. | Refuse on missing key, collision, ambiguity, or replay risk. |
| Evidence Snapshot Gate | Preserve immutable before/after evidence. | Before snapshot, projected after snapshot, evidence envelope identity. | Before snapshot exists and after snapshot model is deterministic. | Refuse if snapshots are absent, mutable, incomplete, or non-deterministic. |
| Transaction Gate | Bound all writes atomically. | Transaction boundary, affected repositories, expected rejection classes. | All writes are inside an explicit transaction boundary. | Refuse if writes would autocommit independently or span unclear boundaries. |
| Rollback Gate | Require deterministic failure handling. | Failure classes, rollback behavior, committed rejection evidence policy. | Unexpected failures roll back; expected rejections are explicitly handled. | Refuse if partial effects, silent continuation, or ambiguous rollback is possible. |
| Schema/Migration Gate | Prevent recovery-time schema mutation. | Schema identity, migration state, migration policy. | Schema is already valid; no migration or repair is needed. | Refuse if schema is missing, stale, mutated, or requires migration/repair. |
| CLI/Operator Confirmation Gate | Prevent hidden or accidental execution. | Operator command surface, confirmation state, command manifest. | Any operator action is explicit and confirmed. | Refuse if hidden, implicit, unconfirmed, or expanded CLI behavior is present. |
| Runtime Boundary Gate | Prevent background or upstream runtime creep. | Runtime boundary declaration, dependency list, call graph evidence. | No daemon/server/queue behavior and no upstream runtime calls in handoff layers. | Refuse if background execution, queues, servers, or runtime calls are required. |
## 8. Required Refusal Conditions
Refuse if any of the following occurs:
1. `read-only-governance-layer-v1` cannot be resolved.
2. The tag target differs from `4656e8f03404c6bb39e7976c6165e3d7dc0314fb`.
3. Source truth depends on the working tree and the working tree is dirty.
4. Governance aggregate is missing, malformed, or not ready.
5. Target task lifecycle snapshot contract fails.
6. Evidence/replay readiness fails.
7. Approval/review readiness fails.
8. Human approval is absent or ambiguous.
9. Dry-run result is absent, failed, stale, or mismatched.
10. Idempotency key is missing or reused ambiguously.
11. Before/after evidence snapshot cannot be produced immutably.
12. Transaction boundary is unclear.
13. Rollback behavior is non-deterministic.
14. Schema validation requires migration or repair.
15. CLI execution is implicit or unconfirmed.
16. Any daemon/server/queue behavior is required.
17. Any upstream runtime call is required inside CI/contract handoff layers.
18. Any write would occur without an audit/evidence envelope.
## 9. Non-Goals
This document does not implement or authorize:
- restore
- write-side recovery
- CLI command
- daemon/server/queue
- schema/migration
- audit-log sink
- dashboard/reporting sink
- DB mutation
## 10. Next Allowed Engineering Step
The next allowed step is limited to one of:
- keep this as a human governance artifact only
- after human review and adoption, allow only a purely read-only precondition checker that consumes already-rendered readiness payloads and returns pass/fail
Any checker must not write, restore, migrate, call CLI execution surfaces, mutate DB state, create files, spawn background runtime, or call upstream runtime from CI/contract handoff layers.
## 11. Explicitly Forbidden Next Engineering Steps
The following are forbidden as next steps:
- Restore CLI
- Restore executor
- write-side recovery runner
- audit-log sink
- dashboard/reporting sink
- daemon/server/queue worker
- schema migration
- DB repair
- hidden command surface
## 12. Adoption Rule
This artifact may only become repository-governed after human review.
If committed later, it must be committed as documentation only.
Any PR adopting it must not include production code, tests, schema, migration, CLI, restore, daemon/server/queue, or DB mutation changes.
Adoption does not authorize implementation.
## 13. Next-Step Constraint
The only possible next engineering implementation after adoption is a read-only precondition checker.
That checker must consume already-rendered readiness payloads.
That checker must not write, restore, migrate, call CLI, mutate DB, create files, spawn background runtime, or call upstream runtime from CI/contract handoff layers.
## 14. Final Decision
Verdict: `WRITE_SIDE_PRECONDITIONS_ONLY`
Restore is not authorized.
Write-side recovery is not authorized.
The only safe next implementation, if any, is a read-only precondition checker after this document is reviewed and adopted.
