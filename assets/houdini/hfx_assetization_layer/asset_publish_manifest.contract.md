# Asset Publish Manifest Contract

## Purpose
Describe the minimum data required before an HFX asset can enter the publish validation queue.

## Contract Boundary
- This layer defines interfaces, schemas, reports, and validation gates only.
- This layer does not create final pixels, production renders, shaders, plates, or client deliverables.
- Maximum legal state: `HFX_MASTER_PIPELINE_SYSTEM_READY_NO_FINAL_PIXELS`.

## Required Inputs
- Asset id, HDA path, publish version, dependency list.

## Required Outputs
- Validated manifest envelope for downstream gates.

## Validation Gates
- Asset id pattern is stable.
- Publish version is explicit.
- Dependencies are declared.

## Failure Policy
All unresolved, missing, ambiguous, or unimplemented checks fail closed.
