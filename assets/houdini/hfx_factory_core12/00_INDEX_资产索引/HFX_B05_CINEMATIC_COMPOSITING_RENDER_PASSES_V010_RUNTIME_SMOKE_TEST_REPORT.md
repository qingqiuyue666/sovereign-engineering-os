# HFX Batch 05 Cinematic Compositing Render Passes v010 Runtime Smoke Test Report

Generated: 2026-05-17T23:20:44

Status: RUNTIME_SMOKE_TEST_RUNNING

Policy:
- Runtime smoke tests preview/proxy HDA behavior only.
- Real EXR render/export remains blocked.
- Cache/export execution remains blocked.
- EXR pass separation remains required.
- Comp pass flattening remains forbidden.
- Geometry is resolved through display/render/internal SOP nodes.

## Previous Stage Checks

- PASS: HFX_B05_CINEMATIC_COMPOSITING_RENDER_PASSES_V001_VALIDATION_REPORT.md marker found
- PASS: HFX_B05_CINEMATIC_COMPOSITING_RENDER_PASSES_V002_HIP_TEMPLATE_VALIDATION_REPORT.md marker found
- PASS: HFX_B05_CINEMATIC_COMPOSITING_RENDER_PASSES_V003_TRIGGER_ANIMATION_VALIDATION_REPORT.md marker found
- PASS: HFX_B05_CINEMATIC_COMPOSITING_RENDER_PASSES_V004_PRODUCTION_SPEC_VALIDATION_REPORT.md marker found
- PASS: HFX_B05_CINEMATIC_COMPOSITING_RENDER_PASSES_V005_RENDER_PASS_INTERFACE_SPEC_VALIDATION_REPORT.md marker found
- PASS: HFX_B05_CINEMATIC_COMPOSITING_RENDER_PASSES_V006_WRAPPER_SPEC_VALIDATION_REPORT.md marker found
- PASS: HFX_B05_CINEMATIC_COMPOSITING_RENDER_PASSES_V007_HDA_PACKAGING_PREFLIGHT_VALIDATION_REPORT.md marker found
- PASS: HFX_B05_CINEMATIC_COMPOSITING_RENDER_PASSES_V008_HDA_PACKAGE_BUILD_VALIDATION_REPORT.md marker found
- PASS: HFX_B05_CINEMATIC_COMPOSITING_RENDER_PASSES_V009_HDA_INSTALL_VALIDATION_REPORT.md marker found

## Runtime Smoke Tests

- PASS: /obj exists
### HFX_033_Glow_Emission_Pass

- PASS: HDA file exists: `26_发光通道_能量Emission/HFX_033_Glow_Emission_Pass/03_hda/qqy_hfx_glow_emission_pass_b05_v008.hda`
- PASS: v009 install_validated true
- PASS: preview enabled / render export blocked preserved
- PASS: cache blocked / comp flatten forbidden / EXR separation preserved
- PASS: OUT_TRIGGER_METADATA preserved
- PASS: HDA type installed: `qqy::hfx_glow_emission_pass::5.0`
- PASS: instance created: `/obj/SMOKE_HFX_033_Glow_Emission_Pass_v010`
- PASS: frame 1 cook ok | sop=/obj/SMOKE_HFX_033_Glow_Emission_Pass_v010/OUT_GLOW_EMISSION_MAIN points=512 prims=0 vertices=None
- PASS: frame 12 cook ok | sop=/obj/SMOKE_HFX_033_Glow_Emission_Pass_v010/OUT_GLOW_EMISSION_MAIN points=512 prims=0 vertices=None
- PASS: frame 24 cook ok | sop=/obj/SMOKE_HFX_033_Glow_Emission_Pass_v010/OUT_GLOW_EMISSION_MAIN points=512 prims=0 vertices=None
- PASS: frame 48 cook ok | sop=/obj/SMOKE_HFX_033_Glow_Emission_Pass_v010/OUT_GLOW_EMISSION_MAIN points=512 prims=0 vertices=None
- PASS: frame 72 cook ok | sop=/obj/SMOKE_HFX_033_Glow_Emission_Pass_v010/OUT_GLOW_EMISSION_MAIN points=512 prims=0 vertices=None
- PASS: frame 120 cook ok | sop=/obj/SMOKE_HFX_033_Glow_Emission_Pass_v010/OUT_GLOW_EMISSION_MAIN points=512 prims=0 vertices=None
- Result: PASS

### HFX_034_ZDepth_Fog_Pass

