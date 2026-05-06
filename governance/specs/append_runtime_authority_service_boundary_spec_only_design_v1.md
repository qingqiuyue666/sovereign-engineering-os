# Append Runtime Authority / Service Boundary Spec-Only Design v1

Status: draft for human review

Canonical target filename: `governance/specs/append_runtime_authority_service_boundary_spec_only_design_v1.md`

Verdict: SPEC_ONLY_COMPLETE

Tag candidate: `append-runtime-authority-service-boundary-spec-only-v1`

## 1. Purpose and Non-Authority

This document is governance-only.

This document defines runtime append authority/service boundary vocabulary.

This document is non-executable and spec-only. It adds no production code, no
tests, no validator, no checker, no CI consumer, no runtime allowlist, no
executor, no restore path, no CLI command, no schema, no migration, no daemon,
no server, and no queue.

This document does not authorize runtime append.

This document does not authorize evidence append.

This document does not authorize audit append.

This document does not authorize evidence service calls.

This document does not authorize approval/review/revision service calls.

This document does not authorize DB/repository/UoW writes.

This document does not authorize transaction runtime.

This document does not authorize idempotency reservation runtime.

This document does not authorize rollback runtime.

This document does not authorize executor.

This document does not authorize restore.

This document does not authorize CLI/schema/daemon work.

Readiness is not authorization. Authorization is not execution. Default deny
and fail closed remain mandatory.

## 2. Governing Baselines

The following frozen baselines govern this specification. The pinned commits
are binding source refs; this specification is invalid if any listed tag is
moved, missing, unresolved, ambiguous, or commit-mismatched.

- `read-only-governance-layer-v1` -> `4656e8f03404c6bb39e7976c6165e3d7dc0314fb`
- `write-side-precondition-checker-v1` -> `fd5788c7a4d3ed953fbc0295414ba7e6ad4f89f6`
- `write-side-precondition-ci-v1` -> `05c81541ad3d7deee20023843142f702937f6c3f`
- `write-side-recovery-spec-only-v1` -> `ad560cc2dab135f2c1d56d948410ae47586d118e`
- `restore-dry-run-read-only-stack-v1` -> `e7c78e3ff0c5dc05806c293f01ab32cd33c9518b`
- `preflight-read-only-stack-v1` -> `662b6161253c35204b437e88809c5bab21908c6d`
- `execution-authorization-read-only-stack-v1` -> `d586aeb60620010c900df7be1a88621ab2cb8dc1`
- `executor-precondition-read-only-stack-v1` -> `cb3948eb843866dcc961b6a074038c13db64d017`
- `write-path-read-only-stack-v1` -> `8ffd4679aca8f593415089748df35df42af8f015`
- `repository-uow-allowlist-read-only-stack-v1` -> `bec2d04eab1922594dcbfbe35971f4efe0fe4849`
- `evidence-audit-append-read-only-stack-v1` -> `62db8a586efa9375d2c77cf7c6335ccf5ef11279`

These baselines provide source evidence, vocabulary, and governance boundaries
only. They do not authorize runtime append, evidence append, audit append,
service calls, DB access, repository or Unit of Work access, executor
implementation, restore execution, CLI expansion, schema changes, background
execution, DB repair, durable writes, or irreversible action.

## 3. Contract Object

`AppendRuntimeAuthorityServiceBoundaryV1` is the contract object defined by
this specification.

`AppendRuntimeAuthorityServiceBoundaryV1` is a future declaration target for
read-only validation. It is not an implementation, not a validator, not a
checker, not a CI consumer, not a service adapter, not an evidence writer, not
an audit writer, not a DB handle, not a repository handle, not a Unit of Work
handle, not a transaction, not a rollback runtime, not an idempotency
reservation runtime, not a runtime allowlist, not an executor, not restore, not
CLI, not schema or migration logic, not daemon/server/queue logic, and not DB
repair.

A future rendered `AppendRuntimeAuthorityServiceBoundaryV1` object must be
explicit, bounded, source-bound, operation-bound, replay-honest, JSON-safe,
deterministic, revocable, and fail-closed.

The future contract must define these fields and concepts:

- source bindings
- operation binding fields
- authority declaration fields
- service boundary fields
- DB/repository/UoW boundary fields
- idempotency reservation fields
- transaction ownership fields
- rollback/failure/incident fields
- append phase authority fields
- required false authority flags
- forbidden surface declarations
- future validator requirements
- future CI requirements
- freeze criteria

## 4. Source Bindings

A future `AppendRuntimeAuthorityServiceBoundaryV1` object must define source
tag and commit fields for every governing baseline:

