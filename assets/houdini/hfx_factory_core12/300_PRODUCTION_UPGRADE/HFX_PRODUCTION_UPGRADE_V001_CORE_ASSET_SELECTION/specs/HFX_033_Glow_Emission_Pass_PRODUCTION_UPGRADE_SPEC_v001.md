# HFX_033 Glow Emission Pass Production Upgrade Spec v001

Status: HFX_PRODUCTION_UPGRADE_V001_CORE_ASSET_SELECTED

- Batch: B05
- Priority: P0
- Upgrade Class: compositing_emission_support
- Current Level: SUPPORT_PROXY
- Target Level: PRODUCTION_SUPPORT_FINAL

## Why Core

Required for almost every premium FX shot; improves perceived cinematic quality heavily.

## Required Disciplines

- EXR_passes
- shader
- comp
- colorspace

## PREVIEW Goal

basic emission mask

## MID Goal

separated emission/color bleed/bloom source

## FINAL Goal

ACES-safe emission pass system with bloom source, color bleed, matte gating and shot manifest binding

## Required Outputs

- emission_mask
- color_bleed_mask
- bloom_source
- metadata_manifest

## Blocked Until

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
