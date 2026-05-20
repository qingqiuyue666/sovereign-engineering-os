# Contact Sheet Contract

## Purpose
Define source media, layout, and burn-ins for contact sheet generation.

## Contract Boundary
- This layer defines interfaces, schemas, reports, and validation gates only.
- This layer does not create final pixels, production renders, shaders, plates, or client deliverables.
- Maximum legal state: `HFX_MASTER_PIPELINE_SYSTEM_READY_NO_FINAL_PIXELS`.

## Required Inputs
- Review media.
- Layout profile.
- Burn-in metadata.

## Required Outputs
- Contact sheet manifest.

## Validation Gates
- Missing source media blocks contact sheet generation.

## Failure Policy
All unresolved, missing, ambiguous, or unimplemented checks fail closed.