- `source_read_only_governance_layer_tag`
- `source_read_only_governance_layer_commit`
- `source_write_side_precondition_checker_tag`
- `source_write_side_precondition_checker_commit`
- `source_write_side_precondition_ci_tag`
- `source_write_side_precondition_ci_commit`
- `source_write_side_recovery_spec_only_tag`
- `source_write_side_recovery_spec_only_commit`
- `source_restore_dry_run_read_only_stack_tag`
- `source_restore_dry_run_read_only_stack_commit`
- `source_preflight_read_only_stack_tag`
- `source_preflight_read_only_stack_commit`
- `source_execution_authorization_read_only_stack_tag`
- `source_execution_authorization_read_only_stack_commit`
- `source_executor_precondition_read_only_stack_tag`
- `source_executor_precondition_read_only_stack_commit`
- `source_write_path_read_only_stack_tag`
- `source_write_path_read_only_stack_commit`
- `source_repository_uow_allowlist_read_only_stack_tag`
- `source_repository_uow_allowlist_read_only_stack_commit`
- `source_evidence_audit_append_read_only_stack_tag`
- `source_evidence_audit_append_read_only_stack_commit`

The object must fail closed on any missing, malformed, stale, ambiguous,
unresolved, target-mismatched, or commit-mismatched source binding.

## 5. Operation Binding Model

A future `AppendRuntimeAuthorityServiceBoundaryV1` object must define these
operation binding fields:

- `approved_task_id`
- `approved_operation_kind`
- `idempotency_key`
- `append_contract_ref`
- `append_idempotency_key`
- `evidence_ref_set`
- `audit_ref_set`
- `human_approval_ref`
- `operator_confirmation_ref`
- `execution_authorization_validator_ci_ref`
- `executor_precondition_validator_ci_ref`
- `write_path_contract_validator_ci_ref`
- `repository_uow_allowlist_validator_ci_ref`
- `evidence_audit_append_contract_validator_ci_ref`
- `append_runtime_authority_contract_ref`

All operation binding fields are declarations only. They perform no runtime
lookup, call no validator, call no CI consumer, call no service, open no DB,
import no repository or Unit of Work, reserve no idempotency key, create no
evidence ref, create no audit ref, and append nothing.

The object must fail closed on derived, inferred, partial, best-effort,
target-ambiguous, stale, or binding-mismatched operation fields.

## 6. Runtime Authority Model

Append authority is explicit only.

Evidence append authority is explicit only.

Audit append authority is explicit only.

Service authority is explicit only.

DB authority is explicit only.

Repository/UoW authority is explicit only.

Transaction authority is explicit only.

Idempotency reservation authority is explicit only.

Rollback authority is explicit only.

Executor authority is explicit only.

Read-only stack success never grants runtime authority.

Authority must be source-bound, operation-bound, narrow, revocable, and
fail-closed.

No authority exists in this package. Any attempt to treat this specification,
any frozen read-only stack, or any future read-only validator/CI verdict as
runtime authority fails closed.

## 7. Service Boundary Model

A future `AppendRuntimeAuthorityServiceBoundaryV1` object must declare these
service boundary fields:

- `evidence_service_append_forbidden = true`
- `approval_service_forbidden = true`
- `review_service_forbidden = true`
- `revision_seal_service_forbidden = true`
- `service_adapter_required_for_future_runtime = true`
- `service_method_allowlist_required = true`
- `service_result_contract_required = true`
- `service_transaction_ownership_forbidden_by_default = true`
- `evidence_audit_ref_fabrication_forbidden = true`
- `service_calls_forbidden_in_spec_only_package = true`

A future service adapter must be separately authorized.

A future service adapter must use exact method allowlist.

A future service adapter must return bounded JSON-safe result.

Service must not own transaction unless separately authorized.

Service must not fabricate refs.

This specification calls no evidence service, approval service, review service,
revision seal service, or any other service.

## 8. DB / Repository / UoW Boundary Model

A future `AppendRuntimeAuthorityServiceBoundaryV1` object must declare these
DB/repository/UoW boundary fields:

- `direct_sqlite_forbidden = true`
- `ad_hoc_sql_forbidden = true`
- `repository_uow_import_forbidden = true`
- `repository_uow_call_forbidden = true`
- `kernel_owned_uow_required_for_future_runtime = true`
- `repository_method_allowlist_required = true`
- `repository_result_contract_required = true`
- `evidence_bearing_result_required = true`
- `executor_transaction_ownership_forbidden = true`
- `uncontrolled_nested_transaction_forbidden = true`

Direct sqlite remains forbidden.

Ad hoc SQL remains forbidden.

Repository/UoW import remains forbidden until separately authorized.

A future append implementation must go through kernel-owned UoW.

Future repository methods must be exact allowlist entries.

Future repository methods must return evidence-bearing result.

