# HFX Batch 04 Character Magic Environment v005 Hero Upgrade Candidate Spec

Status: HFX_B04_CHARACTER_MAGIC_ENVIRONMENT_V005_HERO_UPGRADE_CANDIDATE_SPEC_READY

Purpose:
Define candidate hero upgrade families and upgrade gates before introducing final stylized hero networks.

Global Rules:
- v005 does not build hero networks.
- v005 defines candidate hero upgrade contracts only.
- Preview mode must remain available for every asset.
- Hero mode must be explicitly gated.
- Stable OUT nodes must not be renamed.
- OUT_TRIGGER_METADATA must remain available.
- EXR comp passes must remain separated.
- No silent mutation of Batch 01, Batch 02, or Batch 03 sealed releases.

## Hero Upgrade Candidates

### HFX_025_Character_Energy_Field

- Candidate Family: `CHARACTER_AURA`
- Candidate Upgrade: body-following aura shell + orbiting particles + glow matte + character attach controls
- Preview Mode: `LIGHT_VEX_AURA_PROXY`
- Hero Mode: `CHARACTER_AURA_HERO`
- Main Output: `OUT_ENERGY_FIELD_MAIN`
- Layers: OUT_AURA_SHELL, OUT_ORBIT_PARTICLES, OUT_GLOW_MASK, OUT_TRIGGER_METADATA
- Comp Passes: beauty_proxy, glow_mask, aura_shell, orbit_particles, depth_optional
- Cache Types: bgeo, abc, exr
- Risk: `medium`
- Upgrade Gate: must pass character scale, attachment, glow/matte separation, and cache version contracts

### HFX_026_Ground_Magic_Rune_Circle

- Candidate Family: `MAGIC_RUNE`
- Candidate Upgrade: procedural rune glyph curves + rotating rings + reveal mask + decal-friendly EXR pass
- Preview Mode: `NO_VEX_RUNE_PROXY`
- Hero Mode: `GROUND_RUNE_HERO`
- Main Output: `OUT_RUNE_CIRCLE_MAIN`
- Layers: OUT_RING_LINES, OUT_RUNE_GLYPHS, OUT_GLOW_MASK, OUT_TRIGGER_METADATA
- Comp Passes: ring_lines, rune_glyphs, glow_mask, reveal_mask, decal_matte
- Cache Types: bgeo, abc, exr
- Risk: `medium`
- Upgrade Gate: must pass glyph curve contract, EXR pass separation, decal scale, and no-VEX fallback contract

### HFX_027_Summoning_Portal_Gate

- Candidate Family: `PORTAL_GATE`
- Candidate Upgrade: animated portal ring + vortex interior + edge energy + distortion matte
- Preview Mode: `LIGHT_VEX_PORTAL_PROXY`
- Hero Mode: `SUMMONING_PORTAL_HERO`
- Main Output: `OUT_PORTAL_GATE_MAIN`
- Layers: OUT_PORTAL_RING, OUT_PORTAL_INTERIOR, OUT_EDGE_ENERGY, OUT_TRIGGER_METADATA
- Comp Passes: portal_ring, portal_interior, edge_energy, distortion_mask, glow_mask
- Cache Types: bgeo, vdb, abc, exr
- Risk: `medium_high`
- Upgrade Gate: must pass portal radius, camera-facing orientation, interior/edge separation, distortion pass, and cache budget

### HFX_028_Space_Rift_Tear

- Candidate Family: `SPACE_RIFT`
- Candidate Upgrade: jagged rift edge + void core + chromatic distortion mask + alpha matte
- Preview Mode: `NO_VEX_RIFT_PROXY`
- Hero Mode: `SPACE_RIFT_HERO`
- Main Output: `OUT_RIFT_TEAR_MAIN`
- Layers: OUT_RIFT_EDGE, OUT_VOID_CORE, OUT_DISTORTION_MASK, OUT_TRIGGER_METADATA
- Comp Passes: rift_edge, void_core, distortion_mask, glow_edge, alpha_matte
- Cache Types: bgeo, abc, exr
- Risk: `medium_high`
- Upgrade Gate: must pass rift curve topology, void/core separation, distortion matte, and no-VEX fallback contract

### HFX_029_Black_Hole_Accretion_Disk

- Candidate Family: `BLACK_HOLE_GRAVITY`
- Candidate Upgrade: accretion disk swirl + lensing mask + particle spiral + heat/glow separation
- Preview Mode: `LIGHT_VEX_BLACK_HOLE_PROXY`
- Hero Mode: `BLACK_HOLE_ACCRETION_HERO`
- Main Output: `OUT_BLACK_HOLE_MAIN`
- Layers: OUT_ACCRETION_DISK, OUT_GRAVITY_LENS_MASK, OUT_PARTICLE_SPIRAL, OUT_TRIGGER_METADATA
- Comp Passes: accretion_disk, gravity_lens_mask, particle_spiral, heat_glow, core_matte
- Cache Types: bgeo, vdb, abc, exr
- Risk: `high`
- Upgrade Gate: must pass disk orientation, lensing mask policy, particle count budget, EXR split, and cache budget

### HFX_030_Ice_Freeze_Spread

- Candidate Family: `ICE_GROWTH`
- Candidate Upgrade: branching frost lines + ice crystal growth + surface freeze mask + timed reveal control
- Preview Mode: `NO_VEX_ICE_PROXY`
- Hero Mode: `ICE_FREEZE_SPREAD_HERO`
- Main Output: `OUT_ICE_SPREAD_MAIN`
- Layers: OUT_FROST_LINES, OUT_ICE_CRYSTALS, OUT_FREEZE_MASK, OUT_TRIGGER_METADATA
- Comp Passes: frost_lines, ice_crystals, freeze_mask, reveal_mask, specular_matte
- Cache Types: bgeo, abc, exr
- Risk: `medium`
- Upgrade Gate: must pass branching curve contract, freeze/reveal mask separation, surface scale, and no-VEX fallback contract

### HFX_031_Ground_Fire_Crawl

- Candidate Family: `GROUND_FIRE`
- Candidate Upgrade: ground flame front + ember trail + heat distortion mask + optional VDB fire
- Preview Mode: `NO_VEX_FIRE_PROXY`
- Hero Mode: `GROUND_FIRE_CRAWL_HERO`
- Main Output: `OUT_GROUND_FIRE_MAIN`
- Layers: OUT_FIRE_FRONT, OUT_EMBER_TRAIL, OUT_HEAT_MASK, OUT_TRIGGER_METADATA
- Comp Passes: fire_front, ember_trail, heat_mask, glow_mask, smoke_optional
- Cache Types: bgeo, vdb, abc, exr
- Risk: `medium_high`
- Upgrade Gate: must pass flame front mask, heat distortion pass, VDB optional budget, and no-VEX fallback contract

### HFX_032_EMP_Scan_Wave

- Candidate Family: `EMP_SCAN`
- Candidate Upgrade: expanding scan ring + grid reveal + glitch mask + sci-fi pulse timing
- Preview Mode: `NO_VEX_EMP_PROXY`
- Hero Mode: `EMP_SCAN_WAVE_HERO`
- Main Output: `OUT_EMP_SCAN_MAIN`
- Layers: OUT_SCAN_RING, OUT_GRID_LINES, OUT_GLITCH_MASK, OUT_TRIGGER_METADATA
- Comp Passes: scan_ring, grid_lines, glitch_mask, emission_mask, alpha_matte
- Cache Types: bgeo, abc, exr
- Risk: `medium`
- Upgrade Gate: must pass scan radius, ring/grid separation, glitch matte policy, and no-VEX fallback contract

