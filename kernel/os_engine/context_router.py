"""Sanitized context-pack router for upstream LLM handoffs."""

from __future__ import annotations

import asyncio
import hashlib
import os
import platform
import re
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Sequence

BINARY_EXTENSIONS = frozenset(
    {
        ".7z",
        ".abc",
        ".bgeo",
        ".bgeo.sc",
        ".bin",
        ".dmg",
        ".exr",
        ".gif",
        ".gz",
        ".hip",
        ".hiplc",
        ".hipnc",
        ".ico",
        ".jpeg",
        ".jpg",
        ".mov",
        ".mp4",
        ".pdf",
        ".png",
        ".pyc",
        ".safetensors",
        ".so",
        ".sqlite",
        ".sqlite3",
        ".tar",
        ".usdc",
        ".vdb",
        ".webp",
        ".zip",
    }
)
CACHE_PARTS = frozenset(
    {
        ".git",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".venv",
        "__pycache__",
        "cache",
        "caches",
        "node_modules",
    }
)
SECRET_NAME_HINTS = frozenset(
    {
        ".env",
        ".env.local",
        ".netrc",
        "id_rsa",
        "id_dsa",
        "id_ed25519",
        "known_hosts",
    }
)
SECRET_PATTERNS = (
    re.compile(r"(?i)(api[_-]?key|token|secret|password|passwd|authorization)\s*[:=]\s*['\"]?[^'\"\s]+"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"(?s)-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----"),
)
DEFAULT_OUTPUT_ROOT = Path.home() / ".sovereign_engineering_os" / "artifacts" / "context_packs"


@dataclass(frozen=True, slots=True)
class ContextPackResult:
    path: Path
    sha256: str
    size_bytes: int
    skipped_paths: tuple[str, ...]


class ContextRouterError(RuntimeError):
    """Raised when context routing fails closed."""


