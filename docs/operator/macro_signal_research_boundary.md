# Macro Signal Research Boundary

## Purpose

This is a safe boundary for macro and XAUUSD signal research. This is not a trading system.

## Research Domain

The research domain is macro market context and XAUUSD signal research for manual operator review. The boundary supports structured notes, evidence, contradiction checks, and after-action review templates.

## Allowed Outputs

- Research notes.
- Evidence packs.
- Contradiction packs.
- Signal strength summaries.
- No-trade reasons.
- Scenario maps.
- After-action review templates.
- Manual checklist.

## Forbidden Outputs

- Auto order execution.
- Broker/API execution.
- Full-position instructions.
- Leverage instructions.
- Autonomous trading.
- Guaranteed certainty claims.
- Execution bypass.
- Secret/env/API credential handling.

Auto order execution is forbidden.

## Evidence Requirements

- Cite caller-provided evidence summaries.
- Separate observation from interpretation.
- Include contradiction checks.
- Include no-trade reasons when evidence is incomplete or conflicting.
- Avoid certainty claims.

## Manual Decision Boundary

Final decisions remain manual. The operator may use research notes as one input, but the boundary must not recommend automated execution, full-position sizing, leverage, or broker/API actions.

## No-Trade Conditions

- Missing evidence.
- Conflicting evidence without resolution.
- Ambiguous macro regime.
- Event risk too high for manual confidence.
- Any request for automatic execution.
- Any request for leverage execution or broker/API execution.

## Blocked Execution

- No automatic financial execution.
- No trading automation.
- No broker/API execution.
- No order routing.
- No auto-buy.
- No auto-sell.
- No full-position execution logic.
- No leverage execution.
- No network execution inside new runtime modules.
- No subprocess execution inside new runtime modules.
- No environment value access.
- No SQLite mutation or introduction.

## Risk Controls

- Research output must include no-trade reasons.
- Research output must preserve manual decision boundaries.
- Any future unblock requires separate authorization, tests, audit, and human review.
- Blocked does not mean hidden-ready or enabled by operator preference.
