# Execution Receipt V1

## Purpose

`execution_receipt_v1` records the result of a bounded local run. It is a receipt
for observed dry-run behavior, not proof of live provider execution or
production autonomy.

## Required Fields

- `contract_version`: must be `execution_receipt_v1`.
- `receipt_id`: stable execution receipt identifier.
- `task_id`: task being run.
- `run_id`: local run identifier.
- `dry_run`: must be true unless a later approved contract changes scope.
- `policy_version`: policy used for the run.
- `result`: `accepted` or `rejected`.
- `output_digest`: digest of bounded output evidence.

## Optional Fields

- `failure_ids`: list of failure bundle identifiers.
- `duration_ms`: bounded runtime metadata.
- `receipt_refs`: related repository-relative receipt references.

## Version

The only valid version for this contract is `execution_receipt_v1`.

## Immutability Rule

Accepted execution receipts must not be mutated. Corrections require a new
receipt linked to the original `receipt_id`.

## Unknown Field Policy

Consumers must reject unknown fields and fail closed before treating a run as
accepted.

## Compatibility Rule

Compatible readers may add optional metadata only when `dry_run`, `task_id`,
`run_id`, `result`, and `output_digest` remain stable.

## Migration/Deprecation Rule

Migration requires a new contract version and a deterministic receipt-chain
mapping.

## Valid Example

```json
{
  "contract_version": "execution_receipt_v1",
  "receipt_id": "exec-readiness-001",
  "task_id": "task-readiness-001",
  "run_id": "run-readiness-001",
  "dry_run": true,
  "policy_version": "runtime_runner_v1",
  "result": "accepted",
  "output_digest": "sha256:5555555555555555555555555555555555555555555555555555555555555555"
}
```

## Invalid Example

```json
{
  "contract_version": "execution_receipt_v1",
  "receipt_id": "exec-readiness-001",
  "task_id": "task-readiness-001",
  "run_id": "run-readiness-001",
  "dry_run": false,
  "result": "accepted",
  "output": "raw output"
}
```

The invalid example enables non-dry-run behavior and stores raw output instead
of an output digest.

## Failure Behavior

Validation must fail closed, mark the run rejected, and avoid emitting evidence
that looks like a successful execution.
