# Non-Core Asset Kit Manifest v1

This document describes the deterministic manifest for the non-core production asset kit.

## Purpose

The manifest ties together documents, templates, examples, forms, sprint artifacts, blocked capabilities, and verification status without implying live execution readiness.

## Included Asset Families

- code audit examples
- creative sample pack
- macro templates
- operator review forms
- sprint artifacts

## Hashing Rules

- `content_hash` is computed by the builder.
- `observed_at` is observation metadata only and must not affect deterministic hashing.
- Missing required fields fail closed.
- Forbidden raw, env, or secret fields fail closed.
