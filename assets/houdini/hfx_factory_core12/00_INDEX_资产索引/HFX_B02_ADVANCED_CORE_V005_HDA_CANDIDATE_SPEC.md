# HFX Batch 02 Advanced Core v005 HDA Candidate Spec

Status: HFX_B02_ADVANCED_CORE_V005_HDA_CANDIDATE_SPEC_READY

Purpose:
Define HDA candidate type names, stable interfaces, parameter families, and output contracts for Batch 02 advanced FX.

Global HDA Rules:
- HDA candidates must be self-contained at packaging stage.
- No export/cache ROP nodes may remain inside final HDA package if they create external references.
- Stable OUT nodes must not be renamed.
- OUT_TRIGGER_METADATA must remain available.
- HDA does not decide final comp; it produces separated layers.
- Unreal handoff must use baked/validated ABC/VDB/EXR/FBX/BGEO paths.

## HDA Candidate Assets

### HFX_009_Volumetric_Fog_Bank

- HDA Type: `qqy::hfx_volumetric_fog_bank::2.0`
- HDA File: `qqy_hfx_volumetric_fog_bank_b02_v005.hda`
- Main Output: `OUT_FOG_BANK_MAIN`
- Outputs: OUT_FOG_BANK_MAIN, OUT_DENSITY_ONLY, OUT_LIGHT_BEAM_MASK, OUT_DEPTH_FADE_MASK, OUT_TRIGGER_METADATA
- Parameters: trigger_frame, duration_frames, fog_density, field_width, field_height, field_depth, wind_speed, noise_scale, seed
- Handoff: VDB, EXR, BGEO
- Risk: `medium`

### HFX_010_Smoke_Plume_Column

- HDA Type: `qqy::hfx_smoke_plume_column::2.0`
- HDA File: `qqy_hfx_smoke_plume_column_b02_v005.hda`
- Main Output: `OUT_SMOKE_PLUME_MAIN`
- Outputs: OUT_SMOKE_PLUME_MAIN, OUT_DENSITY_ONLY, OUT_TOP_ROLL, OUT_BASE_SPREAD, OUT_TRIGGER_METADATA
- Parameters: trigger_frame, duration_frames, plume_height, base_radius, density, rise_speed, curl_strength, wind_speed, seed
- Handoff: VDB, EXR, BGEO
- Risk: `medium_high`

### HFX_011_Ember_Ash_Field

- HDA Type: `qqy::hfx_ember_ash_field::2.0`
- HDA File: `qqy_hfx_ember_ash_field_b02_v005.hda`
- Main Output: `OUT_EMBER_ASH_MAIN`
- Outputs: OUT_EMBER_ASH_MAIN, OUT_EMBERS_ONLY, OUT_ASH_ONLY, OUT_FOREGROUND_LAYER, OUT_TRIGGER_METADATA
- Parameters: trigger_frame, duration_frames, particle_count, rise_speed, drift_strength, ember_ratio, glow_intensity, foreground_depth, seed
- Handoff: ABC, BGEO, EXR
- Risk: `low`

### HFX_012_Sparks_Impact_Spray

- HDA Type: `qqy::hfx_sparks_impact_spray::2.0`
- HDA File: `qqy_hfx_sparks_impact_spray_b02_v005.hda`
- Main Output: `OUT_SPARKS_MAIN`
- Outputs: OUT_SPARKS_MAIN, OUT_HOT_SPARKS, OUT_TRAILS_ONLY, OUT_CONTACT_FLASH, OUT_TRIGGER_METADATA
- Parameters: trigger_frame, duration_frames, spark_count, spray_angle, velocity, gravity, trail_length, flash_strength, seed
- Handoff: ABC, BGEO, EXR
- Risk: `low`

### HFX_013_Debris_Burst_Radial

- HDA Type: `qqy::hfx_debris_burst_radial::2.0`
- HDA File: `qqy_hfx_debris_burst_radial_b02_v005.hda`
- Main Output: `OUT_DEBRIS_BURST_MAIN`
- Outputs: OUT_DEBRIS_BURST_MAIN, OUT_LARGE_DEBRIS, OUT_SMALL_DEBRIS, OUT_DUST_PROXY, OUT_TRIGGER_METADATA
- Parameters: trigger_frame, duration_frames, debris_count, burst_radius, velocity, gravity, large_piece_ratio, dust_proxy_strength, seed
- Handoff: ABC, FBX, BGEO, EXR
- Risk: `medium`

### HFX_014_Magic_Particle_Aura

- HDA Type: `qqy::hfx_magic_particle_aura::2.0`
- HDA File: `qqy_hfx_magic_particle_aura_b02_v005.hda`
- Main Output: `OUT_MAGIC_AURA_MAIN`
- Outputs: OUT_MAGIC_AURA_MAIN, OUT_CORE_PARTICLES, OUT_ORBITING_PARTICLES, OUT_GLOW_FIELD, OUT_TRIGGER_METADATA
- Parameters: trigger_frame, duration_frames, aura_radius, particle_count, orbit_speed, pulse_rate, glow_strength, noise_scale, seed
- Handoff: ABC, BGEO, EXR
- Risk: `low_medium`

### HFX_015_Portal_Ring_Field

- HDA Type: `qqy::hfx_portal_ring_field::2.0`
- HDA File: `qqy_hfx_portal_ring_field_b02_v005.hda`
- Main Output: `OUT_PORTAL_RING_MAIN`
- Outputs: OUT_PORTAL_RING_MAIN, OUT_RING_CORE, OUT_EDGE_SPARKS, OUT_DISTORTION_MASK, OUT_TRIGGER_METADATA
- Parameters: trigger_frame, duration_frames, ring_radius, ring_width, spin_speed, edge_noise, spark_count, distortion_strength, seed
- Handoff: ABC, BGEO, EXR
- Risk: `medium`

### HFX_016_Heat_Distortion_Field

- HDA Type: `qqy::hfx_heat_distortion_field::2.0`
- HDA File: `qqy_hfx_heat_distortion_field_b02_v005.hda`
- Main Output: `OUT_HEAT_DISTORTION_MAIN`
- Outputs: OUT_HEAT_DISTORTION_MAIN, OUT_VECTOR_FIELD, OUT_MASK_ONLY, OUT_NOISE_FIELD, OUT_TRIGGER_METADATA
- Parameters: trigger_frame, duration_frames, distortion_strength, field_width, field_height, noise_speed, falloff, direction, seed
- Handoff: EXR, BGEO
- Risk: `medium`

