# Dailies Report Contract

## Purpose
Record reviewed items, session id, and decisions from a dailies session.

## Contract Boundary
- This layer defines interfaces, schemas, reports, and validation gates only.
- This layer does not create final pixels, production renders, shaders, plates, or client deliverables.
- Maximum legal state: `HFX_MASTER_PIPELINE_SYSTEM_READY_NO_FINAL_PIXELS`.

## Required Inputs
- Review package ids.
- Session id.

## Required Outputs
- Dailies report manifest.

## Validation Gates
- Unresolved decisions remain non-delivery blockers until explicitly cleared.

## Failure Policy
All unresolved, missing, ambiguous, or unimplemented checks fail closed.
