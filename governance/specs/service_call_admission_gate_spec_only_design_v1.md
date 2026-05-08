# Service Call Admission Gate Spec-Only Design V1

Status: draft for human review

Canonical target filename: `governance/specs/service_call_admission_gate_spec_only_design_v1.md`

Verdict: SPEC_ONLY_COMPLETE

Tag candidate: `service-call-admission-gate-spec-only-v1`

Contract name: `ServiceCallAdmissionGateV1`

This document is spec-only.

This document is non-executable.

This document adds no production code.

This document adds no tests.

This document modifies no existing governance document.

## 1. Purpose

This specification defines the non-executable governance contract for a
future bounded service-call admission declaration.

The contract defined by this package is `ServiceCallAdmissionGateV1`.

`ServiceCallAdmissionGateV1` may only declare what would have to be
present before a future service-call attempt can be considered. It is a
future declaration object and validation target. It is not a service
call, not service-call execution, not a service adapter runtime, not a
runtime checker, not a runtime enforcer, not runtime authority, not
runtime authority grant usage, not authority ref runtime usage, not an
evidence writer, not an audit writer, not a DB handle, not a repository
or Unit of Work handle, not transaction runtime, not an idempotency
reservation, not rollback runtime, not executor dispatch, not restore
execution, not CLI, not schema or migration logic, and not daemon,
server, or queue logic.

This package must not execute a service call, authorize a service call,
create runtime authority, use a runtime authority grant, use an
authority ref, run checker/enforcer, open DB, call repository/UoW,
append evidence/audit, reserve idempotency, open transaction, roll back,
dispatch executor, restore, perform durable write, or perform
irreversible action.

Readiness is not authority. Authorization is not execution. Approval is
not authority. Service-call admission is not service-call execution.
Default deny and fail closed remain mandatory.

## 2. Non-Authority Clause

This spec grants no service-call admission runtime, no service-call
admission gate authority, no admission decision authority, no runtime,
no runtime checker, no runtime enforcer, no runtime authority, no
runtime authority grant usage, no authority ref runtime usage, no
service call, no service adapter runtime, no DB/repository/UoW write, no
evidence/audit append, no transaction, no idempotency reservation, no
rollback, no executor dispatch, no durable write, and no
irreversible-action authority.

This spec does not authorize checker runtime, enforcer runtime, runtime
authority grant runtime, authority ref runtime, service-call admission
runtime, admission decision runtime, service call execution, service
adapter implementation, service method calls, service side effects,
evidence service calls, approval service calls, review service calls,
revision seal service calls, audit service calls, evidence append, audit
append, runtime append, DB writes, direct DB writes, raw sqlite, ad hoc
SQL, repository writes, Unit of Work writes, transaction runtime,
idempotency reservation runtime, rollback runtime, executor dispatch,
restore execution, CLI/schema/daemon work, filesystem side effects,
external network effects, durable writes, DB repair, or irreversible
actions.

The following non-authority rules are mandatory:

* service-call admission is not service-call execution
* admission readiness is not authority
* admission decision is not service call
* tag existence is not authority
* validator success is not authority
* CI success is not authority
* approval is not authority
* execution authorization is not execution
* method authority is not runtime authority
* service call boundary is not runtime authority
* runtime authority grant object readiness is not runtime authority
* runtime authority checker/enforcer stack readiness is not runtime authority

Any attempt to treat this specification, a source binding, a frozen tag,
a branch name, a file presence check, a readiness result, validator
success, CI success, approval alone, execution authorization alone,
method authority alone, a service call boundary alone, runtime authority
grant object readiness alone, runtime authority checker/enforcer stack
readiness alone, repository/UoW allowlist readiness alone, write-path
readiness alone, executor precondition readiness alone, preflight
readiness alone, restore dry-run readiness alone, or operator
confirmation alone as runtime authority fails closed.

## 3. Exact Source Bindings

`ServiceCallAdmissionGateV1` source bindings must include these exact
frozen tag and commit pairs:

