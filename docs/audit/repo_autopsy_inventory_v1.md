# Repo Autopsy Inventory V1

Repo Autopsy Inventory V1 is a static classification framework for existing
repository modules. It records execution value, evidence value, risk reduction
value, use case linkage, pressure levels, and pruning or archive candidacy.

This framework does not delete files, move files, archive files, rewrite the
repository, run scans that mutate the filesystem, call the network, launch
creative tools, or execute commands.

## Categories

- `CORE_RUNTIME`
- `EVIDENCE_SPINE`
- `RISK_BOUNDARY`
- `APPROVAL_BOUNDARY`
- `DRY_RUN_SUPPORT`
- `GOVERNANCE_POLICY`
- `TEST_INFRASTRUCTURE`
- `DOCS_EXPLANATORY`
- `USE_CASE_LINKED`
- `CANDIDATE_ASSET`
- `PRUNE_CANDIDATE`
- `ARCHIVE_CANDIDATE`
- `UNKNOWN`

## Scoring

Execution value, evidence value, risk reduction value, runtime pressure, test
pressure, and external pressure use the same scale:

- `NONE`
- `LOW`
- `MEDIUM`
- `HIGH`

## Record Rules

- `CORE_RUNTIME` requires execution value above `NONE`.
- `EVIDENCE_SPINE` requires evidence value above `NONE`.
- `RISK_BOUNDARY` requires risk reduction value above `NONE`.
- A core runtime record cannot silently be marked as a prune candidate.
- An archive candidate requires `prune_reason` or `archive_reason`.
- A module with no use case IDs and no runtime pressure is review-required.
- Record content hashes exclude `last_reviewed_at`.

## Intended Use

Future PRs can populate this inventory with reviewed records. The inventory is
evidence for simplification and execution closure, not a deletion mechanism.
