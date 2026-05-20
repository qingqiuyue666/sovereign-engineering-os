"""Isolated hython ROP executor with fail-closed EXR sequence validation."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Final
import argparse
import asyncio
import json
import os
import re
import shlex
import shutil
import signal
import subprocess
import sys
import tempfile
import time

from kernel.vfx.render_artifact_ledger import (
    ArtifactLedgerError,
    RenderArtifactRecord,
    record_render_artifact,
)

__all__ = [
    "DEFAULT_ALLOWED_ROP_TYPE_TOKENS",
    "FrameAudit",
    "FrameIntegrityIssue",
    "HythonExecutorError",
    "HythonRenderRequest",
    "HythonRenderResult",
    "RenderFrameRange",
    "audit_exr_sequence",
    "execute_hython_rop",
    "execute_hython_rop_async",
]

DEFAULT_ALLOWED_ROP_TYPE_TOKENS: Final[tuple[str, ...]] = (
    "karma",
    "opengl",
    "ogl",
    "usdrender",
)
DEFAULT_OUTPUT_PARMS: Final[tuple[str, ...]] = (
    "picture",
    "vm_picture",
    "lopoutput",
    "sopoutput",
    "output",
    "filename",
)
_OUTPUT_PADDING: Final[int] = 4
_EXR_MAGIC: Final[bytes] = b"\x76\x2f\x31\x01"
_MIN_EXR_BYTES: Final[int] = 16
_MAX_OUTPUT_CHARS: Final[int] = 240_000
_MAX_FRAME_COUNT: Final[int] = 100_000
_MAX_TIMEOUT_SECONDS: Final[float] = 86_400.0
_SAFE_PREFIX_RE: Final[re.Pattern[str]] = re.compile(r"\A[A-Za-z0-9][A-Za-z0-9._-]{0,127}\Z")
_SAFE_ROP_PATH_RE: Final[re.Pattern[str]] = re.compile(r"\A/[A-Za-z0-9_./-]{1,255}\Z")
_SAFE_PARMS_RE: Final[re.Pattern[str]] = re.compile(r"\A[A-Za-z][A-Za-z0-9_]{0,63}\Z")
_SECRET_ENV_MARKERS: Final[tuple[str, ...]] = (
    "AUTH",
    "BEARER",
    "CREDENTIAL",
    "KEY",
    "PASSWORD",
    "SECRET",
    "TOKEN",
)
_CHILD_ENV_ALLOWLIST: Final[frozenset[str]] = frozenset(
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


class HythonExecutorError(RuntimeError):
    """Raised when a render request cannot be admitted safely."""


@dataclass(frozen=True, slots=True)
class RenderFrameRange:
    """Frame range rendered and audited as an explicit sequence."""

    start: int
    end: int
    step: int = 1

    def validated(self) -> RenderFrameRange:
        if self.start != 1:
            raise HythonExecutorError("Render Automation MVP requires 0001-to-N frame ranges")
        if self.end < self.start:
            raise HythonExecutorError("end frame must be >= start frame")
        if self.step != 1:
            raise HythonExecutorError("Render Automation MVP requires contiguous step=1 frames")
        if self.frame_count > _MAX_FRAME_COUNT:
            raise HythonExecutorError(f"frame range exceeds {_MAX_FRAME_COUNT} frames")
        return self

    @property
    def frame_count(self) -> int:
        return ((self.end - self.start) // self.step) + 1

    @property
    def expected_frames(self) -> tuple[int, ...]:
        return tuple(range(self.start, self.end + 1, self.step))

    def as_dict(self) -> dict[str, int]:
        return {
            "end": self.end,
            "start": self.start,
            "step": self.step,
        }


@dataclass(frozen=True, slots=True)
class HythonRenderRequest:
    """Controlled request for one isolated hython ROP render job."""

    hip_file: Path | str
    rop_node_path: str
    output_directory: Path | str
    end_frame: int
    output_prefix: str = "hfx_render"
    start_frame: int = 1
    frame_step: int = 1
    hython_executable: Path | str = "hython"
    timeout_seconds: float = 3_600.0
    output_parameter: str | None = None
    allowed_rop_type_tokens: tuple[str, ...] = DEFAULT_ALLOWED_ROP_TYPE_TOKENS
    write_ledger: bool = True
    ledger_root: Path | str | None = None
    allow_existing_frames: bool = False

    def validated(self) -> HythonRenderRequest:
        frame_range = self.frame_range.validated()
        hip_file = Path(self.hip_file).expanduser().resolve()
        if not hip_file.exists() or not hip_file.is_file():
            raise HythonExecutorError(f"HIP file is missing: {hip_file}")
        if hip_file.suffix.lower() not in {".hip", ".hiplc", ".hipnc"}:
            raise HythonExecutorError("HIP file must use .hip, .hiplc, or .hipnc")
        if not _SAFE_ROP_PATH_RE.fullmatch(self.rop_node_path):
            raise HythonExecutorError("ROP node path must be an absolute Houdini node path")
        if not _SAFE_PREFIX_RE.fullmatch(self.output_prefix):
            raise HythonExecutorError("output_prefix must be alphanumeric plus . _ -")
        output_directory = Path(self.output_directory).expanduser().resolve()
        if output_directory.exists() and not output_directory.is_dir():
            raise HythonExecutorError(f"output_directory is not a directory: {output_directory}")
        if output_directory.exists() and output_directory.is_symlink():
            raise HythonExecutorError("output_directory may not be a symlink")
        if self.timeout_seconds <= 0 or self.timeout_seconds > _MAX_TIMEOUT_SECONDS:
            raise HythonExecutorError(
                f"timeout_seconds must be within (0, {_MAX_TIMEOUT_SECONDS}]"
            )
        if self.output_parameter is not None and not _SAFE_PARMS_RE.fullmatch(
            self.output_parameter
        ):
            raise HythonExecutorError("output_parameter is not a safe Houdini parm name")
        tokens = tuple(token.lower().strip() for token in self.allowed_rop_type_tokens)
        if not tokens or any(not _SAFE_PARMS_RE.fullmatch(token) for token in tokens):
            raise HythonExecutorError("allowed ROP type tokens must be safe nonempty names")
        return HythonRenderRequest(
            hip_file=hip_file,
            rop_node_path=self.rop_node_path,
            output_directory=output_directory,
            end_frame=frame_range.end,
            output_prefix=self.output_prefix,
            start_frame=frame_range.start,
            frame_step=frame_range.step,
            hython_executable=self.hython_executable,
            timeout_seconds=float(self.timeout_seconds),
            output_parameter=self.output_parameter,
            allowed_rop_type_tokens=tokens,
            write_ledger=self.write_ledger,
            ledger_root=self.ledger_root,
            allow_existing_frames=self.allow_existing_frames,
        )

    @property
    def frame_range(self) -> RenderFrameRange:
        return RenderFrameRange(
            start=int(self.start_frame),
            end=int(self.end_frame),
            step=int(self.frame_step),
        )

    @property
    def houdini_output_pattern(self) -> str:
        return (
            self.output_directory_path
            / f"{self.output_prefix}.$F{_OUTPUT_PADDING}.exr"
        ).as_posix()

    @property
    def resolve_frame_pattern(self) -> str:
        return f"{self.output_prefix}.%0{_OUTPUT_PADDING}d.exr"

    @property
    def sequence_glob(self) -> str:
        return f"{self.output_prefix}.*.exr"

    @property
    def output_directory_path(self) -> Path:
        return Path(self.output_directory)

    def frame_path(self, frame: int) -> Path:
        return self.output_directory_path / f"{self.output_prefix}.{frame:0{_OUTPUT_PADDING}d}.exr"

    def as_dict(self) -> dict[str, object]:
        return {
            "allow_existing_frames": self.allow_existing_frames,
            "allowed_rop_type_tokens": list(self.allowed_rop_type_tokens),
            "end_frame": self.end_frame,
            "frame_step": self.frame_step,
            "hip_file": Path(self.hip_file).as_posix(),
            "hython_executable": str(self.hython_executable),
            "ledger_root": str(self.ledger_root) if self.ledger_root is not None else None,
            "output_directory": Path(self.output_directory).as_posix(),
            "output_parameter": self.output_parameter,
            "output_prefix": self.output_prefix,
            "rop_node_path": self.rop_node_path,
            "start_frame": self.start_frame,
            "timeout_seconds": self.timeout_seconds,
            "write_ledger": self.write_ledger,
        }


@dataclass(frozen=True, slots=True)
class FrameIntegrityIssue:
    """One failed physical frame validation."""

    frame: int | None
    path: Path
    reason: str
    size_bytes: int | None = None

    def as_dict(self) -> dict[str, object]:
        return {
            "frame": self.frame,
            "path": self.path.as_posix(),
            "reason": self.reason,
            "size_bytes": self.size_bytes,
        }


@dataclass(frozen=True, slots=True)
class FrameAudit:
    """Fail-closed disk audit for the expected EXR sequence."""

    output_directory: Path
    frame_range: RenderFrameRange
    checked_at: str
    valid_frames: tuple[int, ...]
    missing_frames: tuple[int, ...]
    invalid_frames: tuple[FrameIntegrityIssue, ...]
    unexpected_frames: tuple[FrameIntegrityIssue, ...]

    @property
    def passed(self) -> bool:
        return (
            len(self.valid_frames) == self.frame_range.frame_count
            and not self.missing_frames
            and not self.invalid_frames
            and not self.unexpected_frames
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "checked_at": self.checked_at,
            "expected_frame_count": self.frame_range.frame_count,
            "frame_range": self.frame_range.as_dict(),
            "invalid_frames": [issue.as_dict() for issue in self.invalid_frames],
            "missing_frames": list(self.missing_frames),
            "output_directory": self.output_directory.as_posix(),
            "passed": self.passed,
            "unexpected_frames": [issue.as_dict() for issue in self.unexpected_frames],
            "valid_frames": list(self.valid_frames),
        }


@dataclass(frozen=True, slots=True)
class HythonRenderResult:
    """Process result plus physical EXR validation and optional ledger record."""

    request: HythonRenderRequest
    argv: tuple[str, ...]
    returncode: int
    stdout: str
    stderr: str
    duration_seconds: float
    timed_out: bool
    audit: FrameAudit
    ledger_record: RenderArtifactRecord | None = None
    ledger_error: str | None = None

    @property
    def process_ok(self) -> bool:
        return self.returncode == 0 and not self.timed_out

    @property
    def complete(self) -> bool:
        ledger_ok = True
        if self.request.write_ledger:
            ledger_ok = self.ledger_record is not None and self.ledger_error is None
        return self.process_ok and self.audit.passed and ledger_ok

    @property
    def command_line(self) -> str:
        return shlex.join(self.argv)

    def as_dict(self) -> dict[str, object]:
        return {
            "audit": self.audit.as_dict(),
            "command_line": self.command_line,
            "complete": self.complete,
            "duration_seconds": self.duration_seconds,
            "ledger_error": self.ledger_error,
            "ledger_record": self.ledger_record.as_dict() if self.ledger_record else None,
            "process_ok": self.process_ok,
            "request": self.request.as_dict(),
            "returncode": self.returncode,
            "stderr": self.stderr,
            "stdout": self.stdout,
            "timed_out": self.timed_out,
        }


def execute_hython_rop(request: HythonRenderRequest) -> HythonRenderResult:
    """Render one ROP through isolated hython and verify every EXR frame on disk."""

    admitted = request.validated()
    admitted.output_directory_path.mkdir(parents=True, exist_ok=True)
    _reject_existing_expected_frames(admitted)
    hython = _resolve_hython_executable(admitted.hython_executable)
    env = _build_child_env()

    with tempfile.TemporaryDirectory(prefix="hfx_hython_rop_") as temp_dir_name:
        temp_dir = Path(temp_dir_name)
        driver_path = temp_dir / "render_driver.py"
        config_path = temp_dir / "render_config.json"
        driver_path.write_text(_HYTHON_DRIVER, encoding="utf-8")
        config_path.write_text(
            json.dumps(_hython_config(admitted), ensure_ascii=True, sort_keys=True),
            encoding="utf-8",
        )
        argv = (hython, driver_path.as_posix(), config_path.as_posix())
        start = time.monotonic()
        process = subprocess.Popen(
            argv,
            cwd=admitted.output_directory_path,
            env=env,
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
            stdout, stderr = process.communicate(timeout=admitted.timeout_seconds)
        except subprocess.TimeoutExpired:
            timed_out = True
            _terminate_process(process)
            stdout, stderr = process.communicate(timeout=10)
        duration = time.monotonic() - start

    audit = audit_exr_sequence(admitted)
    ledger_record: RenderArtifactRecord | None = None
    ledger_error: str | None = None
    if process.returncode == 0 and not timed_out and audit.passed and admitted.write_ledger:
        try:
            ledger_record = record_render_artifact(
                admitted.output_directory_path,
                sequence_glob=admitted.sequence_glob,
                frame_pattern=admitted.resolve_frame_pattern,
                metadata={
                    "executor": "kernel.vfx.hython_rop_executor",
                    "hip_file": admitted.hip_file.as_posix()
                    if isinstance(admitted.hip_file, Path)
                    else str(admitted.hip_file),
                    "houdini_output_pattern": admitted.houdini_output_pattern,
                    "rop_node_path": admitted.rop_node_path,
                    "start_frame": admitted.start_frame,
                    "end_frame": admitted.end_frame,
                },
                ledger_root=admitted.ledger_root,
            )
        except ArtifactLedgerError as exc:
            ledger_error = str(exc)

    return HythonRenderResult(
        request=admitted,
        argv=argv,
        returncode=int(process.returncode),
        stdout=_clip_output(stdout),
        stderr=_clip_output(stderr),
        duration_seconds=duration,
        timed_out=timed_out,
        audit=audit,
        ledger_record=ledger_record,
        ledger_error=ledger_error,
    )


async def execute_hython_rop_async(request: HythonRenderRequest) -> HythonRenderResult:
    """Run the isolated render from an event loop without blocking the caller."""

    return await asyncio.to_thread(execute_hython_rop, request)


def audit_exr_sequence(request: HythonRenderRequest) -> FrameAudit:
    """Audit every expected EXR frame and reject missing, stale-extra, or corrupt files."""

    admitted = request.validated()
    frame_range = admitted.frame_range
    expected_frames = set(frame_range.expected_frames)
    valid_frames: list[int] = []
    missing_frames: list[int] = []
    invalid_frames: list[FrameIntegrityIssue] = []

    for frame in frame_range.expected_frames:
        path = admitted.frame_path(frame)
        if not path.exists():
            missing_frames.append(frame)
            continue
        issue = _validate_exr_frame(path, frame=frame)
        if issue is None:
            valid_frames.append(frame)
        else:
            invalid_frames.append(issue)

    unexpected_frames = _find_unexpected_frames(admitted, expected_frames)
    return FrameAudit(
        output_directory=admitted.output_directory_path,
        frame_range=frame_range,
        checked_at=datetime.now(UTC).isoformat(timespec="seconds"),
        valid_frames=tuple(valid_frames),
        missing_frames=tuple(missing_frames),
        invalid_frames=tuple(invalid_frames),
        unexpected_frames=unexpected_frames,
    )


def _reject_existing_expected_frames(request: HythonRenderRequest) -> None:
    if request.allow_existing_frames:
        return
    existing = [request.frame_path(frame) for frame in request.frame_range.expected_frames]
    existing = [path for path in existing if path.exists()]
    if existing:
        sample = ", ".join(path.name for path in existing[:8])
        extra_count = len(existing) - 8
        suffix = f", +{extra_count} more" if extra_count > 0 else ""
        raise HythonExecutorError(
            "refusing to render over existing expected EXR frames: "
            f"{sample}{suffix}"
        )


def _validate_exr_frame(path: Path, *, frame: int | None) -> FrameIntegrityIssue | None:
    try:
        if path.is_symlink():
            return FrameIntegrityIssue(frame=frame, path=path, reason="symlink rejected")
        if not path.is_file():
            return FrameIntegrityIssue(frame=frame, path=path, reason="not a regular file")
        stat = path.stat()
        if stat.st_size < _MIN_EXR_BYTES:
            return FrameIntegrityIssue(
                frame=frame,
                path=path,
                reason="too small for valid EXR",
                size_bytes=stat.st_size,
            )
        with path.open("rb") as handle:
            magic = handle.read(len(_EXR_MAGIC))
        if magic != _EXR_MAGIC:
            return FrameIntegrityIssue(
                frame=frame,
                path=path,
                reason="bad EXR magic bytes",
                size_bytes=stat.st_size,
            )
    except OSError as exc:
        return FrameIntegrityIssue(frame=frame, path=path, reason=f"stat/read failed: {exc}")
    return None


def _find_unexpected_frames(
    request: HythonRenderRequest,
    expected_frames: set[int],
) -> tuple[FrameIntegrityIssue, ...]:
    pattern = re.compile(
        rf"\A{re.escape(request.output_prefix)}\.(?P<frame>\d{{{_OUTPUT_PADDING},}})\.exr\Z",
        re.IGNORECASE,
    )
    issues: list[FrameIntegrityIssue] = []
    if not request.output_directory_path.exists():
        return ()
    for path in sorted(request.output_directory_path.glob(request.sequence_glob)):
        match = pattern.fullmatch(path.name)
        if match is None:
            issues.append(
                FrameIntegrityIssue(frame=None, path=path, reason="unexpected EXR name")
            )
            continue
        frame = int(match.group("frame"))
        if frame not in expected_frames:
            issues.append(
                FrameIntegrityIssue(frame=frame, path=path, reason="unexpected frame number")
            )
    return tuple(issues)


def _resolve_hython_executable(hython_executable: Path | str) -> str:
    executable = str(hython_executable)
    if not executable:
        raise HythonExecutorError("hython executable is required")
    if any(character in executable for character in ("\x00", "\n", "\r")):
        raise HythonExecutorError("hython executable contains control characters")
    if "/" in executable or "\\" in executable:
        path = Path(executable).expanduser().resolve()
        if not path.exists() or not path.is_file():
            raise HythonExecutorError(f"hython executable is missing: {path}")
        if not os.access(path, os.X_OK):
            raise HythonExecutorError(f"hython executable is not executable: {path}")
        return path.as_posix()
    if not _SAFE_PARMS_RE.fullmatch(executable):
        raise HythonExecutorError("hython executable command name is not safe")
    resolved = shutil.which(executable)
    if resolved is None:
        raise HythonExecutorError(f"hython executable not found on PATH: {executable}")
    return resolved


def _build_child_env() -> dict[str, str]:
    env: dict[str, str] = {}
    for key, value in os.environ.items():
        upper_key = key.upper()
        if any(marker in upper_key for marker in _SECRET_ENV_MARKERS):
            continue
        if key in _CHILD_ENV_ALLOWLIST:
            env[key] = value
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


def _hython_config(request: HythonRenderRequest) -> dict[str, object]:
    return {
        "allowed_rop_type_tokens": list(request.allowed_rop_type_tokens),
        "end_frame": request.end_frame,
        "hip_file": Path(request.hip_file).as_posix(),
        "houdini_output_pattern": request.houdini_output_pattern,
        "output_parameter": request.output_parameter,
        "output_parm_candidates": list(DEFAULT_OUTPUT_PARMS),
        "rop_node_path": request.rop_node_path,
        "start_frame": request.start_frame,
        "step": request.frame_step,
    }


def _clip_output(output: str) -> str:
    if len(output) <= _MAX_OUTPUT_CHARS:
        return output
    return f"{output[:_MAX_OUTPUT_CHARS]}\n...[output truncated at {_MAX_OUTPUT_CHARS} chars]"


_HYTHON_DRIVER: Final[str] = r'''
import json
import sys


def _find_output_parm(rop, preferred, candidates):
    names = []
    if preferred:
        names.append(preferred)
    names.extend(candidates)
    for name in names:
        parm = rop.parm(name)
        if parm is not None:
            return parm
    raise RuntimeError("ROP output parameter was not found")


def _set_if_present(node, parm_name, value):
    parm = node.parm(parm_name)
    if parm is not None:
        parm.set(value)


def main():
    if len(sys.argv) != 2:
        raise RuntimeError("expected exactly one JSON config path")
    with open(sys.argv[1], "r", encoding="utf-8") as handle:
        config = json.load(handle)

    import hou

    hou.hipFile.load(config["hip_file"], suppress_save_prompt=True)
    rop = hou.node(config["rop_node_path"])
    if rop is None:
        raise RuntimeError("ROP node does not exist: %s" % config["rop_node_path"])

    rop_type_name = rop.type().name().lower()
    allowed_tokens = tuple(config["allowed_rop_type_tokens"])
    if not any(token in rop_type_name for token in allowed_tokens):
        raise RuntimeError("ROP type is not allowed: %s" % rop_type_name)

    output_parm = _find_output_parm(
        rop,
        config.get("output_parameter"),
        config["output_parm_candidates"],
    )
    output_parm.set(config["houdini_output_pattern"])

    _set_if_present(rop, "trange", 1)
    _set_if_present(rop, "f1", int(config["start_frame"]))
    _set_if_present(rop, "f2", int(config["end_frame"]))
    _set_if_present(rop, "f3", int(config["step"]))

    rop.render(
        frame_range=(
            int(config["start_frame"]),
            int(config["end_frame"]),
            int(config["step"]),
        ),
        verbose=True,
    )
    print(
        "HFX_HYTHON_RESULT="
        + json.dumps(
            {
                "ok": True,
                "output_pattern": config["houdini_output_pattern"],
                "rop_node_path": config["rop_node_path"],
                "rop_type_name": rop_type_name,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
'''


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Render one Houdini ROP via isolated hython.")
    parser.add_argument("--hip-file", required=True)
    parser.add_argument("--rop-node-path", required=True)
    parser.add_argument("--output-directory", required=True)
    parser.add_argument("--output-prefix", default="hfx_render")
    parser.add_argument("--start-frame", type=int, default=1)
    parser.add_argument("--end-frame", type=int, required=True)
    parser.add_argument("--hython", default="hython")
    parser.add_argument("--timeout-seconds", type=float, default=3_600.0)
    parser.add_argument("--output-parameter", default=None)
    parser.add_argument("--ledger-root", default=None)
    parser.add_argument("--no-ledger", action="store_true")
    parser.add_argument("--allow-existing-frames", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_arg_parser()
    args = parser.parse_args(argv)
    request = HythonRenderRequest(
        hip_file=args.hip_file,
        rop_node_path=args.rop_node_path,
        output_directory=args.output_directory,
        output_prefix=args.output_prefix,
        start_frame=args.start_frame,
        end_frame=args.end_frame,
        hython_executable=args.hython,
        timeout_seconds=args.timeout_seconds,
        output_parameter=args.output_parameter,
        write_ledger=not args.no_ledger,
        ledger_root=args.ledger_root,
        allow_existing_frames=args.allow_existing_frames,
    )
    try:
        result = execute_hython_rop(request)
    except HythonExecutorError as exc:
        print(json.dumps({"complete": False, "error": str(exc)}, sort_keys=True), file=sys.stderr)
        return 2
    print(json.dumps(result.as_dict(), ensure_ascii=True, sort_keys=True, indent=2))
    return 0 if result.complete else 2


if __name__ == "__main__":
    raise SystemExit(main())
