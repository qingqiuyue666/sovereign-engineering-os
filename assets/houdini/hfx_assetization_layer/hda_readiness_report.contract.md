# HDA Readiness Report Contract

## Purpose
Record whether an HDA satisfies structural readiness checks before any production publish.

## Contract Boundary
- This layer defines interfaces, schemas, reports, and validation gates only.
- This layer does not create final pixels, production renders, shaders, plates, or client deliverables.
- Maximum legal state: `HFX_MASTER_PIPELINE_SYSTEM_READY_NO_FINAL_PIXELS`.

## Required Inputs
- HDA path.
- Readiness checklist.

## Required Outputs
- Blocked or ready-for-validation report.

## Validation Gates
- Missing checks block publish.
- Unresolved findings block seal.

## Failure Policy
All unresolved, missing, ambiguous, or unimplemented checks fail closed.
