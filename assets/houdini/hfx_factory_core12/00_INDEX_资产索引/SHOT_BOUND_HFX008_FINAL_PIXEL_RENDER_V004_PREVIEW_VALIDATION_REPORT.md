# SHOT_BOUND_HFX008_FINAL_PIXEL_RENDER_V004 Preview Validation Report

Generated: 2026-05-19T16:49:41

Status: SHOT_BOUND_PREVIEW_VALIDATION_RUNNING

## Previous Stage Checks

- PASS: SHOT_BOUND_HFX008_FINAL_PIXEL_RENDER_V001
- PASS: SHOT_BOUND_HFX008_FINAL_PIXEL_RENDER_V002_PREFLIGHT
- PASS: SHOT_BOUND_HFX008_FINAL_PIXEL_RENDER_V003_CONTROLLED_PREVIEW_RENDER

## Input File Checks / Copy

- PASS: copied V003 controlled preview HIP -> `400_SHOT_BOUND_FINAL_PIXEL/HFX008_SHOT001_V004_PREVIEW_VALIDATION/00_inputs/SHOT_001_HFX008_CONTROLLED_PREVIEW_RENDER_v003.hip`
- PASS: copied V003 main manifest -> `400_SHOT_BOUND_FINAL_PIXEL/HFX008_SHOT001_V004_PREVIEW_VALIDATION/00_inputs/SHOT_BOUND_HFX008_FINAL_PIXEL_RENDER_V003_CONTROLLED_PREVIEW_RENDER_MANIFEST.json`
- PASS: copied V003 preview output manifest -> `400_SHOT_BOUND_FINAL_PIXEL/HFX008_SHOT001_V004_PREVIEW_VALIDATION/00_inputs/SHOT_001_HFX008_PREVIEW_OUTPUT_MANIFEST_v003.json`
- PASS: copied V003 preview frame manifest -> `400_SHOT_BOUND_FINAL_PIXEL/HFX008_SHOT001_V004_PREVIEW_VALIDATION/00_inputs/SHOT_001_HFX008_PREVIEW_FRAME_MANIFEST_v003.json`
- PASS: copied V003 validation JSON -> `400_SHOT_BOUND_FINAL_PIXEL/HFX008_SHOT001_V004_PREVIEW_VALIDATION/00_inputs/SHOT_001_HFX008_CONTROLLED_PREVIEW_RENDER_VALIDATION_v003.json`
- PASS: copied V003 validation MD -> `400_SHOT_BOUND_FINAL_PIXEL/HFX008_SHOT001_V004_PREVIEW_VALIDATION/00_inputs/SHOT_001_HFX008_CONTROLLED_PREVIEW_RENDER_VALIDATION_v003.md`
- PASS: copied V003 readme -> `400_SHOT_BOUND_FINAL_PIXEL/HFX008_SHOT001_V004_PREVIEW_VALIDATION/00_inputs/README_SHOT_001_HFX008_CONTROLLED_PREVIEW_RENDER_v003.md`

## V003 Policy Checks

- PASS: v003_status_pass
- PASS: shot_id_correct
- PASS: take_id_correct
- PASS: asset_id_correct
- PASS: v003_validation_ready
- PASS: controlled_preview_completed
- PASS: production_exr_rendered_false
- PASS: final_render_allowed_false
- PASS: delivery_allowed_false
- PASS: hollywood_final_pixel_claim_allowed_false
- PASS: output_manifest_ready
- PASS: frame_manifest_ready
- PASS: placeholder_count_42
- PASS: frame_count_6
- PASS: outputs_per_frame_7
- PASS: total_placeholder_outputs_42

## Preview Placeholder Completeness Checks

