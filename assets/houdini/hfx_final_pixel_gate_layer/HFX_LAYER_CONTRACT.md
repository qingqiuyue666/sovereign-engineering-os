# HFX Final Pixel Gate Layer

## Purpose
Defines the blocked claim registry that prevents premature final-pixel assertions.

## Status
This is a bureaucratic skeleton contract. It defines governance surfaces only and
does not authorize final-pixel production, renderer execution, compositing, or
loading of large production assets.

## Schemas
- `hfx_blocked_claim_registry.schema.json`: Default schema for final-pixel blocked claim governance.

## Required Gates
- Final-pixel claims must be registered as blocked unless explicitly cleared later.
- Blocked claims must include owner, reason, and the gate that can unblock them.
- The registry is a governance artifact and does not inspect final images.

## Hard Prohibitions
- Do not load PBR texture payloads, VDB caches, HDRIs, EXR sequences, HIP files,
  comp timelines, or delivery media from this layer.
- Do not claim final pixels from this layer.
- Do not bypass the layer validator when one is later implemented.

## Validator
The generated validator template is `validate_hfx_final_pixel_gate_layer.py`. It is empty by
design and must be filled with fail-closed checks before the layer can govern real
production work.
