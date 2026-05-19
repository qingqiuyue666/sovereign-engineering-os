# HFX Production Upgrade v005 HFX_008 MID Tier Build Report

Generated: 2026-05-18T22:53:42

Status: HFX_008_MID_TIER_BUILD_RUNNING

## Previous Stage Checks

- PASS: HFX Production Upgrade v001
- PASS: HFX_008 Source Resolution v002
- PASS: HFX_008 Preview Tier Build v003
- PASS: HFX_008 Preview Tier Validation v004

## Source Checks

- PASS: source HDA exists `300_PRODUCTION_UPGRADE/HFX_008_ENERGY_SHOCKWAVE/00_source/qqy_hfx_energy_shockwave_v009C.hda`
- PASS: preview HIP exists `300_PRODUCTION_UPGRADE/HFX_008_ENERGY_SHOCKWAVE/01_preview/hip/HFX_008_ENERGY_SHOCKWAVE_PREVIEW_TIER_v003.hip`

## MID HIP Build

- PASS: source HDA installed
- PASS: resolved HDA type `qqy::hfx_energy_shockwave::9.0`
- PASS: HFX_008_MID_SHOCKWAVE_CORE_v005 cook passed frames [1, 12, 24, 48, 72, 120]
- PASS: HFX_008_MID_SUPPORT_PASSES_v005 cook passed frames [1, 12, 24, 48, 72, 120]
- PASS: HFX_008_MID_EMISSION_MASK_PROXY_v005 cook passed frames [1, 12, 24, 48, 72, 120]
- PASS: HFX_008_MID_DISTORTION_MASK_PROXY_v005 cook passed frames [1, 12, 24, 48, 72, 120]
- PASS: HFX_008_MID_ZDEPTH_PROXY_v005 cook passed frames [1, 12, 24, 48, 72, 120]
- PASS: MID HIP saved `300_PRODUCTION_UPGRADE/HFX_008_ENERGY_SHOCKWAVE/02_mid/hip/HFX_008_ENERGY_SHOCKWAVE_MID_TIER_v005.hip`

## Generated File Checks

- PASS: `300_PRODUCTION_UPGRADE/HFX_008_ENERGY_SHOCKWAVE/02_mid/manifests/HFX_008_MID_TIER_SPEC_v005.json`
- PASS: `300_PRODUCTION_UPGRADE/HFX_008_ENERGY_SHOCKWAVE/02_mid/docs/HFX_008_MID_TIER_SPEC_v005.md`
- PASS: `300_PRODUCTION_UPGRADE/HFX_008_ENERGY_SHOCKWAVE/02_mid/validation/HFX_008_MID_TIER_BUILD_VALIDATION_v005.md`
- PASS: `300_PRODUCTION_UPGRADE/HFX_008_ENERGY_SHOCKWAVE/02_mid/docs/README_HFX_008_MID_TIER_v005.md`

## Pollution Check

Result: PASS
No video/archive/macOS metadata pollution found in MID tier workspace.

## Summary

- Asset: HFX_008 Energy Shockwave
- Tier: MID
- Quality Claim: MID_LOOKDEV_ONLY
- MID HIP created: true
- Render/export: blocked
- Delivery: blocked
- Next: HFX_PRODUCTION_UPGRADE_V006_HFX008_MID_TIER_VALIDATION

---

Final Status: HFX_PRODUCTION_UPGRADE_V005_HFX008_MID_TIER_BUILD_PASS
