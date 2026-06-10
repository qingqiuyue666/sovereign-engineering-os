# HFX Master Pipeline Seal

## Purpose
Defines the locked global seal proving the scaffold is ready as a contract system while still forbidding final-pixel production.

## Status
This is a bureaucratic skeleton contract. It defines governance surfaces only and
does not authorize final-pixel production, renderer execution, compositing, or
loading of large production assets.

## Schemas
- `hfx_master_pipeline_global_seal.schema.json`: Default schema for the locked global no-final-pixels seal.

## Required Gates
- `HFX_MASTER_PIPELINE_GLOBAL_SEAL.json` status must equal `HFX_MASTER_PIPELINE_SYSTEM_READY_NO_FINAL_PIXELS`.
- The seal must list all 12 governed HFX layers.
- The seal must keep final-pixel execution and large asset loading blocked.

## Hard Prohibitions
- Do not load PBR texture payloads, VDB caches, HDRIs, EXR sequences, HIP files,
  comp timelines, or delivery media from this layer.
- Do not claim final pixels from this layer.
- Do not bypass the layer validator when one is later implemented.

## Validator
The generated validator template is `validate_hfx_master_pipeline_seal.py`. It is empty by
design and must be filled with fail-closed checks before the layer can govern real
production work.
