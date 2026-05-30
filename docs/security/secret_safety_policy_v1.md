# Secret Safety Policy V1

## Policy

SEOS evidence must not include real secrets. Operators and AI workers must not
read, print, copy, inspect, persist, summarize, or exfiltrate credential values.

Forbidden material includes `.env` content, API keys, cloud tokens, SSH private
keys, cookies, browser session values, keychain values, private model-provider
tokens, and raw private prompts.

## Required Handling

- Use secret references instead of secret values.
- Use digests for evidence that depends on private material.
- Redact logs before failure bundle creation.
- Reject or quarantine secret-like fields in task, receipt, context, replay, and
  audit artifacts.
- Do not ask an AI worker to recover, infer, reveal, or transform secrets.

## Validation

Validated by `python3 scripts/secret_context_safety_check_v1.py` and existing
secret scanner coverage.
