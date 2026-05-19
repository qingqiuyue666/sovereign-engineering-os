# HFX_028 Space Rift Tear Production Upgrade Spec v001

Status: HFX_PRODUCTION_UPGRADE_V001_CORE_ASSET_SELECTED

- Batch: B04
- Priority: P0
- Upgrade Class: space_rift_distortion
- Current Level: PREVIEW_PROXY
- Target Level: PRODUCTION_FINAL

## Why Core

High-impact transition and hero-frame FX; pairs with distortion, glow and black-hole style shots.

## Required Disciplines

- curves
- particles
- distortion
- shader
- comp_passes

## PREVIEW Goal

readable tear shape with timing

## MID Goal

animated rift edge with particles and distortion mask

## FINAL Goal

cinematic spatial tear with refraction vectors, edge glow, interior mask, z-depth, lightwrap and comp-ready passes

## Required Outputs

- edge_emission
- distortion_vector
- interior_mask
- alpha_holdout
- zdepth
- metadata_manifest

## Blocked Until

- rift_path_locked
- camera_declared
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
