# Local Core Operating Foundation v1

## Purpose

This runbook defines the local-only core operating foundation for protected architecture work.

## Stage 1: Task Classification Gate

Every task must be classified before execution:

- A: cloud assist allowed with sanitized context
- B: patch-only with minimal snippets
- C: local-only with no cloud AI

## Stage 2: Cloud AI Boundary Enforcer

Cloud AI is a draft worker only. It may not receive secrets, full core architecture context, production context, provider live execution context, vault live-write context, or repository authority.

## Stage 3: Patch-Only Intake Contract

Patch-only work requires minimal snippets, source snippet digest, patch digest, unified diff patch output, local apply, local CI, and human review.

## Stage 4: Local Authority Gate

Local terminal remains authority for branch creation, diff check, local tests, CI, commit, merge, push, and branch deletion.

Cloud AI is not authority.

## Stage 5: Core Asset Protection Registry

Protected assets are C-layer and local-only.

Protected assets include system architecture core, runtime spine design, provider architecture, replay architecture, evidence vault architecture, OSINT / asset mapping architecture, decision engine, real provider implementation, real strategy parameters, real execution logic, real deployment scripts, real run history, real evidence vault, and real KMS/keyring.

## Stage 6: CI Gate

The local core operating foundation must remain testable through local unit tests and the global `make ci` suite.

## Non-Overclaim

This foundation does not implement real provider execution, real vault storage, real OSINT ingestion, real strategy execution, or production autonomy. It only defines local-only governance and validation boundaries.
