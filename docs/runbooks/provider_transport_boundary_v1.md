# Provider Transport Boundary v1

## Purpose
Bounded local-only provider transport boundary. Validates provider
transport requests without making real provider calls.

## Boundaries
- no live provider execution
- no unknown provider
- no missing capability token
- no missing evidence binding
- no secret material
- no network execution in v1
- no production autonomy
- no real provider calls in v1

## Operations
1. validate_provider_transport_request — structural validation
2. validate_provider_capability_boundary — token validation
3. validate_provider_transport_preflight — preflight checks
4. produce_provider_transport_receipt — full receipt production

## Scope
Contract-only. Does not make any provider calls.
