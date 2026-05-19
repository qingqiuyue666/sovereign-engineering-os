# HFX Batch 03 Destruction Cloth Fluid v004 Production Spec

Status: HFX_B03_DESTRUCTION_CLOTH_FLUID_V004_PRODUCTION_SPEC_READY

Purpose:
Define production/cache/export/handoff rules for heavyweight Batch 03 Houdini FX assets.

Global Rules:
- Do not modify Batch 01 final sealed release.
- Do not modify Batch 02 final sealed release.
- Batch 03 heavy solvers must remain gated behind preview mode and validation.
- Every asset must keep cheap preview mode.
- Every asset must preserve stable OUT nodes and OUT_TRIGGER_METADATA.
- No cache/export may overwrite previous versions.
- Unreal handoff should prefer baked Alembic/VDB/EXR/FBX assets unless Houdini Engine is explicitly validated.
- Heavy solver upgrade requires explicit v005+ contract, not silent replacement.

## Asset Specs

### HFX_017_Building_Fracture_Collapse

- Category: `rbd_building_destruction`
- Main Output: `OUT_COLLAPSE_MAIN`
- Stable Layers: OUT_LARGE_CHUNKS, OUT_SMALL_CHUNKS, OUT_DUST_PROXY, OUT_TRIGGER_METADATA
- Cache Types: bgeo, abc, fbx
- Preview Mode: no-VEX add/null cook-safe proxy
- Solver Upgrade: RBD fracture / constraint network / packed primitives; deferred after v004
- Preferred Handoff: Alembic for animated chunks, FBX for static/proxy, BGEO for Houdini internal cache
- Shot Use: hero wall/building collapse, concrete chunks, structural destruction
- Risk: `high`

### HFX_018_Glass_Shatter_Burst

- Category: `rbd_glass_shatter`
- Main Output: `OUT_GLASS_SHATTER_MAIN`
- Stable Layers: OUT_LARGE_SHARDS, OUT_SMALL_SHARDS, OUT_GLASS_DUST, OUT_TRIGGER_METADATA
- Cache Types: bgeo, abc, fbx, exr
- Preview Mode: point shard proxy
- Solver Upgrade: RBD glass fracture / material fracture / shard instancing; deferred after v004
- Preferred Handoff: Alembic for glass shard motion, EXR for dust/spark/glint comp pass
- Shot Use: window hit, vehicle glass, impact shatter, action collision
- Risk: `medium_high`

### HFX_019_Vellum_Cape_Cloth_Sim

- Category: `vellum_cloth_character`
- Main Output: `OUT_CLOTH_MAIN`
- Stable Layers: OUT_CLOTH_LOWRES_PROXY, OUT_PINNED_POINTS, OUT_WIND_FIELD_PROXY, OUT_TRIGGER_METADATA
- Cache Types: bgeo, abc
- Preview Mode: animated cloth grid point proxy
- Solver Upgrade: Vellum cloth with pinned constraints and wind; deferred after v004
- Preferred Handoff: Alembic for baked cloth animation, BGEO for Houdini iteration
- Shot Use: cape, robe, banner, cloth strip, character costume motion
- Risk: `high`

### HFX_020_FLIP_Water_Splash

- Category: `flip_water_splash`
- Main Output: `OUT_WATER_SPLASH_MAIN`
- Stable Layers: OUT_MESH_SURFACE, OUT_DROPLETS, OUT_WHITEWATER_PROXY, OUT_TRIGGER_METADATA
- Cache Types: bgeo, vdb, abc, exr
- Preview Mode: droplet point proxy
- Solver Upgrade: FLIP tank/splash + whitewater; deferred after v004
- Preferred Handoff: Alembic for meshed water, VDB/BGEO for Houdini cache, EXR for splash comp passes
- Shot Use: impact splash, falling water, liquid hit, secondary droplets
- Risk: `high`

### HFX_021_Advanced_Pyro_Explosion

- Category: `advanced_pyro_explosion`
- Main Output: `OUT_PYRO_EXPLOSION_MAIN`
- Stable Layers: OUT_FIRE_CORE, OUT_SMOKE_ROLL, OUT_BLAST_MASK, OUT_TRIGGER_METADATA
- Cache Types: bgeo, vdb, exr
- Preview Mode: point-volume pyro proxy
- Solver Upgrade: Pyro sparse solver / combustion / disturbance / shredding; deferred after v004
- Preferred Handoff: VDB for volume render, EXR for final comp, BGEO for Houdini iteration
- Shot Use: hero explosion, fireball, rolling smoke, blast core, heat support
- Risk: `very_high`

### HFX_022_Storm_Cloud_Volume

- Category: `storm_cloud_volume`
- Main Output: `OUT_STORM_CLOUD_MAIN`
- Stable Layers: OUT_DENSITY_VOLUME, OUT_LIGHTING_MASK, OUT_EDGE_BREAKUP, OUT_TRIGGER_METADATA
- Cache Types: bgeo, vdb, exr
- Preview Mode: storm cloud point-density proxy
- Solver Upgrade: procedural VDB cloud volume / noise field / wind advection; deferred after v004
- Preferred Handoff: VDB for cloud volume, EXR for atmosphere/matte, BGEO for Houdini iteration
- Shot Use: cloud wall, storm bank, large environment volume, sky pressure
- Risk: `high`

### HFX_023_Ground_Collapse_Sinkhole

- Category: `rbd_ground_collapse`
- Main Output: `OUT_GROUND_COLLAPSE_MAIN`
- Stable Layers: OUT_TERRAIN_PLATES, OUT_FALLING_ROCKS, OUT_CRACK_MASK, OUT_TRIGGER_METADATA
- Cache Types: bgeo, abc, fbx, exr
- Preview Mode: terrain collapse point proxy
- Solver Upgrade: RBD terrain fracture / Boolean fracture / crater deformation; deferred after v004
- Preferred Handoff: Alembic for falling terrain pieces, FBX for proxy terrain, EXR for crack/mask pass
- Shot Use: floor collapse, sinkhole, crater, rock fall, terrain destruction
- Risk: `high`

### HFX_024_Energy_Shield_Shatter

- Category: `energy_shield_fracture`
- Main Output: `OUT_SHIELD_SHATTER_MAIN`
- Stable Layers: OUT_SHIELD_PIECES, OUT_CRACK_LINES, OUT_ENERGY_RIPPLE, OUT_TRIGGER_METADATA
- Cache Types: bgeo, abc, exr
- Preview Mode: ring/particle shield proxy
- Solver Upgrade: procedural shield shell fracture + energy ripple + crack propagation; deferred after v004
- Preferred Handoff: Alembic for shield pieces, EXR for glow/crack/ripple comp passes, BGEO for Houdini iteration
- Shot Use: sci-fi shield hit, magical barrier break, energy shell fracture
- Risk: `medium_high`

