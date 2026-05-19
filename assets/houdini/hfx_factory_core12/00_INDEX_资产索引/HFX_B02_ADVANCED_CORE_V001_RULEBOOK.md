# HFX Batch 02 Advanced Core v001 Rulebook

Status: HFX_B02_ADVANCED_CORE_V001_RULEBOOK_READY

Purpose:
Extend the sealed Houdini HFX core library with Hollywood-style secondary FX layers.

Batch 01 solved:
- trails
- slash
- dust impact
- dust ring
- small pyro
- cracks/debris
- lightning
- shockwave

Batch 02 adds:
- volumetric atmosphere
- smoke plume
- embers / ash
- sparks
- radial debris
- magic aura
- portal ring
- heat distortion

## Production Role

Batch 02 is not random expansion.
It fills missing Hollywood-style support layers that make shots feel expensive:
- air depth
- atmosphere
- foreground particles
- backlit smoke
- secondary destruction
- energy field detail
- spatial transition FX
- heat shimmer

## Asset List

1. HFX_009_Volumetric_Fog_Bank
   Role: cinematic fog layer / atmospheric depth / backlight beam support
   Preferred Export: VDB / EXR
   Unreal Use: background atmosphere, plate integration, depth separation

2. HFX_010_Smoke_Plume_Column
   Role: smoke column / explosion aftermath / rising dust-smoke plume
   Preferred Export: VDB / EXR
   Unreal Use: explosion aftermath, background smoke, destruction environment

3. HFX_011_Ember_Ash_Field
   Role: floating embers / ash field / foreground particle texture
   Preferred Export: Alembic / BGEO / EXR
   Unreal Use: cinematic foreground particles, fire aftermath

4. HFX_012_Sparks_Impact_Spray
   Role: metal sparks / weapon clash / bullet hit / impact spray
   Preferred Export: Alembic / BGEO / EXR
   Unreal Use: action hit detail, slash impact, contact accents

5. HFX_013_Debris_Burst_Radial
   Role: secondary debris burst / blast debris / ground ejecta
   Preferred Export: Alembic / FBX / BGEO
   Unreal Use: impact enhancement, destruction support

6. HFX_014_Magic_Particle_Aura
   Role: character aura / magic energy field / charge-up layer
   Preferred Export: Alembic / EXR / point cache
   Unreal Use: character power-up, spell charge, energy buildup

7. HFX_015_Portal_Ring_Field
   Role: portal boundary / spatial ring / transition energy field
   Preferred Export: Alembic / EXR
   Unreal Use: portal transitions, scene entrance, sci-fi/fantasy space tear

8. HFX_016_Heat_Distortion_Field
   Role: heat shimmer / blast distortion / air refraction
   Preferred Export: EXR distortion pass / vector pass
   Unreal Use: pyro support, desert heat, explosion aftermath

## v001 Scope

v001 creates:
- directory skeleton
- README per asset
- batch rulebook
- batch registry
- validation report

v001 does not create final HIP networks yet.
Next stage v002 creates procedural HIP templates.

## Failure Rules

- Missing folder = fail.
- Missing README.md = fail.
- Missing batch registry = fail.
- Pollution files = fail.
- Do not touch HFX_V013_FINAL_SEAL.
