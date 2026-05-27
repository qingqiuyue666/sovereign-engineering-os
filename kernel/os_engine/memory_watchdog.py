"""Async out-of-process supervisor with local quarantine diagnostics."""

from __future__ import annotations

import asyncio
import hashlib
import json
import math
import os
import platform
import resource
import signal
import time
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Mapping, Sequence

DEFAULT_CRASH_DIR = Path.home() / ".sovereign_engineering_os" / "artifacts" / "crashes"
MAX_RUNTIME_SECONDS = 86_400
MAX_MEMORY_LIMIT_MB = 262_144
MAX_STREAM_LIMIT_BYTES = 128 * 1024 * 1024
RETRY_POLICY_MAX_ATTEMPTS = 1


@dataclass(frozen=True, slots=True)
class ProcessLimits:
    max_runtime_seconds: float
    memory_limit_mb: int
    stdout_limit_bytes: int = 8 * 1024 * 1024
    stderr_limit_bytes: int = 8 * 1024 * 1024
    kill_grace_seconds: float = 1.0

    def __post_init__(self) -> None:
        if self.max_runtime_seconds <= 0:
            raise ProcessSupervisorError("max_runtime_seconds must be positive")
        if self.max_runtime_seconds > MAX_RUNTIME_SECONDS:
            raise ProcessSupervisorError("max_runtime_seconds exceeds bounded policy")
        if self.memory_limit_mb <= 0:
            raise ProcessSupervisorError("memory_limit_mb must be positive")
        if self.memory_limit_mb > MAX_MEMORY_LIMIT_MB:
            raise ProcessSupervisorError("memory_limit_mb exceeds bounded policy")
        if self.stdout_limit_bytes <= 0 or self.stderr_limit_bytes <= 0:
            raise ProcessSupervisorError("stdout/stderr limits must be positive")
        if self.stdout_limit_bytes > MAX_STREAM_LIMIT_BYTES or self.stderr_limit_bytes > MAX_STREAM_LIMIT_BYTES:
            raise ProcessSupervisorError("stdout/stderr limits exceed bounded policy")
        if self.kill_grace_seconds <= 0:
            raise ProcessSupervisorError("kill_grace_seconds must be positive")

    def to_dict(self) -> dict[str, int | float]:
        return {
            "kill_grace_seconds": self.kill_grace_seconds,
            "max_runtime_seconds": self.max_runtime_seconds,
            "memory_limit_mb": self.memory_limit_mb,
            "stderr_limit_bytes": self.stderr_limit_bytes,
            "stdout_limit_bytes": self.stdout_limit_bytes,
        }


@dataclass(frozen=True, slots=True)
class ProcessResult:
    command: tuple[str, ...]
    returncode: int | None
    stdout: str
    stderr: str
    duration_seconds: float
    max_rss_mb: float
    timed_out: bool
    memory_exceeded: bool
    stdout_overflow: bool
    stderr_overflow: bool
    quarantined: bool
    diagnostic_path: Path | None
    termination_reason: str
    partial_outputs_policy: str
    watchdog_receipt_path: Path | None = None

    @property
    def ok(self) -> bool:
        return self.returncode == 0 and not self.quarantined


class ProcessSupervisorError(RuntimeError):
    """Raised when a process cannot be launched or supervised."""


