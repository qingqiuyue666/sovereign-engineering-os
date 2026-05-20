# HFX AOV Pass Contract Layer

## Purpose
Defines the global AOV matrix required by render and comp layers.

## Status
This is a bureaucratic skeleton contract. It defines governance surfaces only and
does not authorize final-pixel production, renderer execution, compositing, or
loading of large production assets.

## Schemas
- `hfx_global_aov_matrix.schema.json`: Default schema for the global render pass and AOV contract.

## Required Gates
- Every AOV must declare channel type, bit depth, color role, and ownership.
- AOV additions require contract review before render automation can reference them.
- The matrix describes intent only and does not inspect rendered frames.

## Hard Prohibitions
- Do not load PBR texture payloads, VDB caches, HDRIs, EXR sequences, HIP files,
  comp timelines, or delivery media from this layer.
- Do not claim final pixels from this layer.
- Do not bypass the layer validator when one is later implemented.

## Validator
The generated validator template is `validate_hfx_aov_pass_contract_layer.py`. It is empty by
design and must be filled with fail-closed checks before the layer can govern real
production work.
