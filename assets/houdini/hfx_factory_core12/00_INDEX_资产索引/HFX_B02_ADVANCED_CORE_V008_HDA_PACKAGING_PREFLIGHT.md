# HFX Batch 02 Advanced Core v008 HDA Packaging Preflight

Status: HFX_B02_ADVANCED_CORE_V008_HDA_PACKAGING_PREFLIGHT_READY

Purpose:
Validate that all Batch 02 advanced FX assets are ready for HDA wrapper construction and packaging.

Preflight Rules:
- v003 HIP must exist.
- v004 production spec must exist.
- v005 HDA candidate spec must exist.
- v006 HDA interface spec must exist.
- v007 wrapper spec must exist.
- HDA type must remain stable.
- Wrapper name must remain stable.
- Stable outputs must include OUT_TRIGGER_METADATA.
- No video/archive/macOS pollution.
- This stage does not package HDA yet.

## Assets

### HFX_009_Volumetric_Fog_Bank

- HDA Type: `qqy::hfx_volumetric_fog_bank::2.0`
- Wrapper Name: `WRAP_HFX_009_Volumetric_Fog_Bank_v007`
- Main Output: `OUT_FOG_BANK_MAIN`
- Stable Outputs: OUT_FOG_BANK_MAIN, OUT_DENSITY_ONLY, OUT_LIGHT_BEAM_MASK, OUT_DEPTH_FADE_MASK, OUT_TRIGGER_METADATA

### HFX_010_Smoke_Plume_Column

- HDA Type: `qqy::hfx_smoke_plume_column::2.0`
- Wrapper Name: `WRAP_HFX_010_Smoke_Plume_Column_v007`
- Main Output: `OUT_SMOKE_PLUME_MAIN`
- Stable Outputs: OUT_SMOKE_PLUME_MAIN, OUT_DENSITY_ONLY, OUT_TOP_ROLL, OUT_BASE_SPREAD, OUT_TRIGGER_METADATA

### HFX_011_Ember_Ash_Field

- HDA Type: `qqy::hfx_ember_ash_field::2.0`
- Wrapper Name: `WRAP_HFX_011_Ember_Ash_Field_v007`
- Main Output: `OUT_EMBER_ASH_MAIN`
- Stable Outputs: OUT_EMBER_ASH_MAIN, OUT_EMBERS_ONLY, OUT_ASH_ONLY, OUT_FOREGROUND_LAYER, OUT_TRIGGER_METADATA

### HFX_012_Sparks_Impact_Spray

- HDA Type: `qqy::hfx_sparks_impact_spray::2.0`
- Wrapper Name: `WRAP_HFX_012_Sparks_Impact_Spray_v007`
- Main Output: `OUT_SPARKS_MAIN`
- Stable Outputs: OUT_SPARKS_MAIN, OUT_HOT_SPARKS, OUT_TRAILS_ONLY, OUT_CONTACT_FLASH, OUT_TRIGGER_METADATA

### HFX_013_Debris_Burst_Radial

- HDA Type: `qqy::hfx_debris_burst_radial::2.0`
- Wrapper Name: `WRAP_HFX_013_Debris_Burst_Radial_v007`
- Main Output: `OUT_DEBRIS_BURST_MAIN`
- Stable Outputs: OUT_DEBRIS_BURST_MAIN, OUT_LARGE_DEBRIS, OUT_SMALL_DEBRIS, OUT_DUST_PROXY, OUT_TRIGGER_METADATA

### HFX_014_Magic_Particle_Aura

- HDA Type: `qqy::hfx_magic_particle_aura::2.0`
- Wrapper Name: `WRAP_HFX_014_Magic_Particle_Aura_v007`
- Main Output: `OUT_MAGIC_AURA_MAIN`
- Stable Outputs: OUT_MAGIC_AURA_MAIN, OUT_CORE_PARTICLES, OUT_ORBITING_PARTICLES, OUT_GLOW_FIELD, OUT_TRIGGER_METADATA

### HFX_015_Portal_Ring_Field

- HDA Type: `qqy::hfx_portal_ring_field::2.0`
- Wrapper Name: `WRAP_HFX_015_Portal_Ring_Field_v007`
- Main Output: `OUT_PORTAL_RING_MAIN`
- Stable Outputs: OUT_PORTAL_RING_MAIN, OUT_RING_CORE, OUT_EDGE_SPARKS, OUT_DISTORTION_MASK, OUT_TRIGGER_METADATA

### HFX_016_Heat_Distortion_Field

- HDA Type: `qqy::hfx_heat_distortion_field::2.0`
- Wrapper Name: `WRAP_HFX_016_Heat_Distortion_Field_v007`
- Main Output: `OUT_HEAT_DISTORTION_MAIN`
- Stable Outputs: OUT_HEAT_DISTORTION_MAIN, OUT_VECTOR_FIELD, OUT_MASK_ONLY, OUT_NOISE_FIELD, OUT_TRIGGER_METADATA

