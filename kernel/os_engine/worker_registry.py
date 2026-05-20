"""Registered worker contracts for the local Sovereign OS execution bus."""

from __future__ import annotations

import shlex
import sys
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Protocol, Sequence, runtime_checkable

from kernel.os_engine.artifact_store import ArtifactRecord, ArtifactStore
from kernel.os_engine.context_router import ContextRouter
from kernel.os_engine.job_queue import Job, JobValidationError, JsonValue, UnknownJobTypeError
from kernel.os_engine.memory_watchdog import ProcessLimits, ProcessResult, ProcessSupervisor


class WorkerAdmissionError(RuntimeError):
    """Raised when a worker refuses a job before queue admission."""


SUPPORTED_CAPABILITIES = frozenset(
    {
        "artifact_collection",
        "context_pack",
        "git_read",
        "houdini_single_frame_proof",
        "houdini_topology_audit",
        "subprocess",
        "test_execution",
    }
)


@dataclass(frozen=True, slots=True)
class WorkerCapabilityReport:
    name: str
    capabilities: tuple[str, ...]
    safety_boundary: str
    can_create_large_artifacts: bool
    human_review_required: bool

    def to_json(self) -> str:
        return json.dumps(asdict(self), sort_keys=True, separators=(",", ":"))


@dataclass(frozen=True, slots=True)
class WorkerContext:
    repo_root: Path
    artifact_root: Path
    crash_dir: Path
    artifact_store: ArtifactStore | None = None
    environment: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class WorkerRunResult:
    succeeded: bool
    quarantined: bool
    exit_code: int | None = None
    stdout: str = ""
    stderr: str = ""
    artifact_paths: tuple[Path, ...] = ()
    diagnostic_path: Path | None = None
    metadata: dict[str, JsonValue] = field(default_factory=dict)

    @classmethod
    def from_process(
        cls,
        process: ProcessResult,
        *,
        artifact_paths: Sequence[Path] = (),
        metadata: dict[str, JsonValue] | None = None,
    ) -> "WorkerRunResult":
        return cls(
            succeeded=process.ok,
            quarantined=process.quarantined,
            exit_code=process.returncode,
            stdout=process.stdout,
            stderr=process.stderr,
            artifact_paths=tuple(artifact_paths),
            diagnostic_path=process.diagnostic_path,
            metadata=metadata
            or {
                "termination_reason": process.termination_reason,
                "partial_outputs_policy": process.partial_outputs_policy,
            },
        )


@runtime_checkable
class WorkerAdapter(Protocol):
    name: str
    capabilities: frozenset[str]
    safety_boundary: str
    can_create_large_artifacts: bool
    human_review_required: bool

    async def preflight(self, job: Job, context: WorkerContext) -> None:
        ...

    async def admit(self, job: Job, context: WorkerContext) -> None:
        ...

    async def run(self, job: Job, context: WorkerContext) -> WorkerRunResult:
        ...

    async def collect_artifacts(
        self,
        job: Job,
        result: WorkerRunResult,
        context: WorkerContext,
    ) -> list[ArtifactRecord]:
        ...

    async def validate_outputs(self, job: Job, result: WorkerRunResult, context: WorkerContext) -> None:
        ...

    async def quarantine_failure(self, job: Job, exc: Exception, context: WorkerContext) -> WorkerRunResult:
        ...

    def summarize(self) -> WorkerCapabilityReport:
        ...

    async def cleanup(self, job: Job, result: WorkerRunResult | None, context: WorkerContext) -> None:
        ...


