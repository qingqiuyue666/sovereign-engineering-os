# Audit Packet V1

## Purpose

`audit_packet_v1` groups bounded evidence for human review. It links claims,
contracts, validation commands, and residual risks without self-certifying
external recognition.

## Required Fields

- `contract_version`: must be `audit_packet_v1`.
- `packet_id`: stable audit packet identifier.
- `scope`: bounded review scope.
- `git_head`: reviewed commit.
- `claim_matrix_ref`: repository-relative claim matrix reference.
- `evidence_refs`: non-empty list of repository-relative evidence references.
- `external_review_required`: must be true.

## Optional Fields

- `validation_commands`: list of command/result records.
- `residual_risks`: bounded residual risks.
- `created_at`: metadata timestamp excluded from deterministic hashes.

## Version

The only valid version for this contract is `audit_packet_v1`.

## Immutability Rule

Accepted audit packets must not be mutated. A corrected packet requires a new
packet id and a link to the superseded packet.

## Unknown Field Policy

Consumers must reject unknown fields and fail closed before treating an audit
packet as ready for review.

## Compatibility Rule

Compatible readers may add optional validation metadata only when scope, git
head, claim matrix reference, and evidence references remain stable.

## Migration/Deprecation Rule

Migration requires a new contract version and a deterministic mapping from old
packet ids to new packet ids.

## Valid Example

```json
{
  "contract_version": "audit_packet_v1",
  "packet_id": "audit-packet-readiness-001",
  "scope": "global recognition readiness external review input",
  "git_head": "bbbe7a688f579c807bbd0ee5716f9a82c77adab8",
  "claim_matrix_ref": "reports/audits/claim_to_evidence_matrix_v1.json",
  "evidence_refs": [
    "docs/audits/claim_to_evidence_matrix_v1.md",
    "scripts/contract_check_v1.py"
  ],
  "external_review_required": true
}
```

## Invalid Example

```json
{
  "contract_version": "audit_packet_v1",
  "packet_id": "audit-packet-readiness-001",
  "scope": "self certified final recognition",
  "git_head": "bbbe7a688f579c807bbd0ee5716f9a82c77adab8",
  "evidence_refs": [],
  "external_review_required": false
}
```

The invalid example self-certifies readiness, omits the claim matrix, and has no
evidence references.

## Failure Behavior

Validation must fail closed and keep the packet out of external-review handoff
until required evidence and review boundaries are present.