Executor must not own commit/rollback.

This specification opens no DB, imports no repository or Unit of Work, calls no
repository or Unit of Work, performs no direct SQL, performs no raw sqlite
operation, and changes no DB/repository/UoW behavior.

## 9. Idempotency Reservation Model

A future `AppendRuntimeAuthorityServiceBoundaryV1` object must declare these
idempotency reservation fields:

- `idempotency_reservation_required_before_mutation_or_append = true`
- `append_idempotency_key_binding_required = true`
- `same_key_same_binding_safe_replay_only = true`
- `same_key_different_binding_fail_closed = true`
- `ambiguous_reservation_incident_class = true`
- `replay_classification_required = true`
- `idempotency_runtime_not_authorized = true`

The append idempotency binding must include:

- source stack refs
- approved task
- operation kind
- idempotency key
- append contract ref
- append idempotency key
- evidence_ref_set
- audit_ref_set
- human approval ref
- operator confirmation ref
- execution authorization CI ref
- executor precondition CI ref
- write path contract CI ref
- repository/UoW allowlist CI ref
- evidence/audit append validator CI ref

No idempotency reservation runtime is authorized by this specification. It
creates no reservation table, no reservation row, no reservation repository, no
reservation service, and no reservation API.

## 10. Transaction Ownership Model

A future `AppendRuntimeAuthorityServiceBoundaryV1` object must declare these
transaction ownership fields:

- `one_outer_kernel_owned_transaction_required = true`
- `uncontrolled_nested_transaction_forbidden = true`
- `append_mutation_order_required = true`
- `commit_after_required_bookkeeping_only = true`
- `rollback_on_unexpected_exception_required = true`
- `rollback_failure_incident_class = true`
- `out_of_band_append_requires_explicit_declaration = true`
- `transaction_runtime_not_authorized = true`

A future authorized path must use this order:

1. validate read-only prerequisites
2. bind operation refs
3. reserve idempotency key
4. declare before evidence append
5. declare mutation intent evidence append
6. perform mutation only if separately authorized
7. declare after evidence append
8. declare audit event append
9. declare failure/rejection/rollback append
10. commit only after required bookkeeping succeeds
11. rollback on unexpected failure

This ordering is a declaration only. This specification starts no transaction,
commits nothing, rolls back nothing, reserves no idempotency key, performs no
mutation, and appends no evidence or audit record.

## 11. Append Phase Runtime Model

A future `AppendRuntimeAuthorityServiceBoundaryV1` object must declare every
append phase as separately authorized:

- `before_evidence_append_authority_required = true`
- `mutation_intent_evidence_append_authority_required = true`
- `after_evidence_append_authority_required = true`
- `rejection_evidence_append_authority_required = true`
- `failure_evidence_append_authority_required = true`
- `rollback_evidence_append_authority_required = true`
- `audit_event_append_authority_required = true`
- `duplicate_replay_audit_append_authority_required = true`
- `ambiguous_replay_audit_append_authority_required = true`
- `incident_audit_append_authority_required = true`
- `per_phase_authorization_required = true`

None of these phases are implemented or authorized in this package.

These declarations do not capture evidence, append evidence, append audit
records, create refs, reserve keys, run rollback, perform mutation, or grant
service authority.

## 12. Failure / Incident Model

A future `AppendRuntimeAuthorityServiceBoundaryV1` object must declare these
failure and incident fields:

- `expected_rejection_is_not_execution_failure = true`
- `unexpected_exception_requires_rollback = true`
- `append_failure_before_mutation_blocks_mutation = true`
- `append_failure_after_mutation_is_incident_class = true`
- `rollback_failure_is_incident_class = true`
- `duplicate_mismatched_idempotency_is_incident_class = true`
- `ambiguous_append_or_replay_is_incident_class = true`
- `partial_success_forbidden = true`
- `success_requires_all_required_append_bookkeeping = true`
- `silent_success_forbidden = true`

Expected rejection is not mutation success.

Unexpected exception is not expected rejection.

Rollback failure must not be hidden as success, expected rejection, duplicate
replay, or ordinary failure.

Post-mutation append failure requires incident classification in a later
separately authorized package. This specification does not authorize any
mutation that could create that state.

## 13. Required False Authority Flags

A future `AppendRuntimeAuthorityServiceBoundaryV1` object must list exactly and
keep false:

