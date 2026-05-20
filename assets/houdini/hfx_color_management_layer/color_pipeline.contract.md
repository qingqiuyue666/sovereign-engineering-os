# Color Pipeline Contract

## Purpose
Define working space, display transform, OCIO config pointer, and LUT registry.

## Contract Boundary
- This layer defines interfaces, schemas, reports, and validation gates only.
- This layer does not create final pixels, production renders, shaders, plates, or client deliverables.
- Maximum legal state: `HFX_MASTER_PIPELINE_SYSTEM_READY_NO_FINAL_PIXELS`.

## Required Inputs
- Show id.
- OCIO config path or placeholder id.

## Required Outputs
- Color pipeline manifest.

## Validation Gates
- Missing OCIO config blocks production color approval.

## Failure Policy
All unresolved, missing, ambiguous, or unimplemented checks fail closed.
