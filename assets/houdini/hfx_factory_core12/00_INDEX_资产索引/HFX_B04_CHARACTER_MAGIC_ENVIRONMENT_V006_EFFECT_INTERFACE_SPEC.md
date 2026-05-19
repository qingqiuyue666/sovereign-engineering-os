# HFX Batch 04 Character Magic Environment v006 Effect Interface Spec

Status: HFX_B04_CHARACTER_MAGIC_ENVIRONMENT_V006_EFFECT_INTERFACE_SPEC_READY

Purpose:
Freeze effect interface contracts before wrapper/preflight stages. This stage does not build hero networks.

Global Rules:
- Preview mode must always exist.
- Hero mode is blocked unless all input/cache/budget/output/comp contracts are present.
- Stable OUT nodes must not be renamed.
- OUT_TRIGGER_METADATA must remain available.
- EXR/comp passes must remain separated.
- Cache exports must be versioned.
- Batch 01, Batch 02, and Batch 03 sealed releases are immutable.

## Interfaces

### HFX_025_Character_Energy_Field

- Interface: `B04_CHARACTER_AURA_EFFECT_INTERFACE`
- Family: `CHARACTER_AURA`
- Main Output: `OUT_ENERGY_FIELD_MAIN`
- Stable Layers: OUT_AURA_SHELL, OUT_ORBIT_PARTICLES, OUT_GLOW_MASK, OUT_TRIGGER_METADATA
- Inputs: optional_character_proxy, optional_skeleton_root, optional_camera_vector
- Cache Types: bgeo, abc, exr
- Comp Passes: beauty_proxy, glow_mask, aura_shell, orbit_particles, depth_optional

### HFX_026_Ground_Magic_Rune_Circle

- Interface: `B04_GROUND_RUNE_EFFECT_INTERFACE`
- Family: `MAGIC_RUNE`
- Main Output: `OUT_RUNE_CIRCLE_MAIN`
- Stable Layers: OUT_RING_LINES, OUT_RUNE_GLYPHS, OUT_GLOW_MASK, OUT_TRIGGER_METADATA
- Inputs: optional_ground_plane, optional_center_point, optional_camera_vector
- Cache Types: bgeo, abc, exr
- Comp Passes: ring_lines, rune_glyphs, glow_mask, reveal_mask, decal_matte

### HFX_027_Summoning_Portal_Gate

- Interface: `B04_SUMMONING_PORTAL_EFFECT_INTERFACE`
- Family: `PORTAL_GATE`
- Main Output: `OUT_PORTAL_GATE_MAIN`
- Stable Layers: OUT_PORTAL_RING, OUT_PORTAL_INTERIOR, OUT_EDGE_ENERGY, OUT_TRIGGER_METADATA
- Inputs: optional_portal_frame, optional_camera_vector, optional_destination_plate
- Cache Types: bgeo, vdb, abc, exr
- Comp Passes: portal_ring, portal_interior, edge_energy, distortion_mask, glow_mask

### HFX_028_Space_Rift_Tear

- Interface: `B04_SPACE_RIFT_EFFECT_INTERFACE`
- Family: `SPACE_RIFT`
- Main Output: `OUT_RIFT_TEAR_MAIN`
- Stable Layers: OUT_RIFT_EDGE, OUT_VOID_CORE, OUT_DISTORTION_MASK, OUT_TRIGGER_METADATA
- Inputs: optional_rift_curve, optional_camera_vector, optional_depth_plate
- Cache Types: bgeo, abc, exr
- Comp Passes: rift_edge, void_core, distortion_mask, glow_edge, alpha_matte

### HFX_029_Black_Hole_Accretion_Disk

- Interface: `B04_BLACK_HOLE_EFFECT_INTERFACE`
- Family: `BLACK_HOLE_GRAVITY`
- Main Output: `OUT_BLACK_HOLE_MAIN`
- Stable Layers: OUT_ACCRETION_DISK, OUT_GRAVITY_LENS_MASK, OUT_PARTICLE_SPIRAL, OUT_TRIGGER_METADATA
- Inputs: optional_center_point, optional_camera_vector, optional_lensing_plate
- Cache Types: bgeo, vdb, abc, exr
- Comp Passes: accretion_disk, gravity_lens_mask, particle_spiral, heat_glow, core_matte

### HFX_030_Ice_Freeze_Spread

- Interface: `B04_ICE_FREEZE_EFFECT_INTERFACE`
- Family: `ICE_GROWTH`
- Main Output: `OUT_ICE_SPREAD_MAIN`
- Stable Layers: OUT_FROST_LINES, OUT_ICE_CRYSTALS, OUT_FREEZE_MASK, OUT_TRIGGER_METADATA
- Inputs: optional_surface_mesh, optional_start_point, optional_surface_uv
- Cache Types: bgeo, abc, exr
- Comp Passes: frost_lines, ice_crystals, freeze_mask, reveal_mask, specular_matte

### HFX_031_Ground_Fire_Crawl

- Interface: `B04_GROUND_FIRE_EFFECT_INTERFACE`
- Family: `GROUND_FIRE`
- Main Output: `OUT_GROUND_FIRE_MAIN`
- Stable Layers: OUT_FIRE_FRONT, OUT_EMBER_TRAIL, OUT_HEAT_MASK, OUT_TRIGGER_METADATA
- Inputs: optional_ground_plane, optional_ignition_point, optional_wind_vector
- Cache Types: bgeo, vdb, abc, exr
- Comp Passes: fire_front, ember_trail, heat_mask, glow_mask, smoke_optional

### HFX_032_EMP_Scan_Wave

- Interface: `B04_EMP_SCAN_EFFECT_INTERFACE`
- Family: `EMP_SCAN`
- Main Output: `OUT_EMP_SCAN_MAIN`
- Stable Layers: OUT_SCAN_RING, OUT_GRID_LINES, OUT_GLITCH_MASK, OUT_TRIGGER_METADATA
- Inputs: optional_center_point, optional_ground_plane, optional_scene_bounds
- Cache Types: bgeo, abc, exr
- Comp Passes: scan_ring, grid_lines, glitch_mask, emission_mask, alpha_matte

