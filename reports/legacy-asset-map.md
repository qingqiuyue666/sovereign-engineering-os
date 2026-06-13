# Legacy Asset Map

## Purpose

Classify pre-existing repository assets for SEIS integration.

## Scope

Existing docs, code, tests, governance, creative, reports, and scripts.

## Classification

| Area | Classification | Reason |
| --- | --- | --- |
| `kernel/` | Upgrade and integrate | Runtime/evidence primitives for trusted delivery. |
| `execution_plane/` | Upgrade and integrate | Controlled execution and review artifact patterns. |
| `governance/` | Upgrade and integrate | Approval, audit, policy, security, and worker boundaries. |
| `docs/audit/` | Upgrade and integrate | Evidence-rich audit trail and no-fake-success precedent. |
| `scripts/` and `validation/` | Upgrade and integrate | Local validation gates and repository checks. |
| `creative/` and `reports/creative/` | Upgrade and integrate with limits | Useful proof/delivery examples, not full strategy. |
| `assets/houdini/` | Upgrade and integrate with rights caution | Production assets and validators; not market adoption. |
| `docs/decisions/` | Archive/deprecate by reference | Large historical decision trail with mixed current relevance. |
| Old README and ROADMAP | Archived/replaced | Root strategy needed SEIS navigation. |
| Untracked production spine reports | Preserve | Existing untracked work; not modified by this pass. |

## Operating Rules

- Do not permanently delete in this pass.
- Use archived copies for replaced root docs.
- Future cleanup requires explicit approval and validation.

## Failure Modes

- Useful audit evidence is lost.
- Weak historical strategy remains presented as current.
- Creative pipeline becomes mistaken for the whole SEIS mission.

## Upgrade Path

Create a deprecation index for `docs/decisions/` after the first paid wedge
decision clarifies which historical assets remain useful.
