# Token ROI V1

## Purpose

`token_roi_v1` records deterministic local token-use evidence for a proposed AI
route. It helps compare bounded routes without invoking a live provider.

## Required Fields

- `contract_version`: must be `token_roi_v1`.
- `roi_id`: stable token ROI receipt identifier.
- `task_id`: task associated with the estimate.
- `route`: local deterministic route name.
- `input_tokens`: non-negative integer input token count.
- `output_tokens`: non-negative integer output token count.
- `decision`: bounded route decision.

## Optional Fields

- `savings_estimate_digest`: digest of an estimate explanation.
- `budget_ref`: repository-relative budget reference.
- `created_at`: metadata timestamp excluded from deterministic hashes.

## Version

The only valid version for this contract is `token_roi_v1`.

## Immutability Rule

Accepted token ROI receipts must not be mutated. A changed estimate requires a
new `roi_id`.

## Unknown Field Policy

Consumers must reject unknown fields and fail closed before using a token ROI
receipt as routing evidence.

## Compatibility Rule

Compatible readers may add optional budget references only when route, counts,
and decision remain stable.

## Migration/Deprecation Rule

Migration requires a new contract version and a documented mapping for old ROI
ids.

## Valid Example

```json
{
  "contract_version": "token_roi_v1",
  "roi_id": "roi-readiness-001",
  "task_id": "task-readiness-001",
  "route": "deterministic_local_first",
  "input_tokens": 120,
  "output_tokens": 60,
  "decision": "local_route_preferred"
}
```

## Invalid Example

```json
{
  "contract_version": "token_roi_v1",
  "roi_id": "roi-readiness-001",
  "task_id": "task-readiness-001",
  "route": "live_provider_now",
  "input_tokens": -1,
  "output_tokens": 60,
  "decision": "execute_live"
}
```

The invalid example uses a live-provider route, a negative token count, and an
execution decision outside this contract.

## Failure Behavior

Validation must fail closed and avoid selecting any provider or execution route
from a malformed estimate.
