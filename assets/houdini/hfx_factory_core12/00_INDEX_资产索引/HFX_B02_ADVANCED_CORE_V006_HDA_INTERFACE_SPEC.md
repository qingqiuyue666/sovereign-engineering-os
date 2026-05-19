# HFX Batch 02 Advanced Core v006 HDA Interface Spec

Status: HFX_B02_ADVANCED_CORE_V006_HDA_INTERFACE_SPEC_READY

Purpose:
Define concrete HDA interface contracts before wrapper creation and packaging.

Interface Rules:
- Every HDA must expose Timing, Look, Motion, and Seed controls.
- Every HDA must preserve OUT_TRIGGER_METADATA.
- Every HDA must preserve stable output names.
- Optional inputs must not be required for node creation.
- Missing shot binding must block final cache/export, not block preview.
- HDA output is source-side; Unreal receives validated baked outputs.

## Asset Interfaces

### HFX_009_Volumetric_Fog_Bank

- HDA Type: `qqy::hfx_volumetric_fog_bank::2.0`
- Main Output: `OUT_FOG_BANK_MAIN`
- Outputs: OUT_FOG_BANK_MAIN, OUT_DENSITY_ONLY, OUT_LIGHT_BEAM_MASK, OUT_DEPTH_FADE_MASK, OUT_TRIGGER_METADATA
- Optional Inputs: none
- Handoff Types: VDB, EXR, BGEO
- Parameter Folders:
  - Timing: trigger_frame, duration_frames, fps
  - Shape: field_width, field_height, field_depth
  - Motion: wind_speed, noise_scale
  - Look: fog_density, beam_mask_strength, depth_fade
  - Seed: seed

### HFX_010_Smoke_Plume_Column

- HDA Type: `qqy::hfx_smoke_plume_column::2.0`
- Main Output: `OUT_SMOKE_PLUME_MAIN`
- Outputs: OUT_SMOKE_PLUME_MAIN, OUT_DENSITY_ONLY, OUT_TOP_ROLL, OUT_BASE_SPREAD, OUT_TRIGGER_METADATA
- Optional Inputs: none
- Handoff Types: VDB, EXR, BGEO
- Parameter Folders:
  - Timing: trigger_frame, duration_frames, fps
  - Shape: plume_height, base_radius
  - Motion: rise_speed, curl_strength, wind_speed
  - Look: density, top_roll_strength, base_spread_strength
  - Seed: seed

### HFX_011_Ember_Ash_Field

- HDA Type: `qqy::hfx_ember_ash_field::2.0`
- Main Output: `OUT_EMBER_ASH_MAIN`
- Outputs: OUT_EMBER_ASH_MAIN, OUT_EMBERS_ONLY, OUT_ASH_ONLY, OUT_FOREGROUND_LAYER, OUT_TRIGGER_METADATA
- Optional Inputs: none
- Handoff Types: ABC, BGEO, EXR
- Parameter Folders:
  - Timing: trigger_frame, duration_frames, fps
  - Particles: particle_count, ember_ratio
  - Motion: rise_speed, drift_strength
  - Look: glow_intensity, foreground_depth
  - Seed: seed

### HFX_012_Sparks_Impact_Spray

- HDA Type: `qqy::hfx_sparks_impact_spray::2.0`
- Main Output: `OUT_SPARKS_MAIN`
- Outputs: OUT_SPARKS_MAIN, OUT_HOT_SPARKS, OUT_TRAILS_ONLY, OUT_CONTACT_FLASH, OUT_TRIGGER_METADATA
- Optional Inputs: optional_impact_point
- Handoff Types: ABC, BGEO, EXR
- Parameter Folders:
  - Timing: trigger_frame, duration_frames, fps
  - Particles: spark_count
  - Motion: spray_angle, velocity, gravity, trail_length
  - Look: flash_strength, hot_spark_ratio
  - Seed: seed

### HFX_013_Debris_Burst_Radial

- HDA Type: `qqy::hfx_debris_burst_radial::2.0`
- Main Output: `OUT_DEBRIS_BURST_MAIN`
- Outputs: OUT_DEBRIS_BURST_MAIN, OUT_LARGE_DEBRIS, OUT_SMALL_DEBRIS, OUT_DUST_PROXY, OUT_TRIGGER_METADATA
- Optional Inputs: optional_collision_surface, optional_impact_point
- Handoff Types: ABC, FBX, BGEO, EXR
- Parameter Folders:
  - Timing: trigger_frame, duration_frames, fps
  - Debris: debris_count, large_piece_ratio
  - Motion: burst_radius, velocity, gravity
  - Look: dust_proxy_strength, piece_scale
  - Seed: seed

### HFX_014_Magic_Particle_Aura

- HDA Type: `qqy::hfx_magic_particle_aura::2.0`
- Main Output: `OUT_MAGIC_AURA_MAIN`
- Outputs: OUT_MAGIC_AURA_MAIN, OUT_CORE_PARTICLES, OUT_ORBITING_PARTICLES, OUT_GLOW_FIELD, OUT_TRIGGER_METADATA
- Optional Inputs: optional_character_position
- Handoff Types: ABC, BGEO, EXR
- Parameter Folders:
  - Timing: trigger_frame, duration_frames, fps
  - Shape: aura_radius
  - Particles: particle_count
  - Motion: orbit_speed, pulse_rate, noise_scale
  - Look: glow_strength
  - Seed: seed

### HFX_015_Portal_Ring_Field

- HDA Type: `qqy::hfx_portal_ring_field::2.0`
- Main Output: `OUT_PORTAL_RING_MAIN`
- Outputs: OUT_PORTAL_RING_MAIN, OUT_RING_CORE, OUT_EDGE_SPARKS, OUT_DISTORTION_MASK, OUT_TRIGGER_METADATA
- Optional Inputs: optional_portal_center
- Handoff Types: ABC, BGEO, EXR
- Parameter Folders:
  - Timing: trigger_frame, duration_frames, fps
  - Shape: ring_radius, ring_width
  - Motion: spin_speed, edge_noise
  - Particles: spark_count
  - Look: distortion_strength, glow_strength
  - Seed: seed

### HFX_016_Heat_Distortion_Field

- HDA Type: `qqy::hfx_heat_distortion_field::2.0`
- Main Output: `OUT_HEAT_DISTORTION_MAIN`
- Outputs: OUT_HEAT_DISTORTION_MAIN, OUT_VECTOR_FIELD, OUT_MASK_ONLY, OUT_NOISE_FIELD, OUT_TRIGGER_METADATA
- Optional Inputs: optional_distortion_region
- Handoff Types: EXR, BGEO
- Parameter Folders:
  - Timing: trigger_frame, duration_frames, fps
  - Shape: field_width, field_height
  - Motion: noise_speed, direction
  - Look: distortion_strength, falloff
  - Seed: seed

