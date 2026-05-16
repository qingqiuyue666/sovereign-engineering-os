# Root Integrity Verifier Foundation v1

## Verdict

`ROOT_INTEGRITY_VERIFIER_FOUNDATION_READY_FOR_LOCAL_TESTS`

This branch adds a narrow bootstrap integrity verifier for the repository root.

## Scope

This is a read-only bootstrap foundation.

It does not:

- execute runtime code
- call model APIs
- access network
- read secret values
- persist secret values
- repair files
- mutate repository files during verification
- grant runtime authority
- launch browsers
- launch creative software
- execute subprocesses
- checkpoint SQLite
- truncate WAL

## Added surfaces

- `governance/root/root_manifest_v1.json`
- `kernel/bootstrap/root_integrity_verifier.py`
- `tests/tracer_bullet/test_root_integrity_verifier.py`

## Protected foundation files

The first root manifest binds a narrow critical file set:

- `kernel/bootstrap/root_integrity_verifier.py`
- `kernel/schemas/__init__.py`
- `kernel/lifecycle/signoff_gate.py`
- `kernel/services/capability_service.py`
- `kernel/services/validation_service.py`
- `kernel/personal_ai/adapters/openai_explicit_transport.py`
- `kernel/personal_ai/model_provider_real_smoke_manual_run.py`
- `Makefile`
- `governance/constitution/sovereign_engineering_operating_system_master_plan_v11.txt`
- `governance/implementation/v11_narrow_path_implementation_foundation.md`

## Boundary invariant

Normal startup trust is not allowed unless the root manifest is well-formed and every critical file hash matches.

Failure means:

`read_only_seed_recovery_required`

## Required local verification commands

```bash
python3 -m unittest tests.tracer_bullet.test_root_integrity_verifier -v
python3 -m unittest discover -s tests/tracer_bullet -v
make ci
git diff --check
git status --short
```

## Next step

After this foundation is merged, the next narrow slice should promote this verifier into the canonical health gate so root integrity is checked before higher-level runtime smoke, model transport, or WAL planning claims are trusted.
