# Supported Software Matrix V3

The supported surface is contract-first. Houdini and ComfyUI now have optional
approval-gated local smoke runners. Blender, After Effects, DaVinci Resolve,
Unreal Engine, and ZBrush are covered by optional adapter contracts that report
readiness and next proof requirements without claiming execution support.

## Operating Boundary

- Local-first execution is the default.
- Private assets stay out of tracked public artifacts.
- Long render, simulation, generation, and DCC jobs require budget gates and default to dry-run plans.
- External adoption is recorded only from real verifiable URLs and real actors.

## Validation

Run `python3 scripts/creative_total_check_v3.py`, `make creative-comfyui-runner-check`,
`make creative-houdini-runner-check`, and
`make creative-optional-adapter-contracts-check` before public release.

## Evidence

Evidence is repository-local, schema-backed, and fixture-backed unless a real external signal is explicitly recorded.

## Residual Risk

Live DCC installations, paid asset licenses, and real community adoption require human or external confirmation.