- `append_runtime_authorized = false`
- `evidence_append_authorized = false`
- `audit_append_authorized = false`
- `evidence_service_authorized = false`
- `approval_service_authorized = false`
- `review_service_authorized = false`
- `revision_seal_service_authorized = false`
- `repository_uow_writes_authorized = false`
- `direct_db_writes_authorized = false`
- `raw_sqlite_authorized = false`
- `ad_hoc_sql_authorized = false`
- `transaction_runtime_authorized = false`
- `idempotency_reservation_authorized = false`
- `rollback_runtime_authorized = false`
- `durable_writes_authorized = false`
- `irreversible_action_authorized = false`
- `executor_implementation_authorized = false`
- `restore_execution_authorized = false`
- `write_side_recovery_authorized = false`
- `cli_execution_authorized = false`
- `schema_migration_authorized = false`
- `daemon_server_queue_authorized = false`
- `db_repair_authorized = false`

Any missing, malformed, non-boolean, or unauthorized true flag fails closed.

## 14. Forbidden Surfaces

The following surfaces are explicitly forbidden by this specification:

- evidence append implementation
- audit append implementation
- evidence service call
- approval service call
- review service call
- revision seal service call
- DB open/write
- repository/UoW import/call
- direct SQL/raw sqlite
- transaction runtime
- idempotency reservation runtime
- rollback runtime
- runtime allowlist/checker/enforcer
- executor
- restore
- restore CLI
- CLI expansion
- schema/migration
- daemon/server/queue
- external network
- filesystem side channel
- irreversible action

This list grants no exception. Any future request into one of these surfaces
requires separate authorization.

## 15. Future Validator Requirements

A future validator must:

- consume already-rendered `AppendRuntimeAuthorityServiceBoundaryV1`
- validate source bindings
- validate operation bindings
- validate service boundary declarations
- validate DB/repository/UoW boundary declarations
- validate idempotency reservation declarations
- validate transaction ownership declarations
- validate rollback/failure/incident declarations
- validate append phase authority declarations
- validate all required false authority flags
- validate JSON safety
- not call services
- not open DB
- not import repository/UoW
- not append evidence/audit
- not implement runtime

The future validator must fail closed on missing, malformed, stale,
ambiguous, mismatched, non-JSON-safe, or unauthorized true declarations.

This specification does not add that validator.

## 16. Future CI Requirements

A future CI must:

- consume already-rendered validator output only
- not call validator
- validate bounded shape
- validate false authority flags
- validate JSON safety
- not call services
- not open DB
- not import repository/UoW
- not append evidence/audit
- not implement runtime

The future CI consumer must fail closed on malformed validator output,
ambiguous status, missing false flags, unauthorized true flags, unbounded
output, or runtime-object leakage.

This specification does not add that CI consumer.

## 17. Future Package Sequence

A future package sequence is:

1. append-runtime-authority-service-boundary-spec-only-v1
2. read-only validator over AppendRuntimeAuthorityServiceBoundaryV1
3. read-only CI consumer over validator output
4. append runtime authority read-only stack consolidation
5. service adapter spec-only design audit
6. repository/UoW runtime allowlist/enforcer design audit
7. executor design audit only after all above freeze

This sequence is planning guidance only. It authorizes no runtime append,
evidence append, audit append, service call, DB/repository/UoW access,
transaction runtime, idempotency reservation runtime, rollback runtime,
executor, restore, CLI, schema/migration, daemon/server/queue, durable write,
or irreversible action.

## 18. Acceptance Requirements

This package is acceptable only if all of the following remain true:

- exactly one new spec doc
- no production code
- no tests unless required by repository convention
- no existing docs changed
- no service calls
- no DB/repository/UoW use
- no append implementation
- no runtime authority granted
- all false flags remain false
- all required health checks green
- working tree clean
- candidate tag absent before freeze

Acceptance of this spec-only package does not authorize runtime append,
evidence append, audit append, service calls, DB/repository/UoW access,
transaction runtime, idempotency reservation runtime, rollback runtime,
executor implementation, restore execution, CLI expansion, schema changes,
daemon/server/queue execution, DB repair, durable writes, or irreversible
action.

## 19. Freeze Criteria

Future tag criteria for
`append-runtime-authority-service-boundary-spec-only-v1`:

- PR merged to main
- exactly one new governance spec doc
- no production/test/runtime/schema/service/DB changes
- all baselines resolve
- candidate tag absent
- health checks green
- working tree clean
- stop/consolidate audit recommends tag

Freeze of `append-runtime-authority-service-boundary-spec-only-v1` must not
claim runtime append is authorized, evidence append is authorized, audit append
is authorized, service authority is authorized, DB/repository/UoW writes are
authorized, transaction runtime is authorized, idempotency reservation is
authorized, rollback runtime is authorized, durable writes are authorized, or
irreversible action is authorized.

Freeze is a checkpoint recommendation only. It does not authorize
implementation, execution, append, DB, service, repository/UoW, CLI,
schema/migration, daemon/server/queue, DB repair, durable write, or
irreversible action.
