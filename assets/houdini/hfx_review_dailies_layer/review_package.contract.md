# Review Package Contract

## Purpose
Package reviewable media and notes for dailies and stakeholder review.

## Contract Boundary
- This layer defines interfaces, schemas, reports, and validation gates only.
- This layer does not create final pixels, production renders, shaders, plates, or client deliverables.
- Maximum legal state: `HFX_MASTER_PIPELINE_SYSTEM_READY_NO_FINAL_PIXELS`.

## Required Inputs
- Reviewable media ids.
- Shot id.
- Review targets.

## Required Outputs
- Review package manifest.

## Validation Gates
- Missing media blocks review package approval.

## Failure Policy
All unresolved, missing, ambiguous, or unimplemented checks fail closed.
