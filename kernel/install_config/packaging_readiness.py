"""Static install/config/packaging readiness checks.

The checker validates packaging metadata and console entry-point declarations.
It does not install dependencies, spawn subprocesses, access networks, or
execute entry-point callables.
"""

from __future__ import annotations

import importlib
import json
import tomllib
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from kernel.os_engine.database import (
    UnsafePayloadError,
    stable_content_hash,
    validate_no_secret_like,
)

__all__ = [
    "PackagingReadinessReport",
    "build_packaging_readiness_report",
    "render_packaging_readiness_report",
]


_PROJECT_NAME = "sovereign-engineering-os"
_REQUIRED_PYTHON = ">=3.13"
_REQUIRED_BUILD_BACKEND = "setuptools.build_meta"
_REQUIRED_DEPENDENCY_PREFIXES = ("openpyxl>=3.1",)
_REQUIRED_SCRIPTS = {
    "seos": "apps.operator_cli.main:main",
    "seos-local": "kernel.personal_ai.local_mvp_cli:main",
}
_REQUIRED_PACKAGE_INCLUDES = ("apps*", "kernel*", "tools*")


@dataclass(frozen=True, slots=True)
class PackagingReadinessReport:
    report_type: str
    repo_root: str
    pyproject_path: str
    accepted: bool
    failure_codes: tuple[str, ...]
    project_name: str
    requires_python: str
    build_backend: str
    build_requires: tuple[str, ...]
    dependencies: tuple[str, ...]
    scripts: dict[str, str]
    script_targets_importable: dict[str, bool]
    package_find_where: tuple[str, ...]
    package_find_include: tuple[str, ...]
    namespace_packages_enabled: bool
    config_hash: str
    mutation_performed: bool = False
    installation_performed: bool = False
    dependency_install_performed: bool = False
    subprocess_spawned: bool = False
    network_accessed: bool = False
    entrypoint_executed: bool = False
    secret_value_read: bool = False

    def as_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["failure_codes"] = list(self.failure_codes)
        payload["build_requires"] = list(self.build_requires)
        payload["dependencies"] = list(self.dependencies)
        payload["package_find_where"] = list(self.package_find_where)
        payload["package_find_include"] = list(self.package_find_include)
        return dict(sorted(payload.items()))

    def to_json(self) -> str:
        return json.dumps(self.as_dict(), sort_keys=True, separators=(",", ":"))


