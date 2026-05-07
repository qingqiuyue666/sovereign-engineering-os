# Service Method Authority Contract Spec-Only Design V1

Status: draft for human review

Canonical target filename:
`governance/specs/service_method_authority_contract_spec_only_design_v1.md`

Tag candidate: `service-method-authority-contract-spec-only-v1`

Contract object: `ServiceMethodAuthorityContractV1`

## 1. Purpose

This spec defines the future governance contract object
`ServiceMethodAuthorityContractV1`.

This spec is non-executable.

`ServiceMethodAuthorityContractV1` is a declaration-only authority contract for
future service method eligibility review. It is not production code, not a
test, not a validator, not a checker, not a CI consumer, not a service adapter,
not a service method call site, not an evidence or audit append path, not DB or
repository/UoW access, not transaction runtime, not idempotency reservation
runtime, not rollback runtime, not executor, not restore, not CLI, not schema
or migration logic, and not daemon/server/queue logic.

This spec exists because service adapter boundary readiness does not authorize
runtime. Runtime is not authorized. Service calls are not authorized. Readiness
is not authorization. Authorization is not execution. Default deny and fail
closed remain mandatory.

## 2. Non-Authority Clause

This spec grants no service adapter runtime authority.

This spec grants no service method call authority.

This spec grants no evidence service authority.

This spec grants no approval service authority.

This spec grants no review service authority.

This spec grants no revision seal service authority.

This spec grants no audit service authority.

This spec grants no evidence append authority.

This spec grants no audit append authority.

This spec grants no runtime append authority.

This spec grants no DB/repository/UoW write authority.

This spec grants no transaction runtime authority.

This spec grants no idempotency reservation runtime authority.

This spec grants no rollback runtime authority.

This spec grants no runtime allowlist/checker/enforcer authority.

This spec grants no executor authority.

This spec grants no restore authority.

This spec grants no CLI/schema/daemon authority.

This spec grants no durable write authority.

This spec grants no irreversible action authority.

Any attempt to treat this spec as service call authority, service adapter
runtime authority, evidence/audit append authority, DB/repository/UoW write
authority, durable write authority, or irreversible action authority fails
closed.

## 3. Source Bindings

`ServiceMethodAuthorityContractV1` is source-bound to the following frozen
checkpoints. These bindings are invalid if any tag is missing, moved, rewritten,
ambiguous, unresolved, stale, or commit-mismatched.

```text
source_read_only_governance_layer_tag = read-only-governance-layer-v1
source_read_only_governance_layer_commit = 4656e8f03404c6bb39e7976c6165e3d7dc0314fb
source_write_side_precondition_checker_tag = write-side-precondition-checker-v1
source_write_side_precondition_checker_commit = fd5788c7a4d3ed953fbc0295414ba7e6ad4f89f6
source_write_side_precondition_ci_tag = write-side-precondition-ci-v1
source_write_side_precondition_ci_commit = 05c81541ad3d7deee20023843142f702937f6c3f
source_write_side_recovery_spec_only_tag = write-side-recovery-spec-only-v1
source_write_side_recovery_spec_only_commit = ad560cc2dab135f2c1d56d948410ae47586d118e
source_restore_dry_run_read_only_stack_tag = restore-dry-run-read-only-stack-v1
source_restore_dry_run_read_only_stack_commit = e7c78e3ff0c5dc05806c293f01ab32cd33c9518b
source_preflight_read_only_stack_tag = preflight-read-only-stack-v1
source_preflight_read_only_stack_commit = 662b6161253c35204b437e88809c5bab21908c6d
source_execution_authorization_read_only_stack_tag = execution-authorization-read-only-stack-v1
source_execution_authorization_read_only_stack_commit = d586aeb60620010c900df7be1a88621ab2cb8dc1
source_executor_precondition_read_only_stack_tag = executor-precondition-read-only-stack-v1
source_executor_precondition_read_only_stack_commit = cb3948eb843866dcc961b6a074038c13db64d017
source_write_path_read_only_stack_tag = write-path-read-only-stack-v1
source_write_path_read_only_stack_commit = 8ffd4679aca8f593415089748df35df42af8f015
source_repository_uow_allowlist_read_only_stack_tag = repository-uow-allowlist-read-only-stack-v1
source_repository_uow_allowlist_read_only_stack_commit = bec2d04eab1922594dcbfbe35971f4efe0fe4849
source_evidence_audit_append_read_only_stack_tag = evidence-audit-append-read-only-stack-v1
source_evidence_audit_append_read_only_stack_commit = 62db8a586efa9375d2c77cf7c6335ccf5ef11279
source_append_runtime_authority_service_boundary_read_only_stack_tag = append-runtime-authority-service-boundary-read-only-stack-v1
source_append_runtime_authority_service_boundary_read_only_stack_commit = bda430a6a8d1e1dbede2adb9594baa1ab5cf2039
source_service_adapter_boundary_read_only_stack_tag = service-adapter-boundary-read-only-stack-v1
source_service_adapter_boundary_read_only_stack_commit = 8698ea42c78cbe79231698be8839b9d2c246cfdf
```

