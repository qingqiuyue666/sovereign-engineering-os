# Migration Map

## Purpose

Classify the existing repository into the SEIS architecture without deleting
useful evidence or pretending legacy assets are complete market proof.

## Scope

Covers the local-first governance/runtime substrate, creative pipeline,
audit reports, validation scripts, docs, examples, policies, and generated
reports present before the SEIS assembly.

## Non-goals

- This is not a permanent deletion plan.
- This does not claim the legacy creative pipeline is the strategic center.
- This does not claim old reports are external market validation.

## Legacy Classification

| Legacy Area | Classification | SEIS Destination | Action |
| --- | --- | --- | --- |
| `kernel/`, `execution_plane/`, `governance/` | Upgrade and integrate | `trusted-delivery/`, `brain/`, `protocol/` | Preserve as runtime/evidence substrate. |
| `docs/audit/`, `reports/audits/`, validation tests | Upgrade and integrate | `trusted-delivery/`, `proof/`, `reports/` | Use as audit and no-fake-success evidence patterns. |
| `creative/`, `assets/houdini/`, `reports/creative/` | Upgrade and integrate with limits | `assets/`, `proof/`, `distribution/` | Treat as delivery/proof examples, not total strategy. |
| `docs/decisions/` historical plans | Archive/deprecate by reference | `archive/`, `reports/legacy-asset-map.md` | Do not delete; mark as historical decision trail. |
| `ROADMAP.md` old creative-only focus | Deprecated/replaced | `EIGHT_ENGINES.md`, `NEXT_ACTIONS.md` | Archive old roadmap, replace root roadmap. |
| Old README narrative | Deprecated/replaced | `README.md`, archive copy | Archive previous README and replace root navigation. |
| Untracked `reports/creative/production_spine_v1/` | Preserve, not owned by this pass | `reports/legacy-asset-map.md` | Leave untouched unless user authorizes. |

## Replacement References

- Strategy: `SEIS_DOCTRINE.md`
- Architecture: `EIGHT_ENGINES.md`
- Market selection: `BATTLEFIELD_SCORECARD.md`
- First wedge: `FIRST_WEDGE_SELECTION.md`
- Runtime trust: `trusted-delivery/README.md`
- Model authority: `BRAIN_GOVERNANCE.md`
- Validation: `VALIDATION_REPORT.md`

## Operating Rules

- Preserve historical evidence unless a separate cleanup pass has explicit
  human approval.
- Archive before replacing root-level strategic narratives.
- Mark old claims as historical where they could be confused with current
  strategy.
- Keep runtime code changes out of this pass.

## Failure Modes

- Deleting useful audit evidence.
- Treating historical readiness reports as market proof.
- Leaving old root navigation to imply the creative pipeline is the whole
  strategy.

## Upgrade Path

Create a future cleanup branch only after the first paid-signal test
identifies which legacy assets are still economically useful.
