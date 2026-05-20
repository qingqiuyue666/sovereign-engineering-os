# Render Validation Contract

## Purpose
Collect pre-submit render checks and frame blockers.

## Contract Boundary
- This layer defines interfaces, schemas, reports, and validation gates only.
- This layer does not create final pixels, production renders, shaders, plates, or client deliverables.
- Maximum legal state: `HFX_MASTER_PIPELINE_SYSTEM_READY_NO_FINAL_PIXELS`.

## Required Inputs
- Render job manifest.
- Upstream AOV and integration contracts.

## Required Outputs
- Approved or blocked submission report.

## Validation Gates
- Failed validation blocks farm submission.

## Failure Policy
All unresolved, missing, ambiguous, or unimplemented checks fail closed.
