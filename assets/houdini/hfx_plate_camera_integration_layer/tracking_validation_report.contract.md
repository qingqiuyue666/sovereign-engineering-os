# Tracking Validation Report Contract

## Purpose
Record tracking source, validation checks, approval flag, and blocking findings.

## Contract Boundary
- This layer defines interfaces, schemas, reports, and validation gates only.
- This layer does not create final pixels, production renders, shaders, plates, or client deliverables.
- Maximum legal state: `HFX_MASTER_PIPELINE_SYSTEM_READY_NO_FINAL_PIXELS`.

## Required Inputs
- Tracking export.
- Shot integration binding.

## Required Outputs
- Blocked or ready-for-validation tracking report.

## Validation Gates
- Unapproved tracking blocks render automation.

## Failure Policy
All unresolved, missing, ambiguous, or unimplemented checks fail closed.
