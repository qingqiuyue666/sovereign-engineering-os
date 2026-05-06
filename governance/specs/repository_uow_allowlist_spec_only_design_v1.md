# Repository/UoW Allowlist Spec-Only Design V1

Contract name: `RepositoryUoWAllowlistV1`

## 1. Purpose and Non-Authority

- This is governance specification only.
- It authorizes no runtime behavior.
- It authorizes no DB writes.
- It authorizes no repository/UoW writes.
- It authorizes no executor.
- It authorizes no restore.
- It authorizes no CLI.
- It authorizes no evidence/audit append.
- It authorizes no service calls.
- It only defines the future allowlist model.

This document is a frozen governance artifact. It does not introduce, alter,
or enable any production behavior. It defines vocabulary and constraints that
a future allowlist validator, allowlist checker, allowlist CI consumer, and
eventual executor design audit will be required to honor. Until each of those
downstream artifacts is independently designed, audited, and frozen, no
runtime authority of any kind is conferred by this specification.

## 2. Governing Baselines

The following frozen baselines govern this spec. The pinned commit SHAs are
binding; the spec is invalid if any of these tags are moved or rewritten.

- `read-only-governance-layer-v1`
  - `4656e8f03404c6bb39e7976c6165e3d7dc0314fb`
- `write-side-precondition-checker-v1`
  - `fd5788c7a4d3ed953fbc0295414ba7e6ad4f89f6`
- `write-side-precondition-ci-v1`
  - `05c81541ad3d7deee20023843142f702937f6c3f`
- `write-side-recovery-spec-only-v1`
  - `ad560cc2dab135f2c1d56d948410ae47586d118e`
- `restore-dry-run-read-only-stack-v1`
  - `e7c78e3ff0c5dc05806c293f01ab32cd33c9518b`
- `preflight-read-only-stack-v1`
  - `662b6161253c35204b437e88809c5bab21908c6d`
- `execution-authorization-read-only-stack-v1`
  - `d586aeb60620010c900df7be1a88621ab2cb8dc1`
- `executor-precondition-read-only-stack-v1`
  - `cb3948eb843866dcc961b6a074038c13db64d017`
- `write-path-read-only-stack-v1`
  - `8ffd4679aca8f593415089748df35df42af8f015`

## 3. Relationship to Write Path Read-Only Stack

- This spec sits after `write-path-read-only-stack-v1`.
- The write-path stack proves only read-only structural readiness.
- This spec does not convert readiness into write authority.
- Future executor cannot exist until allowlist spec, allowlist validator,
  allowlist CI, evidence/audit append contract, and executor design audit
  are frozen.

Read-only structural readiness means only that upstream contracts agree on
what a hypothetical write attempt would look like as data; it does not mean
that any write attempt may proceed. The transition from "readiness data
exists" to "a write may execute" is intentionally gated by additional
artifacts that have not been authored, audited, or frozen.

## 4. Repository/UoW Threat Model

The following threats motivate the allowlist:

- direct SQL bypass
- raw connection access
- arbitrary repository method access
- executor-owned transactions
- nested transaction ambiguity
- hidden writes through services
- evidence-free mutations
- idempotency-free mutations
- rollback-unsafe mutations
- schema/migration drift
- filesystem side channels
- external network side effects

Each of the above threats is explicitly excluded from any future authorized
write surface. Mitigations are described as constraints across the remaining
sections; this section is the canonical enumeration of threats addressed.

## 5. Forbidden Surfaces

The following surfaces are explicitly forbidden under this spec:

- executor implementation
- restore execution
- restore CLI
- direct DB writes
- raw sqlite access
- ad hoc SQL
- repository methods not allowlisted
- repository/UoW writes now
- schema/migration
- DB repair
- daemon/server/queue
- approval service
- review service
- revision seal service
- evidence service
- evidence/audit append
- recovery gate/session host/orchestrator
- filesystem side channels
- external network calls
- irreversible actions

This list is exhaustive for the purposes of this spec. Any future request to
build into one of these surfaces requires a separate, independently frozen
governance artifact.

## 6. Direct SQL Prohibition

- no direct SQL from executor
- no direct SQL from allowlist validator/checker
- no ad hoc SQL
- no raw cursor execution
- no schema inspection through runtime DB
- future DB access can only occur through explicitly allowlisted
  repository/UoW surface and only after separate authorization

