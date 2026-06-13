# Internal Workbench App Spec

## Purpose

Define the future internal workbench for SEIS after transaction, delivery,
validation, and asset compounding layers exist.

## Status

Repository status: `APP_SPEC_READY`.

Real-world status: `APP_IMPLEMENTATION_PENDING`.

Status label: `INTERNAL_WORKBENCH_SPEC_READY`.

## Core Boundary

The app is the visible shell. SEIS is the hidden kernel. The first app should
be an internal workbench for operating delivery loops, evidence, approvals,
and asset compounding. It should not be a public SaaS until repeated
validated workflow patterns exist.

## Required Screens

- workflow diagnosis
- automation opportunity score
- delivery command center
- evidence and audit log
- asset library
- human approval flow
- AI brain routing
- security and permission boundaries

## Non-Goals

- no broad runtime implementation in this pass
- no live provider integration
- no secret manager
- no production control plane
- no customer-facing SaaS
- no app claim stronger than `APP_SPEC_READY`
