# Failed Frame Retry Contract

## Purpose
Define failed frame retry policy, frame list, and maximum attempts.

## Contract Boundary
- This layer defines interfaces, schemas, reports, and validation gates only.
- This layer does not create final pixels, production renders, shaders, plates, or client deliverables.
- Maximum legal state: `HFX_MASTER_PIPELINE_SYSTEM_READY_NO_FINAL_PIXELS`.

## Required Inputs
- Failed frame identifiers.
- Render job id.

## Required Outputs
- Retry request manifest.

## Validation Gates
- Unknown failure mode requires manual review.

## Failure Policy
All unresolved, missing, ambiguous, or unimplemented checks fail closed.
