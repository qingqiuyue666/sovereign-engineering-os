# HFX Review Dailies Layer

## Purpose
Defines dailies manifests and QC checklist schemas for review gates.

## Status
This is a bureaucratic skeleton contract. It defines governance surfaces only and
does not authorize final-pixel production, renderer execution, compositing, or
loading of large production assets.

## Schemas
- `hfx_dailies_manifest.schema.json`: Default schema for daily review submission manifests.
- `hfx_qc_checklist.schema.json`: Default schema for review and dailies QC checklists.

## Required Gates
- Dailies manifests must reference media logically and cannot inspect encoded media.
- QC checklist items must declare severity, required status, and waiver state.
- Review approval does not imply final-pixel acceptance while the master seal blocks it.

## Hard Prohibitions
- Do not load PBR texture payloads, VDB caches, HDRIs, EXR sequences, HIP files,
  comp timelines, or delivery media from this layer.
- Do not claim final pixels from this layer.
- Do not bypass the layer validator when one is later implemented.

## Validator
The generated validator template is `validate_hfx_review_dailies_layer.py`. It is empty by
design and must be filled with fail-closed checks before the layer can govern real
production work.
