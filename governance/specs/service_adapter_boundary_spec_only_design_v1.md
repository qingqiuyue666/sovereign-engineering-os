# Service Adapter Boundary Spec-Only Design V1

Status: draft for human review

Canonical target filename: `governance/specs/service_adapter_boundary_spec_only_design_v1.md`

Tag candidate: `service-adapter-boundary-spec-only-v1`

Contract object: `ServiceAdapterBoundaryV1`

## 1. Purpose and Non-Authority

This is a governance-only boundary contract.

This defines future service adapter boundary requirements.

`ServiceAdapterBoundaryV1` is a non-executable governance declaration for a
future service adapter boundary. It is not production code, not a test, not a
validator, not a checker, not a CI consumer, not a service adapter, not a
service call site, not an append implementation, not an executor, not restore,
not CLI, not schema or migration logic, not daemon/server/queue logic, and not
DB repair.

This does not authorize service calls.

This does not authorize service adapter runtime.

This does not authorize evidence service calls.

This does not authorize approval service calls.

This does not authorize review service calls.

This does not authorize revision seal service calls.

This does not authorize audit service calls.

This does not authorize evidence append.

This does not authorize audit append.

This does not authorize runtime append.

This does not authorize DB/repository/UoW writes.

This does not authorize transaction runtime.

This does not authorize idempotency reservation runtime.

This does not authorize rollback runtime.

This does not authorize executor.

This does not authorize restore.

This does not authorize CLI/schema/daemon.

This does not create service adapter implementation.

Readiness is not authorization.

Authorization is not execution.

Default deny and fail closed remain mandatory.

## 2. Source Bindings

