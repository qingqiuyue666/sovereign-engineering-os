Service Call Execution Boundary Spec-Only Design v1

Status: draft for human review

Canonical target filename: governance/specs/service_call_execution_boundary_spec_only_design_v1.md

Verdict: SPEC_ONLY_COMPLETE

Tag candidate: service-call-execution-boundary-spec-only-v1

1. Title

Service Call Execution Boundary Spec-Only Design v1

This document is spec-only.

This document is non-executable.

This document adds no production code.

This document adds no tests.

This document modifies no existing governance document.

2. Contract object: ServiceCallExecutionBoundaryV1

The contract object defined by this package is `ServiceCallExecutionBoundaryV1`.

`ServiceCallExecutionBoundaryV1` is a future declaration object and validation target. It is not a service adapter, not a service method call, not a runtime checker, not a runtime enforcer, not an executor, not a DB handle, not a repository or Unit of Work, not a transaction, not an idempotency reservation, not rollback or compensation runtime, not evidence append, and not audit append.

`ServiceCallExecutionBoundaryV1` may only describe the non-executable boundary between a validated service method authority declaration and any later package that separately proposes an actual service call attempt.

3. Purpose

This spec defines the non-executable boundary between a validated service method authority declaration and any future actual service call attempt.

The boundary exists because method authority readiness is not service-call authority, execution authorization readiness is not execution, and readiness is not authorization.

This package must not create a service call attempt, execute a service call attempt, create a service adapter runtime, call service methods, call evidence services, call approval services, call review services, call revision seal services, call audit services, append evidence, append audit records, open a DB, import or call repository or Unit of Work code, create transaction runtime, create idempotency reservation runtime, create rollback runtime, create checker/enforcer runtime, create executor runtime, create restore runtime, add CLI execution, add schema or migration changes, add daemon/server/queue execution, authorize durable writes, or authorize irreversible actions.

4. Non-authority clause

The `ServiceCallExecutionBoundaryV1` contract grants no service call authority, no service adapter runtime authority, no DB authority, no append authority, no transaction authority, no idempotency reservation authority, no rollback authority, no executor authority, no durable-write authority, and no irreversible-action authority.

This spec does not authorize service calls.

This spec does not authorize service adapter implementation.

This spec does not authorize service method calls.

This spec does not authorize service side effects.

This spec does not authorize evidence service calls, approval service calls, review service calls, revision seal service calls, or audit service calls.

This spec does not authorize evidence append or audit append.

This spec does not authorize runtime append.

This spec does not authorize DB writes, direct DB writes, raw sqlite, ad hoc SQL, repository writes, or Unit of Work writes.

This spec does not authorize transaction runtime, idempotency reservation runtime, rollback runtime, checker runtime, enforcer runtime, executor runtime, restore runtime, CLI execution, schema migration, daemon/server/queue execution, filesystem side effects, external network effects, durable writes, DB repair, or irreversible actions.

Any attempt to treat this spec as runtime authority fails closed.

5. Source bindings

`ServiceCallExecutionBoundaryV1` source bindings must include these exact frozen tag and commit pairs:

* read-only-governance-layer-v1 -> 4656e8f03404c6bb39e7976c6165e3d7dc0314fb
* write-side-precondition-checker-v1 -> fd5788c7a4d3ed953fbc0295414ba7e6ad4f89f6
* write-side-precondition-ci-v1 -> 05c81541ad3d7deee20023843142f702937f6c3f
* write-side-recovery-spec-only-v1 -> ad560cc2dab135f2c1d56d948410ae47586d118e
* restore-dry-run-read-only-stack-v1 -> e7c78e3ff0c5dc05806c293f01ab32cd33c9518b
* preflight-read-only-stack-v1 -> 662b6161253c35204b437e88809c5bab21908c6d
* execution-authorization-read-only-stack-v1 -> d586aeb60620010c900df7be1a88621ab2cb8dc1
* executor-precondition-read-only-stack-v1 -> cb3948eb843866dcc961b6a074038c13db64d017
* write-path-read-only-stack-v1 -> 8ffd4679aca8f593415089748df35df42af8f015
* repository-uow-allowlist-read-only-stack-v1 -> bec2d04eab1922594dcbfbe35971f4efe0fe4849
* evidence-audit-append-read-only-stack-v1 -> 62db8a586efa9375d2c77cf7c6335ccf5ef11279
* append-runtime-authority-service-boundary-read-only-stack-v1 -> bda430a6a8d1e1dbede2adb9594baa1ab5cf2039
* service-adapter-boundary-read-only-stack-v1 -> 8698ea42c78cbe79231698be8839b9d2c246cfdf
* service-method-authority-read-only-stack-v1 -> db2f628cc79df0dc7b4f1306cbe24d880693188b

