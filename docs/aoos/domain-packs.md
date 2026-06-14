# AOOS Domain Packs

## Purpose

Domain packs make AOOS replaceable across fields. A pack translates the common
execution, authority, evidence, audit, and learning rules into a domain without
changing the core protocol.

## Domain Pack Contract

Each domain pack must define:

- scope and non-goals
- state inspection checklist
- ALLOW / ASK / DENY / REPORT boundaries
- expected inputs and outputs
- evidence records and evidence levels
- domain acceptance rubric
- failure and incident triggers
- rollback or recovery path
- observability events and evaluator metrics
- learning promotion path
- claims that must not be made without higher evidence

## Initial Pack Set

| Pack | Scope | Existing anchors | Minimum acceptance rubric | Not proven |
| --- | --- | --- | --- | --- |
| Engineering Pack | GitHub, PR, CI, review, release, security scan, branch protection, evidence report. | `AGENTS.md`, `.github/workflows/ci.yml`, `Makefile`, `docs/agent-protocols/` | L2 diff plus L3 local/CI checks for engineering completion; L4 human review for merge. | CI success does not prove user adoption. |
| DCC / Creative Pack | AE, Houdini, Unreal, Blender, ComfyUI, asset ingestion, render/output validation, aesthetic rubric, reproducibility. | `docs/operator/examples/creative_asset_factory/`, `templates/*manifest/`, `scripts/creative_total_check_v3.py` | Visible output, manifest, provenance, repeatable render or explicit blocker, and human aesthetic acceptance for final creative claims. | Generated assets do not prove publish performance or audience response. |
| Content Production Pack | Topic, script, copy, visual quality, publishing, retention, conversion, audience feedback, AI-smell gate. | `distribution/`, `proof/`, `validation/` | Draft plus source/evidence, editorial review, publish record, and audience metric source before performance claims. | Content creation is not audience validation. |
| Trade / Sales Pack | Lead source, outreach, reply classification, quotation, objection, follow-up, payment, delivery, repeat order. | `first-wedge/`, `transaction/`, `validation/outreach-*`, `validation/paid-signal-criteria.md` | Real source record, actor, date, consent/redaction status, and outcome for L5 commercial claims. | Interest is not payment; payment is not repeatable product-market fit. |
| Business Validation Pack | ICP, pain proof, budget, willingness to pay, paid pilot, retention, repeat usage, commercial evidence. | `validation/`, `market/`, `battlefield/`, `reports/real-world-validation/` | Counterevidence, paid or high-commitment signal, retention/repeat evidence, and kill/revise decision. | Templates do not prove market pull. |
| Research / Intelligence Pack | Source hierarchy, counterevidence, recency decay, uncertainty, hypothesis expiry, decision log, alternative explanations. | `docs/research/`, `world/`, `market/` | Source hierarchy, dated sources, counterevidence, confidence, expiry, and decision impact. | Research confidence is not operational truth. |
| Security / Compliance Pack | Secrets, accounts, platform policy, privacy, copyright/IP, supply chain, legal/commercial claims. | `SECURITY.md`, `docs/security/`, `scripts/secret_context_safety_check_v1.py`, `scripts/supply_chain_check_v1.py` | No secret exposure, scoped threat model, policy boundaries, and review for legal/commercial claims. | Static checks do not prove continuous security. |
| Asset / Supply Chain Pack | Source, license, version, checksum, compatibility, owner, backup, deprecation, migration. | `assets/`, `docs/compatibility/`, `docs/audits/claim_to_evidence_matrix_v1.md` | Asset manifest, license/provenance, checksum or digest, compatibility notes, owner, and migration plan. | Possession of assets does not prove rights to publish. |
| Operator UX Pack | Approval queue, interrupt mechanism, rollback instructions, risk summary, checkpoint dashboard, human gate clarity. | `app/human-approval-flow.md`, `app/evidence-and-audit-log-screen.md`, `docs/operator/` | Human gate clarity, interruption path, rollback path, and observable checkpoint state. | UI specs are not deployed operator software. |
| Model / Tool Routing Pack | Codex, Claude, GPT, Gemini, DeepSeek, routing criteria, disagreement protocol, reviewer separation, fallback policy. | `BRAIN_GOVERNANCE.md`, `app/ai-brain-routing-spec.md`, `docs/audit/ai_router_runtime_boundary_v1.md` | Tool routing decision record, authority boundary, reviewer separation, fallback, and no secret leakage. | Routing policy does not prove model quality. |

## Domain Acceptance Rubric Levels

| Level | Meaning |
| --- | --- |
| L0 | Agent claim only; not sufficient for acceptance. |
| L1 | Local observable result or command output. |
| L2 | Diff, file change, artifact, receipt, manifest, or commit. |
| L3 | Automated check, reproducible validation, local test, CI, or evaluator run. |
| L4 | Human review, approval, editorial acceptance, or merge decision. |
| L5 | Real user, customer, payment, delivery, retention, audience, or market source record. |

## Pack Promotion Rule

When a repeated failure appears in a domain pack, promote the fix through this
path when justified by evidence:

`memory -> checklist -> playbook -> script -> CI / evaluator / policy`

Do not promote a one-off observation into hard policy unless the cost and
false-positive risk are acceptable.
