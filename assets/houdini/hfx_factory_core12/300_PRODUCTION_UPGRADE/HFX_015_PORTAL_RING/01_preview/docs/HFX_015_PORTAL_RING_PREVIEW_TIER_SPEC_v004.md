# HFX_015 Portal Ring PREVIEW Tier Spec v004

Status: HFX_015_PORTAL_RING_PREVIEW_TIER_SPEC_V004_READY

Asset:
- HFX_015 Portal Ring

Tier:
- PREVIEW

Purpose:
Fast portal ring layout, timing, scale, radial composition, rim emission, inner-surface proxy, and placeholder distortion.

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

Blocked:
- MID lookdev claim
- FINAL_CANDIDATE claim
- production render claim
- Hollywood final-pixel claim
- delivery

Next:
HFX_FACTORY_V005_HFX015_PORTAL_RING_PREVIEW_TIER_VALIDATION
