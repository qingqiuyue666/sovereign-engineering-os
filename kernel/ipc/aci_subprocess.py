"""Whitelisted subprocess proxy for the desktop Code Audit surface."""

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
    "CommandRejected",
    "CommandResult",
    "parse_command_line",
    "run_whitelisted_command",
]

_MAX_ARGS: Final[int] = 64
_MAX_ARG_LENGTH: Final[int] = 4096
_MAX_OUTPUT_CHARS: Final[int] = 120_000
_DEFAULT_TIMEOUT_SECONDS: Final[float] = 180.0

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

_PYTEST_FLAGS: Final[frozenset[str]] = frozenset(
    {
        "-q",
        "-s",
        "-v",
        "-x",
        "--collect-only",
        "--disable-warnings",
        "--failed-first",
        "--last-failed",
        "--strict-config",
        "--strict-markers",
    }
)
_PYTEST_VALUE_OPTIONS: Final[frozenset[str]] = frozenset(
    {
        "-k",
        "-m",
        "--color",
        "--durations",
        "--maxfail",
        "--tb",
    }
)
_PYTEST_VALUE_PREFIXES: Final[tuple[str, ...]] = tuple(f"{option}=" for option in _PYTEST_VALUE_OPTIONS)
_PYTEST_ALLOWED_TB: Final[frozenset[str]] = frozenset({"auto", "long", "short", "line", "native", "no"})
_PYTEST_ALLOWED_COLOR: Final[frozenset[str]] = frozenset({"yes", "no", "auto"})

_RUFF_FLAGS: Final[frozenset[str]] = frozenset({"--quiet", "--statistics", "--preview"})
_RUFF_VALUE_OPTIONS: Final[frozenset[str]] = frozenset(
    {
        "--config",
        "--exclude",
        "--extend-exclude",
        "--extend-ignore",
        "--extend-select",
        "--ignore",
        "--output-format",
        "--select",
        "--target-version",
    }
)
_RUFF_VALUE_PREFIXES: Final[tuple[str, ...]] = tuple(f"{option}=" for option in _RUFF_VALUE_OPTIONS)

_MYPY_FLAGS: Final[frozenset[str]] = frozenset(
    {
        "--check-untyped-defs",
        "--disallow-untyped-defs",
        "--ignore-missing-imports",
        "--no-error-summary",
        "--pretty",
        "--show-column-numbers",
        "--strict",
        "--warn-redundant-casts",
        "--warn-unused-ignores",
    }
)
_MYPY_VALUE_OPTIONS: Final[frozenset[str]] = frozenset({"--config-file", "--python-version"})
_MYPY_VALUE_PREFIXES: Final[tuple[str, ...]] = tuple(f"{option}=" for option in _MYPY_VALUE_OPTIONS)

_GIT_READONLY_SUBCOMMANDS: Final[frozenset[str]] = frozenset(
    {
        "branch",
        "diff",
        "log",
        "rev-parse",
        "show",
        "status",
    }
)
_GIT_SAFE_FLAGS: Final[frozenset[str]] = frozenset(
    {
        "--branch",
        "--check",
        "--name-only",
        "--oneline",
        "--porcelain",
        "--short",
        "--stat",
        "-sb",
    }
)
_GIT_VALUE_OPTIONS: Final[frozenset[str]] = frozenset({"--max-count"})
_GIT_VALUE_PREFIXES: Final[tuple[str, ...]] = tuple(f"{option}=" for option in _GIT_VALUE_OPTIONS)


class CommandRejected(ValueError):
    """Raised when a GUI command does not pass the subprocess allowlist."""


@dataclass(frozen=True, slots=True)
class CommandResult:
    """Result payload returned to the GUI after a whitelisted command exits."""

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
        chunks = []
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
    """Parse a GUI command into argv without invoking a shell."""

    if isinstance(command_line, str):
        argv = tuple(shlex.split(command_line, comments=False, posix=True))
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
    """Run a safe audit command and return bounded stdout/stderr for the GUI."""

    argv = parse_command_line(command_line)
    working_directory = Path(cwd).resolve()
    if not working_directory.exists() or not working_directory.is_dir():
        raise CommandRejected(f"working directory does not exist: {working_directory}")
    _validate_allowed_command(argv, working_directory)
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


def _validate_allowed_command(argv: tuple[str, ...], cwd: Path) -> None:
    executable = Path(argv[0]).name
    args = argv[1:]
    if executable == "pytest":
        _validate_pytest_args(args, cwd)
        return
    if executable in {"python", "python3"} and len(args) >= 2 and args[0] == "-m" and args[1] == "pytest":
        _validate_pytest_args(args[2:], cwd)
        return
    if executable == "ruff":
        _validate_ruff_args(args, cwd)
        return
    if executable == "mypy":
        _validate_mypy_args(args, cwd)
        return
    if executable == "git":
        _validate_git_args(args, cwd)
        return
    raise CommandRejected(f"command is not allowlisted: {executable}")


def _validate_pytest_args(args: Sequence[str], cwd: Path) -> None:
    index = 0
    while index < len(args):
        token = args[index]
        if token in _PYTEST_FLAGS:
            index += 1
            continue
        if token in _PYTEST_VALUE_OPTIONS:
            value = _require_option_value(token, args, index)
            _validate_pytest_option_value(token, value)
            index += 2
            continue
        if token.startswith(_PYTEST_VALUE_PREFIXES):
            option, value = token.split("=", 1)
            _validate_pytest_option_value(option, value)
            index += 1
            continue
        if token.startswith("-"):
            raise CommandRejected(f"pytest option is not allowlisted: {token}")
        _validate_repo_path_token(token, cwd)
        index += 1


