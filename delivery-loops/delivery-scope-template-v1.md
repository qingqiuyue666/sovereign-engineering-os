# Delivery Scope Template V1

Status label: `DELIVERY_SCOPE_TEMPLATE_READY`

Repository status: `SEIS_REAL_WORLD_VALIDATION_READY`

Real-world status: `HUMAN_ACTION_REQUIRED`

## Scope Record

```text
date:
target identifier:
workflow owner:
workflow name:
workflow trigger:
accepted scope:
explicit exclusions:
inputs:
outputs:
tools/files:
data sensitivity:
risk tier:
human confirmation points:
evidence access:
acceptance criteria:
failure criteria:
rollback method:
maintenance expectation:
price/commitment status:
limitations:
```

## Required Before Delivery

Delivery may not start until these are known:

- workflow owner
- one workflow name
- accepted scope
- explicit exclusions
- risk tier
- human confirmation points
- evidence access
- acceptance criteria
- rollback method

## Explicit Exclusions

Add exclusions directly to each scope record:

- no payment automation
- no account changes
- no secret handling
- no platform-rule bypass
- no unapproved production changes
- no final external messages without human review
- no ROI, certification, or case-study claim before evidence

## Scope Change Rule

If scope changes, create a new scope record or append a dated change note.
Do not silently expand the first delivery beyond one workflow.
