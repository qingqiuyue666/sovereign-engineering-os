# Buyer Budget Trigger Scorecard

Status label: `BUYER_BUDGET_TRIGGER_SCORECARD_READY`

Repository status: `SEIS_REAL_WORLD_VALIDATION_READY`

Real-world status: `HUMAN_ACTION_REQUIRED`

## Purpose

Score whether a target is real-world validation quality before spending time
on delivery design.

Use 0-3 for each category:

- 0: absent or unknown
- 1: weak
- 2: plausible
- 3: strong

## Scorecard

| Dimension | 0 | 1 | 2 | 3 |
| --- | --- | --- | --- | --- |
| pain intensity | no pain | annoyance only | recurring cost or error | urgent pain with clear consequence |
| frequency | one-off | monthly or unclear | weekly | daily or high-volume weekly |
| budget access | none | unknown | approver reachable | buyer can approve or strongly influence spend |
| authority | no influence | user only | workflow owner | buyer/operator owns change |
| urgency | no trigger | vague interest | near-term pressure | deadline, backlog, audit, campaign, or error trend |
| evidence access | none | limited verbal notes | sanitized artifacts possible | before/after evidence approved |
| risk tolerance | unsafe expectations | high-risk only | safe if bounded | accepts human review and exclusions |
| repeatability | one-off custom | partly repeated | repeated workflow | repeatable across similar targets |
| asset potential | no reusable output | weak template | SOP/checklist likely | case, SOP, template, and failure rule likely |
| delivery feasibility | not feasible | unclear | feasible with constraints | clear one-workflow delivery possible |

## Interpretation

| Total | Meaning | Action |
| ---: | --- | --- |
| 0-9 | invalid or too weak | close, defer, or request missing facts |
| 10-17 | weak validation | keep as learning, do not deliver yet |
| 18-24 | viable discovery | continue discovery and price test |
| 25-30 | strong delivery candidate | prepare bounded delivery scope if evidence access is accepted |

## Required Notes

Every score must include:

- target identifier
- scorer
- date
- evidence source
- limitation
- next action

No score is market proof by itself.
