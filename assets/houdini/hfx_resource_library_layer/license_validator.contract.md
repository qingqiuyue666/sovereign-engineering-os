# License Validator Contract

## Purpose
Gate resource use against permitted uses, restricted uses, expiry, and production scope.

## Contract Boundary
- This layer defines interfaces, schemas, reports, and validation gates only.
- This layer does not create final pixels, production renders, shaders, plates, or client deliverables.
- Maximum legal state: `HFX_MASTER_PIPELINE_SYSTEM_READY_NO_FINAL_PIXELS`.

## Required Inputs
- License record.
- Resource manifest usage scope.

## Required Outputs
- Valid, expired, or blocked license status.

## Validation Gates
- Expired or ambiguous license blocks downstream use.

## Failure Policy
All unresolved, missing, ambiguous, or unimplemented checks fail closed.
