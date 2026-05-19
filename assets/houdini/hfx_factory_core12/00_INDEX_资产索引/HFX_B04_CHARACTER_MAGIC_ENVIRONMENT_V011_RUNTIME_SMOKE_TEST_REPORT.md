# HFX Batch 04 Character Magic Environment v011 Runtime Smoke Test Report

Generated: 2026-05-17T19:23:53

Status: RUNTIME_SMOKE_TEST_RUNNING

Policy:
- Runtime smoke tests preview/proxy HDA behavior only.
- Hero stylized network mode remains blocked.
- Cache execution remains blocked.
- Comp pass flattening remains forbidden.
- Geometry is resolved through display/render/internal SOP nodes.

## Previous Stage Checks

- PASS: HFX_B04_CHARACTER_MAGIC_ENVIRONMENT_V001_VALIDATION_REPORT.md marker found
- PASS: HFX_B04_CHARACTER_MAGIC_ENVIRONMENT_V002_HIP_TEMPLATE_VALIDATION_REPORT.md marker found
- PASS: HFX_B04_CHARACTER_MAGIC_ENVIRONMENT_V003_TRIGGER_ANIMATION_VALIDATION_REPORT.md marker found
- PASS: HFX_B04_CHARACTER_MAGIC_ENVIRONMENT_V004_PRODUCTION_SPEC_VALIDATION_REPORT.md marker found
- PASS: HFX_B04_CHARACTER_MAGIC_ENVIRONMENT_V005_HERO_UPGRADE_CANDIDATE_SPEC_VALIDATION_REPORT.md marker found
- PASS: HFX_B04_CHARACTER_MAGIC_ENVIRONMENT_V006_EFFECT_INTERFACE_SPEC_VALIDATION_REPORT.md marker found
- PASS: HFX_B04_CHARACTER_MAGIC_ENVIRONMENT_V007_WRAPPER_SPEC_VALIDATION_REPORT.md marker found
- PASS: HFX_B04_CHARACTER_MAGIC_ENVIRONMENT_V008_HDA_PACKAGING_PREFLIGHT_VALIDATION_REPORT.md marker found
- PASS: HFX_B04_CHARACTER_MAGIC_ENVIRONMENT_V009_HDA_PACKAGE_BUILD_VALIDATION_REPORT.md marker found
- PASS: HFX_B04_CHARACTER_MAGIC_ENVIRONMENT_V010_HDA_INSTALL_VALIDATION_REPORT.md marker found

## Runtime Smoke Tests

- PASS: /obj exists
### HFX_025_Character_Energy_Field

- PASS: HDA file exists: `18_角色能量_周身气场/HFX_025_Character_Energy_Field/03_hda/qqy_hfx_character_energy_field_b04_v009.hda`
- PASS: v010 install_validated true
- PASS: preview enabled / hero blocked preserved
- PASS: cache blocked / comp flatten forbidden preserved
- PASS: OUT_TRIGGER_METADATA preserved
- PASS: HDA type installed: `qqy::hfx_character_energy_field::4.0`
- PASS: instance created: `/obj/SMOKE_HFX_025_Character_Energy_Field_v011`
- PASS: frame 1 cook ok | sop=/obj/SMOKE_HFX_025_Character_Energy_Field_v011/OUT_ENERGY_FIELD_MAIN points=640 prims=0 vertices=None
- PASS: frame 12 cook ok | sop=/obj/SMOKE_HFX_025_Character_Energy_Field_v011/OUT_ENERGY_FIELD_MAIN points=640 prims=0 vertices=None
- PASS: frame 24 cook ok | sop=/obj/SMOKE_HFX_025_Character_Energy_Field_v011/OUT_ENERGY_FIELD_MAIN points=640 prims=0 vertices=None
- PASS: frame 48 cook ok | sop=/obj/SMOKE_HFX_025_Character_Energy_Field_v011/OUT_ENERGY_FIELD_MAIN points=640 prims=0 vertices=None
- PASS: frame 72 cook ok | sop=/obj/SMOKE_HFX_025_Character_Energy_Field_v011/OUT_ENERGY_FIELD_MAIN points=640 prims=0 vertices=None
- PASS: frame 120 cook ok | sop=/obj/SMOKE_HFX_025_Character_Energy_Field_v011/OUT_ENERGY_FIELD_MAIN points=640 prims=0 vertices=None
- Result: PASS

### HFX_026_Ground_Magic_Rune_Circle

