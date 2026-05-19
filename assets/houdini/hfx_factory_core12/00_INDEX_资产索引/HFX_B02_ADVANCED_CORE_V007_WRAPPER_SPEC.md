# HFX Batch 02 Advanced Core v007 Wrapper Spec

Status: HFX_B02_ADVANCED_CORE_V007_WRAPPER_SPEC_READY

Purpose:
Define wrapper construction rules before generating wrapper HIPs and final HDA packaging.

Wrapper Rules:
- Wrapper must reference the v003 procedural network as source authority.
- Wrapper must preserve all stable OUT nodes.
- Wrapper must not create external file/cache/export dependencies.
- Wrapper must forward timing and seed controls.
- Wrapper must forward metadata to OUT_TRIGGER_METADATA.
- Wrapper preview must work with no external inputs.
- Wrapper must not touch Batch 01 sealed release.

## Wrapper Targets

### HFX_009_Volumetric_Fog_Bank

- Wrapper Name: `WRAP_HFX_009_Volumetric_Fog_Bank_v007`
- Source Geo: `HFX_009_Volumetric_Fog_Bank_v003`
- HDA Type: `qqy::hfx_volumetric_fog_bank::2.0`
- Main Output: `OUT_FOG_BANK_MAIN`
- Stable Outputs: OUT_FOG_BANK_MAIN, OUT_DENSITY_ONLY, OUT_LIGHT_BEAM_MASK, OUT_DEPTH_FADE_MASK, OUT_TRIGGER_METADATA

### HFX_010_Smoke_Plume_Column

- Wrapper Name: `WRAP_HFX_010_Smoke_Plume_Column_v007`
- Source Geo: `HFX_010_Smoke_Plume_Column_v003`
- HDA Type: `qqy::hfx_smoke_plume_column::2.0`
- Main Output: `OUT_SMOKE_PLUME_MAIN`
- Stable Outputs: OUT_SMOKE_PLUME_MAIN, OUT_DENSITY_ONLY, OUT_TOP_ROLL, OUT_BASE_SPREAD, OUT_TRIGGER_METADATA

### HFX_011_Ember_Ash_Field

- Wrapper Name: `WRAP_HFX_011_Ember_Ash_Field_v007`
- Source Geo: `HFX_011_Ember_Ash_Field_v003`
- HDA Type: `qqy::hfx_ember_ash_field::2.0`
- Main Output: `OUT_EMBER_ASH_MAIN`
- Stable Outputs: OUT_EMBER_ASH_MAIN, OUT_EMBERS_ONLY, OUT_ASH_ONLY, OUT_FOREGROUND_LAYER, OUT_TRIGGER_METADATA

### HFX_012_Sparks_Impact_Spray

- Wrapper Name: `WRAP_HFX_012_Sparks_Impact_Spray_v007`
- Source Geo: `HFX_012_Sparks_Impact_Spray_v003`
- HDA Type: `qqy::hfx_sparks_impact_spray::2.0`
- Main Output: `OUT_SPARKS_MAIN`
- Stable Outputs: OUT_SPARKS_MAIN, OUT_HOT_SPARKS, OUT_TRAILS_ONLY, OUT_CONTACT_FLASH, OUT_TRIGGER_METADATA

### HFX_013_Debris_Burst_Radial

- Wrapper Name: `WRAP_HFX_013_Debris_Burst_Radial_v007`
- Source Geo: `HFX_013_Debris_Burst_Radial_v003`
- HDA Type: `qqy::hfx_debris_burst_radial::2.0`
- Main Output: `OUT_DEBRIS_BURST_MAIN`
- Stable Outputs: OUT_DEBRIS_BURST_MAIN, OUT_LARGE_DEBRIS, OUT_SMALL_DEBRIS, OUT_DUST_PROXY, OUT_TRIGGER_METADATA

### HFX_014_Magic_Particle_Aura

- Wrapper Name: `WRAP_HFX_014_Magic_Particle_Aura_v007`
- Source Geo: `HFX_014_Magic_Particle_Aura_v003`
- HDA Type: `qqy::hfx_magic_particle_aura::2.0`
- Main Output: `OUT_MAGIC_AURA_MAIN`
- Stable Outputs: OUT_MAGIC_AURA_MAIN, OUT_CORE_PARTICLES, OUT_ORBITING_PARTICLES, OUT_GLOW_FIELD, OUT_TRIGGER_METADATA

### HFX_015_Portal_Ring_Field

- Wrapper Name: `WRAP_HFX_015_Portal_Ring_Field_v007`
- Source Geo: `HFX_015_Portal_Ring_Field_v003`
- HDA Type: `qqy::hfx_portal_ring_field::2.0`
- Main Output: `OUT_PORTAL_RING_MAIN`
- Stable Outputs: OUT_PORTAL_RING_MAIN, OUT_RING_CORE, OUT_EDGE_SPARKS, OUT_DISTORTION_MASK, OUT_TRIGGER_METADATA

### HFX_016_Heat_Distortion_Field

- Wrapper Name: `WRAP_HFX_016_Heat_Distortion_Field_v007`
- Source Geo: `HFX_016_Heat_Distortion_Field_v003`
- HDA Type: `qqy::hfx_heat_distortion_field::2.0`
- Main Output: `OUT_HEAT_DISTORTION_MAIN`
- Stable Outputs: OUT_HEAT_DISTORTION_MAIN, OUT_VECTOR_FIELD, OUT_MASK_ONLY, OUT_NOISE_FIELD, OUT_TRIGGER_METADATA

