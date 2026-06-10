# Install Config Packaging Readiness V1

Status: implemented as an independent packaging/config slice.

## Scope

This slice makes the repository packaging metadata concrete and validates it
without performing installation.

Implemented surfaces:

- `pyproject.toml` build backend and console entry points
- `kernel/install_config/packaging_readiness.py`
- `tools/install_config_readiness.py`
- focused tracer-bullet tests
- acceptance coverage for static install/config/packaging readiness

## Packaging Metadata

The package metadata now declares:

- `setuptools.build_meta` as the build backend
- `setuptools>=69` as the build-system requirement
- `seos = apps.operator_cli.main:main`
- `seos-local = kernel.personal_ai.local_mvp_cli:main`
- namespace-aware package discovery for `apps*`, `kernel*`, and `tools*`

## Readiness Checker

The readiness checker validates:

- project name
- Python requirement
- build backend
- build-system requirements
- required runtime dependency declaration
- console script targets
- importability of entry-point modules and callables
- package discovery includes
- namespace package discovery

The checker emits a deterministic `config_hash` over accepted packaging
configuration.

## Boundaries

This slice does not:

- install the project
- install dependencies
- run package manager commands
- spawn subprocesses
- access networks
- execute entry-point callables
- read secret values
- mutate repository files at runtime

The CLI renders JSON readiness only and exits nonzero if the metadata is not
ready.

## Failure Paths

Fail-closed outcomes include:

- `pyproject_missing`
- `pyproject_malformed`
- `secret_like_pyproject_material`
- `project_name_mismatch`
- `requires_python_mismatch`
- `build_backend_missing`
- `setuptools_build_requirement_missing`
- `required_dependency_missing`
- `script_seos_missing`
- `script_seos_target_not_importable`
- `script_seos-local_missing`
- `script_seos-local_target_not_importable`
- `package_find_where_missing`
- `package_include_missing`
- `namespace_package_discovery_disabled`

## Dependency Blockers Recorded

The open draft PRs #497 through #505 remain unmerged. This packaging readiness
slice does not depend on, recreate, or duplicate those contract PRs.

## Validation

Focused validation:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.tracer_bullet.test_install_config_packaging_readiness -v
```

Acceptance validation:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest validation.tests.acceptance.test_install_config_packaging_readiness_v1 -v
```
