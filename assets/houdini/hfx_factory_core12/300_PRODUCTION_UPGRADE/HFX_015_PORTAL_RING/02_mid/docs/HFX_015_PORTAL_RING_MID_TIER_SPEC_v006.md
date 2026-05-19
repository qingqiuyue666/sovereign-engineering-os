# HFX_015 Portal Ring MID Tier Spec v006

Status: HFX_015_PORTAL_RING_MID_TIER_SPEC_V006_READY

Asset:
- HFX_015 Portal Ring

Tier:
- MID

Purpose:
Lookdev-ready portal with improved core, animated rim proxy, spark layer, alpha, zdepth, and distortion-vector pass structure.

Required Nodes:
- HFX_015_MID_PORTAL_CORE_v006
- HFX_015_MID_RIM_EMISSION_v006
- HFX_015_MID_INNER_SURFACE_v006
- HFX_015_MID_SPARK_LAYER_v006
- HFX_015_MID_DISTORTION_VECTOR_v006
- HFX_015_MID_ALPHA_ZDEPTH_v006
- HFX_015_MID_METADATA_ANCHOR_v006

Required Outputs:
- OUT_MID_PORTAL_CORE
- OUT_MID_RIM_EMISSION
- OUT_MID_INNER_SURFACE
- OUT_MID_SPARK_LAYER
- OUT_MID_DISTORTION_VECTOR
- OUT_MID_ALPHA
- OUT_MID_ZDEPTH
- OUT_MID_METADATA

Blocked:
- FINAL_CANDIDATE claim
- release seal claim
- production render claim
- Hollywood final-pixel claim
- delivery

Next:
HFX_FACTORY_V007_HFX015_PORTAL_RING_MID_TIER_VALIDATION
