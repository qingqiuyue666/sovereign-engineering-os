"""Command envelope admission router v1.

This module is the narrow physical safety gate between LLM-authored XML
envelopes and optional local validation commands. Payloads may express only a
``COMMAND_ID`` intent. The executable argv is resolved exclusively from the
immutable local registry below, and execution is disabled unless the caller
explicitly passes ``execute=True``.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from types import MappingProxyType
from typing import Mapping
import hashlib
import json
import subprocess
import xml.etree.ElementTree as ET

__all__ = [
    "ALLOWED_ENVELOPE_FIELDS",
    "ALLOWED_EXECUTION_LEVELS",
    "ALLOWED_STATUS_VALUES",
    "COMMAND_REGISTRY",
    "FORBIDDEN_PAYLOAD_FIELDS",
    "CommandAdmissionReport",
    "CommandExecutionReceipt",
    "CommandRegistryEntry",
    "argv_hash",
    "route_envelope",
]

POLICY_ID = "command_envelope_admission_router_v1"

ALLOWED_STATUS_VALUES = frozenset(("PASS", "BLOCKED", "FATAL"))
ALLOWED_ENVELOPE_FIELDS = frozenset(
    (
        "STATUS",
        "COMMAND_ID",
        "TOKEN_ID",
        "APPROVAL_ID",
        "POLICY_ID",
        "RUN_ID",
        "REASON",
    )
)
FORBIDDEN_PAYLOAD_FIELDS = frozenset(
    (
        "COMMAND",
        "RAW_COMMAND",
        "COMMAND_LINE",
        "ARGV",
        "ARGS",
        "SHELL",
        "SCRIPT",
        "BASH",
        "PYTHON_CODE",
        "EXECUTABLE",
        "EXECUTABLE_PATH",
        "WORKDIR",
        "CWD",
        "ENV",
        "ENVIRONMENT",
        "PATH",
        "PATH_OVERRIDE",
        "URL",
        "NETWORK",
        "BROWSER",
        "PROVIDER",
        "CREDENTIAL",
        "SECRET",
        "TOKEN_VALUE",
        "FILE_WRITE_PATH",
        "DELETE_PATH",
        "HOME_PATH",
    )
)
ALLOWED_EXECUTION_LEVELS = frozenset(
    (
        "LEVEL_0_VERIFY_ONLY",
        "LEVEL_1_FIXTURE_ONLY",
        "LEVEL_2_ALLOWLISTED_LOCAL_COMMAND",
    )
)
HIGH_RISK = "HIGH_RISK"


@dataclass(frozen=True)
class CommandRegistryEntry:
    command_id: str
    argv: tuple[str, ...]
    argv_hash: str
    description: str
    policy_id: str
    risk_class: str
    execution_level: str
    timeout_seconds: int
    cwd_policy: str
    env_policy_id: str
    approval_required: bool
    token_required: bool


@dataclass(frozen=True)
class CommandAdmissionReport:
    run_id: str
    command_id: str | None
    admitted: bool
    would_execute: bool
    executed: bool
    failure_classification: str
    failures: tuple[str, ...]
    policy_id: str | None
    token_id: str | None
    approval_id: str | None
    registry_argv_hash: str | None
    content_hash: str
    observed_at: str

    def as_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["failures"] = list(self.failures)
        return data


@dataclass(frozen=True)
class CommandExecutionReceipt:
    run_id: str
    command_id: str
    returncode: int
    stdout_sha256: str
    stderr_sha256: str
    registry_argv_hash: str
    policy_id: str
    token_id: str | None
    approval_id: str | None
    started_at: str
    completed_at: str
    receipt_hash: str

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def _canonical_json(payload: Mapping[str, object]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


def _sha256_text(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def _sha256_bytes(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


def argv_hash(argv: tuple[str, ...]) -> str:
    """Return the deterministic registry argv hash."""

    return _sha256_text(_canonical_json({"argv": list(argv)}))


def _registry_entry(
    command_id: str,
    argv: tuple[str, ...],
    description: str,
    *,
    execution_level: str,
    approval_required: bool,
    token_required: bool,
) -> CommandRegistryEntry:
    return CommandRegistryEntry(
        command_id=command_id,
        argv=argv,
        argv_hash=argv_hash(argv),
        description=description,
        policy_id=POLICY_ID,
        risk_class="LOW_RISK",
        execution_level=execution_level,
        timeout_seconds=120,
        cwd_policy="repository_default_no_payload_override",
        env_policy_id="command_envelope_registry_environment_v1",
        approval_required=approval_required,
        token_required=token_required,
    )


COMMAND_REGISTRY = MappingProxyType(
    {
        "focused_replay_engine_test": _registry_entry(
            "focused_replay_engine_test",
            (
                "python3",
                "-m",
                "unittest",
                "tests.tracer_bullet.test_replay_engine_v1",
            ),
            "Focused replay engine tracer-bullet validation.",
            execution_level="LEVEL_1_FIXTURE_ONLY",
            approval_required=True,
            token_required=True,
        ),
        "focused_external_pattern_test": _registry_entry(
            "focused_external_pattern_test",
            (
                "python3",
                "-m",
                "unittest",
                "tests.tracer_bullet.test_external_pattern_assimilation_record",
            ),
            "Focused external pattern assimilation tracer-bullet validation.",
            execution_level="LEVEL_1_FIXTURE_ONLY",
            approval_required=False,
            token_required=False,
        ),
        "diff_check": _registry_entry(
            "diff_check",
            ("git", "diff", "--check"),
            "Whitespace and conflict marker validation.",
            execution_level="LEVEL_2_ALLOWLISTED_LOCAL_COMMAND",
            approval_required=False,
            token_required=False,
        ),
    }
)


def route_envelope(
    xml_string: str,
    *,
    execute: bool = False,
) -> tuple[CommandAdmissionReport, CommandExecutionReceipt | None]:
    """Route one XML command envelope through admission and optional execution.

    ``STATUS == PASS`` is necessary but not sufficient. Admission also requires
    an allowlisted command id, matching policy id, required token/approval
    metadata, acceptable risk class, and an allowed execution level.
    """

    observed_at = _now()
    parsed_fields: dict[str, str] = {}
    failures: list[str] = []

    if not isinstance(xml_string, str) or not xml_string.strip():
        failures.append("xml_envelope_required")
    elif "<!DOCTYPE" in xml_string.upper() or "<!ENTITY" in xml_string.upper():
        failures.append("xml_doctype_or_entity_forbidden")
    else:
        parsed_fields, parse_failures = _parse_envelope_fields(xml_string)
        failures.extend(parse_failures)

    status = parsed_fields.get("STATUS")
    command_id = parsed_fields.get("COMMAND_ID")
    policy_id = parsed_fields.get("POLICY_ID")
    token_id = parsed_fields.get("TOKEN_ID")
    approval_id = parsed_fields.get("APPROVAL_ID")
    run_id = parsed_fields.get("RUN_ID") or "run-unassigned"
    registry_entry = COMMAND_REGISTRY.get(command_id or "")

    if not failures:
        if status not in ALLOWED_STATUS_VALUES:
            failures.append("status_must_be_pass_blocked_or_fatal")
        elif status != "PASS":
            failures.append(f"status_{status.lower()}_quarantined")

    if not failures:
        if not command_id:
            failures.append("command_id_required")
        elif registry_entry is None:
            failures.append("unknown_command_id")

    if not failures and registry_entry is not None:
        failures.extend(
            _admission_failures(
                registry_entry=registry_entry,
                policy_id=policy_id,
                token_id=token_id,
                approval_id=approval_id,
            )
        )

    admitted = not failures
    receipt: CommandExecutionReceipt | None = None
    executed = False
    if admitted and execute and registry_entry is not None:
        receipt = _execute_registry_entry(
            registry_entry,
            run_id=run_id,
            token_id=token_id,
            approval_id=approval_id,
        )
        executed = True

    report_fields = {
        "run_id": run_id,
        "command_id": command_id,
        "admitted": admitted,
        "would_execute": admitted,
        "executed": executed,
        "failure_classification": _failure_classification(
            admitted=admitted,
            failures=failures,
            executed=executed,
            receipt=receipt,
        ),
        "failures": tuple(failures),
        "policy_id": policy_id,
        "token_id": token_id,
        "approval_id": approval_id,
        "registry_argv_hash": None
        if registry_entry is None
        else registry_entry.argv_hash,
    }
    content_hash = _sha256_text(
        _canonical_json(
            {
                "report": _json_ready(report_fields),
                "parsed_fields": parsed_fields,
                "xml_digest": _sha256_text(xml_string),
            }
        )
    )
    report = CommandAdmissionReport(
        **report_fields,
        content_hash=content_hash,
        observed_at=observed_at,
    )
    return report, receipt


def _parse_envelope_fields(xml_string: str) -> tuple[dict[str, str], tuple[str, ...]]:
    failures: list[str] = []
    fields: dict[str, str] = {}
    try:
        root = ET.fromstring(xml_string)
    except ET.ParseError:
        return {}, ("malformed_xml",)

    if root.attrib:
        failures.append("xml_attributes_forbidden")
    for element in root:
        field_name = element.tag
        if "}" in field_name or ":" in field_name:
            failures.append("xml_namespace_forbidden")
            continue
        if list(element):
            failures.append(f"{field_name}_nested_xml_forbidden")
            continue
        if element.attrib:
            failures.append(f"{field_name}_attributes_forbidden")
            continue
        if field_name in FORBIDDEN_PAYLOAD_FIELDS:
            failures.append(f"{field_name}_forbidden")
            continue
        if field_name not in ALLOWED_ENVELOPE_FIELDS:
            failures.append(f"{field_name}_not_allowed")
            continue
        if field_name in fields:
            failures.append(f"{field_name}_duplicate")
            continue
        fields[field_name] = (element.text or "").strip()
    return fields, tuple(failures)


def _admission_failures(
    *,
    registry_entry: CommandRegistryEntry,
    policy_id: str | None,
    token_id: str | None,
    approval_id: str | None,
) -> tuple[str, ...]:
    failures: list[str] = []
    if policy_id != registry_entry.policy_id:
        failures.append("policy_id_mismatch")
    if registry_entry.token_required and not token_id:
        failures.append("token_id_required")
    if registry_entry.approval_required and not approval_id:
        failures.append("approval_id_required")
    if registry_entry.risk_class == HIGH_RISK:
        failures.append("high_risk_command_not_admitted")
    if registry_entry.execution_level not in ALLOWED_EXECUTION_LEVELS:
        failures.append("execution_level_not_allowed")
    return tuple(failures)


def _execute_registry_entry(
    registry_entry: CommandRegistryEntry,
    *,
    run_id: str,
    token_id: str | None,
    approval_id: str | None,
) -> CommandExecutionReceipt:
    started_at = _now()
    completed = subprocess.run(
        registry_entry.argv,
        capture_output=True,
        check=False,
        shell=False,
        timeout=registry_entry.timeout_seconds,
    )
    completed_at = _now()
    receipt_fields = {
        "run_id": run_id,
        "command_id": registry_entry.command_id,
        "returncode": int(completed.returncode),
        "stdout_sha256": _stream_hash(completed.stdout),
        "stderr_sha256": _stream_hash(completed.stderr),
        "registry_argv_hash": registry_entry.argv_hash,
        "policy_id": registry_entry.policy_id,
        "token_id": token_id,
        "approval_id": approval_id,
        "started_at": started_at,
        "completed_at": completed_at,
    }
    receipt_hash = compute_receipt_hash(receipt_fields)
    return CommandExecutionReceipt(**receipt_fields, receipt_hash=receipt_hash)


def compute_receipt_hash(receipt_fields: Mapping[str, object]) -> str:
    """Compute a receipt hash while excluding timestamp fields."""

    stable = {
        key: value
        for key, value in receipt_fields.items()
        if key not in {"started_at", "completed_at", "receipt_hash"}
    }
    return _sha256_text(_canonical_json(stable))


def _stream_hash(value: object) -> str:
    if value is None:
        return _sha256_bytes(b"")
    if isinstance(value, bytes):
        return _sha256_bytes(value)
    if isinstance(value, str):
        return _sha256_text(value)
    return _sha256_text(str(value))


def _failure_classification(
    *,
    admitted: bool,
    failures: list[str],
    executed: bool,
    receipt: CommandExecutionReceipt | None,
) -> str:
    if admitted and not executed:
        return "ADMITTED_DRY_RUN"
    if admitted and receipt is not None and receipt.returncode == 0:
        return "EXECUTED"
    if admitted and receipt is not None:
        return "EXECUTED_NONZERO"
    if any(failure.endswith("_quarantined") for failure in failures):
        return "QUARANTINED"
    if "malformed_xml" in failures or "xml_envelope_required" in failures:
        return "FAIL_CLOSED"
    return "REJECTED"


def _json_ready(payload: Mapping[str, object]) -> dict[str, object]:
    ready: dict[str, object] = {}
    for key, value in payload.items():
        if isinstance(value, tuple):
            ready[key] = list(value)
        else:
            ready[key] = value
    return ready
