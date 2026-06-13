# Workflow Diagnosis Screen

## Purpose

Specify the screen for diagnosing a buyer's AI-assisted engineering workflow.

## Inputs

- buyer role
- risk owner
- workflow name
- AI entry point
- production relevance
- current review path
- test evidence
- approval gates
- rollback path
- external claim pressure

## Outputs

- current-state map
- missing evidence list
- risk-tier proposal
- buyer questions
- rejection or next-step recommendation

## Controls

- require source or mark `EVIDENCE_PENDING`
- no readiness claim without evidence
- route Tier 3 and Tier 4 items to auditor/human approval

## Not In Scope

- executing code
- changing production workflow
- storing secrets
- calling live providers by default
