# Failure Bundle V1

## Purpose

`failure_bundle_v1` records bounded failure evidence for a task or run. It keeps
raw stderr, stdout, paths, prompts, and secret material out of the committed
failure record.

## Required Fields

- `contract_version`: must be `failure_bundle_v1`.
- `failure_id`: stable failure bundle identifier.
- `task_id`: task associated with the failure.
- `run_id`: run associated with the failure.
- `failure_class`: bounded failure category.
- `evidence_digests`: non-empty list of evidence digests.
- `quarantine_required`: boolean quarantine decision.

## Optional Fields

- `retry_allowed`: boolean retry policy.
- `rollback_plan_digest`: digest of a rollback plan.
- `created_at`: metadata timestamp excluded from deterministic hashes.

## Version

The only valid version for this contract is `failure_bundle_v1`.

## Immutability Rule

Accepted failure bundles must not be mutated. Additional evidence requires a new
bundle linked to the original failure id.

## Unknown Field Policy

Consumers must reject unknown fields and fail closed before treating a failure
as retryable or resolved.

## Compatibility Rule

Compatible readers may add optional rollback metadata only when failure class,
evidence digests, and quarantine decision remain stable.

## Migration/Deprecation Rule

Migration requires a new contract version and a deterministic mapping for
failure ids and evidence digests.

## Valid Example

```json
{
  "contract_version": "failure_bundle_v1",
  "failure_id": "failure-readiness-001",
  "task_id": "task-readiness-001",
  "run_id": "run-readiness-001",
  "failure_class": "policy_blocked",
  "evidence_digests": [
    "sha256:7777777777777777777777777777777777777777777777777777777777777777"
  ],
  "quarantine_required": true
}
```

## Invalid Example

```json
{
  "contract_version": "failure_bundle_v1",
  "failure_id": "failure-readiness-001",
  "task_id": "task-readiness-001",
  "run_id": "run-readiness-001",
  "failure_class": "policy_blocked",
  "raw_stderr": "traceback text",
  "quarantine_required": false
}
```

The invalid example stores raw stderr and omits digest-only evidence.

## Failure Behavior

Validation must fail closed, require quarantine when evidence is malformed, and
avoid printing any pass marker for the failed path.
