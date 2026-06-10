# HFX Delivery Package Layer

## Purpose
Defines delivery manifest contracts without packaging final media.

## Status
This is a bureaucratic skeleton contract. It defines governance surfaces only and
does not authorize final-pixel production, renderer execution, compositing, or
loading of large production assets.

## Schemas
- `hfx_delivery_manifest.schema.json`: Default schema for delivery package governance.

## Required Gates
- Delivery manifests must enumerate intended deliverables and approvals.
- Checksum manifests must be referenced logically until real packaging is authorized.
- Delivery readiness cannot override the master no-final-pixels seal.

## Hard Prohibitions
- Do not load PBR texture payloads, VDB caches, HDRIs, EXR sequences, HIP files,
  comp timelines, or delivery media from this layer.
- Do not claim final pixels from this layer.
- Do not bypass the layer validator when one is later implemented.

## Validator
The generated validator template is `validate_hfx_delivery_package_layer.py`. It is empty by
design and must be filled with fail-closed checks before the layer can govern real
production work.