- PASS: HDA file exists: `19_魔法阵_地面符文/HFX_026_Ground_Magic_Rune_Circle/03_hda/qqy_hfx_ground_magic_rune_circle_b04_v009.hda`
- PASS: v010 install_validated true
- PASS: preview enabled / hero blocked preserved
- PASS: cache blocked / comp flatten forbidden preserved
- PASS: OUT_TRIGGER_METADATA preserved
- PASS: HDA type installed: `qqy::hfx_ground_magic_rune_circle::4.0`
- PASS: instance created: `/obj/SMOKE_HFX_026_Ground_Magic_Rune_Circle_v011`
- PASS: frame 1 cook ok | sop=/obj/SMOKE_HFX_026_Ground_Magic_Rune_Circle_v011/OUT_RUNE_CIRCLE_MAIN points=256 prims=0 vertices=None
- PASS: frame 12 cook ok | sop=/obj/SMOKE_HFX_026_Ground_Magic_Rune_Circle_v011/OUT_RUNE_CIRCLE_MAIN points=256 prims=0 vertices=None
- PASS: frame 24 cook ok | sop=/obj/SMOKE_HFX_026_Ground_Magic_Rune_Circle_v011/OUT_RUNE_CIRCLE_MAIN points=256 prims=0 vertices=None
- PASS: frame 48 cook ok | sop=/obj/SMOKE_HFX_026_Ground_Magic_Rune_Circle_v011/OUT_RUNE_CIRCLE_MAIN points=256 prims=0 vertices=None
- PASS: frame 72 cook ok | sop=/obj/SMOKE_HFX_026_Ground_Magic_Rune_Circle_v011/OUT_RUNE_CIRCLE_MAIN points=256 prims=0 vertices=None
- PASS: frame 120 cook ok | sop=/obj/SMOKE_HFX_026_Ground_Magic_Rune_Circle_v011/OUT_RUNE_CIRCLE_MAIN points=256 prims=0 vertices=None
- Result: PASS

### HFX_027_Summoning_Portal_Gate

- PASS: HDA file exists: `20_召唤门_传送空间/HFX_027_Summoning_Portal_Gate/03_hda/qqy_hfx_summoning_portal_gate_b04_v009.hda`
- PASS: v010 install_validated true
- PASS: preview enabled / hero blocked preserved
- PASS: cache blocked / comp flatten forbidden preserved
- PASS: OUT_TRIGGER_METADATA preserved
- PASS: HDA type installed: `qqy::hfx_summoning_portal_gate::4.0`
- PASS: instance created: `/obj/SMOKE_HFX_027_Summoning_Portal_Gate_v011`
- PASS: frame 1 cook ok | sop=/obj/SMOKE_HFX_027_Summoning_Portal_Gate_v011/OUT_PORTAL_GATE_MAIN points=760 prims=0 vertices=None
- PASS: frame 12 cook ok | sop=/obj/SMOKE_HFX_027_Summoning_Portal_Gate_v011/OUT_PORTAL_GATE_MAIN points=760 prims=0 vertices=None
- PASS: frame 24 cook ok | sop=/obj/SMOKE_HFX_027_Summoning_Portal_Gate_v011/OUT_PORTAL_GATE_MAIN points=760 prims=0 vertices=None
- PASS: frame 48 cook ok | sop=/obj/SMOKE_HFX_027_Summoning_Portal_Gate_v011/OUT_PORTAL_GATE_MAIN points=760 prims=0 vertices=None
- PASS: frame 72 cook ok | sop=/obj/SMOKE_HFX_027_Summoning_Portal_Gate_v011/OUT_PORTAL_GATE_MAIN points=760 prims=0 vertices=None
- PASS: frame 120 cook ok | sop=/obj/SMOKE_HFX_027_Summoning_Portal_Gate_v011/OUT_PORTAL_GATE_MAIN points=760 prims=0 vertices=None
- Result: PASS

### HFX_028_Space_Rift_Tear

