# HFX Batch 04 Character Magic Environment v004 Production Spec

Status: HFX_B04_CHARACTER_MAGIC_ENVIRONMENT_V004_PRODUCTION_SPEC_READY

Purpose:
Define production/cache/export/handoff rules for Batch 04 character magic and stylized environment Houdini FX assets.

Global Rules:
- Do not modify Batch 01 final sealed release.
- Do not modify Batch 02 final sealed release.
- Do not modify Batch 03 final sealed release.
- Every asset must keep cheap preview mode.
- Every asset must preserve stable OUT nodes and OUT_TRIGGER_METADATA.
- EXR/comp-facing passes must remain separated from geometry-facing outputs.
- Cache exports must be versioned and non-overwriting.
- Unreal handoff should prefer baked Alembic/VDB/EXR unless Houdini Engine is explicitly validated.
- DaVinci/AE handoff should use EXR pass separation for glow/matte/distortion/heat/scan layers.
- ComfyUI use is allowed only as post/repair/stylization layer, not as source-of-truth geometry.

## Asset Specs

### HFX_025_Character_Energy_Field

- Category: `character_energy_aura`
- Main Output: `OUT_ENERGY_FIELD_MAIN`
- Stable Layers: OUT_AURA_SHELL, OUT_ORBIT_PARTICLES, OUT_GLOW_MASK, OUT_TRIGGER_METADATA
- Cache Types: bgeo, abc, exr
- Preview Mode: light VEX character aura pulse proxy
- Hero Upgrade: body-following aura shell, orbiting particles, animated glow mask, character attachment controls
- Preferred Handoff: Alembic for aura geometry/proxy, EXR for glow/mask comp, BGEO for Houdini iteration
- Shot Use: power-up, anime aura, superhero transformation, character energy shell
- Comp Passes: beauty_proxy, glow_mask, aura_shell, orbit_particles, depth_optional
- Risk: `medium`

### HFX_026_Ground_Magic_Rune_Circle

- Category: `ground_magic_rune`
- Main Output: `OUT_RUNE_CIRCLE_MAIN`
- Stable Layers: OUT_RING_LINES, OUT_RUNE_GLYPHS, OUT_GLOW_MASK, OUT_TRIGGER_METADATA
- Cache Types: bgeo, abc, exr
- Preview Mode: no-VEX cook-safe point proxy after v002 repair
- Hero Upgrade: procedural rune glyph curves, rotating rings, reveal masks, decal-friendly EXR pass
- Preferred Handoff: EXR for rune glow/matte passes, Alembic for animated ring geometry, BGEO for Houdini iteration
- Shot Use: summoning floor, ritual mark, magic circle, ground decal comp layer
- Comp Passes: ring_lines, rune_glyphs, glow_mask, reveal_mask, decal_matte
- Risk: `medium`

### HFX_027_Summoning_Portal_Gate

- Category: `summoning_portal_gate`
- Main Output: `OUT_PORTAL_GATE_MAIN`
- Stable Layers: OUT_PORTAL_RING, OUT_PORTAL_INTERIOR, OUT_EDGE_ENERGY, OUT_TRIGGER_METADATA
- Cache Types: bgeo, vdb, abc, exr
- Preview Mode: light VEX circular portal proxy
- Hero Upgrade: animated portal ring, interior vortex, edge energy, distortion matte
- Preferred Handoff: Alembic for portal ring, VDB/BGEO for volume interior, EXR for portal comp passes
- Shot Use: hero portal, summon gate, circular dimensional opening, background comp portal
- Comp Passes: portal_ring, portal_interior, edge_energy, distortion_mask, glow_mask
- Risk: `medium_high`

### HFX_028_Space_Rift_Tear

