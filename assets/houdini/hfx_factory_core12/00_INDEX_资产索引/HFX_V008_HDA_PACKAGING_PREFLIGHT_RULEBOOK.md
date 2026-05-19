# HFX v008 HDA Packaging Preflight Rulebook

Status: HFX_V008_HDA_PACKAGING_PREFLIGHT_RULEBOOK_READY

Purpose:
Prepare for actual Houdini Digital Asset packaging without creating or overwriting .hda/.otl files.

v008 is a hard preflight stage.
v009 is the earliest allowed stage for actual HDA file creation.

---

## v008 Scope

v008 creates:

- HDA packaging preflight rulebook
- HDA name registry
- HDA output directory contract
- rollback directory contract
- non-overwrite policy
- wrapper existence checks
- wrapper output alias checks
- README_v007 checks
- README_v008 generation
- v008 validation report

v008 does not create:
- .hda
- .otl
- installed Houdini assets
- overwritten digital asset definitions

---

## HDA Output Directory

Approved future HDA output root:

99_HDA_CANDIDATES/v009_hda_output

Approved rollback root:

99_HDA_CANDIDATES/rollback

Approved v008 preflight root:

99_HDA_CANDIDATES/v008_preflight

---

## Non-Overwrite Rule

v009 must not overwrite an existing .hda/.otl file.

If a target HDA file already exists:
- fail packaging
- write rollback warning
- require explicit new version path

---

## Required v008 Preconditions

Each asset must have:

- v003 HIP
- v007 wrapper HIP
- README_v006
- README_v007
- v007 wrapper validation pass marker
- stable output aliases:
  - OUT_MAIN
  - OUT_RENDER
  - OUT_CACHE
  - OUT_DEBUG
  - OUT_LAYER_* as required

---

## Approved Future HDA Names

- qqy::hfx_energy_trail::9.0
- qqy::hfx_slash_trail::9.0
- qqy::hfx_footstep_dust::9.0
- qqy::hfx_ground_dust_ring::9.0
- qqy::hfx_small_pyro_burst::9.0
- qqy::hfx_ground_crack_debris::9.0
- qqy::hfx_lightning_arc::9.0
- qqy::hfx_energy_shockwave::9.0

---

## v008 Pass Marker

Final pass marker:

HFX_V008_HDA_PACKAGING_PREFLIGHT_PASS