* read-only-governance-layer-v1 = 4656e8f03404c6bb39e7976c6165e3d7dc0314fb
* write-side-precondition-checker-v1 = fd5788c7a4d3ed953fbc0295414ba7e6ad4f89f6
* write-side-precondition-ci-v1 = 05c81541ad3d7deee20023843142f702937f6c3f
* write-side-recovery-spec-only-v1 = ad560cc2dab135f2c1d56d948410ae47586d118e
* restore-dry-run-read-only-stack-v1 = e7c78e3ff0c5dc05806c293f01ab32cd33c9518b
* preflight-read-only-stack-v1 = 662b6161253c35204b437e88809c5bab21908c6d
* execution-authorization-read-only-stack-v1 = d586aeb60620010c900df7be1a88621ab2cb8dc1
* executor-precondition-read-only-stack-v1 = cb3948eb843866dcc961b6a074038c13db64d017
* write-path-read-only-stack-v1 = 8ffd4679aca8f593415089748df35df42af8f015
* repository-uow-allowlist-read-only-stack-v1 = bec2d04eab1922594dcbfbe35971f4efe0fe4849
* evidence-audit-append-read-only-stack-v1 = 62db8a586efa9375d2c77cf7c6335ccf5ef11279
* append-runtime-authority-service-boundary-read-only-stack-v1 = bda430a6a8d1e1dbede2adb9594baa1ab5cf2039
* service-adapter-boundary-read-only-stack-v1 = 8698ea42c78cbe79231698be8839b9d2c246cfdf
* service-method-authority-read-only-stack-v1 = db2f628cc79df0dc7b4f1306cbe24d880693188b
* service-call-execution-boundary-read-only-stack-v1 = 2a82b78665541d2e408113646ea11fbda4b62037
* runtime-authority-checker-enforcer-read-only-stack-v1 = a749545998e94aceee52775d363f9b8bb43e26a4
* runtime-authority-grant-object-read-only-stack-v1 = 4acbddba3e0897d16bcfc74007ecd094817faa11
* runtime-authority-checker-enforcer-boundary-spec-only-v1 = 9bd776b4178ce627e28eb430ea07d6b7a2a002ce
* runtime-authority-checker-enforcer-boundary-validator-v1 = b2627216e5efb803ebe673dc38b3167db7a8e3db
* runtime-authority-checker-enforcer-boundary-validator-ci-v1 = a749545998e94aceee52775d363f9b8bb43e26a4
* runtime-authority-grant-object-spec-only-v1 = 3910680b973a7bfb9fa89b2ab52a213d402fbdae
* runtime-authority-grant-object-validator-v1 = ed31e3c92a7bd3d35e411dd4e559038023a2f8d9
* runtime-authority-grant-object-validator-ci-v1 = 4acbddba3e0897d16bcfc74007ecd094817faa11

These source bindings provide frozen evidence, vocabulary, and boundary
context only. They do not grant service-call admission runtime,
admission decision authority, runtime authority, checker authority,
enforcer authority, runtime authority grant usage, authority ref runtime
usage, service-call authority, append authority, DB authority,
repository/UoW authority, transaction authority, idempotency authority,
rollback authority, executor authority, durable-write authority, or
irreversible-action authority.

Missing, malformed, stale, unresolved, ambiguous, target-mismatched, or
commit-mismatched source bindings fail closed.

## 4. Admission Input Model

A future `ServiceCallAdmissionGateV1` declaration must be a bounded
JSON-safe object with this exact conceptual field set:

* surface
* version
* source_refs
* service_identity
* service_class_name
* service_method_name
* operation_ref
* target_surface
* permitted_action_class
* forbidden_action_class
* runtime_authority_grant_object_ref
* authority_ref
* service_method_authority_ref
* service_call_execution_boundary_ref
* execution_authorization_ref
* human_approval_ref
* operator_confirmation_ref
* runtime_authority_checker_enforcer_stack_ref
* service_adapter_boundary_ref
* evidence_audit_append_boundary_ref
* repository_uow_allowlist_ref
* write_path_boundary_ref
* executor_precondition_ref
* idempotency_key_ref
* transaction_placement_ref
* evidence_pre_bookkeeping_ref
* audit_pre_bookkeeping_ref
* evidence_post_bookkeeping_ref
* audit_post_bookkeeping_ref
* expiry_ref
* revocation_ref
* revocation_status_ref
* admission_denial_policy
* incident_classification_policy
* false_authority_flags
* true_declarations
* json_safe

The `surface` value must be `ServiceCallAdmissionGateV1`.

The `version` value must be `1`.

The admission declaration must be declaration-only. It must not call
services, open DB, import repository/UoW code, append evidence/audit,
reserve idempotency, start transactions, roll back transactions,
dispatch executors, execute restore, invoke CLI/schema/daemon work,
write files, perform network effects, perform durable writes, or
perform irreversible actions.

## 5. Required Bindings

The admission declaration must include every binding in this section.
Each binding is a future validation input only and does not authorize
runtime.

The following bindings are mandatory:

