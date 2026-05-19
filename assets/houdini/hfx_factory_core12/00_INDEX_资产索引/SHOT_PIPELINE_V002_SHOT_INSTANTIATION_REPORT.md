# SHOT Pipeline v002 Shot Instantiation Report

Generated: 2026-05-18T00:02:18

Status: SHOT_INSTANTIATION_RUNNING

## Previous Stage Checks

- PASS: SHOT_PIPELINE_V001_REAL_SHOT_BINDING_REPORT.md marker found

## Template Checks

- PASS: template root exists: `200_SHOTS/SHOT_TEMPLATE_V001_REAL_SHOT_BINDING`
- PASS: template file exists: `shot_manifest_v001.json`
- PASS: template file exists: `00_plate/PLATE_BINDING_v001.json`
- PASS: template file exists: `01_camera/CAMERA_BINDING_v001.json`
- PASS: template file exists: `02_unreal/UNREAL_BINDING_v001.json`
- PASS: template file exists: `03_houdini/HFX_ASSET_SELECTION_v001.json`
- PASS: template file exists: `05_comp/COMP_PASS_MAP_v001.json`
- PASS: template file exists: `06_delivery/SHOT_HANDOFF_MANIFEST_v001.json`
- PASS: template file exists: `07_validation/SHOT_VALIDATION_CHECKLIST_v001.md`
- PASS: template file exists: `README_SHOT_TEMPLATE_V001.md`

## Shot Template Copy

- PASS: copied template to `200_SHOTS/SHOT_001_TEST_REAL_FX_BINDING`

## Shot V002 Required File Checks

- PASS: `200_SHOTS/SHOT_001_TEST_REAL_FX_BINDING/shot_manifest_v002.json`
- PASS: `200_SHOTS/SHOT_001_TEST_REAL_FX_BINDING/00_plate/PLATE_BINDING_v002.json`
- PASS: `200_SHOTS/SHOT_001_TEST_REAL_FX_BINDING/01_camera/CAMERA_BINDING_v002.json`
- PASS: `200_SHOTS/SHOT_001_TEST_REAL_FX_BINDING/02_unreal/UNREAL_BINDING_v002.json`
- PASS: `200_SHOTS/SHOT_001_TEST_REAL_FX_BINDING/03_houdini/HFX_ASSET_SELECTION_v002.json`
- PASS: `200_SHOTS/SHOT_001_TEST_REAL_FX_BINDING/05_comp/COMP_PASS_MAP_v002.json`
- PASS: `200_SHOTS/SHOT_001_TEST_REAL_FX_BINDING/06_delivery/SHOT_HANDOFF_MANIFEST_v002.json`
- PASS: `200_SHOTS/SHOT_001_TEST_REAL_FX_BINDING/07_validation/SHOT_VALIDATION_CHECKLIST_v002.md`
- PASS: `200_SHOTS/SHOT_001_TEST_REAL_FX_BINDING/README_SHOT_001_TEST_REAL_FX_BINDING.md`

## Shot Directory Checks

- PASS: dir `200_SHOTS/SHOT_001_TEST_REAL_FX_BINDING/00_plate`
- PASS: dir `200_SHOTS/SHOT_001_TEST_REAL_FX_BINDING/01_camera`
- PASS: dir `200_SHOTS/SHOT_001_TEST_REAL_FX_BINDING/02_unreal`
- PASS: dir `200_SHOTS/SHOT_001_TEST_REAL_FX_BINDING/03_houdini`
- PASS: dir `200_SHOTS/SHOT_001_TEST_REAL_FX_BINDING/03_houdini/hero_hip`
- PASS: dir `200_SHOTS/SHOT_001_TEST_REAL_FX_BINDING/03_houdini/cache`
- PASS: dir `200_SHOTS/SHOT_001_TEST_REAL_FX_BINDING/03_houdini/cache/bgeo`
- PASS: dir `200_SHOTS/SHOT_001_TEST_REAL_FX_BINDING/03_houdini/cache/vdb`
- PASS: dir `200_SHOTS/SHOT_001_TEST_REAL_FX_BINDING/03_houdini/cache/abc`
- PASS: dir `200_SHOTS/SHOT_001_TEST_REAL_FX_BINDING/04_render`
- PASS: dir `200_SHOTS/SHOT_001_TEST_REAL_FX_BINDING/04_render/exr`
- PASS: dir `200_SHOTS/SHOT_001_TEST_REAL_FX_BINDING/04_render/preview`
- PASS: dir `200_SHOTS/SHOT_001_TEST_REAL_FX_BINDING/05_comp`
- PASS: dir `200_SHOTS/SHOT_001_TEST_REAL_FX_BINDING/05_comp/ae`
- PASS: dir `200_SHOTS/SHOT_001_TEST_REAL_FX_BINDING/05_comp/davinci`
- PASS: dir `200_SHOTS/SHOT_001_TEST_REAL_FX_BINDING/05_comp/comfyui_post`
- PASS: dir `200_SHOTS/SHOT_001_TEST_REAL_FX_BINDING/06_delivery`
- PASS: dir `200_SHOTS/SHOT_001_TEST_REAL_FX_BINDING/07_validation`
- PASS: dir `200_SHOTS/SHOT_001_TEST_REAL_FX_BINDING/08_notes`

## Policy Checks

- PASS: shot_id
- PASS: take_id
- PASS: render_blocked
- PASS: sealed_assets_immutable
- PASS: selected_hfx_assets_non_empty

## Pollution Check

Result: PASS
No video/archive/macOS metadata pollution found in shot package.

## Summary

- Shot ID: SHOT_001_TEST_REAL_FX_BINDING
- Take ID: TAKE_A
- Shot Root: `200_SHOTS/SHOT_001_TEST_REAL_FX_BINDING`
- Selected HFX Assets: 7
- Render/export: blocked
- Real plate/camera: unbound
- Final sealed assets: immutable

---

Final Status: SHOT_PIPELINE_V002_SHOT_INSTANTIATION_PASS
