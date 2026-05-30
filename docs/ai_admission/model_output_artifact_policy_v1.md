# Model Output Artifact Policy V1

## Purpose

Model output must become a bounded artifact before it can influence repository
work. The artifact records proposal evidence, not authority.

## Artifact Requirements

- model output artifact
- response receipt binding
- prompt provenance binding
- digest of sanitized output
- no raw provider response persistence
- no PASS status without validation evidence

## Patch Boundary

The model output artifact may suggest a patch. It must not apply a patch. A
patch requires human approval and validation before PR.

## Failure Behavior

Malformed, oversized, secret-bearing, or authority-claiming output is
quarantined and cannot enter the evidence trace as accepted work.