* runtime authority grant object binding
* authority ref binding
* service method authority binding
* service call execution boundary binding
* execution authorization binding
* human approval binding
* operator confirmation binding
* runtime authority checker/enforcer stack binding
* service adapter boundary binding
* evidence/audit append boundary binding
* repository/UoW allowlist binding
* write-path binding
* executor precondition binding
* exact service identity binding
* exact service class name binding
* exact service method name binding
* operation-bound binding
* target-surface binding
* permitted action class binding
* forbidden action class binding
* expiry declaration
* revocation declaration
* revocation status declaration
* idempotency key ref declaration
* transaction placement ref declaration
* evidence/audit pre-call refs
* evidence/audit post-call refs

Derived, inferred, wildcard, class-wide, module-wide, method-family,
best-effort, stale, ambiguous, partial, or runtime-discovered admission
authority is forbidden.

## 6. Service Identity Binding

Service identity must be exact, explicit, bounded, source-bound, and
operation-bound.

The declaration must identify:

* exact service identity
* exact service class name
* exact service method name
* exact operation ref
* exact target surface
* exact permitted action class
* exact forbidden action class

No wildcard service identity, dynamic service lookup, class-level
authority, module-level authority, method-family authority, implicit
adapter selection, executor-owned direct service call, or service object
handle may be treated as admission authority.

## 7. Authority Input Binding

The admission declaration must bind both:

* `runtime_authority_grant_object_ref`
* `authority_ref`

Runtime authority grant object readiness is not runtime authority. An
authority ref is not runtime authority. Neither a grant object nor an
authority ref authorizes service-call admission runtime, service-call
execution, checker runtime, enforcer runtime, append, DB writes,
transaction runtime, idempotency reservation, rollback, executor
dispatch, durable writes, or irreversible actions.

The authority ref must be source-bound, operation-bound, target-bound,
revocation-checked, and expiry-checked as a future declaration input.
This specification authorizes no runtime use of the authority ref.

## 8. Read-Only Stack Bindings

The admission declaration must bind the frozen read-only stacks for:

* service method authority
* service call execution boundary
* execution authorization
* runtime authority checker/enforcer
* service adapter boundary
* evidence/audit append boundary
* repository/UoW allowlist
* write-path boundary
* executor precondition
* preflight
* restore dry-run

These read-only stacks are prerequisites only. Their existence,
readiness, validator success, CI success, and frozen tag status do not
authorize service-call admission runtime, service-call execution,
runtime authority, append, DB/repository/UoW writes, transaction
runtime, idempotency reservation, rollback, executor dispatch, durable
writes, or irreversible actions.

## 9. Evidence, Audit, Idempotency, and Transaction Bindings

The admission declaration must require:

* idempotency_key_ref
* transaction_placement_ref
* evidence_pre_bookkeeping_ref
* audit_pre_bookkeeping_ref
* evidence_post_bookkeeping_ref
* audit_post_bookkeeping_ref

The idempotency key ref is a declaration only. This specification does
not authorize idempotency reservation, idempotency replay classification
runtime, DB writes, repository/UoW writes, transaction runtime,
rollback runtime, or durable writes.

Transaction placement is a declaration only. This specification does not
authorize transaction runtime, `KernelUnitOfWork` use, DB writes,
repository/UoW writes, rollback runtime, compensation runtime, durable
writes, or irreversible actions.

Evidence and audit refs are declaration-only. This specification does
not authorize evidence service calls, audit service calls, evidence
append, audit append, runtime append, or durable evidence/audit writes.

## 10. Expiry and Revocation Requirements

The admission declaration must include:

* expiry_ref
* revocation_ref
* revocation_status_ref

Expiry and revocation are future validation inputs only. This
specification does not authorize wall-clock runtime, timestamp parsing
runtime, revocation lookup, DB reads, DB writes, service calls, audit
append, runtime authority checks, service-call admission runtime, or
irreversible actions.

Expired authority fails closed.

Revoked authority fails closed.

Missing, ambiguous, stale, mismatched, unverifiable, or malformed
revocation status fails closed.

## 11. Denial and Fail-Closed Policy

Default denial is mandatory.

The following denial and fail-closed declarations are mandatory:

* missing grant fails closed
* missing authority ref fails closed
* malformed authority ref fails closed
* mismatched authority ref fails closed
* expired authority fails closed
* revoked authority fails closed
* missing service method authority fails closed
* missing service call execution boundary fails closed
* missing execution authorization fails closed
* missing human approval fails closed
* missing operator confirmation fails closed
* missing runtime authority checker/enforcer stack fails closed
* missing service adapter boundary fails closed
* missing evidence/audit append boundary fails closed
* missing repository/UoW allowlist fails closed
* missing write-path boundary fails closed
* missing executor precondition fails closed
* admission mismatch becomes incident class
* ambiguous authority becomes incident class
* silent admission success forbidden
* implicit admission escalation forbidden
* implicit authority escalation forbidden

