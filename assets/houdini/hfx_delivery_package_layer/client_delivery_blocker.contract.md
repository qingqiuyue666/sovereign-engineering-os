# Client Delivery Blocker Contract

## Purpose
Block client delivery while final pixel gates and production content remain unavailable.

## Contract Boundary
- This layer defines interfaces, schemas, reports, and validation gates only.
- This layer does not create final pixels, production renders, shaders, plates, or client deliverables.
- Maximum legal state: `HFX_MASTER_PIPELINE_SYSTEM_READY_NO_FINAL_PIXELS`.

## Required Inputs
- Delivery manifest.
- Final pixel gate result.

## Required Outputs
- Client delivery blocker record.

## Validation Gates
- Blocked final pixels block client delivery.
- Missing delivery item evidence blocks delivery.

## Failure Policy
All unresolved, missing, ambiguous, or unimplemented checks fail closed.
