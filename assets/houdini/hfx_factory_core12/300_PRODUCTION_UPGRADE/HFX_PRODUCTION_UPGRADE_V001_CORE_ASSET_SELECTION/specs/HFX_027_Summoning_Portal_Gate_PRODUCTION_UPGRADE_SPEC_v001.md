# HFX_027 Summoning Portal Gate Production Upgrade Spec v001

Status: HFX_PRODUCTION_UPGRADE_V001_CORE_ASSET_SELECTED

- Batch: B04
- Priority: P0
- Upgrade Class: summoning_gate
- Current Level: PREVIEW_PROXY
- Target Level: PRODUCTION_FINAL

## Why Core

Strong fantasy/anime cinematic motif; combines environment, portal, glow, particles and comp.

## Required Disciplines

- curves
- particles
- volumes
- shader
- runes
- EXR_passes
- comp

## PREVIEW Goal

gate silhouette and timing proxy

## MID Goal

animated gate with sparks/runes/glow

## FINAL Goal

shot-ready summoning gate with layered energy, volumetric edge, runes, emission, distortion, z-depth and contact integration

## Required Outputs

- emission_mask
- rune_mask
- distortion_mask
- zdepth
- contact_shadow
- metadata_manifest

## Blocked Until

- gate_position_locked
- camera_declared
- shot_scale_declared

## Hard Rules

- Do not modify existing final sealed releases directly.
- Upgrade work must live under 300_PRODUCTION_UPGRADE.
- PREVIEW is not FINAL.
- FINAL requires shot/camera/colorspace/pass/caching validation.
- EXR pass separation is required for final.
- Comp flattening before review is forbidden.

Next Stage:
HFX_PRODUCTION_UPGRADE_V002_SINGLE_ASSET_SOURCE_RESOLUTION
