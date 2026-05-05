Execution Authorization Spec-Only Design v1

Status: draft for human review

Canonical target filename: governance/specs/execution_authorization_spec_only_design_v1.md

Verdict: SPEC_ONLY_COMPLETE

Tag candidate: execution-authorization-spec-only-v1

1. Scope

This document is spec-only.

This document is non-executable.

This document adds no code.

This document adds no CLI.

This document opens no DB and defines no DB write path.

This document makes no service calls.

This document appends no evidence.

This document appends no audit record.

This document performs no restore.

This document performs no write-side recovery.

This spec defines the `ExecutionAuthorizationV1` object and the write-side execution authorization contract only.

Readiness, authorization, and execution are separate states. This document defines an authorization input shape for future validation; it does not produce readiness and does not execute anything.

2. Governing Baseline

The governing baseline is fixed by the following frozen dependency tags:

* preflight-read-only-stack-v1
    * target: 662b6161253c35204b437e88809c5bab21908c6d
* preflight-aggregate-summary-v1
    * target: 662b6161253c35204b437e88809c5bab21908c6d
* h2-execution-preflight-ci-v1
    * target: 2574c9fc92cadbab8c357a9d78561c3b12b27786
* h2-execution-preflight-v1
    * target: 01a8a0bbe11ba62b2eb55b4a21f0420bfea6274a
* human-approval-readiness-ci-v1
    * target: e1af80affb00a0bebd70e4933769d48d4444c380
* human-approval-readiness-v1
    * target: 7735241ce1effbe18d3835c6a0e185b88cc5ff17
* restore-dry-run-read-only-stack-v1
    * target: e7c78e3ff0c5dc05806c293f01ab32cd33c9518b
* write-side-recovery-spec-only-v1
    * target: ad560cc2dab135f2c1d56d948410ae47586d118e
* write-side-precondition-ci-v1
    * target: 05c81541ad3d7deee20023843142f702937f6c3f
* write-side-precondition-checker-v1
    * target: fd5788c7a4d3ed953fbc0295414ba7e6ad4f89f6
* read-only-governance-layer-v1
    * target: 4656e8f03404c6bb39e7976c6165e3d7dc0314fb

These checkpoints provide source evidence only. They do not grant write authority.

3. Readiness Is Not Authorization

Read-only readiness is evidence, not authority.

H1, H1-CI, H2, H2-CI, and H3 outputs cannot trigger restore.

`aggregate_ok=True` is not permission.

`preflight_ok=True` is not permission.

`ci_ok=True` is not permission.

`human_approval_ready=True` is not permission.

No read-only verdict can trigger restore.

Only a future validated `ExecutionAuthorizationV1` may become an executor precondition.

Even a valid authorization object still does not execute anything by itself.

Readiness may support a future authorization decision, but readiness is never authorization. Authorization may support a future executor precondition, but authorization is never execution.

4. ExecutionAuthorizationV1 Object

`ExecutionAuthorizationV1` is a required-field authorization object for a future read-only validator. It must be JSON-safe, durable, explicit, bounded, and separately validated before any future executor may treat it as input.

Required fields:

* `surface`
    * Must identify the object surface as `ExecutionAuthorizationV1`.
* `version`
    * Must identify the object version as `1`.
* `source_preflight_stack_tag`
    * Must identify the frozen read-only source stack tag.
* `source_preflight_stack_commit`
    * Must identify the frozen read-only source stack commit.
* `source_preflight_aggregate_ref`
    * Must identify the already-rendered H3 aggregate output.
* `approved_task_id`
    * Must identify the task that the authorization covers.
* `approved_operation_kind`
    * Must identify the operation kind that the authorization covers.
* `idempotency_key`
    * Must bind the authorized attempt and replay boundary.
* `projected_action`
    * Must identify the exact projected action from the H3 aggregate.
* `projected_evidence_ref`
    * Must identify the exact projected evidence reference from the H3 aggregate.
* `human_approval_ref`
    * Must identify the human approval readiness reference bound by H3.
* `operator_confirmation_ref`
    * Must identify the operator confirmation reference bound by H3.
* `actor_policy`
    * Must declare the actor matching and dual-control policy.
* `approval_actor_identity`
    * Must identify the human approval actor.
* `confirmation_actor_identity`
    * Must identify the operator confirmation actor.
* `authorization_issuer`
    * Must identify the actor or governance surface issuing the authorization object.
* `authorization_reason`
    * Must state the bounded reason for the authorization.
* `authorization_created_at`
    * Must state when the authorization object was created.
* `authorization_expires_at`
    * Must state when the authorization object expires.
* `freshness_seconds`
    * Must state the maximum allowed age for freshness-sensitive sources.
* `transaction_boundary_declared`
    * Must be true only when the future write transaction boundary is declared.
* `rollback_boundary_declared`
    * Must be true only when the future rollback boundary is declared.
* `idempotency_boundary_declared`
    * Must be true only when the replay and idempotency boundary is declared.
