# PR Factory Capability Scaffold

This directory contains a small generator for future metadata-only capability
PRs. It writes inert skeleton files for capability contracts, tracer tests,
decision notes, artifact manifest/index contracts, validation checklists, and a
PR report template.

The scaffold is developer productivity tooling only. It does not change runtime
governance, issue tokens, create runners, execute adapters, launch browsers, or
access the network.

## Usage

```bash
python3 tools/pr_factory/generate_capability_scaffold.py \
  --capability-id example-capability \
  --output-dir /tmp/example-capability-scaffold
```

Optional inputs:

```bash
python3 tools/pr_factory/generate_capability_scaffold.py \
  --capability-id example-capability \
  --capability-file-name example_capability.py \
  --output-file result_contract.json \
  --output-file output_artifact_manifest.json \
  --output-dir /tmp/example-capability-scaffold
```

The generator refuses output collisions by default. Use `--allow-overwrite` only
when replacing an existing generated scaffold is intentional.

## Generated Skeleton

The default output layout is:

- `capability/<capability_file_name>`
- `tests/tracer_bullet/test_<capability_id>.py`
- `docs/decisions/<capability_id>_decision.md`
- `contracts/result_contract.md`
- `contracts/output_artifact_manifest_contract.md`
- `contracts/artifact_index_contract.md`
- `contracts/artifact_index_manifest_contract.md`
- `reports/summary.md`
- `checklists/forbidden_boundary_checklist.md`
- `reports/pr_report_template.md`
- `validation/validation_checklist.md`

## Boundary

Generated text is metadata-only and fail-closed. The default forbidden boundary
checklist includes live website automation, arbitrary URL execution, general
browser automation, account login, credential handling, cookie handling,
scraping, CAPTCHA, bypass, stealth, external network, npm install, npx install,
candidate repo runtime execution, token issuance, runner creation, adapter
execution, Playwright execution, browser opening, production promotion,
autonomous execution, and daemon/scheduler/worker loop.

## Validation

```bash
python3 -m unittest tests.tools.test_pr_factory_capability_scaffold
python3 -m unittest discover tests
make ci
git diff --check
git status --short --branch
```
