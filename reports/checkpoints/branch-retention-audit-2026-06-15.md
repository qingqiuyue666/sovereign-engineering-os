
# Branch Retention Audit — 2026-06-15

## Current Decision

Do not delete the remaining long-lived branches yet.

## Branches

### agent-operating-protocol-v1

Decision: KEEP_PROTOCOL_ASSETS

Reason:

- Contains AOOS schemas.

- Contains AOOS templates.

- Contains AOOS playbooks.

- Contains AOOS evidence/report fixtures.

- Contains agent operating protocol materials.

Next action:

- Audit for extraction into main control-plane / AOOS documentation.

- Do not delete until protocol assets are either merged, superseded, or archived.

### seis-real-world-validation-continuous-v1

Decision: KEEP_NEXT_VALIDATION

Reason:

- Contains real-world validation workflows.

- Contains buyer validation materials.

- Contains outreach, pricing, objection-handling, close-loss, and target-list materials.

- Directly relevant to the next external validation stage.

Next action:

- Use as candidate source for the next real-world validation PR.

- Do not delete.

### seis-16-stage-strategic-os-v1

Decision: AUDIT_SUPERSEDED_BY_576

Reason:

- Contains 16-stage strategic OS and validation command layer materials.

- May be partially superseded by PR #576, but this is not proven yet.

Next action:

- Compare against current `CONTROLLED_AUTONOMOUS_ENGINEERING_OS_FULL_STACK_OPERATION_READY` mainline.

- Delete only if all useful strategic materials are superseded or archived.

### seis-9-step-continuous-execution-v1

Decision: KEEP_PRODUCTIZATION_ASSETS

Reason:

- Contains app, assets, delivery-loops, governance, market, product, proof, protocol, validation, and trusted-delivery materials.

- Large productization/asset-compounding branch.

- Not safe to delete without extraction audit.

Next action:

- Audit for productization assets.

- Potentially split into smaller PRs or archive as source material.

## Delete Policy

Allowed:

- Delete only branches proven merged, superseded, or archived.

Blocked:

- No `git branch -D`.

- No `git push origin --delete`.

- No remote branch deletion until extraction/supersession is documented.

## Current Recommendation

Keep all four branches for now.

Proceed with targeted extraction or archive audit later.

