# HFX Color Management Layer

## Purpose
Defines OCIO and ACES governance contracts for the pipeline.

## Status
This is a bureaucratic skeleton contract. It defines governance surfaces only and
does not authorize final-pixel production, renderer execution, compositing, or
loading of large production assets.

## Schemas
- `hfx_ocio_contract.schema.json`: Default schema for OpenColorIO contract declarations.
- `hfx_aces_contract.schema.json`: Default schema for ACES color pipeline declarations.

## Required Gates
- Color contracts must reference configs and transforms logically.
- Roles, display views, and interchange spaces must be declared before render or comp use.
- The layer must not load LUT payloads or OCIO config files during scaffold validation.

## Hard Prohibitions
- Do not load PBR texture payloads, VDB caches, HDRIs, EXR sequences, HIP files,
  comp timelines, or delivery media from this layer.
- Do not claim final pixels from this layer.
- Do not bypass the layer validator when one is later implemented.

## Validator
The generated validator template is `validate_hfx_color_management_layer.py`. It is empty by
design and must be filled with fail-closed checks before the layer can govern real
production work.
