# HFX Batch 02 Advanced Core v004 Production Spec

Status: HFX_B02_ADVANCED_CORE_V004_PRODUCTION_SPEC_READY

Purpose:
Define production/cache/export/handoff rules for Batch 02 advanced Hollywood support FX.

Scope:
- HFX_009 through HFX_016
- atmosphere, smoke, embers, sparks, debris, aura, portal, heat distortion

Global Rules:
- Do not modify HFX Batch 01 v013 final sealed release.
- Do not rename stable OUT nodes.
- Do not flatten separated layers.
- Every shot binding must include shot_id, take_id, trigger_frame, frame_start, frame_end, fps, scale, and handoff type.
- Unreal final usage should prefer baked Alembic/EXR/VDB outputs unless Houdini Engine is explicitly validated.
- Volume-heavy assets should prefer EXR final comp pass unless UE VDB runtime is validated.

## Asset Specs

### HFX_009_Volumetric_Fog_Bank

- Category: `volume_atmosphere`
- Main Output: `OUT_FOG_BANK_MAIN`
- Stable Layers: OUT_DENSITY_ONLY, OUT_LIGHT_BEAM_MASK, OUT_DEPTH_FADE_MASK, OUT_TRIGGER_METADATA
- Cache Types: bgeo, vdb, exr
- Preferred Handoff: VDB for Houdini/volume pipeline, EXR for final comp, BGEO for internal cache
- Shot Use: atmosphere, background depth, light beam support, green-screen plate integration
- Risk: `medium`

Required Production Fields:
- asset_id
- shot_id
- take_id
- trigger_frame
- frame_start
- frame_end
- fps
- scale
- world_transform
- cache_type
- cache_path
- render_pass_policy
- comp_handoff_path
- unreal_destination

### HFX_010_Smoke_Plume_Column

- Category: `volume_smoke`
- Main Output: `OUT_SMOKE_PLUME_MAIN`
- Stable Layers: OUT_DENSITY_ONLY, OUT_TOP_ROLL, OUT_BASE_SPREAD, OUT_TRIGGER_METADATA
- Cache Types: bgeo, vdb, exr
- Preferred Handoff: VDB or EXR depending on Unreal compatibility; EXR is safer for final comp
- Shot Use: explosion aftermath, fire background, destruction smoke column
- Risk: `medium_high`

Required Production Fields:
- asset_id
- shot_id
- take_id
- trigger_frame
- frame_start
- frame_end
- fps
- scale
- world_transform
- cache_type
- cache_path
- render_pass_policy
- comp_handoff_path
- unreal_destination

### HFX_011_Ember_Ash_Field

- Category: `particles_foreground`
- Main Output: `OUT_EMBER_ASH_MAIN`
- Stable Layers: OUT_EMBERS_ONLY, OUT_ASH_ONLY, OUT_FOREGROUND_LAYER, OUT_TRIGGER_METADATA
- Cache Types: bgeo, abc, exr
- Preferred Handoff: Alembic/BGEO for geometry particles, EXR for comp foreground particle pass
- Shot Use: fire aftermath, cinematic foreground texture, atmospheric particles
- Risk: `low`

Required Production Fields:
- asset_id
- shot_id
- take_id
- trigger_frame
- frame_start
- frame_end
- fps
- scale
- world_transform
- cache_type
- cache_path
- render_pass_policy
- comp_handoff_path
- unreal_destination

### HFX_012_Sparks_Impact_Spray

- Category: `particles_impact`
- Main Output: `OUT_SPARKS_MAIN`
- Stable Layers: OUT_HOT_SPARKS, OUT_TRAILS_ONLY, OUT_CONTACT_FLASH, OUT_TRIGGER_METADATA
- Cache Types: bgeo, abc, exr
- Preferred Handoff: Alembic for particles/trails, EXR for contact flash and comp sparks
- Shot Use: weapon clash, bullet hit, metal impact, slash contact
- Risk: `low`

Required Production Fields:
- asset_id
- shot_id
- take_id
- trigger_frame
- frame_start
- frame_end
- fps
- scale
- world_transform
- cache_type
- cache_path
- render_pass_policy
- comp_handoff_path
- unreal_destination

### HFX_013_Debris_Burst_Radial

- Category: `debris_secondary_destruction`
- Main Output: `OUT_DEBRIS_BURST_MAIN`
- Stable Layers: OUT_LARGE_DEBRIS, OUT_SMALL_DEBRIS, OUT_DUST_PROXY, OUT_TRIGGER_METADATA
- Cache Types: bgeo, abc, fbx, exr
- Preferred Handoff: Alembic for animated debris, FBX for simple proxy, EXR for dust/contact support
- Shot Use: impact enhancement, ground ejecta, blast debris, secondary destruction
- Risk: `medium`

Required Production Fields:
- asset_id
- shot_id
- take_id
- trigger_frame
- frame_start
- frame_end
- fps
- scale
- world_transform
- cache_type
- cache_path
- render_pass_policy
- comp_handoff_path
- unreal_destination

### HFX_014_Magic_Particle_Aura

- Category: `energy_particles`
- Main Output: `OUT_MAGIC_AURA_MAIN`
- Stable Layers: OUT_CORE_PARTICLES, OUT_ORBITING_PARTICLES, OUT_GLOW_FIELD, OUT_TRIGGER_METADATA
- Cache Types: bgeo, abc, exr
- Preferred Handoff: Alembic for orbiting particles, EXR for glow/energy pass
- Shot Use: character power-up, spell charge, supernatural aura
- Risk: `low_medium`

Required Production Fields:
- asset_id
- shot_id
- take_id
- trigger_frame
- frame_start
- frame_end
- fps
- scale
- world_transform
- cache_type
- cache_path
- render_pass_policy
- comp_handoff_path
- unreal_destination

### HFX_015_Portal_Ring_Field

- Category: `portal_spatial_energy`
- Main Output: `OUT_PORTAL_RING_MAIN`
- Stable Layers: OUT_RING_CORE, OUT_EDGE_SPARKS, OUT_DISTORTION_MASK, OUT_TRIGGER_METADATA
- Cache Types: bgeo, abc, exr
- Preferred Handoff: Alembic for ring geometry, EXR for glow/distortion/edge sparks
- Shot Use: portal opening, spatial tear, sci-fi/fantasy transition
- Risk: `medium`

Required Production Fields:
- asset_id
- shot_id
- take_id
- trigger_frame
- frame_start
- frame_end
- fps
- scale
- world_transform
- cache_type
- cache_path
- render_pass_policy
- comp_handoff_path
- unreal_destination

### HFX_016_Heat_Distortion_Field

- Category: `distortion_vector_field`
- Main Output: `OUT_HEAT_DISTORTION_MAIN`
- Stable Layers: OUT_VECTOR_FIELD, OUT_MASK_ONLY, OUT_NOISE_FIELD, OUT_TRIGGER_METADATA
- Cache Types: bgeo, exr
- Preferred Handoff: EXR/vector pass for comp; BGEO only for internal preview
- Shot Use: heat shimmer, explosion aftermath, invisible force distortion, hot surface distortion
- Risk: `medium`

Required Production Fields:
- asset_id
- shot_id
- take_id
- trigger_frame
- frame_start
- frame_end
- fps
- scale
- world_transform
- cache_type
- cache_path
- render_pass_policy
- comp_handoff_path
- unreal_destination

