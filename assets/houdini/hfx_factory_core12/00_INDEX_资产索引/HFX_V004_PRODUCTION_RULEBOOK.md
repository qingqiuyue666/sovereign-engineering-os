# HFX v004 Production Rulebook

Status: HFX_V004_PRODUCTION_RULEBOOK_READY

Purpose:
Move the HFX library from animated templates into long-term production assets.

v001:
- Base node skeleton.

v002:
- Hollywood reference layering.

v003:
- Trigger-frame time evolution.

v004:
- Production packaging layer.
- Material/lookdev intent.
- Flipbook preview contract.
- Cache/export discipline.
- Solver upgrade route.
- Shot integration rules.
- Reusable asset readiness.

---

## Global v004 Production Standard

Every v004 HFX asset must define:

1. Lookdev Intent
   - Core material behavior
   - Glow/emission behavior
   - Smoke/dust/fire surface language
   - Comp usage expectations

2. Preview Contract
   - Camera name
   - Suggested frame range
   - Flipbook output folder
   - Preview naming convention

3. Cache Contract
   - BGEO cache path
   - VDB cache path where relevant
   - ABC export path where relevant
   - Full effect output
   - Separated comp outputs

4. Solver Upgrade Route
   - Whether the current asset is procedural proxy or solver-ready
   - What the next true solver should be:
     - POP
     - Pyro
     - RBD
     - Vellum
     - FLIP
     - Hair / Guide Groom
   - What inputs are required for solver integration

5. Shot Integration Rule
   - What real footage element this asset attaches to
   - What frame should trigger the effect
   - What scale should be checked
   - What comp passes must be separated

6. Failure Rules
   - If there is no trigger frame, do not export.
   - If scale is unknown, do not final-cache.
   - If output layer nodes are missing, fail validation.
   - If asset contains video/course/archive pollution, fail validation.
   - If README_v004 is missing, fail validation.

---

## Asset v004 Targets

### HFX_001_Energy_Trail_Basic
v004 target:
- Add material intent for core/glow/ghost/sparks.
- Add flipbook preview contract.
- Add real input curve replacement route.
- Add velocity/motion-vector validation route.

Solver upgrade:
- Not solver-first.
- Optional POP spark trail.
- Curve input should drive trail.

Shot integration:
- Attach to hand/weapon/body motion path.
- Trigger frame = motion start.
- Export separated core/glow/ghost/sparks.

---

### HFX_002_Slash_Trail_Curve
v004 target:
- Add material intent for blade glow, hot cut, afterimage, sparks.
- Add flipbook preview contract.
- Add collision spark burst route.
- Add real input curve replacement route.

Solver upgrade:
- Not solver-first.
- Optional POP sparks.
- Collision burst optional.

Shot integration:
- Attach to weapon/hand swing.
- Trigger frame = slash start.
- Export separated core/glow/hotcut/afterimage/sparks.

---

### HFX_003_Footstep_Dust_Impact
v004 target:
- Add dust material intent.
- Add VDB render/comp notes.
- Add POP dust upgrade route.
- Add collision proxy input route.
- Add flipbook preview contract.

Solver upgrade:
- Procedural VDB proxy now.
- Next: POP-advection + collision proxy.
- Optional Pyro sparse smoke for high-end dust.

Shot integration:
- Attach to foot contact/landing contact.
- Trigger frame = contact frame.
- Export VDB dust and contact shadow.

---

### HFX_004_Ground_Dust_Ring
v004 target:
- Add dust ring material intent.
- Add VDB render/comp notes.
- Add debris-driven emission route.
- Add flipbook preview contract.

Solver upgrade:
- Procedural VDB proxy now.
- Next: POP advected ring dust.
- Optional Pyro sparse dust.

Shot integration:
- Attach to heavy landing / punch ground / explosion impact.
- Trigger frame = impact.
- Export VDB ring dust and shadow matte.

---

### HFX_005_Small_Pyro_Burst
v004 target:
- Add fire/smoke/ember material intent.
- Add real Pyro Solver upgrade route.
- Add temperature/fuel/velocity field route.
- Add heat shimmer/distortion pass route.
- Add flipbook preview contract.

Solver upgrade:
- Procedural VDB proxy now.
- Next: Pyro Solver.
- Required fields:
  - density
  - temperature
  - flame
  - vel
  - optional fuel

Shot integration:
- Attach to ignition/explosion frame.
- Trigger frame = ignition.
- Export flame VDB, smoke VDB, embers, shadow.

---

### HFX_006_Ground_Crack_Debris
v004 target:
- Add rock/concrete material intent.
- Add true RBD fracture route.
- Add collision proxy route.
- Add debris-driven dust route.
- Add flipbook preview contract.

Solver upgrade:
- Procedural debris proxy now.
- Next: RBD Material Fracture + Bullet.
- Required inputs:
  - ground mesh
  - impact point
  - fracture radius
  - collision proxy

Shot integration:
- Attach to impact foot/fist/object.
- Trigger frame = impact.
- Export debris ABC/BGEO, cracks, shadow.

---

### HFX_007_Lightning_Arc_Basic
v004 target:
- Add emission material intent.
- Add endpoint constraint route.
- Add camera-facing glow card route.
- Add distortion pass route.
- Add flipbook preview contract.

Solver upgrade:
- Not solver-first.
- Optional POP sparks.
- Endpoint nulls should drive main arc.

Shot integration:
- Attach endpoints to hand/weapon/portal/object.
- Trigger frame = energy activation.
- Export core, branches, sparks separately.

---

### HFX_008_Energy_Shockwave
v004 target:
- Add emission material intent.
- Add distortion ring pass route.
- Add alpha-card glow route.
- Add flipbook preview contract.
- Add comp ID group policy.

Solver upgrade:
- Not solver-first.
- Optional POP edge sparks.
- Optional volume distortion proxy.

Shot integration:
- Attach to impact origin.
- Trigger frame = impact / energy burst.
- Export core ring, glow, streaks, sparks separately.

---

## v004 Validation Standard

Validation must check:

- v003 HIP exists.
- README_v003 exists.
- README_v004 exists.
- v004 production spec exists.
- Critical OUT nodes exist in v003 HIP.
- 00_preview exists.
- 02_cache exists.
- 04_export exists.
- No video files.
- No archive files.
- No .DS_Store.
- No ._* files.

Final pass marker:

HFX_V004_PRODUCTION_SPEC_PASS