- PASS: frame 0001 `preview_beauty_proxy`
- PASS: frame 0001 `preview_emission_mask`
- PASS: frame 0001 `preview_distortion_proxy`
- PASS: frame 0001 `preview_dust_contact`
- PASS: frame 0001 `preview_zdepth_falloff`
- PASS: frame 0001 `preview_contact_shadow`
- PASS: frame 0001 `preview_metadata`
- PASS: frame 0012 `preview_beauty_proxy`
- PASS: frame 0012 `preview_emission_mask`
- PASS: frame 0012 `preview_distortion_proxy`
- PASS: frame 0012 `preview_dust_contact`
- PASS: frame 0012 `preview_zdepth_falloff`
- PASS: frame 0012 `preview_contact_shadow`
- PASS: frame 0012 `preview_metadata`
- PASS: frame 0024 `preview_beauty_proxy`
- PASS: frame 0024 `preview_emission_mask`
- PASS: frame 0024 `preview_distortion_proxy`
- PASS: frame 0024 `preview_dust_contact`
- PASS: frame 0024 `preview_zdepth_falloff`
- PASS: frame 0024 `preview_contact_shadow`
- PASS: frame 0024 `preview_metadata`
- PASS: frame 0048 `preview_beauty_proxy`
- PASS: frame 0048 `preview_emission_mask`
- PASS: frame 0048 `preview_distortion_proxy`
- PASS: frame 0048 `preview_dust_contact`
- PASS: frame 0048 `preview_zdepth_falloff`
- PASS: frame 0048 `preview_contact_shadow`
- PASS: frame 0048 `preview_metadata`
- PASS: frame 0072 `preview_beauty_proxy`
- PASS: frame 0072 `preview_emission_mask`
- PASS: frame 0072 `preview_distortion_proxy`
- PASS: frame 0072 `preview_dust_contact`
- PASS: frame 0072 `preview_zdepth_falloff`
- PASS: frame 0072 `preview_contact_shadow`
- PASS: frame 0072 `preview_metadata`
- PASS: frame 0120 `preview_beauty_proxy`
- PASS: frame 0120 `preview_emission_mask`
- PASS: frame 0120 `preview_distortion_proxy`
- PASS: frame 0120 `preview_dust_contact`
- PASS: frame 0120 `preview_zdepth_falloff`
- PASS: frame 0120 `preview_contact_shadow`
- PASS: frame 0120 `preview_metadata`

## Frame Matrix Checks

- PASS: frame 0001 has all 7 preview outputs
- PASS: frame 0012 has all 7 preview outputs
- PASS: frame 0024 has all 7 preview outputs
- PASS: frame 0048 has all 7 preview outputs
- PASS: frame 0072 has all 7 preview outputs
- PASS: frame 0120 has all 7 preview outputs

## Generated File Checks

- PASS: `400_SHOT_BOUND_FINAL_PIXEL/HFX008_SHOT001_V004_PREVIEW_VALIDATION/01_validation/SHOT_001_HFX008_PREVIEW_VALIDATION_v004.json`
- PASS: `400_SHOT_BOUND_FINAL_PIXEL/HFX008_SHOT001_V004_PREVIEW_VALIDATION/01_validation/SHOT_001_HFX008_PREVIEW_VALIDATION_v004.md`
- PASS: `400_SHOT_BOUND_FINAL_PIXEL/HFX008_SHOT001_V004_PREVIEW_VALIDATION/03_docs/README_SHOT_001_HFX008_PREVIEW_VALIDATION_v004.md`

## Pollution Check

Result: PASS
No video/archive/macOS metadata pollution found in V004 preview validation package.

## Summary

- Shot: SHOT_001_TEST_REAL_FX_BINDING
- Asset: HFX_008 Energy Shockwave
- Preview validation: PASS
- Expected placeholder outputs: 42
- Actual pass placeholder outputs: 42
- Production EXR render: blocked
- Final delivery: blocked
- Hollywood final-pixel claim: blocked
- Next: SHOT_BOUND_HFX008_FINAL_PIXEL_RENDER_V005_SYNTHETIC_FINAL_CONTEXT_DECISION

---

Final Status: SHOT_BOUND_HFX008_FINAL_PIXEL_RENDER_V004_PREVIEW_VALIDATION_PASS
