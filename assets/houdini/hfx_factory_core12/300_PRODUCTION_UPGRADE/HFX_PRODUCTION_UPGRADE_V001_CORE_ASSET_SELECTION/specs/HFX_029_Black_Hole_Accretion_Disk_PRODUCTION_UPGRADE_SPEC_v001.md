# HFX_029 Black Hole Accretion Disk Production Upgrade Spec v001

Status: HFX_PRODUCTION_UPGRADE_V001_CORE_ASSET_SELECTED

- Batch: B04
- Priority: P0
- Upgrade Class: black_hole_gravity_lens
- Current Level: PREVIEW_PROXY
- Target Level: PRODUCTION_FINAL

## Why Core

Visually premium but requires strict comp/render control; strong short-form hero shot potential.

## Required Disciplines

- particles
- volumes
- shader
- distortion
- lighting
- EXR_passes
- comp

## PREVIEW Goal

readable disk and gravity center

## MID Goal

animated accretion disk with emission and distortion masks

## FINAL Goal

hero black-hole FX with accretion disk, lens distortion, emission, depth separation, bloom control and comp-ready passes

## Required Outputs

- emission_mask
- distortion_vector
- disk_mask
- zdepth
- bloom_source
- metadata_manifest

## Blocked Until

- camera_declared
- shot_scale_declared
- render_engine_declared

## Hard Rules

- Do not modify existing final sealed releases directly.
- Upgrade work must live under 300_PRODUCTION_UPGRADE.
- PREVIEW is not FINAL.
- FINAL requires shot/camera/colorspace/pass/caching validation.
- EXR pass separation is required for final.
- Comp flattening before review is forbidden.

Next Stage:
HFX_PRODUCTION_UPGRADE_V002_SINGLE_ASSET_SOURCE_RESOLUTION
