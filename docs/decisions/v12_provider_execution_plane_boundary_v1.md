# Decision: V12 Provider Execution Plane Boundary (v1)

## Status
Accepted — provider execution plane boundary implemented, default disabled.

## Decision
Implement provider execution plane, adapter registry, and execution receipt as deterministic boundary validators. No real provider calls, no network access.

## Consequences
- Provider execution requires explicit authorization descriptor
- No live provider calls permitted through this boundary
- Production autonomy remains gated