- PASS: HDA file exists: `21_空间裂缝_维度撕裂/HFX_028_Space_Rift_Tear/03_hda/qqy_hfx_space_rift_tear_b04_v009.hda`
- PASS: v010 install_validated true
- PASS: preview enabled / hero blocked preserved
- PASS: cache blocked / comp flatten forbidden preserved
- PASS: OUT_TRIGGER_METADATA preserved
- PASS: HDA type installed: `qqy::hfx_space_rift_tear::4.0`
- PASS: instance created: `/obj/SMOKE_HFX_028_Space_Rift_Tear_v011`
- PASS: frame 1 cook ok | sop=/obj/SMOKE_HFX_028_Space_Rift_Tear_v011/OUT_RIFT_TEAR_MAIN points=192 prims=0 vertices=None
- PASS: frame 12 cook ok | sop=/obj/SMOKE_HFX_028_Space_Rift_Tear_v011/OUT_RIFT_TEAR_MAIN points=192 prims=0 vertices=None
- PASS: frame 24 cook ok | sop=/obj/SMOKE_HFX_028_Space_Rift_Tear_v011/OUT_RIFT_TEAR_MAIN points=192 prims=0 vertices=None
- PASS: frame 48 cook ok | sop=/obj/SMOKE_HFX_028_Space_Rift_Tear_v011/OUT_RIFT_TEAR_MAIN points=192 prims=0 vertices=None
- PASS: frame 72 cook ok | sop=/obj/SMOKE_HFX_028_Space_Rift_Tear_v011/OUT_RIFT_TEAR_MAIN points=192 prims=0 vertices=None
- PASS: frame 120 cook ok | sop=/obj/SMOKE_HFX_028_Space_Rift_Tear_v011/OUT_RIFT_TEAR_MAIN points=192 prims=0 vertices=None
- Result: PASS

### HFX_029_Black_Hole_Accretion_Disk

- PASS: HDA file exists: `22_黑洞吸积盘_引力扭曲/HFX_029_Black_Hole_Accretion_Disk/03_hda/qqy_hfx_black_hole_accretion_disk_b04_v009.hda`
- PASS: v010 install_validated true
- PASS: preview enabled / hero blocked preserved
- PASS: cache blocked / comp flatten forbidden preserved
- PASS: OUT_TRIGGER_METADATA preserved
- PASS: HDA type installed: `qqy::hfx_black_hole_accretion_disk::4.0`
- PASS: instance created: `/obj/SMOKE_HFX_029_Black_Hole_Accretion_Disk_v011`
- PASS: frame 1 cook ok | sop=/obj/SMOKE_HFX_029_Black_Hole_Accretion_Disk_v011/OUT_BLACK_HOLE_MAIN points=900 prims=0 vertices=None
- PASS: frame 12 cook ok | sop=/obj/SMOKE_HFX_029_Black_Hole_Accretion_Disk_v011/OUT_BLACK_HOLE_MAIN points=900 prims=0 vertices=None
- PASS: frame 24 cook ok | sop=/obj/SMOKE_HFX_029_Black_Hole_Accretion_Disk_v011/OUT_BLACK_HOLE_MAIN points=900 prims=0 vertices=None
- PASS: frame 48 cook ok | sop=/obj/SMOKE_HFX_029_Black_Hole_Accretion_Disk_v011/OUT_BLACK_HOLE_MAIN points=900 prims=0 vertices=None
- PASS: frame 72 cook ok | sop=/obj/SMOKE_HFX_029_Black_Hole_Accretion_Disk_v011/OUT_BLACK_HOLE_MAIN points=900 prims=0 vertices=None
- PASS: frame 120 cook ok | sop=/obj/SMOKE_HFX_029_Black_Hole_Accretion_Disk_v011/OUT_BLACK_HOLE_MAIN points=900 prims=0 vertices=None
- Result: PASS

### HFX_030_Ice_Freeze_Spread

- PASS: HDA file exists: `23_冰冻蔓延_霜纹扩散/HFX_030_Ice_Freeze_Spread/03_hda/qqy_hfx_ice_freeze_spread_b04_v009.hda`
- PASS: v010 install_validated true
- PASS: preview enabled / hero blocked preserved
- PASS: cache blocked / comp flatten forbidden preserved
- PASS: OUT_TRIGGER_METADATA preserved
- PASS: HDA type installed: `qqy::hfx_ice_freeze_spread::4.0`
- PASS: instance created: `/obj/SMOKE_HFX_030_Ice_Freeze_Spread_v011`
- PASS: frame 1 cook ok | sop=/obj/SMOKE_HFX_030_Ice_Freeze_Spread_v011/OUT_ICE_SPREAD_MAIN points=224 prims=0 vertices=None
- PASS: frame 12 cook ok | sop=/obj/SMOKE_HFX_030_Ice_Freeze_Spread_v011/OUT_ICE_SPREAD_MAIN points=224 prims=0 vertices=None
- PASS: frame 24 cook ok | sop=/obj/SMOKE_HFX_030_Ice_Freeze_Spread_v011/OUT_ICE_SPREAD_MAIN points=224 prims=0 vertices=None
- PASS: frame 48 cook ok | sop=/obj/SMOKE_HFX_030_Ice_Freeze_Spread_v011/OUT_ICE_SPREAD_MAIN points=224 prims=0 vertices=None
- PASS: frame 72 cook ok | sop=/obj/SMOKE_HFX_030_Ice_Freeze_Spread_v011/OUT_ICE_SPREAD_MAIN points=224 prims=0 vertices=None
- PASS: frame 120 cook ok | sop=/obj/SMOKE_HFX_030_Ice_Freeze_Spread_v011/OUT_ICE_SPREAD_MAIN points=224 prims=0 vertices=None
- Result: PASS

