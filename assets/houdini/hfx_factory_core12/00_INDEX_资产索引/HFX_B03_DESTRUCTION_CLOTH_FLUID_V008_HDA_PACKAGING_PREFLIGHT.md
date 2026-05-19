# HFX Batch 03 Destruction Cloth Fluid v008 HDA Packaging Preflight

Status: HFX_B03_DESTRUCTION_CLOTH_FLUID_V008_HDA_PACKAGING_PREFLIGHT_READY

Purpose:
Validate HDA packaging readiness before building Batch 03 HDA files.

Preflight Rules:
- v003 HIP must exist.
- v004 production spec must exist.
- v005 heavy solver candidate spec must exist.
- v006 solver interface spec must exist.
- v007 wrapper spec must exist.
- Wrapper HDA type must be stable and versioned as ::3.0.
- Preview mode must be enabled by default.
- Hero mode must be blocked by default.
- Cache execution must be blocked by default.
- OUT_TRIGGER_METADATA must be present.
- This stage does not package HDA files.

