# HFX_015 Portal Ring Production Upgrade Spec v001

Status: HFX_PRODUCTION_UPGRADE_V001_CORE_ASSET_SELECTED

- Batch: B02
- Priority: P0
- Upgrade Class: portal_energy_ring
- Current Level: PREVIEW_PROXY
- Target Level: PRODUCTION_FINAL

## Why Core

High-value visual motif for travel, reveal, summon, anime/film transition shots.

## Required Disciplines

- particles
- volumes
- curves
- shader
- distortion
- EXR_passes
- comp

## PREVIEW Goal

readable ring structure with timing control

## MID Goal

layered portal edge, sparks, internal turbulence, glow pass

## FINAL Goal

dense portal with volumetric edge, internal distortion, sparks, lightwrap, holdout, emission and comp-ready EXR passes

## Required Outputs

- beauty_proxy
- emission_mask
- distortion_mask
- rim_light
- alpha_holdout
- metadata_manifest

## Blocked Until

- shot_center_declared
- camera_declared
- colorspace_declared
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
