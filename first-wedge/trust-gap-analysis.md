# Trust Gap Analysis

## Purpose

Describe why the buyer cannot solve this wedge with generic AI enthusiasm,
basic code review, or another model/tool purchase alone.

## Core Trust Gap

AI-assisted engineering creates output faster than most teams can prove the
output is safe, reviewed, reversible, owned, and accepted. The gap is not
"can the model write code." The gap is "can leadership trust the workflow
that admits AI-assisted work into production."

## Buyer Questions

| Question | Why It Matters | Audit Response |
| --- | --- | --- |
| Who is accountable for AI-assisted changes? | Without ownership, production risk becomes diffuse. | Name risk owner and decision rights. |
| What evidence is required before merge or release? | Review comments alone may not prove readiness. | Build evidence matrix and minimum evidence rules. |
| What changes are high risk? | Not all AI-assisted work should share one approval path. | Define risk tiers and approval gates. |
| What happens when the change fails? | Rollback and remediation must exist before readiness claims. | Produce rollback/remediation plan. |
| What can be shown to customers, auditors, or leadership? | External claims must be bounded and evidence-backed. | Create approved wording and limitation notes. |

## Current Alternatives And Weaknesses

| Alternative | Weakness |
| --- | --- |
| Generic AI coding policy | Often too abstract to govern real PR and release paths. |
| Tool vendor controls | Usually tool-specific and not enough for workflow acceptance. |
| More code review | Does not automatically produce evidence, rollback, or accountability. |
| Security checklist | May miss engineering workflow, acceptance, and release quality. |
| Internal meeting | Does not create a reusable evidence package or proof asset. |

## Required Trust Proof

The audit must produce:

- a clear workflow map
- evidence requirements by risk tier
- human approval points
- rollback/remediation path
- unresolved evidence gaps marked as `EVIDENCE_PENDING`
- buyer-approved acceptance criteria

## Boundary

The audit can reduce ambiguity and expose readiness gaps. It does not certify
compliance, guarantee production safety, or prove market adoption.
