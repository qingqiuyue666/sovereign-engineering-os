# HFX Render Automation Layer

## Purpose
Defines render job and retry contracts without executing renders.

## Status
This is a bureaucratic skeleton contract. It defines governance surfaces only and
does not authorize final-pixel production, renderer execution, compositing, or
loading of large production assets.

## Schemas
- `hfx_render_job.schema.json`: Default schema for render automation job declarations.
- `hfx_render_retry_policy.schema.json`: Default schema for render retry and escalation policy.

## Required Gates
- Render jobs must remain dry-run contracts until final-pixel gates are opened.
- Retry policies must be explicit before farm orchestration is connected.
- The layer must not invoke Houdini, hython, renderers, or file probes.

## Hard Prohibitions
- Do not load PBR texture payloads, VDB caches, HDRIs, EXR sequences, HIP files,
  comp timelines, or delivery media from this layer.
- Do not claim final pixels from this layer.
- Do not bypass the layer validator when one is later implemented.

## Validator
The generated validator template is `validate_hfx_render_automation_layer.py`. It is empty by
design and must be filled with fail-closed checks before the layer can govern real
production work.