class ContextRouter:
    def __init__(
        self,
        *,
        repo_root: Path,
        output_dir: Path = DEFAULT_OUTPUT_ROOT,
        command_timeout_seconds: float = 10.0,
        command_output_limit_bytes: int = 512 * 1024,
    ) -> None:
        self.repo_root = repo_root.expanduser().resolve()
        self.output_dir = output_dir.expanduser().resolve()
        self.command_timeout_seconds = command_timeout_seconds
        self.command_output_limit_bytes = command_output_limit_bytes

    async def build_context_pack(
        self,
        *,
        max_files: int = 32,
        max_diff_bytes_per_file: int = 64 * 1024,
    ) -> ContextPackResult:
        if not (self.repo_root / ".git").exists():
            raise ContextRouterError(f"repo root is not a git worktree: {self.repo_root}")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        skipped: list[str] = []

        status = await self._git("status", "--short", "--branch")
        diff_stat = await self._git("diff", "--stat")
        staged_stat = await self._git("diff", "--cached", "--stat")
        recent_commits = await self._git("log", "--oneline", "--decorate", "-n", "16")
        changed_files = await self._changed_files()

        diff_sections: list[str] = []
        for relative in changed_files[:max_files]:
            if self._should_skip_path(relative):
                skipped.append(relative)
                continue
            path = self._resolve_repo_path(relative)
            if not path.exists():
                skipped.append(f"{relative} (deleted or missing)")
                continue
            if _compound_suffix(path).lower() in BINARY_EXTENSIONS:
                skipped.append(f"{relative} (binary)")
                continue
            diff_text = await self._bounded_diff(relative, max_bytes=max_diff_bytes_per_file)
            if not diff_text:
                excerpt = await asyncio.to_thread(_read_text_excerpt, path, max_diff_bytes_per_file)
                diff_text = f"[untracked or no textual git diff]\n\n{excerpt}"
            diff_sections.append(f"### {relative}\n\n```diff\n{self._sanitize(diff_text)}\n```")

        body = "\n\n".join(
            [
                "# Sovereign Engineering OS Context Pack",
                f"- Created: {datetime.now(UTC).isoformat(timespec='seconds')}",
                f"- Repo: `{self.repo_root}`",
                f"- Python: `{sys.version.split()[0]}`",
                f"- Platform: `{platform.platform()}`",
                f"- PID: `{os.getpid()}`",
                "## Git Status",
                f"```text\n{self._sanitize(status)}\n```",
                "## Diff Boundaries",
                "### Unstaged",
                f"```text\n{self._sanitize(diff_stat or '<no unstaged diff>')}\n```",
                "### Staged",
                f"```text\n{self._sanitize(staged_stat or '<no staged diff>')}\n```",
                "## Recent Commits",
                f"```text\n{self._sanitize(recent_commits)}\n```",
                "## Selected Text Diffs",
                "\n\n".join(diff_sections) if diff_sections else "<no eligible text diffs>",
                "## Purged Paths",
                "\n".join(f"- `{item}`" for item in skipped) if skipped else "<none>",
            ]
        )
        body = self._sanitize(body)
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        path = self.output_dir / f"context_pack_{stamp}.md"
        await asyncio.to_thread(path.write_text, body + "\n", "utf-8")
        sha256 = await asyncio.to_thread(_sha256_file, path)
        return ContextPackResult(
            path=path,
            sha256=sha256,
            size_bytes=path.stat().st_size,
            skipped_paths=tuple(skipped),
        )

    async def _changed_files(self) -> list[str]:
        outputs = await asyncio.gather(
            self._git("diff", "--name-only"),
            self._git("diff", "--cached", "--name-only"),
            self._git("ls-files", "--others", "--exclude-standard"),
        )
        ordered: list[str] = []
        seen: set[str] = set()
        for output in outputs:
            for line in output.splitlines():
                relative = line.strip()
                if relative and relative not in seen:
                    seen.add(relative)
                    ordered.append(relative)
        return ordered

    async def _bounded_diff(self, relative_path: str, *, max_bytes: int) -> str:
        unstaged, staged = await asyncio.gather(
            self._git("diff", "--", relative_path, output_limit=max_bytes),
            self._git("diff", "--cached", "--", relative_path, output_limit=max_bytes),
        )
        return "\n".join(part for part in (unstaged, staged) if part)

    async def _git(self, *args: str, output_limit: int | None = None) -> str:
        limit = output_limit or self.command_output_limit_bytes
        process = await asyncio.create_subprocess_exec(
            "git",
            *args,
            cwd=str(self.repo_root),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout_task = asyncio.create_task(_read_limited_stream(process.stdout, limit, process))
        stderr_task = asyncio.create_task(_read_limited_stream(process.stderr, min(limit, 64 * 1024), process))
        try:
            returncode = await asyncio.wait_for(process.wait(), timeout=self.command_timeout_seconds)
        except TimeoutError:
            process.kill()
            await process.wait()
            await asyncio.gather(stdout_task, stderr_task, return_exceptions=True)
            raise ContextRouterError(f"git command timed out: git {' '.join(args)}") from None
        stdout, stdout_truncated = await stdout_task
        stderr, _stderr_truncated = await stderr_task
        decoded_stdout = stdout.decode("utf-8", errors="replace")
        if stdout_truncated:
            decoded_stdout += "\n[TRUNCATED_BY_CONTEXT_ROUTER]"
        if returncode != 0 and not stdout_truncated:
            message = stderr.decode("utf-8", errors="replace")[:limit]
            raise ContextRouterError(f"git {' '.join(args)} failed: {message}")
        return decoded_stdout

    def _resolve_repo_path(self, relative_path: str) -> Path:
        path = (self.repo_root / relative_path).resolve()
        if not path.is_relative_to(self.repo_root):
            raise ContextRouterError(f"path escaped repo root: {relative_path}")
        return path

    def _should_skip_path(self, relative_path: str) -> bool:
        path = Path(relative_path)
        lowered_parts = {part.lower() for part in path.parts}
        if lowered_parts & CACHE_PARTS:
            return True
        if path.name.lower() in SECRET_NAME_HINTS:
            return True
        if "secret" in path.name.lower() or "credential" in path.name.lower():
            return True
        if _compound_suffix(path).lower() in BINARY_EXTENSIONS:
            return True
        return False

    def _sanitize(self, text: str) -> str:
        sanitized = text
        for pattern in SECRET_PATTERNS:
            sanitized = pattern.sub("[REDACTED_SECRET]", sanitized)
        return sanitized


def _read_text_excerpt(path: Path, max_bytes: int) -> str:
    data = path.read_bytes()[:max_bytes]
    if b"\x00" in data:
        return "[binary content purged]"
    return data.decode("utf-8", errors="replace")


async def _read_limited_stream(
    stream: asyncio.StreamReader | None,
    limit: int,
    process: asyncio.subprocess.Process,
) -> tuple[bytes, bool]:
    if stream is None:
        return b"", False
    buffer = bytearray()
    truncated = False
    while True:
        chunk = await stream.read(64 * 1024)
        if not chunk:
            return bytes(buffer), truncated
        remaining = limit - len(buffer)
        if remaining > 0:
            buffer.extend(chunk[:remaining])
        if len(chunk) > remaining:
            truncated = True
            try:
                process.kill()
            except ProcessLookupError:
                pass
            return bytes(buffer), truncated


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _compound_suffix(path: Path) -> str:
    name = path.name.lower()
    if name.endswith(".bgeo.sc"):
        return ".bgeo.sc"
    return path.suffix.lower()
