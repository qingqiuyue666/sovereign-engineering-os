# HFX Batch 04 Character Magic Environment v007 Wrapper Spec

Status: HFX_B04_CHARACTER_MAGIC_ENVIRONMENT_V007_WRAPPER_SPEC_READY

Purpose:
Define HDA wrapper contracts before packaging preflight. This stage does not package HDA files and does not build hero networks.

Global Rules:
- Wrapper source is v003 HIP.
- Effect interface source is v006.
- Preview mode is default enabled.
- Hero mode is default blocked.
- Cache execution is default blocked.
- Comp pass flattening is forbidden.
- Stable OUT nodes must not be renamed.
- OUT_TRIGGER_METADATA must remain available.
- Batch 01, Batch 02, and Batch 03 sealed releases are immutable.

## Wrapper Targets

### HFX_025_Character_Energy_Field

- HDA Type: `qqy::hfx_character_energy_field::4.0`
- Wrapper Name: `WRAP_HFX_025_Character_Energy_Field_v007`
- Source Geo: `HFX_025_Character_Energy_Field_v003`
- Effect Interface: `B04_CHARACTER_AURA_EFFECT_INTERFACE`
- Main Output: `OUT_ENERGY_FIELD_MAIN`
- Stable Outputs: OUT_ENERGY_FIELD_MAIN, OUT_AURA_SHELL, OUT_ORBIT_PARTICLES, OUT_GLOW_MASK, OUT_TRIGGER_METADATA

### HFX_026_Ground_Magic_Rune_Circle

- HDA Type: `qqy::hfx_ground_magic_rune_circle::4.0`
- Wrapper Name: `WRAP_HFX_026_Ground_Magic_Rune_Circle_v007`
- Source Geo: `HFX_026_Ground_Magic_Rune_Circle_v003`
- Effect Interface: `B04_GROUND_RUNE_EFFECT_INTERFACE`
- Main Output: `OUT_RUNE_CIRCLE_MAIN`
- Stable Outputs: OUT_RUNE_CIRCLE_MAIN, OUT_RING_LINES, OUT_RUNE_GLYPHS, OUT_GLOW_MASK, OUT_TRIGGER_METADATA

### HFX_027_Summoning_Portal_Gate

- HDA Type: `qqy::hfx_summoning_portal_gate::4.0`
- Wrapper Name: `WRAP_HFX_027_Summoning_Portal_Gate_v007`
- Source Geo: `HFX_027_Summoning_Portal_Gate_v003`
- Effect Interface: `B04_SUMMONING_PORTAL_EFFECT_INTERFACE`
- Main Output: `OUT_PORTAL_GATE_MAIN`
- Stable Outputs: OUT_PORTAL_GATE_MAIN, OUT_PORTAL_RING, OUT_PORTAL_INTERIOR, OUT_EDGE_ENERGY, OUT_TRIGGER_METADATA

### HFX_028_Space_Rift_Tear

- HDA Type: `qqy::hfx_space_rift_tear::4.0`
- Wrapper Name: `WRAP_HFX_028_Space_Rift_Tear_v007`
- Source Geo: `HFX_028_Space_Rift_Tear_v003`
- Effect Interface: `B04_SPACE_RIFT_EFFECT_INTERFACE`
- Main Output: `OUT_RIFT_TEAR_MAIN`
- Stable Outputs: OUT_RIFT_TEAR_MAIN, OUT_RIFT_EDGE, OUT_VOID_CORE, OUT_DISTORTION_MASK, OUT_TRIGGER_METADATA

### HFX_029_Black_Hole_Accretion_Disk

- HDA Type: `qqy::hfx_black_hole_accretion_disk::4.0`
- Wrapper Name: `WRAP_HFX_029_Black_Hole_Accretion_Disk_v007`
- Source Geo: `HFX_029_Black_Hole_Accretion_Disk_v003`
- Effect Interface: `B04_BLACK_HOLE_EFFECT_INTERFACE`
- Main Output: `OUT_BLACK_HOLE_MAIN`
- Stable Outputs: OUT_BLACK_HOLE_MAIN, OUT_ACCRETION_DISK, OUT_GRAVITY_LENS_MASK, OUT_PARTICLE_SPIRAL, OUT_TRIGGER_METADATA

### HFX_030_Ice_Freeze_Spread

- HDA Type: `qqy::hfx_ice_freeze_spread::4.0`
- Wrapper Name: `WRAP_HFX_030_Ice_Freeze_Spread_v007`
- Source Geo: `HFX_030_Ice_Freeze_Spread_v003`
- Effect Interface: `B04_ICE_FREEZE_EFFECT_INTERFACE`
- Main Output: `OUT_ICE_SPREAD_MAIN`
- Stable Outputs: OUT_ICE_SPREAD_MAIN, OUT_FROST_LINES, OUT_ICE_CRYSTALS, OUT_FREEZE_MASK, OUT_TRIGGER_METADATA

### HFX_031_Ground_Fire_Crawl

- HDA Type: `qqy::hfx_ground_fire_crawl::4.0`
- Wrapper Name: `WRAP_HFX_031_Ground_Fire_Crawl_v007`
- Source Geo: `HFX_031_Ground_Fire_Crawl_v003`
- Effect Interface: `B04_GROUND_FIRE_EFFECT_INTERFACE`
- Main Output: `OUT_GROUND_FIRE_MAIN`
- Stable Outputs: OUT_GROUND_FIRE_MAIN, OUT_FIRE_FRONT, OUT_EMBER_TRAIL, OUT_HEAT_MASK, OUT_TRIGGER_METADATA

### HFX_032_EMP_Scan_Wave

- HDA Type: `qqy::hfx_emp_scan_wave::4.0`
- Wrapper Name: `WRAP_HFX_032_EMP_Scan_Wave_v007`
- Source Geo: `HFX_032_EMP_Scan_Wave_v003`
- Effect Interface: `B04_EMP_SCAN_EFFECT_INTERFACE`
- Main Output: `OUT_EMP_SCAN_MAIN`
- Stable Outputs: OUT_EMP_SCAN_MAIN, OUT_SCAN_RING, OUT_GRID_LINES, OUT_GLITCH_MASK, OUT_TRIGGER_METADATA

