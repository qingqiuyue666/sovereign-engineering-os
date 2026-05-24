#!/usr/bin/env python3
"""Deterministic PR readiness and merge-audit artifact tooling.

This module evaluates caller-provided evidence only. It does not call GitHub,
push branches, merge pull requests, delete branches, execute tests, launch
browsers, or access the network.
"""

from __future__ import annotations

import argparse
import json
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Mapping, Sequence

__all__ = [
    "AUDIT_RECOMMENDATIONS",
    "REQUIRED_PR_BODY_SECTIONS",
    "REQUIRED_TEST_COMMANDS",
    "ChangedFileScopeResult",
    "ForbiddenSurfaceResult",
    "PRBodyContractResult",
    "TestChecklistResult",
    "FixtureCIStatusReader",
    "MergeAuditInput",
    "MergeAuditArtifact",
    "check_changed_file_scope",
    "scan_forbidden_surfaces",
    "validate_required_test_checklist",
    "validate_pr_body_contract",
    "build_merge_audit_artifact",
    "write_merge_audit_artifact",
]


AUDIT_RECOMMENDATIONS = (
    "MERGE_ALLOWED",
    "DO_NOT_MERGE",
    "WAITING_FOR_CI",
    "BLOCKED",
)

REQUIRED_PR_BODY_SECTIONS = (
    "## Scope summary",
    "## Changed files",
    "## Boundary statement",
    "## Dependency status",
    "## Test commands and results",
    "## Forbidden-surface confirmation",
    "## Remaining blockers",
    "## Audit packet",
)

REQUIRED_TEST_COMMANDS = (
    "focused_tests",
    "python3 -m unittest discover tests",
    "make ci",
    "git diff --check",
)

_FORBIDDEN_SURFACE_PATTERNS = {
    "subprocess_execution": r"\bsubprocess\.(run|Popen|call|check_call|check_output)\b",
    "shell_true": r"\bshell\s*=\s*True\b",
    "arbitrary_command_line": r"\bcommand_line\b",
    "browser_opening": r"\bwebbrowser\.open\b|\bbrowser\.launch\b|\bopen_browser\s*\(",
    "network_access": r"\brequests\.|\burllib\.|\bhttp\.client\b|\bsocket\b|\burlopen\s*\(",
    "live_playwright": r"\bplaywright\b|\bnpx\s+playwright\b",
    "provider_live_call": r"\bapi_key\b|\bprovider_api\b|\blive_provider_call\b",
    "production_autonomy": r"\bproduction_autonomy\b|\bauto_?approve\b",
    "auto_merge": r"\bauto-merge\b|\bauto_merge\b|\bmerge_now\b",
    "branch_deletion": r"\bdelete_branch\b|\bgit\s+branch\s+-D\b|\bgit\s+push\s+origin\s+--delete\b",
    "direct_main_push": r"\bgit\s+push\s+origin\s+main\b|\bpush_to_main\b",
}

_PATH_RE = re.compile(r"^[A-Za-z0-9._@/+:-]+$")


@dataclass(frozen=True)
class ChangedFileScopeResult:
    changed_files: tuple[str, ...]
    allowed_prefixes: tuple[str, ...]
    out_of_scope_files: tuple[str, ...]
    invalid_paths: tuple[str, ...]

    @property
    def passed(self) -> bool:
        return not self.out_of_scope_files and not self.invalid_paths

    def as_dict(self) -> dict[str, object]:
        return {
            "passed": self.passed,
            "changed_files": list(self.changed_files),
            "allowed_prefixes": list(self.allowed_prefixes),
            "out_of_scope_files": list(self.out_of_scope_files),
            "invalid_paths": list(self.invalid_paths),
        }


@dataclass(frozen=True)
class ForbiddenSurfaceResult:
    scanned_files: tuple[str, ...]
    violations: tuple[dict[str, str], ...]

    @property
    def passed(self) -> bool:
        return not self.violations

    def as_dict(self) -> dict[str, object]:
        return {
            "passed": self.passed,
            "scanned_files": list(self.scanned_files),
            "violations": list(self.violations),
        }


@dataclass(frozen=True)
class TestChecklistResult:
    required_commands: tuple[str, ...]
    missing_commands: tuple[str, ...]
    failed_commands: tuple[str, ...]

    @property
    def passed(self) -> bool:
        return not self.missing_commands and not self.failed_commands

    def as_dict(self) -> dict[str, object]:
        return {
            "passed": self.passed,
            "required_commands": list(self.required_commands),
            "missing_commands": list(self.missing_commands),
            "failed_commands": list(self.failed_commands),
        }


@dataclass(frozen=True)
class PRBodyContractResult:
    missing_sections: tuple[str, ...]

    @property
    def passed(self) -> bool:
        return not self.missing_sections

    def as_dict(self) -> dict[str, object]:
        return {
            "passed": self.passed,
            "required_sections": list(REQUIRED_PR_BODY_SECTIONS),
            "missing_sections": list(self.missing_sections),
        }


