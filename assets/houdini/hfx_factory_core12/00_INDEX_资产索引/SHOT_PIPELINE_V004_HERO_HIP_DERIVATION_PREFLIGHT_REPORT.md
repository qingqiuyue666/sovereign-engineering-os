# SHOT Pipeline v004 Hero HIP Derivation Preflight Report

Generated: 2026-05-18T00:09:47

Status: HERO_HIP_DERIVATION_PREFLIGHT_RUNNING

## Previous Stage Checks

- PASS: SHOT_PIPELINE_V001_REAL_SHOT_BINDING_REPORT.md marker found
- PASS: SHOT_PIPELINE_V002_SHOT_INSTANTIATION_REPORT.md marker found
- PASS: SHOT_PIPELINE_V003_SYNTHETIC_PLATE_CAMERA_BINDING_REPORT.md marker found

## V003 Shot File Checks

- PASS: shot root exists: `200_SHOTS/SHOT_001_TEST_REAL_FX_BINDING`
- PASS: `200_SHOTS/SHOT_001_TEST_REAL_FX_BINDING/shot_manifest_v003.json`
- PASS: `200_SHOTS/SHOT_001_TEST_REAL_FX_BINDING/00_plate/PLATE_BINDING_v003_SYNTHETIC.json`
- PASS: `200_SHOTS/SHOT_001_TEST_REAL_FX_BINDING/01_camera/CAMERA_BINDING_v003_SYNTHETIC.json`
- PASS: `200_SHOTS/SHOT_001_TEST_REAL_FX_BINDING/02_unreal/UNREAL_BINDING_v003.json`
- PASS: `200_SHOTS/SHOT_001_TEST_REAL_FX_BINDING/03_houdini/HFX_ASSET_SELECTION_v003.json`
- PASS: `200_SHOTS/SHOT_001_TEST_REAL_FX_BINDING/05_comp/COMP_PASS_MAP_v003.json`
- PASS: `200_SHOTS/SHOT_001_TEST_REAL_FX_BINDING/06_delivery/SHOT_HANDOFF_MANIFEST_v003.json`
- PASS: `200_SHOTS/SHOT_001_TEST_REAL_FX_BINDING/07_validation/SHOT_VALIDATION_SYNTHETIC_BINDING_v003.md`
- PASS: `200_SHOTS/SHOT_001_TEST_REAL_FX_BINDING/08_notes/README_V003_SYNTHETIC_BINDING.md`
- PASS: writable dir `200_SHOTS/SHOT_001_TEST_REAL_FX_BINDING/03_houdini/hero_hip`
- PASS: writable dir `200_SHOTS/SHOT_001_TEST_REAL_FX_BINDING/03_houdini/cache`
- PASS: writable dir `200_SHOTS/SHOT_001_TEST_REAL_FX_BINDING/04_render`
- PASS: writable dir `200_SHOTS/SHOT_001_TEST_REAL_FX_BINDING/07_validation`
- PASS: writable dir `200_SHOTS/SHOT_001_TEST_REAL_FX_BINDING/08_notes`

## Synthetic Binding Policy Checks

- PASS: shot_id
- PASS: take_id
- PASS: binding_mode_synthetic
- PASS: plate_synthetic
- PASS: camera_synthetic
- PASS: render_blocked
- PASS: delivery_blocked
- PASS: real_world_claim_blocked
- PASS: sealed_assets_immutable
- PASS: selected assets count = 7

## Release Root Checks

- PASS: B01 root `100_RELEASE/HFX_V013_FINAL_SEAL/release_package`
  - PASS: HDA count = 8
  - INFO: legacy B01 hda-only mode accepted; HIP/docs not required
- PASS: B02 root `100_RELEASE/HFX_B02_V013_FINAL_SEAL/release_package`
  - PASS: HDA count = 8
  - PASS: HIP count = 8
  - PASS: docs dir exists
- PASS: B03 root `100_RELEASE/HFX_B03_V013_FINAL_SEAL/release_package`
  - PASS: HDA count = 8
  - PASS: HIP count = 8
  - PASS: docs dir exists
- PASS: B04 root `100_RELEASE/HFX_B04_V013_FINAL_SEAL/release_package`
  - PASS: HDA count = 8
  - PASS: HIP count = 8
  - PASS: docs dir exists
- PASS: B05 root `100_RELEASE/HFX_B05_V012_FINAL_SEAL/release_package`
  - PASS: HDA count = 8
  - PASS: HIP count = 8
  - PASS: docs dir exists