No silent success is permitted. No partial success is permitted. No
implicit authority escalation is permitted. No readiness-to-runtime
promotion is permitted. Missing, malformed, mismatched, expired,
revoked, stale, ambiguous, unverifiable, or unsupported admission
authority fails closed.

Incident classification does not authorize evidence append, audit
append, runtime append, DB writes, repository/UoW writes, service calls,
executor dispatch, durable writes, rollback, compensation, repair, or
irreversible actions.

## 12. Forbidden Implicit Authority Sources

The admission declaration must explicitly forbid deriving authority
from:

* tag existence
* branch name
* file presence
* validator success
* CI success
* ready
* ci_ok
* approval readiness
* execution authorization readiness
* human approval existence
* operator confirmation existence
* method authority readiness
* service call boundary readiness
* runtime authority checker/enforcer readiness
* runtime authority grant object readiness
* repository/UoW allowlist readiness
* write-path readiness
* executor precondition readiness
* preflight readiness
* restore dry-run readiness
* audit/evidence ref existence
* idempotency key existence
* transaction placement declaration
* service adapter boundary declaration

Implicit authority from any source fails closed.

## 13. Required False Authority Flags

All of the following flags must appear exactly as false in any future
rendered `ServiceCallAdmissionGateV1` declaration:

```text
service_call_admission_runtime_authorized = false
service_call_admission_gate_authorized = false
service_call_admission_decision_authorized = false
runtime_authority_grant_runtime_authorized = false
runtime_authority_ref_runtime_authorized = false
runtime_authority_checker_authorized = false
runtime_authority_enforcer_authorized = false
runtime_authority_runtime_authorized = false
runtime_allowlist_authorized = false
runtime_checker_authorized = false
runtime_enforcer_authorized = false
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
executor_implementation_authorized = false
executor_service_dispatch_authorized = false
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

All required false authority flags must be present as false. Any missing
flag, extra flag, non-boolean flag, or true authority flag fails closed.

## 14. Required True Declarations

All of the following declarations must appear exactly as true in any
future rendered `ServiceCallAdmissionGateV1` declaration:

```text
spec_only_non_executable = true
service_call_admission_forbidden = true
service_call_admission_runtime_forbidden = true
service_call_admission_is_not_execution = true
admission_decision_is_not_service_call = true
readiness_is_not_authority = true
authorization_is_not_execution = true
approval_is_not_authority = true
execution_authorization_is_not_execution = true
method_authority_is_not_runtime_authority = true
service_call_boundary_is_not_runtime_authority = true
runtime_authority_stack_readiness_is_not_runtime_authority = true
runtime_authority_grant_object_readiness_is_not_runtime_authority = true
tag_existence_is_not_authority = true
runtime_authority_grant_object_required = true
authority_ref_required = true
authority_ref_source_bound_required = true
authority_ref_operation_bound_required = true
authority_ref_target_bound_required = true
authority_ref_revocation_checked_required = true
authority_ref_expiry_checked_required = true
service_method_authority_required = true
service_call_execution_boundary_required = true
execution_authorization_required = true
human_approval_required = true
operator_confirmation_required = true
runtime_authority_checker_enforcer_stack_required = true
service_adapter_boundary_required = true
evidence_audit_append_boundary_required = true
repository_uow_allowlist_required = true
write_path_boundary_required = true
executor_precondition_required = true
exact_service_identity_required = true
exact_service_class_name_required = true
exact_service_method_name_required = true
operation_bound_required = true
target_surface_bound_required = true
permitted_action_class_required = true
forbidden_action_class_required = true
idempotency_key_ref_required = true
transaction_placement_ref_required = true
evidence_pre_bookkeeping_ref_required = true
audit_pre_bookkeeping_ref_required = true
evidence_post_bookkeeping_ref_required = true
audit_post_bookkeeping_ref_required = true
denial_fail_closed_required = true
missing_grant_fail_closed = true
missing_authority_ref_fail_closed = true
malformed_authority_ref_fail_closed = true
mismatched_authority_ref_fail_closed = true
expired_authority_fail_closed = true
revoked_authority_fail_closed = true
ambiguous_authority_incident_class = true
admission_mismatch_incident_class = true
silent_admission_success_forbidden = true
implicit_admission_escalation_forbidden = true
implicit_authority_escalation_forbidden = true
service_calls_forbidden = true
service_call_execution_forbidden = true
service_adapter_implementation_forbidden = true
db_repository_uow_writes_forbidden = true
evidence_append_forbidden = true
audit_append_forbidden = true
transaction_runtime_forbidden = true
idempotency_reservation_forbidden = true
rollback_runtime_forbidden = true
executor_dispatch_forbidden = true
durable_writes_forbidden = true
irreversible_actions_forbidden = true
future_validator_required = true
future_ci_required = true
```

All required true declarations must be present as true. Any missing
declaration, extra declaration, non-boolean declaration, or false
required declaration fails closed.

## 15. JSON Safety

All admission declarations and all future validator/CI outputs must be
bounded JSON-safe.

`ServiceCallAdmissionGateV1` declarations, future validator outputs, and
future CI outputs must contain no:

* runtime object handles
* DB handles
* service objects
* exception objects
* repr leakage
* callables
* subprocess handles
* mutable runtime state
* raw UoW/session/connection object
* implicit object identity
* filesystem handles
* network handles

JSON safety does not authorize runtime, service-call admission runtime,
service-call execution, checker/enforcer runtime, append, DB writes,
repository/UoW writes, transaction runtime, idempotency reservation,
rollback, executor dispatch, durable writes, or irreversible actions.

## 16. Future Validator Requirements

A future `service-call-admission-gate-validator-v1` package must add a
pure read-only validator over already-rendered
`ServiceCallAdmissionGateV1` declarations only.

The future validator must:

* consume already-rendered `ServiceCallAdmissionGateV1` declaration only
* remain read-only
* import only `Mapping` and `deepcopy`
* call no services
* open no DB
* import no repository/UoW
* append no evidence/audit
* implement no runtime
* authorize no service calls
* validate exact source refs
* validate exact admission input shape
* validate false authority flags
* validate true declarations
* validate JSON safety
* produce bounded JSON-safe output
* keep all authority flags false

The future validator must not authorize service-call admission runtime,
admission decision runtime, runtime, checker runtime, enforcer runtime,
runtime authority grant usage, authority ref runtime usage, service
calls, service adapter implementation, DB/repository/UoW writes,
evidence/audit append, transaction runtime, idempotency reservation,
rollback runtime, executor dispatch, restore execution, CLI/schema/daemon
work, durable writes, or irreversible actions.

## 17. Future CI Requirements

A future `service-call-admission-gate-validator-ci-v1` package must add
a pure read-only CI consumer over already-rendered validator output only.

The future CI consumer must:

* consume already-rendered validator output only
* not import/call validator
* remain read-only
* call no services
* open no DB
* import no repository/UoW
* append no evidence/audit
* implement no runtime
* authorize no service calls
* validate validator checkpoint binding
* validate exact validator output shape
* validate failure taxonomy
* validate hard-false authority summary
* validate non-authority semantics
* produce bounded JSON-safe output

The future CI consumer must keep every authority flag false. `ci_ok` is
not authority.

The future CI consumer must not authorize service-call admission
runtime, admission decision runtime, runtime, checker runtime, enforcer
runtime, runtime authority grant usage, authority ref runtime usage,
service calls, service adapter implementation, DB/repository/UoW writes,
evidence/audit append, transaction runtime, idempotency reservation,
rollback runtime, executor dispatch, restore execution, CLI/schema/daemon
work, durable writes, or irreversible actions.

## 18. Acceptance Requirements

Acceptance requires:

* exactly one added governance spec file
* no production code change
* no tests changed
* no existing governance docs changed
* no validator/CI added
* no runtime implementation
* no service call
* no DB/repository/UoW
* no evidence/audit append
* no executor/restore/CLI/schema/daemon
* all false authority flags present as false
* all true declarations present as true
* source bindings exact
* JSON safety present
* future validator/CI requirements present
* health checks green
* working tree clean

Any scope expansion outside the single new governance spec file blocks
acceptance.

## 19. Freeze Criteria

Freeze/tag may be considered only after:

* PR is merged
* first-parent diff is exactly one added file:
  * `governance/specs/service_call_admission_gate_spec_only_design_v1.md`
* all source bindings match
* all false flags and true declarations are present
* no runtime/write/service/import expansion exists
* full health checks pass
* working tree is clean
* candidate tag is absent

The candidate tag is:

`service-call-admission-gate-spec-only-v1`

Freeze is a checkpoint recommendation only. It does not authorize
service-call admission runtime, admission decision runtime, runtime,
checker runtime, enforcer runtime, runtime authority grant usage,
authority ref runtime usage, service calls, service adapter runtime,
DB/repository/UoW writes, evidence/audit append, transaction runtime,
idempotency reservation, rollback, executor dispatch, restore,
CLI/schema/daemon work, durable writes, or irreversible actions.