@dataclass(frozen=True)
class MergeAuditInput:
    milestone: str
    branch: str
    pr_url: str
    head_sha: str
    base_sha: str
    changed_files: tuple[str, ...]
    allowed_file_prefixes: tuple[str, ...]
    file_text_by_path: dict[str, str]
    test_results: dict[str, str]
    pr_body: str
    ci_status_payload: dict[str, object]
    blockers: tuple[str, ...] = ()
    dependency_notes: tuple[str, ...] = ()


@dataclass(frozen=True)
class MergeAuditArtifact:
    artifact_type: str
    recommendation: str
    milestone: str
    branch: str
    pr_url: str
    head_sha: str
    base_sha: str
    changed_files: tuple[str, ...]
    scope: ChangedFileScopeResult
    forbidden_surfaces: ForbiddenSurfaceResult
    test_checklist: TestChecklistResult
    pr_body_contract: PRBodyContractResult
    ci_status: dict[str, object]
    blockers: tuple[str, ...]
    dependency_notes: tuple[str, ...]
    human_merge_required: bool = True
    merge_performed: bool = False
    branch_deleted: bool = False
    direct_main_push_performed: bool = False
    auto_merge_enabled: bool = False

    def as_dict(self) -> dict[str, object]:
        return {
            "artifact_type": self.artifact_type,
            "recommendation": self.recommendation,
            "milestone": self.milestone,
            "branch": self.branch,
            "pr_url": self.pr_url,
            "head_sha": self.head_sha,
            "base_sha": self.base_sha,
            "changed_files": list(self.changed_files),
            "scope": self.scope.as_dict(),
            "forbidden_surfaces": self.forbidden_surfaces.as_dict(),
            "test_checklist": self.test_checklist.as_dict(),
            "pr_body_contract": self.pr_body_contract.as_dict(),
            "ci_status": self.ci_status,
            "blockers": list(self.blockers),
            "dependency_notes": list(self.dependency_notes),
            "human_merge_required": self.human_merge_required,
            "merge_performed": self.merge_performed,
            "branch_deleted": self.branch_deleted,
            "direct_main_push_performed": self.direct_main_push_performed,
            "auto_merge_enabled": self.auto_merge_enabled,
        }


class FixtureCIStatusReader:
    """Read CI status from caller-provided fixture data only."""

    def __init__(self, payload: Mapping[str, object]):
        self._payload = dict(payload)

    def read(self) -> dict[str, object]:
        status = self._payload.get("status")
        run_url = self._payload.get("run_url")
        checks = self._payload.get("checks", [])
        if status not in {"pass", "fail", "pending", "missing"}:
            raise ValueError("ci_status_fixture_status_invalid")
        if run_url is not None and not isinstance(run_url, str):
            raise ValueError("ci_status_fixture_run_url_invalid")
        if not isinstance(checks, list):
            raise ValueError("ci_status_fixture_checks_invalid")
        return {
            "reader": "fixture_only",
            "status": status,
            "run_url": run_url or "",
            "checks": checks,
            "live_github_api_called": False,
        }


def check_changed_file_scope(
    changed_files: Sequence[str],
    allowed_prefixes: Sequence[str],
) -> ChangedFileScopeResult:
    normalized_files = tuple(str(item) for item in changed_files)
    prefixes = tuple(_normalize_prefix(item) for item in allowed_prefixes)
    invalid = tuple(path for path in normalized_files if not _valid_repo_path(path))
    out_of_scope = tuple(
        path
        for path in normalized_files
        if path not in invalid and not any(path == prefix or path.startswith(prefix) for prefix in prefixes)
    )
    return ChangedFileScopeResult(
        changed_files=normalized_files,
        allowed_prefixes=prefixes,
        out_of_scope_files=out_of_scope,
        invalid_paths=invalid,
    )


def scan_forbidden_surfaces(file_text_by_path: Mapping[str, str]) -> ForbiddenSurfaceResult:
    violations: list[dict[str, str]] = []
    scanned: list[str] = []
    for path, text in sorted(file_text_by_path.items()):
        if not _valid_repo_path(path):
            violations.append({"path": path, "surface": "invalid_path", "match": path})
            continue
        scanned.append(path)
        if not isinstance(text, str):
            violations.append({"path": path, "surface": "non_text_input", "match": ""})
            continue
        for surface, pattern in sorted(_FORBIDDEN_SURFACE_PATTERNS.items()):
            match = re.search(pattern, text)
            if match:
                violations.append(
                    {
                        "path": path,
                        "surface": surface,
                        "match": match.group(0),
                    }
                )
    return ForbiddenSurfaceResult(
        scanned_files=tuple(scanned),
        violations=tuple(violations),
    )


