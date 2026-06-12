# Delivery Command Center

## Purpose

Specify the internal surface for running one delivery loop.

## Panels

- scope and acceptance
- current-state map
- evidence matrix
- risk map
- review gates
- approval queue
- rollback/remediation
- findings and recommendations
- handoff package
- asset conversion decisions

## Status Flow

`intake -> scoped -> evidence_review -> findings -> audit_review -> handoff -> accepted/incomplete -> asset_capture`

## Required Gates

- scope approved
- evidence access approved
- material risks reviewed
- claims audited
- handoff accepted or incomplete
- asset decisions recorded

## Boundary

The command center is an internal coordination view. It does not execute
production changes.
