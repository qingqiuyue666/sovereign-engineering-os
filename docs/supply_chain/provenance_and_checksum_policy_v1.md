# Provenance And Checksum Policy V1

Artifacts used as release or audit evidence must have a provenance and checksum
story before external review.

Requirements:

- record repository-relative evidence references
- record validation commands and results
- use SHA-256 or git object hashes for integrity evidence
- do not store raw secrets in provenance records
- do not claim external certification from local checks
- keep release-candidate tag evidence immutable, including `v0.1.0-rc3`

The current readiness program records local repository evidence only. External
review must decide whether additional signed attestations are required.
