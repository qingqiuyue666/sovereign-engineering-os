# Buying Trigger Map

## Purpose

Identify events that can turn the readiness audit from interesting strategy
into an urgent purchase.

## Primary Triggers

| Trigger | Buyer Concern | Audit Angle | Evidence To Capture |
| --- | --- | --- | --- |
| AI-code entering production | "We do not know if review gates are enough." | Map admission, review, tests, rollback, and ownership. | PR examples, review policies, release notes. |
| Upcoming release | "We need confidence before launch." | Focus on the release path and rollback readiness. | Release checklist, test coverage, rollback plan. |
| Customer or enterprise review | "A customer is asking how AI is controlled." | Produce bounded readiness language and evidence matrix. | Customer question, security review prompt, current answer. |
| Security/compliance audit | "We need an audit trail for AI-assisted work." | Show provenance, approvals, and evidence gaps. | Existing controls, policy docs, audit requirements. |
| Incident or near miss | "AI-assisted changes may increase production risk." | Reconstruct failure path and define gates. | Incident note, postmortem, failed test/review path. |
| AI tooling expansion | "We want to scale AI coding safely." | Define governance before broader adoption. | Tool rollout plan, usage pattern, risk owner. |

## Weak Triggers

- curiosity about AI
- generic transformation mandate
- tool evaluation without production pressure
- research-only request
- request for low-cost code review

Weak triggers should be nurtured only if they can become a named risk event
within 30-90 days.

## Trigger Qualification Script

Ask:

- What happens if this workflow is not governed in the next 30-90 days?
- Who will notice the failure?
- What deadline exists?
- What decision depends on the audit result?
- What proof would make the decision easier?

## Current Evidence Status

All triggers are hypotheses until recorded in discovery notes, outreach
responses, signed scope, or a paid audit.
