# HFX Batch 02 Advanced Core v011 Runtime Smoke Test Report

Generated: 2026-05-17T18:29:46

Status: RUNTIME_SMOKE_TEST_RUNNING

Patch:
- Fixed Houdini Geometry API compatibility.
- Removed hard dependency on geo.vertices().
- Non-empty check now uses points/prims only; vertex count is optional.

## Previous Stage Checks

- PASS: HFX_B02_ADVANCED_CORE_V001_VALIDATION_REPORT.md marker found
- PASS: HFX_B02_ADVANCED_CORE_V002_HIP_TEMPLATE_VALIDATION_REPORT.md marker found
- PASS: HFX_B02_ADVANCED_CORE_V003_TRIGGER_ANIMATION_VALIDATION_REPORT.md marker found
- PASS: HFX_B02_ADVANCED_CORE_V004_PRODUCTION_SPEC_VALIDATION_REPORT.md marker found
- PASS: HFX_B02_ADVANCED_CORE_V005_HDA_CANDIDATE_SPEC_VALIDATION_REPORT.md marker found
- PASS: HFX_B02_ADVANCED_CORE_V006_HDA_INTERFACE_SPEC_VALIDATION_REPORT.md marker found
- PASS: HFX_B02_ADVANCED_CORE_V007_WRAPPER_SPEC_VALIDATION_REPORT.md marker found
- PASS: HFX_B02_ADVANCED_CORE_V008_HDA_PACKAGING_PREFLIGHT_VALIDATION_REPORT.md marker found
- PASS: HFX_B02_ADVANCED_CORE_V009_HDA_PACKAGE_BUILD_VALIDATION_REPORT.md marker found
- PASS: HFX_B02_ADVANCED_CORE_V010_HDA_INSTALL_VALIDATION_REPORT.md marker found

## Runtime Smoke Tests

- PASS: /obj exists
### HFX_009_Volumetric_Fog_Bank

- PASS: HDA file exists: `06_体积雾气_环境烟雾/HFX_009_Volumetric_Fog_Bank/03_hda/qqy_hfx_volumetric_fog_bank_b02_v009.hda`
- PASS: HDA type installed: `qqy::hfx_volumetric_fog_bank::2.0`
- PASS: instance created: `/obj/SMOKE_HFX_009_Volumetric_Fog_Bank_v011`
- PASS: frame 1 cook ok | sop=/obj/SMOKE_HFX_009_Volumetric_Fog_Bank_v011/OUT_FOG_BANK_MAIN points=700 prims=0 vertices=None
- PASS: frame 12 cook ok | sop=/obj/SMOKE_HFX_009_Volumetric_Fog_Bank_v011/OUT_FOG_BANK_MAIN points=700 prims=0 vertices=None
- PASS: frame 24 cook ok | sop=/obj/SMOKE_HFX_009_Volumetric_Fog_Bank_v011/OUT_FOG_BANK_MAIN points=700 prims=0 vertices=None
- PASS: frame 48 cook ok | sop=/obj/SMOKE_HFX_009_Volumetric_Fog_Bank_v011/OUT_FOG_BANK_MAIN points=700 prims=0 vertices=None
- PASS: frame 72 cook ok | sop=/obj/SMOKE_HFX_009_Volumetric_Fog_Bank_v011/OUT_FOG_BANK_MAIN points=700 prims=0 vertices=None
- PASS: frame 120 cook ok | sop=/obj/SMOKE_HFX_009_Volumetric_Fog_Bank_v011/OUT_FOG_BANK_MAIN points=700 prims=0 vertices=None
- Result: PASS

### HFX_010_Smoke_Plume_Column

