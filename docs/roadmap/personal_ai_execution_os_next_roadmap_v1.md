# Personal AI Execution OS Next Roadmap v1

Date: 2026-05-15

Current landing verdict: `PARTIAL_LANDING_READY_WITH_DEFERRED_ITEMS`

## Roadmap Principles

- Local-first boundary remains the default.
- Readiness is not authorization.
- Authorization is not execution.
- Default deny and fail closed remain mandatory.
- Real runtime admission requires explicit future policy, tests, manifests,
  provenance, and human review.

## Next Review Packages

1. Full landing PR review and merge decision.
2. Runtime deferral audit after merge.
3. Local launcher usability review with real local sample folders.
4. Task graph schema review before any broader orchestration work.
5. Delivery package replay and artifact sensitivity review.

## Future Candidate Work

- Live model provider admission design, still disabled by default.
- Real browser runtime admission design with Playwright/Selenium still disabled
  until policy, allowlist, evidence, and credential controls are accepted.
- ComfyUI local endpoint admission design with loopback-only policy and no
  external downloads by default.
- Blender runtime admission design with no arbitrary Python and operation-plan
  allowlists.
- Creative software adapter admission designs for After Effects, Unreal,
  Houdini, and ZBrush.
- Stronger package replay tooling and offline audit reports.
- More realistic local fixture galleries for office, browser, model, and
  creative workflows.

## Non-Goals Until Explicitly Authorized

- No unrestricted network runtime.
- No unrestricted subprocess runtime.
- No OS automation runtime.
- No real browser automation by default.
- No live model API runtime by default.
- No real creative software control by default.
- No secret storage.
- No source asset overwrite.
- No input mutation.
