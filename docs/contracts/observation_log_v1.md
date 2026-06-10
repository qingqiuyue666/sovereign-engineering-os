# Observation Log V1

## Purpose

`observation_log_v1` records repository observation posture and hard blocker
status. It is an internal evidence log, not external recognition or public
certification.

## Required Fields

- `contract_version`: must be `observation_log_v1`.
- `observation_period_id`: stable observation period identifier.
- `mode`: observation mode.
- `release_candidate_tag`: protected release-candidate tag.
- `main_head`: observed main commit or tag target.
- `current_verdict`: bounded observation verdict.
- `observations`: non-empty list of observation entries.

## Optional Fields

- `allowed_change_classes`: bounded list of allowed change classes.
- `forbidden_change_classes`: bounded list of forbidden change classes.
- `hard_evidence_blocker_types`: bounded blocker taxonomy.

## Version

The only valid version for this contract is `observation_log_v1`.

## Immutability Rule

Accepted observation entries must not be mutated. New observations must append a
new entry or create a new observation log version.

## Unknown Field Policy

Consumers must reject unknown fields and fail closed before using the log as
readiness evidence.

## Compatibility Rule

Compatible readers may accept new optional blocker taxonomy fields only when the
period id, tag, head, verdict, and observations remain valid.

## Migration/Deprecation Rule

Migration requires a new contract version and a mapping from old observation
period ids to new period ids.

## Valid Example

```json
{
  "contract_version": "observation_log_v1",
  "observation_period_id": "REAL_OPERATION_OBSERVATION_PERIOD_V1",
  "mode": "real_operation_observation",
  "release_candidate_tag": "v0.1.0-rc3",
  "main_head": "9a363f95b85602ffc598db463dc6181a9bbbdf3c",
  "current_verdict": "NO_HARD_EVIDENCE_BLOCKER_RECORDED",
  "observations": [
    {
      "result": "Observation mode active."
    }
  ]
}
```

## Invalid Example

```json
{
  "contract_version": "observation_log_v1",
  "observation_period_id": "REAL_OPERATION_OBSERVATION_PERIOD_V1",
  "mode": "complete",
  "release_candidate_tag": "v0.1.0-rc3",
  "current_verdict": "unsupported_final_verdict",
  "observations": []
}
```

The invalid example omits `main_head`, claims an unsupported verdict, and has no
observation entries.

## Failure Behavior

Validation must fail closed and report the log as unusable evidence until the
missing or unsupported fields are corrected.