- PASS: HDA file exists: `06_体积雾气_环境烟雾/HFX_010_Smoke_Plume_Column/03_hda/qqy_hfx_smoke_plume_column_b02_v009.hda`
- PASS: HDA type installed: `qqy::hfx_smoke_plume_column::2.0`
- PASS: instance created: `/obj/SMOKE_HFX_010_Smoke_Plume_Column_v011`
- PASS: frame 1 cook ok | sop=/obj/SMOKE_HFX_010_Smoke_Plume_Column_v011/OUT_SMOKE_PLUME_MAIN points=620 prims=0 vertices=None
- PASS: frame 12 cook ok | sop=/obj/SMOKE_HFX_010_Smoke_Plume_Column_v011/OUT_SMOKE_PLUME_MAIN points=620 prims=0 vertices=None
- PASS: frame 24 cook ok | sop=/obj/SMOKE_HFX_010_Smoke_Plume_Column_v011/OUT_SMOKE_PLUME_MAIN points=620 prims=0 vertices=None
- PASS: frame 48 cook ok | sop=/obj/SMOKE_HFX_010_Smoke_Plume_Column_v011/OUT_SMOKE_PLUME_MAIN points=620 prims=0 vertices=None
- PASS: frame 72 cook ok | sop=/obj/SMOKE_HFX_010_Smoke_Plume_Column_v011/OUT_SMOKE_PLUME_MAIN points=620 prims=0 vertices=None
- PASS: frame 120 cook ok | sop=/obj/SMOKE_HFX_010_Smoke_Plume_Column_v011/OUT_SMOKE_PLUME_MAIN points=620 prims=0 vertices=None
- Result: PASS

### HFX_011_Ember_Ash_Field

- PASS: HDA file exists: `07_粒子火星_灰烬火花/HFX_011_Ember_Ash_Field/03_hda/qqy_hfx_ember_ash_field_b02_v009.hda`
- PASS: HDA type installed: `qqy::hfx_ember_ash_field::2.0`
- PASS: instance created: `/obj/SMOKE_HFX_011_Ember_Ash_Field_v011`
- PASS: frame 1 cook ok | sop=/obj/SMOKE_HFX_011_Ember_Ash_Field_v011/OUT_EMBER_ASH_MAIN points=520 prims=0 vertices=None
- PASS: frame 12 cook ok | sop=/obj/SMOKE_HFX_011_Ember_Ash_Field_v011/OUT_EMBER_ASH_MAIN points=520 prims=0 vertices=None
- PASS: frame 24 cook ok | sop=/obj/SMOKE_HFX_011_Ember_Ash_Field_v011/OUT_EMBER_ASH_MAIN points=520 prims=0 vertices=None
- PASS: frame 48 cook ok | sop=/obj/SMOKE_HFX_011_Ember_Ash_Field_v011/OUT_EMBER_ASH_MAIN points=520 prims=0 vertices=None
- PASS: frame 72 cook ok | sop=/obj/SMOKE_HFX_011_Ember_Ash_Field_v011/OUT_EMBER_ASH_MAIN points=520 prims=0 vertices=None
- PASS: frame 120 cook ok | sop=/obj/SMOKE_HFX_011_Ember_Ash_Field_v011/OUT_EMBER_ASH_MAIN points=520 prims=0 vertices=None
- Result: PASS

### HFX_012_Sparks_Impact_Spray

