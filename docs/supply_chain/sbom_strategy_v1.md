# SBOM Strategy V1

SEOS does not yet publish a public release artifact. Before public release
publication, the project must produce or document an SBOM strategy.

Minimum strategy:

- enumerate Python package metadata from `pyproject.toml`
- list runtime dependencies and test-only dependencies separately
- record direct dependency versions used in CI
- include action versions used by GitHub Actions
- attach checksums or provenance for release artifacts
- document known gaps and external review requirements

Until then, SBOM status is strategy-defined, not release-complete.
