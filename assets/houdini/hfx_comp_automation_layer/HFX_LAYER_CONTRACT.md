# HFX Comp Automation Layer

## Purpose
Defines Nuke and Resolve comp template schemas without running comp applications.

## Status
This is a bureaucratic skeleton contract. It defines governance surfaces only and
does not authorize final-pixel production, renderer execution, compositing, or
loading of large production assets.

## Schemas
- `hfx_nuke_comp_template.schema.json`: Default schema for Nuke comp template contracts.
- `hfx_resolve_comp_template.schema.json`: Default schema for Resolve/Fusion comp template contracts.

## Required Gates
- Comp templates may reference render intents but not actual frame sequences.
- Color-management refs must be explicit before a template is admitted.
- The layer must not launch Nuke, Resolve, or media transcode jobs.

## Hard Prohibitions
- Do not load PBR texture payloads, VDB caches, HDRIs, EXR sequences, HIP files,
  comp timelines, or delivery media from this layer.
- Do not claim final pixels from this layer.
- Do not bypass the layer validator when one is later implemented.

## Validator
The generated validator template is `validate_hfx_comp_automation_layer.py`. It is empty by
design and must be filled with fail-closed checks before the layer can govern real
production work.