These source bindings provide governance vocabulary and bounded source evidence
only. They do not grant service adapter runtime authority, service method call
authority, evidence/audit append authority, DB/repository/UoW write authority,
durable write authority, or irreversible action authority.

## 4. Service Identity Model

The service identity set is closed and exact. A future
`ServiceMethodAuthorityContractV1` declaration may refer only to these service
identities:

```text
evidence_service
approval_service
review_service
revision_seal_service
audit_service_future_adapter
```

No other service identity is valid. Unnamed services are forbidden. Aliased
service identities are forbidden. Dynamic service resolution is forbidden.
Wildcard service identity authority is forbidden. Service identity presence is
declaration only and does not authorize a service call.

## 5. Exact Service Method Authority Model

Each future service method authority declaration must bind all of the following
fields exactly:

- exact service identity
- exact service class name
- exact service method name
- exact operation kind
- exact authority scope
- exact phase
- exact input contract ref
- exact output contract ref
- exact idempotency binding ref
- exact transaction placement ref
- exact failure/incident policy ref
- exact evidence/audit ref binding
- exact authority grant ref
- exact revocation ref

Any missing, malformed, inferred, stale, ambiguous, mismatched, wildcard,
class-level, module-level, or dynamically resolved authority field fails
closed. Exact method authority remains declaration-only until a later
separately authorized runtime package exists.

## 6. Service Method Allowlist Declaration Model

A future service method allowlist declaration must enumerate each eligible
method independently. The declaration model forbids:

- wildcard method authority
- class-level authority
- module-level authority
- dynamic service resolution
- runtime method lookup
- reflection-based method discovery
- inferred method authority
- service object passthrough
- raw callable passthrough

Method authority cannot be inherited from service identity, service class,
module, package, validator success, CI success, tag existence, or read-only
stack readiness. The allowlist is a future declaration model only. This spec
does not add a runtime allowlist, checker, enforcer, validator, CI consumer, or
service adapter implementation.

## 7. Service Result Contract Model

A future service result contract must require:

- bounded JSON-safe mapping
- deterministic output shape
- explicit success/failure state
- explicit reason code
- explicit failure taxonomy
- no service objects
- no DB handles
- no repository/UoW handles
- no exception objects
- no raw repr
- no file/network/socket handles
- no raw service result passthrough
- no implicit append success
- no implicit audit emission
- no fabricated evidence/audit refs
- no success if required evidence/audit refs are missing

A malformed, unbounded, nondeterministic, non-JSON-safe, handle-bearing,
repr-leaking, ref-missing, ref-mismatched, append-ambiguous, audit-ambiguous,
or success-ambiguous result fails closed. The result contract is data-only and
does not authorize a service call or append outcome.

## 8. Service Idempotency / Replay Model

A future service call must declare idempotency binding before any future side
effect. The binding must be:

