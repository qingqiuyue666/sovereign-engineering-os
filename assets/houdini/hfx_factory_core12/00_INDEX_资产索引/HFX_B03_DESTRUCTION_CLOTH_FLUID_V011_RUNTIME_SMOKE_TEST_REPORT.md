# HFX Batch 03 Destruction Cloth Fluid v011 Runtime Smoke Test Report

Generated: 2026-05-17T19:00:37

Status: RUNTIME_SMOKE_TEST_RUNNING

Policy:
- Runtime smoke tests preview/proxy HDA behavior only.
- Hero heavy solver mode remains blocked.
- Geometry is resolved through display/render/internal SOP nodes.

## Previous Stage Checks

- PASS: HFX_B03_DESTRUCTION_CLOTH_FLUID_V001_VALIDATION_REPORT.md marker found
- PASS: HFX_B03_DESTRUCTION_CLOTH_FLUID_V002_HIP_TEMPLATE_VALIDATION_REPORT.md marker found
- PASS: HFX_B03_DESTRUCTION_CLOTH_FLUID_V003_TRIGGER_ANIMATION_VALIDATION_REPORT.md marker found
- PASS: HFX_B03_DESTRUCTION_CLOTH_FLUID_V004_PRODUCTION_SPEC_VALIDATION_REPORT.md marker found
- PASS: HFX_B03_DESTRUCTION_CLOTH_FLUID_V005_HEAVY_SOLVER_CANDIDATE_SPEC_VALIDATION_REPORT.md marker found
- PASS: HFX_B03_DESTRUCTION_CLOTH_FLUID_V006_SOLVER_INTERFACE_SPEC_VALIDATION_REPORT.md marker found
- PASS: HFX_B03_DESTRUCTION_CLOTH_FLUID_V007_WRAPPER_SPEC_VALIDATION_REPORT.md marker found
- PASS: HFX_B03_DESTRUCTION_CLOTH_FLUID_V008_HDA_PACKAGING_PREFLIGHT_VALIDATION_REPORT.md marker found
- PASS: HFX_B03_DESTRUCTION_CLOTH_FLUID_V009_HDA_PACKAGE_BUILD_VALIDATION_REPORT.md marker found
- PASS: HFX_B03_DESTRUCTION_CLOTH_FLUID_V010_HDA_INSTALL_VALIDATION_REPORT.md marker found

## Runtime Smoke Tests

- PASS: /obj exists
### HFX_017_Building_Fracture_Collapse

- PASS: HDA file exists: `11_大规模破坏_建筑碎裂/HFX_017_Building_Fracture_Collapse/03_hda/qqy_hfx_building_fracture_collapse_b03_v009.hda`
- PASS: v010 install_validated true
- PASS: preview enabled / hero blocked preserved
- PASS: HDA type installed: `qqy::hfx_building_fracture_collapse::3.0`
- PASS: instance created: `/obj/SMOKE_HFX_017_Building_Fracture_Collapse_v011`
- PASS: frame 1 cook ok | sop=/obj/SMOKE_HFX_017_Building_Fracture_Collapse_v011/OUT_COLLAPSE_MAIN points=128 prims=0 vertices=None
- PASS: frame 12 cook ok | sop=/obj/SMOKE_HFX_017_Building_Fracture_Collapse_v011/OUT_COLLAPSE_MAIN points=128 prims=0 vertices=None
- PASS: frame 24 cook ok | sop=/obj/SMOKE_HFX_017_Building_Fracture_Collapse_v011/OUT_COLLAPSE_MAIN points=128 prims=0 vertices=None
- PASS: frame 48 cook ok | sop=/obj/SMOKE_HFX_017_Building_Fracture_Collapse_v011/OUT_COLLAPSE_MAIN points=128 prims=0 vertices=None
- PASS: frame 72 cook ok | sop=/obj/SMOKE_HFX_017_Building_Fracture_Collapse_v011/OUT_COLLAPSE_MAIN points=128 prims=0 vertices=None
- PASS: frame 120 cook ok | sop=/obj/SMOKE_HFX_017_Building_Fracture_Collapse_v011/OUT_COLLAPSE_MAIN points=128 prims=0 vertices=None
- Result: PASS

### HFX_018_Glass_Shatter_Burst

