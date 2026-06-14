# External Project Absorption Shortlist V1

Status: `SHORTLIST_COMPLETE_REFERENCE_ONLY`

## external project absorption shortlist

No external code, dependency, benchmark dataset, or runtime was copied or
integrated in this run.

| Candidate | Source | Category | Decision | Why it matters | Possible scope | Risk | Benchmark contamination risk | Smallest safe action now | Evidence path |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| SWE-bench / SWE-bench Verified | https://www.swebench.com/ | coding benchmark | `REFERENCE_ONLY` | Real repository issue benchmark | Acceptance criteria inspiration | Dataset/license/access review needed | High if tasks leak into prompts | Record no benchmark score claim | Source audit |
| Terminal-Bench | https://www.tbench.ai/ | terminal benchmark | `REFERENCE_ONLY` | Multi-step terminal work | Future sample plan criteria | Environment cost and setup risk | Medium | Record terminal task gap | Sample plan |
| WebArena / BrowserGym | https://webarena.dev/ / https://github.com/ServiceNow/BrowserGym | browser benchmark | `NEEDS_REVIEW` | Web-agent realism | Future runnable slice only | Setup and data risks | Medium | Keep browser benchmark unrun | Gap audit |
| OSWorld | https://os-world.github.io/ | OS benchmark | `NEEDS_REVIEW` | Desktop task realism | Future computer-use benchmark plan | Requires environment isolation | Medium | Keep OS benchmark unrun | Gap audit |
| GDPval / SWE-Lancer / APEX-agents | OpenAI and Epoch pages | economic value benchmark | `REFERENCE_ONLY` | Professional task value | Future criteria only | Access/license/rubric uncertainty | High | Queue review | Deep review queue |
| OpenHands | https://github.com/OpenHands/openhands | agent runtime | `REFERENCE_ONLY` | Agent/runtime/workspace architecture | Architecture notes only | Dependency and security review needed | Low | No code copied | Source ledger |
| SWE-agent | https://github.com/swe-agent/swe-agent | coding agent runtime | `REFERENCE_ONLY` | Agent-computer interface pattern | Architecture notes only | Dependency review needed | Low | No code copied | Source ledger |
| Aider | https://aider.chat/docs/leaderboards/ | coding tool/benchmark | `REFERENCE_ONLY` | Git-integrated edit loop | Review criteria only | Tool adoption not reviewed | Medium | No tool adoption | Source ledger |
| LangGraph | https://docs.langchain.com/oss/python/langgraph/overview | runtime/orchestration | `INTEGRATE_TOOL` only after review | Durable execution and HITL patterns | Possible future dependency | License/dependency/security review needed | Low | Leave queued | Deep review queue |
| E2B / Daytona | https://e2b.dev/ / https://www.daytona.io/ | sandbox | `NEEDS_REVIEW` | Runtime isolation | Future sandbox evaluation | Vendor, cost, data, secret risk | Low | Map sandbox gap | Runtime control map |
| NIST / OWASP / MITRE | Official pages | governance/security | `COPY_SMALL_PATTERN` only as generic criteria | Security framing | Checklist patterns, not code | Must attribute and adapt | Low | Map to security gate | Security map |
| OpenSSF / SLSA / SBOM / Sigstore | Official pages | supply chain | `NEEDS_REVIEW` | Supply-chain hardening | Future tooling | CI/admin and dependency risk | Low | Keep as queue | Security map |
| MCP / A2A | Official repositories | protocol/interoperability | `REFERENCE_ONLY` | Tool and agent interop | Future threat-model input | Protocol security risk | Low | No protocol adoption | Source ledger |
| OpenTelemetry GenAI | Official docs | observability | `REFERENCE_ONLY` | Telemetry schema ideas | Future trace schema | Runtime not present | Low | Keep documented-only | Observability map |

## Decisions Summary

- `COPY_SMALL_PATTERN`: generic governance checklist patterns only, after
  attribution and review.
- `INTEGRATE_TOOL`: LangGraph-style durable execution concepts only after
  license/security/dependency review.
- `REFERENCE_ONLY`: most benchmark/runtime/protocol sources.
- `NEEDS_REVIEW`: sandboxes, browser/OS benchmarks, supply-chain tooling, and
  benchmark datasets.
- `REJECT_FOR_NOW`: noncanonical summaries when official sources exist.
