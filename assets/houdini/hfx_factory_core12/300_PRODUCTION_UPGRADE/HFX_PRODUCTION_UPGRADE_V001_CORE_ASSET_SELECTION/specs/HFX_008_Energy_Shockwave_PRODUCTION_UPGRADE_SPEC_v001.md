# HFX_008 Energy Shockwave Production Upgrade Spec v001

Status: HFX_PRODUCTION_UPGRADE_V001_CORE_ASSET_SELECTED

- Batch: B01
- Priority: P0
- Upgrade Class: radial_energy_impact
- Current Level: PREVIEW_PROXY
- Target Level: PRODUCTION_FINAL

## Why Core

Most reusable combat/action transition FX; can anchor hero-frame impact shots.

## Required Disciplines

- SOP
- particles
- VDB_optional
- shader
- EXR_passes
- comp

## PREVIEW Goal

fast radial ring with visible timing and scale controls

## MID Goal

layered shockwave with dust/heat/rim/emission passes

## FINAL Goal

cinematic radial impact with distortion, debris/dust coupling, emission, z-depth, contact shadow and compositing passes

## Required Outputs

- beauty_proxy
- emission_mask
- distortion_mask
- zdepth
- contact_shadow
- metadata_manifest

## Blocked Until

- shot_scale_declared
- camera_declared
- frame_range_locked
- pass_manifest_declared

## Hard Rules

- Do not modify existing final sealed releases directly.
- Upgrade work must live under 300_PRODUCTION_UPGRADE.
- PREVIEW is not FINAL.
- FINAL requires shot/camera/colorspace/pass/caching validation.
- EXR pass separation is required for final.
- Comp flattening before review is forbidden.

Next Stage:
HFX_PRODUCTION_UPGRADE_V002_SINGLE_ASSET_SOURCE_RESOLUTION
