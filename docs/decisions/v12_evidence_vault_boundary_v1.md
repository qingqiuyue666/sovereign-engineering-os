# Decision: V12 Evidence Vault Boundary (v1)

## Status
Accepted — evidence vault boundary implemented, default disabled.

## Decision
Implement evidence vault boundary, receipt, and protected storage interface as deterministic validators only. No real encryption, KMS, or key material.

## Consequences
- Vault operations require explicit policy change to enable
- Human approval required before future real vault execution