The prohibition holds regardless of whether SQL would be read-only or
mutating. Schema reflection, pragma queries, and exploratory inspection are
all included in the prohibition for the executor and for any allowlist
validator/checker.

## 7. Raw Connection Prohibition

- no raw sqlite connection use by executor
- no raw sqlite connection use by allowlist validator/checker
- no direct connection/cursor handle exposure
- no connection escaping from UnitOfWork
- no direct transaction control by executor

Raw connection handles, cursor handles, and any equivalent low-level driver
object must never be exposed across the executor or allowlist boundary. The
UnitOfWork is the only legitimate carrier of transactional context, and it is
not granted any executable authority by this spec.

## 8. Repository Method Allowlist Model

A future method declaration object under `RepositoryUoWAllowlistV1` shall
declare each candidate repository or UoW-bound method by the following
fields:

- repository_class
- method_name
- method_owner
- read_write_classification
- allowed_for_executor
- allowed_for_restore
- allowed_for_write_side_recovery
- required_uow_context
- required_transaction_owner
- required_idempotency_binding
- required_evidence_output_fields
- required_mutation_summary_fields
- rollback_behavior
- allowed_failure_modes
- forbidden_side_effects
- json_safe_result_required
- filesystem_side_effects_forbidden
- external_network_forbidden
- services_forbidden
- schema_migration_forbidden
- db_repair_forbidden

Allowlist scope rules:

- methods not listed are forbidden
- class-level allow is insufficient
- module-level allow is insufficient
- wildcard methods are forbidden
- dynamically resolved method names are forbidden
- private/internal methods are forbidden unless separately named and justified

The allowlist is therefore strictly enumerated. No pattern, prefix, glob,
package allowance, or class-wide allowance may be used to admit methods.

## 9. Read/Write Classification

Each declared method must carry one of:

- `read_only`
- `mutation_declared_but_not_authorized`
- `future_write_candidate`

Semantics:

- no write classification grants execution authority
- `future_write_candidate` means candidate for future executor design review
  only
- `mutation_declared_but_not_authorized` still cannot run

`read_only` classification likewise does not grant execution authority under
this spec; it only constrains the future shape of an allowed method.

## 10. UoW Boundary Model

- exactly one outer kernel-owned UoW boundary per future execution attempt
- executor must not own commit/rollback
- uncontrolled nested UoW is forbidden
- repositories must not escape UoW boundary
- UoW cannot be created by random helper code
- no long-lived UoW across attempts
- no UoW across daemon/server/queue boundary

The UoW is, in the future executable design, owned by the kernel. Any
attempt by an executor, service, helper, or background process to start,
extend, or share a UoW falls outside this spec.

## 11. Transaction Ownership Model

- future transaction ownership is kernel-owned
- executor is a participant, not transaction owner
- commit/rollback policy must be decided by future
  transaction/evidence executor contract
- nested transaction requires explicit future exception
- rollback failure is incident-class

Transaction ownership cannot be implied from method participation. Only the
kernel-owned UoW boundary may begin or end a transaction. Rollback failure
is treated as an incident-class event for future incident contracts to
define.

## 12. Evidence-Bearing Return Contract

Future allowed repository methods must return bounded JSON-safe
evidence-bearing fields:

- target_artifact_id
- target_task_id
- mutation_summary
- affected_rows_or_entities
- before_ref
- after_ref_requirement
- journal_ref_requirement
- idempotency_key
- operation_kind
- result_classification

Constraints:

- this is declaration only
- no evidence append authorized
- evidence/audit append remains separate future contract

Field shapes and field semantics must be JSON-safe and bounded. The presence
of these fields in a return type does not, on its own, authorize anything to
be written, appended, or persisted.

## 13. Mutation Summary Contract

Each future allowed mutation method must declare a mutation summary with:

- mutation_summary_required
- changed_entity_types
- changed_entity_ids
- before_state_ref_or_reason
- after_state_ref_or_requirement
- expected_rejection_summary
- unexpected_failure_summary
- rollback_summary_requirement

Constraints:

- mutation summary is not evidence append
- mutation summary does not authorize write

The mutation summary is a structural artifact for future contracts to
consume. It is not, and may not become, a substitute for a frozen evidence
append contract.