class WorkerRegistry:
    def __init__(self) -> None:
        self._adapters: dict[str, WorkerAdapter] = {}

    def register(self, job_type: str, adapter: WorkerAdapter) -> None:
        normalized = self._normalize(job_type)
        if normalized in self._adapters:
            raise ValueError(f"worker type already registered: {job_type}")
        self._validate_adapter(adapter)
        self._adapters[normalized] = adapter

    def has_type(self, job_type: str) -> bool:
        return self._normalize(job_type) in self._adapters

    def get(self, job_type: str) -> WorkerAdapter:
        normalized = self._normalize(job_type)
        try:
            return self._adapters[normalized]
        except KeyError as exc:
            raise UnknownJobTypeError(f"unregistered job type blocked: {job_type}") from exc

    def registered_types(self) -> list[str]:
        return sorted(self._adapters)

    def capability_report(self) -> list[dict[str, object]]:
        return [
            asdict(self._adapters[job_type].summarize())
            for job_type in sorted(self._adapters)
        ]

    def capability_report_json(self) -> str:
        return json.dumps(self.capability_report(), sort_keys=True, separators=(",", ":"))

    @staticmethod
    def _normalize(job_type: str) -> str:
        normalized = job_type.strip()
        if not normalized:
            raise WorkerAdmissionError("worker type is required")
        return normalized

    @staticmethod
    def _validate_adapter(adapter: WorkerAdapter) -> None:
        for attribute in (
            "name",
            "capabilities",
            "safety_boundary",
            "can_create_large_artifacts",
            "human_review_required",
        ):
            if not hasattr(adapter, attribute):
                raise WorkerAdmissionError(f"worker must declare {attribute}")
        if not str(adapter.name).strip():
            raise WorkerAdmissionError("worker must declare name")
        unknown = set(adapter.capabilities).difference(SUPPORTED_CAPABILITIES)
        if unknown:
            raise WorkerAdmissionError(f"unsupported worker capabilities: {', '.join(sorted(unknown))}")
        for method in (
            "preflight",
            "admit",
            "run",
            "collect_artifacts",
            "validate_outputs",
            "quarantine_failure",
            "summarize",
        ):
            if not callable(getattr(adapter, method, None)):
                raise WorkerAdmissionError(f"worker must implement {method}()")


class BaseWorker:
    name = "BaseWorker"
    capabilities: frozenset[str] = frozenset()
    safety_boundary = "fail_closed_local_only"
    can_create_large_artifacts = False
    human_review_required = False

    async def preflight(self, job: Job, context: WorkerContext) -> None:
        _validate_job_identity(job)
        _ = context

    async def admit(self, job: Job, context: WorkerContext) -> None:
        _validate_job_identity(job)
        _ = context

    async def cleanup(self, job: Job, result: WorkerRunResult | None, context: WorkerContext) -> None:
        _ = (job, result, context)

    async def collect_artifacts(
        self,
        job: Job,
        result: WorkerRunResult,
        context: WorkerContext,
    ) -> list[ArtifactRecord]:
        if context.artifact_store is None:
            return []
        records: list[ArtifactRecord] = []
        for artifact_path in result.artifact_paths:
            record = await _register_artifact_async(context.artifact_store, job.id, artifact_path)
            records.append(record)
        return records

    async def validate_outputs(self, job: Job, result: WorkerRunResult, context: WorkerContext) -> None:
        _validate_job_identity(job)
        _ = context
        if result.succeeded and result.quarantined:
            raise WorkerAdmissionError("worker result cannot be both succeeded and quarantined")
        if result.succeeded and result.exit_code not in {0, None}:
            raise WorkerAdmissionError("worker cannot claim success with nonzero exit code")
        for artifact_path in result.artifact_paths:
            if not artifact_path.exists():
                raise WorkerAdmissionError(f"claimed artifact does not exist: {artifact_path}")

    async def quarantine_failure(self, job: Job, exc: Exception, context: WorkerContext) -> WorkerRunResult:
        _validate_job_identity(job)
        _ = context
        return WorkerRunResult(
            succeeded=False,
            quarantined=True,
            exit_code=None,
            stderr=str(exc),
            metadata={"quarantine_reason": str(exc)},
        )

    def summarize(self) -> WorkerCapabilityReport:
        return WorkerCapabilityReport(
            name=self.name,
            capabilities=tuple(sorted(self.capabilities)),
            safety_boundary=self.safety_boundary,
            can_create_large_artifacts=bool(self.can_create_large_artifacts),
            human_review_required=bool(self.human_review_required),
        )


