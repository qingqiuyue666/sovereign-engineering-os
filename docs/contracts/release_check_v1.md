# Release Check V1

## Purpose

`release_check_v1` records a bounded release-readiness check. It tracks local
validation and protected tag evidence without publishing a release or claiming
external approval.

## Required Fields

- `contract_version`: must be `release_check_v1`.
- `release_check_id`: stable release check identifier.
- `git_head`: checked commit.
- `release_candidate_tag`: checked tag.
- `tag_target`: peeled tag target.
- `validation_results`: non-empty list of command result objects.
- `external_review_required`: must be true.

## Optional Fields

- `blockers`: list of open blockers.
- `residual_risks`: list of bounded residual risks.
- `created_at`: metadata timestamp excluded from deterministic hashes.

## Version

The only valid version for this contract is `release_check_v1`.

## Immutability Rule

Accepted release checks must not be mutated. A later check must create a new
release check id.

## Unknown Field Policy

Consumers must reject unknown fields and fail closed before using a release
check as readiness evidence.

## Compatibility Rule

Compatible readers may add optional risk fields only when git head, tag, tag
target, and validation results remain stable.

## Migration/Deprecation Rule

Migration requires a new contract version and a deterministic mapping for old
release check ids.

## Valid Example

```json
{
  "contract_version": "release_check_v1",
  "release_check_id": "release-check-readiness-001",
  "git_head": "bbbe7a688f579c807bbd0ee5716f9a82c77adab8",
  "release_candidate_tag": "v0.1.0-rc3",
  "tag_target": "9a363f95b85602ffc598db463dc6181a9bbbdf3c",
  "validation_results": [
    {
      "command": "make ci",
      "result": "passed"
    }
  ],
  "external_review_required": true
}
```

## Invalid Example

```json
{
  "contract_version": "release_check_v1",
  "release_check_id": "release-check-readiness-001",
  "git_head": "bbbe7a688f579c807bbd0ee5716f9a82c77adab8",
  "release_candidate_tag": "v0.1.0-rc3",
  "validation_results": [],
  "external_review_required": false
}
```

The invalid example omits the tag target, has no validation results, and claims
external review is not required.

## Failure Behavior

Validation must fail closed, keep release status blocked, and avoid publishing a
release or success statement.
