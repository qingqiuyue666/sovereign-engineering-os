# HFX Batch 03 Destruction Cloth Fluid v001 Rulebook

Status: HFX_B03_DESTRUCTION_CLOTH_FLUID_V001_RULEBOOK_READY

Purpose:
Extend the sealed Houdini FX library into heavyweight Hollywood-style simulation categories:
- destruction
- glass
- cloth
- fluid
- advanced pyro
- storm volume
- ground collapse
- energy shield fracture

Batch 01 solved:
- action impact FX
- trails
- slash
- dust
- lightning
- shockwave

Batch 02 solved:
- cinematic support FX
- fog
- smoke
- embers
- sparks
- debris
- aura
- portal
- heat distortion

Batch 03 adds:
- heavyweight simulation classes
- hero-shot destruction
- cloth dynamics
- FLIP water
- advanced pyro
- large volume environment
- structural collapse
- shield fracture

## Asset List

1. HFX_017_Building_Fracture_Collapse
   Role: concrete wall/building fracture, collapsing chunks, hero destruction
   Preferred Export: Alembic / FBX / BGEO
   Unreal Use: baked destruction geometry, background collapse, impact scene destruction

2. HFX_018_Glass_Shatter_Burst
   Role: glass/window shatter, transparent shards, radial burst
   Preferred Export: Alembic / FBX / BGEO
   Unreal Use: window hit, vehicle glass, action collision

3. HFX_019_Vellum_Cape_Cloth_Sim
   Role: cape, cloth strip, banner, robe extension, character-linked cloth motion
   Preferred Export: Alembic / BGEO
   Unreal Use: baked cloth simulation, hero costume movement

4. HFX_020_FLIP_Water_Splash
   Role: water splash, impact splash, falling liquid, secondary droplets
   Preferred Export: Alembic / VDB / BGEO / EXR
   Unreal Use: baked water mesh, splash pass, comp element

5. HFX_021_Advanced_Pyro_Explosion
   Role: hero explosion, fireball, rolling smoke, shock core
   Preferred Export: VDB / EXR / BGEO
   Unreal Use: volume render, comp pass, pyro background

6. HFX_022_Storm_Cloud_Volume
   Role: massive cloud bank, storm wall, sky volume, environmental pressure
   Preferred Export: VDB / EXR / BGEO
   Unreal Use: atmosphere, background, matte volume

7. HFX_023_Ground_Collapse_Sinkhole
   Role: ground collapse, sinkhole, broken terrain, falling chunks
   Preferred Export: Alembic / FBX / BGEO
   Unreal Use: terrain destruction, hero impact floor collapse

8. HFX_024_Energy_Shield_Shatter
   Role: sci-fi shield cracking, barrier shatter, energy shell fracture
   Preferred Export: Alembic / EXR / BGEO
   Unreal Use: energy shield hit, magical barrier break, sci-fi defense layer

## v001 Scope

v001 creates:
- directory skeleton
- README per asset
- batch rulebook
- batch registry
- validation report
- pollution check

v001 does not create final simulation networks.
v002 creates stable ultra-safe HIP templates.

## Hard Rules

- Do not modify Batch 01 final seal.
- Do not modify Batch 02 final seal.
- Batch 03 starts from HFX_017.
- Heavy solvers must be introduced in controlled stages, not in v001.
- All later heavy sims must preserve cheap preview mode.
- No external downloads, videos, archives, or macOS pollution in asset folders.
- Future cache exports must be versioned and non-overwriting.