- Category: `space_rift_tear`
- Main Output: `OUT_RIFT_TEAR_MAIN`
- Stable Layers: OUT_RIFT_EDGE, OUT_VOID_CORE, OUT_DISTORTION_MASK, OUT_TRIGGER_METADATA
- Cache Types: bgeo, abc, exr
- Preview Mode: no-VEX cook-safe point proxy after v002 repair
- Hero Upgrade: animated jagged rift edge, void core, chromatic distortion mask, comp-friendly split layers
- Preferred Handoff: EXR for void/distortion/matte passes, Alembic for rift edge geometry, BGEO for Houdini iteration
- Shot Use: dimensional crack, black slit, anime space tear, unstable portal edge
- Comp Passes: rift_edge, void_core, distortion_mask, glow_edge, alpha_matte
- Risk: `medium_high`

### HFX_029_Black_Hole_Accretion_Disk

- Category: `black_hole_accretion_disk`
- Main Output: `OUT_BLACK_HOLE_MAIN`
- Stable Layers: OUT_ACCRETION_DISK, OUT_GRAVITY_LENS_MASK, OUT_PARTICLE_SPIRAL, OUT_TRIGGER_METADATA
- Cache Types: bgeo, vdb, abc, exr
- Preview Mode: light VEX accretion disk point proxy
- Hero Upgrade: accretion disk swirl, lensing mask, particle spiral, heat/glow separation
- Preferred Handoff: EXR for lensing/matte/heat passes, Alembic for spiral particles, VDB/BGEO for volume/disk iteration
- Shot Use: black hole shot, gravity object, sci-fi orb, distortion source
- Comp Passes: accretion_disk, gravity_lens_mask, particle_spiral, heat_glow, core_matte
- Risk: `high`

### HFX_030_Ice_Freeze_Spread

- Category: `ice_freeze_spread`
- Main Output: `OUT_ICE_SPREAD_MAIN`
- Stable Layers: OUT_FROST_LINES, OUT_ICE_CRYSTALS, OUT_FREEZE_MASK, OUT_TRIGGER_METADATA
- Cache Types: bgeo, abc, exr
- Preview Mode: no-VEX cook-safe point proxy after v002 repair
- Hero Upgrade: branching frost lines, crystal growth, surface freeze mask, timed reveal control
- Preferred Handoff: EXR for freeze/reveal masks, Alembic for ice crystal geometry, BGEO for Houdini iteration
- Shot Use: ice power, freezing ground, frost spread, surface takeover
- Comp Passes: frost_lines, ice_crystals, freeze_mask, reveal_mask, specular_matte
- Risk: `medium`

### HFX_031_Ground_Fire_Crawl

- Category: `ground_fire_crawl`
- Main Output: `OUT_GROUND_FIRE_MAIN`
- Stable Layers: OUT_FIRE_FRONT, OUT_EMBER_TRAIL, OUT_HEAT_MASK, OUT_TRIGGER_METADATA
- Cache Types: bgeo, vdb, abc, exr
- Preview Mode: no-VEX cook-safe point proxy after v002 repair
- Hero Upgrade: ground flame front, ember trail, heat distortion mask, VDB fire optional
- Preferred Handoff: EXR for flame/heat/ember comp passes, VDB for hero fire volume, Alembic/BGEO for proxy geometry
- Shot Use: fire crawl, burning floor, anime fire line, ground ignition
- Comp Passes: fire_front, ember_trail, heat_mask, glow_mask, smoke_optional
- Risk: `medium_high`

### HFX_032_EMP_Scan_Wave

- Category: `emp_scan_wave`
- Main Output: `OUT_EMP_SCAN_MAIN`
- Stable Layers: OUT_SCAN_RING, OUT_GRID_LINES, OUT_GLITCH_MASK, OUT_TRIGGER_METADATA
- Cache Types: bgeo, abc, exr
- Preview Mode: no-VEX cook-safe point proxy after v002 repair
- Hero Upgrade: expanding scan ring, grid line reveal, glitch mask, sci-fi pulse timing
- Preferred Handoff: EXR for scan/glitch masks, Alembic for ring/grid geometry, BGEO for Houdini iteration
- Shot Use: EMP pulse, sci-fi scan, environmental detection wave, digital shock ring
- Comp Passes: scan_ring, grid_lines, glitch_mask, emission_mask, alpha_matte
- Risk: `medium`

