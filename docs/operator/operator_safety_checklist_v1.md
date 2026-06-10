# Operator Safety Checklist V1

Before approving a task or PR, the operator must confirm:

- the task scope is explicit and bounded
- no secret values are included in objectives, receipts, context, or reports
- evidence references exist and are repository-relative
- failed commands do not print fake PASS output
- replay status does not claim reconstruction without evidence
- proposed AI output is review-only until a human accepts it
- dependency or CI changes are explained and minimal
- `v0.1.0-rc3` is not moved, deleted, recreated, or retagged
- no local path markers are introduced into public docs
- residual risks and known limitations are documented

This checklist is not runtime authority. It is human review evidence.
