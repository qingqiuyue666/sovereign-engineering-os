# Resource Manifest Contract

## Purpose
Capture resource identity, type, source, checksum, license, scope, and metadata.

## Contract Boundary
- This layer defines interfaces, schemas, reports, and validation gates only.
- This layer does not create final pixels, production renders, shaders, plates, or client deliverables.
- Maximum legal state: `HFX_MASTER_PIPELINE_SYSTEM_READY_NO_FINAL_PIXELS`.

## Required Inputs
- Incoming resource candidate.
- License id.

## Required Outputs
- Resource manifest pending license approval.

## Validation Gates
- Missing license blocks use.
- Missing source path blocks publish.

## Failure Policy
All unresolved, missing, ambiguous, or unimplemented checks fail closed.