- PASS: HDA file exists: `11_大规模破坏_建筑碎裂/HFX_018_Glass_Shatter_Burst/03_hda/qqy_hfx_glass_shatter_burst_b03_v009.hda`
- PASS: v010 install_validated true
- PASS: preview enabled / hero blocked preserved
- PASS: HDA type installed: `qqy::hfx_glass_shatter_burst::3.0`
- PASS: instance created: `/obj/SMOKE_HFX_018_Glass_Shatter_Burst_v011`
- PASS: frame 1 cook ok | sop=/obj/SMOKE_HFX_018_Glass_Shatter_Burst_v011/OUT_GLASS_SHATTER_MAIN points=360 prims=0 vertices=None
- PASS: frame 12 cook ok | sop=/obj/SMOKE_HFX_018_Glass_Shatter_Burst_v011/OUT_GLASS_SHATTER_MAIN points=360 prims=0 vertices=None
- PASS: frame 24 cook ok | sop=/obj/SMOKE_HFX_018_Glass_Shatter_Burst_v011/OUT_GLASS_SHATTER_MAIN points=360 prims=0 vertices=None
- PASS: frame 48 cook ok | sop=/obj/SMOKE_HFX_018_Glass_Shatter_Burst_v011/OUT_GLASS_SHATTER_MAIN points=360 prims=0 vertices=None
- PASS: frame 72 cook ok | sop=/obj/SMOKE_HFX_018_Glass_Shatter_Burst_v011/OUT_GLASS_SHATTER_MAIN points=360 prims=0 vertices=None
- PASS: frame 120 cook ok | sop=/obj/SMOKE_HFX_018_Glass_Shatter_Burst_v011/OUT_GLASS_SHATTER_MAIN points=360 prims=0 vertices=None
- Result: PASS

### HFX_019_Vellum_Cape_Cloth_Sim

- PASS: HDA file exists: `12_布料披风_角色动力学/HFX_019_Vellum_Cape_Cloth_Sim/03_hda/qqy_hfx_vellum_cape_cloth_sim_b03_v009.hda`
- PASS: v010 install_validated true
- PASS: preview enabled / hero blocked preserved
- PASS: HDA type installed: `qqy::hfx_vellum_cape_cloth_sim::3.0`
- PASS: instance created: `/obj/SMOKE_HFX_019_Vellum_Cape_Cloth_Sim_v011`
- PASS: frame 1 cook ok | sop=/obj/SMOKE_HFX_019_Vellum_Cape_Cloth_Sim_v011/OUT_CLOTH_MAIN points=480 prims=0 vertices=None
- PASS: frame 12 cook ok | sop=/obj/SMOKE_HFX_019_Vellum_Cape_Cloth_Sim_v011/OUT_CLOTH_MAIN points=480 prims=0 vertices=None
- PASS: frame 24 cook ok | sop=/obj/SMOKE_HFX_019_Vellum_Cape_Cloth_Sim_v011/OUT_CLOTH_MAIN points=480 prims=0 vertices=None
- PASS: frame 48 cook ok | sop=/obj/SMOKE_HFX_019_Vellum_Cape_Cloth_Sim_v011/OUT_CLOTH_MAIN points=480 prims=0 vertices=None
- PASS: frame 72 cook ok | sop=/obj/SMOKE_HFX_019_Vellum_Cape_Cloth_Sim_v011/OUT_CLOTH_MAIN points=480 prims=0 vertices=None
- PASS: frame 120 cook ok | sop=/obj/SMOKE_HFX_019_Vellum_Cape_Cloth_Sim_v011/OUT_CLOTH_MAIN points=480 prims=0 vertices=None
- Result: PASS

### HFX_020_FLIP_Water_Splash

