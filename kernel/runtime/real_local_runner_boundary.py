"""Controlled real local runner boundary v1.

This module admits only immutable repo-owned validation commands selected by
``command_id``. It does not accept command lines, argv overrides, shell
execution, network/browser commands, provider calls, credentials, or production
autonomy.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Mapping, Sequence
import json
import os
import subprocess
import time

from kernel.personal_ai.hash_utils import sha256_canonical_json, sha256_file
from kernel.personal_ai.io_utils import write_json_atomically

__all__ = [
    "REAL_LOCAL_RUNNER_ADAPTER_ID",
    "REAL_LOCAL_RUNNER_APPROVAL_ATTESTATION",
    "REAL_LOCAL_RUNNER_ARTIFACT_BINDING_FILE",
    "REAL_LOCAL_RUNNER_COMMAND_ALLOWLIST",
    "REAL_LOCAL_RUNNER_DESCRIPTOR_FILE",
    "REAL_LOCAL_RUNNER_FAILURE_BUNDLE_FILE",
    "REAL_LOCAL_RUNNER_RECEIPT_FILE",
    "REAL_LOCAL_RUNNER_REPLAY_MANIFEST_FILE",
    "REAL_LOCAL_RUNNER_STDERR_FILE",
    "REAL_LOCAL_RUNNER_STDOUT_FILE",
    "REAL_LOCAL_RUNNER_SUMMARY_FILE",
    "RealLocalRunnerDescriptor",
    "RealLocalRunnerResult",
    "build_real_local_runner_task_graph_node",
    "preflight_real_local_runner_descriptor",
    "run_real_local_runner_boundary",
    "run_real_local_runner_boundary_launcher",
]

REAL_LOCAL_RUNNER_ADAPTER_ID = "real_local_runner_boundary"
REAL_LOCAL_RUNNER_CAPABILITY = "launch_real_local_runner_boundary"
REAL_LOCAL_RUNNER_APPROVAL_ATTESTATION = (
    "I_REVIEWED_REAL_LOCAL_RUNNER_BOUNDARY_V1_COMMAND_ID_ONLY_"
    "NO_SHELL_NO_ARGV_OVERRIDE_NO_NETWORK_NO_BROWSER_NO_PRODUCTION"
)

REAL_LOCAL_RUNNER_DESCRIPTOR_FILE = "real_local_runner_descriptor.json"
REAL_LOCAL_RUNNER_STDOUT_FILE = "stdout.txt"
REAL_LOCAL_RUNNER_STDERR_FILE = "stderr.txt"
REAL_LOCAL_RUNNER_RECEIPT_FILE = "real_local_runner_receipt.json"
REAL_LOCAL_RUNNER_FAILURE_BUNDLE_FILE = "real_local_runner_failure_bundle.json"
REAL_LOCAL_RUNNER_REPLAY_MANIFEST_FILE = "real_local_runner_replay_manifest.json"
REAL_LOCAL_RUNNER_ARTIFACT_BINDING_FILE = "real_local_runner_artifacts.json"
REAL_LOCAL_RUNNER_SUMMARY_FILE = "real_local_runner_summary.md"

REAL_LOCAL_RUNNER_COMMAND_ALLOWLIST = MappingProxyType(
    {
        "focused_runner_chain_tests": (
            "python3",
            "-m",
            "unittest",
            "tests.tracer_bullet.test_local_fixture_runner_chain_integration",
        ),
        "full_unittest_discover": (
            "python3",
            "-m",
            "unittest",
            "discover",
            "tests",
        ),
        "make_ci": ("make", "ci"),
        "diff_check": ("git", "diff", "--check"),
    }
)

_FORBIDDEN_DESCRIPTOR_FIELDS = frozenset(
    {
        "argv",
        "args",
        "command",
        "command_line",
        "command_text",
        "shell",
        "shell_command",
        "browser",
        "url",
        "network",
        "provider_api",
        "credentials",
    }
)
_FORBIDDEN_ALLOWLIST_TOKENS = frozenset(
    {
        "bash",
        "browser",
        "curl",
        "node",
        "npm",
        "npx",
        "playwright",
        "python",
        "requests",
        "sh",
        "socket",
        "webbrowser",
        "wget",
        "zsh",
    }
)
_OUTPUT_FILES = (
    REAL_LOCAL_RUNNER_DESCRIPTOR_FILE,
    REAL_LOCAL_RUNNER_STDOUT_FILE,
    REAL_LOCAL_RUNNER_STDERR_FILE,
    REAL_LOCAL_RUNNER_RECEIPT_FILE,
    REAL_LOCAL_RUNNER_REPLAY_MANIFEST_FILE,
    REAL_LOCAL_RUNNER_ARTIFACT_BINDING_FILE,
    REAL_LOCAL_RUNNER_SUMMARY_FILE,
)


@dataclass(frozen=True)
class RealLocalRunnerDescriptor:
    """Command-id-only descriptor for a bounded local validation run."""

    command_id: str
    output_dir: Path
    approval_artifact_path: Path
    run_id: str
    timeout_seconds: float
    repo_root: Path = Path(".")
    repo_revision: str = "not_provided"

    @classmethod
    def from_mapping(
        cls,
        payload: Mapping[str, object],
        *,
        repo_root: Path | None = None,
    ) -> "RealLocalRunnerDescriptor":
        if not isinstance(payload, Mapping):
            raise ValueError("real_local_runner_descriptor_must_be_mapping")
        forbidden = sorted(
            field_name
            for field_name in payload
            if str(field_name) in _FORBIDDEN_DESCRIPTOR_FIELDS
        )
        if forbidden:
            raise ValueError(
                "real_local_runner_descriptor_forbidden_fields:"
                + ",".join(forbidden)
            )
        command_id = _required_string(payload, "command_id")
        output_dir = Path(_required_string(payload, "output_dir"))
        approval_artifact_path = Path(
            _required_string(payload, "approval_artifact_path")
        )
        run_id = _required_string(payload, "run_id")
        timeout_seconds = _required_timeout(payload.get("timeout_seconds"))
        revision = str(payload.get("repo_revision", "not_provided"))
        root = Path(payload.get("repo_root", repo_root or Path.cwd()))
        return cls(
            command_id=command_id,
            output_dir=output_dir,
            approval_artifact_path=approval_artifact_path,
            run_id=run_id,
            timeout_seconds=timeout_seconds,
            repo_root=root,
            repo_revision=revision,
        )

    @property
    def argv(self) -> tuple[str, ...]:
        try:
            return REAL_LOCAL_RUNNER_COMMAND_ALLOWLIST[self.command_id]
        except KeyError as error:
            raise ValueError("real_local_runner_command_id_not_allowlisted") from error

    def to_dict(self) -> dict[str, object]:
        return {
            "approval_artifact_path": self.approval_artifact_path.as_posix(),
            "argv_hash": sha256_canonical_json(list(self.argv)),
            "command_id": self.command_id,
            "command_id_only": True,
            "output_dir": self.output_dir.as_posix(),
            "repo_revision": self.repo_revision,
            "repo_root": self.repo_root.as_posix(),
            "run_id": self.run_id,
            "timeout_seconds": self.timeout_seconds,
            "user_argv_allowed": False,
            "user_command_line_allowed": False,
        }


@dataclass(frozen=True)
class RealLocalRunnerResult:
    """Paths and status for a controlled real local runner execution."""

    descriptor: RealLocalRunnerDescriptor
    status: str
    exit_code: int | None
    timed_out: bool
    receipt_path: Path
    stdout_path: Path
    stderr_path: Path
    replay_manifest_path: Path
    artifact_binding_path: Path
    summary_path: Path
    failure_bundle_path: Path | None

    @property
    def complete(self) -> bool:
        return self.status == "passed"

    @property
    def output_dir(self) -> Path:
        return self.descriptor.output_dir

    def to_cli_payload(self) -> dict[str, object]:
        return {
            "adapter_id": REAL_LOCAL_RUNNER_ADAPTER_ID,
            "artifact_binding_path": self.artifact_binding_path.as_posix(),
            "command_id": self.descriptor.command_id,
            "complete": self.complete,
            "exit_code": self.exit_code,
            "failure_bundle_path": None
            if self.failure_bundle_path is None
            else self.failure_bundle_path.as_posix(),
            "receipt_path": self.receipt_path.as_posix(),
            "replay_manifest_path": self.replay_manifest_path.as_posix(),
            "run_id": self.descriptor.run_id,
            "status": self.status,
            "stderr_path": self.stderr_path.as_posix(),
            "stdout_path": self.stdout_path.as_posix(),
            "summary_path": self.summary_path.as_posix(),
            "timed_out": self.timed_out,
            "required_human_approval": True,
            "production_admitted": False,
        }


def preflight_real_local_runner_descriptor(
    descriptor: RealLocalRunnerDescriptor,
) -> dict[str, object]:
    """Validate descriptor, allowlist, approval, and output sandbox."""

    failures: list[str] = []
    try:
        argv = descriptor.argv
    except ValueError as error:
        argv = ()
        failures.append(str(error))
    failures.extend(_allowlist_rejection_reasons(argv))
    failures.extend(_descriptor_rejection_reasons(descriptor))
    failures.extend(_output_sandbox_rejection_reasons(descriptor.output_dir))
    failures.extend(_approval_rejection_reasons(descriptor))
    return {
        "preflight_type": "real_local_runner_preflight_v1",
        "accepted": not failures,
        "failure_reasons": sorted(set(failures)),
        "command_id": descriptor.command_id,
        "argv_hash": sha256_canonical_json(list(argv)),
        "command_id_only": True,
        "user_command_line_allowed": False,
        "user_argv_allowed": False,
        "shell_allowed": False,
        "shell_false_required": True,
        "timeout_required": True,
        "output_sandbox_required": True,
        "network_allowed": False,
        "browser_allowed": False,
        "provider_api_allowed": False,
        "production_autonomy_allowed": False,
        "human_approval_required": True,
        "adapter_admission_status": "candidate",
    }


def run_real_local_runner_boundary_launcher(
    command_id: str,
    output_dir: Path,
    approval_artifact_path: Path,
    run_id: str,
    *,
    timeout_seconds: float,
    repo_root: Path | None = None,
    repo_revision: str = "not_provided",
) -> RealLocalRunnerResult:
    """Launcher wrapper for the controlled real local runner."""

    return run_real_local_runner_boundary(
        RealLocalRunnerDescriptor(
            command_id=command_id,
            output_dir=Path(output_dir),
            approval_artifact_path=Path(approval_artifact_path),
            run_id=run_id,
            timeout_seconds=timeout_seconds,
            repo_root=Path.cwd() if repo_root is None else Path(repo_root),
            repo_revision=repo_revision,
        )
    )


def run_real_local_runner_boundary(
    descriptor: RealLocalRunnerDescriptor,
) -> RealLocalRunnerResult:
    """Execute one allowlisted validation command and write audit artifacts."""

    preflight = preflight_real_local_runner_descriptor(descriptor)
    if not preflight["accepted"]:
        raise ValueError(
            "real_local_runner_preflight_failed:"
            + ",".join(preflight["failure_reasons"])
        )

    paths = _artifact_paths(descriptor.output_dir)
    _write_json_exclusive(paths[REAL_LOCAL_RUNNER_DESCRIPTOR_FILE], descriptor.to_dict())
    started_at = time.time()
    timed_out = False
    exit_code: int | None
    stdout_text = ""
    stderr_text = ""
    try:
        completed = subprocess.run(
            list(descriptor.argv),
            cwd=descriptor.repo_root,
            capture_output=True,
            text=True,
            timeout=descriptor.timeout_seconds,
            shell=False,
            check=False,
            env=_runner_environment(),
        )
        exit_code = completed.returncode
        stdout_text = completed.stdout
        stderr_text = completed.stderr
    except subprocess.TimeoutExpired as error:
        timed_out = True
        exit_code = None
        stdout_text = _timeout_stream_text(error.stdout)
        stderr_text = _timeout_stream_text(error.stderr)

    duration_ms = int((time.time() - started_at) * 1000)
    _write_text_exclusive(paths[REAL_LOCAL_RUNNER_STDOUT_FILE], stdout_text)
    _write_text_exclusive(paths[REAL_LOCAL_RUNNER_STDERR_FILE], stderr_text)

    status = _status(exit_code=exit_code, timed_out=timed_out)
    receipt = _receipt_payload(
        descriptor=descriptor,
        status=status,
        exit_code=exit_code,
        timed_out=timed_out,
        duration_ms=duration_ms,
        paths=paths,
    )
    _write_json_exclusive(paths[REAL_LOCAL_RUNNER_RECEIPT_FILE], receipt)

    failure_bundle_path = None
    if status != "passed":
        failure_bundle = _failure_bundle_payload(receipt)
        _write_json_exclusive(
            paths[REAL_LOCAL_RUNNER_FAILURE_BUNDLE_FILE],
            failure_bundle,
        )
        failure_bundle_path = paths[REAL_LOCAL_RUNNER_FAILURE_BUNDLE_FILE]

    replay_manifest = _replay_manifest_payload(
        descriptor=descriptor,
        receipt=receipt,
        paths=paths,
        failure_bundle_path=failure_bundle_path,
    )
    _write_json_exclusive(
        paths[REAL_LOCAL_RUNNER_REPLAY_MANIFEST_FILE],
        replay_manifest,
    )
    _write_text_exclusive(
        paths[REAL_LOCAL_RUNNER_SUMMARY_FILE],
        _summary_markdown(receipt, failure_bundle_path),
    )
    artifact_binding = _artifact_binding_payload(
        descriptor=descriptor,
        paths=paths,
        failure_bundle_path=failure_bundle_path,
    )
    _write_json_exclusive(
        paths[REAL_LOCAL_RUNNER_ARTIFACT_BINDING_FILE],
        artifact_binding,
    )
    return RealLocalRunnerResult(
        descriptor=descriptor,
        status=status,
        exit_code=exit_code,
        timed_out=timed_out,
        receipt_path=paths[REAL_LOCAL_RUNNER_RECEIPT_FILE],
        stdout_path=paths[REAL_LOCAL_RUNNER_STDOUT_FILE],
        stderr_path=paths[REAL_LOCAL_RUNNER_STDERR_FILE],
        replay_manifest_path=paths[REAL_LOCAL_RUNNER_REPLAY_MANIFEST_FILE],
        artifact_binding_path=paths[REAL_LOCAL_RUNNER_ARTIFACT_BINDING_FILE],
        summary_path=paths[REAL_LOCAL_RUNNER_SUMMARY_FILE],
        failure_bundle_path=failure_bundle_path,
    )


def build_real_local_runner_task_graph_node(
    *,
    node_id: str,
    command_id: str,
    output_dir: Path,
    approval_artifact_path: Path,
    run_id: str,
    timeout_seconds: float,
    depends_on: Sequence[str] = (),
) -> dict[str, object]:
    """Build a task-graph node descriptor for this bounded runner."""

    return {
        "adapter_id": REAL_LOCAL_RUNNER_ADAPTER_ID,
        "approval_checkpoint_required": True,
        "capability": REAL_LOCAL_RUNNER_CAPABILITY,
        "depends_on": list(depends_on),
        "execution_mode": "fixture",
        "inputs": {
            "approval_artifact_path": Path(approval_artifact_path).as_posix(),
            "command_id": command_id,
            "output_dir": Path(output_dir).as_posix(),
            "run_id": run_id,
            "timeout_seconds": timeout_seconds,
        },
        "node_id": node_id,
        "runtime_class": "controlled_local_validation",
    }


def _required_string(payload: Mapping[str, object], field_name: str) -> str:
    value = payload.get(field_name)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(field_name + "_required")
    return value.strip()


def _required_timeout(value: object) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool) or value <= 0:
        raise ValueError("timeout_seconds_must_be_positive_number")
    return float(value)


def _descriptor_rejection_reasons(
    descriptor: RealLocalRunnerDescriptor,
) -> tuple[str, ...]:
    failures: list[str] = []
    if not descriptor.run_id:
        failures.append("run_id_required")
    if descriptor.timeout_seconds <= 0:
        failures.append("timeout_seconds_required")
    if not descriptor.repo_root.exists() or not descriptor.repo_root.is_dir():
        failures.append("repo_root_missing")
    if descriptor.repo_root.is_symlink():
        failures.append("repo_root_symlink_forbidden")
    return tuple(failures)


def _allowlist_rejection_reasons(argv: Sequence[str]) -> tuple[str, ...]:
    failures: list[str] = []
    if not argv:
        failures.append("argv_missing_from_allowlist")
    for token in argv:
        normalized = token.lower()
        if normalized in _FORBIDDEN_ALLOWLIST_TOKENS:
            failures.append("forbidden_allowlist_token:" + normalized)
    for command_id, command_argv in REAL_LOCAL_RUNNER_COMMAND_ALLOWLIST.items():
        if not isinstance(command_id, str) or not command_id:
            failures.append("allowlist_command_id_invalid")
        if not command_argv or not all(
            isinstance(part, str) and part for part in command_argv
        ):
            failures.append("allowlist_argv_invalid:" + str(command_id))
    return tuple(failures)


def _output_sandbox_rejection_reasons(output_dir: Path) -> tuple[str, ...]:
    output_path = Path(output_dir)
    failures: list[str] = []
    if not output_path.exists() or not output_path.is_dir():
        failures.append("output_dir_missing")
        return tuple(failures)
    if output_path.is_symlink():
        failures.append("output_dir_symlink_forbidden")
    paths = _artifact_paths(output_path)
    for path in paths.values():
        if path.exists():
            failures.append("output_artifact_overwrite_forbidden:" + path.name)
        if path.is_symlink():
            failures.append("output_artifact_symlink_forbidden:" + path.name)
    return tuple(failures)


def _approval_rejection_reasons(
    descriptor: RealLocalRunnerDescriptor,
) -> tuple[str, ...]:
    approval_path = Path(descriptor.approval_artifact_path)
    failures: list[str] = []
    if not approval_path.exists() or not approval_path.is_file():
        return ("approval_artifact_missing",)
    if approval_path.is_symlink():
        return ("approval_artifact_symlink_forbidden",)
    try:
        payload = json.loads(approval_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return ("approval_artifact_malformed",)
    if not isinstance(payload, dict):
        return ("approval_artifact_malformed",)
    if payload.get("approval_type") != "real_local_runner_human_approval_v1":
        failures.append("approval_type_invalid")
    if payload.get("approved") is not True:
        failures.append("approval_not_granted")
    if payload.get("command_id") != descriptor.command_id:
        failures.append("approval_command_id_mismatch")
    if payload.get("run_id") != descriptor.run_id:
        failures.append("approval_run_id_mismatch")
    if payload.get("approval_attestation") != REAL_LOCAL_RUNNER_APPROVAL_ATTESTATION:
        failures.append("approval_attestation_invalid")
    approval_revision = payload.get("repo_revision")
    if (
        descriptor.repo_revision != "not_provided"
        and approval_revision != descriptor.repo_revision
    ):
        failures.append("approval_repo_revision_mismatch")
    return tuple(failures)


def _runner_environment() -> dict[str, str]:
    return {
        "LC_ALL": "C",
        "PATH": os.environ.get("PATH", "/usr/bin:/bin:/usr/sbin:/sbin"),
        "PYTHONDONTWRITEBYTECODE": "1",
        "REAL_LOCAL_RUNNER_NETWORK_ALLOWED": "0",
        "REAL_LOCAL_RUNNER_BROWSER_ALLOWED": "0",
        "REAL_LOCAL_RUNNER_PRODUCTION_AUTONOMY_ALLOWED": "0",
    }


def _artifact_paths(output_dir: Path) -> dict[str, Path]:
    output_path = Path(output_dir)
    return {
        REAL_LOCAL_RUNNER_DESCRIPTOR_FILE: output_path / REAL_LOCAL_RUNNER_DESCRIPTOR_FILE,
        REAL_LOCAL_RUNNER_STDOUT_FILE: output_path / REAL_LOCAL_RUNNER_STDOUT_FILE,
        REAL_LOCAL_RUNNER_STDERR_FILE: output_path / REAL_LOCAL_RUNNER_STDERR_FILE,
        REAL_LOCAL_RUNNER_RECEIPT_FILE: output_path / REAL_LOCAL_RUNNER_RECEIPT_FILE,
        REAL_LOCAL_RUNNER_FAILURE_BUNDLE_FILE: output_path
        / REAL_LOCAL_RUNNER_FAILURE_BUNDLE_FILE,
        REAL_LOCAL_RUNNER_REPLAY_MANIFEST_FILE: output_path
        / REAL_LOCAL_RUNNER_REPLAY_MANIFEST_FILE,
        REAL_LOCAL_RUNNER_ARTIFACT_BINDING_FILE: output_path
        / REAL_LOCAL_RUNNER_ARTIFACT_BINDING_FILE,
        REAL_LOCAL_RUNNER_SUMMARY_FILE: output_path / REAL_LOCAL_RUNNER_SUMMARY_FILE,
    }


def _write_json_exclusive(path: Path, payload: Mapping[str, object]) -> None:
    if Path(path).exists() or Path(path).is_symlink():
        raise ValueError("output_artifact_overwrite_forbidden:" + Path(path).name)
    write_json_atomically(Path(path), payload)


def _write_text_exclusive(path: Path, text: str) -> None:
    target = Path(path)
    if target.exists() or target.is_symlink():
        raise ValueError("output_artifact_overwrite_forbidden:" + target.name)
    target.write_text(text, encoding="utf-8")


def _timeout_stream_text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def _status(*, exit_code: int | None, timed_out: bool) -> str:
    if timed_out:
        return "timed_out"
    if exit_code == 0:
        return "passed"
    return "failed"


def _receipt_payload(
    *,
    descriptor: RealLocalRunnerDescriptor,
    status: str,
    exit_code: int | None,
    timed_out: bool,
    duration_ms: int,
    paths: Mapping[str, Path],
) -> dict[str, object]:
    return {
        "receipt_type": "real_local_runner_receipt_v1",
        "adapter_id": REAL_LOCAL_RUNNER_ADAPTER_ID,
        "adapter_admission_status": "candidate",
        "argv": list(descriptor.argv),
        "argv_hash": sha256_canonical_json(list(descriptor.argv)),
        "browser_allowed": False,
        "command_id": descriptor.command_id,
        "command_id_only": True,
        "duration_ms": duration_ms,
        "exit_code": exit_code,
        "human_approval_required": True,
        "network_allowed": False,
        "output_sandbox": descriptor.output_dir.as_posix(),
        "production_autonomy_allowed": False,
        "provider_api_allowed": False,
        "repo_revision": descriptor.repo_revision,
        "run_id": descriptor.run_id,
        "shell": False,
        "status": status,
        "stderr_path": paths[REAL_LOCAL_RUNNER_STDERR_FILE].as_posix(),
        "stderr_sha256": sha256_file(paths[REAL_LOCAL_RUNNER_STDERR_FILE]),
        "stdout_path": paths[REAL_LOCAL_RUNNER_STDOUT_FILE].as_posix(),
        "stdout_sha256": sha256_file(paths[REAL_LOCAL_RUNNER_STDOUT_FILE]),
        "timed_out": timed_out,
        "timeout_seconds": descriptor.timeout_seconds,
        "user_argv_allowed": False,
        "user_command_line_allowed": False,
    }


def _failure_bundle_payload(receipt: Mapping[str, object]) -> dict[str, object]:
    return {
        "failure_bundle_type": "real_local_runner_failure_bundle_v1",
        "adapter_id": REAL_LOCAL_RUNNER_ADAPTER_ID,
        "command_id": receipt["command_id"],
        "exit_code": receipt["exit_code"],
        "failure_class": "timeout"
        if receipt["timed_out"] is True
        else "nonzero_exit",
        "human_review_required": True,
        "network_allowed": False,
        "browser_allowed": False,
        "production_autonomy_allowed": False,
        "receipt_status": receipt["status"],
        "run_id": receipt["run_id"],
        "stderr_path": receipt["stderr_path"],
        "stderr_sha256": receipt["stderr_sha256"],
        "stdout_path": receipt["stdout_path"],
        "stdout_sha256": receipt["stdout_sha256"],
    }


def _replay_manifest_payload(
    *,
    descriptor: RealLocalRunnerDescriptor,
    receipt: Mapping[str, object],
    paths: Mapping[str, Path],
    failure_bundle_path: Path | None,
) -> dict[str, object]:
    return {
        "replay_manifest_type": "real_local_runner_replay_manifest_v1",
        "adapter_id": REAL_LOCAL_RUNNER_ADAPTER_ID,
        "automatic_reexecution_allowed": False,
        "argv_hash": receipt["argv_hash"],
        "command_id": descriptor.command_id,
        "command_id_match_required": True,
        "environment_digest": sha256_canonical_json(_runner_environment()),
        "failure_bundle_path": None
        if failure_bundle_path is None
        else failure_bundle_path.as_posix(),
        "output_digest_comparison_required": True,
        "receipt_path": paths[REAL_LOCAL_RUNNER_RECEIPT_FILE].as_posix(),
        "receipt_sha256": sha256_file(paths[REAL_LOCAL_RUNNER_RECEIPT_FILE]),
        "repo_revision": descriptor.repo_revision,
        "run_id": descriptor.run_id,
        "stderr_sha256": receipt["stderr_sha256"],
        "stdout_sha256": receipt["stdout_sha256"],
    }


def _artifact_binding_payload(
    *,
    descriptor: RealLocalRunnerDescriptor,
    paths: Mapping[str, Path],
    failure_bundle_path: Path | None,
) -> dict[str, object]:
    artifacts = {
        "descriptor": paths[REAL_LOCAL_RUNNER_DESCRIPTOR_FILE],
        "receipt": paths[REAL_LOCAL_RUNNER_RECEIPT_FILE],
        "replay_manifest": paths[REAL_LOCAL_RUNNER_REPLAY_MANIFEST_FILE],
        "stderr": paths[REAL_LOCAL_RUNNER_STDERR_FILE],
        "stdout": paths[REAL_LOCAL_RUNNER_STDOUT_FILE],
        "summary": paths[REAL_LOCAL_RUNNER_SUMMARY_FILE],
    }
    if failure_bundle_path is not None:
        artifacts["failure_bundle"] = failure_bundle_path
    return {
        "artifact_binding_type": "real_local_runner_artifact_binding_v1",
        "adapter_id": REAL_LOCAL_RUNNER_ADAPTER_ID,
        "artifact_count": len(artifacts),
        "artifacts": [
            {
                "path": artifact_path.as_posix(),
                "role": role,
                "sha256": sha256_file(artifact_path),
            }
            for role, artifact_path in sorted(artifacts.items())
        ],
        "command_id": descriptor.command_id,
        "output_sandbox": descriptor.output_dir.as_posix(),
        "run_id": descriptor.run_id,
    }


def _summary_markdown(
    receipt: Mapping[str, object],
    failure_bundle_path: Path | None,
) -> str:
    lines = [
        "# Real Local Runner Boundary V1",
        "",
        "Status: " + str(receipt["status"]),
        "Command ID: " + str(receipt["command_id"]),
        "Exit code: " + str(receipt["exit_code"]),
        "Timed out: " + str(receipt["timed_out"]).lower(),
        "Shell: false",
        "Network allowed: false",
        "Browser allowed: false",
        "Production autonomy allowed: false",
        "Human approval required: true",
        "Adapter admission status: candidate",
    ]
    if failure_bundle_path is not None:
        lines.append("Failure bundle: " + failure_bundle_path.as_posix())
    return "\n".join(lines) + "\n"
