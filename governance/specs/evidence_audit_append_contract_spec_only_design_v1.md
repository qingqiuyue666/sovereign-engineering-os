# Evidence/Audit Append Contract Spec-Only Design V1

Status: draft for human review

Canonical target filename: `governance/specs/evidence_audit_append_contract_spec_only_design_v1.md`

Verdict: SPEC_ONLY_COMPLETE

Tag candidate: `evidence-audit-append-contract-spec-only-v1`

## 1. Purpose and non-authority

This document defines the spec-only package
`evidence-audit-append-contract-spec-only-v1`.

This document is non-executable governance specification only.

This document adds no production code.

This document adds no tests.

This document adds no validator, checker, CI consumer, runtime allowlist,
executor, restore path, CLI command, schema, migration, daemon, server, queue,
DB repair path, repository behavior, Unit of Work behavior, service adapter,
evidence append implementation, or audit append implementation.

This document opens no DB, imports no repository or Unit of Work, calls no
repository or Unit of Work, calls no service, appends no evidence, appends no
audit record, performs no filesystem side-channel write, performs no external
network action, and performs no irreversible action.

This document grants no write authority. Readiness is not authorization.
Authorization is not execution. Default deny and fail closed remain mandatory.

## 2. Governing baselines

The following frozen baselines govern this specification. The pinned commits
are binding source refs; this specification is invalid if any listed tag is
moved, missing, unresolved, ambiguous, or commit-mismatched.

- `read-only-governance-layer-v1`
  - target: `4656e8f03404c6bb39e7976c6165e3d7dc0314fb`
- `write-side-precondition-checker-v1`
  - target: `fd5788c7a4d3ed953fbc0295414ba7e6ad4f89f6`
- `write-side-precondition-ci-v1`
  - target: `05c81541ad3d7deee20023843142f702937f6c3f`
- `write-side-recovery-spec-only-v1`
  - target: `ad560cc2dab135f2c1d56d948410ae47586d118e`
- `restore-dry-run-read-only-stack-v1`
  - target: `e7c78e3ff0c5dc05806c293f01ab32cd33c9518b`
- `preflight-read-only-stack-v1`
  - target: `662b6161253c35204b437e88809c5bab21908c6d`
- `execution-authorization-read-only-stack-v1`
  - target: `d586aeb60620010c900df7be1a88621ab2cb8dc1`
- `executor-precondition-read-only-stack-v1`
  - target: `cb3948eb843866dcc961b6a074038c13db64d017`
- `write-path-read-only-stack-v1`
  - target: `8ffd4679aca8f593415089748df35df42af8f015`
- `repository-uow-allowlist-read-only-stack-v1`
  - target: `bec2d04eab1922594dcbfbe35971f4efe0fe4849`

These baselines provide source evidence, vocabulary, and governance boundaries
only. They do not authorize evidence append, audit append, durable writes,
service calls, DB access, repository or Unit of Work access, executor
implementation, restore execution, CLI expansion, schema changes, background
execution, DB repair, or irreversible action.

## 3. Relationship to write-path read-only stack

This specification sits after `write-path-read-only-stack-v1`.

The write-path read-only stack establishes read-only structural readiness for
future write-path analysis. It does not authorize mutation, evidence append,
audit append, repository writes, Unit of Work writes, service calls, executor
implementation, restore execution, or CLI expansion.

`EvidenceAuditAppendContractV1` must preserve the write-path stack boundary:
all future append requirements are declarations over already-rendered inputs
until a later separately frozen package authorizes implementation.

## 4. Relationship to repository/UoW allowlist read-only stack

This specification sits after `repository-uow-allowlist-read-only-stack-v1`.

The repository/UoW allowlist read-only stack defines read-only allowlist
readiness and forbidden repository/UoW surfaces. It does not authorize a
repository import, a Unit of Work import, a repository call, a Unit of Work
call, direct SQL, raw sqlite, DB open, DB write, transaction execution, or
durable mutation.

`EvidenceAuditAppendContractV1` must not narrow, override, or bypass the
repository/UoW allowlist boundary. Any future append implementation remains
ineligible until the allowlist, transaction, evidence, audit, service, and
executor boundaries are separately authorized and frozen.

## 5. Contract object: EvidenceAuditAppendContractV1

`EvidenceAuditAppendContractV1` is the future contract object defined by this
specification.

`EvidenceAuditAppendContractV1` is a declaration target for future read-only
validation. It is not an implementation, not a validator, not a checker, not a
CI consumer, not a service adapter, not an evidence writer, not an audit
writer, not a DB handle, not a repository or Unit of Work handle, not a
runtime allowlist, not an executor, not restore, not CLI, not schema or
migration logic, not daemon/server/queue logic, and not DB repair.