- source-bound idempotency key
- operation-bound idempotency key
- service-identity-bound idempotency key
- method-bound idempotency key
- authority-ref-bound idempotency key
- evidence/audit-ref-bound idempotency key

Replay classification requirements:

- same-key/same-binding safe replay classification only
- same-key/different-binding fail closed
- ambiguous replay incident-class
- no idempotency reservation runtime authorized by this spec

This spec creates no idempotency reservation table, row, repository, UoW,
service, API, lock, lease, or runtime lookup.

## 9. Transaction Placement Model

Future runtime must declare transaction placement before any service method can
be considered. The transaction placement model requires:

- kernel-owned transaction for future runtime
- service must not own transaction by default
- service must not commit
- service must not rollback
- uncontrolled nested transactions forbidden
- in-transaction service call requires explicit future authority
- out-of-band service call requires explicit future policy
- commit only after required bookkeeping
- rollback on unexpected exception
- rollback failure incident-class
- no transaction runtime authorized by this spec

This spec opens no DB, starts no transaction, commits nothing, rolls back
nothing, and creates no transaction runtime.

## 10. Failure / Incident Model

`ServiceMethodAuthorityContractV1` must define these failure and incident
cases:

- expected rejection
- forbidden service call
- method not allowlisted
- malformed service result
- missing ref
- mismatched ref
- idempotency mismatch
- ambiguous replay
- transaction violation
- post-mutation service failure
- rollback failure
- partial success forbidden
- silent success forbidden
- incident-class conditions
- fail-closed behavior

Required classifications:

- expected rejection is bounded refusal, not execution permission
- forbidden service call fails closed
- method not allowlisted fails closed
- malformed service result fails closed
- missing ref fails closed
- mismatched ref fails closed
- idempotency mismatch fails closed
- ambiguous replay is incident-class
- transaction violation is incident-class
- post-mutation service failure is incident-class
- rollback failure is incident-class
- partial success is forbidden
- silent success is forbidden

No failure or incident classification in this spec authorizes evidence append,
audit append, rollback runtime, durable write, or service recovery action.

## 11. Evidence / Audit Ref Model

Future service method authority must declare evidence and audit refs as refs
only. The ref model requires:

- source-bound refs
- operation-bound refs
- method-bound refs
- authority-bound refs
- JSON-safe refs
- no fabricated refs
- no undeclared refs
- no missing refs
- no mismatched refs
- no implied append success
- no implied audit emission

Evidence and audit refs under this spec are references only. This spec creates
no evidence ref, creates no audit ref, appends no evidence, appends no audit,
and cannot imply that evidence or audit append succeeded.

## 12. Authority Grant Prerequisite Model

Future service method authority requires a separate, source-bound authority
grant before runtime can be discussed. The prerequisite model requires:

- source-bound authority
- operation-bound authority
- service-identity-bound authority
- method-bound authority
- phase-bound authority
- result-contract-bound authority
- idempotency-bound authority
- transaction-placement-bound authority
- failure-policy-bound authority
- evidence/audit-ref-bound authority
- human approval bound authority
- operator confirmation bound authority
- expiration bound authority
- issuer bound authority
- revocation bound authority
- narrow authority only
- no wildcard authority
- no durable authority by default

Authority cannot be broad, permanent, wildcard, class-level, module-level,
service-wide, inferred, or durable by default. A future authority grant must
remain narrower than the operation and method it governs.

## 13. Revocation Model

Future service method authority must include a revocation ref and must fail
closed under each of these conditions:

- revocation ref
- revoked authority fails closed
- expired authority fails closed
- mismatched authority fails closed
- missing authority fails closed
- authority cannot be inferred from read-only validation
- authority cannot be inferred from CI success
- authority cannot be inferred from tag existence

Revocation is a contract prerequisite only. This spec does not implement
revocation storage, revocation lookup, revocation service calls, or revocation
runtime.

## 14. Required False Authority Flags

All of these authority flags must be present as false:

