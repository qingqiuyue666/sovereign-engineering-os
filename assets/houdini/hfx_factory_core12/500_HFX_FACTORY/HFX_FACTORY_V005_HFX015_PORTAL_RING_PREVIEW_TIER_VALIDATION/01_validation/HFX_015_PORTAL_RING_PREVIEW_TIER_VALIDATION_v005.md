# HFX_015 Portal Ring PREVIEW Tier Validation v005

Status: HFX_FACTORY_V005_HFX015_PORTAL_RING_PREVIEW_TIER_VALIDATION_PASS

Asset:
- HFX_015 Portal Ring

Validated:
- PREVIEW HIP reopens
- required PREVIEW nodes exist
- required PREVIEW outputs exist
- six-frame cook validation passes
- render/export remains blocked
- delivery remains blocked
- MID tier build unlock generated

Required Nodes:
- HFX_015_PREVIEW_PORTAL_CORE_v004
- HFX_015_PREVIEW_RIM_EMISSION_v004
- HFX_015_PREVIEW_INNER_SURFACE_PROXY_v004
- HFX_015_PREVIEW_DISTORTION_PROXY_v004
- HFX_015_PREVIEW_METADATA_ANCHOR_v004

Required Outputs:
- OUT_PREVIEW_PORTAL_CORE
- OUT_PREVIEW_RIM_EMISSION
- OUT_PREVIEW_INNER_SURFACE_PROXY
- OUT_PREVIEW_DISTORTION_PROXY
- OUT_PREVIEW_METADATA

Test Frames:
[1, 12, 24, 48, 72, 120]

Still Blocked:
- FINAL_CANDIDATE claim
- release seal claim
- production render claim
- delivery
- Hollywood final-pixel portal claim

Next:
HFX_FACTORY_V006_HFX015_PORTAL_RING_MID_TIER_BUILD
