# Next Decision Gate V1

Status label: `NEXT_DECISION_GATE_READY`

Repository status: `SEIS_REAL_WORLD_VALIDATION_READY`

Real-world status: `HUMAN_ACTION_REQUIRED`

## Purpose

Define what SEIS should do after the first real-world validation attempt.

## Decision Options

| Decision | Use when | Repository update |
| --- | --- | --- |
| continue battlefield | real evidence shows pain, owner, trigger, and safe scope | keep battlefield and refine target list |
| narrow battlefield | pain exists but target segment is too broad | narrow target profile and outreach copy |
| change target segment | wrong roles or weak budget path | update target-list rules |
| change offer | pain exists but scope does not fit | revise delivery package and message |
| lower scope | price/risk too high but workflow is real | reduce deliverables before discounting |
| change pricing | real buyer accepts/rejects/counters price | update pricing hypothesis with limitation |
| pause | evidence is weak or access blocked | record blocker and wait for better target/evidence |
| reject battlefield | repeated evidence shows no pain, budget, trigger, or safe scope | record falsification and choose next battlefield |
| attempt first bounded delivery | accepted scope, evidence access, and review owner exist | create delivery scope and acceptance record |
| repeat validation | evidence is inconclusive but not invalid | run another target batch with revised copy |
| allow internal workbench prototype | repeated real workflow demand needs internal tooling | open explicit prototype decision; do not imply SaaS |
| do not productize yet | default unless repeated delivery evidence exists | keep product/app/protocol gates closed |

## Decision Inputs

Required inputs:

- target list results
- outreach classifications
- discovery notes
- pricing reactions
- buyer/budget/trigger scores
- accepted/rejected scope
- evidence access
- risk boundary
- close/loss review

## Default Decision

Default after this repository run:

`HUMAN_ACTION_REQUIRED`

No further strategy expansion is justified until real evidence exists.
