# Dry-Run Expansion Freeze V1

The dry-run layer is complete at `WORKFLOW_DRY_RUN_PLANNING_READY`.
Future work must stop adding dry-run-only surfaces and must move toward
controlled execution closure, evidence strengthening, risk reduction, use case
validation, or simplification.

## Freeze Rule

No new dry-run-only abstraction may enter main unless an explicit exception
shows the use case, the execution or evidence gap, the risk reduction claim,
the evidence output, the rollback or failure boundary, and the reviewer reason.

## Allowed PR Classes

- Execution Closure
- Risk Reduction
- Evidence Strengthening
- Prune / Archive / Simplification
- Use Case Validation

## Disallowed PR Classes

- new dry-run-only abstraction
- new future adapter placeholder
- governance-only vision expansion
- operator snapshot proliferation
- pure naming upgrade
- abstraction without use case mapping
- docs-only roadmap inflation

## Admission Rule

Every new abstraction must delete more complexity than it adds, or must close a
real execution, evidence, or risk gap. This policy does not require mutation of
existing modules; it is a repository-level admission boundary for future work.

## Exception Packet

Every exception must include:

- `use_case_id`
- `execution_gap`
- `risk_reduction_claim`
- `evidence_output`
- `rollback_or_failure_boundary`
- `reviewer_reason`

An exception that cannot name a use case and evidence output is not an
exception; it is abstraction drift.