- PASS: HDA file exists: `07_粒子火星_灰烬火花/HFX_012_Sparks_Impact_Spray/03_hda/qqy_hfx_sparks_impact_spray_b02_v009.hda`
- PASS: HDA type installed: `qqy::hfx_sparks_impact_spray::2.0`
- PASS: instance created: `/obj/SMOKE_HFX_012_Sparks_Impact_Spray_v011`
- PASS: frame 1 cook ok | sop=/obj/SMOKE_HFX_012_Sparks_Impact_Spray_v011/OUT_SPARKS_MAIN points=360 prims=0 vertices=None
- PASS: frame 12 cook ok | sop=/obj/SMOKE_HFX_012_Sparks_Impact_Spray_v011/OUT_SPARKS_MAIN points=360 prims=0 vertices=None
- PASS: frame 24 cook ok | sop=/obj/SMOKE_HFX_012_Sparks_Impact_Spray_v011/OUT_SPARKS_MAIN points=360 prims=0 vertices=None
- PASS: frame 48 cook ok | sop=/obj/SMOKE_HFX_012_Sparks_Impact_Spray_v011/OUT_SPARKS_MAIN points=360 prims=0 vertices=None
- PASS: frame 72 cook ok | sop=/obj/SMOKE_HFX_012_Sparks_Impact_Spray_v011/OUT_SPARKS_MAIN points=360 prims=0 vertices=None
- PASS: frame 120 cook ok | sop=/obj/SMOKE_HFX_012_Sparks_Impact_Spray_v011/OUT_SPARKS_MAIN points=360 prims=0 vertices=None
- Result: PASS

### HFX_013_Debris_Burst_Radial

- PASS: HDA file exists: `08_碎片爆发_二级破坏/HFX_013_Debris_Burst_Radial/03_hda/qqy_hfx_debris_burst_radial_b02_v009.hda`
- PASS: HDA type installed: `qqy::hfx_debris_burst_radial::2.0`
- PASS: instance created: `/obj/SMOKE_HFX_013_Debris_Burst_Radial_v011`
- PASS: frame 1 cook ok | sop=/obj/SMOKE_HFX_013_Debris_Burst_Radial_v011/OUT_DEBRIS_BURST_MAIN points=180 prims=0 vertices=None
- PASS: frame 12 cook ok | sop=/obj/SMOKE_HFX_013_Debris_Burst_Radial_v011/OUT_DEBRIS_BURST_MAIN points=180 prims=0 vertices=None
- PASS: frame 24 cook ok | sop=/obj/SMOKE_HFX_013_Debris_Burst_Radial_v011/OUT_DEBRIS_BURST_MAIN points=180 prims=0 vertices=None
- PASS: frame 48 cook ok | sop=/obj/SMOKE_HFX_013_Debris_Burst_Radial_v011/OUT_DEBRIS_BURST_MAIN points=180 prims=0 vertices=None
- PASS: frame 72 cook ok | sop=/obj/SMOKE_HFX_013_Debris_Burst_Radial_v011/OUT_DEBRIS_BURST_MAIN points=180 prims=0 vertices=None
- PASS: frame 120 cook ok | sop=/obj/SMOKE_HFX_013_Debris_Burst_Radial_v011/OUT_DEBRIS_BURST_MAIN points=180 prims=0 vertices=None
- Result: PASS

### HFX_014_Magic_Particle_Aura

- PASS: HDA file exists: `09_魔法能量_空间场/HFX_014_Magic_Particle_Aura/03_hda/qqy_hfx_magic_particle_aura_b02_v009.hda`
- PASS: HDA type installed: `qqy::hfx_magic_particle_aura::2.0`
- PASS: instance created: `/obj/SMOKE_HFX_014_Magic_Particle_Aura_v011`
- PASS: frame 1 cook ok | sop=/obj/SMOKE_HFX_014_Magic_Particle_Aura_v011/OUT_MAGIC_AURA_MAIN points=420 prims=0 vertices=None
- PASS: frame 12 cook ok | sop=/obj/SMOKE_HFX_014_Magic_Particle_Aura_v011/OUT_MAGIC_AURA_MAIN points=420 prims=0 vertices=None
- PASS: frame 24 cook ok | sop=/obj/SMOKE_HFX_014_Magic_Particle_Aura_v011/OUT_MAGIC_AURA_MAIN points=420 prims=0 vertices=None
- PASS: frame 48 cook ok | sop=/obj/SMOKE_HFX_014_Magic_Particle_Aura_v011/OUT_MAGIC_AURA_MAIN points=420 prims=0 vertices=None
- PASS: frame 72 cook ok | sop=/obj/SMOKE_HFX_014_Magic_Particle_Aura_v011/OUT_MAGIC_AURA_MAIN points=420 prims=0 vertices=None
- PASS: frame 120 cook ok | sop=/obj/SMOKE_HFX_014_Magic_Particle_Aura_v011/OUT_MAGIC_AURA_MAIN points=420 prims=0 vertices=None
- Result: PASS

