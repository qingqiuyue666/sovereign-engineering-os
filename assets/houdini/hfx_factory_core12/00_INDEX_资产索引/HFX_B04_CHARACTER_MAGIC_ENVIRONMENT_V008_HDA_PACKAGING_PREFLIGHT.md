# HFX Batch 04 Character Magic Environment v008 HDA Packaging Preflight

Status: HFX_B04_CHARACTER_MAGIC_ENVIRONMENT_V008_HDA_PACKAGING_PREFLIGHT_READY

Purpose:
Validate HDA packaging readiness before building Batch 04 HDA files.

Preflight Rules:
- v003 HIP must exist.
- v004 production spec must exist.
- v005 hero upgrade candidate spec must exist.
- v006 effect interface spec must exist.
- v007 wrapper spec must exist.
- Wrapper HDA type must be stable and versioned as ::4.0.
- Preview mode must be enabled by default.
- Hero mode must be blocked by default.
- Cache execution must be blocked by default.
- Comp pass flattening must be forbidden.
- OUT_TRIGGER_METADATA must be present.
- This stage does not package HDA files.

