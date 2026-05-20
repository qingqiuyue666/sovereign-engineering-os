# Master Pipeline Seal Contract

## Purpose
Aggregate all twelve layer contracts into the global scaffold seal.

## Contract Boundary
- This layer defines interfaces, schemas, reports, and validation gates only.
- This layer does not create final pixels, production renders, shaders, plates, or client deliverables.
- Maximum legal state: `HFX_MASTER_PIPELINE_SYSTEM_READY_NO_FINAL_PIXELS`.

## Required Inputs
- Layer manifests.
- Final pixel gate policy.
- Delivery blocker policy.

## Required Outputs
- HFX_MASTER_PIPELINE_GLOBAL_SEAL.json.

## Validation Gates
- All twelve layer directories must exist.
- Final pixel gate must remain fail-closed.
- Output state must be HFX_MASTER_PIPELINE_SYSTEM_READY_NO_FINAL_PIXELS.

## Failure Policy
All unresolved, missing, ambiguous, or unimplemented checks fail closed.