### HFX_015_Portal_Ring_Field

- PASS: HDA file exists: `09_魔法能量_空间场/HFX_015_Portal_Ring_Field/03_hda/qqy_hfx_portal_ring_field_b02_v009.hda`
- PASS: HDA type installed: `qqy::hfx_portal_ring_field::2.0`
- PASS: instance created: `/obj/SMOKE_HFX_015_Portal_Ring_Field_v011`
- PASS: frame 1 cook ok | sop=/obj/SMOKE_HFX_015_Portal_Ring_Field_v011/OUT_PORTAL_RING_MAIN points=360 prims=0 vertices=None
- PASS: frame 12 cook ok | sop=/obj/SMOKE_HFX_015_Portal_Ring_Field_v011/OUT_PORTAL_RING_MAIN points=360 prims=0 vertices=None
- PASS: frame 24 cook ok | sop=/obj/SMOKE_HFX_015_Portal_Ring_Field_v011/OUT_PORTAL_RING_MAIN points=360 prims=0 vertices=None
- PASS: frame 48 cook ok | sop=/obj/SMOKE_HFX_015_Portal_Ring_Field_v011/OUT_PORTAL_RING_MAIN points=360 prims=0 vertices=None
- PASS: frame 72 cook ok | sop=/obj/SMOKE_HFX_015_Portal_Ring_Field_v011/OUT_PORTAL_RING_MAIN points=360 prims=0 vertices=None
- PASS: frame 120 cook ok | sop=/obj/SMOKE_HFX_015_Portal_Ring_Field_v011/OUT_PORTAL_RING_MAIN points=360 prims=0 vertices=None
- Result: PASS

### HFX_016_Heat_Distortion_Field

- PASS: HDA file exists: `10_热浪扭曲_空气扰动/HFX_016_Heat_Distortion_Field/03_hda/qqy_hfx_heat_distortion_field_b02_v009.hda`
- PASS: HDA type installed: `qqy::hfx_heat_distortion_field::2.0`
- PASS: instance created: `/obj/SMOKE_HFX_016_Heat_Distortion_Field_v011`
- PASS: frame 1 cook ok | sop=/obj/SMOKE_HFX_016_Heat_Distortion_Field_v011/OUT_HEAT_DISTORTION_MAIN points=480 prims=0 vertices=None
- PASS: frame 12 cook ok | sop=/obj/SMOKE_HFX_016_Heat_Distortion_Field_v011/OUT_HEAT_DISTORTION_MAIN points=480 prims=0 vertices=None
- PASS: frame 24 cook ok | sop=/obj/SMOKE_HFX_016_Heat_Distortion_Field_v011/OUT_HEAT_DISTORTION_MAIN points=480 prims=0 vertices=None
- PASS: frame 48 cook ok | sop=/obj/SMOKE_HFX_016_Heat_Distortion_Field_v011/OUT_HEAT_DISTORTION_MAIN points=480 prims=0 vertices=None
- PASS: frame 72 cook ok | sop=/obj/SMOKE_HFX_016_Heat_Distortion_Field_v011/OUT_HEAT_DISTORTION_MAIN points=480 prims=0 vertices=None
- PASS: frame 120 cook ok | sop=/obj/SMOKE_HFX_016_Heat_Distortion_Field_v011/OUT_HEAT_DISTORTION_MAIN points=480 prims=0 vertices=None
- Result: PASS

## Pollution Check

Result: PASS
No video/archive/macOS metadata pollution found.

---

Final Status: HFX_B02_ADVANCED_CORE_V011_RUNTIME_SMOKE_TEST_PASS
