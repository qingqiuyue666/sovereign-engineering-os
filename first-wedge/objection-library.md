# Objection Library

## Purpose

Capture likely buyer objections and bounded responses before discovery.

## Objections

| Objection | What It May Mean | Response | Record |
| --- | --- | --- | --- |
| "We already review code." | They may not see the AI-specific evidence gap. | Ask what changes for AI-assisted code, risk tiering, rollback, and external claims. | Note whether review produces evidence. |
| "We use vendor controls." | They may confuse tool controls with workflow governance. | Acknowledge vendor controls, then map the full workflow from prompt/code to release. | Record vendor dependency. |
| "This sounds like compliance." | They may fear bureaucracy or legal cost. | Clarify this is operational readiness, not certification. | Record compliance trigger. |
| "We are too early." | No trigger or no production path. | Offer a diagnostic only if a 30-90 day trigger exists. | Mark `NO_TRIGGER` if none. |
| "We cannot share code." | Evidence access may be constrained. | Use sanitized artifacts, process maps, screenshots, or metadata if enough for truthful findings. | Record access limit. |
| "Can you implement it too?" | They may want delivery after audit. | Keep audit first; offer implementation support only after acceptance and new scope. | Mark add-on interest. |
| "Can you certify us?" | They need external trust language. | Reject certification claims; provide evidence-backed readiness language only. | Mark `CERTIFICATION_REQUESTED`. |
| "This is too expensive." | Scope, urgency, or value is unclear. | Reconfirm trigger and decision value; reduce scope before discounting. | Log price objection. |
| "We need autonomous execution." | Unsafe or wrong-fit request. | Reject uncontrolled automation and restate governance boundaries. | Mark hard reject. |

## Objection Rules

- Treat objections as market data, not failure.
- Update service-page language only after repeated patterns.
- Do not overpromise to overcome an objection.
- Do not convert certification, ROI, or traction language into sales claims.

## Current Evidence Status

This library is hypothetical until real buyer conversations are logged.
