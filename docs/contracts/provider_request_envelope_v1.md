# Provider Request Envelope V1

## Purpose

`provider_request_envelope_v1` describes the bounded envelope that would be
required before any provider request is considered. In the current readiness
scope it is contract evidence only and does not authorize live provider calls.

## Required Fields

- `contract_version`: must be `provider_request_envelope_v1`.
- `request_id`: stable request envelope identifier.
- `task_id`: task associated with the request.
- `provider_ref`: provider identifier or disabled provider reference.
- `model_ref`: model identifier or disabled model reference.
- `payload_digest`: digest of sanitized request payload.
- `dry_run`: must be true for this readiness scope.
- `operator_approved`: boolean approval binding.

## Optional Fields

- `approval_ref`: repository-relative approval receipt reference.
- `policy_ref`: repository-relative provider policy reference.
- `created_at`: metadata timestamp excluded from deterministic hashes.

## Version

The only valid version for this contract is `provider_request_envelope_v1`.

## Immutability Rule

Accepted provider request envelopes must not be mutated. Any change requires a
new request id and a new digest.

## Unknown Field Policy

Consumers must reject unknown fields and fail closed before any provider request
can be admitted.

## Compatibility Rule

Compatible readers may add optional policy references only when dry-run status,
approval binding, and payload digest remain unchanged.

## Migration/Deprecation Rule

Migration requires a new contract version and a deterministic mapping from old
request ids to new request ids.

## Valid Example

```json
{
  "contract_version": "provider_request_envelope_v1",
  "request_id": "provider-req-readiness-001",
  "task_id": "task-readiness-001",
  "provider_ref": "disabled_provider",
  "model_ref": "disabled_model",
  "payload_digest": "sha256:9999999999999999999999999999999999999999999999999999999999999999",
  "dry_run": true,
  "operator_approved": true
}
```

## Invalid Example

```json
{
  "contract_version": "provider_request_envelope_v1",
  "request_id": "provider-req-readiness-001",
  "task_id": "task-readiness-001",
  "provider_ref": "live_provider",
  "payload": "raw provider prompt",
  "dry_run": false,
  "operator_approved": false
}
```

The invalid example contains raw payload material, disables dry-run mode, and
lacks operator approval.

## Failure Behavior

Validation must fail closed and prevent provider transport from being invoked.
