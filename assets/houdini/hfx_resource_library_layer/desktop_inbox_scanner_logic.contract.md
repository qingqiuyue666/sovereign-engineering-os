# Desktop Inbox Scanner Logic Contract

## Purpose
Describe scanner roots, extension filters, dedupe strategy, and quarantine policy for resource intake.

## Contract Boundary
- This layer defines interfaces, schemas, reports, and validation gates only.
- This layer does not create final pixels, production renders, shaders, plates, or client deliverables.
- Maximum legal state: `HFX_MASTER_PIPELINE_SYSTEM_READY_NO_FINAL_PIXELS`.

## Required Inputs
- Desktop inbox paths.
- Allowed extension list.

## Required Outputs
- Scanned resource candidate envelope.

## Validation Gates
- Unknown extensions quarantine.
- Duplicates require deterministic handling.

## Failure Policy
All unresolved, missing, ambiguous, or unimplemented checks fail closed.
