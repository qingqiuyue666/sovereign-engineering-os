# HFX Batch 05 Cinematic Compositing Render Passes v001 Rulebook

Status: HFX_B05_CINEMATIC_COMPOSITING_RENDER_PASSES_V001_RULEBOOK_READY

Purpose:
Batch 05 adds the compositing/render-pass delivery layer for the sealed Houdini FX library.

This batch is not a new spectacle-FX batch.
It is the production handoff layer that makes prior FX usable in real shots.

Batch 01 solved:
- core action FX

Batch 02 solved:
- cinematic support FX

Batch 03 solved:
- heavyweight support FX

Batch 04 solved:
- character magic and stylized environment FX

Batch 05 adds:
- glow/emission pass
- z-depth/fog pass
- distortion/heat/shockwave mask
- alpha/holdout matte
- light wrap/rim interaction
- contact shadow/ground integration
- lens dirt/bloom streak proxy
- Unreal/DaVinci/AE handoff template

## Asset List

1. HFX_033_Glow_Emission_Pass
   Role: universal glow/emission support pass for energy, magic, fire, portal, shield, aura
   Preferred Export: EXR / ABC / BGEO
   Primary Use: DaVinci/AE glow isolation, bloom, color bleed, emissive control

2. HFX_034_ZDepth_Fog_Pass
   Role: z-depth and distance fog support pass
   Preferred Export: EXR / ABC / BGEO
   Primary Use: spatial depth, atmospheric layering, DaVinci depth/fog control

3. HFX_035_Distortion_Heat_Shockwave_Mask
   Role: heat haze, shockwave, air refraction, distortion vector/mask proxy
   Preferred Export: EXR / ABC / BGEO
   Primary Use: heat distortion, impact shockwave, portal distortion, black hole lensing support

4. HFX_036_Alpha_Holdout_Matte
   Role: alpha, holdout, occlusion matte, foreground/background separation
   Preferred Export: EXR / ABC / BGEO
   Primary Use: real footage integration, subject/FX occlusion, matte extraction support

5. HFX_037_LightWrap_Rim_Interaction
   Role: light wrap, rim interaction, edge contamination proxy
   Preferred Export: EXR / ABC / BGEO
   Primary Use: CG/real footage fusion, edge glow, backlight integration

6. HFX_038_ContactShadow_Ground_Integration
   Role: contact shadow, ground integration, foot/FX grounding
   Preferred Export: EXR / ABC / BGEO
   Primary Use: grounding FX into Unreal/live-action plate, contact shadow matte

7. HFX_039_LensDirt_BloomStreak_Proxy
   Role: lens dirt, bloom streak, flare proxy, dirty lens response
   Preferred Export: EXR / ABC / BGEO
   Primary Use: final polish, lens response, bloom streak layer

8. HFX_040_Unreal_DaVinci_AE_Handoff_Template
   Role: standardized handoff template for Unreal, DaVinci, AE, and ComfyUI repair/stylization
   Preferred Export: EXR / ABC / BGEO / JSON
   Primary Use: shot package structure, naming, pass mapping, delivery manifest

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
- Do not modify Batch 04 final seal.
- Batch 05 starts from HFX_033.
- All assets must support EXR-oriented handoff policy.
- All assets must preserve separated pass outputs.
- No flattening of comp passes.
- No destructive overwrite of render/cache exports.
- Unreal handoff must be explicit.
- DaVinci/AE handoff must be explicit.
- ComfyUI is allowed only as post/repair/stylization layer, not source-of-truth geometry.
- No external downloads, videos, archives, or macOS pollution in asset folders.