These source bindings provide frozen evidence only. They do not grant service-call authority, runtime authority, append authority, DB authority, durable-write authority, or irreversible-action authority.

Missing, malformed, stale, unresolved, ambiguous, target-mismatched, or commit-mismatched source bindings fail closed.

6. Service call attempt boundary

A future service call attempt must require exact service identity, exact service class name, exact service method name, operation kind, phase, task/ref bindings, authority ref, method authority CI ref, execution authorization CI ref, human approval ref, operator confirmation ref, idempotency key, transaction placement declaration, evidence/audit pre/post bookkeeping refs, result contract ref, failure policy ref, revocation/expiry status, and JSON safety.

This package must not create such call attempts.

This package must not execute such call attempts.

A future call attempt boundary must be explicit, bounded, source-bound, operation-bound, JSON-safe, and fail-closed.

Derived, inferred, wildcard, class-wide, module-wide, partial, or best-effort service call authority is forbidden.

7. Authority input binding

A future service call attempt requires an authority ref.

Missing authority ref fails closed.

Mismatched authority ref fails closed.

Revoked authority ref fails closed.

Expired authority ref fails closed.

Authority ref must be source-bound.

Authority ref must be operation-bound.

Authority ref does not itself authorize runtime.

Authority ref does not bypass the service call attempt boundary.

8. Method authority CI binding

A future service call attempt requires a validated `service-method-authority-read-only-stack-v1` lineage.

The future object must bind the service method authority declaration to method authority CI evidence.

`method_authority_ready` is a prerequisite only.

`ci_ok` is a prerequisite only.

`method_authority_ready` and `ci_ok` are not service-call authority.

Method authority CI readiness is not runtime authority.

9. Execution authorization binding

A future service call attempt requires execution authorization binding.

Execution authorization readiness is not execution.

Authorization is not execution.

Executor remains unauthorized by this spec.

Execution authorization binding does not grant service adapter runtime authority, service call authority, append authority, DB authority, transaction authority, idempotency reservation authority, rollback authority, durable-write authority, or irreversible-action authority.

10. Human approval binding

Human approval ref is required.

Missing human approval ref fails closed.

Mismatched human approval ref fails closed.

Human approval does not bypass the service-call boundary.

Human approval does not authorize service adapter runtime, service method calls, evidence append, audit append, DB writes, transaction runtime, idempotency reservation runtime, rollback runtime, executor runtime, durable writes, or irreversible actions.

11. Operator confirmation binding

Operator confirmation ref is required.

Missing operator confirmation ref fails closed.

Mismatched operator confirmation ref fails closed.

Operator confirmation does not bypass the service-call boundary.

Operator confirmation does not authorize service adapter runtime, service method calls, evidence append, audit append, DB writes, transaction runtime, idempotency reservation runtime, rollback runtime, executor runtime, durable writes, or irreversible actions.

12. Idempotency key binding

Idempotency key is required.

The key must be source-bound.

The key must be operation-bound.

The same key with the same binding may only classify replay.

The same key with a different binding fails closed.

Ambiguous idempotency state is incident-class.

No idempotency reservation runtime is authorized by this spec.

This spec creates no reservation table, reservation row, reservation repository, reservation service, reservation API, durable marker, or idempotency write path.

13. Transaction placement binding

Kernel-owned transaction is required for future runtime.

Service-owned transaction is forbidden by default.

Uncontrolled nested transaction is forbidden.

Out-of-band service call requires a separate future declaration.

No transaction runtime is authorized by this spec.

This spec starts no transaction, commits no transaction, rolls back no transaction, and creates no transaction manager.

14. Evidence/audit pre/post bookkeeping boundary

Evidence pre-bookkeeping is required.

Audit pre-bookkeeping is required.

Evidence post-bookkeeping is required.

Audit post-bookkeeping is required.

Missing pre-bookkeeping blocks any future call.

Missing post-bookkeeping after service result is incident-class.

No evidence append is authorized by this spec.

No audit append is authorized by this spec.

This spec does not call evidence service or audit service.

This spec does not append evidence, append audit records, allocate evidence refs, allocate audit refs, close evidence refs, or close audit refs.

15. Service result intake boundary

Result contract is required.

