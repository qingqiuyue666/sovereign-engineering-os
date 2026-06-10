# Supply Chain Integrity Policy V1

## Policy

SEOS supply-chain work must be explicit, reviewable, and bounded. It must avoid
curl pipe-to-shell bootstrap patterns, uncontrolled network in tests, hidden
dependency installation, and mutable release evidence.

## Required Controls

- no `curl | bash` or `wget | bash` install path
- no uncontrolled network in tests
- minimal CI permissions
- GitHub Actions pinning policy
- dependency review policy
- artifact checksum and provenance story
- tag immutability for `v0.1.0-rc3`
- SBOM strategy before public release packaging

## Validation

Validated by `python3 scripts/supply_chain_check_v1.py` and
`python3 scripts/release_invariant_check_v1.py`.