- PASS: HDA file exists: `27_深度雾_ZDepth/HFX_034_ZDepth_Fog_Pass/03_hda/qqy_hfx_zdepth_fog_pass_b05_v008.hda`
- PASS: v009 install_validated true
- PASS: preview enabled / render export blocked preserved
- PASS: cache blocked / comp flatten forbidden / EXR separation preserved
- PASS: OUT_TRIGGER_METADATA preserved
- PASS: HDA type installed: `qqy::hfx_zdepth_fog_pass::5.0`
- PASS: instance created: `/obj/SMOKE_HFX_034_ZDepth_Fog_Pass_v010`
- PASS: frame 1 cook ok | sop=/obj/SMOKE_HFX_034_ZDepth_Fog_Pass_v010/OUT_ZDEPTH_FOG_MAIN points=512 prims=0 vertices=None
- PASS: frame 12 cook ok | sop=/obj/SMOKE_HFX_034_ZDepth_Fog_Pass_v010/OUT_ZDEPTH_FOG_MAIN points=512 prims=0 vertices=None
- PASS: frame 24 cook ok | sop=/obj/SMOKE_HFX_034_ZDepth_Fog_Pass_v010/OUT_ZDEPTH_FOG_MAIN points=512 prims=0 vertices=None
- PASS: frame 48 cook ok | sop=/obj/SMOKE_HFX_034_ZDepth_Fog_Pass_v010/OUT_ZDEPTH_FOG_MAIN points=512 prims=0 vertices=None
- PASS: frame 72 cook ok | sop=/obj/SMOKE_HFX_034_ZDepth_Fog_Pass_v010/OUT_ZDEPTH_FOG_MAIN points=512 prims=0 vertices=None
- PASS: frame 120 cook ok | sop=/obj/SMOKE_HFX_034_ZDepth_Fog_Pass_v010/OUT_ZDEPTH_FOG_MAIN points=512 prims=0 vertices=None
- Result: PASS

### HFX_035_Distortion_Heat_Shockwave_Mask

- PASS: HDA file exists: `28_热浪扭曲_冲击波Mask/HFX_035_Distortion_Heat_Shockwave_Mask/03_hda/qqy_hfx_distortion_heat_shockwave_mask_b05_v008.hda`
- PASS: v009 install_validated true
- PASS: preview enabled / render export blocked preserved
- PASS: cache blocked / comp flatten forbidden / EXR separation preserved
- PASS: OUT_TRIGGER_METADATA preserved
- PASS: HDA type installed: `qqy::hfx_distortion_heat_shockwave_mask::5.0`
- PASS: instance created: `/obj/SMOKE_HFX_035_Distortion_Heat_Shockwave_Mask_v010`
- PASS: frame 1 cook ok | sop=/obj/SMOKE_HFX_035_Distortion_Heat_Shockwave_Mask_v010/OUT_DISTORTION_MAIN points=600 prims=0 vertices=None
- PASS: frame 12 cook ok | sop=/obj/SMOKE_HFX_035_Distortion_Heat_Shockwave_Mask_v010/OUT_DISTORTION_MAIN points=600 prims=0 vertices=None
- PASS: frame 24 cook ok | sop=/obj/SMOKE_HFX_035_Distortion_Heat_Shockwave_Mask_v010/OUT_DISTORTION_MAIN points=600 prims=0 vertices=None
- PASS: frame 48 cook ok | sop=/obj/SMOKE_HFX_035_Distortion_Heat_Shockwave_Mask_v010/OUT_DISTORTION_MAIN points=600 prims=0 vertices=None
- PASS: frame 72 cook ok | sop=/obj/SMOKE_HFX_035_Distortion_Heat_Shockwave_Mask_v010/OUT_DISTORTION_MAIN points=600 prims=0 vertices=None
- PASS: frame 120 cook ok | sop=/obj/SMOKE_HFX_035_Distortion_Heat_Shockwave_Mask_v010/OUT_DISTORTION_MAIN points=600 prims=0 vertices=None
- Result: PASS

### HFX_036_Alpha_Holdout_Matte

- PASS: HDA file exists: `29_Alpha遮挡_HoldoutMatte/HFX_036_Alpha_Holdout_Matte/03_hda/qqy_hfx_alpha_holdout_matte_b05_v008.hda`
- PASS: v009 install_validated true
- PASS: preview enabled / render export blocked preserved
- PASS: cache blocked / comp flatten forbidden / EXR separation preserved
- PASS: OUT_TRIGGER_METADATA preserved
- PASS: HDA type installed: `qqy::hfx_alpha_holdout_matte::5.0`
- PASS: instance created: `/obj/SMOKE_HFX_036_Alpha_Holdout_Matte_v010`
- PASS: frame 1 cook ok | sop=/obj/SMOKE_HFX_036_Alpha_Holdout_Matte_v010/OUT_ALPHA_HOLDOUT_MAIN points=384 prims=0 vertices=None
- PASS: frame 12 cook ok | sop=/obj/SMOKE_HFX_036_Alpha_Holdout_Matte_v010/OUT_ALPHA_HOLDOUT_MAIN points=384 prims=0 vertices=None
- PASS: frame 24 cook ok | sop=/obj/SMOKE_HFX_036_Alpha_Holdout_Matte_v010/OUT_ALPHA_HOLDOUT_MAIN points=384 prims=0 vertices=None
- PASS: frame 48 cook ok | sop=/obj/SMOKE_HFX_036_Alpha_Holdout_Matte_v010/OUT_ALPHA_HOLDOUT_MAIN points=384 prims=0 vertices=None
- PASS: frame 72 cook ok | sop=/obj/SMOKE_HFX_036_Alpha_Holdout_Matte_v010/OUT_ALPHA_HOLDOUT_MAIN points=384 prims=0 vertices=None
- PASS: frame 120 cook ok | sop=/obj/SMOKE_HFX_036_Alpha_Holdout_Matte_v010/OUT_ALPHA_HOLDOUT_MAIN points=384 prims=0 vertices=None
- Result: PASS