## 14. Idempotency Interaction

- future write methods require idempotency key binding
- idempotency reservation remains unimplemented
- allowlist does not reserve keys
- allowlist does not check replay DB
- duplicate handling remains future contract

The allowlist binds method declarations to idempotency requirements but does
not itself reserve, check, or replay any keys.

## 15. Rollback Interaction

- repository/UoW methods must declare rollback behavior
- rollback runtime is not implemented
- rollback failure incident path remains future contract
- no partial success allowed
- no ambiguous success allowed

Each declared method must specify its rollback behavior. The actual runtime
rollback path, including its failure incident handling, remains
unauthorized and undefined under this spec.

## 16. Schema/Migration Exclusion

- schema migration forbidden
- DB repair forbidden
- migration helpers excluded from allowlist
- repair helpers excluded from allowlist
- schema inspection through runtime DB forbidden for this path

No schema-altering, repair-oriented, or migration-oriented method may be
present on the allowlist now or under this spec. Such methods require an
entirely separate governance path.

## 17. Service Boundary Exclusion

- approval/review/revision/evidence services remain forbidden
- services may create hidden artifacts or side effects
- future service integration requires separate contract

No method that calls, wraps, or proxies an approval, review, revision seal,
or evidence service may appear on the allowlist under this spec.

## 18. Restore/Recovery Exclusion

- recovery gate/session host/orchestrator surfaces remain forbidden
- restore execution remains unauthorized
- restore CLI remains unauthorized
- restore dry-run stack remains read-only only

The restore dry-run stack remains strictly read-only. No restore execution,
recovery execution, recovery gate, session host, or orchestrator surface may
be admitted by the allowlist now.

## 19. Filesystem Side-Channel Exclusion

- executor cannot write filesystem side channels
- repository methods cannot emit unmanaged files
- no ad hoc artifact files
- no temp-file mutation side effects
- no external network writes

All filesystem side channels and external network writes are categorically
excluded from any allowlisted future method.

## 20. Future Validator/Checker Requirements

A future allowlist validator/checker:

- consumes already-rendered `RepositoryUoWAllowlistV1` declaration only
- no DB open
- no repository calls
- no UoW calls
- no services
- no filesystem writes
- no evidence append
- no upstream runtime calls
- JSON-safe output only
- all authorization flags false

The validator/checker is a pure data validator over a rendered declaration.
It performs no runtime introspection of the application and grants no
authority.

## 21. Future CI Consumer Requirements

A future CI consumer of the allowlist:

- consumes already-rendered allowlist validator/checker output only
- does not call validator/checker
- does not open DB
- does not call services
- does not authorize writes
- keeps false flags false

The CI consumer reads only the already-rendered output of the
validator/checker. It runs no validator/checker logic itself and changes no
authorization state.

## 22. Required False Authorization Flags

Any future rendered declaration under `RepositoryUoWAllowlistV1` must carry
the following flags, each set to `false`:

- executor_implementation_authorized: false
- restore_execution_authorized: false
- write_side_recovery_authorized: false
- cli_execution_authorized: false
- schema_migration_authorized: false
- daemon_server_queue_authorized: false
- db_repair_authorized: false
- repository_uow_writes_authorized: false
- direct_db_writes_authorized: false
- raw_sqlite_authorized: false
- ad_hoc_sql_authorized: false
- evidence_append_authorized: false
- audit_append_authorized: false
- approval_service_authorized: false
- review_service_authorized: false
- revision_seal_service_authorized: false
- evidence_service_authorized: false
- filesystem_side_effects_authorized: false
- external_network_authorized: false
- durable_writes_authorized: false
- irreversible_action_authorized: false

These flags must remain `false` under this spec and under all future
validator/checker and CI consumer artifacts derived from this spec.

## 23. Acceptance Requirements

- one new spec document only
- no production code changes
- no tests changed unless required by repository convention
- all current tests green
- git diff check clean
- no authorization language granting writes
- all forbidden surfaces listed
- all baseline refs pinned

## 24. Freeze Criteria

- PR merged
- candidate tag absent before tag
- all target tags resolve
- working tree clean
- tests green
- exactly one spec file changed
- no production/test/schema/service/repo/UoW changes
- no runtime authorizations granted

Candidate future tag after merge: `repository-uow-allowlist-spec-only-v1`.
