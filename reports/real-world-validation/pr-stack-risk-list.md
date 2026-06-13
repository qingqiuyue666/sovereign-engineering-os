# PR Stack Risk List

Status date: 2026-06-13

## Migration-Diff Risk

Risk: #573 previously depended on lower stacked branches. After #570, #574,
and #572 were squash-merged into `main`, #573 can show duplicate lower-stack
changes unless the branch is reconciled against current `main`.

Current condition:

- #570 is merged into `main`.
- #574 replaced #571 and is merged into `main`.
- #572 is merged into `main`.
- #573 targets `main` and is the final remaining PR.

Control:

- Merge current `origin/main` into `seis-real-world-validation-continuous-v1`.
- Keep the final PR diff limited to the intended real-world validation
  continuous execution package.
- Do not delete branches or push directly to `main`.

## CI / Canonical-Health Risk

Risk: current status can drift when a lower stacked branch receives a review
commit. A newer lower-branch check must complete before higher stacked PRs can
be considered stable.

Current condition:

- Old #573 `canonical-health` may refer to the pre-migration head.
- A refreshed head requires a new GitHub Actions result.

Control:

- Run the focused local checks before push.
- Push only `seis-real-world-validation-continuous-v1`.
- Wait for GitHub `canonical-health` on the new head.

## Untracked Artifact Risk

Risk: the local checkout contains the known untracked
`reports/creative/production_spine_v1/` tree. Accidentally staging, deleting,
or broadly ignoring it would mix unrelated generated artifacts into this PR.

Control:

- Preserve the directory.
- Stage only files created or modified by this review run.
- Keep any `.gitignore` handling narrow unless explicitly requested.

## Fake-Completion Risk

Risk: validation files can look like proof even when no buyer, pricing,
delivery, adoption, or revenue evidence exists.

Control:

- Keep repository status separate from real-world status.
- Use `HUMAN_ACTION_REQUIRED`, `MARKET_PROOF_PENDING`,
  `REAL_DELIVERY_PENDING`, and `EVIDENCE_PENDING` where evidence is missing.
- Do not write fake case studies, fake testimonials, fake outreach results,
  fake pricing feedback, fake customer commitments, or fake delivery proof.

## Path / Reference Consistency Risk

Risk: older SEOS/runtime paths, new SEIS strategic paths, and prior first-wedge
paths can drift from new real-world validation files.

Control:

- Link the new package to `REAL_WORLD_VALIDATION_COMMAND_LAYER_V1.md`,
  `SEIS_16_STAGE_EXECUTION_GATES.md`, `SEIS_16_STAGE_STATUS.md`,
  `STOP_BUILDING_AND_VALIDATE_GATE.md`, `battlefield/first-wedge-selection.md`,
  `validation/`, `delivery-loops/`, and `assets/`.
- Treat the prior `AI Engineering Production Governance` wedge as the
  secondary/high-trust path for this run, not as validated market proof.

## Merge-Order Recommendation

Only #573 remains. Stop at the human merge gate after the refreshed branch is
clean and GitHub `canonical-health` succeeds.
