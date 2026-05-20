# Assetization Global Seal Contract

## Purpose
Aggregate the assetization contracts into a single local seal without authorizing final pixels.

## Contract Boundary
- This layer defines interfaces, schemas, reports, and validation gates only.
- This layer does not create final pixels, production renders, shaders, plates, or client deliverables.
- Maximum legal state: `HFX_MASTER_PIPELINE_SYSTEM_READY_NO_FINAL_PIXELS`.

## Required Inputs
- Asset manifest schema.
- Parameter interface schema.
- HDA readiness schema.

## Required Outputs
- Layer-level scaffold seal.

## Validation Gates
- Seal remains non-final-pixel.
- All missing child contracts block production seal.

## Failure Policy
All unresolved, missing, ambiguous, or unimplemented checks fail closed.