class ProcessSupervisor:
    def __init__(
        self,
        *,
        crash_dir: Path = DEFAULT_CRASH_DIR,
        receipt_dir: Path | None = None,
        poll_interval_seconds: float = 0.5,
    ) -> None:
        self.crash_dir = crash_dir.expanduser().resolve()
        self.receipt_dir = (
            receipt_dir.expanduser().resolve() if receipt_dir is not None else None
        )
        self.poll_interval_seconds = poll_interval_seconds

    async def run(
        self,
        command: Sequence[str],
        *,
        cwd: Path | None = None,
        env: Mapping[str, str] | None = None,
        limits: ProcessLimits,
    ) -> ProcessResult:
        if not command:
            raise ProcessSupervisorError("command cannot be empty")
        if RETRY_POLICY_MAX_ATTEMPTS != 1:
            raise ProcessSupervisorError("watchdog retry policy must remain single-attempt")
        command_tuple = tuple(str(part) for part in command)
        child_env = os.environ.copy()
        if env:
            child_env.update({str(key): str(value) for key, value in env.items()})
        working_dir = cwd.expanduser().resolve() if cwd is not None else None
        if working_dir is not None and not working_dir.exists():
            raise ProcessSupervisorError(f"cwd does not exist: {working_dir}")

        process = await asyncio.create_subprocess_exec(
            *command_tuple,
            cwd=str(working_dir) if working_dir is not None else None,
            env=child_env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            preexec_fn=_preexec_factory(limits) if os.name == "posix" else None,
        )
        start = time.monotonic()
        stdout_buffer = bytearray()
        stderr_buffer = bytearray()
        stdout_overflow = False
        stderr_overflow = False
        timed_out = False
        memory_exceeded = False
        termination_reason: str | None = None
        max_rss_mb = 0.0
        kill_lock = asyncio.Lock()

        async def request_kill(reason: str) -> None:
            nonlocal termination_reason
            async with kill_lock:
                if termination_reason is not None:
                    return
                termination_reason = reason
                await self._kill_process(process)

        async def read_stream(
            stream: asyncio.StreamReader | None,
            buffer: bytearray,
            limit: int,
            stream_name: str,
        ) -> bool:
            if stream is None:
                return False
            overflow = False
            while True:
                chunk = await stream.read(64 * 1024)
                if not chunk:
                    return overflow
                remaining = limit - len(buffer)
                if remaining > 0:
                    buffer.extend(chunk[:remaining])
                if len(chunk) > remaining:
                    overflow = True
                    await request_kill(f"{stream_name} byte limit exceeded")
                    return overflow

        async def monitor() -> None:
            nonlocal timed_out, memory_exceeded, max_rss_mb
            while process.returncode is None:
                await asyncio.sleep(self.poll_interval_seconds)
                elapsed = time.monotonic() - start
                max_rss_mb = max(max_rss_mb, await _rss_mb(process.pid))
                if elapsed > limits.max_runtime_seconds:
                    timed_out = True
                    await request_kill(f"runtime limit exceeded: {limits.max_runtime_seconds:.1f}s")
                    return
                if max_rss_mb > limits.memory_limit_mb:
                    memory_exceeded = True
                    await request_kill(f"memory limit exceeded: {max_rss_mb:.1f} MB")
                    return

        stdout_task = asyncio.create_task(
            read_stream(process.stdout, stdout_buffer, limits.stdout_limit_bytes, "stdout")
        )
        stderr_task = asyncio.create_task(
            read_stream(process.stderr, stderr_buffer, limits.stderr_limit_bytes, "stderr")
        )
        monitor_task = asyncio.create_task(monitor())
        returncode = await process.wait()
        monitor_task.cancel()
        await asyncio.gather(monitor_task, return_exceptions=True)
        stdout_overflow, stderr_overflow = await asyncio.gather(stdout_task, stderr_task)
        duration = time.monotonic() - start
        max_rss_mb = max(max_rss_mb, _children_ru_maxrss_mb())
        if termination_reason is None and returncode not in {0, None}:
            termination_reason = f"process exited nonzero: {returncode}"
        if termination_reason is None:
            termination_reason = "completed"
        quarantined = timed_out or memory_exceeded or stdout_overflow or stderr_overflow
        diagnostic_path: Path | None = None
        if quarantined or returncode not in {0, None}:
            diagnostic_path = await self._write_diagnostics(
                command=command_tuple,
                returncode=returncode,
                reason=termination_reason,
                cwd=working_dir,
                duration_seconds=duration,
                max_rss_mb=max_rss_mb,
                stdout=stdout_buffer.decode("utf-8", errors="replace"),
                stderr=stderr_buffer.decode("utf-8", errors="replace"),
            )
        receipt_path: Path | None = None
        if self.receipt_dir is not None:
            receipt_path = await self._write_receipt(
                command=command_tuple,
                limits=limits,
                returncode=returncode,
                duration_seconds=duration,
                max_rss_mb=max_rss_mb,
                timed_out=timed_out,
                memory_exceeded=memory_exceeded,
                stdout_overflow=stdout_overflow,
                stderr_overflow=stderr_overflow,
                quarantined=quarantined,
                diagnostic_path=diagnostic_path,
                termination_reason=termination_reason,
            )
        return ProcessResult(
            command=command_tuple,
            returncode=returncode,
            stdout=stdout_buffer.decode("utf-8", errors="replace"),
            stderr=stderr_buffer.decode("utf-8", errors="replace"),
            duration_seconds=duration,
            max_rss_mb=max_rss_mb,
            timed_out=timed_out,
            memory_exceeded=memory_exceeded,
            stdout_overflow=stdout_overflow,
            stderr_overflow=stderr_overflow,
            quarantined=quarantined,
            diagnostic_path=diagnostic_path,
            termination_reason=termination_reason,
            partial_outputs_policy="preserve_in_crash_bundle_when_available" if diagnostic_path else "no_partial_outputs",
            watchdog_receipt_path=receipt_path,
        )

    async def _kill_process(self, process: asyncio.subprocess.Process) -> None:
        if process.returncode is not None:
            return
        try:
            if os.name == "posix":
                os.killpg(os.getpgid(process.pid), signal.SIGKILL)
            else:
                process.kill()
        except ProcessLookupError:
            return
        except Exception:
            process.kill()

    async def _write_diagnostics(
        self,
        *,
        command: Sequence[str],
        returncode: int | None,
        reason: str,
        cwd: Path | None,
        duration_seconds: float,
        max_rss_mb: float,
        stdout: str,
        stderr: str,
    ) -> Path:
        self.crash_dir.mkdir(parents=True, exist_ok=True)
        path = self.crash_dir / f"crash_{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}_{uuid.uuid4().hex}.json"
        payload = {
            "created_at": datetime.now(UTC).isoformat(timespec="seconds"),
            "reason": reason,
            "command": list(command),
            "returncode": returncode,
            "cwd": str(cwd) if cwd is not None else None,
            "duration_seconds": duration_seconds,
            "max_rss_mb": max_rss_mb,
            "stdout_tail": stdout[-16_384:],
            "stderr_tail": stderr[-16_384:],
        }
        await asyncio.to_thread(path.write_text, json.dumps(payload, indent=2, sort_keys=True) + "\n", "utf-8")
        return path

    async def _write_receipt(
        self,
        *,
        command: Sequence[str],
        limits: ProcessLimits,
        returncode: int | None,
        duration_seconds: float,
        max_rss_mb: float,
        timed_out: bool,
        memory_exceeded: bool,
        stdout_overflow: bool,
        stderr_overflow: bool,
        quarantined: bool,
        diagnostic_path: Path | None,
        termination_reason: str,
    ) -> Path:
        if self.receipt_dir is None:
            raise ProcessSupervisorError("receipt_dir is not configured")
        self.receipt_dir.mkdir(parents=True, exist_ok=True)
        receipt_id = uuid.uuid4().hex
        created_at = datetime.now(UTC).isoformat(timespec="seconds")
        payload: dict[str, object] = {
            "receipt_type": "os_engine_process_watchdog_receipt_v1",
            "receipt_id": receipt_id,
            "created_at": created_at,
            "command_sha256": _stable_hash({"command": list(command)}),
            "limits": limits.to_dict(),
            "returncode": returncode,
            "duration_seconds": duration_seconds,
            "max_rss_mb": max_rss_mb,
            "timed_out": timed_out,
            "memory_exceeded": memory_exceeded,
            "stdout_overflow": stdout_overflow,
            "stderr_overflow": stderr_overflow,
            "quarantined": quarantined,
            "diagnostic_path": str(diagnostic_path) if diagnostic_path else None,
            "termination_reason": termination_reason,
            "raw_stdout_stored": False,
            "raw_stderr_stored": False,
            "retry_attempts": RETRY_POLICY_MAX_ATTEMPTS,
        }
        hash_material = dict(payload)
        hash_material.pop("created_at", None)
        payload["content_hash"] = _stable_hash(hash_material)
        path = (
            self.receipt_dir
            / f"watchdog_receipt_{created_at.replace(':', '')}_{receipt_id}.json"
        )
        await asyncio.to_thread(
            path.write_text,
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            "utf-8",
        )
        return path


