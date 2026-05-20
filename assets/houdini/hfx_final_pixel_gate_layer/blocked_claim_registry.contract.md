# Blocked Claim Registry Contract

## Purpose
Record attempted final-pixel claims and the reasons they remain blocked.

## Contract Boundary
- This layer defines interfaces, schemas, reports, and validation gates only.
- This layer does not create final pixels, production renders, shaders, plates, or client deliverables.
- Maximum legal state: `HFX_MASTER_PIPELINE_SYSTEM_READY_NO_FINAL_PIXELS`.

## Required Inputs
- Final pixel claim id.
- Shot id.
- Blocking reason.

## Required Outputs
- Blocked claim registry.

## Validation Gates
- Registry must preserve all blocked claim reasons.

## Failure Policy
All unresolved, missing, ambiguous, or unimplemented checks fail closed.
