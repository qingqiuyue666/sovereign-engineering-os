# HFX_016 Heat Distortion Production Upgrade Spec v001

Status: HFX_PRODUCTION_UPGRADE_V001_CORE_ASSET_SELECTED

- Batch: B02
- Priority: P0
- Upgrade Class: refraction_heat_haze
- Current Level: PREVIEW_PROXY
- Target Level: PRODUCTION_FINAL

## Why Core

Required support layer for fire, explosion, shockwave, portal and high-energy shots.

## Required Disciplines

- VOP/VEX
- noise_fields
- vector_pass
- EXR_passes
- comp

## PREVIEW Goal

visible heat mask preview

## MID Goal

animated distortion vector proxy with falloff controls

## FINAL Goal

comp-stable refraction vector pass with z-depth gating, matte control, edge falloff and non-color EXR export contract

## Required Outputs

- distortion_vector
- heat_mask
- falloff_mask
- zdepth_gate
- metadata_manifest

## Blocked Until

- plate_or_synthetic_context_declared
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
