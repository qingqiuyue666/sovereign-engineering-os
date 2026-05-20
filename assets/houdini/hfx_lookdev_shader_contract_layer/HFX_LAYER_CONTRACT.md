# HFX Lookdev Shader Contract Layer

## Purpose
Defines material binding and shader parameter contracts for lookdev handoff.

## Status
This is a bureaucratic skeleton contract. It defines governance surfaces only and
does not authorize final-pixel production, renderer execution, compositing, or
loading of large production assets.

## Schemas
- `hfx_material_binding.schema.json`: Default schema for logical material-to-geometry binding.
- `hfx_shader_parameter_contract.schema.json`: Default schema for shader parameter declarations.

## Required Gates
- Material bindings must target logical geometry queries, not loaded geometry.
- Texture slots may reference only catalog IDs or logical resource refs.
- Shader parameter contracts must declare defaults and review ownership.

## Hard Prohibitions
- Do not load PBR texture payloads, VDB caches, HDRIs, EXR sequences, HIP files,
  comp timelines, or delivery media from this layer.
- Do not claim final pixels from this layer.
- Do not bypass the layer validator when one is later implemented.

## Validator
The generated validator template is `validate_hfx_lookdev_shader_contract_layer.py`. It is empty by
design and must be filled with fail-closed checks before the layer can govern real
production work.
