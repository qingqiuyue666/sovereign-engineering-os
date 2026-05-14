# OSS Top Repo Integration Intake Audit v1

Status: implementation intake complete

Branch: `oss-top-repo-integration-autonomous-sprint`

Authoritative baseline: `origin/main` at `105f5f4357a925a336d419fdce5ad125640fbd34`

Metadata basis: GitHub repository search, public OSS ecosystem search, and GitHub repository API metadata checked on 2026-05-14.

## Decision summary

- repositories reviewed: 42
- strong candidates shortlisted: 17
- selected for implementation or design integration: 7
- explicitly rejected: 12
- dependency additions approved now: none
- vendored code approved now: none

This sprint selects standard-library implementations shaped by proven OSS patterns. No external source code is copied into this repository. No runtime authority, external tool control, API/LLM runtime, browser automation, OS automation, spreadsheet mutation, spreadsheet output writing, or input mutation is authorized.

## Selection gates

Each candidate was checked against these gates:

- permissive or otherwise compatible license
- local-first compatibility
- no input mutation by default
- no raw data leakage by default
- deterministic output compatibility
- testability
- maintainability
- no hidden network/API requirement
- no external tool control unless isolated and disabled by default
- no conflict with current kernel/adapters boundary

## Strong shortlist

The strong shortlist is:

1. `Textualize/rich`
2. `pallets/click`
3. `fastapi/typer`
4. `python-jsonschema/jsonschema`
5. `pydantic/pydantic`
6. `frictionlessdata/frictionless-py`
7. `duckdb/duckdb`
8. `pola-rs/polars`
9. `jqnatividad/qsv`
10. `medialab/xan`
11. `microsoft/markitdown`
12. `docling-project/docling`
13. `simonw/sqlite-utils`
14. `quickwit-oss/tantivy`
15. `CycloneDX/cyclonedx-python-lib`
16. `anchore/syft`
17. `syrupy-project/syrupy`

## Selected integrations

Selected for this sprint:

| Repository | License | Integration type | Local capability | Decision |
| --- | --- | --- | --- | --- |
| `python-jsonschema/jsonschema` | MIT | design inspiration only | deterministic package validation shape | implement local validator with no dependency |
| `frictionlessdata/frictionless-py` | MIT | design inspiration only | tabular package completeness and report posture | implement local job/package report with no dependency |
| `simonw/sqlite-utils` | Apache-2.0 | design inspiration only | local artifact indexing and metadata search concepts | implement JSON artifact index with no dependency |
| `syrupy-project/syrupy` | MIT | design inspiration only | normalized snapshot/golden comparison | implement snapshot utilities with no dependency |
| `Textualize/rich` | MIT | design inspiration only | readable CLI result contracts | add explicit safe CLI subcommands with JSON output, no dependency |
| `pallets/click` | BSD-3-Clause | design inspiration only | command grouping and focused subcommands | add argparse subcommands, no dependency |
| `CycloneDX/cyclonedx-python-lib` | Apache-2.0 | design inspiration only | integration registry and manifest/provenance discipline | implement static OSS integration registry with no dependency |

## Candidate audit

