# Sealed Evidence Redaction Contract v1

## Verdict

`SEALED_EVIDENCE_REDACTION_CONTRACT_READY_FOR_LOCAL_TESTS`

This branch adds the first narrow sealed/redacted evidence contract.

## Scope

Contract and tests only.

It does not:

- append audit records
- change `AppendOnlyLedger`
- read secret values
- persist secret values
- encrypt or decrypt blobs
- access network
- execute runtime code
- launch browsers
- launch creative software
- execute subprocesses
- checkpoint SQLite
- truncate WAL
- grant runtime authority

## Added surface

- `kernel/evidence/sealed_redaction_contract.py`
- `tests/tracer_bullet/test_sealed_evidence_redaction_contract.py`

## Evidence classifications

The contract recognizes:

- `public`
- `restricted`
- `secret`

## Secret-safe representations

Secret-classified evidence may only use safe representations:

- `sha256`
- `salted_hash`
- `hmac_placeholder`
- `sealed_blob_ref`
- `redacted_digest`

## Boundary invariant

Plaintext sensitive material must not become evidence payload.

The contract rejects:

- raw prompt fields
- raw provider response fields
- token/password/key/cookie/credential fields
- plaintext secret markers
- public evidence carrying sensitive material
- restricted evidence carrying secret material
- sealed-blob records without a sealed reference

## Current limitation

This is not yet an encrypted evidence vault.

It is a deterministic ingress contract for future sealed evidence storage. It validates that sensitive evidence is represented by digest, redacted digest, placeholder HMAC, or sealed reference rather than plaintext.

## Required local verification commands

```bash
python3 -m unittest tests.tracer_bullet.test_sealed_evidence_redaction_contract -v
python3 -m unittest discover -s tests/tracer_bullet -v
make ci
git diff --check
git status --short
```

## Next step

After merge, the next narrow slice should wire this contract into the append-only evidence path for selected high-risk audit payloads without changing existing runtime behavior.
