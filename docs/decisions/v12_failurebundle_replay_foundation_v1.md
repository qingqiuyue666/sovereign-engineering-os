# Decision: V12 Failure Bundle & Replay Foundation (v1)

## Status
Accepted — sanitized failure bundle and deterministic replay foundation implemented.

## Decision
Implement three modules: failure_bundle.py (sanitized, digest-only), replay_plan.py (exact replay only), replay_diff.py (digest comparison with version binding).

## Consequences
- Failure data is sanitized before persistence
- Replay verification is deterministic and bound to version tuples
- No live cloud re-query permitted in exact replay mode