class CommandWorker(BaseWorker):
    allowed_programs: frozenset[str] = frozenset()
    default_command: tuple[str, ...] | None = None
    stdout_limit_bytes = 8 * 1024 * 1024
    stderr_limit_bytes = 8 * 1024 * 1024
    capabilities = frozenset({"subprocess"})
    safety_boundary = "allowlisted_subprocess_shell_false_watchdog"

    async def preflight(self, job: Job, context: WorkerContext) -> None:
        await super().preflight(job, context)
        command = self._command(job)
        if not command:
            raise WorkerAdmissionError(f"{self.name} requires a command")
        program = Path(command[0]).name
        if self.allowed_programs and program not in self.allowed_programs:
            raise WorkerAdmissionError(f"{self.name} blocked program: {program}")
        self._validate_command(command, job, context)

    async def run(self, job: Job, context: WorkerContext) -> WorkerRunResult:
        command = self._command(job)
        artifact_paths = tuple(_artifact_paths_from_inputs(job, context))
        supervisor = ProcessSupervisor(crash_dir=context.crash_dir)
        process = await supervisor.run(
            command,
            cwd=context.repo_root,
            env=context.environment,
            limits=ProcessLimits(
                max_runtime_seconds=job.max_runtime,
                memory_limit_mb=job.memory_limit_mb,
                stdout_limit_bytes=self.stdout_limit_bytes,
                stderr_limit_bytes=self.stderr_limit_bytes,
            ),
        )
        return WorkerRunResult.from_process(process, artifact_paths=artifact_paths)

    def _command(self, job: Job) -> tuple[str, ...]:
        raw = job.inputs.get("command")
        if raw is None and self.default_command is not None:
            return self.default_command
        if isinstance(raw, str):
            return tuple(shlex.split(raw))
        if isinstance(raw, list) and all(isinstance(item, str) for item in raw):
            return tuple(raw)
        raise WorkerAdmissionError("command must be a shell-free string list or shlex string")

    def _validate_command(self, command: Sequence[str], job: Job, context: WorkerContext) -> None:
        _ = (command, job, context)


class GitWorker(CommandWorker):
    name = "GitWorker"
    capabilities = frozenset({"git_read", "subprocess"})
    safety_boundary = "read_only_git_subprocess"
    allowed_programs = frozenset({"git"})
    default_command = ("git", "status", "--short")
    _allowed_subcommands = frozenset(
        {
            "branch",
            "diff",
            "log",
            "rev-parse",
            "show",
            "status",
            "ls-files",
        }
    )

    def _validate_command(self, command: Sequence[str], job: Job, context: WorkerContext) -> None:
        _ = (job, context)
        if len(command) < 2 or command[1] not in self._allowed_subcommands:
            raise WorkerAdmissionError("GitWorker only permits read-only git subcommands")
        blocked = {"commit", "push", "pull", "merge", "rebase", "reset", "checkout", "switch", "clean"}
        if any(part in blocked for part in command[1:]):
            raise WorkerAdmissionError("GitWorker blocks mutating git operations")


