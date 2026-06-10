# AI Context Bundle V1

## Purpose

`ai_context_bundle_v1` describes the sanitized context packet that may be shown
to an AI worker. It carries digests and redaction metadata, not raw secrets or
hidden private state.

## Required Fields

- `contract_version`: must be `ai_context_bundle_v1`.
- `bundle_id`: stable context bundle identifier.
- `task_id`: task associated with the bundle.
- `context_digest`: digest of sanitized context.
- `redaction_policy`: policy used to remove unsafe material.
- `secret_values_present`: must be false.
- `created_at`: metadata timestamp excluded from deterministic hashes.

## Optional Fields

- `token_budget`: bounded token budget metadata.
- `source_refs`: repository-relative source references.
- `omission_digests`: digests for intentionally omitted material.

## Version

The only valid version for this contract is `ai_context_bundle_v1`.

## Immutability Rule

Accepted context bundles must not be mutated. A refreshed context requires a new
bundle id and new digest.

## Unknown Field Policy

Consumers must reject unknown fields and fail closed before exposing context to
an AI worker.

## Compatibility Rule

Compatible readers may add optional token metadata only when the context digest
and redaction policy remain stable.

## Migration/Deprecation Rule

Migration requires a new contract version and a mapping from old bundle ids to
new bundle ids.

## Valid Example

```json
{
  "contract_version": "ai_context_bundle_v1",
  "bundle_id": "ctx-readiness-001",
  "task_id": "task-readiness-001",
  "context_digest": "sha256:8888888888888888888888888888888888888888888888888888888888888888",
  "redaction_policy": "ai_context_firewall_v1",
  "secret_values_present": false,
  "created_at": "2026-05-30T00:04:00Z"
}
```

## Invalid Example

```json
{
  "contract_version": "ai_context_bundle_v1",
  "bundle_id": "ctx-readiness-001",
  "task_id": "task-readiness-001",
  "context": "raw private context",
  "redaction_policy": "none",
  "secret_values_present": true
}
```

The invalid example exposes raw context and admits secret values.

## Failure Behavior

Validation must fail closed and prevent the bundle from being handed to an AI
worker.
