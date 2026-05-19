# HFX_036 Alpha Holdout Matte Production Upgrade Spec v001

Status: HFX_PRODUCTION_UPGRADE_V001_CORE_ASSET_SELECTED

- Batch: B05
- Priority: P0
- Upgrade Class: live_action_holdout_support
- Current Level: SUPPORT_PROXY
- Target Level: PRODUCTION_SUPPORT_FINAL

## Why Core

Mandatory for real plate / green-screen / Unreal integration where FX must pass behind subjects or objects.

## Required Disciplines

- matte
- holdout
- edge
- comp

## PREVIEW Goal

basic holdout matte

## MID Goal

foreground/occlusion/edge matte separation

## FINAL Goal

production holdout system with edge softness, coverage mask, ID/matte input support and comp-safe EXR outputs

## Required Outputs

- foreground_matte
- occlusion_matte
- edge_matte
- coverage_mask
- metadata_manifest

## Blocked Until

- plate_or_subject_proxy_declared
- camera_declared

## Hard Rules

- Do not modify existing final sealed releases directly.
- Upgrade work must live under 300_PRODUCTION_UPGRADE.
- PREVIEW is not FINAL.
- FINAL requires shot/camera/colorspace/pass/caching validation.
- EXR pass separation is required for final.
- Comp flattening before review is forbidden.

Next Stage:
HFX_PRODUCTION_UPGRADE_V002_SINGLE_ASSET_SOURCE_RESOLUTION
