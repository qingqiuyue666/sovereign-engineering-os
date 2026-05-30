# AI Provider Admission Policy V1

## Purpose

This policy defines the repository evidence required before any AI provider
can be considered for admission. It is a governance boundary only. It does not
enable live provider calls, runtime expansion, direct AI execution, or
autonomous patching.

## Default State

- providers disabled by default
- deterministic mock provider only unless explicit future admission
- no direct AI execution
- no live provider transport
- no uncontrolled network access

## Required Admission Gates

Any future provider admission must include a request envelope, response
receipt, network access receipt, prompt provenance, token budget ceiling,
context redaction evidence, and model output artifact policy before execution
is considered.

## Human Boundary

Provider output is advisory evidence only. A patch requires human approval
before it can be applied, and validation before PR remains mandatory.

## External Review Boundary

This document is repository evidence for external review. It is not an
external approval, provider certification, or production readiness claim.
