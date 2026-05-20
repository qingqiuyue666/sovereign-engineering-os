# Nuke Instruction Generator Contract

## Purpose
Describe the manifest used to generate Nuke scripts from approved render and plate inputs.

## Contract Boundary
- This layer defines interfaces, schemas, reports, and validation gates only.
- This layer does not create final pixels, production renders, shaders, plates, or client deliverables.
- Maximum legal state: `HFX_MASTER_PIPELINE_SYSTEM_READY_NO_FINAL_PIXELS`.

## Required Inputs
- Render products.
- Plate bindings.
- Color pipeline contract.

## Required Outputs
- Nuke instruction manifest.

## Validation Gates
- Missing render inputs block script generation.

## Failure Policy
All unresolved, missing, ambiguous, or unimplemented checks fail closed.