def _validate_ruff_args(args: Sequence[str], cwd: Path) -> None:
    if not args or args[0] != "check":
        raise CommandRejected("only 'ruff check' is allowlisted")
    index = 1
    while index < len(args):
        token = args[index]
        if token in _RUFF_FLAGS:
            index += 1
            continue
        if token in _RUFF_VALUE_OPTIONS:
            value = _require_option_value(token, args, index)
            if token == "--config":
                _validate_repo_path_token(value, cwd)
            else:
                _validate_plain_value(value)
            index += 2
            continue
        if token.startswith(_RUFF_VALUE_PREFIXES):
            option, value = token.split("=", 1)
            if option == "--config":
                _validate_repo_path_token(value, cwd)
            else:
                _validate_plain_value(value)
            index += 1
            continue
        if token.startswith("-"):
            raise CommandRejected(f"ruff option is not allowlisted: {token}")
        _validate_repo_path_token(token, cwd)
        index += 1


def _validate_mypy_args(args: Sequence[str], cwd: Path) -> None:
    if not args:
        raise CommandRejected("mypy requires at least one target path")
    index = 0
    saw_target = False
    while index < len(args):
        token = args[index]
        if token in _MYPY_FLAGS:
            index += 1
            continue
        if token in _MYPY_VALUE_OPTIONS:
            value = _require_option_value(token, args, index)
            if token == "--config-file":
                _validate_repo_path_token(value, cwd)
            else:
                _validate_plain_value(value)
            index += 2
            continue
        if token.startswith(_MYPY_VALUE_PREFIXES):
            option, value = token.split("=", 1)
            if option == "--config-file":
                _validate_repo_path_token(value, cwd)
            else:
                _validate_plain_value(value)
            index += 1
            continue
        if token.startswith("-"):
            raise CommandRejected(f"mypy option is not allowlisted: {token}")
        _validate_repo_path_token(token, cwd)
        saw_target = True
        index += 1
    if not saw_target:
        raise CommandRejected("mypy requires at least one target path")


def _validate_git_args(args: Sequence[str], cwd: Path) -> None:
    if not args:
        raise CommandRejected("git requires a readonly subcommand")
    subcommand = args[0]
    if subcommand not in _GIT_READONLY_SUBCOMMANDS:
        raise CommandRejected(f"git subcommand is not readonly allowlisted: {subcommand}")
    index = 1
    while index < len(args):
        token = args[index]
        if token == "--":
            for path_token in args[index + 1 :]:
                _validate_repo_path_token(path_token, cwd)
            return
        if token in _GIT_SAFE_FLAGS:
            index += 1
            continue
        if token in _GIT_VALUE_OPTIONS:
            _validate_int_value(_require_option_value(token, args, index), token)
            index += 2
            continue
        if token.startswith(_GIT_VALUE_PREFIXES):
            option, value = token.split("=", 1)
            _validate_int_value(value, option)
            index += 1
            continue
        if token.startswith("-"):
            raise CommandRejected(f"git option is not allowlisted: {token}")
        if subcommand in {"log", "rev-parse", "show"}:
            _validate_git_ref(token)
        else:
            _validate_repo_path_token(token, cwd)
        index += 1


def _require_option_value(option: str, args: Sequence[str], index: int) -> str:
    next_index = index + 1
    if next_index >= len(args):
        raise CommandRejected(f"{option} requires a value")
    value = args[next_index]
    if value.startswith("-"):
        raise CommandRejected(f"{option} value is missing")
    return value


def _validate_pytest_option_value(option: str, value: str) -> None:
    if option == "--maxfail":
        _validate_int_value(value, option)
    elif option == "--durations":
        _validate_int_value(value, option)
    elif option == "--tb" and value not in _PYTEST_ALLOWED_TB:
        raise CommandRejected(f"pytest --tb value is not allowlisted: {value}")
    elif option == "--color" and value not in _PYTEST_ALLOWED_COLOR:
        raise CommandRejected(f"pytest --color value is not allowlisted: {value}")
    else:
        _validate_plain_value(value)


def _validate_int_value(value: str, option: str) -> None:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise CommandRejected(f"{option} requires an integer") from exc
    if parsed < 0 or parsed > 10_000:
        raise CommandRejected(f"{option} integer value is out of range")


def _validate_plain_value(value: str) -> None:
    if not value or len(value) > 512:
        raise CommandRejected("option value is empty or too long")
    if "\x00" in value or any(ord(character) < 32 for character in value):
        raise CommandRejected("option values may not contain control characters")


def _validate_git_ref(value: str) -> None:
    _validate_plain_value(value)
    forbidden = ("..", "~", "^", ":", "\\", " ")
    if any(marker in value for marker in forbidden):
        raise CommandRejected(f"git ref is not allowlisted: {value}")


def _validate_repo_path_token(token: str, cwd: Path) -> None:
    path_part = token.split("::", 1)[0]
    if not path_part:
        raise CommandRejected("path token is empty")
    raw_path = Path(path_part)
    if raw_path.is_absolute():
        candidate = raw_path.resolve()
    else:
        candidate = (cwd / raw_path).resolve()
    try:
        candidate.relative_to(cwd)
    except ValueError as exc:
        raise CommandRejected(f"path escapes repository root: {token}") from exc


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
