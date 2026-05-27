# Approval Runtime Contract V1

This change adds a contract-only approval runtime admission boundary. It ties a
human-invoked approval request, a human-attested operator decision, WAL evidence,
artifact evidence, snapshot/replay evidence, risk decision evidence, and optional
operator receipt evidence into a deterministic admission receipt.

The contract is intentionally narrow. It does not persist decisions, open a
review UI, schedule work, execute commands, call providers, launch browsers,
perform DCC or MCP actions, or read environment state.

## Guarantees

- All request, decision, and admission receipts are digest-only.
- `created_at`, `decided_at`, and `admitted_at` are metadata and excluded from
  deterministic hashes.
- Human invocation and human attestation are required.
- Production autonomy and live execution flags must remain false.
- Approval only permits `next_manual_stage_allowed`.
- Rejection requires a rollback plan hash and yields `rollback_required`.
- Deferral yields `human_review_pending`.
- WAL record hashes and prior WAL head hashes are bindings only; no storage is
  implemented in this PR.

## Fail-Closed Rejections

The contract rejects malformed digests, mismatched request/decision identities,
wrong requested action for a final decision, missing rollback evidence for a
rejection, raw stdout/stderr, raw prompt/content/payload/path fields, secret-like
fields, execution material, provider responses, browser/DCC/MCP fields, and any
attempt to enable production autonomy or live execution.

## Deferred Work

Persistent approval runtime storage, read-only review UI integration, WAL-backed
append, artifact store binding, snapshot store binding, and system acceptance
must land only after their prerequisite contract and storage PRs are merged.