class TestWorker(CommandWorker):
    name = "TestWorker"
    capabilities = frozenset({"test_execution", "subprocess"})
    safety_boundary = "local_test_subprocess"
    allowed_programs = frozenset({Path(sys.executable).name, "python", "python3", "pytest"})
    default_command = (sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v")
    stdout_limit_bytes = 16 * 1024 * 1024
    stderr_limit_bytes = 16 * 1024 * 1024

    def _validate_command(self, command: Sequence[str], job: Job, context: WorkerContext) -> None:
        _ = (job, context)
        program = Path(command[0]).name
        if program == "pytest":
            return
        if "-m" in command:
            module_index = command.index("-m") + 1
            if module_index < len(command) and command[module_index] in {"pytest", "unittest"}:
                return
        raise WorkerAdmissionError("TestWorker permits pytest or unittest execution only")


class ContextPackWorker(BaseWorker):
    name = "ContextPackWorker"
    capabilities = frozenset({"context_pack", "artifact_collection"})
    safety_boundary = "sanitized_git_context_no_network"

    async def preflight(self, job: Job, context: WorkerContext) -> None:
        await super().preflight(job, context)
        if not context.repo_root.exists():
            raise WorkerAdmissionError(f"repo root does not exist: {context.repo_root}")

    async def run(self, job: Job, context: WorkerContext) -> WorkerRunResult:
        output_dir = context.artifact_root / "context_packs"
        router = ContextRouter(repo_root=context.repo_root, output_dir=output_dir)
        max_files = int(job.inputs.get("max_files", 32))
        result = await router.build_context_pack(max_files=max_files)
        return WorkerRunResult(
            succeeded=True,
            quarantined=False,
            artifact_paths=(result.path,),
            metadata={
                "sha256": result.sha256,
                "size_bytes": result.size_bytes,
                "skipped_paths": list(result.skipped_paths),
            },
        )


class HoudiniTopologyAuditWorker(CommandWorker):
    name = "HoudiniTopologyAuditWorker"
    capabilities = frozenset({"houdini_topology_audit", "subprocess", "artifact_collection"})
    safety_boundary = "allowlisted_houdini_audit_subprocess"
    can_create_large_artifacts = True
    human_review_required = True
    allowed_programs = frozenset({"hython", "hbatch", "python", "python3", Path(sys.executable).name})
    stdout_limit_bytes = 32 * 1024 * 1024
    stderr_limit_bytes = 32 * 1024 * 1024

    def _validate_command(self, command: Sequence[str], job: Job, context: WorkerContext) -> None:
        _ = command
        _validate_artifact_paths(job, context)


class HoudiniSingleFrameProofWorker(CommandWorker):
    name = "HoudiniSingleFrameProofWorker"
    capabilities = frozenset({"houdini_single_frame_proof", "subprocess", "artifact_collection"})
    safety_boundary = "allowlisted_houdini_single_frame_subprocess"
    can_create_large_artifacts = True
    human_review_required = True
    allowed_programs = frozenset(
        {"hython", "hbatch", "houdini", "python", "python3", Path(sys.executable).name}
    )
    stdout_limit_bytes = 64 * 1024 * 1024
    stderr_limit_bytes = 64 * 1024 * 1024

    def _validate_command(self, command: Sequence[str], job: Job, context: WorkerContext) -> None:
        _ = command
        _validate_artifact_paths(job, context)


def build_default_worker_registry() -> WorkerRegistry:
    registry = WorkerRegistry()
    mappings: dict[str, WorkerAdapter] = {
        "GitWorker": GitWorker(),
        "git": GitWorker(),
        "TestWorker": TestWorker(),
        "test": TestWorker(),
        "ContextPackWorker": ContextPackWorker(),
        "context_pack": ContextPackWorker(),
        "HoudiniTopologyAuditWorker": HoudiniTopologyAuditWorker(),
        "houdini_topology_audit": HoudiniTopologyAuditWorker(),
        "HoudiniSingleFrameProofWorker": HoudiniSingleFrameProofWorker(),
        "houdini_single_frame_proof": HoudiniSingleFrameProofWorker(),
    }
    for job_type, adapter in mappings.items():
        registry.register(job_type, adapter)
    return registry


def _artifact_paths_from_inputs(job: Job, context: WorkerContext) -> list[Path]:
    raw = job.inputs.get("artifact_paths", [])
    if raw is None:
        return []
    if not isinstance(raw, list) or not all(isinstance(item, str) for item in raw):
        raise WorkerAdmissionError("artifact_paths must be a list of strings")
    paths = [(context.repo_root / item).resolve() if not Path(item).is_absolute() else Path(item).resolve() for item in raw]
    for path in paths:
        if not path.is_relative_to(context.artifact_root.resolve()):
            raise WorkerAdmissionError(f"artifact path must stay under artifact root: {path}")
    return paths


def _validate_artifact_paths(job: Job, context: WorkerContext) -> None:
    _artifact_paths_from_inputs(job, context)


def _validate_job_identity(job: Job) -> None:
    if not getattr(job, "id", None):
        raise JobValidationError("worker cannot run without job_id")


async def _register_artifact_async(
    store: ArtifactStore,
    job_id: str,
    artifact_path: Path,
) -> ArtifactRecord:
    import asyncio

    return await asyncio.to_thread(store.register_artifact, job_id=job_id, local_path=artifact_path)
