# Provider Response Receipt V1

## Purpose

`provider_response_receipt_v1` records digest-only response evidence for a
provider request. It does not store raw provider responses and does not claim a
live provider call occurred.

## Required Fields

- `contract_version`: must be `provider_response_receipt_v1`.
- `response_receipt_id`: stable response receipt identifier.
- `request_id`: provider request envelope identifier.
- `task_id`: task associated with the request.
- `response_digest`: digest of sanitized response evidence.
- `status`: `accepted`, `rejected`, or `not_executed`.
- `raw_response_stored`: must be false.

## Optional Fields

- `provider_metadata_digest`: digest of bounded provider metadata.
- `failure_id`: failure bundle identifier for rejected responses.
- `created_at`: metadata timestamp excluded from deterministic hashes.

## Version

The only valid version for this contract is `provider_response_receipt_v1`.

## Immutability Rule

Accepted provider response receipts must not be mutated. Corrections require a
new response receipt id.

## Unknown Field Policy

Consumers must reject unknown fields and fail closed before treating a provider
response as accepted evidence.

## Compatibility Rule

Compatible readers may add optional metadata digests only when request binding,
status, response digest, and raw-response policy remain unchanged.

## Migration/Deprecation Rule

Migration requires a new contract version and a deterministic mapping for old
response receipt ids.

## Valid Example

```json
{
  "contract_version": "provider_response_receipt_v1",
  "response_receipt_id": "provider-resp-readiness-001",
  "request_id": "provider-req-readiness-001",
  "task_id": "task-readiness-001",
  "response_digest": "sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "status": "not_executed",
  "raw_response_stored": false
}
```

## Invalid Example

```json
{
  "contract_version": "provider_response_receipt_v1",
  "response_receipt_id": "provider-resp-readiness-001",
  "request_id": "provider-req-readiness-001",
  "task_id": "task-readiness-001",
  "response": "raw response body",
  "status": "accepted",
  "raw_response_stored": true
}
```

The invalid example stores a raw response and marks raw response storage as
true.

## Failure Behavior

Validation must fail closed and prevent the response from entering evidence
trace or replay flows.
