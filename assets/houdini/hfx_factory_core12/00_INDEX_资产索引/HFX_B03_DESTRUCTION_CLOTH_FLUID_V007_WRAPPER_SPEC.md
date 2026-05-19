# HFX Batch 03 Destruction Cloth Fluid v007 Wrapper Spec

Status: HFX_B03_DESTRUCTION_CLOTH_FLUID_V007_WRAPPER_SPEC_READY

Purpose:
Define HDA wrapper contracts before packaging preflight. This stage does not build HDA files and does not run heavy solvers.

Global Rules:
- Wrapper source is v003 HIP.
- Solver interface source is v006.
- Preview mode is default enabled.
- Hero mode is default blocked.
- Stable OUT nodes must not be renamed.
- OUT_TRIGGER_METADATA must remain available.
- Cache/export execution is blocked until preflight.
- Batch 01 and Batch 02 sealed releases are immutable.

## Wrapper Targets

### HFX_017_Building_Fracture_Collapse

- HDA Type: `qqy::hfx_building_fracture_collapse::3.0`
- Wrapper Name: `WRAP_HFX_017_Building_Fracture_Collapse_v007`
- Source Geo: `HFX_017_Building_Fracture_Collapse_v003`
- Solver Interface: `B03_RBD_BUILDING_COLLAPSE_INTERFACE`
- Main Output: `OUT_COLLAPSE_MAIN`
- Stable Outputs: OUT_COLLAPSE_MAIN, OUT_LARGE_CHUNKS, OUT_SMALL_CHUNKS, OUT_DUST_PROXY, OUT_TRIGGER_METADATA

### HFX_018_Glass_Shatter_Burst

- HDA Type: `qqy::hfx_glass_shatter_burst::3.0`
- Wrapper Name: `WRAP_HFX_018_Glass_Shatter_Burst_v007`
- Source Geo: `HFX_018_Glass_Shatter_Burst_v003`
- Solver Interface: `B03_RBD_GLASS_SHATTER_INTERFACE`
- Main Output: `OUT_GLASS_SHATTER_MAIN`
- Stable Outputs: OUT_GLASS_SHATTER_MAIN, OUT_LARGE_SHARDS, OUT_SMALL_SHARDS, OUT_GLASS_DUST, OUT_TRIGGER_METADATA

### HFX_019_Vellum_Cape_Cloth_Sim

- HDA Type: `qqy::hfx_vellum_cape_cloth_sim::3.0`
- Wrapper Name: `WRAP_HFX_019_Vellum_Cape_Cloth_Sim_v007`
- Source Geo: `HFX_019_Vellum_Cape_Cloth_Sim_v003`
- Solver Interface: `B03_VELLUM_CAPE_CLOTH_INTERFACE`
- Main Output: `OUT_CLOTH_MAIN`
- Stable Outputs: OUT_CLOTH_MAIN, OUT_CLOTH_LOWRES_PROXY, OUT_PINNED_POINTS, OUT_WIND_FIELD_PROXY, OUT_TRIGGER_METADATA

### HFX_020_FLIP_Water_Splash

- HDA Type: `qqy::hfx_flip_water_splash::3.0`
- Wrapper Name: `WRAP_HFX_020_FLIP_Water_Splash_v007`
- Source Geo: `HFX_020_FLIP_Water_Splash_v003`
- Solver Interface: `B03_FLIP_WATER_SPLASH_INTERFACE`
- Main Output: `OUT_WATER_SPLASH_MAIN`
- Stable Outputs: OUT_WATER_SPLASH_MAIN, OUT_MESH_SURFACE, OUT_DROPLETS, OUT_WHITEWATER_PROXY, OUT_TRIGGER_METADATA

### HFX_021_Advanced_Pyro_Explosion

- HDA Type: `qqy::hfx_advanced_pyro_explosion::3.0`
- Wrapper Name: `WRAP_HFX_021_Advanced_Pyro_Explosion_v007`
- Source Geo: `HFX_021_Advanced_Pyro_Explosion_v003`
- Solver Interface: `B03_SPARSE_PYRO_EXPLOSION_INTERFACE`
- Main Output: `OUT_PYRO_EXPLOSION_MAIN`
- Stable Outputs: OUT_PYRO_EXPLOSION_MAIN, OUT_FIRE_CORE, OUT_SMOKE_ROLL, OUT_BLAST_MASK, OUT_TRIGGER_METADATA

### HFX_022_Storm_Cloud_Volume

- HDA Type: `qqy::hfx_storm_cloud_volume::3.0`
- Wrapper Name: `WRAP_HFX_022_Storm_Cloud_Volume_v007`
- Source Geo: `HFX_022_Storm_Cloud_Volume_v003`
- Solver Interface: `B03_STORM_CLOUD_VOLUME_INTERFACE`
- Main Output: `OUT_STORM_CLOUD_MAIN`
- Stable Outputs: OUT_STORM_CLOUD_MAIN, OUT_DENSITY_VOLUME, OUT_LIGHTING_MASK, OUT_EDGE_BREAKUP, OUT_TRIGGER_METADATA

### HFX_023_Ground_Collapse_Sinkhole

- HDA Type: `qqy::hfx_ground_collapse_sinkhole::3.0`
- Wrapper Name: `WRAP_HFX_023_Ground_Collapse_Sinkhole_v007`
- Source Geo: `HFX_023_Ground_Collapse_Sinkhole_v003`
- Solver Interface: `B03_RBD_TERRAIN_COLLAPSE_INTERFACE`
- Main Output: `OUT_GROUND_COLLAPSE_MAIN`
- Stable Outputs: OUT_GROUND_COLLAPSE_MAIN, OUT_TERRAIN_PLATES, OUT_FALLING_ROCKS, OUT_CRACK_MASK, OUT_TRIGGER_METADATA

### HFX_024_Energy_Shield_Shatter

- HDA Type: `qqy::hfx_energy_shield_shatter::3.0`
- Wrapper Name: `WRAP_HFX_024_Energy_Shield_Shatter_v007`
- Source Geo: `HFX_024_Energy_Shield_Shatter_v003`
- Solver Interface: `B03_ENERGY_SHIELD_SHATTER_INTERFACE`
- Main Output: `OUT_SHIELD_SHATTER_MAIN`
- Stable Outputs: OUT_SHIELD_SHATTER_MAIN, OUT_SHIELD_PIECES, OUT_CRACK_LINES, OUT_ENERGY_RIPPLE, OUT_TRIGGER_METADATA

