# DaVinci Resolve Instruction Generator Contract

## Purpose
Describe the manifest used to generate DaVinci Resolve timeline and color handoff instructions.

## Contract Boundary
- This layer defines interfaces, schemas, reports, and validation gates only.
- This layer does not create final pixels, production renders, shaders, plates, or client deliverables.
- Maximum legal state: `HFX_MASTER_PIPELINE_SYSTEM_READY_NO_FINAL_PIXELS`.

## Required Inputs
- Review media.
- Color pipeline contract.

## Required Outputs
- DaVinci Resolve instruction manifest.

## Validation Gates
- Missing color pipeline blocks generation.

## Failure Policy
All unresolved, missing, ambiguous, or unimplemented checks fail closed.
