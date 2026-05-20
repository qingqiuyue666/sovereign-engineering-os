# HFX Delivery Package Layer Global Seal Contract

## Purpose
Aggregate this layer's schemas, contracts, validators, and manifest into a fail-closed scaffold seal.

## Contract Boundary
- This layer defines interfaces, schemas, reports, and validation gates only.
- This layer does not create final pixels, production renders, shaders, plates, or client deliverables.
- Maximum legal state: `HFX_MASTER_PIPELINE_SYSTEM_READY_NO_FINAL_PIXELS`.

## Required Inputs
- Layer schema files.
- Layer Markdown contracts.
- Layer Python validator templates.
- Layer manifest.

## Required Outputs
- GLOBAL_SEAL.json
- GLOBAL_SEAL.contract.md
- global_seal_validator.py

## Validation Gates
- All required layer files must exist.
- Layer seal cannot authorize final pixels.
- Layer seal cannot authorize client delivery.

## Failure Policy
All unresolved, missing, ambiguous, or unimplemented checks fail closed.
