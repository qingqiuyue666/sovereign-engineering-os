# Audit Log Export V1

Status: `implemented_local`

This export contract defines a local audit packet for demos, pilots, and
reviewers.

## Export Inputs

- `reports/control-plane/evidence-ledger-v1.jsonl`
- `reports/control-plane/failure-ledger-v1.jsonl`
- `reports/control-plane/first-controlled-cycle-v1.json`
- `reports/control-plane/real-world-validation-tracker-v1.json`
- `reports/control-plane/external-evidence-ledger-v1.json`
- `reports/control-plane/non-claim-audit-v1.json`
- `reports/control-plane/final-scorecard-v1.json`

## Export Fields

Each exported event should include run id, task id, operation id, trace id,
stage, classifier output, policy decision, command summary, file paths, check
result, failure reason when applicable, evidence links, and claim boundary.

## Redaction Rules

Do not export secrets, raw credentials, customer private data, private local
machine paths, unapproved source material, or raw prompt/tool instructions that
contain attacker-controlled content. Export summaries and hashes where needed.

## Buyer Packet

The buyer packet may include the allowed local commercial claim and must include
the unsupported claim list plus external blockers.

