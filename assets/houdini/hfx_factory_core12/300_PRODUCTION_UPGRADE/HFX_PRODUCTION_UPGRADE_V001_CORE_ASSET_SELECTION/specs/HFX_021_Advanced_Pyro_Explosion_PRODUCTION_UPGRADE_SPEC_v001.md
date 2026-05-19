# HFX_021 Advanced Pyro Explosion Production Upgrade Spec v001

Status: HFX_PRODUCTION_UPGRADE_V001_CORE_ASSET_SELECTED

- Batch: B03
- Priority: P0
- Upgrade Class: hero_pyro_explosion
- Current Level: PREVIEW_PROXY
- Target Level: PRODUCTION_FINAL

## Why Core

Highest cinematic value but also highest simulation/render cost; must be upgraded through strict quality tiers.

## Required Disciplines

- Pyro
- Sparse volumes
- VDB
- shader
- lighting
- cache
- EXR_passes
- comp

## PREVIEW Goal

cheap timing/shape explosion proxy

## MID Goal

medium-resolution pyro with temperature/density/fire mask passes

## FINAL Goal

high-resolution cached pyro with separate fire/smoke/heat/distortion/emission/z-depth passes and shot-specific lighting

## Required Outputs

- fire
- smoke
- density
- temperature
- emission
- zdepth
- holdout
- metadata_manifest

## Blocked Until

- sim_scale_locked
- cache_budget_declared
- render_engine_declared
- shot_camera_locked

## Hard Rules

- Do not modify existing final sealed releases directly.
- Upgrade work must live under 300_PRODUCTION_UPGRADE.
- PREVIEW is not FINAL.
- FINAL requires shot/camera/colorspace/pass/caching validation.
- EXR pass separation is required for final.
- Comp flattening before review is forbidden.

Next Stage:
HFX_PRODUCTION_UPGRADE_V002_SINGLE_ASSET_SOURCE_RESOLUTION