def validate_required_test_checklist(
    test_results: Mapping[str, str],
) -> TestChecklistResult:
    missing: list[str] = []
    failed: list[str] = []
    for command in REQUIRED_TEST_COMMANDS:
        value = test_results.get(command)
        if value is None:
            missing.append(command)
        elif value != "pass":
            failed.append(command)
    return TestChecklistResult(
        required_commands=REQUIRED_TEST_COMMANDS,
        missing_commands=tuple(missing),
        failed_commands=tuple(failed),
    )


def validate_pr_body_contract(pr_body: str) -> PRBodyContractResult:
    missing = tuple(section for section in REQUIRED_PR_BODY_SECTIONS if section not in pr_body)
    return PRBodyContractResult(missing_sections=missing)


def build_merge_audit_artifact(material: MergeAuditInput) -> MergeAuditArtifact:
    scope = check_changed_file_scope(
        material.changed_files,
        material.allowed_file_prefixes,
    )
    forbidden = scan_forbidden_surfaces(material.file_text_by_path)
    tests = validate_required_test_checklist(material.test_results)
    body = validate_pr_body_contract(material.pr_body)
    ci_status = FixtureCIStatusReader(material.ci_status_payload).read()
    recommendation = _recommendation(
        blockers=material.blockers,
        scope=scope,
        forbidden=forbidden,
        tests=tests,
        body=body,
        ci_status=ci_status,
    )
    return MergeAuditArtifact(
        artifact_type="pr_factory_merge_audit_v1",
        recommendation=recommendation,
        milestone=material.milestone,
        branch=material.branch,
        pr_url=material.pr_url,
        head_sha=material.head_sha,
        base_sha=material.base_sha,
        changed_files=material.changed_files,
        scope=scope,
        forbidden_surfaces=forbidden,
        test_checklist=tests,
        pr_body_contract=body,
        ci_status=ci_status,
        blockers=material.blockers,
        dependency_notes=material.dependency_notes,
    )


def write_merge_audit_artifact(
    output_path: Path,
    artifact: MergeAuditArtifact,
) -> None:
    target = Path(output_path)
    if target.exists():
        raise ValueError("merge_audit_artifact_output_exists")
    if not target.parent.exists() or not target.parent.is_dir():
        raise ValueError("merge_audit_artifact_parent_missing")

    data = json.dumps(artifact.as_dict(), indent=2, sort_keys=True) + "\n"
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=target.parent,
        prefix=f".{target.name}.",
        suffix=".tmp",
        delete=False,
    ) as handle:
        temp_path = Path(handle.name)
        handle.write(data)
        handle.flush()
    temp_path.replace(target)


def _recommendation(
    *,
    blockers: Sequence[str],
    scope: ChangedFileScopeResult,
    forbidden: ForbiddenSurfaceResult,
    tests: TestChecklistResult,
    body: PRBodyContractResult,
    ci_status: Mapping[str, object],
) -> str:
    if blockers:
        return "BLOCKED"
    if ci_status["status"] == "pending":
        return "WAITING_FOR_CI"
    if ci_status["status"] in {"fail", "missing"}:
        return "DO_NOT_MERGE"
    if not scope.passed or not forbidden.passed or not tests.passed or not body.passed:
        return "DO_NOT_MERGE"
    return "MERGE_ALLOWED"


def _valid_repo_path(path: str) -> bool:
    if not isinstance(path, str) or not path or not _PATH_RE.fullmatch(path):
        return False
    parsed = PurePosixPath(path)
    return not parsed.is_absolute() and ".." not in parsed.parts and "." not in parsed.parts


def _normalize_prefix(prefix: str) -> str:
    value = str(prefix).strip()
    if not value:
        raise ValueError("allowed_prefix_empty")
    if not _valid_repo_path(value.rstrip("/")):
        raise ValueError("allowed_prefix_invalid")
    return value if value.endswith("/") else value + "/"


def _load_input(path: Path) -> MergeAuditInput:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return MergeAuditInput(
        milestone=str(payload["milestone"]),
        branch=str(payload["branch"]),
        pr_url=str(payload["pr_url"]),
        head_sha=str(payload["head_sha"]),
        base_sha=str(payload["base_sha"]),
        changed_files=tuple(str(item) for item in payload["changed_files"]),
        allowed_file_prefixes=tuple(str(item) for item in payload["allowed_file_prefixes"]),
        file_text_by_path={str(key): str(value) for key, value in payload["file_text_by_path"].items()},
        test_results={str(key): str(value) for key, value in payload["test_results"].items()},
        pr_body=str(payload["pr_body"]),
        ci_status_payload=dict(payload["ci_status_payload"]),
        blockers=tuple(str(item) for item in payload.get("blockers", ())),
        dependency_notes=tuple(str(item) for item in payload.get("dependency_notes", ())),
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a fixture-only PR merge-audit recommendation artifact.",
    )
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    artifact = build_merge_audit_artifact(_load_input(args.input))
    write_merge_audit_artifact(args.output, artifact)
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
