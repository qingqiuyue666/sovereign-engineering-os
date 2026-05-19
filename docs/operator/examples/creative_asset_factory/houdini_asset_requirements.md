# Houdini Asset Requirements

## Allowed Role

Houdini role: particle / VDB / field assets only.

## Requirements

- Define particle behaviors that support the motivated transition.
- Define VDB or field assets that support the hero frame.
- Keep the asset list deterministic and reviewable.

## Forbidden

- No Houdini execution.
- No hython execution.
- No subprocess launch.
- No tool launching from this repository slice.

## Review Note

These are requirements only and do not authorize simulation execution.