### HFX_031_Ground_Fire_Crawl

- PASS: HDA file exists: `24_地火蔓延_火线扩散/HFX_031_Ground_Fire_Crawl/03_hda/qqy_hfx_ground_fire_crawl_b04_v009.hda`
- PASS: v010 install_validated true
- PASS: preview enabled / hero blocked preserved
- PASS: cache blocked / comp flatten forbidden preserved
- PASS: OUT_TRIGGER_METADATA preserved
- PASS: HDA type installed: `qqy::hfx_ground_fire_crawl::4.0`
- PASS: instance created: `/obj/SMOKE_HFX_031_Ground_Fire_Crawl_v011`
- PASS: frame 1 cook ok | sop=/obj/SMOKE_HFX_031_Ground_Fire_Crawl_v011/OUT_GROUND_FIRE_MAIN points=224 prims=0 vertices=None
- PASS: frame 12 cook ok | sop=/obj/SMOKE_HFX_031_Ground_Fire_Crawl_v011/OUT_GROUND_FIRE_MAIN points=224 prims=0 vertices=None
- PASS: frame 24 cook ok | sop=/obj/SMOKE_HFX_031_Ground_Fire_Crawl_v011/OUT_GROUND_FIRE_MAIN points=224 prims=0 vertices=None
- PASS: frame 48 cook ok | sop=/obj/SMOKE_HFX_031_Ground_Fire_Crawl_v011/OUT_GROUND_FIRE_MAIN points=224 prims=0 vertices=None
- PASS: frame 72 cook ok | sop=/obj/SMOKE_HFX_031_Ground_Fire_Crawl_v011/OUT_GROUND_FIRE_MAIN points=224 prims=0 vertices=None
- PASS: frame 120 cook ok | sop=/obj/SMOKE_HFX_031_Ground_Fire_Crawl_v011/OUT_GROUND_FIRE_MAIN points=224 prims=0 vertices=None
- Result: PASS

### HFX_032_EMP_Scan_Wave

- PASS: HDA file exists: `25_电磁脉冲_扫描波/HFX_032_EMP_Scan_Wave/03_hda/qqy_hfx_emp_scan_wave_b04_v009.hda`
- PASS: v010 install_validated true
- PASS: preview enabled / hero blocked preserved
- PASS: cache blocked / comp flatten forbidden preserved
- PASS: OUT_TRIGGER_METADATA preserved
- PASS: HDA type installed: `qqy::hfx_emp_scan_wave::4.0`
- PASS: instance created: `/obj/SMOKE_HFX_032_EMP_Scan_Wave_v011`
- PASS: frame 1 cook ok | sop=/obj/SMOKE_HFX_032_EMP_Scan_Wave_v011/OUT_EMP_SCAN_MAIN points=224 prims=0 vertices=None
- PASS: frame 12 cook ok | sop=/obj/SMOKE_HFX_032_EMP_Scan_Wave_v011/OUT_EMP_SCAN_MAIN points=224 prims=0 vertices=None
- PASS: frame 24 cook ok | sop=/obj/SMOKE_HFX_032_EMP_Scan_Wave_v011/OUT_EMP_SCAN_MAIN points=224 prims=0 vertices=None
- PASS: frame 48 cook ok | sop=/obj/SMOKE_HFX_032_EMP_Scan_Wave_v011/OUT_EMP_SCAN_MAIN points=224 prims=0 vertices=None
- PASS: frame 72 cook ok | sop=/obj/SMOKE_HFX_032_EMP_Scan_Wave_v011/OUT_EMP_SCAN_MAIN points=224 prims=0 vertices=None
- PASS: frame 120 cook ok | sop=/obj/SMOKE_HFX_032_EMP_Scan_Wave_v011/OUT_EMP_SCAN_MAIN points=224 prims=0 vertices=None
- Result: PASS

## Pollution Check

Result: PASS
No video/archive/macOS metadata pollution found.

---

Final Status: HFX_B04_CHARACTER_MAGIC_ENVIRONMENT_V011_RUNTIME_SMOKE_TEST_PASS
