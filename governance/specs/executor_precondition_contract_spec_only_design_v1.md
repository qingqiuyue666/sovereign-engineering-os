Executor Precondition Contract Spec-Only Design v1

Status: draft for human review

Canonical target filename: governance/specs/executor_precondition_contract_spec_only_design_v1.md

Verdict: SPEC_ONLY_COMPLETE

Tag candidate: executor-precondition-contract-spec-only-v1

1. Scope

This document is spec-only.

This document is non-executable.

This document adds no code.

This document adds no validator.

This document adds no CI consumer.

This document adds no executor.

This document adds no restore.

This document adds no CLI.

This document opens no DB and defines no DB write path.

This document defines no repository or Unit of Work behavior.

This document makes no service calls.

This document appends no evidence.

This document appends no audit record.

This document defines no schema or migration.

This spec defines the pre-executor contract only.

The pre-executor contract is a declaration surface for future read-only validation. It is not a command, not a write path, and not an execution grant.

2. Governing Baseline

The governing baseline is fixed by the following frozen dependency tags:

* execution-authorization-read-only-stack-v1
    * target: d586aeb60620010c900df7be1a88621ab2cb8dc1
* execution-authorization-validator-ci-v1
    * target: d586aeb60620010c900df7be1a88621ab2cb8dc1
* execution-authorization-validator-v1
    * target: 1fa687c22e6816b7a55cd9072124ba89ebddc2d1
* execution-authorization-spec-only-v1
    * target: 6e86a29dc8ccdadc672a13c93a4eaf3cfd7aff8c
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

These checkpoints provide source evidence and governance boundaries only. They do not grant executor authority, restore authority, write-side recovery authority, DB write authority, CLI authority, service authority, evidence append authority, or audit append authority.

3. Readiness, Authorization, Precondition, Execution

Preflight readiness is not authorization.

Execution authorization readiness is not execution.

Executor precondition readiness is not execution.

No read-only verdict may dispatch an executor.

No validator or CI verdict may call restore.

No precondition contract may open DB.

No precondition contract may append evidence.

Only a future separately authorized executor may mutate state.

Even a valid `ExecutorPreconditionV1` does not execute anything by itself.

Readiness may support later authorization analysis, but readiness is never authorization.

Authorization readiness may support later executor precondition analysis, but authorization readiness is never execution.

Precondition readiness may support later executor eligibility analysis, but precondition readiness is never execution.

Default deny is mandatory.

Fail closed is mandatory.

Replay honesty is mandatory: replay must preserve the same source stack commits, task, operation, idempotency key, projected action, projected evidence reference, approval reference, confirmation reference, executor intent, and required declarations.

The evidence spine must remain intact from read-only governance evidence, through preflight evidence, through execution authorization validation evidence, through precondition validation evidence, and through any separately authorized future before and after mutation evidence.

Approval barrier semantics remain intact. No readiness result, authorization object, precondition object, validator verdict, or CI verdict may bypass human approval or operator confirmation boundaries.

Kernel authority remains the only allowable future write authority. No service, repository, Unit of Work, CLI, daemon, server, queue, or external orchestration surface receives mutation authority from this contract.

The local-first boundary remains intact. Future validation may consume local rendered governance artifacts and explicit local declaration inputs only unless a separately frozen package authorizes another boundary.

Capability boundaries remain intact. A surface that can read, render, summarize, validate, or report cannot acquire write capability by implication.

The executor remains unauthorized.

Restore remains unauthorized.

DB writes remain unauthorized.

Evidence append remains unauthorized.

Audit append remains unauthorized.

4. ExecutorPreconditionV1 Object

`ExecutorPreconditionV1` is a required-field pre-executor declaration object for a future read-only validator. It must be JSON-safe, explicit, durable, bounded, replay-honest, fail-closed, and non-executable.

Required fields:

* `surface`
    * Must identify the object surface as `ExecutorPreconditionV1`.
* `version`
    * Must identify the object version as `1`.
* `source_execution_authorization_read_only_stack_tag`
    * Must identify the frozen execution authorization read-only stack tag.
* `source_execution_authorization_read_only_stack_commit`
    * Must identify the frozen execution authorization read-only stack commit.
* `source_execution_authorization_validator_ci_ref`
    * Must identify the already-rendered execution authorization validator CI output.
* `source_preflight_read_only_stack_tag`
    * Must identify the frozen preflight read-only stack tag.
