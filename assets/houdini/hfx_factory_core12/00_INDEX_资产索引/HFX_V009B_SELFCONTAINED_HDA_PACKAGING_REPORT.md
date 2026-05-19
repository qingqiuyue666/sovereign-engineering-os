# HFX v009B Self-Contained HDA Packaging Report

Generated: 2026-05-17T17:33:04

Status: PACKAGING_RUNNING

Fix Reason:
- v009 wrapper packaging failed because wrapper object_merge nodes referenced v003 nodes outside the subnet.
- v009B packages the v003 engine itself and adds stable output aliases inside the same network.
- This removes external references and produces self-contained HDA candidates.

## Preflight Chain

- PASS: HFX_V003_OPEN_VALIDATION_REPORT.md marker found
- PASS: HFX_V004_PRODUCTION_SPEC_VALIDATION_REPORT.md marker found
- PASS: HFX_V005_HDA_CANDIDATE_SPEC_VALIDATION_REPORT.md marker found
- PASS: HFX_V006_HDA_INTERFACE_SPEC_VALIDATION_REPORT.md marker found
- PASS: HFX_V007_WRAPPER_VALIDATION_REPORT.md marker found
- PASS: HFX_V008_HDA_PACKAGING_PREFLIGHT_REPORT.md marker found

## Self-Contained HDA Packaging

### HFX_001_Energy_Trail_Basic

Result: FAIL
Reason: `The attempted operation failed.
The selected subnet has references to nodes outside
the subnet, or has references that use absolute paths
to operators inside the subnet.  These references
should be converted to relative internal references
or this operator type may not work properly in other
Hip files.


/obj/HFX_001_Energy_Trail_Basic_v003/EXPORT_energy_trail_v003_abc: references /obj
        which is outside the network being saved.`

### HFX_002_Slash_Trail_Curve

Result: FAIL
Reason: `The attempted operation failed.
The selected subnet has references to nodes outside
the subnet, or has references that use absolute paths
to operators inside the subnet.  These references
should be converted to relative internal references
or this operator type may not work properly in other
Hip files.


/obj/HFX_002_Slash_Trail_Curve_v003/EXPORT_slash_trail_v003_abc: references /obj
        which is outside the network being saved.`

### HFX_003_Footstep_Dust_Impact

Result: PASS
HDA Type: `qqy::hfx_footstep_dust::9.0`
HDA File: `99_HDA_CANDIDATES/v009_hda_output/qqy_hfx_footstep_dust_v009.hda`
Rollback Manifest: `99_HDA_CANDIDATES/rollback/HFX_003_Footstep_Dust_Impact_v009B_2026-05-17T17-33-04/rollback_manifest.json`
README_v009B: `02_烟尘雾气_扬尘环境雾/HFX_003_Footstep_Dust_Impact/05_notes/README_v009B.md`

### HFX_004_Ground_Dust_Ring

Result: PASS
HDA Type: `qqy::hfx_ground_dust_ring::9.0`
HDA File: `99_HDA_CANDIDATES/v009_hda_output/qqy_hfx_ground_dust_ring_v009.hda`
Rollback Manifest: `99_HDA_CANDIDATES/rollback/HFX_004_Ground_Dust_Ring_v009B_2026-05-17T17-33-04/rollback_manifest.json`
README_v009B: `02_烟尘雾气_扬尘环境雾/HFX_004_Ground_Dust_Ring/05_notes/README_v009B.md`

### HFX_005_Small_Pyro_Burst

Result: PASS
HDA Type: `qqy::hfx_small_pyro_burst::9.0`
HDA File: `99_HDA_CANDIDATES/v009_hda_output/qqy_hfx_small_pyro_burst_v009.hda`
Rollback Manifest: `99_HDA_CANDIDATES/rollback/HFX_005_Small_Pyro_Burst_v009B_2026-05-17T17-33-04/rollback_manifest.json`
README_v009B: `03_火焰爆炸_火球浓烟/HFX_005_Small_Pyro_Burst/05_notes/README_v009B.md`

### HFX_006_Ground_Crack_Debris

Result: FAIL
Reason: `The attempted operation failed.
The selected subnet has references to nodes outside
the subnet, or has references that use absolute paths
to operators inside the subnet.  These references
should be converted to relative internal references
or this operator type may not work properly in other
Hip files.


/obj/HFX_006_Ground_Crack_Debris_v003/EXPORT_ground_crack_debris_v003_abc: references /obj
        which is outside the network being saved.`

### HFX_007_Lightning_Arc_Basic

Result: FAIL
Reason: `The attempted operation failed.
The selected subnet has references to nodes outside
the subnet, or has references that use absolute paths
to operators inside the subnet.  These references
should be converted to relative internal references
or this operator type may not work properly in other
Hip files.


/obj/HFX_007_Lightning_Arc_Basic_v003/EXPORT_lightning_arc_v003_abc: references /obj
        which is outside the network being saved.`

### HFX_008_Energy_Shockwave

Result: FAIL
Reason: `The attempted operation failed.
The selected subnet has references to nodes outside
the subnet, or has references that use absolute paths
to operators inside the subnet.  These references
should be converted to relative internal references
or this operator type may not work properly in other
Hip files.


/obj/HFX_008_Energy_Shockwave_v003/EXPORT_energy_shockwave_v003_abc: references /obj
        which is outside the network being saved.`

---

Final Status: HFX_V009B_SELFCONTAINED_HDA_PACKAGING_FAIL
