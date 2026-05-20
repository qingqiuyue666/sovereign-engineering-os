# ACES OCIO Placeholder Contract

## Purpose
Record that ACES/OCIO exists only as a scaffold placeholder until a real config is approved.

## Contract Boundary
- This layer defines interfaces, schemas, reports, and validation gates only.
- This layer does not create final pixels, production renders, shaders, plates, or client deliverables.
- Maximum legal state: `HFX_MASTER_PIPELINE_SYSTEM_READY_NO_FINAL_PIXELS`.

## Required Inputs
- ACES version.
- OCIO version.
- Placeholder id.

## Required Outputs
- Blocked placeholder contract.

## Validation Gates
- Placeholder cannot authorize final pixels or client delivery.

## Failure Policy
All unresolved, missing, ambiguous, or unimplemented checks fail closed.