## Selected HFX Asset Source Checks

- PASS: HFX_008 Energy Shockwave HDA candidate found
  - HDA: `100_RELEASE/HFX_V013_FINAL_SEAL/release_package/hda/qqy_hfx_energy_shockwave_v009C.hda`
  - INFO: legacy B01 hda-only asset; HIP candidate not required
- PASS: HFX_033 Glow Emission Pass HDA candidate found
  - HDA: `100_RELEASE/HFX_B05_V012_FINAL_SEAL/release_package/hda/qqy_hfx_glow_emission_pass_b05_v008.hda`
  - PASS: HIP candidate found: `100_RELEASE/HFX_B05_V012_FINAL_SEAL/release_package/hip/HFX_033_Glow_Emission_Pass_v003.hip`
- PASS: HFX_034 ZDepth Fog Pass HDA candidate found
  - HDA: `100_RELEASE/HFX_B05_V012_FINAL_SEAL/release_package/hda/qqy_hfx_glow_emission_pass_b05_v008.hda`
  - PASS: HIP candidate found: `100_RELEASE/HFX_B05_V012_FINAL_SEAL/release_package/hip/HFX_033_Glow_Emission_Pass_v003.hip`
- PASS: HFX_036 Alpha Holdout Matte HDA candidate found
  - HDA: `100_RELEASE/HFX_B05_V012_FINAL_SEAL/release_package/hda/qqy_hfx_alpha_holdout_matte_b05_v008.hda`
  - PASS: HIP candidate found: `100_RELEASE/HFX_B05_V012_FINAL_SEAL/release_package/hip/HFX_036_Alpha_Holdout_Matte_v003.hip`
- PASS: HFX_037 LightWrap Rim Interaction HDA candidate found
  - HDA: `100_RELEASE/HFX_B05_V012_FINAL_SEAL/release_package/hda/qqy_hfx_lightwrap_rim_interaction_b05_v008.hda`
  - PASS: HIP candidate found: `100_RELEASE/HFX_B05_V012_FINAL_SEAL/release_package/hip/HFX_037_LightWrap_Rim_Interaction_v003.hip`
- PASS: HFX_038 ContactShadow Ground Integration HDA candidate found
  - HDA: `100_RELEASE/HFX_B05_V012_FINAL_SEAL/release_package/hda/qqy_hfx_contact_shadow_ground_integration_b05_v008.hda`
  - PASS: HIP candidate found: `100_RELEASE/HFX_B05_V012_FINAL_SEAL/release_package/hip/HFX_038_ContactShadow_Ground_Integration_v003.hip`
- PASS: HFX_040 Unreal DaVinci AE Handoff Template HDA candidate found
  - HDA: `100_RELEASE/HFX_B05_V012_FINAL_SEAL/release_package/hda/qqy_hfx_unreal_davinci_ae_handoff_template_b05_v008.hda`
  - PASS: HIP candidate found: `100_RELEASE/HFX_B05_V012_FINAL_SEAL/release_package/hip/HFX_040_Unreal_DaVinci_AE_Handoff_Template_v003.hip`

## B05 Support Pass Minimum Checks

- PASS: required B05 support pass set present

## V004 Generated File Checks

- PASS: `200_SHOTS/SHOT_001_TEST_REAL_FX_BINDING/03_houdini/HERO_HIP_DERIVATION_PREFLIGHT_v004.json`
- PASS: `200_SHOTS/SHOT_001_TEST_REAL_FX_BINDING/03_houdini/HERO_HIP_DERIVATION_PREFLIGHT_v004.md`
- PASS: `200_SHOTS/SHOT_001_TEST_REAL_FX_BINDING/07_validation/SHOT_VALIDATION_HERO_HIP_PREFLIGHT_v004.md`
- PASS: `200_SHOTS/SHOT_001_TEST_REAL_FX_BINDING/08_notes/README_V004_HERO_HIP_PREFLIGHT.md`

## Pollution Check

Result: PASS
No video/archive/macOS metadata pollution found in shot package.

## Summary

- Shot ID: SHOT_001_TEST_REAL_FX_BINDING
- Take ID: TAKE_A
- Hero HIP derivation: allowed next
- Render/export: blocked
- Delivery: blocked
- Synthetic binding: pipeline test only

---

Final Status: SHOT_PIPELINE_V004_HERO_HIP_DERIVATION_PREFLIGHT_PASS
