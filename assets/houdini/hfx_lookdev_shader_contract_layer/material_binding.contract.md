# Material Binding Contract

## Purpose
Map geometry paths to material ids and shader slot profiles.

## Contract Boundary
- This layer defines interfaces, schemas, reports, and validation gates only.
- This layer does not create final pixels, production renders, shaders, plates, or client deliverables.
- Maximum legal state: `HFX_MASTER_PIPELINE_SYSTEM_READY_NO_FINAL_PIXELS`.

## Required Inputs
- Asset geometry paths.
- Shader slot registry.

## Required Outputs
- Material binding manifest.

## Validation Gates
- Unbound geometry follows explicit block or warning policy.

## Failure Policy
All unresolved, missing, ambiguous, or unimplemented checks fail closed.