* `source_preflight_read_only_stack_commit`
    * Must identify the frozen preflight read-only stack commit.
* `approved_task_id`
    * Must identify the exact approved task bound by the execution authorization CI output.
* `approved_operation_kind`
    * Must identify the exact approved operation kind bound by the execution authorization CI output.
* `idempotency_key`
    * Must bind the declared future attempt and replay boundary.
* `projected_action`
    * Must identify the exact projected action bound by the execution authorization CI output.
* `projected_evidence_ref`
    * Must identify the exact projected evidence reference bound by the execution authorization CI output.
* `human_approval_ref`
    * Must identify the human approval readiness reference bound by the execution authorization CI output.
* `operator_confirmation_ref`
    * Must identify the operator confirmation reference bound by the execution authorization CI output.
* `authorization_issuer`
    * Must identify the actor or governance surface that issued the execution authorization object.
* `authorization_reason`
    * Must state the bounded reason carried by the execution authorization object.
* `executor_intent_ref`
    * Must identify a rendered executor intent declaration reference. It is not a command.
* `executor_intent_created_at`
    * Must state when the executor intent declaration was created.
* `executor_intent_expires_at`
    * Must state when the executor intent declaration expires.
* `executor_mode`
    * Must identify the declared non-executable executor mode.
* `dry_run_required`
    * Must declare that dry-run evidence remains required.
* `transaction_plan_required`
    * Must declare that a future transaction plan is required before any mutation.
* `rollback_plan_required`
    * Must declare that a future rollback plan is required before any mutation.
* `idempotency_reservation_required`
    * Must declare that a future idempotency reservation is required before any mutation.
* `before_evidence_capture_required`
    * Must declare that before evidence capture is required before any mutation.
* `after_evidence_capture_required`
    * Must declare that after evidence capture is required after any mutation.
* `audit_append_required`
    * Must declare that audit append is required by any future governed write contract.
* `evidence_append_required`
    * Must declare that evidence append is required by any future governed write contract.
* `expected_rejection_policy_required`
    * Must declare that a future expected rejection policy is required before any mutation.
* `no_schema_migration_required`
    * Must declare that schema migration is not allowed in this path.
* `no_daemon_server_queue_required`
    * Must declare that daemon, server, and queue execution are not allowed in this path.
* `no_cli_required`
    * Must declare that CLI execution is not allowed in this path.
* `no_db_repair_required`
    * Must declare that DB repair is not allowed in this path.
* `irreversible_action_prohibited`
    * Must declare that irreversible action is prohibited.
* `executor_implementation_authorized`
    * Must declare whether executor implementation is authorized.
* `restore_execution_authorized`
    * Must declare whether restore execution is authorized.
* `write_side_recovery_authorized`
    * Must declare whether write-side recovery is authorized.
* `cli_execution_authorized`
    * Must declare whether CLI execution is authorized.
* `schema_migration_authorized`
    * Must declare whether schema migration is authorized.
* `daemon_server_queue_authorized`
    * Must declare whether daemon, server, or queue execution is authorized.
* `db_repair_authorized`
    * Must declare whether DB repair is authorized.
* `fail_closed_declared`
    * Must declare fail-closed behavior.
* `json_safe`
    * Must declare that the object is JSON-safe.

Missing fields, empty fields, malformed fields, non-JSON-safe values, ambiguous values, source mismatches, stale intent, unknown modes, or unauthorized true flags fail closed.

5. Required Source Bindings

A future read-only validator must enforce the following source bindings:

* `source_execution_authorization_read_only_stack_tag` must equal `execution-authorization-read-only-stack-v1`.
* `source_execution_authorization_read_only_stack_commit` must equal `d586aeb60620010c900df7be1a88621ab2cb8dc1`.
* `source_execution_authorization_validator_ci_ref` must bind to rendered validator CI output.
* `source_preflight_read_only_stack_tag` must equal `preflight-read-only-stack-v1`.
* `source_preflight_read_only_stack_commit` must equal `662b6161253c35204b437e88809c5bab21908c6d`.
* All task, operation, idempotency, projected action, and evidence refs must match execution authorization CI output.

The binding must be exact. Derived, inferred, partial, stale, or best-effort source binding is invalid and fails closed.

6. Required Operation Bindings

A future read-only validator must enforce the following operation bindings:

