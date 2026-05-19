# HFX Batch 03 Destruction Cloth Fluid v006 Solver Interface Spec

Status: HFX_B03_DESTRUCTION_CLOTH_FLUID_V006_SOLVER_INTERFACE_SPEC_READY

Purpose:
Freeze solver interface contracts before wrapper/preflight stages. This stage does not build heavy solvers.

Global Rules:
- Preview mode must always exist.
- Hero mode is blocked unless all input/cache/budget/output contracts are present.
- Stable OUT nodes must not be renamed.
- OUT_TRIGGER_METADATA must remain available.
- Cache exports must be versioned.
- Heavy solver execution must be explicit, never implicit.
- Batch 01 and Batch 02 sealed releases are immutable.

## Interfaces

### HFX_017_Building_Fracture_Collapse

- Interface: `B03_RBD_BUILDING_COLLAPSE_INTERFACE`
- Solver Family: `RBD`
- Main Output: `OUT_COLLAPSE_MAIN`
- Stable Layers: OUT_LARGE_CHUNKS, OUT_SMALL_CHUNKS, OUT_DUST_PROXY, OUT_TRIGGER_METADATA
- Required/Optional Inputs: optional_source_structure, optional_collision_proxy, optional_impact_point
- Cache Types: bgeo, abc, fbx
- Hero Block: RBD hero mode blocked until source/collision/budget/cache contracts exist

### HFX_018_Glass_Shatter_Burst

- Interface: `B03_RBD_GLASS_SHATTER_INTERFACE`
- Solver Family: `RBD_GLASS`
- Main Output: `OUT_GLASS_SHATTER_MAIN`
- Stable Layers: OUT_LARGE_SHARDS, OUT_SMALL_SHARDS, OUT_GLASS_DUST, OUT_TRIGGER_METADATA
- Required/Optional Inputs: optional_glass_surface, optional_collision_proxy, optional_impact_point
- Cache Types: bgeo, abc, fbx, exr
- Hero Block: Glass hero mode blocked until shard/material/cache contracts exist

### HFX_019_Vellum_Cape_Cloth_Sim

- Interface: `B03_VELLUM_CAPE_CLOTH_INTERFACE`
- Solver Family: `VELLUM`
- Main Output: `OUT_CLOTH_MAIN`
- Stable Layers: OUT_CLOTH_LOWRES_PROXY, OUT_PINNED_POINTS, OUT_WIND_FIELD_PROXY, OUT_TRIGGER_METADATA
- Required/Optional Inputs: optional_cloth_mesh, optional_pin_curve, optional_character_collision
- Cache Types: bgeo, abc
- Hero Block: Vellum hero mode blocked until pin/collision/substep/cache contracts exist

### HFX_020_FLIP_Water_Splash

- Interface: `B03_FLIP_WATER_SPLASH_INTERFACE`
- Solver Family: `FLIP`
- Main Output: `OUT_WATER_SPLASH_MAIN`
- Stable Layers: OUT_MESH_SURFACE, OUT_DROPLETS, OUT_WHITEWATER_PROXY, OUT_TRIGGER_METADATA
- Required/Optional Inputs: optional_emitter_geometry, optional_collision_proxy, optional_waterline
- Cache Types: bgeo, vdb, abc, exr
- Hero Block: FLIP hero mode blocked until particle/mesh/whitewater/cache contracts exist

### HFX_021_Advanced_Pyro_Explosion

- Interface: `B03_SPARSE_PYRO_EXPLOSION_INTERFACE`
- Solver Family: `PYRO`
- Main Output: `OUT_PYRO_EXPLOSION_MAIN`
- Stable Layers: OUT_FIRE_CORE, OUT_SMOKE_ROLL, OUT_BLAST_MASK, OUT_TRIGGER_METADATA
- Required/Optional Inputs: optional_source_volume, optional_collision_proxy, optional_ignition_point
- Cache Types: bgeo, vdb, exr
- Hero Block: Pyro hero mode blocked until VDB field/budget/cache/render-pass contracts exist

### HFX_022_Storm_Cloud_Volume

- Interface: `B03_STORM_CLOUD_VOLUME_INTERFACE`
- Solver Family: `VOLUME`
- Main Output: `OUT_STORM_CLOUD_MAIN`
- Stable Layers: OUT_DENSITY_VOLUME, OUT_LIGHTING_MASK, OUT_EDGE_BREAKUP, OUT_TRIGGER_METADATA
- Required/Optional Inputs: optional_volume_bounds, optional_wind_vector, optional_light_direction
- Cache Types: bgeo, vdb, exr
- Hero Block: Storm cloud hero mode blocked until VDB density/lighting/matte/cache contracts exist

### HFX_023_Ground_Collapse_Sinkhole

- Interface: `B03_RBD_TERRAIN_COLLAPSE_INTERFACE`
- Solver Family: `RBD_TERRAIN`
- Main Output: `OUT_GROUND_COLLAPSE_MAIN`
- Stable Layers: OUT_TERRAIN_PLATES, OUT_FALLING_ROCKS, OUT_CRACK_MASK, OUT_TRIGGER_METADATA
- Required/Optional Inputs: optional_terrain_mesh, optional_collision_proxy, optional_collapse_mask
- Cache Types: bgeo, abc, fbx, exr
- Hero Block: Terrain collapse hero mode blocked until terrain/collision/crack/cache contracts exist

### HFX_024_Energy_Shield_Shatter

- Interface: `B03_ENERGY_SHIELD_SHATTER_INTERFACE`
- Solver Family: `PROCEDURAL_ENERGY_FRACTURE`
- Main Output: `OUT_SHIELD_SHATTER_MAIN`
- Stable Layers: OUT_SHIELD_PIECES, OUT_CRACK_LINES, OUT_ENERGY_RIPPLE, OUT_TRIGGER_METADATA
- Required/Optional Inputs: optional_shield_surface, optional_impact_point, optional_camera_vector
- Cache Types: bgeo, abc, exr
- Hero Block: Shield hero mode blocked until shell/crack/ripple/glow/cache contracts exist