Result must be bounded and JSON-safe.

Result must contain no runtime handles.

Result must contain no service objects.

Result must contain no DB handles.

Result must contain no repository or Unit of Work handles.

Result must contain no exception objects.

Result must contain no raw repr.

Result must imply no append success.

Result must imply no audit success.

Service result intake does not authorize follow-on writes, evidence append, audit append, durable writes, or irreversible actions.

16. Service result to evidence/audit ref binding

Explicit result-to-evidence-ref binding is required.

Explicit result-to-audit-ref binding is required.

Fabricated refs are forbidden.

Missing refs fail closed before call.

Missing refs after service result are incident-class.

Result cannot create refs without authorized append runtime.

Result-to-ref binding does not authorize evidence append, audit append, runtime append, DB writes, durable writes, or irreversible actions.

17. Failure/incident classification

Expected refusal is not execution failure.

Forbidden call fails closed.

Missing authority fails closed.

Revoked authority fails closed.

Expired authority fails closed.

Idempotency mismatch fails closed.

Transaction violation is incident-class.

Post-service failure is incident-class.

Append failure after service is incident-class.

Rollback failure is incident-class.

Partial success is forbidden.

Silent success is forbidden.

Incident classification does not authorize repair, rollback runtime, compensation runtime, DB writes, evidence append, audit append, durable writes, or irreversible actions.

18. Rollback/compensation boundary

Future rollback/compensation policy is required.

Rollback runtime remains unauthorized.

Compensation runtime remains unauthorized.

Rollback failure is incident-class.

This spec implements no rollback runtime, no compensation runtime, no rollback service, no compensation service, no repair path, and no durable side effect.

19. Forbidden direct service call boundary

Direct service call without a boundary object is forbidden.

Dynamic lookup is forbidden.

Wildcard service authority is forbidden.

Class-level service authority is forbidden.

Module-level service authority is forbidden.

Executor-owned direct service call is forbidden.

Service adapter runtime cannot be inferred from method authority, execution authorization, human approval, operator confirmation, or this spec.

20. Forbidden DB/repository/UoW boundary

No DB open is authorized.

No DB write is authorized.

No repository import is authorized.

No repository call is authorized.

No Unit of Work import is authorized.

No Unit of Work call is authorized.

No direct SQL is authorized.

No raw sqlite is authorized.

No service-owned Unit of Work is authorized.

No transaction ownership by service adapter is authorized.

21. Forbidden executor boundary

No executor implementation is authorized.

No executor-owned service call is authorized.

No restore execution is authorized.

No CLI execution is authorized.

No schema/migration execution is authorized.

No daemon, server, queue, async worker, or background runner is authorized.

22. Runtime checker/enforcer future requirement

Future runtime requires a separate checker/enforcer design.

This spec does not implement checker/enforcer.

This spec does not import checker/enforcer.

This spec does not call checker/enforcer.

Checker/enforcer authority flags remain false.

Future runtime checker and runtime enforcer cannot be inferred from this spec and must be separately designed, validated, reviewed, and frozen before any runtime discussion.

23. Revocation and expiry boundary

Revocation status is required for any future authority ref.

Expiry status is required for any future authority ref.

Revoked authority fails closed.

Expired authority fails closed.

Unknown revocation state fails closed.

Unknown expiry state fails closed.

Revocation and expiry checks do not authorize runtime and do not authorize service calls.

24. Required false authority flags

`ServiceCallExecutionBoundaryV1` requires these flags to be present and false:

