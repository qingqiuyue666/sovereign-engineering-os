# Branch Consolidation Plan — 2026-06-15

## Current Main State

Main has already merged PR #576:
CONTROLLED_AUTONOMOUS_ENGINEERING_OS_FULL_STACK_OPERATION_READY.

Main also contains the branch retention audit and local creative archive ignore rules.

## Decision

Do not delete the remaining long-lived branches yet.

They contain unmerged strategic, protocol, validation, productization, and delivery assets.

## Branch Classification

### agent-operating-protocol-v1

Classification: KEEP_AND_EXTRACT_PROTOCOL_ASSETS

Reason:
- Contains AOOS schemas, templates, playbooks, and agent operating protocol materials.
- Likely useful for future control-plane / AOOS documentation.
- Not safe to delete.

Next action:
- Extract reusable protocol assets into main through a dedicated PR.
- After extraction, mark the branch as archived or superseded.

### seis-real-world-validation-continuous-v1

Classification: KEEP_FOR_EXTERNAL_VALIDATION_STAGE

Reason:
- Contains buyer validation, outreach, pricing test, objection handling, target list, and close-loss materials.
- Directly relevant to the next real-world commercial validation stage.
- Not safe to delete.

Next action:
- Use as source for the next real-world validation PR.
- Do not delete before extraction.

### seis-16-stage-strategic-os-v1

Classification: AUDIT_FOR_SUPERSESSION_BY_PR_576

Reason:
- Contains 16-stage strategic OS materials, stop-building validation gate, and validation command layer.
- May be partially superseded by PR #576, but this has not been proven file-by-file.

Next action:
- Compare strategic materials against current main.
- Extract only unique strategic gates if still useful.
- Delete only after documented supersession.

### seis-9-step-continuous-execution-v1

Classification: KEEP_PRODUCTIZATION_AND_DELIVERY_ASSET_LIBRARY

Reason:
- Contains app, assets, delivery loops, first wedge, productization, validation, trusted delivery, market, proof, and protocol materials.
- This is a large productization and delivery asset branch, not a throwaway branch.
- Not safe to delete.

Next action:
- Split into smaller extraction PRs:
  1. productization assets
  2. validation assets
  3. delivery-loop templates
  4. first-wedge materials
  5. app/workbench concepts

## Deletion Policy

Blocked:
- No direct `git branch -D`.
- No direct `git push origin --delete`.
- No deletion based only on branch age.
- No deletion until each branch is either:
  - merged,
  - extracted,
  - archived,
  - or explicitly superseded by main.

## Recommended Next PR Stack

1. Protocol extraction PR from `agent-operating-protocol-v1`.
2. Real-world validation extraction PR from `seis-real-world-validation-continuous-v1`.
3. Productization asset extraction PR from `seis-9-step-continuous-execution-v1`.
4. Supersession audit PR for `seis-16-stage-strategic-os-v1`.

## Final Recommendation

Keep all four branches.
Proceed with extraction, not deletion.