def build_packaging_readiness_report(repo_root: Path | str) -> PackagingReadinessReport:
    """Validate packaging metadata without performing installation."""

    root = Path(repo_root).expanduser().resolve(strict=False)
    pyproject_path = root / "pyproject.toml"
    if not pyproject_path.is_file():
        return _report(
            root=root,
            pyproject_path=pyproject_path,
            failure_codes=("pyproject_missing",),
        )

    try:
        pyproject = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError:
        return _report(
            root=root,
            pyproject_path=pyproject_path,
            failure_codes=("pyproject_malformed",),
        )

    try:
        validate_no_secret_like(pyproject)
    except UnsafePayloadError:
        return _report(
            root=root,
            pyproject_path=pyproject_path,
            failure_codes=("secret_like_pyproject_material",),
        )
    project = _mapping(pyproject.get("project"))
    build_system = _mapping(pyproject.get("build-system"))
    scripts = _string_mapping(project.get("scripts"))
    tool = _mapping(pyproject.get("tool"))
    setuptools = _mapping(tool.get("setuptools"))
    packages = _mapping(setuptools.get("packages"))
    package_find = _mapping(packages.get("find"))
    dependencies = tuple(str(item) for item in project.get("dependencies", ()) if isinstance(item, str))
    build_requires = tuple(str(item) for item in build_system.get("requires", ()) if isinstance(item, str))
    package_include = tuple(str(item) for item in package_find.get("include", ()) if isinstance(item, str))
    package_where = tuple(str(item) for item in package_find.get("where", ()) if isinstance(item, str))
    script_targets_importable = {
        script_name: _target_importable(target)
        for script_name, target in scripts.items()
    }

    failures: list[str] = []
    if project.get("name") != _PROJECT_NAME:
        failures.append("project_name_mismatch")
    if project.get("requires-python") != _REQUIRED_PYTHON:
        failures.append("requires_python_mismatch")
    if build_system.get("build-backend") != _REQUIRED_BUILD_BACKEND:
        failures.append("build_backend_missing")
    if not any(requirement.startswith("setuptools") for requirement in build_requires):
        failures.append("setuptools_build_requirement_missing")
    for prefix in _REQUIRED_DEPENDENCY_PREFIXES:
        if not any(dependency.startswith(prefix) for dependency in dependencies):
            failures.append("required_dependency_missing")
            break
    for script_name, target in _REQUIRED_SCRIPTS.items():
        if scripts.get(script_name) != target:
            failures.append(f"script_{script_name}_missing")
        elif not script_targets_importable.get(script_name, False):
            failures.append(f"script_{script_name}_target_not_importable")
    if "." not in package_where:
        failures.append("package_find_where_missing")
    for include_pattern in _REQUIRED_PACKAGE_INCLUDES:
        if include_pattern not in package_include:
            failures.append("package_include_missing")
            break
    if package_find.get("namespaces") is not True:
        failures.append("namespace_package_discovery_disabled")

    return _report(
        root=root,
        pyproject_path=pyproject_path,
        failure_codes=tuple(sorted(set(failures))),
        project_name=str(project.get("name", "")),
        requires_python=str(project.get("requires-python", "")),
        build_backend=str(build_system.get("build-backend", "")),
        build_requires=build_requires,
        dependencies=dependencies,
        scripts=scripts,
        script_targets_importable=script_targets_importable,
        package_find_where=package_where,
        package_find_include=package_include,
        namespace_packages_enabled=package_find.get("namespaces") is True,
    )


def render_packaging_readiness_report(report: PackagingReadinessReport) -> str:
    if not isinstance(report, PackagingReadinessReport):
        raise ValueError("report_must_be_packaging_readiness_report")
    return json.dumps(report.as_dict(), indent=2, sort_keys=True) + "\n"


def _report(
    *,
    root: Path,
    pyproject_path: Path,
    failure_codes: tuple[str, ...],
    project_name: str = "",
    requires_python: str = "",
    build_backend: str = "",
    build_requires: tuple[str, ...] = (),
    dependencies: tuple[str, ...] = (),
    scripts: dict[str, str] | None = None,
    script_targets_importable: dict[str, bool] | None = None,
    package_find_where: tuple[str, ...] = (),
    package_find_include: tuple[str, ...] = (),
    namespace_packages_enabled: bool = False,
) -> PackagingReadinessReport:
    scripts = dict(scripts or {})
    script_targets_importable = dict(script_targets_importable or {})
    config_payload = {
        "build_backend": build_backend,
        "build_requires": list(build_requires),
        "dependencies": list(dependencies),
        "package_find_include": list(package_find_include),
        "package_find_where": list(package_find_where),
        "project_name": project_name,
        "requires_python": requires_python,
        "scripts": scripts,
    }
    return PackagingReadinessReport(
        report_type="install_config_packaging_readiness_v1",
        repo_root=root.as_posix(),
        pyproject_path=pyproject_path.as_posix(),
        accepted=not failure_codes,
        failure_codes=tuple(sorted(set(failure_codes))),
        project_name=project_name,
        requires_python=requires_python,
        build_backend=build_backend,
        build_requires=build_requires,
        dependencies=dependencies,
        scripts=scripts,
        script_targets_importable=script_targets_importable,
        package_find_where=package_find_where,
        package_find_include=package_find_include,
        namespace_packages_enabled=namespace_packages_enabled,
        config_hash=stable_content_hash(config_payload),
    )


def _mapping(value: object) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _string_mapping(value: object) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}
    return {str(key): str(item) for key, item in value.items() if isinstance(item, str)}


def _target_importable(target: str) -> bool:
    module_name, separator, attribute = target.partition(":")
    if not module_name or separator != ":" or not attribute:
        return False
    try:
        module = importlib.import_module(module_name)
    except Exception:
        return False
    return callable(getattr(module, attribute, None))
