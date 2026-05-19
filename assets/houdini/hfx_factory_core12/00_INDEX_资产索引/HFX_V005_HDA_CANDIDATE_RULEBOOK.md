# HFX v005 HDA Candidate Rulebook

Status: HFX_V005_HDA_CANDIDATE_RULEBOOK_READY

Purpose:
Move the first HFX batch from production templates into HDA-candidate assets.

v001:
- Base procedural skeleton.

v002:
- Hollywood reference layering.

v003:
- Trigger-frame time evolution and animated behavior.

v004:
- Production packaging, lookdev intent, preview/cache/solver rules.

v005:
- HDA candidate specification.
- Unified parameter panel design.
- Locked output naming.
- Shot input binding contract.
- Versioned asset interface.
- Validation target for future HDA conversion.

This stage does not modify existing v003 HIP files.
It defines the correct HDA candidate contract before actual digital asset creation.

---

## Global HDA Candidate Standard

Every HFX HDA candidate must have:

1. Stable User Interface Groups
   - 00_GLOBAL
   - 01_INPUT
   - 02_TIMING
   - 03_SHAPE
   - 04_MOTION
   - 05_LOOKDEV
   - 06_OUTPUT
   - 07_DEBUG

2. Required Global Parameters
   - asset_version
   - asset_id
   - trigger_frame
   - frame_start
   - frame_end
   - shot_scale
   - intensity
   - seed
   - enable_preview
   - enable_cache
   - enable_export

3. Required Input Parameters
   - input_mode
   - attach_target
   - world_position
   - world_rotation
   - input_curve_path where curve-based
   - collision_proxy_path where physical
   - ground_proxy_path where ground-based

4. Required Timing Parameters
   - trigger_frame
   - duration_frames
   - attack
   - decay_start
   - decay_strength
   - time_offset

5. Required Output Nodes
   - OUT_MAIN
   - OUT_RENDER
   - OUT_CACHE
   - OUT_DEBUG
   - OUT_LAYER_A
   - OUT_LAYER_B
   - OUT_LAYER_C where relevant

6. Locked Naming Rule
   Internal node names may vary.
   Published output names must not vary.

7. Cache Naming Rule
   Cache paths must resolve to:
   - 02_cache/bgeo/{asset_id}_{version}.$F4.bgeo.sc
   - 02_cache/vdb/{asset_id}_{version}.$F4.vdb
   - 04_export/abc/{asset_id}_{version}.abc
   - 04_export/vdb/{asset_id}_{version}.$F4.vdb

8. Shot Integration Rule
   No final cache without:
   - trigger_frame
   - shot_scale
   - attach target or world position
   - output layer selection
   - preview approval

9. HDA Conversion Rule
   Do not create final HDA until:
   - v005 spec passes
   - v003 HIP open validation passes
   - v004 production spec passes
   - output naming is locked
   - parameter groups are defined
   - README_v005 exists
   - HDA candidate report exists

10. Failure Conditions
   - Missing README_v005
   - Missing v003 HIP
   - Missing README_v004
   - Missing v004 validation pass marker
   - Missing v003 open validation pass marker
   - Missing output naming contract
   - Missing parameter panel contract
   - Dirty asset folder
   - No shot-scale warning

---

## HDA Candidate Naming

HDA candidate name pattern:

- qqy::hfx_energy_trail::5.0
- qqy::hfx_slash_trail::5.0
- qqy::hfx_footstep_dust::5.0
- qqy::hfx_ground_dust_ring::5.0
- qqy::hfx_small_pyro_burst::5.0
- qqy::hfx_ground_crack_debris::5.0
- qqy::hfx_lightning_arc::5.0
- qqy::hfx_energy_shockwave::5.0

Actual HDA creation is deferred until v006 or explicit manual approval.
v005 only defines the asset interface contract.

---

## v005 Pass Marker

Final pass marker:

HFX_V005_HDA_CANDIDATE_SPEC_PASS
