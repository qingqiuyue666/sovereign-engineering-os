# Context Redaction Policy V1

## Purpose

AI context must be sanitized before it reaches any provider boundary. The
context redaction rule protects secrets, local paths, raw prompts, provider
responses, hidden state, and credentials.

## Required Evidence

- context redaction
- prompt provenance
- source references that are repository-relative
- omission digests for excluded sensitive material
- token budget ceiling before context is packaged

## Rejected Material

Raw secret values, unredacted private paths, raw provider responses, raw
exception dumps, and credential-bearing headers are not allowed in AI context
bundles.

## Validation Boundary

The context bundle is digest-first evidence. A malformed bundle prevents
provider admission and must not be repaired by the provider.
