# External Source Intake Ledger V1

Status: `REFERENCE_ONLY_INTAKE_COMPLETE_FOR_THIS_RUN`

## Intake Rule

This ledger records bounded source intake for
`ELEVEN_CORE_DELIVERY_LAYERS_V1_READY`. It does not clone, download, copy,
vendor, or adopt external code.

## Source Categories

| Category | Example admitted sources | Status | Purpose | Next action |
| --- | --- | --- | --- | --- |
| coding-agent and repository-level benchmarks | SWE-bench, SWE-bench Verified, SWE-Bench Pro, Terminal-Bench, Aider benchmark, SWE-Lancer | `REFERENCE_ONLY` | Criteria for repo task realism and validation design | Select allowed subset later |
| browser/OS/mobile benchmarks | WebArena, BrowserGym, OSWorld, BrowseComp | `REFERENCE_ONLY` | Criteria for browser/computer-use gaps | Map to future runnable slice only |
| professional/economic-value benchmarks | GDPval, APEX-agents, GAIA, tau-bench/BFCL | `REFERENCE_ONLY` | Criteria for real professional task value | License/access review |
| production agent runtimes | OpenHands, SWE-agent, Aider, LangGraph | `REFERENCE_ONLY` | Architecture patterns for review | No dependency added |
| runtime sandboxes | E2B, Daytona, sandbox comparison sources | `NEEDS_REVIEW` | Runtime isolation reference | Security/vendor review |
| agent identity/delegation protocols | MCP, A2A | `REFERENCE_ONLY` | Interop and protocol criteria | Security threat review |
| agentic AI security/governance | NIST AI RMF, NIST SSDF, OWASP GenAI/AIVSS, MITRE ATLAS | `VERIFIED_CANONICAL_SOURCE` | Governance and threat criteria | Map to existing repo checks |
| supply-chain/security automation | OpenSSF Scorecard, SLSA, SPDX, CycloneDX, Sigstore, CodeQL, Gitleaks, Semgrep | `REFERENCE_ONLY` | Supply-chain gate criteria | Tool-by-tool review |
| observability/telemetry | OpenTelemetry GenAI, LangSmith, Langfuse, Phoenix, Helicone, AgentOps | `REFERENCE_ONLY` | Observability criteria | No live telemetry claim |
| benchmark contamination/license policy | Benchmark project pages and papers | `NEEDS_REVIEW` | Avoid leaderboard leakage and unsafe reuse | Data/license review |

## Evidence Paths

- `CODEX_EXTERNAL_SOURCE_INTAKE_REGISTRY.md`
- `reports/checkpoints/global-source-freshness-audit-v1.md`
- `reports/checkpoints/frontier-gap-search-audit-v1.md`
- `reports/checkpoints/external-project-absorption-shortlist-v1.md`
- `reports/checkpoints/external-source-deep-review-queue-v1.md`

## Non-Claims

This ledger does not prove exhaustive search, benchmark execution, license
clearance, security clearance, production maturity, or external validation.
