# Shader Slot Registry Contract

## Purpose
Define named shader slots, semantics, required flags, and allowed value types.

## Contract Boundary
- This layer defines interfaces, schemas, reports, and validation gates only.
- This layer does not create final pixels, production renders, shaders, plates, or client deliverables.
- Maximum legal state: `HFX_MASTER_PIPELINE_SYSTEM_READY_NO_FINAL_PIXELS`.

## Required Inputs
- Renderer and show lookdev requirements.

## Required Outputs
- Versioned shader slot registry.

## Validation Gates
- Missing required slots block material validation.

## Failure Policy
All unresolved, missing, ambiguous, or unimplemented checks fail closed.
