Write Path Transaction Evidence Idempotency Spec-Only Design v1

Status: draft for human review

Canonical target filename: governance/specs/write_path_transaction_evidence_idempotency_spec_only_design_v1.md

Verdict: SPEC_ONLY_COMPLETE

Tag candidate: write-path-transaction-evidence-idempotency-spec-only-v1

1. Purpose

This spec freezes the write-side execution contract required before executor or restore implementation can be discussed.

This spec is non-executable.

This spec grants no executor authority, restore authority, write-side recovery authority, CLI authority, DB write authority, repository or Unit of Work write authority, service authority, evidence append authority, audit append authority, schema authority, daemon/server/queue authority, DB repair authority, or irreversible action authority.

This spec defines future layers only. It does not implement them.

2. Governing Baselines

The governing baseline is fixed by the following frozen dependencies:

* restore-dry-run-read-only-stack-v1
    * target: e7c78e3ff0c5dc05806c293f01ab32cd33c9518b
* preflight-read-only-stack-v1
    * target: 662b6161253c35204b437e88809c5bab21908c6d
* execution-authorization-read-only-stack-v1
    * target: d586aeb60620010c900df7be1a88621ab2cb8dc1
* executor-precondition-read-only-stack-v1
    * target: cb3948eb843866dcc961b6a074038c13db64d017
* write-side-recovery-spec-only-v1
    * target: ad560cc2dab135f2c1d56d948410ae47586d118e
* write-side-precondition-checker-v1
    * target: fd5788c7a4d3ed953fbc0295414ba7e6ad4f89f6
* write-side-precondition-ci-v1
    * target: 05c81541ad3d7deee20023843142f702937f6c3f
* read-only-governance-layer-v1
    * target: 4656e8f03404c6bb39e7976c6165e3d7dc0314fb

These checkpoints provide source evidence and governance boundaries only. They do not grant write authority.

3. Non-Authorizing Status

This spec does not authorize executor implementation.

This spec does not authorize restore execution.

This spec does not authorize write-side recovery execution.

This spec does not authorize CLI.

This spec does not authorize DB writes.

This spec does not authorize repository or Unit of Work writes.

This spec does not authorize evidence or audit append.

This spec does not authorize approval service calls, review service calls, revision seal service calls, or evidence service calls.

This spec does not authorize approval artifact creation, review artifact creation, revision seal creation, evidence record creation, or audit record creation.

This spec does not authorize schema or migration changes.

This spec does not authorize daemon, server, queue, async worker, or background execution.

This spec does not authorize DB repair.

This spec does not authorize irreversible actions.

Any attempt to treat this spec as execution authority fails closed.

4. Contract Name

The future contract object name is:

WritePathTransactionEvidenceIdempotencyV1

WritePathTransactionEvidenceIdempotencyV1 is a future contract object, not an implementation.

The object is a declaration and validation target for a later package. It is not an executor, not restore, not CLI, not a DB handle, not a service adapter, not an idempotency reservation, not a transaction, not rollback logic, not evidence append, and not audit append.

5. Source Bindings

A future WritePathTransactionEvidenceIdempotencyV1 object must bind the following source refs:

* restore-dry-run-read-only-stack-v1
* preflight-read-only-stack-v1
* execution-authorization-read-only-stack-v1
* executor-precondition-read-only-stack-v1
* execution authorization validator CI ref
* executor precondition validator CI ref
* human approval ref
* operator confirmation ref

The future object must fail closed on any missing, malformed, stale, ambiguous, unresolved, target-mismatched, or commit-mismatched source binding.

Readiness, authorization readiness, and executor precondition readiness are preconditions only. They are not execution.

6. Operation Bindings

A future WritePathTransactionEvidenceIdempotencyV1 object must bind:

* approved_task_id
* approved_operation_kind
* idempotency_key
* projected_action
* projected_evidence_ref
* target artifact identifiers
* target task identifiers
* before evidence ref placeholder
* after evidence ref requirement

