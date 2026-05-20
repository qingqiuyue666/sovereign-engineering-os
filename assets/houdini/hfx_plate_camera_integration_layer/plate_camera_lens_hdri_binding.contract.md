# Plate Camera Lens HDRI Binding Contract

## Purpose
Bind plates, cameras, lens metadata, and HDRIs into a single shot integration envelope.

## Contract Boundary
- This layer defines interfaces, schemas, reports, and validation gates only.
- This layer does not create final pixels, production renders, shaders, plates, or client deliverables.
- Maximum legal state: `HFX_MASTER_PIPELINE_SYSTEM_READY_NO_FINAL_PIXELS`.

## Required Inputs
- Shot id.
- Plate path.
- Camera path.
- Lens metadata.
- HDRI path.

## Required Outputs
- Shot integration binding manifest.

## Validation Gates
- Missing camera, lens, plate, or HDRI metadata blocks integration approval.

## Failure Policy
All unresolved, missing, ambiguous, or unimplemented checks fail closed.
