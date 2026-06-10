# HFX Assetization Layer

## Purpose
Defines publish manifests and HDA readiness surfaces for Houdini assets before any renderer or large asset payload is touched.

## Status
This is a bureaucratic skeleton contract. It defines governance surfaces only and
does not authorize final-pixel production, renderer execution, compositing, or
loading of large production assets.

## Schemas
- `hfx_publish_manifest.schema.json`: Default schema for a lightweight Houdini publish manifest.
- `hfx_hda_readiness.schema.json`: Default schema for declaring HDA interface readiness.

## Required Gates
- Every publish manifest declares asset identity, version, ownership, and blocked claims.
- HDA readiness must be explicit before an asset can be routed downstream.
- The layer may only reference logical artifacts, not binary production payloads.

## Hard Prohibitions
- Do not load PBR texture payloads, VDB caches, HDRIs, EXR sequences, HIP files,
  comp timelines, or delivery media from this layer.
- Do not claim final pixels from this layer.
- Do not bypass the layer validator when one is later implemented.

## Validator
The generated validator template is `validate_hfx_assetization_layer.py`. It is empty by
design and must be filled with fail-closed checks before the layer can govern real
production work.
