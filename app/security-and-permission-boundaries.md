# Security And Permission Boundaries

## Purpose

Define the safety boundaries for any future internal workbench.

## Boundaries

- no secret custody by default
- no production execution by default
- no browser or OS automation by default
- no live provider transmission of sensitive context without approval
- no customer-facing login or SaaS surface in the first version
- no external publication without permission and redaction
- no compliance/certification claim without external evidence

## Required Controls

- role-based access if implemented
- audit log for claim and approval changes
- explicit evidence permission status
- redaction workflow for proof assets
- human approval for high-risk actions
- fail-closed behavior for missing approval

## Not A Security Product Claim

This specification does not claim the app is secure, audited, certified, or
ready for production. It states requirements for a future internal prototype.