The future object must fail closed on derived, inferred, partial, best-effort, or target-ambiguous operation bindings.

Projected action is not mutation.

Projected evidence is not evidence append.

After evidence requirement is not after evidence capture.

7. Transaction Boundary

A future authorized write path must use one outer kernel-owned transaction per execution attempt.

Uncontrolled nested transactions are forbidden.

Direct executor-owned sqlite transactions are forbidden.

Partial mutation outside the transaction is forbidden.

Commit may occur only after all required mutation, idempotency, evidence, and audit obligations succeed under a future separately authorized path.

Unexpected failure must roll back the mutation boundary.

The transaction cannot begin in this spec.

This spec opens no DB, starts no transaction, commits nothing, and rolls back nothing.

8. Mutation Ordering

A future authorized write path must use this order:

1. validate frozen read-only stack references
2. validate execution authorization CI
3. validate executor precondition CI
4. reserve idempotency key
5. capture or bind before evidence
6. append mutation intent evidence if authorized
7. perform mutation through approved repository or Unit of Work only
8. capture after evidence
9. append after evidence and audit records if authorized
10. commit transaction
11. emit bounded result

None of this order is implemented by this spec.

No mutation order is executable until a later package separately authorizes the required write, repository, Unit of Work, evidence, audit, and service surfaces.

9. Rollback Semantics

Unexpected exception must roll back all mutation.

Rollback failure is incident-class.

Evidence append failure before mutation blocks mutation.

Evidence append failure after mutation enters the incident path.

Expected governance rejection is not rollback.

Silent partial success is forbidden.

Silent continuation after failed mutation is forbidden.

This spec implements no rollback mechanism and records no rollback evidence.

10. Expected Rejection Policy

Expected rejection is a governed refusal, not system failure.

Expected rejection must not mutate target state.

Expected rejection must emit a bounded rejection result.

Rejection evidence may exist only if explicitly authorized by a later package.

Rejection evidence must be bounded to the refusal and must not fabricate mutation success.

Expected rejection must preserve replay honesty across the source refs, operation bindings, idempotency key, approval refs, precondition refs, and evidence declarations.

11. Unexpected Failure Policy

Unexpected runtime failure is not expected rejection.

Unexpected runtime failure requires rollback.

Unexpected runtime failure must not be silently swallowed.

Unexpected runtime failure must not be reported as ambiguous success.

Unexpected runtime failure must not be reported as partial success.

Future failure evidence or incident evidence requires explicit separate authorization.

12. Idempotency Reservation

Idempotency reservation must occur before mutation.

The idempotency key must be bound to:

* approved_task_id
* approved_operation_kind
* projected_action
* projected_evidence_ref
* human_approval_ref
* operator_confirmation_ref
* execution_authorization_validator_ci_ref
* executor_precondition_validator_ci_ref
* target artifact identifiers
* target task identifiers

Duplicate use with the same binding must return the same result or a safe replay classification.

Duplicate use with a different binding must fail closed.

Ambiguous replay must fail closed.

No idempotency reservation implementation exists in this spec.

This spec creates no reservation table, no reservation row, no reservation repository, no reservation service, and no reservation API.

13. Evidence and Audit Model

Before evidence is required before mutation.

Mutation intent evidence is required before mutation if future append is authorized.

After evidence is required after mutation.

Audit and evidence append order must be deterministic.

The evidence spine must support forensic reconstruction from frozen source refs through authorization, precondition, idempotency, mutation intent, before evidence, mutation result, after evidence, audit records, and final bounded result.

Append failure before mutation blocks mutation.

Append failure after mutation enters the incident path.

No append implementation exists in this spec.

This spec captures no evidence, appends no evidence, appends no audit record, writes no replay receipt, and closes no evidence plane.

14. Repository and Unit of Work Boundary

Future executor direct sqlite access is forbidden.

Ad hoc SQL in a future executor is forbidden.

Filesystem write side channels are forbidden.

A future repository and Unit of Work allowlist is required before any write path can execute.

