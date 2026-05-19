# HFX Batch 03 Destruction Cloth Fluid v005 Heavy Solver Candidate Spec

Status: HFX_B03_DESTRUCTION_CLOTH_FLUID_V005_HEAVY_SOLVER_CANDIDATE_SPEC_READY

Purpose:
Define candidate heavy solver families and upgrade gates before introducing actual heavy simulation networks.

Global Rules:
- v005 does not run or build heavy solvers.
- v005 defines candidate solver contracts only.
- Preview mode must remain available for every asset.
- Hero mode must be explicitly gated.
- Stable OUT nodes must not be renamed.
- OUT_TRIGGER_METADATA must remain available.
- Heavy solver upgrade must be reversible and cache-versioned.
- No silent mutation of Batch 01 or Batch 02 sealed releases.

## Solver Candidates

### HFX_017_Building_Fracture_Collapse

- Solver Family: `RBD`
- Candidate Solver: RBD Material Fracture + Packed RBD + Constraint Network
- Preview Mode: `NO_VEX_ADD_NULL_PROXY`
- Hero Mode: `RBD_FRACTURE_COLLAPSE_HERO`
- Main Output: `OUT_COLLAPSE_MAIN`
- Layers: OUT_LARGE_CHUNKS, OUT_SMALL_CHUNKS, OUT_DUST_PROXY, OUT_TRIGGER_METADATA
- Cache Types: bgeo, abc, fbx
- Risk: `high`
- Upgrade Gate: must pass preview contract, collision proxy contract, cache version contract, and solver budget contract

### HFX_018_Glass_Shatter_Burst

- Solver Family: `RBD_GLASS`
- Candidate Solver: Boolean/Material Fracture + Packed Glass Shards + Velocity Burst
- Preview Mode: `POINT_SHARD_PROXY`
- Hero Mode: `RBD_GLASS_SHATTER_HERO`
- Main Output: `OUT_GLASS_SHATTER_MAIN`
- Layers: OUT_LARGE_SHARDS, OUT_SMALL_SHARDS, OUT_GLASS_DUST, OUT_TRIGGER_METADATA
- Cache Types: bgeo, abc, fbx, exr
- Risk: `medium_high`
- Upgrade Gate: must pass shard-count budget, transparent material pass policy, and no-overwrite cache rule

### HFX_019_Vellum_Cape_Cloth_Sim

- Solver Family: `VELLUM`
- Candidate Solver: Vellum Cloth + Pin Constraints + Wind Field + Collision Proxy
- Preview Mode: `CLOTH_GRID_POINT_PROXY`
- Hero Mode: `VELLUM_CLOTH_HERO`
- Main Output: `OUT_CLOTH_MAIN`
- Layers: OUT_CLOTH_LOWRES_PROXY, OUT_PINNED_POINTS, OUT_WIND_FIELD_PROXY, OUT_TRIGGER_METADATA
- Cache Types: bgeo, abc
- Risk: `high`
- Upgrade Gate: must pass pin contract, collision contract, substep budget, and animation attachment contract

### HFX_020_FLIP_Water_Splash

- Solver Family: `FLIP`
- Candidate Solver: FLIP Splash + Meshing + Droplets + Whitewater Proxy
- Preview Mode: `DROPLET_POINT_PROXY`
- Hero Mode: `FLIP_SPLASH_HERO`
- Main Output: `OUT_WATER_SPLASH_MAIN`
- Layers: OUT_MESH_SURFACE, OUT_DROPLETS, OUT_WHITEWATER_PROXY, OUT_TRIGGER_METADATA
- Cache Types: bgeo, vdb, abc, exr
- Risk: `high`
- Upgrade Gate: must pass particle budget, meshing policy, whitewater separation, and cache size budget

### HFX_021_Advanced_Pyro_Explosion

- Solver Family: `PYRO`
- Candidate Solver: Sparse Pyro Explosion + Fuel/Temperature/Density + Disturbance/Shredding
- Preview Mode: `POINT_VOLUME_PYRO_PROXY`
- Hero Mode: `SPARSE_PYRO_EXPLOSION_HERO`
- Main Output: `OUT_PYRO_EXPLOSION_MAIN`
- Layers: OUT_FIRE_CORE, OUT_SMOKE_ROLL, OUT_BLAST_MASK, OUT_TRIGGER_METADATA
- Cache Types: bgeo, vdb, exr
- Risk: `very_high`
- Upgrade Gate: must pass voxel budget, VDB field contract, render pass policy, and no interactive heavy sim rule

### HFX_022_Storm_Cloud_Volume

- Solver Family: `VOLUME`
- Candidate Solver: Procedural VDB Cloud + Noise Fields + Wind Advection Proxy
- Preview Mode: `POINT_DENSITY_CLOUD_PROXY`
- Hero Mode: `VDB_STORM_CLOUD_HERO`
- Main Output: `OUT_STORM_CLOUD_MAIN`
- Layers: OUT_DENSITY_VOLUME, OUT_LIGHTING_MASK, OUT_EDGE_BREAKUP, OUT_TRIGGER_METADATA
- Cache Types: bgeo, vdb, exr
- Risk: `high`
- Upgrade Gate: must pass VDB density field contract, lighting/matte separation, and volume resolution budget

### HFX_023_Ground_Collapse_Sinkhole

- Solver Family: `RBD_TERRAIN`
- Candidate Solver: Terrain Fracture + Packed RBD + Crack Mask + Falling Rocks
- Preview Mode: `TERRAIN_POINT_COLLAPSE_PROXY`
- Hero Mode: `RBD_TERRAIN_COLLAPSE_HERO`
- Main Output: `OUT_GROUND_COLLAPSE_MAIN`
- Layers: OUT_TERRAIN_PLATES, OUT_FALLING_ROCKS, OUT_CRACK_MASK, OUT_TRIGGER_METADATA
- Cache Types: bgeo, abc, fbx, exr
- Risk: `high`
- Upgrade Gate: must pass terrain proxy contract, crack mask contract, collision budget, and cache versioning

### HFX_024_Energy_Shield_Shatter

- Solver Family: `PROCEDURAL_ENERGY_FRACTURE`
- Candidate Solver: Procedural Shield Shell Fracture + Crack Lines + Energy Ripple + Piece Burst
- Preview Mode: `RING_PARTICLE_SHIELD_PROXY`
- Hero Mode: `ENERGY_SHIELD_SHATTER_HERO`
- Main Output: `OUT_SHIELD_SHATTER_MAIN`
- Layers: OUT_SHIELD_PIECES, OUT_CRACK_LINES, OUT_ENERGY_RIPPLE, OUT_TRIGGER_METADATA
- Cache Types: bgeo, abc, exr
- Risk: `medium_high`
- Upgrade Gate: must pass shell topology contract, crack/ripple separation, glow pass policy, and cache versioning

