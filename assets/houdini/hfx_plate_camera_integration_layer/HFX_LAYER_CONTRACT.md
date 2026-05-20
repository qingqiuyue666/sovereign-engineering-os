# HFX Plate Camera Integration Layer

## Purpose
Defines tracking, lens, and camera metadata contracts for shot integration.

## Status
This is a bureaucratic skeleton contract. It defines governance surfaces only and
does not authorize final-pixel production, renderer execution, compositing, or
loading of large production assets.

## Schemas
- `hfx_tracking_contract.schema.json`: Default schema for a tracking and camera solution contract.
- `hfx_lens_metadata.schema.json`: Default schema for lens and calibration metadata.

## Required Gates
- Plate, track, and lens references must be logical metadata refs.
- Frame ranges and coordinate systems must be explicit.
- No image sequence, solve cache, or lens grid payload may be loaded here.

## Hard Prohibitions
- Do not load PBR texture payloads, VDB caches, HDRIs, EXR sequences, HIP files,
  comp timelines, or delivery media from this layer.
- Do not claim final pixels from this layer.
- Do not bypass the layer validator when one is later implemented.

## Validator
The generated validator template is `validate_hfx_plate_camera_integration_layer.py`. It is empty by
design and must be filled with fail-closed checks before the layer can govern real
production work.
