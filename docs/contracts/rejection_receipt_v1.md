# Rejection Receipt V1

## Purpose

`rejection_receipt_v1` records a human or policy rejection for a task. It binds
the rejected task to digest-only reason evidence and a rollback or no-run
decision.

## Required Fields

- `contract_version`: must be `rejection_receipt_v1`.
- `rejection_id`: stable rejection receipt identifier.
- `task_id`: task being rejected.
- `rejected_by`: human role or policy gate.
- `reason_digest`: digest of rejection rationale.
- `decision`: must be `rejected`.
- `created_at`: metadata timestamp excluded from deterministic hashes.

## Optional Fields

- `rollback_plan_digest`: digest of required rollback plan if one exists.
- `appeal_ref`: repository-relative human review reference.
- `severity`: bounded rejection severity.

## Version

The only valid version for this contract is `rejection_receipt_v1`.

## Immutability Rule

Accepted rejection receipts must not be mutated. A later appeal or override must
produce a separate receipt.

## Unknown Field Policy

Consumers must reject unknown fields and fail closed before any task state can
move out of rejection.

## Compatibility Rule

Compatible readers may add optional review references only when the rejection
identity, task binding, and reason digest remain stable.

## Migration/Deprecation Rule

Migration requires a new contract version and a documented mapping for existing
rejection ids and reason digests.

## Valid Example

```json
{
  "contract_version": "rejection_receipt_v1",
  "rejection_id": "reject-readiness-001",
  "task_id": "task-readiness-001",
  "rejected_by": "policy_gate",
  "reason_digest": "sha256:4444444444444444444444444444444444444444444444444444444444444444",
  "decision": "rejected",
  "created_at": "2026-05-30T00:02:00Z"
}
```

## Invalid Example

```json
{
  "contract_version": "rejection_receipt_v1",
  "rejection_id": "reject-readiness-001",
  "task_id": "task-readiness-001",
  "decision": "approved",
  "reason_digest": "sha256:4444444444444444444444444444444444444444444444444444444444444444"
}
```

The invalid example contradicts the rejection decision and omits the rejecting
authority.

## Failure Behavior

Validation must fail closed, keep the prior task state unchanged, and never emit
a pass, approval, or execution receipt.
