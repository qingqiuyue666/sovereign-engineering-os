# Evidence To Asset Conversion V1

Status label: `EVIDENCE_TO_ASSET_CONVERSION_READY`

Repository status: `SEIS_REAL_WORLD_VALIDATION_READY`

Real-world status: `HUMAN_ACTION_REQUIRED`

## Purpose

Define how real evidence becomes reusable SEIS assets without converting
assumptions or empty templates into proof.

## Conversion Map

| Evidence source | Possible asset | Required condition |
| --- | --- | --- |
| accepted workflow delivery | SOP | Reviewer accepts the workflow steps and limitations. |
| accepted workflow delivery | template | The output can be reused without private data. |
| discovery transcript/notes | script | A real question produced useful buyer/workflow evidence. |
| delivery checklist | checklist | The checklist was used or accepted in a real workflow. |
| objection | objection record | A real target raised the objection. |
| pricing feedback | pricing memory | A real buyer accepted, rejected, countered, or deferred a price. |
| failure record | failure rule | A real or attempted delivery produced a failure or near miss. |
| before/after evidence | benchmark | Baseline and after state are both recorded with limitations. |
| accepted delivery | case library entry | Buyer/operator accepts a privacy-safe case summary. |
| tool issue | tool reliability record | A real workflow exposed tool behavior, limitation, or failure. |

## Asset Rules

Every asset must include:

- source
- date
- actor or privacy-safe identifier
- workflow
- claim supported
- limitation
- reuse condition
- confidence
- next use

## Non-Assets

Do not convert these into assets:

- empty templates
- hypothetical examples
- generated testimonials
- generic praise
- internal speculation
- unapproved private data
- one-off output with no reuse condition

## Registry Targets

Use existing registries when evidence exists:

- `assets/sop-registry.md`
- `assets/template-registry.md`
- `assets/prompt-registry.md`
- `assets/objection-library.md`
- `assets/pricing-history.md`
- `assets/failure-library.md`
- `assets/benchmark-history.md`
- `assets/case-library.md`
- `assets/tool-reliability-records.md`

Do not populate registries with fake records.
