# AI Context Safety Policy V1

## Policy

AI context bundles must be bounded, sanitized, digest-bound, and proposal-first.
They must not carry secrets, raw provider responses, browser state, hidden
private context, or execution authority.

## Required Controls

- approval is required before execution receipts
- context bundles must record `raw_file_contents_included: false` when only
  digests are included
- provider calls are disabled unless admitted by a later explicit gate
- provider response poisoning is controlled by digest-only response receipts
- prompt injection in objectives must remain inert text
- token ROI and budget metadata must not select a live provider by itself

## Validation

Validated by `python3 scripts/secret_context_safety_check_v1.py`,
`python3 scripts/adversarial_smoke_v1.py`, and `python3 scripts/contract_check_v1.py`.
