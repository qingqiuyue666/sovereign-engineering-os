# HFX_008 Energy Shockwave MID Tier Validation v006

Status: HFX_008_MID_TIER_VALIDATION_V006_READY

Asset:
- HFX_008 Energy Shockwave

Tier:
- MID

Quality Claim:
- MID_LOOKDEV_ONLY

Validated:
- v001 core asset selection
- v002 source resolution
- v003 preview tier build
- v004 preview tier validation
- v005 MID tier build
- MID HIP exists
- required MID nodes exist in manifest
- required support passes are declared
- six-frame cook results all PASS
- render/export remains blocked
- delivery remains blocked
- final quality claim remains blocked
- sealed source mutation forbidden

Required Nodes:
- HFX_008_MID_SHOCKWAVE_CORE_v005
- HFX_008_MID_SUPPORT_PASSES_v005
- HFX_008_MID_EMISSION_MASK_PROXY_v005
- HFX_008_MID_DISTORTION_MASK_PROXY_v005
- HFX_008_MID_ZDEPTH_PROXY_v005

Required Support Passes:
- OUT_MID_DUST_CONTACT_PROXY
- OUT_MID_EMISSION_MASK_PROXY
- OUT_MID_DISTORTION_MASK_PROXY
- OUT_MID_ZDEPTH_PROXY

Still Not Allowed:
- Hollywood final-quality claim
- final-pixel render claim
- delivery-ready claim
- production EXR output claim

Allowed Next:
HFX_PRODUCTION_UPGRADE_V007_HFX008_FINAL_TIER_BUILD