def _stable_hash(payload: object) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


async def _rss_mb(pid: int) -> float:
    if platform.system() not in {"Darwin", "Linux"}:
        return 0.0
    process = await asyncio.create_subprocess_exec(
        "ps",
        "-o",
        "rss=",
        "-p",
        str(pid),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.DEVNULL,
    )
    stdout, _stderr = await process.communicate()
    try:
        return float(stdout.decode("utf-8", errors="replace").strip() or "0") / 1024
    except ValueError:
        return 0.0


def _children_ru_maxrss_mb() -> float:
    value = float(resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss)
    if platform.system() == "Darwin":
        return value / (1024 * 1024)
    return value / 1024


def _preexec_factory(limits: ProcessLimits):
    def preexec() -> None:
        os.setsid()
        _apply_resource_limits(limits)

    return preexec


def _apply_resource_limits(limits: ProcessLimits) -> None:
    cpu_seconds = max(1, int(math.ceil(limits.max_runtime_seconds + 2)))
    _try_set_limit(resource.RLIMIT_CPU, cpu_seconds, cpu_seconds + 3)
    memory_bytes = max(1, int(limits.memory_limit_mb)) * 1024 * 1024
    if hasattr(resource, "RLIMIT_AS"):
        _try_set_limit(resource.RLIMIT_AS, memory_bytes, memory_bytes)
    if hasattr(resource, "RLIMIT_RSS"):
        _try_set_limit(resource.RLIMIT_RSS, memory_bytes, memory_bytes)


def _try_set_limit(kind: int, soft: int, hard: int) -> None:
    try:
        current_soft, current_hard = resource.getrlimit(kind)
        target_hard = hard if current_hard in {-1, resource.RLIM_INFINITY} else min(hard, int(current_hard))
        target_soft = min(soft, target_hard)
        if current_soft not in {-1, resource.RLIM_INFINITY}:
            target_soft = min(target_soft, int(current_soft))
        resource.setrlimit(kind, (target_soft, target_hard))
    except (OSError, ValueError):
        return
