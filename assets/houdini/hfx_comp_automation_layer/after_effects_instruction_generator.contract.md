# After Effects Instruction Generator Contract

## Purpose
Describe the manifest used to generate After Effects project instructions.

## Contract Boundary
- This layer defines interfaces, schemas, reports, and validation gates only.
- This layer does not create final pixels, production renders, shaders, plates, or client deliverables.
- Maximum legal state: `HFX_MASTER_PIPELINE_SYSTEM_READY_NO_FINAL_PIXELS`.

## Required Inputs
- Review media.
- Plate or render inputs.

## Required Outputs
- After Effects instruction manifest.

## Validation Gates
- Unsupported input media blocks generation.

## Failure Policy
All unresolved, missing, ambiguous, or unimplemented checks fail closed.
