# Delivery Manifest Contract

## Purpose
Describe delivery ids, client ids, items, color pipeline link, and final-pixel claim status.

## Contract Boundary
- This layer defines interfaces, schemas, reports, and validation gates only.
- This layer does not create final pixels, production renders, shaders, plates, or client deliverables.
- Maximum legal state: `HFX_MASTER_PIPELINE_SYSTEM_READY_NO_FINAL_PIXELS`.

## Required Inputs
- Client id.
- Delivery item list.
- Color pipeline contract.

## Required Outputs
- Delivery manifest.

## Validation Gates
- Final pixel claim status must remain blocked in scaffold state.

## Failure Policy
All unresolved, missing, ambiguous, or unimplemented checks fail closed.
