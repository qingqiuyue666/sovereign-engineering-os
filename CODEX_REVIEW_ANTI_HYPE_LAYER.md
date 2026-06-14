# Codex Review And Anti-Hype Layer

Layer id: `REVIEW_ANTI_HYPE_LAYER`

## Purpose

Force conservative language for maturity, benchmarks, production readiness,
runtime enforcement, observability, independent review, and final platform
claims.

## Connected Loop

review/anti-hype -> final report

The review layer feeds the scorecard, table-review residue closure,
real-world proof gap ledger, and final report.

## Evidence Gate

- Final report must include explicit non-claim wording.
- Unsupported maturity claims must be downgraded to `UNPROVEN`, `PARTIAL`,
  `DOCUMENTED_ONLY`, `NEEDS_REVIEW`, or `HUMAN_REVIEW_REQUIRED`.
- Claim language is checked by `scripts/codex_execution_system_check_v1.py` and
  existing claim/evidence checks where safe.

## Non-Claim Boundary

Anti-hype wording is not independent review. Real independent review remains
human review required until an actual reviewer records it.
