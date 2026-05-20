# Final Pixel Gate Contract

## Purpose
Prevent any final-pixel claim from passing in the scaffold state.

## Contract Boundary
- This layer defines interfaces, schemas, reports, and validation gates only.
- This layer does not create final pixels, production renders, shaders, plates, or client deliverables.
- Maximum legal state: `HFX_MASTER_PIPELINE_SYSTEM_READY_NO_FINAL_PIXELS`.

## Required Inputs
- Final pixel claim envelope.
- Verified real EXR evidence from production validators.

## Required Outputs
- Blocked claim report.
- Blocked claim registry update.

## Validation Gates
- No verified real EXRs means blocked.
- Metadata alone means blocked.
- Bootstrap scaffold never authorizes final pixels.

## Failure Policy
All unresolved, missing, ambiguous, or unimplemented checks fail closed.
