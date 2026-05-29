"""Security / abuse boundary hardening V1.

The hardening boundary validates proposed runtime authority before execution or
mutation. It records digest-only receipts and WAL events, rejects every listed
abuse class fail-closed, and never calls networks, providers, tools, shells, or
environment readers.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
from typing import Iterable, Mapping, Sequence

from kernel.stores.real_wal_storage import FileBackedRealWalStorage

__all__ = [
    "SECURITY_ABUSE_BOUNDARY_HARDENING_VERSION",
    "ZERO_HASH",
    "FileBackedSecurityAbuseBoundaryHardening",
    "SecurityAbuseBoundaryHardeningError",
    "SecurityAbuseBoundaryReceipt",
    "SecurityAbuseControlResult",
    "compute_security_abuse_boundary_receipt_hash",
    "compute_security_abuse_control_result_hash",
]

SECURITY_ABUSE_BOUNDARY_HARDENING_VERSION = "security_abuse_boundary_hardening_v1"
ZERO_HASH = "sha256:" + ("0" * 64)

_WAL_RELPATH = "security-abuse-boundary/security.real-wal.jsonl"
_RECEIPT_DIR_RELPATH = "security-abuse-boundary/receipts"
_CONSOLE_ROUTE = "approval_controlled_execution_runtime"
_CONTROL_IDS = (
    "unsafe_subprocess",
    "hidden_network",
    "credential_access",
    "path_traversal",
    "symlink_escape",
    "arbitrary_write",
    "daemon_default",
    "model_tool_direct_mutation",
    "approval_replay_bypass",
    "mutable_audit",
    "silent_repair",
    "uncontrolled_provider",
    "leakage",
    "env_credential_capture",
    "console_mutation_bypass",
)
_SHA256_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")
_URL_PATTERN = re.compile(r"(?i)\b(?:https?|wss?|ftp)://")
_SECRET_VALUE_PATTERNS = (
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"(?i)\bbearer\s+[a-z0-9._~+/=-]{16,}"),
    re.compile(r"(?i)\bsk-[a-z0-9]{20,}"),
    re.compile(
        r"(?s)-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----"
    ),
)
_SECRET_KEY_PATTERN = re.compile(
    r"(?i)(api[_-]?key|auth|authorization|credential|password|private[_-]?key|secret|token)"
)
_SECRET_PATH_PATTERN = re.compile(
    r"(?i)(^\.env$|\.env\.local|\.envrc|credential|id_rsa|id_dsa|id_ed25519|secret|token|password)"
)

_SUBPROCESS_KEYS = frozenset(
    {
        "args",
        "argv",
        "command",
        "command_line",
        "exec",
        "executable",
        "executable_path",
        "popen",
        "process",
        "shell",
        "subprocess",
    }
)
_SUBPROCESS_TRUE_FLAGS = frozenset(
    {
        "allow_subprocess",
        "process_launch_enabled",
        "shell_enabled",
        "subprocess_requested",
        "unsafe_subprocess",
    }
)
_NETWORK_KEYS = frozenset(
    {
        "endpoint",
        "host",
        "http_endpoint",
        "network",
        "request_url",
        "socket",
        "url",
        "webhook",
    }
)
_NETWORK_TRUE_FLAGS = frozenset(
    {
        "allow_network",
        "hidden_network",
        "network_accessed",
        "network_enabled",
        "socket_enabled",
    }
)
_CREDENTIAL_TRUE_FLAGS = frozenset(
    {
        "credential_material_read",
        "credential_read",
        "key_material_read",
        "secret_value_read",
    }
)
_PATH_KEYS = frozenset(
    {
        "artifact_path",
        "filesystem_path",
        "path",
        "paths",
        "relpath",
        "relpaths",
        "requested_write_relpath",
        "requested_write_relpaths",
        "target_path",
        "write_path",
        "write_relpath",
        "write_relpaths",
    }
)
_ARBITRARY_WRITE_FLAGS = frozenset(
    {
        "arbitrary_write",
        "filesystem_write_unscoped",
        "unbounded_write_enabled",
        "write_anywhere",
    }
)
_DAEMON_FLAGS = frozenset(
    {
        "autostart",
        "background",
        "background_daemon_enabled",
        "daemon_enabled",
        "scheduler_enabled",
    }
)
_DIRECT_MUTATION_FLAGS = frozenset(
    {
        "apply_patch_direct",
        "direct_mutation",
        "model_direct_mutation",
        "tool_direct_mutation",
    }
)
_APPROVAL_BYPASS_FLAGS = frozenset(
    {
        "approval_bypass",
        "approval_not_required",
        "replay_bypass",
        "replay_not_required",
    }
)
_MUTABLE_AUDIT_FLAGS = frozenset(
    {
        "audit_mutable",
        "audit_overwrite",
        "audit_rewrite_allowed",
        "mutable_audit",
    }
)
_SILENT_REPAIR_FLAGS = frozenset(
    {
        "repair_performed",
        "repair_without_receipt",
        "silent_repair",
    }
)
_PROVIDER_FLAGS = frozenset(
    {
        "provider_call_performed",
        "provider_enabled",
        "provider_live_call",
        "uncontrolled_provider",
    }
)
_LEAKAGE_FLAGS = frozenset(
    {
        "leak_detected",
        "plaintext_persisted",
        "raw_payload_persisted",
        "sensitive_material_persisted",
    }
)
_LEAKAGE_KEY_FRAGMENTS = (
    "content",
    "plaintext",
    "prompt",
    "provider_response",
    "raw",
    "stderr",
    "stdout",
    "traceback",
)
_ENV_KEYS = frozenset({"env", "environment", "os.environ", "process_env"})
_ENV_TRUE_FLAGS = frozenset(
    {
        "env_credential_capture",
        "env_read_enabled",
        "environment_capture_enabled",
    }
)
_CONSOLE_MUTATION_FLAGS = frozenset(
    {
        "console_mutation_bypass",
        "console_mutation_enabled",
        "direct_console_edits_enabled",
    }
)


class SecurityAbuseBoundaryHardeningError(ValueError):
    """Raised when the security boundary request is invalid."""


@dataclass(frozen=True)
class SecurityAbuseControlResult:
    control_id: str
    accepted: bool
    failures: tuple[str, ...]
    evidence_hash: str
    result_hash: str = ""

    def __post_init__(self) -> None:
        if self.control_id not in _CONTROL_IDS:
            raise SecurityAbuseBoundaryHardeningError("control_id_invalid")
        if not isinstance(self.accepted, bool):
            raise SecurityAbuseBoundaryHardeningError("accepted_must_be_bool")
        object.__setattr__(self, "failures", _normalize_failures(self.failures))
        if self.accepted and self.failures:
            raise SecurityAbuseBoundaryHardeningError("accepted_control_has_failures")
        if not self.accepted and not self.failures:
            raise SecurityAbuseBoundaryHardeningError("rejected_control_requires_failures")
        _require_sha256(self.evidence_hash, "evidence_hash")
        _install_or_verify_hash(self, "result_hash", compute_security_abuse_control_result_hash)

    def as_dict(self) -> dict[str, object]:
        return _json_ready(asdict(self))  # type: ignore[return-value]


@dataclass(frozen=True)
class SecurityAbuseBoundaryReceipt:
    integration_version: str
    accepted: bool
    failures: tuple[str, ...]
    request_id: str
    task_id: str
    run_id: str
    control_results: tuple[SecurityAbuseControlResult, ...]
    request_fingerprint_hash: str
    control_chain_hash: str
    wal_record_hash: str
    network_accessed: bool
    subprocess_spawned: bool
    credential_material_read: bool
    provider_called: bool
    direct_mutation_performed: bool
    silent_repair_performed: bool
    observed_at: str
    receipt_hash: str = ""

    def __post_init__(self) -> None:
        if self.integration_version != SECURITY_ABUSE_BOUNDARY_HARDENING_VERSION:
            raise SecurityAbuseBoundaryHardeningError("integration_version_invalid")
        if not isinstance(self.accepted, bool):
            raise SecurityAbuseBoundaryHardeningError("accepted_must_be_bool")
        object.__setattr__(self, "failures", _normalize_failures(self.failures))
        object.__setattr__(
            self,
            "control_results",
            _normalize_control_results(self.control_results),
        )
        for field_name in ("request_id", "task_id", "run_id", "observed_at"):
            _require_nonempty_string(getattr(self, field_name), field_name)
        for field_name in (
            "control_chain_hash",
            "request_fingerprint_hash",
            "wal_record_hash",
        ):
            _require_sha256(getattr(self, field_name), field_name)
        for field_name in (
            "credential_material_read",
            "direct_mutation_performed",
            "network_accessed",
            "provider_called",
            "silent_repair_performed",
            "subprocess_spawned",
        ):
            if not isinstance(getattr(self, field_name), bool):
                raise SecurityAbuseBoundaryHardeningError(field_name + "_must_be_bool")
        expected_acceptance = (
            not self.failures
            and all(control.accepted for control in self.control_results)
            and not self.network_accessed
            and not self.subprocess_spawned
            and not self.credential_material_read
            and not self.provider_called
            and not self.direct_mutation_performed
            and not self.silent_repair_performed
            and self.wal_record_hash != ZERO_HASH
        )
        if self.accepted != expected_acceptance:
            raise SecurityAbuseBoundaryHardeningError("accepted_must_match_controls")
        _install_or_verify_hash(
            self,
            "receipt_hash",
            compute_security_abuse_boundary_receipt_hash,
        )

    def deterministic_material(self) -> dict[str, object]:
        return {
            "accepted": self.accepted,
            "control_chain_hash": self.control_chain_hash,
            "control_results": tuple(item.as_dict() for item in self.control_results),
            "credential_material_read": self.credential_material_read,
            "direct_mutation_performed": self.direct_mutation_performed,
            "failures": self.failures,
            "integration_version": self.integration_version,
            "network_accessed": self.network_accessed,
            "observed_at": self.observed_at,
            "provider_called": self.provider_called,
            "request_fingerprint_hash": self.request_fingerprint_hash,
            "request_id": self.request_id,
            "run_id": self.run_id,
            "silent_repair_performed": self.silent_repair_performed,
            "subprocess_spawned": self.subprocess_spawned,
            "task_id": self.task_id,
            "wal_record_hash": self.wal_record_hash,
        }

    def as_dict(self) -> dict[str, object]:
        payload = self.deterministic_material()
        payload["receipt_hash"] = self.receipt_hash
        return _json_ready(payload)  # type: ignore[return-value]


class FileBackedSecurityAbuseBoundaryHardening:
    """File-backed digest-only security hardening evaluator."""

    def __init__(self, *, runtime_root: str | Path) -> None:
        self.runtime_root = _validate_runtime_root(Path(runtime_root))

    def evaluate(
        self,
        payload: Mapping[str, object],
        *,
        observed_at: str | None = None,
    ) -> SecurityAbuseBoundaryReceipt:
        if not isinstance(payload, Mapping):
            raise SecurityAbuseBoundaryHardeningError("payload_must_be_mapping")
        observed = _timestamp(observed_at)
        data = _json_ready(payload)
        if not isinstance(data, Mapping):
            raise SecurityAbuseBoundaryHardeningError("payload_must_be_mapping")
        request_id = _string_field(data, "request_id", "security-boundary-request")
        task_id = _string_field(data, "task_id", "security-boundary-task")
        run_id = _string_field(data, "run_id", "security-boundary-run")
        request_fingerprint_hash = _payload_fingerprint_hash(data)
        control_results = self._evaluate_controls(data)
        failures = tuple(
            failure
            for control in control_results
            if not control.accepted
            for failure in control.failures
        )
        control_chain_hash = _sha256_json(tuple(item.result_hash for item in control_results))
        wal_hash = self._append_wal(
            accepted=not failures,
            control_chain_hash=control_chain_hash,
            request_fingerprint_hash=request_fingerprint_hash,
            run_id=run_id,
            task_id=task_id,
            observed_at=observed,
        )
        receipt = SecurityAbuseBoundaryReceipt(
            integration_version=SECURITY_ABUSE_BOUNDARY_HARDENING_VERSION,
            accepted=not failures,
            failures=failures,
            request_id=request_id,
            task_id=task_id,
            run_id=run_id,
            control_results=control_results,
            request_fingerprint_hash=request_fingerprint_hash,
            control_chain_hash=control_chain_hash,
            wal_record_hash=wal_hash,
            network_accessed=False,
            subprocess_spawned=False,
            credential_material_read=False,
            provider_called=False,
            direct_mutation_performed=False,
            silent_repair_performed=False,
            observed_at=observed,
        )
        self._persist_receipt(receipt)
        return receipt

    def _evaluate_controls(
        self,
        data: Mapping[str, object],
    ) -> tuple[SecurityAbuseControlResult, ...]:
        failures_by_control = {
            "unsafe_subprocess": self._unsafe_subprocess_failures(data),
            "hidden_network": self._hidden_network_failures(data),
            "credential_access": self._credential_access_failures(data),
            "path_traversal": self._path_traversal_failures(data),
            "symlink_escape": self._symlink_escape_failures(data),
            "arbitrary_write": self._arbitrary_write_failures(data),
            "daemon_default": self._true_flag_failures(data, _DAEMON_FLAGS),
            "model_tool_direct_mutation": self._true_flag_failures(data, _DIRECT_MUTATION_FLAGS),
            "approval_replay_bypass": self._approval_replay_bypass_failures(data),
            "mutable_audit": self._mutable_audit_failures(data),
            "silent_repair": self._true_flag_failures(data, _SILENT_REPAIR_FLAGS),
            "uncontrolled_provider": self._provider_failures(data),
            "leakage": self._leakage_failures(data),
            "env_credential_capture": self._env_failures(data),
            "console_mutation_bypass": self._console_mutation_failures(data),
        }
        return tuple(
            SecurityAbuseControlResult(
                control_id=control_id,
                accepted=not failures_by_control[control_id],
                failures=failures_by_control[control_id],
                evidence_hash=_sha256_json(
                    {
                        "control_id": control_id,
                        "failures": failures_by_control[control_id],
                    }
                ),
            )
            for control_id in _CONTROL_IDS
        )

    def _unsafe_subprocess_failures(self, data: Mapping[str, object]) -> tuple[str, ...]:
        failures = list(self._true_flag_failures(data, _SUBPROCESS_TRUE_FLAGS))
        failures.extend(_present_key_failures(data, _SUBPROCESS_KEYS, "subprocess_material_forbidden"))
        return tuple(_dedupe(failures))

    def _hidden_network_failures(self, data: Mapping[str, object]) -> tuple[str, ...]:
        failures = list(self._true_flag_failures(data, _NETWORK_TRUE_FLAGS))
        failures.extend(_present_key_failures(data, _NETWORK_KEYS, "network_material_forbidden"))
        for dotted, value in _walk(data):
            if isinstance(value, str) and _URL_PATTERN.search(value):
                failures.append("network_url_forbidden:" + dotted)
        return tuple(_dedupe(failures))

    def _credential_access_failures(self, data: Mapping[str, object]) -> tuple[str, ...]:
        failures = list(self._true_flag_failures(data, _CREDENTIAL_TRUE_FLAGS))
        for dotted, value in _walk(data):
            key = dotted.rsplit(".", 1)[-1]
            if _digest_or_hash_key(key):
                continue
            if _SECRET_KEY_PATTERN.search(key) and _material_present(value):
                failures.append("credential_material_forbidden:" + dotted)
            if isinstance(value, str) and any(pattern.search(value) for pattern in _SECRET_VALUE_PATTERNS):
                failures.append("credential_value_forbidden:" + dotted)
        return tuple(_dedupe(failures))

    def _path_traversal_failures(self, data: Mapping[str, object]) -> tuple[str, ...]:
        failures: list[str] = []
        for dotted, value in _path_values(data):
            for text in _string_values(value):
                if "\\" in text:
                    failures.append("path_backslash_forbidden:" + dotted)
                    continue
                path = PurePosixPath(text)
                if path.is_absolute() or ".." in path.parts:
                    failures.append("path_traversal_forbidden:" + dotted)
                    continue
                if any(_SECRET_PATH_PATTERN.search(part) for part in path.parts):
                    failures.append("sensitive_path_forbidden:" + dotted)
        return tuple(_dedupe(failures))

    def _symlink_escape_failures(self, data: Mapping[str, object]) -> tuple[str, ...]:
        failures: list[str] = []
        root = self.runtime_root.resolve()
        for dotted, value in _path_values(data):
            for text in _string_values(value):
                if "\\" in text or PurePosixPath(text).is_absolute() or ".." in PurePosixPath(text).parts:
                    continue
                candidate = (root / PurePosixPath(text)).resolve(strict=False)
                if root != candidate and root not in candidate.parents:
                    failures.append("path_escapes_runtime_root:" + dotted)
                    continue
                current = root
                for part in PurePosixPath(text).parts:
                    current = current / part
                    if current.exists() and current.is_symlink():
                        failures.append("symlink_escape_forbidden:" + dotted)
                        break
        return tuple(_dedupe(failures))

    def _arbitrary_write_failures(self, data: Mapping[str, object]) -> tuple[str, ...]:
        failures = list(self._true_flag_failures(data, _ARBITRARY_WRITE_FLAGS))
        requested = tuple(_string_values(data.get("requested_write_relpaths", ())))
        allowed = frozenset(_string_values(data.get("allowed_write_relpaths", ())))
        if requested and not allowed:
            failures.append("allowed_write_relpaths_required")
        for relpath in requested:
            if relpath not in allowed:
                failures.append("write_relpath_not_allowlisted:" + relpath)
        return tuple(_dedupe(failures))

    def _approval_replay_bypass_failures(self, data: Mapping[str, object]) -> tuple[str, ...]:
        failures = list(self._true_flag_failures(data, _APPROVAL_BYPASS_FLAGS))
        if data.get("approval_required") is not True:
            failures.append("approval_required_true_missing")
        if data.get("replay_required") is not True:
            failures.append("replay_required_true_missing")
        for field_name in ("approval_receipt_hash", "replay_receipt_hash"):
            value = data.get(field_name)
            if not _valid_nonzero_sha256(value):
                failures.append(field_name + "_required")
        return tuple(_dedupe(failures))

    def _mutable_audit_failures(self, data: Mapping[str, object]) -> tuple[str, ...]:
        failures = list(self._true_flag_failures(data, _MUTABLE_AUDIT_FLAGS))
        if data.get("audit_append_only") is not True:
            failures.append("audit_append_only_true_missing")
        if data.get("audit_mode") != "append_only":
            failures.append("audit_mode_append_only_required")
        if not _valid_nonzero_sha256(data.get("audit_chain_hash")):
            failures.append("audit_chain_hash_required")
        return tuple(_dedupe(failures))

    def _provider_failures(self, data: Mapping[str, object]) -> tuple[str, ...]:
        failures = list(self._true_flag_failures(data, _PROVIDER_FLAGS))
        provider_id = data.get("provider_id")
        if isinstance(provider_id, str) and provider_id not in ("", "disabled", "none"):
            failures.append("provider_id_must_be_disabled")
        return tuple(_dedupe(failures))

    def _leakage_failures(self, data: Mapping[str, object]) -> tuple[str, ...]:
        failures = list(self._true_flag_failures(data, _LEAKAGE_FLAGS))
        for dotted, value in _walk(data):
            key = dotted.rsplit(".", 1)[-1]
            if _digest_or_hash_key(key):
                continue
            if any(fragment in key for fragment in _LEAKAGE_KEY_FRAGMENTS) and _material_present(value):
                failures.append("leakage_material_forbidden:" + dotted)
        return tuple(_dedupe(failures))

    def _env_failures(self, data: Mapping[str, object]) -> tuple[str, ...]:
        failures = list(self._true_flag_failures(data, _ENV_TRUE_FLAGS))
        failures.extend(_present_key_failures(data, _ENV_KEYS, "environment_capture_forbidden"))
        return tuple(_dedupe(failures))

    def _console_mutation_failures(self, data: Mapping[str, object]) -> tuple[str, ...]:
        failures = list(self._true_flag_failures(data, _CONSOLE_MUTATION_FLAGS))
        route = data.get("console_mutation_route")
        if route not in (None, "", _CONSOLE_ROUTE):
            failures.append("console_mutation_route_invalid")
        if not _valid_nonzero_sha256(data.get("operator_console_snapshot_hash")):
            failures.append("operator_console_snapshot_hash_required")
        return tuple(_dedupe(failures))

    def _true_flag_failures(
        self,
        data: Mapping[str, object],
        names: frozenset[str],
    ) -> tuple[str, ...]:
        failures = []
        for dotted, value in _walk(data):
            key = dotted.rsplit(".", 1)[-1]
            if key in names and value is True:
                failures.append(key + "_must_be_false")
        return tuple(_dedupe(failures))

    def _append_wal(
        self,
        *,
        accepted: bool,
        control_chain_hash: str,
        request_fingerprint_hash: str,
        run_id: str,
        task_id: str,
        observed_at: str,
    ) -> str:
        wal_path = self._resolve_relpath(_WAL_RELPATH, "wal_relpath")
        wal_path.parent.mkdir(parents=True, exist_ok=True)
        material = {
            "accepted": accepted,
            "control_chain_hash": control_chain_hash,
            "request_fingerprint_hash": request_fingerprint_hash,
        }
        return FileBackedRealWalStorage(wal_path).append(
            record_type="SYSTEM_ACCEPTANCE_EVENT",
            task_id=task_id,
            run_id=run_id,
            payload_hash=_sha256_json(material),
            digest_bindings={
                "control_chain_hash": control_chain_hash,
                "request_fingerprint_hash": request_fingerprint_hash,
            },
            created_at=observed_at,
        ).record_hash

    def _persist_receipt(self, receipt: SecurityAbuseBoundaryReceipt) -> None:
        relpath = _RECEIPT_DIR_RELPATH + "/" + receipt.receipt_hash.removeprefix("sha256:") + ".json"
        path = self._resolve_relpath(relpath, "receipt_relpath")
        if path.exists():
            raise SecurityAbuseBoundaryHardeningError("receipt_already_exists")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(_canonical_json(receipt.as_dict()) + "\n", encoding="utf-8")

    def _resolve_relpath(self, relpath: str, field_name: str) -> Path:
        _validate_relpath_text(relpath, field_name)
        root = self.runtime_root.resolve()
        candidate = (root / PurePosixPath(relpath)).resolve(strict=False)
        if root != candidate and root not in candidate.parents:
            raise SecurityAbuseBoundaryHardeningError(field_name + "_escapes_runtime_root")
        return candidate


def compute_security_abuse_control_result_hash(
    result: SecurityAbuseControlResult | Mapping[str, object],
) -> str:
    payload = result.as_dict() if isinstance(result, SecurityAbuseControlResult) else dict(result)
    payload.pop("result_hash", None)
    return _sha256_json(payload)


def compute_security_abuse_boundary_receipt_hash(
    receipt: SecurityAbuseBoundaryReceipt | Mapping[str, object],
) -> str:
    payload = (
        receipt.deterministic_material()
        if isinstance(receipt, SecurityAbuseBoundaryReceipt)
        else dict(receipt)
    )
    payload.pop("receipt_hash", None)
    return _sha256_json(payload)


def _normalize_control_results(
    value: Sequence[SecurityAbuseControlResult],
) -> tuple[SecurityAbuseControlResult, ...]:
    if not isinstance(value, tuple):
        value = tuple(value)
    if any(not isinstance(item, SecurityAbuseControlResult) for item in value):
        raise SecurityAbuseBoundaryHardeningError("control_results_must_be_control_results")
    if tuple(item.control_id for item in value) != _CONTROL_IDS:
        raise SecurityAbuseBoundaryHardeningError("control_results_must_be_complete_and_ordered")
    return value


def _present_key_failures(
    data: Mapping[str, object],
    names: frozenset[str],
    code: str,
) -> tuple[str, ...]:
    failures = []
    for dotted, value in _walk(data):
        key = dotted.rsplit(".", 1)[-1]
        if key in names and _material_present(value):
            failures.append(code + ":" + dotted)
    return tuple(_dedupe(failures))


def _path_values(data: Mapping[str, object]) -> Iterable[tuple[str, object]]:
    for dotted, value in _walk(data):
        key = dotted.rsplit(".", 1)[-1]
        if (
            key in _PATH_KEYS
            or key.endswith("_path")
            or key.endswith("_paths")
            or key.endswith("_relpath")
            or key.endswith("_relpaths")
        ):
            yield dotted, value


def _string_values(value: object) -> tuple[str, ...]:
    if isinstance(value, str):
        return (value,) if value else ()
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        values: list[str] = []
        for item in value:
            values.extend(_string_values(item))
        return tuple(values)
    return ()


def _walk(value: object, prefix: str = "") -> Iterable[tuple[str, object]]:
    if isinstance(value, Mapping):
        for key, item in value.items():
            key_text = str(key)
            dotted = key_text if not prefix else prefix + "." + key_text
            yield dotted, item
            yield from _walk(item, dotted)
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for index, item in enumerate(value):
            dotted = prefix + "." + str(index) if prefix else str(index)
            yield dotted, item
            yield from _walk(item, dotted)


def _payload_fingerprint_hash(data: Mapping[str, object]) -> str:
    return _sha256_json(_fingerprint_value(data))


def _fingerprint_value(value: object, key_hint: str = "") -> object:
    if isinstance(value, Mapping):
        return {
            str(key): _fingerprint_value(item, str(key))
            for key, item in sorted(value.items(), key=lambda entry: str(entry[0]))
        }
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_fingerprint_value(item, key_hint) for item in value]
    if isinstance(value, str):
        if _SECRET_KEY_PATTERN.search(key_hint) or any(pattern.search(value) for pattern in _SECRET_VALUE_PATTERNS):
            return {"blocked_sensitive_field": key_hint}
        if _URL_PATTERN.search(value):
            return {"blocked_external_locator": key_hint}
        return {"sha256": _sha256_text(value)}
    if isinstance(value, (bool, int, float)) or value is None:
        return value
    return str(type(value).__name__)


def _material_present(value: object) -> bool:
    if value in (None, False, "", (), [], {}):
        return False
    return True


def _digest_or_hash_key(key: str) -> bool:
    return key.endswith("_hash") or key.endswith("_digest")


def _valid_nonzero_sha256(value: object) -> bool:
    return isinstance(value, str) and value != ZERO_HASH and _SHA256_PATTERN.fullmatch(value) is not None


def _string_field(data: Mapping[str, object], field_name: str, fallback: str) -> str:
    value = data.get(field_name, fallback)
    if not isinstance(value, str) or not value:
        raise SecurityAbuseBoundaryHardeningError(field_name + "_must_be_string")
    return value


def _validate_runtime_root(path: Path) -> Path:
    if path.exists() and path.is_symlink():
        raise SecurityAbuseBoundaryHardeningError("runtime_root_is_symlink")
    if path.exists() and not path.is_dir():
        raise SecurityAbuseBoundaryHardeningError("runtime_root_must_be_directory")
    for part in path.parts:
        if _SECRET_PATH_PATTERN.search(part):
            raise SecurityAbuseBoundaryHardeningError("runtime_root_sensitive_path")
    return path


def _validate_relpath_text(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value:
        raise SecurityAbuseBoundaryHardeningError(field_name + "_required")
    if value.startswith("/") or "\\" in value:
        raise SecurityAbuseBoundaryHardeningError(field_name + "_must_be_posix_relative")
    path = PurePosixPath(value)
    if any(part in ("", ".", "..") for part in path.parts):
        raise SecurityAbuseBoundaryHardeningError(field_name + "_invalid")
    return value


def _require_nonempty_string(value: object, field_name: str) -> None:
    if not isinstance(value, str) or not value:
        raise SecurityAbuseBoundaryHardeningError(field_name + "_required")


def _require_sha256(value: object, field_name: str) -> None:
    if not isinstance(value, str) or _SHA256_PATTERN.fullmatch(value) is None:
        raise SecurityAbuseBoundaryHardeningError(field_name + "_must_be_sha256")


def _normalize_failures(value: object) -> tuple[str, ...]:
    if not isinstance(value, (tuple, list)):
        raise SecurityAbuseBoundaryHardeningError("failures_must_be_sequence")
    failures = tuple(str(item) for item in value if str(item))
    for failure in failures:
        _require_nonempty_string(failure, "failure")
    return tuple(_dedupe(failures))


def _install_or_verify_hash(instance: object, field_name: str, computer) -> None:
    current = getattr(instance, field_name)
    if current:
        _require_sha256(current, field_name)
    expected = computer(instance)
    if current and current != expected:
        raise SecurityAbuseBoundaryHardeningError(field_name + "_mismatch")
    object.__setattr__(instance, field_name, expected)


def _timestamp(value: str | None) -> str:
    if value is None:
        return datetime.now(timezone.utc).isoformat()
    _require_nonempty_string(value, "timestamp")
    return value


def _sha256_text(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def _sha256_json(value: object) -> str:
    return "sha256:" + hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _canonical_json(value: object) -> str:
    return json.dumps(
        _json_ready(value),
        sort_keys=True,
        separators=(",", ":"),
    )


def _json_ready(value: object) -> object:
    if isinstance(value, Mapping):
        return {str(key): _json_ready(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_json_ready(item) for item in value]
    if isinstance(value, list):
        return [_json_ready(item) for item in value]
    if hasattr(value, "as_dict"):
        return _json_ready(value.as_dict())  # type: ignore[no-any-return]
    return value


def _dedupe(values: Iterable[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(values))
