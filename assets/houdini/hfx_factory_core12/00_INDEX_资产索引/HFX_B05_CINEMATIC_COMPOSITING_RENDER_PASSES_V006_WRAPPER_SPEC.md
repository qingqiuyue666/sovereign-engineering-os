# HFX Batch 05 Cinematic Compositing Render Passes v006 Wrapper Spec

Status: HFX_B05_CINEMATIC_COMPOSITING_RENDER_PASSES_V006_WRAPPER_SPEC_READY

Purpose:
Define HDA wrapper contracts for Batch 05 render-pass assets before packaging preflight.

Global Rules:
- v006 does not package HDA files.
- Wrapper source is v003 HIP.
- Render-pass interface source is v005.
- Preview mode is default enabled.
- Render/export is default blocked.
- Cache/export execution is default blocked.
- EXR pass separation is mandatory.
- Flattened comp passes are forbidden.
- OUT_TRIGGER_METADATA must remain available.
- Batch 01-04 final sealed releases are immutable.

## Wrapper Targets

### HFX_033_Glow_Emission_Pass

- HDA Type: `qqy::hfx_glow_emission_pass::5.0`
- Wrapper Name: `WRAP_HFX_033_Glow_Emission_Pass_v006`
- Source Geo: `HFX_033_Glow_Emission_Pass_v003`
- Render Pass Interface: `B05_GLOW_EMISSION_RENDER_PASS_INTERFACE`
- Main Output: `OUT_GLOW_EMISSION_MAIN`
- Stable Outputs: OUT_GLOW_EMISSION_MAIN, OUT_EMISSION_MASK, OUT_COLOR_BLEED_MASK, OUT_BLOOM_SOURCE, OUT_TRIGGER_METADATA

### HFX_034_ZDepth_Fog_Pass

- HDA Type: `qqy::hfx_zdepth_fog_pass::5.0`
- Wrapper Name: `WRAP_HFX_034_ZDepth_Fog_Pass_v006`
- Source Geo: `HFX_034_ZDepth_Fog_Pass_v003`
- Render Pass Interface: `B05_ZDEPTH_FOG_RENDER_PASS_INTERFACE`
- Main Output: `OUT_ZDEPTH_FOG_MAIN`
- Stable Outputs: OUT_ZDEPTH_FOG_MAIN, OUT_ZDEPTH_MASK, OUT_DISTANCE_FOG, OUT_ATMOSPHERE_LAYER, OUT_TRIGGER_METADATA

### HFX_035_Distortion_Heat_Shockwave_Mask

- HDA Type: `qqy::hfx_distortion_heat_shockwave_mask::5.0`
- Wrapper Name: `WRAP_HFX_035_Distortion_Heat_Shockwave_Mask_v006`
- Source Geo: `HFX_035_Distortion_Heat_Shockwave_Mask_v003`
- Render Pass Interface: `B05_DISTORTION_HEAT_RENDER_PASS_INTERFACE`
- Main Output: `OUT_DISTORTION_MAIN`
- Stable Outputs: OUT_DISTORTION_MAIN, OUT_HEAT_MASK, OUT_SHOCKWAVE_RING, OUT_REFRACTION_VECTOR_PROXY, OUT_TRIGGER_METADATA

### HFX_036_Alpha_Holdout_Matte

- HDA Type: `qqy::hfx_alpha_holdout_matte::5.0`
- Wrapper Name: `WRAP_HFX_036_Alpha_Holdout_Matte_v006`
- Source Geo: `HFX_036_Alpha_Holdout_Matte_v003`
- Render Pass Interface: `B05_ALPHA_HOLDOUT_RENDER_PASS_INTERFACE`
- Main Output: `OUT_ALPHA_HOLDOUT_MAIN`
- Stable Outputs: OUT_ALPHA_HOLDOUT_MAIN, OUT_FOREGROUND_MATTE, OUT_OCCLUSION_MATTE, OUT_EDGE_MATTE, OUT_TRIGGER_METADATA

### HFX_037_LightWrap_Rim_Interaction

- HDA Type: `qqy::hfx_lightwrap_rim_interaction::5.0`
- Wrapper Name: `WRAP_HFX_037_LightWrap_Rim_Interaction_v006`
- Source Geo: `HFX_037_LightWrap_Rim_Interaction_v003`
- Render Pass Interface: `B05_LIGHTWRAP_RIM_RENDER_PASS_INTERFACE`
- Main Output: `OUT_LIGHTWRAP_MAIN`
- Stable Outputs: OUT_LIGHTWRAP_MAIN, OUT_RIM_MASK, OUT_EDGE_SPILL, OUT_BACKLIGHT_INTERACTION, OUT_TRIGGER_METADATA

### HFX_038_ContactShadow_Ground_Integration

- HDA Type: `qqy::hfx_contact_shadow_ground_integration::5.0`
- Wrapper Name: `WRAP_HFX_038_ContactShadow_Ground_Integration_v006`
- Source Geo: `HFX_038_ContactShadow_Ground_Integration_v003`
- Render Pass Interface: `B05_CONTACT_SHADOW_RENDER_PASS_INTERFACE`
- Main Output: `OUT_CONTACT_SHADOW_MAIN`
- Stable Outputs: OUT_CONTACT_SHADOW_MAIN, OUT_GROUND_MATTE, OUT_FOOT_CONTACT, OUT_FX_CONTACT_MASK, OUT_TRIGGER_METADATA

### HFX_039_LensDirt_BloomStreak_Proxy

- HDA Type: `qqy::hfx_lens_dirt_bloom_streak_proxy::5.0`
- Wrapper Name: `WRAP_HFX_039_LensDirt_BloomStreak_Proxy_v006`
- Source Geo: `HFX_039_LensDirt_BloomStreak_Proxy_v003`
- Render Pass Interface: `B05_LENS_DIRT_BLOOM_RENDER_PASS_INTERFACE`
- Main Output: `OUT_LENS_DIRT_MAIN`
- Stable Outputs: OUT_LENS_DIRT_MAIN, OUT_BLOOM_STREAK, OUT_DIRT_MASK, OUT_FLARE_RESPONSE, OUT_TRIGGER_METADATA

### HFX_040_Unreal_DaVinci_AE_Handoff_Template

- HDA Type: `qqy::hfx_unreal_davinci_ae_handoff_template::5.0`
- Wrapper Name: `WRAP_HFX_040_Unreal_DaVinci_AE_Handoff_Template_v006`
- Source Geo: `HFX_040_Unreal_DaVinci_AE_Handoff_Template_v003`
- Render Pass Interface: `B05_UNREAL_DAVINCI_AE_HANDOFF_INTERFACE`
- Main Output: `OUT_HANDOFF_PACKAGE_MAIN`
- Stable Outputs: OUT_HANDOFF_PACKAGE_MAIN, OUT_PASS_MANIFEST, OUT_NAMING_POLICY, OUT_DELIVERY_CHECKLIST, OUT_TRIGGER_METADATA

