# HFX Batch 05 Cinematic Compositing Render Passes v007 HDA Packaging Preflight

Status: HFX_B05_CINEMATIC_COMPOSITING_RENDER_PASSES_V007_HDA_PACKAGING_PREFLIGHT_READY

Purpose:
Validate HDA packaging readiness before building Batch 05 HDA files.

Preflight Rules:
- v003 HIP must exist.
- v004 production spec must exist.
- v005 render pass interface spec must exist.
- v006 wrapper spec must exist.
- Wrapper HDA type must be stable and versioned as ::5.0.
- Preview mode must be enabled by default.
- Render/export must be blocked by default.
- Cache/export execution must be blocked by default.
- EXR pass separation must be required.
- Comp pass flattening must be forbidden.
- OUT_TRIGGER_METADATA must be present.
- This stage does not package HDA files.

