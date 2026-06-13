# Failure And Rollback Template V1

Status label: `FAILURE_ROLLBACK_TEMPLATE_READY`

Repository status: `SEIS_REAL_WORLD_VALIDATION_READY`

Real-world status: `HUMAN_ACTION_REQUIRED`

## Failure Record

```text
date:
target identifier:
workflow:
failure type:
what failed:
where detected:
impact:
evidence:
immediate action:
rollback action:
human reviewer:
root cause hypothesis:
what must change:
asset or rule update:
claim limitation:
status:
```

## Failure Types

- wrong workflow selected
- evidence access missing
- output inaccurate
- output incomplete
- risk boundary unclear
- data sensitivity too high
- account/platform risk too high
- buyer approval missing
- price or budget mismatch
- unsafe request
- maintenance burden too high

## Immediate Action

When failure appears:

1. stop expanding scope
2. notify the workflow owner
3. preserve non-sensitive evidence
4. return to prior manual process where possible
5. record limitation
6. decide retry, rescope, defer, or reject

## Rollback Methods

Possible rollback:

- prior manual checklist
- prior file naming convention
- prior spreadsheet format
- prior report process
- prior approval process
- no-change handoff

Rollback must not require hidden credentials or unapproved system access.

## Claim Boundary

A failure record can become a failure rule or risk control. It cannot become a
success case.