| # | Repository | URL | Category | Primary language | License | Stars / activity | Last activity | Dependency weight | Local-first fit | Network/API requirement | Security concerns | License compatibility | Integration type | Reason |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `duckdb/duckdb` | <https://github.com/duckdb/duckdb> | local data processing | C++ | MIT | 38182 stars; active | pushed 2026-05-14 | medium/heavy native engine | strong for local analytics | none required for embedded local use | native engine and SQL surface would broaden scope | compatible | optional dependency | Shortlisted, but deferred because current system forbids spreadsheet output writing and does not need query execution yet. |
| 2 | `pola-rs/polars` | <https://github.com/pola-rs/polars> | dataframe alternative | Rust | MIT | 38488 stars; active | pushed 2026-05-13 | medium/heavy native package | strong for local tabular computation | none required | dataframe execution could encourage raw value copying | compatible | optional dependency | Shortlisted, but deferred; current sprint keeps validation metadata-only. |
| 3 | `jqnatividad/qsv` | <https://github.com/dathere/qsv> | CSV/TSV profiling | Rust | Unlicense | 3640 stars; active | pushed 2026-05-14 | external binary | strong local CSV profiling | none required | external process/binary would violate no subprocess if called | compatible | design inspiration only | Shortlisted for CSV profiling ideas; not integrated as dependency or tool. |
| 4 | `medialab/xan` | <https://github.com/medialab/xan> | CSV/TSV profiling | Rust | Unlicense | 3984 stars; active | pushed 2026-05-13 | external binary | strong local CSV toolkit | none required | external process/binary would violate no subprocess if called | compatible | design inspiration only | Shortlisted for local CSV workflow patterns; not integrated as a runtime tool. |
| 5 | `frictionlessdata/frictionless-py` | <https://github.com/frictionlessdata/frictionless-py> | data validation / contracts | Python | MIT | 820 stars; active | pushed 2026-04-14 | medium | strong local package validation | none required for local validation | schema use must avoid raw value leakage | compatible | design inspiration only | Selected; implement local package validation reports without adding dependency. |
| 6 | `great-expectations/great_expectations` | <https://github.com/great-expectations/great_expectations> | data quality validation | Python | Apache-2.0 | 11502 stars; active | pushed 2026-05-14 | heavy | partial local fit | cloud features optional but substantial | heavy framework and semantic validation pressure | compatible | design inspiration only | Deferred; useful concepts, but too heavy for this local metadata-only sprint. |
| 7 | `sodadata/soda-core` | <https://github.com/sodadata/soda-core> | data quality validation | Python | NOASSERTION | 2346 stars; active | pushed 2026-05-14 | medium/heavy | partial local fit | cloud ecosystem likely adjacent | GitHub API did not assert SPDX license | not accepted | rejected | Rejected for this sprint because license compatibility was not explicit enough from repository API metadata. |
| 8 | `python-jsonschema/jsonschema` | <https://github.com/python-jsonschema/jsonschema> | data validation / contracts | Python | MIT | 4947 stars; active | pushed 2026-05-12 | low/medium | strong | none required | must avoid remote `$ref` use if depended upon | compatible | design inspiration only | Selected; implement deterministic local validation contracts using standard library only. |
| 9 | `pydantic/pydantic` | <https://github.com/pydantic/pydantic> | typed contracts | Python | MIT | 27764 stars; active | pushed 2026-05-13 | medium/native | strong for typed models | none required | dependency weight and model churn | compatible | optional dependency | Shortlisted, but not needed because dataclasses and local validators are enough. |
| 10 | `keleshev/schema` | <https://github.com/keleshev/schema> | schema validation | Python | MIT | 2944 stars; active | pushed 2026-03-04 | low | good | none required | smaller maintainer surface | compatible | design inspiration only | Reviewed; not selected because `jsonschema` patterns are a better fit. |
| 11 | `pallets/click` | <https://github.com/pallets/click> | CLI / terminal UX | Python | BSD-3-Clause | 17485 stars; active | pushed 2026-05-14 | low | strong | none required | dependency not needed for current argparse CLI | compatible | design inspiration only | Selected for explicit command grouping patterns without dependency adoption. |
| 12 | `fastapi/typer` | <https://github.com/fastapi/typer> | CLI / terminal UX | Python | MIT | 19404 stars; active | pushed 2026-05-13 | medium | strong | none required | adds dependency stack not needed now | compatible | design inspiration only | Shortlisted; deferred because the existing CLI can harden with argparse. |
| 13 | `Textualize/rich` | <https://github.com/Textualize/rich> | CLI / terminal UX | Python | MIT | 56341 stars; active | pushed 2026-04-12 | low/medium | strong | none required | colored output is unnecessary for machine-safe JSON | compatible | design inspiration only | Selected for stable result-output conventions, implemented as JSON only. |
| 14 | `prompt-toolkit/python-prompt-toolkit` | <https://github.com/prompt-toolkit/python-prompt-toolkit> | CLI / terminal UX | Python | BSD-3-Clause | 10446 stars; active | pushed 2026-05-14 | medium | partial | none required | interactive shell surface is not needed and could complicate safe CLI | compatible | rejected | Rejected for this sprint because interactive prompt surfaces do not strengthen the safe non-authority batch CLI. |
| 15 | `BrianPugh/cyclopts` | <https://github.com/BrianPugh/cyclopts> | CLI / terminal UX | Python | Apache-2.0 | 1155 stars; active | pushed 2026-05-14 | low/medium | strong | none required | Python version and new dependency not needed | compatible | design inspiration only | Reviewed; not selected because argparse is sufficient. |
| 16 | `microsoft/markitdown` | <https://github.com/microsoft/markitdown> | document processing | Python | MIT | 123126 stars; active | pushed 2026-04-20 | medium/heavy extras | partial | may accept URLs in some modes | document conversion can copy raw content | compatible | optional dependency | Shortlisted but deferred; future optional metadata-only extraction must disable URL and raw content modes. |
| 17 | `docling-project/docling` | <https://github.com/docling-project/docling> | document processing | Python | MIT | 59725 stars; active | pushed 2026-05-13 | heavy | partial | local mode exists, but URL/AI workflows adjacent | document conversion can extract raw content | compatible | optional dependency | Shortlisted but deferred; too heavy for this sprint's metadata-only boundary. |
| 18 | `Unstructured-IO/unstructured` | <https://github.com/Unstructured-IO/unstructured> | document processing | HTML/Python | Apache-2.0 | 14704 stars; active | pushed 2026-05-13 | heavy | partial | cloud integrations adjacent | heavy parser stack and raw content extraction | compatible | design inspiration only | Deferred; useful future optional extractor but not safe for this sprint. |
| 19 | `py-pdf/pypdf` | <https://github.com/py-pdf/pypdf> | document processing | Python | NOASSERTION | 9991 stars; active | pushed 2026-05-14 | low/medium | strong for local PDFs | none required | license assertion needs manual verification before dependency use | not accepted now | rejected | Rejected for this sprint because repository API did not assert a compatible SPDX license. |
| 20 | `python-openxml/python-docx` | <https://github.com/python-openxml/python-docx> | document metadata extraction | Python | MIT | 5576 stars; active | pushed 2025-06-17 | medium | strong for local DOCX | none required | document parsing may expose raw content | compatible | optional dependency | Deferred; future metadata-only DOCX support can revisit. |
| 21 | `scanny/python-pptx` | <https://github.com/scanny/python-pptx> | document metadata extraction | Python | MIT | 3350 stars; active | pushed 2024-08-07 | medium | strong for local PPTX | none required | document parsing may expose raw content | compatible | optional dependency | Deferred; future metadata-only PPTX support can revisit. |
| 22 | `pymupdf/PyMuPDF` | <https://github.com/pymupdf/PyMuPDF> | document processing | Python | AGPL-3.0 | 9702 stars; active | pushed 2026-05-11 | native/heavy | strong local parser | none required | copyleft license incompatible with default policy | incompatible | rejected | Rejected because AGPL is explicitly out of scope for copied code or production dependency use. |
| 23 | `mchaput/whoosh` | <https://github.com/mchaput/whoosh> | local search / indexing | Python | NOASSERTION | 658 stars; limited | pushed 2024-01-03 | low | local-first | none required | inactive and license not asserted | not accepted now | rejected | Rejected due license ambiguity and weaker maintenance. |
| 24 | `quickwit-oss/tantivy` | <https://github.com/quickwit-oss/tantivy> | local search / indexing | Rust | MIT | 15185 stars; active | pushed 2026-05-14 | native engine | strong local indexing | none required | native engine would be excessive for metadata index | compatible | design inspiration only | Shortlisted; not used as dependency because JSON metadata indexing is enough. |
| 25 | `quickwit-oss/tantivy-py` | <https://github.com/quickwit-oss/tantivy-py> | local search / indexing | Rust | MIT | 413 stars; active | pushed 2026-05-12 | native binding | local-first | none required | binary/native dependency weight | compatible | optional dependency | Reviewed; deferred because no native dependency is needed. |
| 26 | `simonw/sqlite-utils` | <https://github.com/simonw/sqlite-utils> | local search / indexing | Python | Apache-2.0 | 2052 stars; active | pushed 2026-01-21 | low/medium | strong local metadata store | none required | SQLite writes must stay outside input | compatible | design inspiration only | Selected for local artifact index shape, implemented as deterministic JSON. |
| 27 | `dagster-io/dagster` | <https://github.com/dagster-io/dagster> | local workflow orchestration | Python | Apache-2.0 | 15505 stars; active | pushed 2026-05-14 | heavy | partial | cloud/control-plane features adjacent | orchestration could imply execution authority | compatible | rejected | Rejected for this sprint because it introduces a workflow runtime surface, not a metadata-only helper. |
| 28 | `PrefectHQ/prefect` | <https://github.com/PrefectHQ/prefect> | local workflow orchestration | Python | Apache-2.0 | 22400 stars; active | pushed 2026-05-14 | heavy | partial | cloud service ecosystem adjacent | orchestration runtime and scheduling authority risks | compatible | rejected | Rejected for this sprint because runtime orchestration conflicts with the no-authority boundary. |
| 29 | `snakemake/snakemake` | <https://github.com/snakemake/snakemake> | local workflow orchestration | Python | MIT | 2777 stars; active | pushed 2026-05-14 | heavy | local-first workflow | none required for local, but invokes external commands by design | execution/subprocess model conflicts with boundary | compatible | rejected | Rejected because its core value is external command orchestration. |
| 30 | `CycloneDX/cyclonedx-python-lib` | <https://github.com/CycloneDX/cyclonedx-python-lib> | security / provenance | Python | Apache-2.0 | 108 stars; active | pushed 2026-05-06 | medium | strong local manifest concepts | none required | SBOM schema complexity unnecessary now | compatible | design inspiration only | Selected for registry/provenance discipline without dependency adoption. |
| 31 | `anchore/syft` | <https://github.com/anchore/syft> | security / provenance | Go | Apache-2.0 | 8928 stars; active | pushed 2026-05-13 | external binary | strong local package inspection | optional remote features must stay disabled | external process forbidden if invoked | compatible | design inspiration only | Shortlisted for local package inspection concepts; not invoked or depended on. |
| 32 | `in-toto/in-toto` | <https://github.com/in-toto/in-toto> | security / provenance | Python | NOASSERTION | 1001 stars; active | pushed 2026-05-05 | medium | strong provenance concept | none required | signing/key workflow and license assertion need review | not accepted now | rejected | Rejected for this sprint because cryptographic signing and ambiguous license metadata are out of scope. |
| 33 | `ossf/scorecard` | <https://github.com/ossf/scorecard> | security / provenance | Go | Apache-2.0 | 5439 stars; active | pushed 2026-05-14 | external binary/service style | partial | GitHub/API use common | network/API scanning conflicts with sprint boundary | compatible | design inspiration only | Reviewed; not integrated because this sprint cannot add network/API checks. |
| 34 | `syrupy-project/syrupy` | <https://github.com/syrupy-project/syrupy> | testing / QA | Python | MIT | 846 stars; active | pushed 2026-04-17 | low | strong | none required | snapshot brittleness if absolute paths leak | compatible | design inspiration only | Selected; implement path-normalized snapshot utilities without dependency adoption. |
| 35 | `HypothesisWorks/hypothesis` | <https://github.com/HypothesisWorks/hypothesis> | testing / QA | Python | NOASSERTION | 8619 stars; active | pushed 2026-05-13 | medium | strong | none required | license metadata needs manual verification before dependency use | not accepted now | design inspiration only | Reviewed; no dependency added because repository API did not assert SPDX license. |
| 36 | `pytest-dev/pytest` | <https://github.com/pytest-dev/pytest> | testing / QA | Python | MIT | 13849 stars; active | pushed 2026-05-14 | medium | strong | none required | current repo uses unittest and make ci | compatible | design inspiration only | Shortlisted but not adopted; keep current test runner unchanged. |
| 37 | `nedbat/coveragepy` | <https://github.com/coveragepy/coveragepy> | testing / QA | Python | Apache-2.0 | 3374 stars; active | pushed 2026-05-13 | low/medium | strong | none required | coverage gates may churn CI scope | compatible | design inspiration only | Reviewed; not selected because acceptance is functional green tests, not coverage gating. |
| 38 | `boxed/mutmut` | <https://github.com/boxed/mutmut> | testing / QA | Python | BSD-3-Clause | 1291 stars; active | pushed 2026-05-09 | medium | partial | none required | mutation testing would expand runtime and CI cost | compatible | rejected | Rejected for this sprint because mutation testing is too broad for this integration branch. |
| 39 | `GothenburgBitFactory/taskwarrior` | <https://github.com/GothenburgBitFactory/taskwarrior> | personal automation foundations | C++ | MIT | 5787 stars; active | pushed 2026-05-12 | external app | local-first | none required | external task app/control surface conflicts with boundary | compatible | rejected | Rejected because local task management app integration would imply external tool control. |
| 40 | `super-productivity/super-productivity` | <https://github.com/super-productivity/super-productivity> | personal automation foundations | TypeScript | MIT | 19344 stars; active | pushed 2026-05-14 | heavy app | local-first app | optional integrations likely | external app/workbench integration conflicts with boundary | compatible | design inspiration only | Reviewed for review-queue ideas; not integrated. |
| 41 | `paperless-ngx/paperless-ngx` | <https://github.com/paperless-ngx/paperless-ngx> | document/workbench automation | Python | GPL-3.0 | 40661 stars; active | pushed 2026-05-14 | heavy app | local-first server | server/workflow app | GPL and app runtime out of scope | incompatible | rejected | Rejected due GPL and broad server/workflow scope. |
| 42 | `OpenRefine/OpenRefine` | <https://github.com/OpenRefine/OpenRefine> | local data workbench | Java | BSD-3-Clause | 11827 stars; active | pushed 2026-05-14 | heavy external app | local-first | none required for local app | data cleaning/transformation conflicts with no spreadsheet mutation | compatible | rejected | Rejected because its core workflow is data transformation and external application control. |

## License and vendoring decision

No code is copied from any candidate. No dependency file is changed. All implemented code must use the Python standard library and local repository helpers only.

GPL, AGPL, unclear-license, no-license, cloud-first, telemetry-by-default, and external-tool-control candidates are rejected or deferred.

## Implementation allowance

Allowed now:

- deterministic artifact index over generated package metadata and hashes
- deterministic job package validator
- deterministic approved output package validator
- normalized snapshot utilities for tests
- safe CLI subcommands that preserve the existing CLI
- static integration registry
- usage documentation updates

Still forbidden:

- runtime authority
- arbitrary execution
- external tool control
- browser automation
- OS automation
- API/LLM runtime
- autonomous file modification
- spreadsheet mutation or output writing
- input mutation
- raw cell value copying
- kernel/adapters modification
- release/tag mutation
