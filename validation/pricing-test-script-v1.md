# Pricing Test Script V1

Status label: `PRICING_TEST_SCRIPT_READY`

Repository status: `SEIS_REAL_WORLD_VALIDATION_READY`

Real-world status: `HUMAN_ACTION_REQUIRED`

## Purpose

Test price sensitivity without claiming validated pricing until a real buyer
accepts, rejects, negotiates, or pays in a recorded context.

## Price Ladder Hypothesis

These are hypotheses only:

| Offer | Initial hypothesis | Evidence required |
| --- | --- | --- |
| Diagnostic | low/free to small paid | Buyer accepts or rejects a short workflow diagnosis. |
| Bounded delivery | small paid pilot | Buyer accepts or rejects one workflow scope with price. |
| Maintenance | monthly support if workflow is used | Buyer accepts or rejects upkeep after seeing workflow value. |

## Diagnostic Price Test

Use after the target confirms a real workflow but before full scope.

Script:

"For a first diagnostic, I would review one workflow, map the risk boundary,
and return a fit/no-fit note plus a scope recommendation. I am testing whether
that is worth a small paid diagnostic or should stay free during validation.
Would you pay for that? If yes, what range feels reasonable? If no, why?"

Record:

- accepted / rejected / no decision
- price range
- reason
- budget owner
- limitation

## First Delivery Price Test

Use only after workflow, evidence access, and acceptance criteria are clear.

Script:

"For the first bounded delivery, the scope would be one workflow only:
current-state map, risk tier, human confirmation points, implementation
options, SOP, evidence package, handoff, failure handling, and rollback rule.
No automatic payments, account changes, secret handling, or external messages
without approval. If this were priced as a small paid pilot, what range would
you consider acceptable?"

Record:

- accepted / rejected / countered / deferred
- price range
- scope concerns
- risk concerns
- discount request
- approval path

## Maintenance Price Test

Use only after the buyer says the workflow would keep changing or need support.

Script:

"If the workflow is used, maintenance could cover monthly review, small SOP
updates, failure log review, checklist changes, and evidence cleanup. Would
monthly support be useful, or would you prefer one-time handoff only?"

Record:

- one-time only
- monthly support interest
- expected update frequency
- price reaction
- owner

## Objection Recording Rules

Every price objection must record:

- exact offer version
- quoted or discussed range
- buyer role
- budget path
- objection reason
- whether scope was too broad
- whether risk boundary was unclear
- next action

## Discount Rules

- Reduce scope before lowering price.
- Do not discount to buy fake validation.
- Do not call a free project paid signal.
- If discounting, record the reason and what was removed.
- Do not promise ROI or guarantee outcome to overcome price objection.

## Reduce Scope Instead Of Price When

- buyer wants fewer deliverables
- evidence access is limited
- risk is higher than expected
- buyer needs proof before larger spend
- workflow is low volume
- maintenance need is unknown

## Paid Signal

Counts as paid signal:

- payment received
- signed paid scope
- written paid pilot approval
- equivalent high-commitment record with buyer, date, scope, timeline, and
  evidence access

Does not count as paid signal:

- friendly interest
- praise
- a free call
- a meeting with no next step
- "send me details"
- internal excitement
- unpaid advice
- fake or generated buyer response
