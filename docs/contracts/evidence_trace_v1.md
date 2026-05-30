# Evidence Trace V1

## Purpose

`evidence_trace_v1` describes the ordered digest-only chain connecting task,
approval, execution, replay, and failure evidence. It supports review without
embedding raw task content or secrets.

## Required Fields

- `contract_version`: must be `evidence_trace_v1`.
- `trace_id`: stable trace identifier.
- `task_id`: task being traced.
- `run_id`: local run identifier.
- `trace_status`: `complete`, `incomplete`, or `rejected`.
- `receipt_refs`: ordered repository-relative receipt references.
- `generated_at`: metadata timestamp excluded from deterministic hashes.

## Optional Fields

- `missing_refs`: expected references not present.
- `trace_digest`: digest of the ordered trace payload.
- `review_note_digest`: digest of a human review note.

## Version

The only valid version for this contract is `evidence_trace_v1`.

## Immutability Rule

Accepted evidence traces must not be mutated. A corrected trace must be a new
trace that references the superseded trace.

## Unknown Field Policy

Consumers must reject unknown fields and fail closed before declaring a trace
complete.

## Compatibility Rule

Compatible readers may accept new optional review metadata only when the ordered
receipt references and trace status are unchanged.

## Migration/Deprecation Rule

Migration requires a new contract version and a deterministic mapping for trace
ids and receipt reference order.

## Valid Example

```json
{
  "contract_version": "evidence_trace_v1",
  "trace_id": "trace-readiness-001",
  "task_id": "task-readiness-001",
  "run_id": "run-readiness-001",
  "trace_status": "complete",
  "receipt_refs": [
    "reports/example/approval_receipt.json",
    "reports/example/execution_receipt.json"
  ],
  "generated_at": "2026-05-30T00:03:00Z"
}
```

## Invalid Example

```json
{
  "contract_version": "evidence_trace_v1",
  "trace_id": "trace-readiness-001",
  "task_id": "task-readiness-001",
  "trace_status": "complete",
  "receipt_refs": []
}
```

The invalid example claims completion without receipt references or a run id.

## Failure Behavior

Validation must fail closed, report the missing evidence, and avoid producing a
complete trace marker.
