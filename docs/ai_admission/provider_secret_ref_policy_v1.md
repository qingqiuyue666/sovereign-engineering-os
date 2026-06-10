# Provider Secret Reference Policy V1

## Purpose

Provider credentials are represented by secret-ref only metadata. The
repository must not store, print, copy, or validate actual API key values.

## Rules

- secret-ref only
- no API key printing
- no `.env` reading by default
- no credential value in request envelope
- no credential value in response receipt
- no credential value in failure evidence

## Allowed Reference

A future admitted provider may name an environment variable or secret manager
reference as metadata, such as `OPENAI_API_KEY`, but the value remains outside
repository evidence.

## Failure Behavior

If a provider request requires an actual secret value during readiness work,
the request fails closed and records only the missing-admission reason.
