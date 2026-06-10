# Task Contract V1

## Purpose

`task_contract_v1` defines the digest-only task descriptor accepted by the
local SEOS control plane. It describes task identity and intent without storing
raw prompt text, secret values, execution authority, or provider payloads.

## Required Fields

- `contract_version`: must be `task_contract_v1`.
- `task_id`: stable repository-local task identifier.
- `title`: short operator-readable title.
- `objective_digest`: digest of the operator objective.
- `input_digest`: digest of the accepted input descriptor.
- `policy_version`: policy version used for admission.
- `created_at`: metadata timestamp excluded from deterministic hashes.

## Optional Fields

- `operator_note_digest`: digest of bounded operator notes.
- `source_refs`: list of repository-relative evidence references.
- `labels`: bounded labels for review and search.

## Version

The only valid version for this contract is `task_contract_v1`.

## Immutability Rule

Accepted task records must not be mutated. Later changes require a new receipt
that references the original `task_id`.

## Unknown Field Policy

Consumers must reject unknown fields and fail closed before any task can be
approved or run.

## Compatibility Rule

Compatible readers may ignore optional fields only after validating all required
fields and the exact contract version.

## Migration/Deprecation Rule

Migration requires a new contract version, a compatibility note, and a
deterministic mapping from the old digest-only record to the new one.

## Valid Example

```json
{
  "contract_version": "task_contract_v1",
  "task_id": "task-readiness-001",
  "title": "Validate readiness evidence",
  "objective_digest": "sha256:1111111111111111111111111111111111111111111111111111111111111111",
  "input_digest": "sha256:2222222222222222222222222222222222222222222222222222222222222222",
  "policy_version": "operator_task_intake_v1",
  "created_at": "2026-05-30T00:00:00Z"
}
```

## Invalid Example

```json
{
  "contract_version": "task_contract_v1",
  "task_id": "",
  "title": "raw objective included",
  "objective": "do the thing directly",
  "input_digest": "not-a-digest",
  "policy_version": "operator_task_intake_v1"
}
```

The invalid example has an empty identity, a raw objective field, and a
malformed digest.

## Failure Behavior

Validation must fail closed, produce a rejection reason, and avoid creating an
approval, execution receipt, evidence trace, or success marker.
