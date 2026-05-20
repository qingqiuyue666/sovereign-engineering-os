# Twelve Asset AOV Contract

## Purpose
Lock the required AOV profile for exactly twelve assets before render automation can proceed.

## Contract Boundary
- This layer defines interfaces, schemas, reports, and validation gates only.
- This layer does not create final pixels, production renders, shaders, plates, or client deliverables.
- Maximum legal state: `HFX_MASTER_PIPELINE_SYSTEM_READY_NO_FINAL_PIXELS`.

## Required Inputs
- Twelve asset ids.
- Required and optional AOV names.

## Required Outputs
- Per-asset AOV contract.

## Validation Gates
- Asset count must be exactly twelve.
- Required AOVs must be explicit.

## Failure Policy
All unresolved, missing, ambiguous, or unimplemented checks fail closed.
