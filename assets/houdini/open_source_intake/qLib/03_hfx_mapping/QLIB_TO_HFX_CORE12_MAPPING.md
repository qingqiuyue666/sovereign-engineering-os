
# qLib to HFX Core12 Mapping v1

## Intake Position

qLib is treated as an upstream procedural Houdini asset library candidate.

It is not production-imported by default.

## Useful For

- HDA structure study

- SOP-level procedural pattern review

- parameter interface design

- backwards-compatible asset organization

- VEX/multithreaded pattern study

- production-compatible tool design

## Candidate HFX Mapping

| HFX Area | qLib Use |

|---|---|

| HFX_008 Energy Shockwave | procedural geometry utilities, attribute handling, falloff/mask patterns |

| HFX_015 Portal Ring | curve/surface/procedural shaping references |

| HFX_016 Heat Distortion | attribute/noise/mask patterns |

| HFX_021 Pyro Explosion | support utilities only; not direct pyro replacement |

| HFX_025 Character Energy Field | attribute fields, group utilities, procedural masking |

| HFX_027 Summoning Portal Gate | curve/surface utilities and interface design |

| HFX_028 Space Rift Tear | procedural fracture/shape patterns if present |

| HFX_033 Glow Emission Pass | attribute/pass preparation references |

| HFX_036 Alpha Holdout Matte | group/mask utilities |

| HFX_037 Lightwrap Rim Interaction | pass/mask preparation references |

| HFX_038 Contact Shadow Ground Integration | ground mask / contact support references |

## Copy Policy

Direct copy into HFX production folders is blocked until:

1. license reviewed

2. candidate asset identified

3. dependency reviewed

4. interface mapped

5. clean-room rebuild or wrapper plan written

6. preview test passed

7. shot-bound validation passed

## Current Status

Status: intake_only

Production use: blocked

HFX direct merge: blocked

Clean-room adaptation: allowed after review

