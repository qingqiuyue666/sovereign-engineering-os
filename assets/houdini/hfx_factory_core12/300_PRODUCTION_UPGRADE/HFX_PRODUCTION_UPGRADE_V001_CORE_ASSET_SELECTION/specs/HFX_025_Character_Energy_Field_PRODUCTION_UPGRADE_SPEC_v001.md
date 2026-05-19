# HFX_025 Character Energy Field Production Upgrade Spec v001

Status: HFX_PRODUCTION_UPGRADE_V001_CORE_ASSET_SELECTED

- Batch: B04
- Priority: P0
- Upgrade Class: character_aura_energy
- Current Level: PREVIEW_PROXY
- Target Level: PRODUCTION_FINAL

## Why Core

Useful for real person, green-screen, anime-style hero character and cinematic reveal shots.

## Required Disciplines

- particles
- surface_proxy
- shader
- motion_trails
- lightwrap
- holdout
- comp

## PREVIEW Goal

character-centered aura proxy

## MID Goal

layered aura with animated field, sparks and rim interaction

## FINAL Goal

subject-aware energy field with holdout, lightwrap, emission, rim, contact and comp integration passes

## Required Outputs

- emission_mask
- rim_mask
- particle_pass
- alpha_holdout
- lightwrap
- metadata_manifest

## Blocked Until

- subject_proxy_or_plate_declared
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