A future rendered `EvidenceAuditAppendContractV1` object must be explicit,
bounded, replay-honest, JSON-safe, deterministic, and fail-closed.

## 6. Source bindings

A future `EvidenceAuditAppendContractV1` object must bind these exact source
refs:

- `read-only-governance-layer-v1`
- `write-side-precondition-checker-v1`
- `write-side-precondition-ci-v1`
- `write-side-recovery-spec-only-v1`
- `restore-dry-run-read-only-stack-v1`
- `preflight-read-only-stack-v1`
- `execution-authorization-read-only-stack-v1`
- `executor-precondition-read-only-stack-v1`
- `write-path-read-only-stack-v1`
- `repository-uow-allowlist-read-only-stack-v1`

The object must fail closed on any missing, malformed, stale, ambiguous,
unresolved, target-mismatched, or commit-mismatched source binding.

## 7. Operation bindings

A future `EvidenceAuditAppendContractV1` object must bind these exact
operation fields:

- `approved_task_id`
- `approved_operation_kind`
- `idempotency_key`
- `projected_action`
- `projected_evidence_ref`
- `target_artifact_id`
- `target_task_id`
- `human_approval_ref`
- `operator_confirmation_ref`
- `execution_authorization_validator_ci_ref`
- `executor_precondition_validator_ci_ref`
- `write_path_contract_validator_ci_ref`
- `repository_uow_allowlist_validator_ci_ref`
- `append_contract_ref`
- `append_idempotency_key`
- `evidence_ref_set`
- `audit_ref_set`

The object must fail closed on derived, inferred, partial, best-effort,
target-ambiguous, stale, or binding-mismatched operation fields.

## 8. Append phase declarations

A future `EvidenceAuditAppendContractV1` object must declare these exact
append phase requirements:

- `before_evidence_required`
- `mutation_intent_evidence_required`
- `after_evidence_required`
- `rejection_evidence_policy_required`
- `failure_evidence_policy_required`
- `rollback_evidence_policy_required`
- `audit_event_required`
- `deterministic_append_order_required`
- `final_append_set_declaration_required`

These fields are declarations only. They do not capture evidence, create
evidence refs, append evidence, create audit events, append audit records, or
execute mutation.

## 9. Evidence categories

A future `EvidenceAuditAppendContractV1` object must declare these exact
evidence categories:

- `before_evidence`
- `mutation_intent_evidence`
- `after_evidence`
- `rejection_evidence`
- `failure_evidence`
- `rollback_evidence`
- `incident_evidence`
- `post_mutation_append_failure_evidence`

The categories are vocabulary and validation targets only. They do not create
evidence artifacts and do not authorize an evidence service call.

## 10. Audit categories

A future `EvidenceAuditAppendContractV1` object must declare these exact audit
categories:

- `write_attempt_audit`
- `append_set_declaration_audit`
- `rejection_audit`
- `failure_audit`
- `rollback_audit`
- `duplicate_replay_audit`
- `ambiguous_replay_audit`
- `incident_audit`

The categories are vocabulary and validation targets only. They do not create
audit artifacts and do not authorize an audit append implementation.

## 11. Deterministic append ordering

A future `EvidenceAuditAppendContractV1` object must declare this
deterministic ordering as contract-only:

1. validate read-only prerequisites
2. bind operation refs
3. declare append idempotency key
4. declare before evidence
5. declare mutation intent evidence
6. keep mutation execution unauthorized
7. declare after evidence
8. declare audit event
9. declare rejection/failure/rollback evidence policies
10. declare final append set
11. keep all append execution unauthorized

This order is not executable. It grants no mutation authority and no append
authority.

## 12. Append idempotency binding

`append_idempotency_key` must bind to the same source and operation frame as
the future append declaration.

The binding must include:

- `approved_task_id`
- `approved_operation_kind`
- `idempotency_key`
- `projected_action`
- `projected_evidence_ref`
- `target_artifact_id`
- `target_task_id`
- `human_approval_ref`
- `operator_confirmation_ref`
- `execution_authorization_validator_ci_ref`
- `executor_precondition_validator_ci_ref`
- `write_path_contract_validator_ci_ref`
- `repository_uow_allowlist_validator_ci_ref`
- `append_contract_ref`
- `evidence_ref_set`
- `audit_ref_set`

The append idempotency key binding must fail closed on missing fields,
ambiguous refs, duplicate different binding, or stale source refs.

## 13. Evidence/audit reference binding

