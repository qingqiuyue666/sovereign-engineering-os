# HFX Batch 05 Cinematic Compositing Render Passes v004 Production Spec

Status: HFX_B05_CINEMATIC_COMPOSITING_RENDER_PASSES_V004_PRODUCTION_SPEC_READY

Purpose:
Define production/cache/export/handoff rules for Batch 05 compositing and render-pass assets.

Global Rules:
- Render/export execution remains blocked until explicit shot binding exists.
- EXR pass separation is mandatory.
- Flattened comp passes are forbidden.
- shot_id, take_id, frame_start, frame_end, fps, colorspace, and naming_policy are required before export.
- Unreal handoff must be explicit.
- DaVinci/AE handoff must be explicit.
- ComfyUI is allowed only as post/repair/stylization layer, not source-of-truth geometry.
- Batch 01-04 final sealed releases are immutable.

## Asset Specs

### HFX_033_Glow_Emission_Pass

- Category: `glow_emission_pass`
- Main Output: `OUT_GLOW_EMISSION_MAIN`
- Stable Layers: OUT_EMISSION_MASK, OUT_COLOR_BLEED_MASK, OUT_BLOOM_SOURCE, OUT_TRIGGER_METADATA
- Cache Types: bgeo, abc, exr
- Preferred Handoff: EXR for glow/emission masks, Alembic/BGEO for proxy geometry
- Shot Use: energy glow, magic glow, portal bloom, fire emission, aura polish
- Comp Passes: emission_mask, color_bleed_mask, bloom_source, alpha_optional, beauty_proxy
- Colorspace: ACEScg source / Rec709 display transform downstream
- Risk: `medium`

### HFX_034_ZDepth_Fog_Pass

- Category: `zdepth_fog_pass`
- Main Output: `OUT_ZDEPTH_FOG_MAIN`
- Stable Layers: OUT_ZDEPTH_MASK, OUT_DISTANCE_FOG, OUT_ATMOSPHERE_LAYER, OUT_TRIGGER_METADATA
- Cache Types: bgeo, abc, exr
- Preferred Handoff: EXR for depth/fog/matte layers, Alembic/BGEO for spatial proxy
- Shot Use: depth haze, atmosphere layering, DaVinci depth-based polish, Unreal depth integration
- Comp Passes: zdepth_mask, distance_fog, atmosphere_layer, depth_alpha, fog_density
- Colorspace: linear depth scalar / comp-managed display
- Risk: `medium`

### HFX_035_Distortion_Heat_Shockwave_Mask

- Category: `distortion_heat_shockwave_mask`
- Main Output: `OUT_DISTORTION_MAIN`
- Stable Layers: OUT_HEAT_MASK, OUT_SHOCKWAVE_RING, OUT_REFRACTION_VECTOR_PROXY, OUT_TRIGGER_METADATA
- Cache Types: bgeo, abc, exr
- Preferred Handoff: EXR for distortion/heat/refraction vectors, Alembic/BGEO for proxy rings
- Shot Use: heat haze, explosion shockwave, portal distortion, black-hole refraction support
- Comp Passes: heat_mask, shockwave_ring, refraction_vector_proxy, distortion_alpha, falloff_mask
- Colorspace: linear scalar/vector pass / comp-managed display
- Risk: `medium_high`

### HFX_036_Alpha_Holdout_Matte

- Category: `alpha_holdout_matte`
- Main Output: `OUT_ALPHA_HOLDOUT_MAIN`
- Stable Layers: OUT_FOREGROUND_MATTE, OUT_OCCLUSION_MATTE, OUT_EDGE_MATTE, OUT_TRIGGER_METADATA
- Cache Types: bgeo, abc, exr
- Preferred Handoff: EXR for alpha/holdout/occlusion mattes, Alembic/BGEO for occluder proxy
- Shot Use: foreground holdout, real-footage occlusion, subject/FX layering, edge matte repair
- Comp Passes: foreground_matte, occlusion_matte, edge_matte, holdout_alpha, coverage_mask
- Colorspace: linear matte scalar / non-color data
- Risk: `medium`

### HFX_037_LightWrap_Rim_Interaction

- Category: `lightwrap_rim_interaction`
- Main Output: `OUT_LIGHTWRAP_MAIN`
- Stable Layers: OUT_RIM_MASK, OUT_EDGE_SPILL, OUT_BACKLIGHT_INTERACTION, OUT_TRIGGER_METADATA
- Cache Types: bgeo, abc, exr
- Preferred Handoff: EXR for rim/wrap/spill passes, Alembic/BGEO for edge proxy
- Shot Use: CG/live-action fusion, edge spill, rim interaction, backlight matching
- Comp Passes: rim_mask, edge_spill, backlight_interaction, wrap_alpha, edge_softness
- Colorspace: ACEScg source / comp-managed display
- Risk: `medium`

### HFX_038_ContactShadow_Ground_Integration

- Category: `contact_shadow_ground_integration`
- Main Output: `OUT_CONTACT_SHADOW_MAIN`
- Stable Layers: OUT_GROUND_MATTE, OUT_FOOT_CONTACT, OUT_FX_CONTACT_MASK, OUT_TRIGGER_METADATA
- Cache Types: bgeo, abc, exr
- Preferred Handoff: EXR for contact/ground/fx masks, Alembic/BGEO for ground proxy
- Shot Use: grounding FX, foot contact, shadow matte, Unreal/live-action ground integration
- Comp Passes: ground_matte, foot_contact, fx_contact_mask, contact_shadow, falloff_mask
- Colorspace: linear matte scalar / non-color data
- Risk: `medium`

### HFX_039_LensDirt_BloomStreak_Proxy

- Category: `lens_dirt_bloom_streak_proxy`
- Main Output: `OUT_LENS_DIRT_MAIN`
- Stable Layers: OUT_BLOOM_STREAK, OUT_DIRT_MASK, OUT_FLARE_RESPONSE, OUT_TRIGGER_METADATA
- Cache Types: bgeo, abc, exr
- Preferred Handoff: EXR for bloom/dirt/flare proxy passes, Alembic/BGEO for proxy placement
- Shot Use: final lens polish, bloom streak, dirt response, flare support
- Comp Passes: bloom_streak, dirt_mask, flare_response, threshold_mask, lens_alpha
- Colorspace: ACEScg source / comp-managed display
- Risk: `medium`

### HFX_040_Unreal_DaVinci_AE_Handoff_Template

- Category: `unreal_davinci_ae_handoff_template`
- Main Output: `OUT_HANDOFF_PACKAGE_MAIN`
- Stable Layers: OUT_PASS_MANIFEST, OUT_NAMING_POLICY, OUT_DELIVERY_CHECKLIST, OUT_TRIGGER_METADATA
- Cache Types: bgeo, abc, exr, json
- Preferred Handoff: JSON manifest plus EXR/ABC/BGEO delivery structure
- Shot Use: standardized handoff package, naming policy, pass mapping, delivery validation
- Comp Passes: pass_manifest, naming_policy, delivery_checklist, colorspace_policy, frame_range_policy
- Colorspace: explicit per-shot policy required
- Risk: `low`