* `approved_task_id` must equal the approved task identifier in the execution authorization CI output.
* `approved_operation_kind` must equal the approved operation kind in the execution authorization CI output.
* `idempotency_key` must equal the idempotency key in the execution authorization CI output.
* `projected_action` must equal the projected action in the execution authorization CI output.
* `projected_evidence_ref` must equal the projected evidence reference in the execution authorization CI output.
* `human_approval_ref` must equal the human approval reference in the execution authorization CI output.
* `operator_confirmation_ref` must equal the operator confirmation reference in the execution authorization CI output.
* `authorization_issuer` must equal the authorization issuer in the execution authorization CI output.
* `authorization_reason` must equal the authorization reason in the execution authorization CI output.

Task mismatch fails closed.

Operation mismatch fails closed.

Idempotency mismatch fails closed.

Projected action mismatch fails closed.

Projected evidence mismatch fails closed.

Human approval mismatch fails closed.

Operator confirmation mismatch fails closed.

Authorization issuer mismatch fails closed.

Authorization reason mismatch fails closed.

7. Executor Intent Model

`executor_intent_ref` is a rendered declaration ref, not a command.

`executor_intent_created_at` must be parseable.

`executor_intent_expires_at` must be parseable.

`executor_intent_expires_at` must be after `executor_intent_created_at`.

`executor_mode` must be a declared string enum.

Allowed v1 `executor_mode` values are:

* `contract_only`
* `future_executor_review`

`dry_run_required` must be true.

Executor intent does not authorize execution.

Executor intent does not authorize restore.

Executor intent does not authorize write-side recovery.

Executor intent does not authorize DB writes.

Executor intent does not authorize evidence append.

Executor intent does not authorize audit append.

Stale intent fails closed in a future validator.

Unknown `executor_mode` fails closed.

8. Required Plan Declarations

`transaction_plan_required` must be true.

`rollback_plan_required` must be true.

`idempotency_reservation_required` must be true.

`expected_rejection_policy_required` must be true.

These are declarations only.

No transaction is opened in this spec.

No idempotency reservation is created in this spec.

No rollback mechanism is implemented in this spec.

No expected rejection policy is implemented in this spec.

Missing or false plan declarations fail closed.

9. Evidence and Audit Declarations

`before_evidence_capture_required` must be true.

`after_evidence_capture_required` must be true.

`audit_append_required` must be true.

`evidence_append_required` must be true.

These are declarations only.

No evidence is captured in this spec.

No evidence is appended in this spec.

No audit record is appended in this spec.

Mutation without before and after evidence remains forbidden.

The evidence spine must remain complete and replay-honest across source authorization output, precondition declaration, future validation output, and any separately authorized future mutation evidence.

10. No-Go Declarations

`no_schema_migration_required` must be true.

`no_daemon_server_queue_required` must be true.

`no_cli_required` must be true.

`no_db_repair_required` must be true.

If any future path requires schema migration, daemon execution, server execution, queue execution, CLI execution, or DB repair, that path fails closed and requires a separate package.

False no-go declarations fail closed.

11. Required False Authorization Flags

For v1:

* `executor_implementation_authorized` must be false.
* `restore_execution_authorized` must be false.
* `write_side_recovery_authorized` must be false.
* `cli_execution_authorized` must be false.
* `schema_migration_authorized` must be false.
* `daemon_server_queue_authorized` must be false.
* `db_repair_authorized` must be false.

The v1 contract defines prerequisites only.

The v1 contract does not authorize implementation.

The v1 contract does not authorize restore.

The v1 contract does not authorize write-side recovery.

The v1 contract does not authorize CLI execution.

The v1 contract does not authorize schema migration.

The v1 contract does not authorize daemon, server, or queue execution.

The v1 contract does not authorize DB repair.

The v1 contract does not authorize DB writes.

The v1 contract does not authorize evidence append or audit append.

Any true authorization flag in v1 fails closed.

12. Fail-Closed and JSON Safety

`irreversible_action_prohibited` must be true.

`fail_closed_declared` must be true.

`json_safe` must be true.

Missing field fails closed.

Malformed field fails closed.

Empty field fails closed unless a future validator contract explicitly identifies the field as optional. This v1 contract defines no optional fields.

Mismatch fails closed.

Stale intent fails closed.

Unknown `executor_mode` fails closed.

Unauthorized true flag fails closed.

Non-JSON-safe payload fails closed.