There must be one Unit of Work boundary per execution attempt.

Repository writes must return or expose artifacts needed for the evidence spine.

Repository writes must not hide evidence, audit, service, filesystem, CLI, daemon, server, queue, schema, migration, or DB repair side effects.

No repository or Unit of Work writes are authorized now.

This spec defines no repository behavior, no Unit of Work behavior, no allowlist code, and no DB write path.

15. Service Boundary

Approval service remains forbidden.

Review service remains forbidden.

Revision seal service remains forbidden.

Evidence service remains forbidden.

Hidden service side effects are forbidden.

Validators, checkers, CI consumers, and spec-only artifacts must not call services.

Future service integration requires separate design, validator or checker coverage, tests, and checkpoint freeze.

This spec calls no service and creates no approval, review, revision, evidence, or audit artifact.

16. Required False Flags

A future WritePathTransactionEvidenceIdempotencyV1 object must keep these flags false unless a later frozen package explicitly authorizes a different value:

* executor_implementation_authorized
* restore_execution_authorized
* write_side_recovery_authorized
* cli_execution_authorized
* schema_migration_authorized
* daemon_server_queue_authorized
* db_repair_authorized
* repository_uow_writes_authorized
* evidence_append_authorized
* audit_append_authorized
* durable_writes_authorized
* irreversible_action_authorized

Any missing, malformed, non-boolean, or unauthorized true flag fails closed.

17. Future Validator and Checker Sequence

A possible future sequence is:

1. write-path spec-only freeze
2. write-path contract validator/checker design audit
3. write-path contract validator/checker
4. write-path CI consumer
5. repository/Unit of Work allowlist spec
6. evidence/audit append contract spec
7. executor design audit
8. only then discuss executor implementation

This sequence is planning guidance only.

No validator, checker, CI consumer, allowlist, append contract, executor audit, executor implementation, restore implementation, CLI, schema migration, daemon, server, queue, DB repair, service integration, evidence append, or audit append is authorized by this spec.

18. Acceptance Requirements for Future Implementation

Future implementation packages must include tests for:

* expected rejection no mutation
* unexpected failure rollback
* duplicate idempotency same binding
* duplicate idempotency different binding
* before evidence missing blocks mutation
* after evidence failure incident path
* evidence append order deterministic
* rollback failure incident-class
* no direct sqlite
* no ad hoc SQL
* no unauthorized service call
* no CLI unless authorized
* replay reconstruction
* fail closed on stale authorization or precondition
* fail closed on unauthorized true flags

These are future acceptance requirements only.

This spec adds no tests.

19. Forbidden Surfaces

The following remain forbidden until separately authorized:

* executor implementation
* restore execution
* restore CLI
* DB writes
* repository writes
* Unit of Work writes
* evidence append
* audit append
* approval service calls
* review service calls
* revision seal service calls
* evidence service calls
* approval artifact creation
* review artifact creation
* revision seal creation
* evidence artifact creation
* schema/migration
* daemon/server/queue
* DB repair
* irreversible actions

This spec creates no exception to any forbidden surface.

20. Freeze Criteria

Freeze requires:

* one doc only
* no production code
* no tests unless required by repository convention
* no validator
* no checker
* no CI consumer
* no executor
* no restore
* no CLI
* no schema or migration
* no daemon, server, queue, async worker, or background execution
* no DB access
* no repository or Unit of Work access
* no service calls
* no evidence append
* no audit append
* health checks green
* prior tags resolve
* working tree clean
* candidate tag absent

Candidate tag:

* write-path-transaction-evidence-idempotency-spec-only-v1

The freeze candidate must not claim executor implementation is authorized, restore execution is authorized, write-side recovery is authorized, CLI execution is authorized, DB writes are authorized, repository or Unit of Work writes are authorized, schema migration is authorized, daemon/server/queue execution is authorized, DB repair is authorized, evidence append is authorized, audit append is authorized, durable writes are authorized, or irreversible action is authorized.