* `before_evidence_ref`
    * Must identify evidence that exists before any future mutation.
* `after_evidence_required`
    * Must declare that after evidence is required after any future mutation.
* `audit_append_required`
    * Must declare that audit append is required by any future governed write contract.
* `evidence_append_required`
    * Must declare that evidence append is required by any future governed write contract.
* `schema_migration_authorized`
    * Must declare whether schema migration is authorized.
* `daemon_server_queue_authorized`
    * Must declare whether daemon, server, or queue execution is authorized.
* `db_repair_authorized`
    * Must declare whether DB repair is authorized.
* `cli_execution_authorized`
    * Must declare whether CLI execution is authorized.
* `restore_authorized`
    * Must declare whether restore execution is authorized.
* `write_side_recovery_authorized`
    * Must declare whether write-side recovery is authorized.
* `irreversible_action_prohibited`
    * Must declare that irreversible action is prohibited.
* `fail_closed_declared`
    * Must declare fail-closed behavior.
* `json_safe`
    * Must declare that the authorization object is JSON-safe.

Missing fields, empty fields, malformed fields, non-JSON-safe values, ambiguous values, or implementation-specific side effects fail closed.

5. Required Bindings

A future validator must enforce the following exact bindings:

* `source_preflight_stack_tag` must equal `preflight-read-only-stack-v1`.
* `source_preflight_stack_commit` must equal `662b6161253c35204b437e88809c5bab21908c6d`.
* `source_preflight_aggregate_ref` must bind to the already-rendered H3 aggregate output.
* `approved_task_id` must equal the H3 `target_task_id`.
* `approved_operation_kind` must equal the H3 `operation_kind`.
* `idempotency_key` must equal the H3 `idempotency_key`.
* `projected_action` must equal the H3 `projected_action`.
* `projected_evidence_ref` must equal the H3 `projected_evidence_ref`.
* `human_approval_ref` must equal the H3 `human_approval_ref`.
* `operator_confirmation_ref` must equal the H3 `confirmation_ref`.
* Actor identities must satisfy `actor_policy`.
* `before_evidence_ref` must exist before mutation.
* After evidence must be produced after mutation in any future executor.

Binding mismatch fails closed. Derived, inferred, partial, or best-effort bindings are invalid.

6. Required Default-Deny Flags

Default deny is mandatory.

`schema_migration_authorized` defaults false.

`daemon_server_queue_authorized` defaults false.

`db_repair_authorized` defaults false.

`cli_execution_authorized` defaults false.

`restore_authorized` defaults false until explicitly authorized by a separate future package.

`write_side_recovery_authorized` defaults false until explicitly authorized by a separate future package.

`irreversible_action_prohibited` must be true.

`fail_closed_declared` must be true.

Any missing default-deny flag fails closed. Any unauthorized true flag fails closed unless a separate frozen spec explicitly permits that flag to be true.

7. Authorization Semantics

The authorization object is not an executor.

The authorization object is not CLI.

The authorization object is not a DB write.

The authorization object is not a service call.

The authorization object is not an evidence append.

The authorization object is a bounded signed or declared input for a future validator.

A future validator may only produce authorization readiness for an executor precondition.

A future executor still needs separate approval to exist.

Authorization must be explicit, durable, bounded, and separately validated. The default outcome is deny, and every ambiguous or incomplete condition must fail closed.

Approval barrier semantics remain intact: a readiness result or authorization object cannot bypass the human approval and operator confirmation boundaries that it claims to bind.

Kernel authority remains the only allowed future write authority. A future executor must be kernel-owned and must not delegate mutation authority to service, repository, CLI, daemon, server, queue, or external orchestration surfaces.

The local-first boundary remains intact. Local rendered evidence and local governance inputs are the only allowed source material for future validation unless a separate frozen package explicitly authorizes another boundary.

Capability boundaries remain intact. A surface that can read, render, summarize, validate, or report cannot acquire write capability by implication.

8. Freshness and Expiry

`authorization_created_at` must be parseable.

`authorization_expires_at` must be parseable.

`authorization_expires_at` must be after `authorization_created_at`.

`freshness_seconds` must be a positive integer.

Stale authorization fails closed.

Stale preflight source fails closed.

Stale human approval fails closed.

Stale operator confirmation fails closed.

Wall-clock evaluation belongs to a future validator, not this spec.

This spec does not read wall-clock time and does not evaluate freshness.

9. Actor and Approval Model

The approval actor is the identity represented by `approval_actor_identity` and bound by `human_approval_ref`.

The confirmation actor is the identity represented by `confirmation_actor_identity` and bound by `operator_confirmation_ref`.

The authorization issuer is the identity or governance surface represented by `authorization_issuer`.

`actor_policy` must declare `same_actor_required` and `dual_control_allowed`.

When `same_actor_required` is true, the approval actor and confirmation actor must match.

When `dual_control_allowed` is true, the approval actor and confirmation actor may differ only if the rendered approval and confirmation references support that separation.

Actor mismatch fails closed.

Dual-control does not imply organization authority.

