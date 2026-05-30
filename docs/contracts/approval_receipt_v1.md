# Approval Receipt V1

## Purpose

`approval_receipt_v1` records a human-attested approval decision for a task. It
is an evidence receipt only and does not execute work, call providers, or bypass
later runtime checks.

## Required Fields

- `contract_version`: must be `approval_receipt_v1`.
- `approval_id`: stable approval receipt identifier.
- `task_id`: task being approved.
- `approved_by_role`: human role that made the decision.
- `reason_digest`: digest of the approval reason.
- `decision`: must be `approved`.
- `approved_at`: metadata timestamp excluded from deterministic hashes.

## Optional Fields

- `constraints`: bounded strings naming approval constraints.
- `review_refs`: repository-relative review evidence references.
- `expires_at`: metadata timestamp for future policy review.

## Version

The only valid version for this contract is `approval_receipt_v1`.

## Immutability Rule

Accepted approval receipts must not be mutated. Revocation or replacement must
be represented by a later receipt.

## Unknown Field Policy

Consumers must reject unknown fields and fail closed before treating a task as
approved.

## Compatibility Rule

Compatible readers may accept new optional review metadata only when the
required approval identity, task binding, and decision remain unchanged.

## Migration/Deprecation Rule

Migration requires a new contract version, a mapping from old approval ids, and
a documented reason why the approval evidence shape changed.

## Valid Example

```json
{
  "contract_version": "approval_receipt_v1",
  "approval_id": "approval-readiness-001",
  "task_id": "task-readiness-001",
  "approved_by_role": "operator",
  "reason_digest": "sha256:3333333333333333333333333333333333333333333333333333333333333333",
  "decision": "approved",
  "approved_at": "2026-05-30T00:01:00Z"
}
```

## Invalid Example

```json
{
  "contract_version": "approval_receipt_v1",
  "approval_id": "approval-readiness-001",
  "task_id": "task-readiness-001",
  "approved_by_role": "automation",
  "decision": "approved"
}
```

The invalid example lacks `reason_digest` and uses a non-human approval role.

## Failure Behavior

Validation must fail closed, leave the task unapproved, and avoid creating any
execution receipt or success marker.