```text
service_adapter_runtime_authorized = false
service_adapter_implementation_authorized = false
service_method_call_authorized = false
service_side_effect_authorized = false
evidence_service_authorized = false
approval_service_authorized = false
review_service_authorized = false
revision_seal_service_authorized = false
audit_service_authorized = false
evidence_append_authorized = false
audit_append_authorized = false
append_runtime_authorized = false
repository_uow_writes_authorized = false
direct_db_writes_authorized = false
raw_sqlite_authorized = false
ad_hoc_sql_authorized = false
transaction_runtime_authorized = false
idempotency_reservation_authorized = false
rollback_runtime_authorized = false
runtime_allowlist_authorized = false
runtime_checker_authorized = false
runtime_enforcer_authorized = false
executor_implementation_authorized = false
restore_execution_authorized = false
write_side_recovery_authorized = false
cli_execution_authorized = false
schema_migration_authorized = false
daemon_server_queue_authorized = false
filesystem_side_effects_authorized = false
external_network_authorized = false
durable_writes_authorized = false
irreversible_action_authorized = false
db_repair_authorized = false
```

These flags are required to remain false. This spec cannot flip any authority
flag true.

## 15. Required True Declarations

All of these declarations must be present as true:

```text
spec_only_non_executable = true
service_adapter_implementation_forbidden = true
service_calls_forbidden = true
evidence_service_call_forbidden = true
approval_service_call_forbidden = true
review_service_call_forbidden = true
revision_seal_service_call_forbidden = true
audit_service_call_forbidden = true
exact_service_identity_required = true
exact_service_class_name_required = true
exact_service_method_name_required = true
exact_operation_kind_required = true
exact_authority_scope_required = true
exact_phase_required = true
service_method_allowlist_required = true
wildcard_method_authority_forbidden = true
class_level_authority_forbidden = true
module_level_authority_forbidden = true
dynamic_service_resolution_forbidden = true
runtime_method_lookup_forbidden = true
reflection_method_discovery_forbidden = true
inferred_method_authority_forbidden = true
service_object_passthrough_forbidden = true
raw_callable_passthrough_forbidden = true
service_result_contract_required = true
service_result_json_safe_required = true
service_result_bounded_required = true
service_result_deterministic_required = true
explicit_success_failure_state_required = true
explicit_reason_code_required = true
explicit_failure_taxonomy_required = true
service_result_no_runtime_handles_required = true
service_result_no_raw_repr_required = true
service_object_leakage_forbidden = true
db_handle_leakage_forbidden = true
repository_uow_handle_leakage_forbidden = true
exception_object_leakage_forbidden = true
filesystem_network_handle_leakage_forbidden = true
raw_service_result_passthrough_forbidden = true
implicit_append_success_forbidden = true
implicit_audit_emission_forbidden = true
fabricated_evidence_audit_refs_forbidden = true
service_idempotency_binding_required = true
service_replay_classification_required = true
same_key_same_binding_safe_replay_only = true
same_key_different_binding_fail_closed = true
ambiguous_replay_incident_class = true
kernel_owned_transaction_required_for_future_runtime = true
service_transaction_ownership_forbidden_by_default = true
service_commit_forbidden = true
service_rollback_forbidden = true
uncontrolled_nested_transaction_forbidden = true
in_transaction_service_call_requires_separate_authority = true
out_of_band_service_call_policy_required = true
commit_after_required_bookkeeping_only = true
rollback_on_unexpected_exception_required = true
rollback_failure_incident_class = true
failure_incident_separation_required = true
partial_success_forbidden = true
silent_success_forbidden = true
evidence_audit_refs_source_bound_required = true
evidence_audit_refs_operation_bound_required = true
evidence_audit_refs_method_bound_required = true
evidence_audit_refs_authority_bound_required = true
evidence_audit_refs_json_safe_required = true
undeclared_ref_forbidden = true
missing_ref_fail_closed = true
mismatched_ref_fail_closed = true
authority_source_bound_required = true
authority_operation_bound_required = true
authority_service_identity_bound_required = true
authority_method_bound_required = true
authority_phase_bound_required = true
authority_result_contract_bound_required = true
authority_idempotency_bound_required = true
authority_transaction_placement_bound_required = true
authority_failure_policy_bound_required = true
authority_evidence_audit_ref_bound_required = true
authority_human_approval_bound_required = true
authority_operator_confirmation_bound_required = true
authority_expiration_bound_required = true
authority_issuer_bound_required = true
authority_revocation_bound_required = true
authority_narrow_required = true
wildcard_authority_forbidden = true
durable_authority_forbidden_by_default = true
revoked_authority_fails_closed = true
expired_authority_fails_closed = true
mismatched_authority_fails_closed = true
missing_authority_fails_closed = true
read_only_validation_does_not_imply_authority = true
ci_success_does_not_imply_authority = true
tag_existence_does_not_imply_authority = true
future_validator_required = true
future_ci_required = true
```

