# Parameter Interface Contract

## Purpose
Define public controls, locked internals, parameter groups, and versioned defaults for HDAs.

## Contract Boundary
- This layer defines interfaces, schemas, reports, and validation gates only.
- This layer does not create final pixels, production renders, shaders, plates, or client deliverables.
- Maximum legal state: `HFX_MASTER_PIPELINE_SYSTEM_READY_NO_FINAL_PIXELS`.

## Required Inputs
- HDA parameter inventory.
- Artist-facing control requirements.

## Required Outputs
- Public interface registry for automation and review.

## Validation Gates
- Public controls are named.
- Locked parameters are declared.
- Defaults are versioned.

## Failure Policy
All unresolved, missing, ambiguous, or unimplemented checks fail closed.
