# HFX Resource Library Layer

## Purpose
Defines a desktop inbox scanner manifest for cataloging candidate resources without loading or decoding large files.

## Status
This is a bureaucratic skeleton contract. It defines governance surfaces only and
does not authorize final-pixel production, renderer execution, compositing, or
loading of large production assets.

## Schemas
- `hfx_desktop_inbox_scanner_manifest.schema.json`: Default schema for lightweight resource inbox scanning.

## Required Gates
- Scanner manifests must declare roots as logical references.
- Scanner policies must forbid binary payload reads during skeleton validation.
- Quarantine rules must exist before any resource is promoted.

## Hard Prohibitions
- Do not load PBR texture payloads, VDB caches, HDRIs, EXR sequences, HIP files,
  comp timelines, or delivery media from this layer.
- Do not claim final pixels from this layer.
- Do not bypass the layer validator when one is later implemented.

## Validator
The generated validator template is `validate_hfx_resource_library_layer.py`. It is empty by
design and must be filled with fail-closed checks before the layer can govern real
production work.