These declarations are governance requirements only. They do not create a
validator, checker, CI consumer, service adapter, runtime, append path, DB
path, executor, restore path, CLI, schema, migration, daemon, server, queue,
durable write, or irreversible action.

## 16. JSON Safety Requirements

Contract declaration must be JSON-safe.

Future validator output must be JSON-safe.

Future CI output must be JSON-safe.

Future service adapter result must be JSON-safe.

No runtime repr leakage.

No object handles.

No exception objects.

No file/network/socket handles.

No DB/repository/UoW handles.

Any non-JSON-safe value, object handle, exception object, runtime repr, DB
handle, repository/UoW handle, file handle, network handle, socket handle, or
raw service object fails closed.

## 17. Future Validator Requirements

A future validator must consume already-rendered
`ServiceMethodAuthorityContractV1` only.

A future validator must not call services.

A future validator must not open DB.

A future validator must not import repository/UoW.

A future validator must not append evidence/audit.

A future validator must not implement transaction/idempotency/rollback/runtime.

A future validator must not authorize service calls.

A future validator must keep all authority flags false.

Future validator scope is read-only validation over an already-rendered
contract declaration. This spec does not add a validator.

## 18. Future CI Requirements

A future CI consumer must consume already-rendered validator output only.

A future CI consumer must not import/call validator.

A future CI consumer must not call services.

A future CI consumer must not open DB.

A future CI consumer must not import repository/UoW.

A future CI consumer must not append evidence/audit.

A future CI consumer must not implement transaction/idempotency/rollback/runtime.

A future CI consumer must not authorize service calls.

A future CI consumer must keep all authority flags false.

Future CI scope is read-only consumption of already-rendered validator output.
This spec does not add a CI consumer.

## 19. Acceptance Requirements

Acceptance requires:

- exactly one new governance spec file
- no production code
- no tests
- no existing files changed
- all existing health checks green
- git diff --check clean
- working tree clean after commit
- candidate tag absent before implementation
- spec includes ServiceMethodAuthorityContractV1
- spec includes all required false authority flags
- spec includes all required true declarations
- spec explicitly says runtime is not authorized

Acceptance must stop if it requires service calls, DB access,
repository/UoW access, evidence/audit append, transaction runtime, idempotency
reservation runtime, rollback runtime, validator/CI implementation,
executor/restore implementation, CLI/schema/migration work, daemon/server/queue
work, existing file modification, or true authorization flags.

## 20. Freeze Criteria

Freeze requires:

- PR merged on main
- candidate tag absent locally and on origin before freeze
- first-parent diff exactly one added governance spec file
- no production code changes
- no tests changed
- no existing governance docs changed
- all required source bindings still resolve to the pinned commits
- all existing health checks green
- git diff --check clean
- no runtime authorization granted
- no service method calls authorized
- no evidence/audit append authorized
- no DB/repository/UoW writes authorized
- stop/consolidate audit recommends tag

The candidate freeze tag is `service-method-authority-contract-spec-only-v1`.
The tag must not be created by this implementation PR. It may only be
recommended by a later stop/consolidate audit after the PR merges on main and
the first-parent diff proves exactly one spec-only governance file.
