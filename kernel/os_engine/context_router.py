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
from enum import StrEnum
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
SKIP_FILE_NAMES = frozenset({".ds_store"})
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


class ContextUseCase(StrEnum):
    GEMINI_FULL_SYSTEM_REVIEW = "gemini_full_system_review"
    CODEX_BRANCH_HARDENING = "codex_branch_hardening"
    HFX_PHYSICAL_PROOF_REVIEW = "hfx_physical_proof_review"
    DESKTOP_OS_ENGINE_REVIEW = "desktop_os_engine_review"


USE_CASE_INSTRUCTIONS: dict[ContextUseCase, str] = {
    ContextUseCase.GEMINI_FULL_SYSTEM_REVIEW: "Review the repository as a local-first engineering OS without making completion claims.",
    ContextUseCase.CODEX_BRANCH_HARDENING: "Harden this branch with tests, fail-closed boundaries, and deterministic validation.",
    ContextUseCase.HFX_PHYSICAL_PROOF_REVIEW: "Review HFX physical proof boundaries without launching Houdini or claiming final output.",
    ContextUseCase.DESKTOP_OS_ENGINE_REVIEW: "Review desktop and os_engine integration for import safety and queue-only execution.",
}

USE_CASE_FILTERS: dict[ContextUseCase, tuple[str, ...]] = {
    ContextUseCase.GEMINI_FULL_SYSTEM_REVIEW: (),
    ContextUseCase.CODEX_BRANCH_HARDENING: (),
    ContextUseCase.HFX_PHYSICAL_PROOF_REVIEW: ("hfx", "houdini", "assets/houdini", "kernel/vfx"),
    ContextUseCase.DESKTOP_OS_ENGINE_REVIEW: ("apps/sovereign_desktop.py", "kernel/os_engine", "sovereign_desktop"),
}


@dataclass(frozen=True, slots=True)
class ContextPackResult:
    path: Path
    sha256: str
    size_bytes: int
    skipped_paths: tuple[str, ...]
    summary_mode: bool = False


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
        task_instructions: str | None = None,
        use_case: ContextUseCase | str = ContextUseCase.CODEX_BRANCH_HARDENING,
        topic_filters: Sequence[str] | None = None,
        changed_files_only: bool = True,
        max_output_bytes: int = 512 * 1024,
        deterministic: bool = False,
    ) -> ContextPackResult:
        if not (self.repo_root / ".git").exists():
            raise ContextRouterError(f"repo root is not a git worktree: {self.repo_root}")
        if max_files <= 0:
            raise ContextRouterError("max_files must be positive")
        if max_output_bytes <= 0:
            raise ContextRouterError("max_output_bytes must be positive")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        skipped: list[str] = []
        selected_use_case = ContextUseCase(use_case)
        use_case_filters = USE_CASE_FILTERS[selected_use_case]
        filters = tuple(topic_filters or use_case_filters)

        status = await self._git("status", "--short", "--branch")
        diff_stat = await self._git("diff", "--stat")
        staged_stat = await self._git("diff", "--cached", "--stat")
        recent_commits = await self._git("log", "--oneline", "--decorate", "-n", "16")
        changed_files = await self._changed_files() if changed_files_only else await self._repo_files()
        changed_files = self._apply_topic_filters(changed_files, filters)

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

        instructions = task_instructions or USE_CASE_INSTRUCTIONS[selected_use_case]
        created = "1970-01-01T00:00:00+00:00" if deterministic else datetime.now(UTC).isoformat(timespec="seconds")
        pid = "0" if deterministic else str(os.getpid())
        body = "\n\n".join(
            [
                "# Sovereign Engineering OS Context Pack",
                f"- Created: {created}",
                f"- Repo: `{self.repo_root}`",
                f"- Use Case: `{selected_use_case.value}`",
                f"- Task Instructions: {self._sanitize(instructions)}",
                f"- Selection Mode: `{'changed_files' if changed_files_only else 'repository_files'}`",
                f"- Topic Filters: `{', '.join(filters) if filters else '<none>'}`",
                f"- Python: `{sys.version.split()[0]}`",
                f"- Platform: `{platform.platform()}`",
                f"- PID: `{pid}`",
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
        summary_mode = False
        encoded_body = body.encode("utf-8")
        if len(encoded_body) > max_output_bytes:
            summary_mode = True
            body = self._summary_body(
                created=created,
                selected_use_case=selected_use_case,
                instructions=instructions,
                changed_files=changed_files[:max_files],
                skipped=skipped,
                filters=filters,
            )
            encoded_body = body.encode("utf-8")
            if len(encoded_body) > max_output_bytes:
                body = encoded_body[:max_output_bytes].decode("utf-8", errors="ignore")
                body += "\n[TRUNCATED_BY_CONTEXT_ROUTER_BUDGET]\n"
        stamp = "deterministic" if deterministic else datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        path = self.output_dir / f"context_pack_{stamp}.md"
        await asyncio.to_thread(path.write_text, body + "\n", "utf-8")
        sha256 = await asyncio.to_thread(_sha256_file, path)
        return ContextPackResult(
            path=path,
            sha256=sha256,
            size_bytes=path.stat().st_size,
            skipped_paths=tuple(skipped),
            summary_mode=summary_mode,
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

    async def _repo_files(self) -> list[str]:
        output = await self._git("ls-files", "--cached", "--others", "--exclude-standard")
        return sorted({line.strip() for line in output.splitlines() if line.strip()})

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
        if path.name.lower() in SKIP_FILE_NAMES:
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

    @staticmethod
    def _apply_topic_filters(files: Sequence[str], filters: Sequence[str]) -> list[str]:
        if not filters:
            return list(files)
        normalized = tuple(item.lower() for item in filters)
        return [relative for relative in files if any(topic in relative.lower() for topic in normalized)]

    def _summary_body(
        self,
        *,
        created: str,
        selected_use_case: ContextUseCase,
        instructions: str,
        changed_files: Sequence[str],
        skipped: Sequence[str],
        filters: Sequence[str],
    ) -> str:
        return "\n\n".join(
            [
                "# Sovereign Engineering OS Context Pack",
                f"- Created: {created}",
                f"- Repo: `{self.repo_root}`",
                f"- Use Case: `{selected_use_case.value}`",
                f"- Task Instructions: {self._sanitize(instructions)}",
                "- Summary Mode: `budget_enforced`",
                f"- Topic Filters: `{', '.join(filters) if filters else '<none>'}`",
                "## Selected Files",
                "\n".join(f"- `{item}`" for item in changed_files) if changed_files else "<none>",
                "## Purged Paths",
                "\n".join(f"- `{item}`" for item in skipped) if skipped else "<none>",
            ]
        )


def _read_text_excerpt(path: Path, max_bytes: int) -> str:
    with path.open("rb") as handle:
        data = handle.read(max_bytes)
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
