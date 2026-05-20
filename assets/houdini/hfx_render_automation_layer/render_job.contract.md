# Render Job Contract

## Purpose
Declare renderer, shot, frame range, AOV contract, farm pool, and priority for render automation.

## Contract Boundary
- This layer defines interfaces, schemas, reports, and validation gates only.
- This layer does not create final pixels, production renders, shaders, plates, or client deliverables.
- Maximum legal state: `HFX_MASTER_PIPELINE_SYSTEM_READY_NO_FINAL_PIXELS`.

## Required Inputs
- Shot id.
- Frame range.
- AOV contract.

## Required Outputs
- Render job manifest.

## Validation Gates
- Missing AOV contract blocks submission.
- Unknown renderer blocks submission.

## Failure Policy
All unresolved, missing, ambiguous, or unimplemented checks fail closed.
