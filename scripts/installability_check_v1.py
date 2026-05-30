#!/usr/bin/env python3
"""Validate Wave 2 reproducibility and installability evidence."""

from __future__ import annotations

import tomllib
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = (
    Path("scripts/clean_clone_observation_smoke_v1.sh"),
    Path("scripts/fresh_venv_install_smoke_v1.sh"),
    Path("scripts/package_build_smoke_v1.sh"),
    Path("scripts/installability_check_v1.py"),
    Path("tests/tracer_bullet/test_installability_v1.py"),
)

SHELL_SCRIPTS = (
    Path("scripts/clean_clone_observation_smoke_v1.sh"),
    Path("scripts/fresh_venv_install_smoke_v1.sh"),
    Path("scripts/package_build_smoke_v1.sh"),
)

REQUIRED_MAKE_TARGETS = (
    "public-grade-check:",
    "identity-check:",
    "installability-check:",
    "test-installability:",
    "package-build-smoke:",
    "clean-clone-smoke:",
    "install-smoke:",
    "smoke:",
    "verify:",
    "final-audit-check:",
)

FORBIDDEN_SNIPPETS = (
    "curl | bash",
    "curl|bash",
    "wget | bash",
    "wget|bash",
    "gh secret",
    "printenv",
    "cat .env",
)

LOCAL_PATH_MARKERS = (
    "/" + "Users" + "/" + "qqy",
    "Documents" + "/" + "Codex",
    "." + "codex",
    "files-mentioned" + "-by-the-user",
)


def main() -> int:
    errors: list[str] = []
    _check_required_files(errors)
    _check_shell_scripts(errors)
    _check_makefile(errors)
    _check_pyproject(errors)
    _check_ci(errors)
    _check_local_path_leaks(errors)

    if errors:
        print("installability_check_v1: FAIL")
        for error in errors:
            print(f"- {error}")
        return 1

    print("installability_check_v1: PASS")
    return 0


def _check_required_files(errors: list[str]) -> None:
    for relative_path in REQUIRED_FILES:
        if not (REPO_ROOT / relative_path).exists():
            errors.append(f"missing required file: {relative_path.as_posix()}")


def _check_shell_scripts(errors: list[str]) -> None:
    for relative_path in SHELL_SCRIPTS:
        path = REPO_ROOT / relative_path
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        if not text.startswith("#!/usr/bin/env bash\n"):
            errors.append(f"{relative_path.as_posix()} missing bash shebang")
        if "set -euo pipefail" not in text:
            errors.append(f"{relative_path.as_posix()} missing set -euo pipefail")
        if "PYTHONDONTWRITEBYTECODE=1" not in text:
            errors.append(f"{relative_path.as_posix()} missing bytecode guard")
        if "echo \"" not in text or ": PASS\"" not in text:
            errors.append(f"{relative_path.as_posix()} missing explicit PASS marker")
        for snippet in FORBIDDEN_SNIPPETS:
            if snippet in text:
                errors.append(
                    f"{relative_path.as_posix()} contains forbidden snippet: {snippet}"
                )

    clean_clone_text = (REPO_ROOT / "scripts/clean_clone_observation_smoke_v1.sh").read_text(
        encoding="utf-8"
    )
    for required in (
        "git clone --no-local",
        "v0.1.0-rc3",
        "observation_check_v1.py",
        "identity_boundary_check_v1.py",
        "evidence trace",
        "replay explain",
        "ai bundle",
        "ai token-roi",
        "deterministic_local_first",
        "git status --short",
    ):
        if required not in clean_clone_text:
            errors.append(f"clean clone smoke missing required check: {required}")

    fresh_venv_text = (
        REPO_ROOT / "scripts/fresh_venv_install_smoke_v1.sh"
    ).read_text(encoding="utf-8")
    for required in (
        "python3 -m venv",
        "pip install --no-index --no-build-isolation --no-deps -e",
        "seos",
        "apps.operator_cli.main --help",
        "evidence trace",
    ):
        if required not in fresh_venv_text:
            errors.append(f"fresh venv smoke missing required check: {required}")


def _check_makefile(errors: list[str]) -> None:
    text = (REPO_ROOT / "Makefile").read_text(encoding="utf-8")
    for target in REQUIRED_MAKE_TARGETS:
        if target not in text:
            errors.append(f"Makefile missing target: {target}")


def _check_pyproject(errors: list[str]) -> None:
    payload = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    project = payload.get("project", {})
    scripts = project.get("scripts", {})
    if project.get("name") != "sovereign-engineering-os":
        errors.append("pyproject project name mismatch")
    if scripts.get("seos") != "apps.operator_cli.main:main":
        errors.append("pyproject missing seos entrypoint")
    if scripts.get("seos-local") != "kernel.personal_ai.local_mvp_cli:main":
        errors.append("pyproject missing seos-local entrypoint")


def _check_ci(errors: list[str]) -> None:
    ci_path = REPO_ROOT / ".github" / "workflows" / "ci.yml"
    if not ci_path.exists():
        errors.append("missing GitHub Actions CI workflow")
        return
    text = ci_path.read_text(encoding="utf-8")
    for required in (
        "scripts/observation_check_v1.py",
        "scripts/identity_boundary_check_v1.py",
        "scripts/installability_check_v1.py",
        "scripts/package_build_smoke_v1.sh",
        "scripts/fresh_venv_install_smoke_v1.sh",
        "make ci",
    ):
        if required not in text:
            errors.append(f"CI workflow missing gate: {required}")


def _check_local_path_leaks(errors: list[str]) -> None:
    checked_paths = [
        *(REPO_ROOT / path for path in REQUIRED_FILES),
        REPO_ROOT / "Makefile",
        REPO_ROOT / ".github" / "workflows" / "ci.yml",
    ]
    for path in checked_paths:
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        for marker in LOCAL_PATH_MARKERS:
            if marker in text:
                errors.append(
                    f"local path leak marker {marker!r} found in "
                    f"{path.relative_to(REPO_ROOT).as_posix()}"
                )


if __name__ == "__main__":
    raise SystemExit(main())
