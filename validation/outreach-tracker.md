# Outreach Tracker

## Purpose

Track outreach activity and keep market evidence separate from activity
volume.

## Tracker

| Date | Target | Role | Channel | Message Variant | Trigger Hypothesis | Response | Next Step | Status | Evidence Link |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
|  |  |  |  |  |  |  |  | not sent / sent / replied / booked / rejected / no decision |  |

## Status Definitions

- `sent`: message delivered.
- `replied`: human response received.
- `booked`: discovery call scheduled.
- `rejected`: target or SEIS rejected fit.
- `no decision`: no active next step.

## Evidence Rules

- A sent message is not market proof.
- A reply is not paid signal.
- A booked call is not commitment.
- A rejected target is useful evidence when reason is recorded.

## Required Capture

For each response, capture:

- role
- trigger confirmed or rejected
- buyer/budget path if known
- objection
- next step
- evidence access possibility

## Update Targets

Use repeated response patterns to update:

- `first-wedge/outreach-message-bank.md`
- `first-wedge/service-page-draft.md`
- `validation/buyer-objection-log.md`
- `validation/pricing-feedback-log.md`