Irreversible action fails closed.

Ambiguous replay fails closed.

13. Future Validator Contract

A future read-only validator may consume already-rendered execution authorization validator CI output.

A future read-only validator may consume an already-rendered `ExecutorPreconditionV1` declaration.

A future read-only validator may consume explicit `evaluation_time` if freshness is evaluated.

A future read-only validator must validate source bindings.

A future read-only validator must validate operation bindings.

A future read-only validator must validate required declarations.

A future read-only validator must validate required false flags.

A future read-only validator may output `executor_precondition_ready`.

`executor_precondition_ready=True` remains readiness only.

The future validator does not execute.

The future validator does not open DB.

The future validator does not call services.

The future validator does not append evidence.

The future validator does not append audit records.

The future validator does not call executor.

The future validator does not call restore.

The future validator does not create approval, review, revision, evidence, or audit artifacts.

14. Future CI Consumer Contract

A future CI consumer may consume already-rendered executor precondition validator output only.

The future CI consumer does not call validator.

The future CI consumer does not execute.

The future CI consumer does not open DB.

The future CI consumer does not call services.

The future CI consumer does not append evidence.

The future CI consumer does not append audit records.

The future CI consumer does not call executor.

The future CI consumer does not call restore.

`ci_ok=True` remains readiness only.

No CI verdict may trigger execution.

No CI verdict may grant authorization.

15. Future Executor Eligibility

Executor discussion cannot begin until all of the following are frozen or separately authorized as applicable:

* executor precondition contract spec is frozen
* executor precondition validator is frozen
* executor precondition validator CI is frozen
* execution authorization read-only stack is frozen
* write path design audit explicitly authorizes executor discussion
* transaction, rollback, evidence, and idempotency paths are separately designed and frozen
* DB, repository, and Unit of Work writes are separately authorized
* evidence and audit append are separately authorized

Even after these eligibility prerequisites, executor implementation remains unauthorized until a separate package explicitly authorizes it.

16. Forbidden Until Separately Authorized

The following remain forbidden until separately authorized:

* executor implementation
* restore execution
* restore CLI
* DB writes
* repository writes
* Unit of Work writes
* approval service calls
* review service calls
* revision seal service calls
* evidence service calls
* approval artifact creation
* review artifact creation
* evidence append
* audit append
* schema/migration
* daemon/server/queue
* DB repair
* irreversible actions

This contract does not create an exception to any forbidden path.

17. Failure Policy

Missing source binding fails closed.

Source commit mismatch fails closed.

Task mismatch fails closed.

Operation mismatch fails closed.

Idempotency mismatch fails closed.

Malformed executor intent fails closed.

Stale executor intent fails closed.

Missing required plan declaration fails closed.

Missing evidence or audit declaration fails closed.

False no-go declaration fails closed.

True authorization flag fails closed.

Unknown mode fails closed.

Non-JSON-safe payload fails closed.

Any attempt to treat readiness as authorization fails closed.

Any attempt to treat authorization readiness as execution fails closed.

Any attempt to treat precondition readiness as execution fails closed.

Any attempt to use a read-only verdict, validator verdict, or CI verdict to trigger execution fails closed.

18. Non-Goals

This spec does not implement anything.

This spec does not define a validator.

This spec does not define CI.

This spec does not define an executor.

This spec does not define restore.

This spec does not define CLI.

This spec does not write to DB.

This spec does not define repository behavior.

This spec does not define Unit of Work behavior.

This spec does not call services.

This spec does not append evidence.

This spec does not append audit records.

This spec does not define schema or migration.

This spec does not define daemon, server, or queue behavior.

This spec does not authorize executor implementation.

This spec does not authorize restore execution.

This spec does not authorize write-side recovery.

This spec does not authorize CLI execution.

This spec does not authorize DB writes.

19. Freeze Criteria

Freeze requires:

* one spec document only
* no production code changes
* no test changes unless required by repository convention
* no service changes
* no schema changes
* no CLI changes
* no DB changes
* tests remain green
* working tree clean
* tag candidate: executor-precondition-contract-spec-only-v1

The freeze candidate must not claim executor implementation is authorized, restore execution is authorized, write-side recovery is authorized, CLI execution is authorized, DB writes are authorized, schema migration is authorized, daemon/server/queue execution is authorized, DB repair is authorized, evidence append is authorized, audit append is authorized, or irreversible action is authorized.
