# Human Approval Before Patch Policy V1

## Purpose

Human approval is required before AI-generated proposals can become repository
patches. This preserves operator control and prevents AI approval bypass.

## Required Approval

- proposal-first
- patch requires human approval
- validation before PR
- approval receipt references the proposal artifact
- rejection receipt records denied proposals

## Rejected Actions

Direct file edits from a provider response, auto-commits, auto-PRs, hidden
patch application, and fake PASS evidence are rejected.

## Operator Review

The reviewer must confirm scope, evidence references, validation commands,
secret safety, and the absence of unsupported recognition or certification
claims.
