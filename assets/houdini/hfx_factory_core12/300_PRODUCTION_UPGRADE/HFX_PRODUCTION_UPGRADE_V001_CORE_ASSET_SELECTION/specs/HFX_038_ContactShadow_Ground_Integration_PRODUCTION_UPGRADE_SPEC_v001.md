# HFX_038 ContactShadow Ground Integration Production Upgrade Spec v001

Status: HFX_PRODUCTION_UPGRADE_V001_CORE_ASSET_SELECTED

- Batch: B05
- Priority: P0
- Upgrade Class: grounding_contact_support
- Current Level: SUPPORT_PROXY
- Target Level: PRODUCTION_SUPPORT_FINAL

## Why Core

Required to stop FX from floating; crucial for grounded cinematic believability.

## Required Disciplines

- matte
- shadow
- ground_proxy
- comp
- lighting

## PREVIEW Goal

basic ground/contact matte

## MID Goal

ground matte + foot/contact/falloff masks

## FINAL Goal

production contact-shadow support with ground proxy, falloff control, object/FX contact masks and comp-safe shadow pass

## Required Outputs

- ground_matte
- foot_contact
- fx_contact_mask
- contact_shadow
- falloff_mask
- metadata_manifest

## Blocked Until

- ground_plane_declared
- camera_declared
- scale_declared

## Hard Rules

- Do not modify existing final sealed releases directly.
- Upgrade work must live under 300_PRODUCTION_UPGRADE.
- PREVIEW is not FINAL.
- FINAL requires shot/camera/colorspace/pass/caching validation.
- EXR pass separation is required for final.
- Comp flattening before review is forbidden.

Next Stage:
HFX_PRODUCTION_UPGRADE_V002_SINGLE_ASSET_SOURCE_RESOLUTION