```text
service_call_execution_authorized = false
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

Any missing false authority flag fails closed.

Any true value for these authority flags fails closed unless a separate future frozen package explicitly authorizes that exact flag, and this spec does not do so.

25. Required true declarations

`ServiceCallExecutionBoundaryV1` requires these declarations to be present and true:

```text
spec_only_non_executable = true
service_call_execution_forbidden = true
service_adapter_implementation_forbidden = true
service_calls_forbidden = true
direct_service_call_forbidden = true
exact_service_identity_required = true
exact_service_class_name_required = true
exact_service_method_name_required = true
service_method_authority_ci_required = true
execution_authorization_ci_required = true
human_approval_required = true
operator_confirmation_required = true
authority_ref_required = true
authority_ref_source_bound_required = true
authority_ref_operation_bound_required = true
idempotency_key_required = true
idempotency_key_source_bound_required = true
idempotency_key_operation_bound_required = true
transaction_placement_required = true
kernel_owned_transaction_required_for_future_runtime = true
service_transaction_ownership_forbidden_by_default = true
uncontrolled_nested_transaction_forbidden = true
evidence_pre_bookkeeping_required = true
audit_pre_bookkeeping_required = true
evidence_post_bookkeeping_required = true
audit_post_bookkeeping_required = true
service_result_contract_required = true
service_result_json_safe_required = true
service_result_bounded_required = true
service_result_no_runtime_handles_required = true
service_result_to_evidence_ref_binding_required = true
service_result_to_audit_ref_binding_required = true
fabricated_refs_forbidden = true
implicit_append_success_forbidden = true
implicit_audit_success_forbidden = true
failure_incident_separation_required = true
forbidden_service_call_fail_closed = true
missing_authority_fail_closed = true
revoked_authority_fail_closed = true
expired_authority_fail_closed = true
idempotency_mismatch_fail_closed = true
transaction_violation_incident_class = true
post_service_failure_incident_class = true
append_failure_after_service_incident_class = true
rollback_failure_incident_class = true
partial_success_forbidden = true
silent_success_forbidden = true
runtime_checker_required_for_future_runtime = true
runtime_enforcer_required_for_future_runtime = true
future_validator_required = true
future_ci_required = true
```

Any missing true declaration fails closed.

Any false value for these required declarations fails closed.

26. JSON safety

`ServiceCallExecutionBoundaryV1` must be JSON-safe.

All future rendered inputs, validator outputs, CI outputs, service result declarations, evidence/audit refs, failure policies, incident classifications, revocation/expiry statuses, and acceptance evidence must be bounded and JSON-safe.

The boundary forbids runtime handles, service objects, DB handles, repository handles, Unit of Work handles, exception objects, raw repr, unserializable values, unbounded payloads, and implementation-private objects.

JSON safety does not authorize runtime.

JSON safety does not authorize append.

JSON safety does not authorize DB writes.

27. Future validator requirements

A future validator must consume already-rendered `ServiceCallExecutionBoundaryV1` only.

A future validator must be read-only.

A future validator must not call services.

A future validator must not open DB.

A future validator must not import repository or Unit of Work code.

A future validator must not call repository or Unit of Work code.

A future validator must not append evidence.

A future validator must not append audit records.

A future validator must not implement transaction runtime.

A future validator must not implement idempotency reservation runtime.

A future validator must not implement rollback runtime.

A future validator must not call upstream validators or CI.

A future validator must not authorize runtime.

A future validator must validate source refs, authority bindings, service call attempt boundary declarations, method authority CI binding, execution authorization binding, approval/confirmation bindings, idempotency binding, transaction placement, evidence/audit bookkeeping, result intake, result-to-ref binding, failure/incident declarations, rollback/compensation declarations, false authority flags, true declarations, and JSON safety.

28. Future CI requirements

A future CI consumer must consume already-rendered validator output only.

A future CI consumer must not import or call the validator.

A future CI consumer must keep all runtime, service, write, append, DB, transaction, idempotency, rollback, and executor flags false.

A future CI consumer must be JSON-safe and bounded.

A future CI consumer must not call services, open DB, import repository or Unit of Work code, append evidence, append audit records, implement transaction runtime, implement idempotency reservation runtime, implement rollback runtime, implement checker/enforcer runtime, implement executor runtime, implement restore runtime, or authorize durable writes.

29. Acceptance requirements

Acceptance requires exactly one new spec file.

Acceptance requires no production code changes.

Acceptance requires no test changes.

Acceptance requires no existing governance doc changes.

Acceptance requires all required source bindings present.

Acceptance requires all required false flags present as false.

Acceptance requires all required true declarations present as true.

Acceptance requires future validator requirements present.

Acceptance requires future CI requirements present.

Acceptance requires runtime, service, DB, append, and executor authority remain false.

Acceptance requires health checks green.

Acceptance requires git diff clean.

Acceptance requires working tree clean after commit.

30. Freeze criteria

Freeze requires the PR to merge with exactly one new governance spec file.

Freeze requires no drift in frozen source refs.

Freeze requires health checks green.

Freeze requires candidate tag `service-call-execution-boundary-spec-only-v1` absent before freeze.

Freeze requires a stop/consolidate audit that recommends tag.

Freeze does not authorize service calls, runtime, append, DB writes, repository or Unit of Work writes, transaction runtime, idempotency reservation runtime, rollback runtime, checker/enforcer runtime, executor runtime, restore runtime, CLI execution, schema migration, daemon/server/queue execution, durable writes, or irreversible actions.
