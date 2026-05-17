# V12 Security Truth Substrate Threat Model

## Scope

This threat model covers descriptor-level truth substrate validation for WAL
metadata, taint propagation, artifact provenance, and capability token policy.

## Threats

- WAL segment descriptors can be replayed, duplicated, reordered, or linked to
  the wrong predecessor digest.
- Taint can be silently downgraded unless declassification is explicit.
- Derived artifacts can omit provenance or claim a lower classification than
  their source chain.
- Capability tokens can overclaim scope, expire silently, authorize unknown
  actions, or carry secret material.

## Controls

- WAL validation is metadata-only and rejects duplicate segment ids, sequence
  rollback, and digest-chain mismatch.
- Taint propagation uses highest-classification-wins semantics.
- Artifact provenance requires digest refs and source refs and forbids raw
  content.
- Capability token policy rejects wildcard scope, expired tokens, unauthorized
  actions, and secret-bearing metadata.

## Non-Authorization

No SQLite import, database read, WAL file read, network access, provider call,
secret read, raw prompt persistence, or raw provider response persistence is
authorized by this substrate.