### HFX_037_LightWrap_Rim_Interaction

- PASS: HDA file exists: `30_边缘光_LightWrap融合/HFX_037_LightWrap_Rim_Interaction/03_hda/qqy_hfx_lightwrap_rim_interaction_b05_v008.hda`
- PASS: v009 install_validated true
- PASS: preview enabled / render export blocked preserved
- PASS: cache blocked / comp flatten forbidden / EXR separation preserved
- PASS: OUT_TRIGGER_METADATA preserved
- PASS: HDA type installed: `qqy::hfx_lightwrap_rim_interaction::5.0`
- PASS: instance created: `/obj/SMOKE_HFX_037_LightWrap_Rim_Interaction_v010`
- PASS: frame 1 cook ok | sop=/obj/SMOKE_HFX_037_LightWrap_Rim_Interaction_v010/OUT_LIGHTWRAP_MAIN points=420 prims=0 vertices=None
- PASS: frame 12 cook ok | sop=/obj/SMOKE_HFX_037_LightWrap_Rim_Interaction_v010/OUT_LIGHTWRAP_MAIN points=420 prims=0 vertices=None
- PASS: frame 24 cook ok | sop=/obj/SMOKE_HFX_037_LightWrap_Rim_Interaction_v010/OUT_LIGHTWRAP_MAIN points=420 prims=0 vertices=None
- PASS: frame 48 cook ok | sop=/obj/SMOKE_HFX_037_LightWrap_Rim_Interaction_v010/OUT_LIGHTWRAP_MAIN points=420 prims=0 vertices=None
- PASS: frame 72 cook ok | sop=/obj/SMOKE_HFX_037_LightWrap_Rim_Interaction_v010/OUT_LIGHTWRAP_MAIN points=420 prims=0 vertices=None
- PASS: frame 120 cook ok | sop=/obj/SMOKE_HFX_037_LightWrap_Rim_Interaction_v010/OUT_LIGHTWRAP_MAIN points=420 prims=0 vertices=None
- Result: PASS

### HFX_038_ContactShadow_Ground_Integration

- PASS: HDA file exists: `31_接触阴影_地面融合/HFX_038_ContactShadow_Ground_Integration/03_hda/qqy_hfx_contact_shadow_ground_integration_b05_v008.hda`
- PASS: v009 install_validated true
- PASS: preview enabled / render export blocked preserved
- PASS: cache blocked / comp flatten forbidden / EXR separation preserved
- PASS: OUT_TRIGGER_METADATA preserved
- PASS: HDA type installed: `qqy::hfx_contact_shadow_ground_integration::5.0`
- PASS: instance created: `/obj/SMOKE_HFX_038_ContactShadow_Ground_Integration_v010`
- PASS: frame 1 cook ok | sop=/obj/SMOKE_HFX_038_ContactShadow_Ground_Integration_v010/OUT_CONTACT_SHADOW_MAIN points=192 prims=0 vertices=None
- PASS: frame 12 cook ok | sop=/obj/SMOKE_HFX_038_ContactShadow_Ground_Integration_v010/OUT_CONTACT_SHADOW_MAIN points=192 prims=0 vertices=None
- PASS: frame 24 cook ok | sop=/obj/SMOKE_HFX_038_ContactShadow_Ground_Integration_v010/OUT_CONTACT_SHADOW_MAIN points=192 prims=0 vertices=None
- PASS: frame 48 cook ok | sop=/obj/SMOKE_HFX_038_ContactShadow_Ground_Integration_v010/OUT_CONTACT_SHADOW_MAIN points=192 prims=0 vertices=None
- PASS: frame 72 cook ok | sop=/obj/SMOKE_HFX_038_ContactShadow_Ground_Integration_v010/OUT_CONTACT_SHADOW_MAIN points=192 prims=0 vertices=None
- PASS: frame 120 cook ok | sop=/obj/SMOKE_HFX_038_ContactShadow_Ground_Integration_v010/OUT_CONTACT_SHADOW_MAIN points=192 prims=0 vertices=None
- Result: PASS

