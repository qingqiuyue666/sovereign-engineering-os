# HFX_037 LightWrap Rim Interaction Production Upgrade Spec v001

Status: HFX_PRODUCTION_UPGRADE_V001_CORE_ASSET_SELECTED

- Batch: B05
- Priority: P0
- Upgrade Class: cg_live_action_edge_integration
- Current Level: SUPPORT_PROXY
- Target Level: PRODUCTION_SUPPORT_FINAL

## Why Core

Key to making CG/Houdini FX feel integrated with real footage instead of pasted on top.

## Required Disciplines

- lightwrap
- rim
- edge_detection
- comp
- colorspace

## PREVIEW Goal

basic rim mask

## MID Goal

separated rim/edge spill/backlight pass

## FINAL Goal

shot-ready lightwrap with controllable rim softness, spill intensity, backlight interaction and ACES-safe comp handoff

## Required Outputs

- rim_mask
- edge_spill
- backlight_interaction
- wrap_alpha
- metadata_manifest

## Blocked Until

- plate_declared
- colorspace_declared
- comp_target_declared

## Hard Rules

- Do not modify existing final sealed releases directly.
- Upgrade work must live under 300_PRODUCTION_UPGRADE.
- PREVIEW is not FINAL.
- FINAL requires shot/camera/colorspace/pass/caching validation.
- EXR pass separation is required for final.
- Comp flattening before review is forbidden.

Next Stage:
HFX_PRODUCTION_UPGRADE_V002_SINGLE_ASSET_SOURCE_RESOLUTION
