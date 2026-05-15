# Personal AI Execution OS Post Completion Roadmap v1

Current verdict: `FINAL_PRODUCT_COMPLETION_READY_FOR_REVIEW`

This roadmap starts after the final product-completion candidate. It does not
authorize runtime activation by itself.

## Next Safe Work

1. Human review of the final product-completion PR.
2. Controlled live smoke design for one runtime at a time.
3. Runtime-specific admission packages for any real activation.
4. Operator runbook for reviewing admission artifacts.
5. Narrow telemetry/audit export for local-only product health reports.

## Deferred Runtime Activation Packages

Each real runtime needs a separate package before activation:

- live model provider smoke:
  - explicit provider config
  - environment-only key check
  - budget ceiling
  - timeout
  - schema validation
  - no tool calls
  - no file edits
- local-only browser smoke:
  - loopback target only
  - action allowlist
  - domain allowlist
  - no login/payment/account creation
  - no credential persistence
- ComfyUI local endpoint smoke:
  - loopback endpoint only
  - workflow/node allowlist
  - no downloads
  - input asset hash binding
- Blender real runtime smoke:
  - no arbitrary Python
  - controlled operation plan only
  - no uncontrolled subprocess
  - source overwrite protection
- Creative software handoff review:
  - continue handoff-first posture for After Effects, Unreal, Houdini,
    ZBrush, Blender, and ComfyUI.

## Still Forbidden By Default

- unrestricted network
- unrestricted subprocess
- unrestricted browser automation
- unrestricted model API calls
- unrestricted creative software control
- model output activating tools directly
- task graph activating real runtime without admission
- CLI flag alone activating real runtime
- secret persistence or logging
- input mutation
- existing user file overwrite

## Product Direction

Keep the system local-first and manifest-bound. Future runtime work should add
one narrow admitted live smoke path at a time, with tests that still pass
without credentials or external services.
