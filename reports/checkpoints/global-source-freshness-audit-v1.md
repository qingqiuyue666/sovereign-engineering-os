# Global Source Freshness Audit V1

Status: `BOUNDED_SOURCE_FRESHNESS_AUDIT_COMPLETE`

## bounded source-freshness audit

Live search availability: available.
Search date/time: 2026-06-14T16:37:09Z / 2026-06-15T00:37:09+0800.
Do not claim exhaustive global search: this was a bounded source-freshness
audit, not a complete survey of the world.

## Search Queries

- `SWE-bench official benchmark coding agents SWE-bench Pro Multi-SWE-bench 2026`
- `Terminal-Bench official benchmark AI agents terminal tasks`
- `OSWorld benchmark official computer use agents AndroidWorld MobileWorld`
- `WebArena WorkArena BrowserGym Mind2Web WebVoyager benchmark official`
- `OpenHands official GitHub AI software development agents SDK sandbox`
- `SWE-agent official GitHub AI software engineering agent`
- `Aider official GitHub AI pair programming benchmark`
- `LangGraph AutoGen CrewAI LlamaIndex agent runtime official docs`
- `NIST AI RMF official NIST AI Risk Management Framework generative AI profile 2026`
- `OWASP Agentic AI Security Project AIVSS LLM Top 10 official`
- `MITRE ATLAS official AI threats framework`
- `SLSA OpenSSF Scorecard SPDX CycloneDX Sigstore Gitleaks Semgrep official supply chain security`
- `OpenTelemetry GenAI semantic conventions official`
- `Model Context Protocol official specification agents 2026`
- `Agent2Agent A2A protocol official Google 2026`
- `GDPval SWE-Lancer BrowseComp APEX-agents official benchmark`

## Opened sources

- SWE-bench: https://www.swebench.com/
- SWE-bench Verified: https://www.swebench.com/verified.html
- SWE-Bench Pro: https://labs.scale.com/leaderboard/swe_bench_pro_public
- Terminal-Bench: https://www.tbench.ai/
- WebArena: https://webarena.dev/
- BrowserGym: https://github.com/ServiceNow/BrowserGym
- OSWorld: https://os-world.github.io/
- OpenHands: https://github.com/OpenHands/openhands
- SWE-agent: https://github.com/swe-agent/swe-agent
- Aider leaderboards: https://aider.chat/docs/leaderboards/
- LangGraph overview: https://docs.langchain.com/oss/python/langgraph/overview
- E2B: https://e2b.dev/
- Daytona: https://www.daytona.io/
- NIST AI RMF: https://www.nist.gov/itl/ai-risk-management-framework
- NIST SSDF: https://csrc.nist.gov/pubs/sp/800/218/final
- OWASP GenAI Security Project: https://genai.owasp.org/
- OWASP AIVSS: https://aivss.owasp.org/
- MITRE ATLAS: https://atlas.mitre.org/
- OpenSSF Scorecard: https://scorecard.dev/
- SLSA/OpenSSF reference: https://openssf.org/slsa-tooling/
- OpenTelemetry GenAI attributes: https://opentelemetry.io/docs/specs/semconv/registry/attributes/gen-ai/
- Model Context Protocol specification repository: https://github.com/modelcontextprotocol/modelcontextprotocol
- Agent2Agent protocol repository: https://github.com/a2aproject/A2A
- GDPval: https://openai.com/index/gdpval/
- SWE-Lancer: https://openai.com/index/swe-lancer/
- BrowseComp: https://openai.com/index/browsecomp/
- APEX-agents: https://epoch.ai/benchmarks/apex-agents
- BFCL: https://gorilla.cs.berkeley.edu/leaderboard.html
- tau-bench/tau2-bench: https://taubench.com/
- GAIA: https://arxiv.org/abs/2311.12983

## Verified sources

- `VERIFIED_CANONICAL_SOURCE`: NIST AI RMF, NIST SSDF, OWASP GenAI, OWASP
  AIVSS, MITRE ATLAS, OpenSSF Scorecard, OpenTelemetry GenAI, MCP, A2A.
- `REFERENCE_ONLY`: SWE-bench family, Terminal-Bench, WebArena, BrowserGym,
  OSWorld, OpenHands, SWE-agent, Aider, LangGraph, E2B, Daytona, GDPval,
  SWE-Lancer, BrowseComp, APEX-agents, BFCL, tau-bench, GAIA.

## Rejected sources

- `REJECTED_FOR_NOW`: social posts, Reddit threads, vendor comparison blogs,
  and noncanonical summaries when a canonical page or repository was available.

## Uncertain sources

- `NEEDS_REVIEW`: any source whose license, benchmark access terms,
  contamination risk, dependency risk, or maintenance state was not fully
  reviewed in this run.

## Categories

| Category | Classification | Note |
| --- | --- | --- |
| coding-agent and repository-level benchmarks | `REFERENCE_ONLY` | No benchmark executed |
| browser/OS/mobile benchmarks | `REFERENCE_ONLY` | No browser/OS benchmark executed |
| professional/economic-value benchmarks | `REFERENCE_ONLY` | GDPval/SWE-Lancer/APEX/GAIA intake only |
| production agent runtimes | `REFERENCE_ONLY` | No runtime integrated |
| runtime sandboxes | `NEEDS_REVIEW` | Vendor/security review needed |
| agent identity/delegation protocols | `REFERENCE_ONLY` | MCP/A2A require security review |
| agentic AI security/governance | `VERIFIED_CANONICAL_SOURCE` | Governance criteria only |
| supply-chain/security automation | `REFERENCE_ONLY` | Tool integration not performed |
| observability/telemetry | `REFERENCE_ONLY` | Live telemetry not implemented |
| benchmark contamination/license policy | `NEEDS_REVIEW` | Legal/data review required |

## Categories not searched

- Full proprietary vendor benchmark suites.
- Private benchmark datasets.
- All academic papers for every seed benchmark.
- All country-specific legal/compliance frameworks.
