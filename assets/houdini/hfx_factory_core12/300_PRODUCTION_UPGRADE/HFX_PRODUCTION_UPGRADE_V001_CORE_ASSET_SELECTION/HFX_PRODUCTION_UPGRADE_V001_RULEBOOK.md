# HFX Production Upgrade v001 Rulebook

Status: HFX_PRODUCTION_UPGRADE_V001_RULEBOOK_READY

Purpose:
Convert the existing Houdini long-term asset library from preview/proxy-level assets into production-upgrade candidates.

This stage does not run high-density simulation.
This stage does not render.
This stage does not modify sealed releases.

Core doctrine:
- Existing Batch 01-05 final seals are immutable.
- Existing assets are valid foundation assets, not final Hollywood-quality outputs.
- Upgrade work must be isolated under 300_PRODUCTION_UPGRADE.
- Every upgraded asset must have PREVIEW / MID / FINAL quality tiers.
- FINAL quality requires shot context, camera, scale, colorspace, cache policy, pass manifest, render policy and comp validation.
- EXR pass separation is required.
- Comp flattening before review is forbidden.
- Real-world final claims require real plate/camera or explicitly approved synthetic final context.

Quality tier definition:

PREVIEW:
- fast
- cheap
- used for blocking and timing
- never sold as final quality

MID:
- medium-density
- good enough for lookdev and some short-form tests
- may generate preview comp
- not final-pixel unless explicitly validated

FINAL:
- high-density or production-resolved
- shot-bound
- cached
- rendered with declared engine and colorspace
- EXR passes separated
- comp validated
- delivery reviewed

V002 should not upgrade all assets at once.
V002 must select one asset first, recommended:
HFX_008 Energy Shockwave.
