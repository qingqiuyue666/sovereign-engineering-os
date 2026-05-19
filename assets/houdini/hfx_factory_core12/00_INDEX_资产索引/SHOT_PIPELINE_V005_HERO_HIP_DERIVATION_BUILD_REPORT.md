# SHOT Pipeline v005 Hero HIP Derivation Build Report

Generated: 2026-05-18T14:39:20

Status: HERO_HIP_DERIVATION_BUILD_RUNNING

## Previous Stage Checks

- PASS: SHOT_PIPELINE_V001_REAL_SHOT_BINDING_REPORT.md marker found
- PASS: SHOT_PIPELINE_V002_SHOT_INSTANTIATION_REPORT.md marker found
- PASS: SHOT_PIPELINE_V003_SYNTHETIC_PLATE_CAMERA_BINDING_REPORT.md marker found
- PASS: SHOT_PIPELINE_V004_HERO_HIP_DERIVATION_PREFLIGHT_REPORT.md marker found
- PASS: v004 hero_hip_derivation_allowed true
- PASS: render/export and delivery remain blocked

## HDA Source Checks

- PASS: HFX_008 HDA exists: `100_RELEASE/HFX_V013_FINAL_SEAL/release_package/hda/qqy_hfx_energy_shockwave_v009C.hda`
- PASS: HFX_033 HDA exists: `100_RELEASE/HFX_B05_V012_FINAL_SEAL/release_package/hda/qqy_hfx_glow_emission_pass_b05_v008.hda`
- PASS: HFX_034 HDA exists: `100_RELEASE/HFX_B05_V012_FINAL_SEAL/release_package/hda/qqy_hfx_zdepth_fog_pass_b05_v008.hda`
- PASS: HFX_036 HDA exists: `100_RELEASE/HFX_B05_V012_FINAL_SEAL/release_package/hda/qqy_hfx_alpha_holdout_matte_b05_v008.hda`
- PASS: HFX_037 HDA exists: `100_RELEASE/HFX_B05_V012_FINAL_SEAL/release_package/hda/qqy_hfx_lightwrap_rim_interaction_b05_v008.hda`
- PASS: HFX_038 HDA exists: `100_RELEASE/HFX_B05_V012_FINAL_SEAL/release_package/hda/qqy_hfx_contact_shadow_ground_integration_b05_v008.hda`
- PASS: HFX_040 HDA exists: `100_RELEASE/HFX_B05_V012_FINAL_SEAL/release_package/hda/qqy_hfx_unreal_davinci_ae_handoff_template_b05_v008.hda`

### HFX_008 Energy Shockwave

- PASS: node created `/obj/SHOT_HFX_008_ENERGY_SHOCKWAVE`
- PASS: hda_type `qqy::hfx_energy_shockwave::9.0`
- PASS: cook no errors

### HFX_033 Glow Emission Pass

- PASS: node created `/obj/SHOT_HFX_033_GLOW_EMISSION_PASS`
- PASS: hda_type `qqy::hfx_glow_emission_pass::5.0`
- PASS: cook no errors

### HFX_034 ZDepth Fog Pass

- PASS: node created `/obj/SHOT_HFX_034_ZDEPTH_FOG_PASS`
- PASS: hda_type `qqy::hfx_zdepth_fog_pass::5.0`
- PASS: cook no errors

### HFX_036 Alpha Holdout Matte

- PASS: node created `/obj/SHOT_HFX_036_ALPHA_HOLDOUT_MATTE`
- PASS: hda_type `qqy::hfx_alpha_holdout_matte::5.0`
- PASS: cook no errors

### HFX_037 LightWrap Rim Interaction

- PASS: node created `/obj/SHOT_HFX_037_LIGHTWRAP_RIM`
- PASS: hda_type `qqy::hfx_lightwrap_rim_interaction::5.0`
- PASS: cook no errors

### HFX_038 ContactShadow Ground Integration

- PASS: node created `/obj/SHOT_HFX_038_CONTACT_SHADOW`
- PASS: hda_type `qqy::hfx_contact_shadow_ground_integration::5.0`
- PASS: cook no errors

### HFX_040 Unreal DaVinci AE Handoff Template

- PASS: node created `/obj/SHOT_HFX_040_HANDOFF_TEMPLATE`
- PASS: hda_type `qqy::hfx_unreal_davinci_ae_handoff_template::5.0`
- PASS: cook no errors

## Hero HIP Save

- PASS: hero HIP saved `200_SHOTS/SHOT_001_TEST_REAL_FX_BINDING/03_houdini/hero_hip/SHOT_001_TEST_REAL_FX_BINDING_TAKE_A_hero_v005.hip`

## Multi-frame Hero HIP Reopen / Cook Validation

- PASS: HFX_008 multi-frame cook [1, 12, 24, 48, 72, 120]
- PASS: HFX_033 multi-frame cook [1, 12, 24, 48, 72, 120]
- PASS: HFX_034 multi-frame cook [1, 12, 24, 48, 72, 120]
- PASS: HFX_036 multi-frame cook [1, 12, 24, 48, 72, 120]
- PASS: HFX_037 multi-frame cook [1, 12, 24, 48, 72, 120]
- PASS: HFX_038 multi-frame cook [1, 12, 24, 48, 72, 120]
- PASS: HFX_040 multi-frame cook [1, 12, 24, 48, 72, 120]

## V005 Generated File Checks

- PASS: `200_SHOTS/SHOT_001_TEST_REAL_FX_BINDING/03_houdini/HERO_HIP_DERIVATION_BUILD_v005.json`
- PASS: `200_SHOTS/SHOT_001_TEST_REAL_FX_BINDING/03_houdini/HERO_HIP_DERIVATION_BUILD_v005.md`
- PASS: `200_SHOTS/SHOT_001_TEST_REAL_FX_BINDING/07_validation/SHOT_VALIDATION_HERO_HIP_BUILD_v005.md`
- PASS: `200_SHOTS/SHOT_001_TEST_REAL_FX_BINDING/08_notes/README_V005_HERO_HIP_BUILD.md`

## Pollution Check

Result: PASS
No video/archive/macOS metadata pollution found in shot package.

## Summary

- Shot ID: SHOT_001_TEST_REAL_FX_BINDING
- Take ID: TAKE_A
- Hero HIP: `200_SHOTS/SHOT_001_TEST_REAL_FX_BINDING/03_houdini/hero_hip/SHOT_001_TEST_REAL_FX_BINDING_TAKE_A_hero_v005.hip`
- Selected HFX assets: 7
- Render/export: blocked
- Delivery: blocked
- Synthetic binding: pipeline test only

---

Final Status: SHOT_PIPELINE_V005_HERO_HIP_DERIVATION_BUILD_PASS