- PASS: HDA file exists: `13_水体液体_FLIP/HFX_020_FLIP_Water_Splash/03_hda/qqy_hfx_flip_water_splash_b03_v009.hda`
- PASS: v010 install_validated true
- PASS: preview enabled / hero blocked preserved
- PASS: HDA type installed: `qqy::hfx_flip_water_splash::3.0`
- PASS: instance created: `/obj/SMOKE_HFX_020_FLIP_Water_Splash_v011`
- PASS: frame 1 cook ok | sop=/obj/SMOKE_HFX_020_FLIP_Water_Splash_v011/OUT_WATER_SPLASH_MAIN points=520 prims=0 vertices=None
- PASS: frame 12 cook ok | sop=/obj/SMOKE_HFX_020_FLIP_Water_Splash_v011/OUT_WATER_SPLASH_MAIN points=520 prims=0 vertices=None
- PASS: frame 24 cook ok | sop=/obj/SMOKE_HFX_020_FLIP_Water_Splash_v011/OUT_WATER_SPLASH_MAIN points=520 prims=0 vertices=None
- PASS: frame 48 cook ok | sop=/obj/SMOKE_HFX_020_FLIP_Water_Splash_v011/OUT_WATER_SPLASH_MAIN points=520 prims=0 vertices=None
- PASS: frame 72 cook ok | sop=/obj/SMOKE_HFX_020_FLIP_Water_Splash_v011/OUT_WATER_SPLASH_MAIN points=520 prims=0 vertices=None
- PASS: frame 120 cook ok | sop=/obj/SMOKE_HFX_020_FLIP_Water_Splash_v011/OUT_WATER_SPLASH_MAIN points=520 prims=0 vertices=None
- Result: PASS

### HFX_021_Advanced_Pyro_Explosion

- PASS: HDA file exists: `14_高级爆炸_Pyro/HFX_021_Advanced_Pyro_Explosion/03_hda/qqy_hfx_advanced_pyro_explosion_b03_v009.hda`
- PASS: v010 install_validated true
- PASS: preview enabled / hero blocked preserved
- PASS: HDA type installed: `qqy::hfx_advanced_pyro_explosion::3.0`
- PASS: instance created: `/obj/SMOKE_HFX_021_Advanced_Pyro_Explosion_v011`
- PASS: frame 1 cook ok | sop=/obj/SMOKE_HFX_021_Advanced_Pyro_Explosion_v011/OUT_PYRO_EXPLOSION_MAIN points=680 prims=0 vertices=None
- PASS: frame 12 cook ok | sop=/obj/SMOKE_HFX_021_Advanced_Pyro_Explosion_v011/OUT_PYRO_EXPLOSION_MAIN points=680 prims=0 vertices=None
- PASS: frame 24 cook ok | sop=/obj/SMOKE_HFX_021_Advanced_Pyro_Explosion_v011/OUT_PYRO_EXPLOSION_MAIN points=680 prims=0 vertices=None
- PASS: frame 48 cook ok | sop=/obj/SMOKE_HFX_021_Advanced_Pyro_Explosion_v011/OUT_PYRO_EXPLOSION_MAIN points=680 prims=0 vertices=None
- PASS: frame 72 cook ok | sop=/obj/SMOKE_HFX_021_Advanced_Pyro_Explosion_v011/OUT_PYRO_EXPLOSION_MAIN points=680 prims=0 vertices=None
- PASS: frame 120 cook ok | sop=/obj/SMOKE_HFX_021_Advanced_Pyro_Explosion_v011/OUT_PYRO_EXPLOSION_MAIN points=680 prims=0 vertices=None
- Result: PASS

### HFX_022_Storm_Cloud_Volume

- PASS: HDA file exists: `15_风暴云_环境体积/HFX_022_Storm_Cloud_Volume/03_hda/qqy_hfx_storm_cloud_volume_b03_v009.hda`
- PASS: v010 install_validated true
- PASS: preview enabled / hero blocked preserved
- PASS: HDA type installed: `qqy::hfx_storm_cloud_volume::3.0`
- PASS: instance created: `/obj/SMOKE_HFX_022_Storm_Cloud_Volume_v011`
- PASS: frame 1 cook ok | sop=/obj/SMOKE_HFX_022_Storm_Cloud_Volume_v011/OUT_STORM_CLOUD_MAIN points=900 prims=0 vertices=None
- PASS: frame 12 cook ok | sop=/obj/SMOKE_HFX_022_Storm_Cloud_Volume_v011/OUT_STORM_CLOUD_MAIN points=900 prims=0 vertices=None
- PASS: frame 24 cook ok | sop=/obj/SMOKE_HFX_022_Storm_Cloud_Volume_v011/OUT_STORM_CLOUD_MAIN points=900 prims=0 vertices=None
- PASS: frame 48 cook ok | sop=/obj/SMOKE_HFX_022_Storm_Cloud_Volume_v011/OUT_STORM_CLOUD_MAIN points=900 prims=0 vertices=None
- PASS: frame 72 cook ok | sop=/obj/SMOKE_HFX_022_Storm_Cloud_Volume_v011/OUT_STORM_CLOUD_MAIN points=900 prims=0 vertices=None
- PASS: frame 120 cook ok | sop=/obj/SMOKE_HFX_022_Storm_Cloud_Volume_v011/OUT_STORM_CLOUD_MAIN points=900 prims=0 vertices=None
- Result: PASS

