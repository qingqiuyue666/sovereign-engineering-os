"""Fail-closed subprocess proxy for the desktop Code Audit surface."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final
import os
import shlex
import subprocess
import time

__all__ = [
    "ALLOWED_COMMANDS",
    "CommandRejected",
    "CommandResult",
    "parse_command_line",
    "run_whitelisted_command",
]

_MAX_ARGS: Final[int] = 16
_MAX_ARG_LENGTH: Final[int] = 256
_MAX_OUTPUT_CHARS: Final[int] = 120_000
_DEFAULT_TIMEOUT_SECONDS: Final[float] = 900.0
_SHELL_METACHARS: Final[tuple[str, ...]] = (
    "&&",
    "||",
    "|",
    ">",
    "<",
    ";",
    "&",
    "`",
    "$",
    "\\",
)
_SECRET_ENV_MARKERS: Final[tuple[str, ...]] = (
    "AUTH",
    "BEARER",
    "CREDENTIAL",
    "KEY",
    "PASSWORD",
    "SECRET",
    "TOKEN",
)
_BASE_ENV_ALLOWLIST: Final[frozenset[str]] = frozenset(
    {
        "HOME",
        "LANG",
        "LC_ALL",
        "PATH",
        "PWD",
        "PYENV_ROOT",
        "SHELL",
        "TMPDIR",
        "USER",
        "VIRTUAL_ENV",
    }
)

ALLOWED_COMMANDS: Final[frozenset[tuple[str, ...]]] = frozenset(
    {
        (
            "python3",
            "-m",
            "unittest",
            "discover",
            "-s",
            "tests/tracer_bullet",
            "-v",
        ),
        (
            "python3",
            "-m",
            "unittest",
            "discover",
            "-s",
            "tests/schemas",
            "-v",
        ),
        (
            "python3",
            "-m",
            "unittest",
            "discover",
            "-s",
            "validation/tests/acceptance",
            "-v",
        ),
        ("make", "ci"),
    }
)


class CommandRejected(ValueError):
    """Raised when a GUI command does not exactly match the subprocess allowlist."""


@dataclass(frozen=True, slots=True)
class CommandResult:
    """Bounded result payload returned to the GUI after a whitelisted command exits."""

    argv: tuple[str, ...]
    cwd: Path
    returncode: int
    stdout: str
    stderr: str
    duration_seconds: float
    timed_out: bool = False

    @property
    def command_line(self) -> str:
        return shlex.join(self.argv)

    @property
    def ok(self) -> bool:
        return self.returncode == 0 and not self.timed_out

    @property
    def combined_output(self) -> str:
        chunks: list[str] = []
        if self.stdout:
            chunks.append(self.stdout)
        if self.stderr:
            chunks.append(self.stderr)
        return "\n".join(chunks)

    def as_dict(self) -> dict[str, object]:
        return {
            "argv": list(self.argv),
            "command_line": self.command_line,
            "cwd": self.cwd.as_posix(),
            "duration_seconds": self.duration_seconds,
            "ok": self.ok,
            "returncode": self.returncode,
            "stderr": self.stderr,
            "stdout": self.stdout,
            "timed_out": self.timed_out,
        }


def parse_command_line(command_line: str | Sequence[str]) -> tuple[str, ...]:
    """Parse argv without a shell and reject shell control syntax fail-closed."""

    if isinstance(command_line, str):
        try:
            argv = tuple(shlex.split(command_line, comments=False, posix=True))
        except ValueError as exc:
            raise CommandRejected(f"command could not be parsed: {exc}") from exc
    else:
        argv = tuple(str(part) for part in command_line)
    _validate_argv_shape(argv)
    return argv


def run_whitelisted_command(
    command_line: str | Sequence[str],
    *,
    cwd: Path | str,
    timeout_seconds: float = _DEFAULT_TIMEOUT_SECONDS,
    extra_env: Mapping[str, str] | None = None,
) -> CommandResult:
    """Run one exact allowlisted validation command with no shell expansion."""

    argv = parse_command_line(command_line)
    _validate_allowed_command(argv)
    working_directory = Path(cwd).resolve()
    if not working_directory.exists() or not working_directory.is_dir():
        raise CommandRejected(f"working directory does not exist: {working_directory}")
    if timeout_seconds <= 0:
        raise CommandRejected("timeout_seconds must be positive")

    start = time.monotonic()
    process = subprocess.Popen(
        argv,
        cwd=working_directory,
        env=_build_child_env(extra_env),
        shell=False,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    timed_out = False
    try:
        stdout, stderr = process.communicate(timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        timed_out = True
        process.kill()
        stdout, stderr = process.communicate(timeout=5)

    duration = time.monotonic() - start
    return CommandResult(
        argv=argv,
        cwd=working_directory,
        returncode=process.returncode,
        stdout=_clip_output(stdout),
        stderr=_clip_output(stderr),
        duration_seconds=duration,
        timed_out=timed_out,
    )


def _validate_argv_shape(argv: tuple[str, ...]) -> None:
    if not argv:
        raise CommandRejected("empty commands are not allowed")
    if len(argv) > _MAX_ARGS:
        raise CommandRejected("command has too many arguments")
    for token in argv:
        if not token:
            raise CommandRejected("empty command arguments are not allowed")
        if len(token) > _MAX_ARG_LENGTH:
            raise CommandRejected("command argument is too long")
        if "\x00" in token or any(ord(character) < 32 for character in token):
            raise CommandRejected("control characters are not allowed in command arguments")
        if any(marker in token for marker in _SHELL_METACHARS):
            raise CommandRejected(f"shell metacharacter rejected in argument: {token}")


def _validate_allowed_command(argv: tuple[str, ...]) -> None:
    if argv not in ALLOWED_COMMANDS:
        allowed = "; ".join(shlex.join(command) for command in sorted(ALLOWED_COMMANDS))
        raise CommandRejected(f"command is not allowlisted; allowed commands: {allowed}")


def _build_child_env(extra_env: Mapping[str, str] | None) -> dict[str, str]:
    source = dict(os.environ)
    if extra_env:
        source.update(extra_env)
    env: dict[str, str] = {}
    for key, value in source.items():
        upper_key = key.upper()
        if any(marker in upper_key for marker in _SECRET_ENV_MARKERS):
            continue
        if key in _BASE_ENV_ALLOWLIST or upper_key.startswith(("PYTHON", "UV_", "PIP_")):
            env[key] = value
    env["NO_COLOR"] = "1"
    env["PYTHONUNBUFFERED"] = "1"
    env.setdefault("PYTHONDONTWRITEBYTECODE", "1")
    return env


def _clip_output(output: str) -> str:
    if len(output) <= _MAX_OUTPUT_CHARS:
        return output
    clipped = output[:_MAX_OUTPUT_CHARS]
    return f"{clipped}\n...[output truncated at {_MAX_OUTPUT_CHARS} characters]"
