# HFX Batch 05 Cinematic Compositing Render Passes v005 Render Pass Interface Spec

Status: HFX_B05_CINEMATIC_COMPOSITING_RENDER_PASSES_V005_RENDER_PASS_INTERFACE_SPEC_READY

Purpose:
Freeze render-pass interface contracts before wrapper and HDA packaging stages.

Global Rules:
- Preview mode is enabled by default.
- Render/export execution is blocked by default.
- EXR pass separation is required.
- Flattened comp passes are forbidden.
- OUT_TRIGGER_METADATA must remain available.
- Unreal / DaVinci / AE handoff must be explicit.
- ComfyUI is post/repair/stylization only, not source-of-truth geometry.
- Batch 01-04 final seals are immutable.

## Interfaces

### HFX_033_Glow_Emission_Pass

- Interface: `B05_GLOW_EMISSION_RENDER_PASS_INTERFACE`
- Family: `GLOW_EMISSION`
- Main Output: `OUT_GLOW_EMISSION_MAIN`
- Stable Layers: OUT_EMISSION_MASK, OUT_COLOR_BLEED_MASK, OUT_BLOOM_SOURCE, OUT_TRIGGER_METADATA
- Inputs: optional_fx_source, optional_camera, optional_luminance_source
- Passes: emission_mask, color_bleed_mask, bloom_source, alpha_optional, beauty_proxy
- Colorspace: ACEScg source / Rec709 display transform downstream
- Cache Types: bgeo, abc, exr

### HFX_034_ZDepth_Fog_Pass

- Interface: `B05_ZDEPTH_FOG_RENDER_PASS_INTERFACE`
- Family: `ZDEPTH_FOG`
- Main Output: `OUT_ZDEPTH_FOG_MAIN`
- Stable Layers: OUT_ZDEPTH_MASK, OUT_DISTANCE_FOG, OUT_ATMOSPHERE_LAYER, OUT_TRIGGER_METADATA
- Inputs: optional_camera, optional_depth_proxy, optional_scene_bounds
- Passes: zdepth_mask, distance_fog, atmosphere_layer, depth_alpha, fog_density
- Colorspace: linear depth scalar / non-color data
- Cache Types: bgeo, abc, exr

### HFX_035_Distortion_Heat_Shockwave_Mask

- Interface: `B05_DISTORTION_HEAT_RENDER_PASS_INTERFACE`
- Family: `DISTORTION_HEAT_SHOCKWAVE`
- Main Output: `OUT_DISTORTION_MAIN`
- Stable Layers: OUT_HEAT_MASK, OUT_SHOCKWAVE_RING, OUT_REFRACTION_VECTOR_PROXY, OUT_TRIGGER_METADATA
- Inputs: optional_center_point, optional_camera, optional_fx_source
- Passes: heat_mask, shockwave_ring, refraction_vector_proxy, distortion_alpha, falloff_mask
- Colorspace: linear scalar/vector pass / non-color data
- Cache Types: bgeo, abc, exr

### HFX_036_Alpha_Holdout_Matte

- Interface: `B05_ALPHA_HOLDOUT_RENDER_PASS_INTERFACE`
- Family: `ALPHA_HOLDOUT`
- Main Output: `OUT_ALPHA_HOLDOUT_MAIN`
- Stable Layers: OUT_FOREGROUND_MATTE, OUT_OCCLUSION_MATTE, OUT_EDGE_MATTE, OUT_TRIGGER_METADATA
- Inputs: optional_subject_proxy, optional_occluder_proxy, optional_camera
- Passes: foreground_matte, occlusion_matte, edge_matte, holdout_alpha, coverage_mask
- Colorspace: linear matte scalar / non-color data
- Cache Types: bgeo, abc, exr

### HFX_037_LightWrap_Rim_Interaction

- Interface: `B05_LIGHTWRAP_RIM_RENDER_PASS_INTERFACE`
- Family: `LIGHTWRAP_RIM`
- Main Output: `OUT_LIGHTWRAP_MAIN`
- Stable Layers: OUT_RIM_MASK, OUT_EDGE_SPILL, OUT_BACKLIGHT_INTERACTION, OUT_TRIGGER_METADATA
- Inputs: optional_subject_proxy, optional_background_plate, optional_camera
- Passes: rim_mask, edge_spill, backlight_interaction, wrap_alpha, edge_softness
- Colorspace: ACEScg source / comp-managed display
- Cache Types: bgeo, abc, exr

### HFX_038_ContactShadow_Ground_Integration

- Interface: `B05_CONTACT_SHADOW_RENDER_PASS_INTERFACE`
- Family: `CONTACT_SHADOW_GROUND`
- Main Output: `OUT_CONTACT_SHADOW_MAIN`
- Stable Layers: OUT_GROUND_MATTE, OUT_FOOT_CONTACT, OUT_FX_CONTACT_MASK, OUT_TRIGGER_METADATA
- Inputs: optional_ground_plane, optional_subject_proxy, optional_fx_source
- Passes: ground_matte, foot_contact, fx_contact_mask, contact_shadow, falloff_mask
- Colorspace: linear matte scalar / non-color data
- Cache Types: bgeo, abc, exr

### HFX_039_LensDirt_BloomStreak_Proxy

- Interface: `B05_LENS_DIRT_BLOOM_RENDER_PASS_INTERFACE`
- Family: `LENS_DIRT_BLOOM`
- Main Output: `OUT_LENS_DIRT_MAIN`
- Stable Layers: OUT_BLOOM_STREAK, OUT_DIRT_MASK, OUT_FLARE_RESPONSE, OUT_TRIGGER_METADATA
- Inputs: optional_luminance_source, optional_camera, optional_lens_profile
- Passes: bloom_streak, dirt_mask, flare_response, threshold_mask, lens_alpha
- Colorspace: ACEScg source / comp-managed display
- Cache Types: bgeo, abc, exr

### HFX_040_Unreal_DaVinci_AE_Handoff_Template

- Interface: `B05_UNREAL_DAVINCI_AE_HANDOFF_INTERFACE`
- Family: `HANDOFF_TEMPLATE`
- Main Output: `OUT_HANDOFF_PACKAGE_MAIN`
- Stable Layers: OUT_PASS_MANIFEST, OUT_NAMING_POLICY, OUT_DELIVERY_CHECKLIST, OUT_TRIGGER_METADATA
- Inputs: optional_shot_manifest, optional_camera, optional_render_layer_manifest
- Passes: pass_manifest, naming_policy, delivery_checklist, colorspace_policy, frame_range_policy
- Colorspace: explicit per-shot policy required
- Cache Types: bgeo, abc, exr, json

