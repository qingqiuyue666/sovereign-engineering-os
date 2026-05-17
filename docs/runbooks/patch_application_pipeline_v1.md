# Patch Application Pipeline v1

## Purpose
Bounded local-only patch application pipeline. Validates patch requests
without applying them to the real repository.

## Boundaries
- no freeform shell
- no git mutation
- no main mutation
- no absolute paths
- no path traversal
- no forbidden roots
- no deployment
- no production execution
- no real patch application in v1

## Operations
1. validate_patch_application_request — structural validation
2. classify_patch_risk — risk classification
3. validate_patch_allowlist — allowlist enforcement
4. validate_patch_preflight — preflight checks
5. produce_patch_application_receipt — full receipt production

## Scope
Contract-only. Does not implement production runtime behavior.
