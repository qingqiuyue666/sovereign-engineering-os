# Global AOV Matrix Contract

## Purpose
Centralize renderer-agnostic AOV names, data types, and required flags.

## Contract Boundary
- This layer defines interfaces, schemas, reports, and validation gates only.
- This layer does not create final pixels, production renders, shaders, plates, or client deliverables.
- Maximum legal state: `HFX_MASTER_PIPELINE_SYSTEM_READY_NO_FINAL_PIXELS`.

## Required Inputs
- Renderer targets.
- AOV semantic definitions.

## Required Outputs
- Global matrix consumed by render and comp layers.

## Validation Gates
- Unsupported data types block validation.
- Missing required AOVs block render submission.

## Failure Policy
All unresolved, missing, ambiguous, or unimplemented checks fail closed.
