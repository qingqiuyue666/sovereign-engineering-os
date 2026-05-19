# HFX Batch 04 Character Magic Environment v001 Rulebook

Status: HFX_B04_CHARACTER_MAGIC_ENVIRONMENT_V001_RULEBOOK_READY

Purpose:
Extend the sealed Houdini FX library into character-centered, magic-centered, and stylized environment energy effects.

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

Batch 03 solved:
- heavyweight support FX
- destruction
- glass
- cloth
- FLIP water
- pyro
- storm volume
- ground collapse
- shield shatter

Batch 04 adds:
- character aura
- ground runes
- summoning gates
- space rifts
- black hole accretion disks
- ice spread
- ground fire crawl
- EMP scan waves

## Asset List

1. HFX_025_Character_Energy_Field
   Role: character-centered aura, power-up field, body-following energy shell
   Preferred Export: Alembic / EXR / BGEO
   Unreal Use: character aura, power transformation, anime/hero activation

2. HFX_026_Ground_Magic_Rune_Circle
   Role: magic circle, rune floor, ritual mark, summon base
   Preferred Export: Alembic / EXR / BGEO
   Unreal Use: ground decal pass, glowing symbol layer, compositing element

3. HFX_027_Summoning_Portal_Gate
   Role: large circular gate, dimensional opening, summon portal
   Preferred Export: Alembic / VDB / EXR / BGEO
   Unreal Use: hero portal, gate edge, portal interior comp layer

4. HFX_028_Space_Rift_Tear
   Role: space tear, dimensional crack, black slit, unstable edge
   Preferred Export: Alembic / EXR / BGEO
   Unreal Use: rift edge, void tear, stylized compositing layer

5. HFX_029_Black_Hole_Accretion_Disk
   Role: black hole visual, accretion disk, gravity distortion proxy
   Preferred Export: Alembic / VDB / EXR / BGEO
   Unreal Use: sci-fi gravity object, black-hole shot, comp distortion source

6. HFX_030_Ice_Freeze_Spread
   Role: ice growth, frost pattern, freezing surface spread
   Preferred Export: Alembic / EXR / BGEO
   Unreal Use: freezing ground, character power, surface takeover

7. HFX_031_Ground_Fire_Crawl
   Role: fire crawling over ground, burning line, floor flame spread
   Preferred Export: Alembic / VDB / EXR / BGEO
   Unreal Use: ground fire pass, anime fire crawl, compositing flame mask

8. HFX_032_EMP_Scan_Wave
   Role: electromagnetic pulse, scan wave, sci-fi shock scan
   Preferred Export: Alembic / EXR / BGEO
   Unreal Use: scanning wave, EMP burst, HUD-like environmental pulse

## v001 Scope

v001 creates:
- directory skeleton
- README per asset
- batch rulebook
- batch registry
- validation report
- pollution check

v001 does not create final Houdini networks.
v002 creates stable ultra-safe HIP templates.

## Hard Rules

- Do not modify Batch 01 final seal.
- Do not modify Batch 02 final seal.
- Do not modify Batch 03 final seal.
- Batch 04 starts from HFX_025.
- All assets must support cheap preview mode before HDA packaging.
- All assets must preserve separated output layers.
- All comp-facing assets must expose EXR-oriented pass policy later.
- No external downloads, videos, archives, or macOS pollution in asset folders.
- Future cache exports must be versioned and non-overwriting.