### HFX_023_Ground_Collapse_Sinkhole

- PASS: HDA file exists: `16_地面塌陷_岩层崩解/HFX_023_Ground_Collapse_Sinkhole/03_hda/qqy_hfx_ground_collapse_sinkhole_b03_v009.hda`
- PASS: v010 install_validated true
- PASS: preview enabled / hero blocked preserved
- PASS: HDA type installed: `qqy::hfx_ground_collapse_sinkhole::3.0`
- PASS: instance created: `/obj/SMOKE_HFX_023_Ground_Collapse_Sinkhole_v011`
- PASS: frame 1 cook ok | sop=/obj/SMOKE_HFX_023_Ground_Collapse_Sinkhole_v011/OUT_GROUND_COLLAPSE_MAIN points=420 prims=0 vertices=None
- PASS: frame 12 cook ok | sop=/obj/SMOKE_HFX_023_Ground_Collapse_Sinkhole_v011/OUT_GROUND_COLLAPSE_MAIN points=420 prims=0 vertices=None
- PASS: frame 24 cook ok | sop=/obj/SMOKE_HFX_023_Ground_Collapse_Sinkhole_v011/OUT_GROUND_COLLAPSE_MAIN points=420 prims=0 vertices=None
- PASS: frame 48 cook ok | sop=/obj/SMOKE_HFX_023_Ground_Collapse_Sinkhole_v011/OUT_GROUND_COLLAPSE_MAIN points=420 prims=0 vertices=None
- PASS: frame 72 cook ok | sop=/obj/SMOKE_HFX_023_Ground_Collapse_Sinkhole_v011/OUT_GROUND_COLLAPSE_MAIN points=420 prims=0 vertices=None
- PASS: frame 120 cook ok | sop=/obj/SMOKE_HFX_023_Ground_Collapse_Sinkhole_v011/OUT_GROUND_COLLAPSE_MAIN points=420 prims=0 vertices=None
- Result: PASS

### HFX_024_Energy_Shield_Shatter

- PASS: HDA file exists: `17_能量护盾_屏障破碎/HFX_024_Energy_Shield_Shatter/03_hda/qqy_hfx_energy_shield_shatter_b03_v009.hda`
- PASS: v010 install_validated true
- PASS: preview enabled / hero blocked preserved
- PASS: HDA type installed: `qqy::hfx_energy_shield_shatter::3.0`
- PASS: instance created: `/obj/SMOKE_HFX_024_Energy_Shield_Shatter_v011`
- PASS: frame 1 cook ok | sop=/obj/SMOKE_HFX_024_Energy_Shield_Shatter_v011/OUT_SHIELD_SHATTER_MAIN points=520 prims=0 vertices=None
- PASS: frame 12 cook ok | sop=/obj/SMOKE_HFX_024_Energy_Shield_Shatter_v011/OUT_SHIELD_SHATTER_MAIN points=520 prims=0 vertices=None
- PASS: frame 24 cook ok | sop=/obj/SMOKE_HFX_024_Energy_Shield_Shatter_v011/OUT_SHIELD_SHATTER_MAIN points=520 prims=0 vertices=None
- PASS: frame 48 cook ok | sop=/obj/SMOKE_HFX_024_Energy_Shield_Shatter_v011/OUT_SHIELD_SHATTER_MAIN points=520 prims=0 vertices=None
- PASS: frame 72 cook ok | sop=/obj/SMOKE_HFX_024_Energy_Shield_Shatter_v011/OUT_SHIELD_SHATTER_MAIN points=520 prims=0 vertices=None
- PASS: frame 120 cook ok | sop=/obj/SMOKE_HFX_024_Energy_Shield_Shatter_v011/OUT_SHIELD_SHATTER_MAIN points=520 prims=0 vertices=None
- Result: PASS

## Pollution Check

Result: PASS
No video/archive/macOS metadata pollution found.

---

Final Status: HFX_B03_DESTRUCTION_CLOTH_FLUID_V011_RUNTIME_SMOKE_TEST_PASS
