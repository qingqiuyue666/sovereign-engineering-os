
# Film FX Reference Rulebook

Purpose:

Use Hollywood-grade FX structure as the target language for Houdini template upgrades.

Do not build random effects. Build layered, film-readable, reusable FX systems.

---

## 01 Motion Trail / Speedline / Afterimage

Reference language:

- Super-speed movement

- Sword slash arcs

- Energy drag

- Residual motion ghosts

- Air disturbance around fast motion

Film targets:

- The Flash / Quicksilver style speed trails

- Tron Legacy energy trails

- Star Wars lightsaber energy smear

- anime-inspired slash arcs adapted to realistic comp

Houdini layers:

1. Core motion curve

2. Tapered trail surface

3. Particle spark leakage

4. Secondary ghost trail

5. Noise breakup

6. Velocity attribute

7. Alembic/BGEO export

Unreal layers:

1. Fast preview trail

2. Character motion reference

3. Camera timing

4. Real-time glow helper

Comp layers:

1. Glow

2. Motion blur

3. Chromatic edge

4. Grain integration

5. Lens response

Upgrade target:

HFX_001 and HFX_002 v002 must add animated reveal, width falloff, sparks, velocity, and material emission groups.

---

## 02 Dust / Smoke / Ground Haze

Reference language:

- Dust must stay physically grounded.

- Heavy dust moves slowly.

- Fine dust floats longer.

- Contact point must feel weighty.

- Dust should have density variation, not uniform fog.

Film targets:

- Dune

- Mad Max: Fury Road

- John Wick impact dust

- The Batman low atmospheric haze

Houdini layers:

1. Contact dust

2. Radial dust ring

3. Fine suspended particles

4. Low ground fog

5. Turbulence breakup

6. VDB density export

7. Shadow/contact matte

Unreal layers:

1. Ground scene preview

2. Rough shockwave timing

3. Simple dust helper if needed

Comp layers:

1. Depth fade

2. Shadow contact

3. Color match to ground

4. Grain

5. Camera shake

Upgrade target:

HFX_003 and HFX_004 v002 must add frame-trigger timing, density falloff, micro dust, wind drift, and shadow/contact pass.

---

## 03 Fire / Explosion / Pyro

Reference language:

- Explosion is layered: flash, flame, smoke, debris, shockwave, residual plume.

- Fire core should be fast and hot.

- Smoke should lag and roll.

- Debris and dust must sell scale.

Film targets:

- Oppenheimer

- Dunkirk

- The Dark Knight

- Transformers

- Man of Steel

Houdini layers:

1. Ignition flash source

2. Flame core

3. Smoke shell

4. Temperature field

5. Density field

6. Ember particles

7. Shockwave dust

8. VDB export

Unreal layers:

1. Rough fire timing preview

2. Environment lighting reference

3. Secondary real-time glow only

Comp layers:

1. Exposure flash

2. Heat shimmer

3. Glow/bloom

4. Smoke color grading

5. Lens dirt

Upgrade target:

HFX_005 v002 must move toward real Pyro Solver or at least structured VDB fields: density, temperature, flame, smoke.

---

## 04 Ground Crack / Debris / Destruction

Reference language:

- Impact point drives crack direction.

- Pieces must vary in scale.

- Large pieces move slower.

- Small debris moves faster.

- Dust must interact with fracture.

Film targets:

- Man of Steel

- Avengers battle impacts

- Godzilla / Pacific Rim heavy contact

- Doctor Strange ground/space deformation language

Houdini layers:

1. Crack curve

2. Fracture pattern

3. Debris pieces

4. Secondary small debris

5. Dust emission from fracture

6. RBD-ready velocity attributes

7. ABC/BGEO export

Unreal layers:

1. Ground material preview

2. Environment collision reference

3. Camera shake timing

Comp layers:

1. Ground shadow

2. Dust integration

3. Debris motion blur

4. Contact darkening

Upgrade target:

HFX_006 v002 must add real fracture chunks, debris hierarchy, velocity attributes, and optional RBD sim hooks.

---

## 05 Energy / Lightning / Portal / Shockwave

Reference language:

- Energy must have core, glow, particles, flicker, and lens response.

- Lightning must branch and vary thickness.

- Shockwave should have structure, not just a flat ring.

- Portal energy should have edge instability and internal motion.

Film targets:

- Doctor Strange portals

- Thor lightning

- Iron Man repulsor

- Tron Legacy light language

- Star Wars energy blade glow

Houdini layers:

1. Core curve/ring

2. Branch arcs

3. Particle sparks

4. Soft glow geometry

5. Noise instability

6. Animated flicker

7. Emission groups

8. ABC/BGEO export

Unreal layers:

1. Portal shell / scene preview

2. Real-time glow helper

3. Camera interaction

4. Background lighting reference

Comp layers:

1. Bloom

2. Lens flare

3. Chromatic edge

4. Distortion

5. Interactive light

Upgrade target:

HFX_007 and HFX_008 v002 must add animated flicker, endpoint sparks, emission groups, and comp-friendly ID groups.

---

## Global Production Rules

1. Do not build one-layer effects.

2. Every reusable FX template needs:

   - input control

   - parameter controls

   - output node

   - cache node

   - export node

   - README

   - versioning

3. Houdini owns physical FX.

4. Unreal owns preview, environment, camera, and real-time helper layers.

5. DaVinci/AE/Nuke own final comp and image response.

6. v001 is structure.

7. v002 is parameterized.

8. v003 is preview/caching.

9. v004 is film-look integration.

10. v005 is stable reusable asset/HDA candidate.

