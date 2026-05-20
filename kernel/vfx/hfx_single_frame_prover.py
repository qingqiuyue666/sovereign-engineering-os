"""Single-frame hython execution prover for audited HFX HIP files.

This orchestrator reads the strict JSON emitted by ``hfx_topology_auditor.py``.
It refuses placeholder guides, invokes a headless hython subprocess to render
exactly frame 1, validates the physical frame bytes, computes SHA-256 metadata,
and writes the successful proof into the render artifact ledger.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Final
import argparse
import hashlib
import json
import os
import re
import shlex
import shutil
import signal
import subprocess
import tempfile
import time
import uuid

from kernel.vfx.render_artifact_ledger import (
    ArtifactLedgerError,
    RenderArtifactRecord,
    record_render_artifact,
)


PROOF_SCHEMA_VERSION: Final[str] = "hfx-single-frame-prover-v1"
AUDIT_SCHEMA_VERSION: Final[str] = "hfx-topology-auditor-v1"
DEFAULT_HYTHON_EXECUTABLE: Final[str] = "hython"
DEFAULT_OUTPUT_PREFIX: Final[str] = "hfx_single_frame_proof"
DEFAULT_IMAGE_EXTENSION: Final[str] = "exr"
DEFAULT_TIMEOUT_SECONDS: Final[float] = 3_600.0
DEFAULT_MINIMUM_FRAME_BYTES: Final[int] = 128
DEFAULT_RENDERER_TYPE_TOKENS: Final[tuple[str, ...]] = (
    "opengl",
    "ogl",
    "karma",
    "usdrender",
    "usd_render",
    "mantra",
    "ifd",
)
DEFAULT_OUTPUT_PARAMETER_CANDIDATES: Final[tuple[str, ...]] = (
    "picture",
    "vm_picture",
    "lopoutput",
    "outputimage",
    "output",
    "filename",
)
_EXR_MAGIC: Final[bytes] = b"\x76\x2f\x31\x01"
_PNG_MAGIC: Final[bytes] = b"\x89PNG\r\n\x1a\n"
_READ_CHUNK_BYTES: Final[int] = 1024 * 1024
_MAX_OUTPUT_CHARS: Final[int] = 240_000
_SAFE_PREFIX_RE: Final[re.Pattern[str]] = re.compile(r"\A[A-Za-z0-9][A-Za-z0-9._-]{0,127}\Z")
_SAFE_NODE_PATH_RE: Final[re.Pattern[str]] = re.compile(r"\A/[A-Za-z0-9_./-]{1,512}\Z")
_SAFE_PARAMETER_RE: Final[re.Pattern[str]] = re.compile(r"\A[A-Za-z][A-Za-z0-9_]{0,63}\Z")
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


class HfxSingleFrameProofError(RuntimeError):
    """Raised when the single-frame proof cannot be completed safely."""


@dataclass(frozen=True, slots=True)
class AuditRenderNode:
    """Renderer candidate imported from the topology audit JSON."""

    path: str
    type_name: str
    output_parameter: str | None
    valid_renderer: bool
    selected: bool = False

    @property
    def render_priority(self) -> int:
        type_name = self.type_name.lower()
        if "opengl" in type_name or "ogl" in type_name:
            return 90
        if "karma" in type_name or "usdrender" in type_name or "usd_render" in type_name:
            return 80
        if "mantra" in type_name or "ifd" in type_name:
            return 70
        return 10

    def as_dict(self) -> dict[str, object]:
        return {
            "output_parameter": self.output_parameter,
            "path": self.path,
            "render_priority": self.render_priority,
            "selected": self.selected,
            "type_name": self.type_name,
            "valid_renderer": self.valid_renderer,
        }


@dataclass(frozen=True, slots=True)
class AdmittedAudit:
    """Validated audit report with enough information to launch proof rendering."""

    audit_json_path: Path
    hip_file: Path
    effective_point_count: int
    minimum_real_asset_points: int
    selected_render_node_path: str
    candidates: tuple[AuditRenderNode, ...]
    raw_report: Mapping[str, object]

    def render_attempts(self) -> tuple[AuditRenderNode, ...]:
        selected = [candidate for candidate in self.candidates if candidate.selected]
        fallback = sorted(
            [candidate for candidate in self.candidates if not candidate.selected],
            key=lambda candidate: (candidate.render_priority, candidate.path),
            reverse=True,
        )
        return tuple(selected + fallback)


@dataclass(frozen=True, slots=True)
class FrameArtifact:
    """Physical checksum metadata for the rendered single frame."""

    path: Path
    size_bytes: int
    sha256: str
    extension: str
    byte_probe: Mapping[str, object]

    def as_dict(self) -> dict[str, object]:
        return {
            "byte_probe": dict(self.byte_probe),
            "extension": self.extension,
            "path": self.path.as_posix(),
            "sha256": self.sha256,
            "size_bytes": self.size_bytes,
        }


@dataclass(frozen=True, slots=True)
class HythonAttemptResult:
    """One headless hython render attempt against one ROP node."""

    candidate: AuditRenderNode
    argv: tuple[str, ...]
    output_directory: Path
    expected_frame_path: Path
    output_pattern: str
    returncode: int
    stdout: str
    stderr: str
    duration_seconds: float
    timed_out: bool
    artifact: FrameArtifact | None
    failure: str | None

    @property
    def complete(self) -> bool:
        return (
            self.returncode == 0
            and not self.timed_out
            and self.artifact is not None
            and self.failure is None
        )

    @property
    def command_line(self) -> str:
        return shlex.join(self.argv)

    def as_dict(self) -> dict[str, object]:
        return {
            "artifact": self.artifact.as_dict() if self.artifact else None,
            "candidate": self.candidate.as_dict(),
            "command_line": self.command_line,
            "complete": self.complete,
            "duration_seconds": self.duration_seconds,
            "expected_frame_path": self.expected_frame_path.as_posix(),
            "failure": self.failure,
            "output_directory": self.output_directory.as_posix(),
            "output_pattern": self.output_pattern,
            "returncode": self.returncode,
            "stderr": self.stderr,
            "stdout": self.stdout,
            "timed_out": self.timed_out,
        }


@dataclass(frozen=True, slots=True)
class SingleFrameProofResult:
    """Final proof result including the render artifact ledger record."""

    schema_version: str
    created_at: str
    audit_json_path: Path
    hip_file: Path
    complete: bool
    attempts: tuple[HythonAttemptResult, ...]
    winning_attempt: HythonAttemptResult | None
    ledger_record: RenderArtifactRecord | None
    ledger_error: str | None

    def as_dict(self) -> dict[str, object]:
        return {
            "attempts": [attempt.as_dict() for attempt in self.attempts],
            "audit_json_path": self.audit_json_path.as_posix(),
            "complete": self.complete,
            "created_at": self.created_at,
            "hip_file": self.hip_file.as_posix(),
            "ledger_error": self.ledger_error,
            "ledger_record": (
                self.ledger_record.as_dict() if self.ledger_record is not None else None
            ),
            "schema_version": self.schema_version,
            "winning_attempt": (
                self.winning_attempt.as_dict()
                if self.winning_attempt is not None
                else None
            ),
        }

    def to_json(self) -> str:
        return json.dumps(
            self.as_dict(),
            ensure_ascii=True,
            indent=2,
            sort_keys=True,
        )


def prove_single_frame(
    audit_json_path: Path | str,
    *,
    output_root: Path | str | None = None,
    hython_executable: Path | str = DEFAULT_HYTHON_EXECUTABLE,
    output_prefix: str = DEFAULT_OUTPUT_PREFIX,
    image_extension: str = DEFAULT_IMAGE_EXTENSION,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    minimum_frame_bytes: int = DEFAULT_MINIMUM_FRAME_BYTES,
    ledger_root: Path | str | None = None,
) -> SingleFrameProofResult:
    """Read an auditor report, render frame 1 via hython, and ledger the proof."""

    admitted_audit = load_admitted_audit(audit_json_path)
    admitted_output_root = _admit_output_root(output_root)
    hython = _resolve_hython_executable(hython_executable)
    admitted_output_prefix = _admit_output_prefix(output_prefix)
    admitted_extension = _admit_image_extension(image_extension)
    if timeout_seconds <= 0:
        raise HfxSingleFrameProofError("timeout_seconds must be > 0")
    if minimum_frame_bytes < 1:
        raise HfxSingleFrameProofError("minimum_frame_bytes must be >= 1")

    attempts: list[HythonAttemptResult] = []
    winning_attempt: HythonAttemptResult | None = None
    for index, candidate in enumerate(admitted_audit.render_attempts(), start=1):
        attempt_output_directory = admitted_output_root / f"attempt_{index:02d}_{_safe_slug(candidate.path)}"
        attempt = _render_one_candidate(
            admitted_audit,
            candidate,
            hython_executable=hython,
            output_directory=attempt_output_directory,
            output_prefix=admitted_output_prefix,
            image_extension=admitted_extension,
            timeout_seconds=timeout_seconds,
            minimum_frame_bytes=minimum_frame_bytes,
        )
        attempts.append(attempt)
        if attempt.complete:
            winning_attempt = attempt
            break

    ledger_record: RenderArtifactRecord | None = None
    ledger_error: str | None = None
    complete = winning_attempt is not None
    if winning_attempt is not None:
        try:
            ledger_record = _record_single_frame_artifact(
                admitted_audit,
                winning_attempt,
                ledger_root=ledger_root,
            )
        except ArtifactLedgerError as exc:
            ledger_error = str(exc)
            complete = False

    return SingleFrameProofResult(
        schema_version=PROOF_SCHEMA_VERSION,
        created_at=datetime.now(UTC).isoformat(timespec="seconds"),
        audit_json_path=admitted_audit.audit_json_path,
        hip_file=admitted_audit.hip_file,
        complete=complete,
        attempts=tuple(attempts),
        winning_attempt=winning_attempt,
        ledger_record=ledger_record,
        ledger_error=ledger_error,
    )


def load_admitted_audit(audit_json_path: Path | str) -> AdmittedAudit:
    """Load and fail-closed validate an auditor JSON report."""

    path = Path(audit_json_path).expanduser().resolve()
    if not path.exists() or not path.is_file():
        raise HfxSingleFrameProofError(f"audit JSON file is missing: {path}")
    with path.open("r", encoding="utf-8") as handle:
        report = json.load(handle)
    if not isinstance(report, dict):
        raise HfxSingleFrameProofError("audit JSON root must be an object")
    schema_version = _require_string(report, "schema_version")
    if schema_version != AUDIT_SCHEMA_VERSION:
        raise HfxSingleFrameProofError(f"unsupported audit schema version: {schema_version}")
    status = _require_string(report, "status")
    classification = _require_string(report, "classification")
    if status != "PASS" or classification != "Real Asset":
        raise HfxSingleFrameProofError(
            "audit report is not a Real Asset PASS; refusing to render placeholder"
        )
    hip_file = Path(_require_string(report, "hip_file")).expanduser().resolve()
    if not hip_file.exists() or not hip_file.is_file():
        raise HfxSingleFrameProofError(f"audited HIP file is missing: {hip_file}")
    minimum_real_asset_points = _require_int(report, "minimum_real_asset_points")
    effective_point_count = _require_int(report, "effective_point_count")
    if effective_point_count < minimum_real_asset_points:
        raise HfxSingleFrameProofError("audit point count is below threshold")
    selected_payload = _require_mapping(report.get("selected_render_node"), "selected_render_node")
    selected_path = _require_string(selected_payload, "path")
    if not _SAFE_NODE_PATH_RE.fullmatch(selected_path):
        raise HfxSingleFrameProofError("selected render node path is unsafe")

    candidates_payload = report.get("render_node_candidates")
    if not isinstance(candidates_payload, list):
        raise HfxSingleFrameProofError("render_node_candidates must be a list")
    candidates: list[AuditRenderNode] = []
    seen_paths: set[str] = set()
    for item in candidates_payload:
        item_mapping = _require_mapping(item, "render_node_candidate")
        candidate = _audit_render_node_from_mapping(item_mapping, selected_path)
        if not candidate.valid_renderer:
            continue
        if candidate.path in seen_paths:
            continue
        seen_paths.add(candidate.path)
        candidates.append(candidate)
    if selected_path not in seen_paths:
        selected_candidate = _audit_render_node_from_mapping(selected_payload, selected_path)
        if not selected_candidate.valid_renderer:
            raise HfxSingleFrameProofError("selected render node is not a valid renderer")
        candidates.insert(0, selected_candidate)
    if not candidates:
        raise HfxSingleFrameProofError("audit report contains no valid renderer candidates")
    return AdmittedAudit(
        audit_json_path=path,
        hip_file=hip_file,
        effective_point_count=effective_point_count,
        minimum_real_asset_points=minimum_real_asset_points,
        selected_render_node_path=selected_path,
        candidates=tuple(candidates),
        raw_report=report,
    )


def _audit_render_node_from_mapping(
    payload: Mapping[str, object],
    selected_path: str,
) -> AuditRenderNode:
    path = _require_string(payload, "path")
    if not _SAFE_NODE_PATH_RE.fullmatch(path):
        raise HfxSingleFrameProofError(f"unsafe render node path in audit report: {path}")
    output_parameter_value = payload.get("output_parameter")
    output_parameter = (
        output_parameter_value
        if isinstance(output_parameter_value, str) and output_parameter_value
        else None
    )
    if output_parameter is not None and not _SAFE_PARAMETER_RE.fullmatch(output_parameter):
        output_parameter = None
    return AuditRenderNode(
        path=path,
        type_name=_require_string(payload, "type_name"),
        output_parameter=output_parameter,
        valid_renderer=bool(payload.get("valid_renderer")),
        selected=path == selected_path,
    )


def _render_one_candidate(
    admitted_audit: AdmittedAudit,
    candidate: AuditRenderNode,
    *,
    hython_executable: str,
    output_directory: Path,
    output_prefix: str,
    image_extension: str,
    timeout_seconds: float,
    minimum_frame_bytes: int,
) -> HythonAttemptResult:
    output_directory.mkdir(parents=True, exist_ok=True)
    expected_frame_path = output_directory / f"{output_prefix}.0001.{image_extension}"
    if expected_frame_path.exists():
        raise HfxSingleFrameProofError(f"expected frame path already exists: {expected_frame_path}")
    output_pattern = (output_directory / f"{output_prefix}.$F4.{image_extension}").as_posix()
    config = {
        "allowed_renderer_type_tokens": list(DEFAULT_RENDERER_TYPE_TOKENS),
        "end_frame": 1,
        "hip_file": admitted_audit.hip_file.as_posix(),
        "output_parameter": candidate.output_parameter,
        "output_parameter_candidates": list(DEFAULT_OUTPUT_PARAMETER_CANDIDATES),
        "output_pattern": output_pattern,
        "rop_node_path": candidate.path,
        "start_frame": 1,
        "step": 1,
    }
    with tempfile.TemporaryDirectory(prefix="hfx_single_frame_hython_") as temp_dir_name:
        temp_dir = Path(temp_dir_name)
        driver_path = temp_dir / "single_frame_driver.py"
        config_path = temp_dir / "single_frame_config.json"
        driver_path.write_text(_HYTHON_SINGLE_FRAME_DRIVER, encoding="utf-8")
        config_path.write_text(
            json.dumps(config, ensure_ascii=True, sort_keys=True),
            encoding="utf-8",
        )
        argv = (hython_executable, driver_path.as_posix(), config_path.as_posix())
        start = time.monotonic()
        process = subprocess.Popen(
            argv,
            cwd=output_directory,
            env=_build_child_env(),
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

    artifact: FrameArtifact | None = None
    failure: str | None = None
    if timed_out:
        failure = "hython_timeout"
    elif process.returncode != 0:
        failure = f"hython_returncode_{process.returncode}"
    else:
        try:
            artifact = _validate_rendered_frame(
                expected_frame_path,
                image_extension=image_extension,
                minimum_frame_bytes=minimum_frame_bytes,
            )
        except HfxSingleFrameProofError as exc:
            failure = str(exc)

    return HythonAttemptResult(
        candidate=candidate,
        argv=argv,
        output_directory=output_directory,
        expected_frame_path=expected_frame_path,
        output_pattern=output_pattern,
        returncode=int(process.returncode),
        stdout=_clip_output(stdout),
        stderr=_clip_output(stderr),
        duration_seconds=duration,
        timed_out=timed_out,
        artifact=artifact,
        failure=failure,
    )


def _record_single_frame_artifact(
    admitted_audit: AdmittedAudit,
    attempt: HythonAttemptResult,
    *,
    ledger_root: Path | str | None,
) -> RenderArtifactRecord:
    if attempt.artifact is None:
        raise ArtifactLedgerError("cannot ledger missing single-frame artifact")
    if attempt.artifact.extension != "exr":
        raise ArtifactLedgerError("render_artifact_ledger currently admits EXR proofs only")
    frame_prefix = _frame_prefix_from_path(attempt.expected_frame_path)
    return record_render_artifact(
        attempt.output_directory,
        sequence_glob=f"{frame_prefix}.*.exr",
        frame_pattern=f"{frame_prefix}.%04d.exr",
        metadata={
            "audit_effective_point_count": admitted_audit.effective_point_count,
            "audit_json_path": admitted_audit.audit_json_path.as_posix(),
            "audit_minimum_real_asset_points": admitted_audit.minimum_real_asset_points,
            "executor": "kernel.vfx.hfx_single_frame_prover",
            "frame": 1,
            "hip_file": admitted_audit.hip_file.as_posix(),
            "physical_frame": attempt.artifact.as_dict(),
            "proof_schema_version": PROOF_SCHEMA_VERSION,
            "rop_node_path": attempt.candidate.path,
            "rop_type_name": attempt.candidate.type_name,
            "single_frame_output_pattern": attempt.output_pattern,
        },
        ledger_root=ledger_root,
    )


def _frame_prefix_from_path(path: Path) -> str:
    suffix = ".0001.exr"
    name = path.name
    if not name.endswith(suffix):
        raise ArtifactLedgerError(f"unexpected single-frame EXR name: {name}")
    prefix = name[: -len(suffix)]
    if not _SAFE_PREFIX_RE.fullmatch(prefix):
        raise ArtifactLedgerError(f"unsafe single-frame output prefix: {prefix}")
    return prefix


def _validate_rendered_frame(
    path: Path,
    *,
    image_extension: str,
    minimum_frame_bytes: int,
) -> FrameArtifact:
    if not path.exists():
        raise HfxSingleFrameProofError(f"expected frame was not created: {path}")
    if path.is_symlink():
        raise HfxSingleFrameProofError(f"rendered frame may not be a symlink: {path}")
    if not path.is_file():
        raise HfxSingleFrameProofError(f"rendered frame is not a regular file: {path}")
    size_bytes = path.stat().st_size
    if size_bytes <= 0:
        raise HfxSingleFrameProofError(f"rendered frame is 0 bytes: {path}")
    if size_bytes < minimum_frame_bytes:
        raise HfxSingleFrameProofError(
            f"rendered frame is below minimum size {minimum_frame_bytes}: {path}"
        )
    with path.open("rb") as handle:
        magic = handle.read(8)
    if image_extension == "exr" and magic[: len(_EXR_MAGIC)] != _EXR_MAGIC:
        raise HfxSingleFrameProofError(f"rendered frame is not an EXR file: {path}")
    if image_extension == "png" and magic != _PNG_MAGIC:
        raise HfxSingleFrameProofError(f"rendered frame is not a PNG file: {path}")
    byte_probe = _probe_frame_bytes(path)
    if bool(byte_probe["all_zero_payload"]):
        raise HfxSingleFrameProofError(f"rendered frame payload is all zero bytes: {path}")
    if int(byte_probe["unique_byte_values"]) <= 2:
        raise HfxSingleFrameProofError(f"rendered frame has near-constant byte payload: {path}")
    return FrameArtifact(
        path=path,
        size_bytes=size_bytes,
        sha256=_sha256_file(path),
        extension=image_extension,
        byte_probe=byte_probe,
    )


def _probe_frame_bytes(path: Path) -> dict[str, object]:
    data = path.read_bytes()
    payload = data[len(_PNG_MAGIC) :] if data.startswith(_PNG_MAGIC) else data[len(_EXR_MAGIC) :]
    if not payload:
        payload = data
    unique_values = len(set(payload))
    nonzero_bytes = sum(1 for byte in payload if byte != 0)
    return {
        "all_zero_payload": nonzero_bytes == 0,
        "nonzero_byte_count": nonzero_bytes,
        "probe_size_bytes": len(payload),
        "unique_byte_values": unique_values,
    }


def _admit_output_root(output_root: Path | str | None) -> Path:
    if output_root is None:
        return Path(tempfile.mkdtemp(prefix="hfx_single_frame_proof_")).resolve()
    path = Path(output_root).expanduser().resolve()
    if path.exists() and not path.is_dir():
        raise HfxSingleFrameProofError(f"output root is not a directory: {path}")
    if path.exists() and path.is_symlink():
        raise HfxSingleFrameProofError(f"output root may not be a symlink: {path}")
    path.mkdir(parents=True, exist_ok=True)
    return path


def _admit_output_prefix(output_prefix: str) -> str:
    if not _SAFE_PREFIX_RE.fullmatch(output_prefix):
        raise HfxSingleFrameProofError("output_prefix must be alphanumeric plus . _ -")
    return output_prefix


def _admit_image_extension(image_extension: str) -> str:
    normalized = image_extension.lower().lstrip(".")
    if normalized not in {"exr", "png"}:
        raise HfxSingleFrameProofError("image_extension must be exr or png")
    return normalized


def _resolve_hython_executable(hython_executable: Path | str) -> str:
    executable = str(hython_executable)
    if not executable:
        raise HfxSingleFrameProofError("hython executable is required")
    if any(character in executable for character in ("\x00", "\n", "\r")):
        raise HfxSingleFrameProofError("hython executable contains control characters")
    if "/" in executable or "\\" in executable:
        path = Path(executable).expanduser().resolve()
        if not path.exists() or not path.is_file():
            raise HfxSingleFrameProofError(f"hython executable is missing: {path}")
        if not os.access(path, os.X_OK):
            raise HfxSingleFrameProofError(f"hython executable is not executable: {path}")
        return path.as_posix()
    if not _SAFE_PARAMETER_RE.fullmatch(executable):
        raise HfxSingleFrameProofError("hython executable command name is unsafe")
    resolved = shutil.which(executable)
    if resolved is None:
        raise HfxSingleFrameProofError(f"hython executable not found on PATH: {executable}")
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


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(_READ_CHUNK_BYTES), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_slug(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9._-]+", "_", value.strip("/"))
    if not slug:
        return uuid.uuid4().hex
    return slug[:96]


def _clip_output(output: str) -> str:
    if len(output) <= _MAX_OUTPUT_CHARS:
        return output
    return f"{output[:_MAX_OUTPUT_CHARS]}\n...[output truncated at {_MAX_OUTPUT_CHARS} chars]"


def _require_string(payload: Mapping[str, object], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value:
        raise HfxSingleFrameProofError(f"{key} must be a nonempty string")
    return value


def _require_int(payload: Mapping[str, object], key: str) -> int:
    value = payload.get(key)
    if not isinstance(value, int):
        raise HfxSingleFrameProofError(f"{key} must be an integer")
    return value


def _require_mapping(value: object, label: str) -> Mapping[str, object]:
    if not isinstance(value, dict):
        raise HfxSingleFrameProofError(f"{label} must be an object")
    return value


_HYTHON_SINGLE_FRAME_DRIVER: Final[str] = r'''
import json
import sys


def _find_output_parm(rop, preferred, candidates):
    names = []
    if preferred:
        names.append(preferred)
    names.extend(candidates)
    seen = set()
    for name in names:
        if name in seen:
            continue
        seen.add(name)
        parm = rop.parm(name)
        if parm is not None:
            return name, parm
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
    hou.setFrame(1)
    rop = hou.node(config["rop_node_path"])
    if rop is None:
        raise RuntimeError("ROP node does not exist: %s" % config["rop_node_path"])
    rop_type_name = rop.type().name().lower()
    allowed = tuple(config["allowed_renderer_type_tokens"])
    if not any(token in rop_type_name for token in allowed):
        raise RuntimeError("ROP type is not allowed for proof render: %s" % rop_type_name)

    output_parm_name, output_parm = _find_output_parm(
        rop,
        config.get("output_parameter"),
        config["output_parameter_candidates"],
    )
    output_parm.set(config["output_pattern"])
    _set_if_present(rop, "trange", 1)
    _set_if_present(rop, "f1", 1)
    _set_if_present(rop, "f2", 1)
    _set_if_present(rop, "f3", 1)

    rop.render(frame_range=(1, 1, 1), verbose=True)
    print(
        "HFX_SINGLE_FRAME_RESULT="
        + json.dumps(
            {
                "frame": 1,
                "ok": True,
                "output_parameter": output_parm_name,
                "output_pattern": config["output_pattern"],
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
    parser = argparse.ArgumentParser(description="Prove one audited HFX HIP with a frame-1 hython render.")
    parser.add_argument("--audit-json", required=True)
    parser.add_argument("--output-root", default=None)
    parser.add_argument("--hython", default=DEFAULT_HYTHON_EXECUTABLE)
    parser.add_argument("--output-prefix", default=DEFAULT_OUTPUT_PREFIX)
    parser.add_argument("--image-extension", default=DEFAULT_IMAGE_EXTENSION, choices=("exr", "png"))
    parser.add_argument("--timeout-seconds", type=float, default=DEFAULT_TIMEOUT_SECONDS)
    parser.add_argument("--minimum-frame-bytes", type=int, default=DEFAULT_MINIMUM_FRAME_BYTES)
    parser.add_argument("--ledger-root", default=None)
    parser.add_argument("--json-output", default=None)
    return parser


def _write_json_output(path: Path | str | None, payload: Mapping[str, object]) -> None:
    if path is None:
        return
    output_path = Path(path).expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_arg_parser()
    args = parser.parse_args(argv)
    try:
        result = prove_single_frame(
            args.audit_json,
            output_root=args.output_root,
            hython_executable=args.hython,
            output_prefix=args.output_prefix,
            image_extension=args.image_extension,
            timeout_seconds=args.timeout_seconds,
            minimum_frame_bytes=args.minimum_frame_bytes,
            ledger_root=args.ledger_root,
        )
        payload = result.as_dict()
        exit_code = 0 if result.complete else 2
    except Exception as exc:
        payload = {
            "complete": False,
            "created_at": datetime.now(UTC).isoformat(timespec="seconds"),
            "error": str(exc),
            "schema_version": PROOF_SCHEMA_VERSION,
        }
        exit_code = 2
    _write_json_output(args.json_output, payload)
    print(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