The authorization issuer cannot override missing approval.

The authorization issuer cannot override stale preflight.

The authorization issuer cannot override failed boundary declarations.

The authorization issuer cannot convert readiness into execution authority.

10. Evidence and Audit Model

Before evidence is required before mutation.

After evidence is required after mutation.

Audit append is required by any future governed write contract.

Evidence append is required by any future governed write contract.

Append must be inside a future governed write contract.

No evidence append occurs in this spec.

No audit append occurs in this spec.

Mutation without before and after evidence is forbidden.

Replay honesty must be preserved. A replayed authorization must reconstruct the same evidence boundary, projected action, idempotency key, approval reference, confirmation reference, and source stack commit.

The evidence spine must remain complete from read-only source evidence, through H3 aggregate evidence, through authorization validation, and through any later before and after mutation evidence. This spec only defines the authorization segment of that spine.

11. Transaction and Rollback Model

A future executor must use one outer kernel-owned transaction.

Expected governance rejection may produce rejection evidence only if explicitly allowed by a future contract.

Unexpected failure rolls back mutation.

Rollback failure is fatal and must fail closed.

No transaction is opened in this spec.

This spec does not define repository writes, Unit of Work writes, DB writes, or service writes.

12. Idempotency and Replay Model

The idempotency key binds:

* task
* operation
* projected action
* projected evidence
* approval ref
* confirmation ref
* source stack commit

Repeated use of the same authorization must be detected.

Conflicting reuse must fail closed.

Replay must reconstruct the same authorization boundary.

A future executor must not mutate on ambiguous replay.

Replay honesty requires the replayed object to preserve the same `approved_task_id`, `approved_operation_kind`, `idempotency_key`, `projected_action`, `projected_evidence_ref`, `human_approval_ref`, `operator_confirmation_ref`, and `source_preflight_stack_commit`.

13. Schema, CLI, Daemon, DB Repair Model

Schema migration is not authorized.

CLI execution is not authorized.

Daemon, server, or queue execution is not authorized.

DB repair is not authorized.

Any need for schema migration, CLI execution, daemon execution, server execution, queue execution, or DB repair fails closed and requires a separate future package.

14. Future Validator Contract

A future read-only validator may perform only this sequence:

1. Validate `ExecutionAuthorizationV1`.
2. Consume the already-rendered preflight aggregate summary.
3. Check bindings.
4. Check freshness.
5. Check flags.
6. Output authorization readiness.
7. Still not execute.

The validator must be read-only. It must not call approval, review, revision seal, evidence, audit, restore, DB, repository, Unit of Work, CLI, daemon, server, or queue surfaces.

15. Future CI Consumer Contract

A future CI consumer may consume rendered authorization validator output.

The CI consumer must make no validator calls.

The CI consumer must make no service calls.

The CI consumer must open no DB.

The CI consumer must invoke no executor.

The CI consumer still does not execute.

CI success is readiness evidence only. Future `ci_ok=True` remains non-authorizing unless separately bound by a future authorization contract.

16. Future Executor Preconditions

A future executor cannot exist until all of the following are frozen and separately authorized:

* execution authorization spec
* authorization validator
* authorization CI
* executor precondition contract
* write path
* evidence append path
* transaction and rollback path
* idempotency and replay path

The future executor must still treat authorization readiness as a precondition, not as execution by itself.

17. Forbidden Until Separately Authorized

The following remain forbidden until separately authorized:

* restore executor
* restore CLI
* DB writes
* repository writes
* Unit of Work writes
* approval artifact creation
* review artifact creation
* evidence append
* audit append
* schema/migration
* daemon/server/queue
* DB repair
* irreversible actions

18. Failure Policy

Missing field fails closed.

Malformed field fails closed.

Stale authorization fails closed.

Mismatch fails closed.

False required boundary fails closed.

Unauthorized true flag fails closed unless explicitly allowed by a frozen spec.

Ambiguous replay fails closed.

Unknown operation kind fails closed.

Schema requirement fails closed.

Daemon, CLI, or DB repair requirement fails closed.

Any attempt to treat read-only readiness as authorization fails closed.

Any attempt to treat authorization readiness as execution fails closed.

19. Non-Goals

This spec does not implement anything.

This spec does not define a validator.

This spec does not define CI.

This spec does not define an executor.

This spec does not define CLI.

This spec does not write to DB.

This spec does not call services.

This spec does not append evidence.

This spec does not append audit records.

This spec does not define schema or migration.

This spec does not authorize restore.

This spec does not authorize write-side recovery.

20. Freeze Criteria

Freeze requires:

* one spec document only
* no production code changes
* no service changes
* no schema changes
* no CLI changes
* no DB changes
* tests remain green
* working tree clean
* tag candidate: execution-authorization-spec-only-v1

The freeze candidate must not claim restore is authorized, write-side recovery is authorized, CLI is authorized, DB writes are authorized, schema migration is authorized, daemon/server/queue execution is authorized, DB repair is authorized, or irreversible action is authorized.
