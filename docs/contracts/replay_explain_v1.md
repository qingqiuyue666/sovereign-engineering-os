# Replay Explain V1

## Purpose

`replay_explain_v1` records what a replay can and cannot reconstruct from
digest-only evidence. It explains receipt relationships without claiming access
to raw hidden context.

## Required Fields

- `contract_version`: must be `replay_explain_v1`.
- `replay_id`: stable replay explanation identifier.
- `trace_id`: evidence trace being explained.
- `task_id`: task being explained.
- `replay_status`: `reconstructable`, `partial`, or `impossible`.
- `source_receipt_refs`: repository-relative receipt references.
- `explanation_digest`: digest of the explanation text.

## Optional Fields

- `limitations`: bounded explanation limitations.
- `missing_refs`: evidence references required for reconstruction.
- `generated_at`: metadata timestamp excluded from deterministic hashes.

## Version

The only valid version for this contract is `replay_explain_v1`.

## Immutability Rule

Accepted replay explanations must not be mutated. Updated explanations require a
new `replay_id`.

## Unknown Field Policy

Consumers must reject unknown fields and fail closed before claiming replay
reconstruction.

## Compatibility Rule

Compatible readers may add optional limitations only when replay status and
source receipt references remain stable.

## Migration/Deprecation Rule

Migration requires a new contract version and a mapping from old replay ids to
new replay ids.

## Valid Example

```json
{
  "contract_version": "replay_explain_v1",
  "replay_id": "replay-readiness-001",
  "trace_id": "trace-readiness-001",
  "task_id": "task-readiness-001",
  "replay_status": "reconstructable",
  "source_receipt_refs": [
    "reports/example/evidence_trace.json"
  ],
  "explanation_digest": "sha256:6666666666666666666666666666666666666666666666666666666666666666"
}
```

## Invalid Example

```json
{
  "contract_version": "replay_explain_v1",
  "replay_id": "replay-readiness-001",
  "trace_id": "trace-readiness-001",
  "task_id": "task-readiness-001",
  "replay_status": "reconstructable",
  "source_receipt_refs": [],
  "explanation": "replay works"
}
```

The invalid example claims reconstruction with no source receipts and stores raw
explanation text instead of a digest.

## Failure Behavior

Validation must fail closed and report `impossible` or `partial` rather than
claiming a reconstructable replay.