### HFX_039_LensDirt_BloomStreak_Proxy

- PASS: HDA file exists: `32_镜头脏污_BloomStreak/HFX_039_LensDirt_BloomStreak_Proxy/03_hda/qqy_hfx_lens_dirt_bloom_streak_proxy_b05_v008.hda`
- PASS: v009 install_validated true
- PASS: preview enabled / render export blocked preserved
- PASS: cache blocked / comp flatten forbidden / EXR separation preserved
- PASS: OUT_TRIGGER_METADATA preserved
- PASS: HDA type installed: `qqy::hfx_lens_dirt_bloom_streak_proxy::5.0`
- PASS: instance created: `/obj/SMOKE_HFX_039_LensDirt_BloomStreak_Proxy_v010`
- PASS: frame 1 cook ok | sop=/obj/SMOKE_HFX_039_LensDirt_BloomStreak_Proxy_v010/OUT_LENS_DIRT_MAIN points=192 prims=0 vertices=None
- PASS: frame 12 cook ok | sop=/obj/SMOKE_HFX_039_LensDirt_BloomStreak_Proxy_v010/OUT_LENS_DIRT_MAIN points=192 prims=0 vertices=None
- PASS: frame 24 cook ok | sop=/obj/SMOKE_HFX_039_LensDirt_BloomStreak_Proxy_v010/OUT_LENS_DIRT_MAIN points=192 prims=0 vertices=None
- PASS: frame 48 cook ok | sop=/obj/SMOKE_HFX_039_LensDirt_BloomStreak_Proxy_v010/OUT_LENS_DIRT_MAIN points=192 prims=0 vertices=None
- PASS: frame 72 cook ok | sop=/obj/SMOKE_HFX_039_LensDirt_BloomStreak_Proxy_v010/OUT_LENS_DIRT_MAIN points=192 prims=0 vertices=None
- PASS: frame 120 cook ok | sop=/obj/SMOKE_HFX_039_LensDirt_BloomStreak_Proxy_v010/OUT_LENS_DIRT_MAIN points=192 prims=0 vertices=None
- Result: PASS

### HFX_040_Unreal_DaVinci_AE_Handoff_Template

- PASS: HDA file exists: `33_交付模板_Unreal_DaVinci_AE/HFX_040_Unreal_DaVinci_AE_Handoff_Template/03_hda/qqy_hfx_unreal_davinci_ae_handoff_template_b05_v008.hda`
- PASS: v009 install_validated true
- PASS: preview enabled / render export blocked preserved
- PASS: cache blocked / comp flatten forbidden / EXR separation preserved
- PASS: OUT_TRIGGER_METADATA preserved
- PASS: HDA type installed: `qqy::hfx_unreal_davinci_ae_handoff_template::5.0`
- PASS: instance created: `/obj/SMOKE_HFX_040_Unreal_DaVinci_AE_Handoff_Template_v010`
- PASS: frame 1 cook ok | sop=/obj/SMOKE_HFX_040_Unreal_DaVinci_AE_Handoff_Template_v010/OUT_HANDOFF_PACKAGE_MAIN points=256 prims=0 vertices=None
- PASS: frame 12 cook ok | sop=/obj/SMOKE_HFX_040_Unreal_DaVinci_AE_Handoff_Template_v010/OUT_HANDOFF_PACKAGE_MAIN points=256 prims=0 vertices=None
- PASS: frame 24 cook ok | sop=/obj/SMOKE_HFX_040_Unreal_DaVinci_AE_Handoff_Template_v010/OUT_HANDOFF_PACKAGE_MAIN points=256 prims=0 vertices=None
- PASS: frame 48 cook ok | sop=/obj/SMOKE_HFX_040_Unreal_DaVinci_AE_Handoff_Template_v010/OUT_HANDOFF_PACKAGE_MAIN points=256 prims=0 vertices=None
- PASS: frame 72 cook ok | sop=/obj/SMOKE_HFX_040_Unreal_DaVinci_AE_Handoff_Template_v010/OUT_HANDOFF_PACKAGE_MAIN points=256 prims=0 vertices=None
- PASS: frame 120 cook ok | sop=/obj/SMOKE_HFX_040_Unreal_DaVinci_AE_Handoff_Template_v010/OUT_HANDOFF_PACKAGE_MAIN points=256 prims=0 vertices=None
- Result: PASS

## Pollution Check

Result: PASS
No video/archive/macOS metadata pollution found.

---

Final Status: HFX_B05_CINEMATIC_COMPOSITING_RENDER_PASSES_V010_RUNTIME_SMOKE_TEST_PASS