`evidence_ref_set` and `audit_ref_set` are reference sets only.

Each ref set must be bounded, deterministic, JSON-safe, and tied to
`append_contract_ref` and `append_idempotency_key`.

Evidence refs must not be fabricated from mutation success claims.

Audit refs must not be fabricated from write attempt claims.

No evidence ref or audit ref may imply that evidence append or audit append has
already occurred unless a later separately authorized implementation produces
that ref under a frozen append path.

## 14. Transaction boundary declaration

This specification declares append obligations that a future transaction
contract must account for. It does not start a transaction.

This specification opens no DB, starts no Unit of Work, imports no repository,
imports no Unit of Work, begins no sqlite transaction, commits nothing, and
rolls back nothing.

A future authorized path must keep transaction ownership kernel-owned and must
not let append contracts create uncontrolled nested transactions.

## 15. Rollback and failure interaction

Expected rejection is a governed refusal before mutation and must not be
reported as mutation success.

Unexpected failure is not expected rejection. It must fail closed and, in a
future executable path, require rollback of the mutation boundary.

Rollback evidence is a required future declaration for rollback-class paths. It
does not authorize evidence capture, evidence append, audit append, or rollback
execution.

Rollback failure is incident-class and must not be hidden as success, expected
rejection, duplicate replay, or ordinary failure.

## 16. Post-mutation append failure policy

Post-mutation append failure is a future incident-class condition in which a
mutation has already occurred but required evidence or audit append did not
complete.

This specification does not authorize any mutation that could create this
state.

A future implementation must not silently treat post-mutation append failure as
success, expected rejection, duplicate replay, or clean rollback.

Post-mutation append failure requires explicit incident evidence and incident
audit classification by a future separately authorized package.

## 17. Incident classification

A future `EvidenceAuditAppendContractV1` object must classify these failure and
replay states:

- expected rejection
- unexpected failure
- post-mutation append failure
- rollback evidence
- rollback failure
- duplicate append classification
- ambiguous append classification
- duplicate same binding
- duplicate different binding
- append idempotency key binding

Expected rejection is not mutation.

Unexpected failure is not rejection.

Duplicate same binding may be replay-safe only when the full source,
operation, append idempotency, evidence ref, and audit ref bindings match.

Duplicate different binding must fail closed.

Ambiguous append classification must fail closed.

## 18. Service boundary exclusion

This specification excludes all service integration.

Forbidden service surfaces include:

- evidence service
- approval service
- review service
- revision seal service
- hidden service side effects
- service-backed evidence artifact creation
- service-backed audit artifact creation

This specification calls no service and authorizes no future service call.

## 19. DB/repository/UoW boundary exclusion

This specification excludes all DB, repository, and Unit of Work access.

Forbidden DB/repository/UoW surfaces include:

- DB open
- DB write
- repository/UoW import
- repository/UoW call
- repository/UoW write
- repository/UoW transaction ownership
- hidden repository/UoW side effects

This specification opens no DB, imports no repository or Unit of Work, calls no
repository or Unit of Work, and changes no DB/repository/UoW behavior.

## 20. Direct SQL/raw sqlite exclusion

This specification excludes direct SQL and raw sqlite.

Forbidden low-level DB surfaces include:

- direct SQL
- ad hoc SQL
- raw sqlite
- raw cursor execution
- raw connection access
- sqlite transaction control
- schema inspection through a runtime DB

This exclusion applies even to read-only SQL. No direct SQL or raw sqlite path
is authorized by this spec.

## 21. Runtime allowlist/checker exclusion

This specification adds no runtime allowlist.

This specification adds no checker.

This specification adds no validator.

This specification adds no CI consumer.

Future runtime allowlist, checker, validator, or CI consumer packages require
separate design, implementation authorization, tests, and checkpoint review.

## 22. Executor/restore exclusion

This specification adds no executor and no restore path.

It does not authorize executor implementation, restore execution, restore CLI,
write-side recovery execution, mutation execution, rollback execution, or
irreversible action.

Any attempt to use this append contract as executor or restore authority fails
closed.

## 23. CLI exclusion

This specification adds no CLI command and expands no existing CLI behavior.

No CLI may create, validate, append, replay, repair, migrate, execute, restore,
or dispatch from this specification.

## 24. Schema/migration exclusion

This specification adds no schema and no migration.

It does not create evidence tables, audit tables, idempotency tables, incident
tables, repository tables, Unit of Work metadata, indexes, triggers, or
migration fixtures.

Schema and migration authority remains false.

## 25. Daemon/server/queue exclusion

This specification adds no daemon, server, queue, async worker, background job,
timer, scheduler, subscriber, webhook, or network listener.