`ServiceAdapterBoundaryV1` is source-bound to the following frozen checkpoints.
The source bindings are invalid if any tag is missing, moved, rewritten,
ambiguous, unresolved, or commit-mismatched.

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
```

These source bindings provide vocabulary and governance constraints only. They
do not authorize service adapter runtime, service calls, evidence append, audit
append, runtime append, DB/repository/UoW writes, durable writes, or
irreversible actions.

## 3. Service Identities

`ServiceAdapterBoundaryV1` must explicitly define these service identities
before any future runtime may be considered:

```text
evidence_service
approval_service
review_service
revision_seal_service
audit_service_future_adapter
```

Unnamed services are forbidden.

Dynamic service resolution is forbidden.

Wildcard service authority is forbidden.

Class-level service authority is forbidden.

Module-level service authority is forbidden.

Service identity must be exact and declared before future runtime.

Future adapter must bind service identity to operation kind and method name.

No identity in this section authorizes a service call. Each identity is a
governance declaration only and fails closed if treated as executable
authority.

## 4. Known Service Methods That Remain Forbidden Now

The following known surfaces are forbidden unless separately authorized later:

- `EvidenceService.close_evidence`
- `ApprovalService.evaluate_barrier`
- `ApprovalService.reverify_for_seal`
- `ReviewService.render_review`
- `RevisionSealService.seal_revision`

Listing these does not authorize them.

No method listed here may be called by this specification. No method listed
here may be treated as allowlisted, callable, implied, inherited, class-level,
module-level, wildcard, or dynamically resolved authority.

## 5. Future Service Method Declaration Requirements

Each future service method declaration must include:

- service identity
- exact service class name
- exact method name
- operation kind
- allowed phase
- input contract
- output contract
- idempotency binding
- transaction ownership
- evidence refs
- audit refs
- human approval ref
- operator confirmation ref
- append/runtime authority ref
- service boundary ref
- failure mode
- rollback/incident behavior
- side-effect classification
- authority scope
- revocation rule
- fail-closed behavior
- JSON safety

The following are forbidden:

- wildcard method authority
- dynamic method lookup
- runtime introspection
- getattr-based access
- callable discovery
- class/module blanket access
- service object passthrough
- service factory passthrough

A future method declaration is declaration-only until a separate governance
artifact, validator, CI consumer, implementation audit, and explicit runtime
authorization say otherwise. Missing, inferred, stale, ambiguous,
operation-mismatched, service-mismatched, or method-mismatched declarations
fail closed.

## 6. Service Result Contract

A future service adapter result must be:

- bounded
- JSON-safe
- deterministic
- explicit about success/failure
- explicit about evidence refs
- explicit about audit refs
- explicit about idempotency/replay classification
- explicit about incident classification
- explicit about side effects

The result contract must forbid:

- service object leakage
- DB handle leakage
- repository/UoW handle leakage
- exception object leakage
- filesystem handle leakage
- network handle leakage
- runtime repr leakage
- raw service result passthrough
- implicit append success
- undeclared evidence/audit refs

Future adapter output must be data only. It must not expose runtime handles,
service objects, exception objects, DB objects, repository/UoW objects,
filesystem handles, network handles, raw repr output, or undeclared refs. A
result that is malformed, unbounded, nondeterministic, non-JSON-safe,
side-effect-ambiguous, or success-ambiguous fails closed.

## 7. Transaction Ownership Model

Service adapter must not own transaction by default.

Kernel-owned transaction is required for future runtime.

Uncontrolled nested transactions are forbidden.

Service calls inside transaction require separate authority.

Service calls outside transaction require explicit out-of-band policy.

Commit cannot occur before required append/record bookkeeping succeeds.

Post-mutation service failure is incident-class.

Transaction runtime is not authorized by this spec.

No transaction boundary, commit policy, rollback policy, or service call timing
is executable under this specification. Any future service call that occurs
inside or outside a transaction requires separate, explicit authorization.

## 8. Idempotency Model

Service call idempotency binding required before side effects.

Idempotency reservation runtime is not authorized by this spec.

Same key + same binding is safe replay classification only.

Same key + different binding fails closed.

Ambiguous replay is incident-class.

Idempotency binding must include:

- source stack refs
- approved task id
- operation kind
- service identity
- service class name
- method name
- idempotency key
- service boundary ref
- append/runtime authority ref
- evidence ref set
- audit ref set
- human approval ref
- operator confirmation ref

The idempotency binding does not reserve a key, perform a lookup, persist a
record, call a service, open a DB, import repository/UoW, append evidence, or
append audit. It is a future declaration requirement only.

## 9. Evidence/Audit Ref Rules

Fabricated refs forbidden.

Undeclared refs forbidden.

Missing refs fail closed.

Mismatched refs fail closed.

Evidence/audit refs must be source-bound.

Evidence/audit refs must be operation-bound.

Evidence/audit refs must be JSON-safe strings.

Adapter output cannot imply append success without append authority.

Adapter output cannot imply audit emission without audit authority.

Adapter output cannot create refs unless separately authorized.

Evidence and audit refs under this spec are references only. This spec creates
no evidence ref, creates no audit ref, appends no evidence, appends no audit,
and cannot imply that evidence or audit append succeeded.

## 10. Failure/Incident Model

`ServiceAdapterBoundaryV1` must define these failure and incident cases:

- expected rejection
- forbidden service call
- service method not allowlisted
- malformed service result
- missing evidence/audit ref
- mismatched evidence/audit ref
- idempotency mismatch
- ambiguous replay
- transaction boundary violation
- post-mutation service failure
- rollback failure
- partial success
- silent success

Required classifications:

- expected rejection: bounded refusal, not execution failure
- forbidden service call: fail closed
- method not allowlisted: fail closed
- malformed result: fail closed
- missing/mismatched refs: fail closed
- idempotency mismatch: fail closed
- ambiguous replay: incident-class
- transaction violation: incident-class
- post-mutation service failure: incident-class
- rollback failure: incident-class
- partial success: forbidden
- silent success: forbidden

Any classification not explicitly declared is invalid. Any attempt to convert
partial success, silent success, ambiguous replay, transaction violation,
post-mutation service failure, or rollback failure into ordinary success fails
closed or becomes incident-class as declared above.

## 11. Required False Authority Flags

All of these authority flags must be present as false:

```text
service_adapter_runtime_authorized = false
evidence_service_authorized = false
approval_service_authorized = false
review_service_authorized = false
revision_seal_service_authorized = false
audit_service_authorized = false
service_method_call_authorized = false
service_side_effect_authorized = false
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
durable_writes_authorized = false
irreversible_action_authorized = false
executor_implementation_authorized = false
restore_execution_authorized = false
write_side_recovery_authorized = false
cli_execution_authorized = false
schema_migration_authorized = false
daemon_server_queue_authorized = false
db_repair_authorized = false
```

These flags are required to remain false unless a later separately authorized
runtime package changes them under an independently frozen governance process.

## 12. Required True Declarations

All of these declarations must be present as true:

```text
service_adapter_implementation_forbidden = true
service_calls_forbidden = true
evidence_service_call_forbidden = true
approval_service_call_forbidden = true
review_service_call_forbidden = true
revision_seal_service_call_forbidden = true
audit_service_call_forbidden = true
unnamed_service_forbidden = true
dynamic_service_resolution_forbidden = true
wildcard_service_authority_forbidden = true
class_level_service_authority_forbidden = true
module_level_service_authority_forbidden = true
service_method_allowlist_required = true
exact_service_identity_required = true
exact_service_class_name_required = true
exact_service_method_name_required = true
service_result_contract_required = true
service_result_json_safe_required = true
service_result_bounded_required = true
service_result_deterministic_required = true
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
service_transaction_ownership_forbidden_by_default = true
kernel_owned_transaction_required_for_future_runtime = true
uncontrolled_nested_transaction_forbidden = true
in_transaction_service_call_requires_separate_authority = true
out_of_band_service_call_policy_required = true
commit_after_required_bookkeeping_only = true
post_mutation_service_failure_incident_class = true
service_idempotency_binding_required = true
service_replay_classification_required = true
same_key_same_binding_safe_replay_only = true
same_key_different_binding_fail_closed = true
ambiguous_replay_incident_class = true
evidence_audit_ref_fabrication_forbidden = true
undeclared_ref_forbidden = true
missing_ref_fail_closed = true
mismatched_ref_fail_closed = true
evidence_audit_refs_source_bound_required = true
evidence_audit_refs_operation_bound_required = true
evidence_audit_refs_json_safe_required = true
adapter_output_cannot_imply_append_success_without_authority = true
adapter_output_cannot_imply_audit_emission_without_authority = true
adapter_output_cannot_create_refs_without_authority = true
forbidden_service_call_fail_closed = true
method_not_allowlisted_fail_closed = true
malformed_service_result_fail_closed = true
idempotency_mismatch_fail_closed = true
transaction_violation_incident_class = true
rollback_failure_incident_class = true
partial_success_forbidden = true
silent_success_forbidden = true
future_validator_required = true
future_ci_required = true
```

These declarations are governance requirements only. They do not create a
validator, checker, CI consumer, service adapter, runtime, append path, DB
path, executor, restore path, CLI, schema, migration, daemon, server, queue,
durable write, or irreversible action.

## 13. Future Validator Requirements

A future validator must consume already-rendered `ServiceAdapterBoundaryV1`
only.

A future validator must validate source refs.

A future validator must validate service identities.

A future validator must validate known forbidden methods.

A future validator must validate service method declaration requirements.

A future validator must validate result contract declarations.

A future validator must validate transaction/idempotency/ref/failure
declarations.

A future validator must validate false authority flags.

A future validator must validate true declarations.

A future validator must validate JSON safety.

A future validator calls no services.

A future validator opens no DB.

A future validator imports no repository/UoW.

A future validator appends no evidence/audit.

A future validator implements no runtime.

A future validator creates no CLI/schema/daemon.

This section does not add a validator. It declares future validator
requirements only.

## 14. Future CI Requirements

A future CI consumer must consume already-rendered validator output only.

A future CI consumer calls no validator.

A future CI consumer calls no services.

A future CI consumer opens no DB.

A future CI consumer imports no repository/UoW.

A future CI consumer appends no evidence/audit.

A future CI consumer implements no runtime.

A future CI consumer validates bounded shape.

A future CI consumer validates false authority flags.

A future CI consumer validates true declarations.

A future CI consumer validates JSON safety.

This section does not add a CI consumer. It declares future CI requirements
only.

## 15. Acceptance Requirements

Acceptance requires:

- exactly one governance spec file added
- no production code changed
- no tests changed
- no existing governance docs changed
- no service call added
- no DB/repository/UoW use added
- no runtime append added
- no evidence/audit append added
- no validator added
- no CI consumer added
- no checker added
- no executor/restore/CLI/schema/daemon added
- all authority flags false
- all required true declarations present
- broad health checks green
- git diff --check clean
- working tree clean

Any acceptance path that requires production code changes, test changes,
existing governance doc changes, service calls, DB/repository/UoW use,
runtime append, evidence/audit append, validator/CI/checker implementation,
executor/restore/CLI/schema/daemon work, or true authority flags must stop.

## 16. Freeze Criteria

Freeze requires:

- PR merged on main
- candidate tag absent
- first-parent diff exactly one spec-only governance file
- health checks green
- no drift from source checkpoints
- stop/consolidate audit recommends tag

The candidate freeze tag is `service-adapter-boundary-spec-only-v1`. The tag
must not be created by this implementation PR. It may only be recommended by a
later stop/consolidate audit after the PR merges on main and the first-parent
diff proves exactly one spec-only governance file.
