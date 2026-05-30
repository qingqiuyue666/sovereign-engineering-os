# Provider Failure Policy V1

## Purpose

Provider failures must fail closed and produce bounded evidence. A provider
error, timeout, schema failure, or poisoned response cannot become success.

## Required Receipts

- request envelope
- response receipt
- network access receipt
- failure bundle when provider output is rejected
- replay explanation when evidence is reviewed later

## Poisoning Controls

Provider response poisoning is treated as adversarial input. Instructions that
claim authority, request secret disclosure, bypass validation, or force a PASS
result are rejected.

## Current Runtime Boundary

Only deterministic mock provider evidence is allowed in this readiness wave.
Live-provider failure handling remains future admission work.
