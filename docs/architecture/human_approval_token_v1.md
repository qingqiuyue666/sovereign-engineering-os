# Human Approval Token V1

## Purpose

Create scoped, expiring, revocable approval artifacts for risky dry-run/runtime
actions without enabling production autonomy.

## Token Model

`HumanApprovalToken` binds an approval id, operator, scope, action type, target,
optional tool/command/workflow/asset root identifiers, risk class, timestamps,
revocation state, reason, and deterministic content hash.

`ApprovalDecision` records an explicit accept/reject decision for a token.

## Evaluation Boundary

`evaluate_human_approval()` checks scope, expiry, revocation, action binding,
target binding, high-risk explicit decisions, credential-touching implicit
approval rejection, and forbidden payload fields.

Approval evaluation always reports that Command Envelope Admission Router and
Tool Risk Classifier checks are still required. Approval cannot authorize raw
commands, arbitrary argv, command lines, router bypass, risk-classifier bypass,
or production autonomy.

## Non-Goals

This does not execute commands, launch processes, call MCP tools, call network,
automate browsers, call providers, store credentials, launch ComfyUI, launch DCC
apps, create a UI, start daemons, start schedulers, or enable production
autonomy.
