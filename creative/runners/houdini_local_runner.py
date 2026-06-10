"""Truthful local Houdini/hython smoke runner."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Final
import hashlib
import json
import os
import re
import shutil
import signal
import subprocess
import tempfile
import time

from creative.common import sanitize_path, write_json

RUNNER_SCHEMA_VERSION: Final[str] = "seos_houdini_local_runner_v1"
SMOKE_OUTPUT_NAME: Final[str] = "hython_smoke_output_v1.json"
DEFAULT_TIMEOUT_SECONDS: Final[float] = 30.0
MAX_TIMEOUT_SECONDS: Final[float] = 600.0
MAX_OUTPUT_CHARS: Final[int] = 80_000
READ_CHUNK_BYTES: Final[int] = 1024 * 1024
SECRET_ENV_MARKERS: Final[tuple[str, ...]] = (
    "AUTH",
    "BEARER",
    "CREDENTIAL",
    "KEY",
    "PASSWORD",
    "SECRET",
    "TOKEN",
)
CHILD_ENV_ALLOWLIST: Final[frozenset[str]] = frozenset(
    {
        "DYLD_LIBRARY_PATH",
        "H",
        "HB",
        "HFS",
        "HH",
        "HHP",
        "HIP",
        "HOME",
        "HOUDINI_PACKAGE_DIR",
        "HOUDINI_PATH",
        "HOUDINI_TEMP_DIR",
        "HOUDINI_USER_PREF_DIR",
        "LANG",
        "LC_ALL",
        "LD_LIBRARY_PATH",
        "PATH",
        "PYTHONHOME",
        "PYTHONPATH",
        "SHELL",
        "TMPDIR",
        "USER",
    }
)
LICENSE_BLOCK_MARKERS: Final[tuple[str, ...]] = (
    "license",
    "hserver",
    "sesinetd",
    "no server",
    "not logged into the license server",
    "unable to connect to hserver",
    "cannot connect to license",
    "no licenses could be found",
)
SAFE_APPROVAL_RE: Final[re.Pattern[str]] = re.compile(r"\A[A-Za-z0-9][A-Za-z0-9._:-]{0,127}\Z")


class HoudiniLocalRunnerError(RuntimeError):
    """Raised when the Houdini smoke request is structurally unsafe."""


@dataclass(frozen=True, slots=True)
class HythonDiscovery:
    status: str
    source: str
    path: str
    checked_candidates: tuple[str, ...]

    @property
    def found(self) -> bool:
        return self.status == "FOUND_BUT_UNTESTED" and bool(self.path)

    def as_dict(self, *, mode: str) -> dict[str, object]:
        return {
            "checked_candidates": [_report_path(path, mode=mode) for path in self.checked_candidates],
            "path": _report_path(self.path, mode=mode),
            "source": self.source,
            "status": self.status,
        }


@dataclass(frozen=True, slots=True)
class HoudiniSmokeRequest:
    output_root: Path | str
    hython_executable: Path | str | None = None
    mode: str = "public"
    approved: bool = False
    approval_id: str = ""
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS
    observed_at: str | None = None
    environ: Mapping[str, str] | None = None

    def validated(self) -> HoudiniSmokeRequest:
        if self.mode not in {"public", "local"}:
            raise HoudiniLocalRunnerError("mode must be public or local")
        output_root = Path(self.output_root).expanduser().resolve()
        if output_root.exists() and not output_root.is_dir():
            raise HoudiniLocalRunnerError("output_root must be a directory")
        if output_root.exists() and output_root.is_symlink():
            raise HoudiniLocalRunnerError("output_root may not be a symlink")
        if self.timeout_seconds <= 0 or self.timeout_seconds > MAX_TIMEOUT_SECONDS:
            raise HoudiniLocalRunnerError(
                f"timeout_seconds must be within (0, {MAX_TIMEOUT_SECONDS}]"
            )
        approval_id = str(self.approval_id or "")
        if self.approved and not SAFE_APPROVAL_RE.fullmatch(approval_id):
            raise HoudiniLocalRunnerError("approved Houdini smoke requires a safe approval_id")
        return HoudiniSmokeRequest(
            output_root=output_root,
            hython_executable=self.hython_executable,
            mode=self.mode,
            approved=bool(self.approved),
            approval_id=approval_id,
            timeout_seconds=float(self.timeout_seconds),
            observed_at=self.observed_at,
            environ=dict(self.environ) if self.environ is not None else None,
        )


def run_houdini_hython_smoke(request: HoudiniSmokeRequest) -> dict[str, object]:
    """Run or truthfully skip a minimal hython smoke according to local state."""

    admitted = request.validated()
    observed_at = admitted.observed_at or _now()
    discovery = discover_hython(
        explicit_hython=admitted.hython_executable,
        environ=admitted.environ,
    )
    output_file = admitted.output_root / SMOKE_OUTPUT_NAME
    materialization = _materialization(
        status="blocked_resource_missing",
        output_file=output_file,
        output_root=admitted.output_root,
        output_sha256="",
        reasons=("hython executable unavailable",),
        mode=admitted.mode,
    )
    base = _base_result(
        admitted,
        discovery=discovery,
        observed_at=observed_at,
        output_file=output_file,
    )

    if not discovery.found:
        return {
            **base,
            "status": "ENV_NOT_FOUND",
            "complete": False,
            "execution_attempted": False,
            "error_code": "ENV_NOT_FOUND",
            "process": _empty_process(),
            "output": _output_metadata(output_file, admitted.output_root, mode=admitted.mode),
            "materialization": materialization,
            "next_actions": [
                "Install Houdini/hython, add hython to PATH, or set SEOS_HYTHON_PATH.",
            ],
        }

    if not admitted.approved:
        return {
            **base,
            "status": "USER_APPROVAL_REQUIRED",
            "complete": False,
            "execution_attempted": False,
            "error_code": "USER_APPROVAL_REQUIRED",
            "process": _empty_process(),
            "output": _output_metadata(output_file, admitted.output_root, mode=admitted.mode),
            "materialization": _materialization(
                status="blocked_human_review_required",
                output_file=output_file,
                output_root=admitted.output_root,
                output_sha256="",
                reasons=("explicit human approval is required before launching hython",),
                mode=admitted.mode,
            ),
            "next_actions": [
                "Rerun with --approve-local-execution and a safe --approval-id after operator review.",
            ],
        }

    admitted.output_root.mkdir(parents=True, exist_ok=True)
    _ensure_contained(output_file, admitted.output_root)
    if output_file.exists():
        raise HoudiniLocalRunnerError("refusing to overwrite existing Houdini smoke output")

    process = _run_hython_process(
        hython_path=discovery.path,
        output_file=output_file,
        output_root=admitted.output_root,
        timeout_seconds=admitted.timeout_seconds,
        environ=admitted.environ,
    )
    output = _output_metadata(output_file, admitted.output_root, mode=admitted.mode)
    status, error_code, reasons = _classify_process(process, output_exists=output_file.is_file())
    if output.get("sha256"):
        materialization = _materialization(
            status="materialized_valid" if status == "EXECUTED" else "blocked_validation_failed",
            output_file=output_file,
            output_root=admitted.output_root,
            output_sha256=str(output.get("sha256") or ""),
            reasons=reasons,
            mode=admitted.mode,
        )
    else:
        materialization = _materialization(
            status="blocked_validation_failed",
            output_file=output_file,
            output_root=admitted.output_root,
            output_sha256="",
            reasons=reasons,
            mode=admitted.mode,
        )
    return {
        **base,
        "status": status,
        "complete": status == "EXECUTED",
        "execution_attempted": True,
        "error_code": error_code,
        "process": process.as_dict(mode=admitted.mode),
        "output": output,
        "materialization": materialization,
        "next_actions": _next_actions(status),
    }


def write_houdini_smoke_reports(
    result: dict[str, object],
    *,
    result_json: Path | None = None,
    materialization_json: Path | None = None,
) -> dict[str, str]:
    outputs: dict[str, str] = {}
    if result_json is not None:
        write_json(result_json, result)
        outputs["result_json"] = result_json.as_posix()
    if materialization_json is not None:
        write_json(materialization_json, result.get("materialization", {}))
        outputs["materialization_json"] = materialization_json.as_posix()
    return outputs


def discover_hython(
    *,
    explicit_hython: Path | str | None = None,
    environ: Mapping[str, str] | None = None,
) -> HythonDiscovery:
    env = dict(os.environ if environ is None else environ)
    candidates: list[tuple[str, str]] = []
    if explicit_hython:
        candidates.append(("explicit", str(explicit_hython)))
    else:
        if env.get("SEOS_HYTHON_PATH"):
            candidates.append(("SEOS_HYTHON_PATH", str(env["SEOS_HYTHON_PATH"])))
        which_hython = shutil.which("hython", path=env.get("PATH"))
        if which_hython:
            candidates.append(("PATH", which_hython))
        for path in _common_hython_paths():
            candidates.append(("common_install_path", path.as_posix()))

    checked: list[str] = []
    for source, candidate in candidates:
        checked.append(candidate)
        path = _candidate_path(candidate)
        if path is None:
            continue
        if path.exists() and path.is_file() and os.access(path, os.X_OK):
            return HythonDiscovery(
                status="FOUND_BUT_UNTESTED",
                source=source,
                path=path.as_posix(),
                checked_candidates=tuple(checked),
            )
    return HythonDiscovery(
        status="NOT_FOUND",
        source="not_found",
        path="",
        checked_candidates=tuple(checked),
    )


@dataclass(frozen=True, slots=True)
class _ProcessResult:
    returncode: int
    duration_seconds: float
    timed_out: bool
    stdout: str
    stderr: str

    def as_dict(self, *, mode: str) -> dict[str, object]:
        payload: dict[str, object] = {
            "duration_seconds": round(self.duration_seconds, 6),
            "returncode": self.returncode,
            "stderr_sha256": _sha256_text(self.stderr),
            "stdout_sha256": _sha256_text(self.stdout),
            "timed_out": self.timed_out,
        }
        if mode == "local":
            payload["stdout"] = _clip(self.stdout)
            payload["stderr"] = _clip(self.stderr)
        return payload


def _run_hython_process(
    *,
    hython_path: str,
    output_file: Path,
    output_root: Path,
    timeout_seconds: float,
    environ: Mapping[str, str] | None,
) -> _ProcessResult:
    with tempfile.TemporaryDirectory(prefix="seos_hython_smoke_") as temp_dir_name:
        temp_dir = Path(temp_dir_name)
        driver_path = temp_dir / "hython_smoke_driver.py"
        driver_path.write_text(_HYTHON_SMOKE_DRIVER, encoding="utf-8")
        argv = (hython_path, driver_path.as_posix(), output_file.as_posix())
        start = time.monotonic()
        process = subprocess.Popen(
            argv,
            cwd=output_root,
            env=_build_child_env(environ),
            shell=False,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            start_new_session=(os.name != "nt"),
        )
        timed_out = False
        try:
            stdout, stderr = process.communicate(timeout=timeout_seconds)
        except subprocess.TimeoutExpired:
            timed_out = True
            _terminate_process(process)
            stdout, stderr = process.communicate(timeout=10)
        duration = time.monotonic() - start
    return _ProcessResult(
        returncode=int(process.returncode) if process.returncode is not None else -1,
        duration_seconds=duration,
        timed_out=timed_out,
        stdout=_clip(stdout),
        stderr=_clip(stderr),
    )


def _base_result(
    request: HoudiniSmokeRequest,
    *,
    discovery: HythonDiscovery,
    observed_at: str,
    output_file: Path,
) -> dict[str, object]:
    return {
        "approval": {
            "approval_id": request.approval_id,
            "approved": request.approved,
            "required": True,
        },
        "destructive_actions_performed": False,
        "hython": discovery.as_dict(mode=request.mode),
        "kind": "houdini_hython_smoke_result_v1",
        "mode": request.mode,
        "observed_at": observed_at,
        "ok": True,
        "output_root": _report_path(request.output_root, mode=request.mode),
        "planned_output": _relative_to(output_file, request.output_root),
        "schema_version": RUNNER_SCHEMA_VERSION,
        "safety": {
            "arbitrary_command_allowed": False,
            "dcc_execution_requires_approval": True,
            "license_checkout_possible_when_executed": True,
            "network_required_by_seos": False,
            "shell": False,
        },
    }


def _classify_process(
    process: _ProcessResult,
    *,
    output_exists: bool,
) -> tuple[str, str | None, tuple[str, ...]]:
    combined = f"{process.stdout}\n{process.stderr}".lower()
    if process.timed_out:
        return "LONG_TASK_BLOCKED", "LONG_TASK_BLOCKED", ("hython smoke timed out",)
    if process.returncode != 0 and any(marker in combined for marker in LICENSE_BLOCK_MARKERS):
        return "LICENSE_BLOCKED", "LICENSE_BLOCKED", ("hython reported a license or hserver problem",)
    if process.returncode != 0:
        return "EXECUTION_FAILED", "VALIDATION_FAILED", (f"hython exited with return code {process.returncode}",)
    if not output_exists:
        return "EXECUTION_FAILED", "FILE_MISSING", ("hython smoke did not create the expected output file",)
    return "EXECUTED", None, ("hython smoke output materialized",)


def _materialization(
    *,
    status: str,
    output_file: Path,
    output_root: Path,
    output_sha256: str,
    reasons: tuple[str, ...],
    mode: str,
) -> dict[str, object]:
    return {
        "kind": "houdini_hython_smoke_materialization_v1",
        "reasons": list(reasons),
        "status": status,
        "target": {
            "artifact_type": "houdini_hython_smoke_output",
            "relative_path": _relative_to(output_file, output_root),
            "sha256": output_sha256,
        },
        "target_root": _report_path(output_root, mode=mode),
    }


def _output_metadata(output_file: Path, output_root: Path, *, mode: str) -> dict[str, object]:
    metadata: dict[str, object] = {
        "exists": output_file.is_file(),
        "path": _report_path(output_file, mode=mode),
        "relative_path": _relative_to(output_file, output_root),
        "sha256": "",
        "size_bytes": 0,
    }
    if output_file.is_file():
        metadata["sha256"] = _sha256_file(output_file)
        metadata["size_bytes"] = output_file.stat().st_size
    return metadata


def _empty_process() -> dict[str, object]:
    return {
        "duration_seconds": 0.0,
        "returncode": None,
        "stderr_sha256": _sha256_text(""),
        "stdout_sha256": _sha256_text(""),
        "timed_out": False,
    }


def _next_actions(status: str) -> list[str]:
    if status == "EXECUTED":
        return ["Review the smoke output and proceed to a gated Houdini render test if needed."]
    if status == "LICENSE_BLOCKED":
        return ["Resolve Houdini licensing or hserver availability, then rerun the smoke."]
    if status == "LONG_TASK_BLOCKED":
        return ["Increase timeout only after confirming the local hython process is healthy."]
    return ["Inspect the result envelope and rerun after fixing the reported issue."]


def _build_child_env(environ: Mapping[str, str] | None) -> dict[str, str]:
    source = os.environ if environ is None else environ
    env: dict[str, str] = {}
    for key, value in source.items():
        upper_key = key.upper()
        if any(marker in upper_key for marker in SECRET_ENV_MARKERS):
            continue
        if key in CHILD_ENV_ALLOWLIST:
            env[key] = str(value)
    env["HOUDINI_NO_SPLASH"] = "1"
    env["HOUDINI_SCRIPT_DEBUG"] = "0"
    env["PYTHONUNBUFFERED"] = "1"
    return env


def _terminate_process(process: subprocess.Popen[str]) -> None:
    if process.poll() is not None:
        return
    if os.name != "nt":
        try:
            os.killpg(process.pid, signal.SIGTERM)
            process.wait(timeout=3)
            return
        except (OSError, subprocess.TimeoutExpired):
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except OSError:
                pass
            return
    process.kill()


def _candidate_path(candidate: str) -> Path | None:
    if any(character in candidate for character in ("\x00", "\n", "\r")):
        return None
    if "/" in candidate or "\\" in candidate:
        return Path(candidate).expanduser().resolve()
    resolved = shutil.which(candidate)
    return Path(resolved).resolve() if resolved else None


def _common_hython_paths() -> tuple[Path, ...]:
    patterns = (
        "/Applications/Houdini/Houdini*/Frameworks/Houdini.framework/Versions/Current/Resources/bin/hython",
        "/Applications/Houdini/Houdini*/Frameworks/Houdini.framework/Versions/*/Resources/bin/hython",
        "/Applications/Houdini/Houdini*/bin/hython",
        "/opt/hfs*/bin/hython",
    )
    paths: list[Path] = []
    for pattern in patterns:
        paths.extend(Path(path) for path in sorted(Path("/").glob(pattern.lstrip("/"))))
    return tuple(paths)


def _ensure_contained(path: Path, root: Path) -> None:
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError as exc:
        raise HoudiniLocalRunnerError("output file must stay inside output_root") from exc


def _relative_to(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.name


def _report_path(path: object, *, mode: str) -> str:
    if not path:
        return ""
    text = Path(path).as_posix() if isinstance(path, Path) else str(path)
    return text if mode == "local" else sanitize_path(text)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(READ_CHUNK_BYTES), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def _sha256_text(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def _clip(value: str) -> str:
    if len(value) <= MAX_OUTPUT_CHARS:
        return value
    return f"{value[:MAX_OUTPUT_CHARS]}\n...[output truncated at {MAX_OUTPUT_CHARS} chars]"


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


_HYTHON_SMOKE_DRIVER: Final[str] = r'''
import json
import platform
import sys
from pathlib import Path


def main():
    if len(sys.argv) != 2:
        raise RuntimeError("expected exactly one output path")
    output_path = Path(sys.argv[1])
    output_path.parent.mkdir(parents=True, exist_ok=True)

    import hou

    version = ".".join(str(part) for part in hou.applicationVersion())
    payload = {
        "kind": "houdini_hython_smoke_output_v1",
        "hou_module_loaded": True,
        "houdini_version": version,
        "platform": platform.system(),
    }
    output_path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")
    print("SEOS_HOUDINI_SMOKE_RESULT=" + json.dumps(payload, sort_keys=True))


if __name__ == "__main__":
    main()
'''
