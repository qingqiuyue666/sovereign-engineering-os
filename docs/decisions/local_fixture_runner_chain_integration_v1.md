# Local Fixture Runner Chain Integration v1

Status: accepted

This decision integrates the existing metadata-only local-fixture runner chain
into the Personal AI system surface.

Integrated capabilities:

- `local_fixture_runner_contract_draft`
- `local_fixture_runner_stub_admission_gate`
- `local_fixture_runner_receipt_contract_draft`
- `local_fixture_runner_receipt_preflight_verifier`
- `local_fixture_runner_receipt_metadata_artifact`

Integration scope:

- Local launcher wrappers expose the existing capability functions.
- CLI subcommands route to those launcher wrappers.
- Adapter registry entries mark all five adapters as `candidate`.
- Task graph fixture routing allows the five candidate adapters as bounded
  metadata fixture nodes only.
- Task graph artifact-output binding records their generated local artifacts.
- Product health static visibility includes the new workflows and subcommands.
- Tracer-bullet tests cover registry, CLI, graph, artifact-output, health, and
  forbidden-boundary checks.

Boundary:

This is integration-only. It does not create a real runner, runnable job,
approval token, execution token, adapter execution path, Playwright execution
path, browser-opening path, network path, live website path, production
promotion path, autonomous execution path, shell command materialization path,
or account/login/registration/scraping/bypass/CAPTCHA workflow.

All five registry entries remain `candidate`, not production admitted. Task graph
support is limited to `fixture_execution` metadata nodes whose route policy is
`local_fixture_runner_metadata_chain_not_production_admitted`.

Future work:

Any runner implementation, runner stub, executable job, token issuance,
adapter execution, Playwright/browser execution, network access, live website
access, or production promotion requires a separate reviewed PR with new
admission evidence.
