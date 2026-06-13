# Outreach Log Template V1

Status label: `OUTREACH_LOG_TEMPLATE_READY`

Repository status: `SEIS_REAL_WORLD_VALIDATION_READY`

Real-world status: `HUMAN_ACTION_REQUIRED`

## Purpose

Record real outreach attempts and responses without storing secrets or
unnecessary personal data.

## Record Format

Copy this block for each real outreach event.

```text
date:
channel:
target identifier:
message variant:
response:
classification:
evidence quality:
next action:
limitations:
```

## Field Rules

- `date`: Use the actual date sent or received.
- `channel`: Record broad channel only, such as email, WeChat, DM, intro, or
  in-person.
- `target identifier`: Use the privacy-safe ID from `validation/target-list-v1.md`.
- `message variant`: Use a variant name from `validation/outreach-message-pack-v1.md`.
- `response`: Use a short summary unless explicit quotation is necessary and
  approved.
- `classification`: Use `validation/outreach-response-classifier.md`.
- `evidence quality`: weak, medium, strong, rejection, no-decision, invalid,
  or non-signal.
- `next action`: Discovery, details, follow-up, close, referral, reject unsafe,
  or no action.
- `limitations`: Record what the response does not prove.

## Empty State

No outreach has been performed by this repository run.

Current evidence status:

`OUTREACH_NOT_STARTED`

## Privacy Boundary

Do not record:

- personal phone numbers
- private email addresses unless explicitly approved
- payment details
- credentials
- secrets
- private keys
- browser cookies
- raw customer datasets
- sensitive customer messages

Use privacy-safe identifiers and summaries.