No durable append, replay, retry, incident processing, restore dispatch, or
write-side execution may be moved into a daemon/server/queue surface by this
specification.

## 26. Required false authorization flags

A future `EvidenceAuditAppendContractV1` object must declare these flags
exactly false:

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

## 27. JSON safety

A future `EvidenceAuditAppendContractV1` object must be JSON-safe.

It must contain only bounded strings, booleans, arrays, and objects that can be
serialized deterministically without runtime repr leakage, DB handles, service
handles, repository objects, Unit of Work objects, exception objects, path
objects, cursors, connections, callables, generators, or arbitrary class
instances.

JSON safety is a future read-only validation requirement. It is not an append
implementation.

## 28. Future validator requirements

A future validator package must satisfy all of the following:

- pure read-only validator over already-rendered `EvidenceAuditAppendContractV1`
- exact source bindings
- exact operation bindings
- exact append phase declarations
- exact evidence/audit categories
- exact deterministic ordering
- exact idempotency/ref bindings
- false authorization flags
- JSON safety
- no service/DB/repository/UoW calls
- no evidence/audit append

The validator must fail closed on missing, malformed, stale, mismatched,
ambiguous, unordered, non-JSON-safe, or unauthorized true declarations.

This specification does not add that validator.

## 29. Future CI consumer requirements

A future CI consumer package must satisfy all of the following:

- pure read-only CI consumer over already-rendered validator output
- no validator import/call
- no service/DB/repository/UoW calls
- no append execution
- false flags preserved
- bounded JSON-safe output

The CI consumer must fail closed on malformed validator output, ambiguous
status, missing false flags, unauthorized true flags, unbounded output, or
runtime-object leakage.

This specification does not add that CI consumer.

## 30. Future implementation eligibility requirements

Future evidence/audit append implementation is ineligible until separate
packages have been designed, audited, implemented, validated, and frozen for:

- `EvidenceAuditAppendContractV1` validator
- `EvidenceAuditAppendContractV1` CI consumer
- evidence service boundary
- audit append boundary
- repository/UoW write boundary
- transaction boundary
- idempotency boundary
- incident classification boundary
- executor design audit

Even after those packages exist, implementation remains unauthorized unless a
later explicit governance decision grants that authority. Readiness is not
authorization.

## 31. Forbidden surfaces

The following surfaces are forbidden by this specification:

- no evidence append implementation
- no audit append implementation
- no evidence service call
- no approval service call
- no review service call
- no revision seal service call
- no DB open
- no DB write
- no repository/UoW import
- no repository/UoW call
- no direct SQL
- no raw sqlite
- no runtime allowlist
- no checker
- no executor
- no restore
- no restore CLI
- no schema/migration
- no daemon/server/queue
- no external network
- no filesystem side channel
- no irreversible action

This list grants no exception. Any future request into one of these surfaces
requires separate authorization.

## 32. Acceptance requirements

This package is acceptable only if all of the following remain true:

- exactly one new governance spec document
- no production code
- no tests unless explicitly required by existing convention
- no validator/checker/CI
- no evidence/audit append
- no service calls
- no DB/repository/UoW changes
- no CLI
- no schema/migration
- no daemon/server/queue
- all frozen refs resolve
- health checks green
- working tree clean
- candidate tag absent

Acceptance of this spec-only package does not authorize evidence append, audit
append, durable writes, service calls, DB/repository/UoW access, executor
implementation, restore execution, CLI expansion, schema changes,
daemon/server/queue execution, DB repair, or irreversible action.

## 33. Freeze criteria

Freeze of `evidence-audit-append-contract-spec-only-v1` requires:

- exactly one added file:
  `governance/specs/evidence_audit_append_contract_spec_only_design_v1.md`
- no production code changes
- no test changes
- no existing governance doc changes
- no validator
- no checker
- no CI consumer
- no evidence append
- no audit append
- no service calls
- no DB access
- no repository or Unit of Work access
- no runtime allowlist
- no executor
- no restore
- no CLI
- no schema or migration
- no daemon, server, queue, async worker, or background execution
- no DB repair
- no durable writes
- no irreversible action
- false authorization flags preserved
- all governing baseline tags resolve to the pinned commits
- candidate tag `evidence-audit-append-contract-spec-only-v1` is absent before
  freeze
- repository health checks pass
- working tree is clean after commit

Freeze is a checkpoint recommendation only. It does not authorize
implementation, execution, append, DB, service, repository/UoW, CLI,
schema/migration, daemon/server/queue, DB repair, durable write, or
irreversible action.
