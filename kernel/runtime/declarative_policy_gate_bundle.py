"""Declarative Policy Gate Bundle V1.

Evaluates local JSON/YAML policy gate bundles against evidence payloads and
emits deterministic decision receipts. The evaluator is intentionally small:
no OPA dependency, no network calls, no credential reads, and no policy code
execution.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import importlib
import json
from pathlib import Path, PurePosixPath
import re
from typing import Mapping, Sequence

from kernel.stores.real_wal_storage import FileBackedRealWalStorage

__all__ = [
    "DECLARATIVE_POLICY_GATE_BUNDLE_VERSION",
    "ZERO_HASH",
    "DeclarativePolicyGateBundleError",
    "DeclarativePolicyDecisionReceipt",
    "FileBackedDeclarativePolicyGateBundle",
    "compute_declarative_policy_bundle_digest",
    "compute_declarative_policy_decision_receipt_hash",
    "load_declarative_policy_bundle",
]

DECLARATIVE_POLICY_GATE_BUNDLE_VERSION = "declarative_policy_gate_bundle_v1"
ZERO_HASH = "sha256:" + ("0" * 64)

_TASK_ID = "task-532-declarative-policy-gate-bundle"
_WAL_RELPATH = "declarative-policy-gate-bundle/policy.real-wal.jsonl"
_REPORT_RELPATH = "declarative-policy-gate-bundle/reports/policy-decision-report.json"
_RECEIPT_DIR_RELPATH = "declarative-policy-gate-bundle/receipts"
_SHA256_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")
_PATH_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*$")
_OPERATORS = frozenset(
    {
        "all_present",
        "equals",
        "exists",
        "falsy",
        "matches",
        "not_equals",
        "sha256",
        "status_in",
        "truthy",
    }
)


class DeclarativePolicyGateBundleError(ValueError):
    """Raised when a policy bundle cannot be loaded or evaluated."""


@dataclass(frozen=True)
class DeclarativePolicyDecisionReceipt:
    decision_version: str
    allowed: bool
    decision: str
    failures: tuple[str, ...]
    failed_rule_ids: tuple[str, ...]
    policy_bundle_id: str
    policy_digest: str
    input_evidence_digest: str
    wal_record_hash: str
    observed_at: str
    receipt_hash: str = ""

    def __post_init__(self) -> None:
        if self.decision_version != DECLARATIVE_POLICY_GATE_BUNDLE_VERSION:
            raise DeclarativePolicyGateBundleError("decision_version_invalid")
        if not isinstance(self.allowed, bool):
            raise DeclarativePolicyGateBundleError("allowed_must_be_bool")
        if self.decision not in {"allow", "deny"}:
            raise DeclarativePolicyGateBundleError("decision_invalid")
        object.__setattr__(self, "failures", _normalize_strings(self.failures, "failure"))
        object.__setattr__(
            self,
            "failed_rule_ids",
            _normalize_strings(self.failed_rule_ids, "failed_rule_id"),
        )
        _require_nonempty_string(self.policy_bundle_id, "policy_bundle_id")
        _require_sha256(self.policy_digest, "policy_digest")
        _require_sha256(self.input_evidence_digest, "input_evidence_digest")
        _require_sha256(self.wal_record_hash, "wal_record_hash")
        _require_nonempty_string(self.observed_at, "observed_at")
        expected_allowed = (
            self.decision == "allow"
            and not self.failures
            and not self.failed_rule_ids
            and self.wal_record_hash != ZERO_HASH
        )
        if self.allowed != expected_allowed:
            raise DeclarativePolicyGateBundleError(
                "allowed_must_match_policy_evidence"
            )
        _install_or_verify_hash(
            self,
            "receipt_hash",
            compute_declarative_policy_decision_receipt_hash,
        )

    def deterministic_material(self) -> dict[str, object]:
        return {
            "allowed": self.allowed,
            "decision": self.decision,
            "decision_version": self.decision_version,
            "failed_rule_ids": self.failed_rule_ids,
            "failures": self.failures,
            "input_evidence_digest": self.input_evidence_digest,
            "observed_at": self.observed_at,
            "policy_bundle_id": self.policy_bundle_id,
            "policy_digest": self.policy_digest,
            "wal_record_hash": self.wal_record_hash,
        }

    def as_dict(self) -> dict[str, object]:
        payload = self.deterministic_material()
        payload["receipt_hash"] = self.receipt_hash
        return _json_ready(payload)  # type: ignore[return-value]


class FileBackedDeclarativePolicyGateBundle:
    """File-backed evaluator for local declarative gate bundles."""

    def __init__(self, *, runtime_root: str | Path) -> None:
        self.runtime_root = _validate_runtime_root(Path(runtime_root))

    def evaluate(
        self,
        policy_bundle: Mapping[str, object] | str | Path,
        evidence_payload: Mapping[str, object],
        *,
        expected_input_evidence_digest: str | None = None,
        observed_at: str | None = None,
    ) -> DeclarativePolicyDecisionReceipt:
        observed = _timestamp(observed_at)
        if not isinstance(evidence_payload, Mapping):
            raise DeclarativePolicyGateBundleError(
                "evidence_payload_must_be_mapping"
            )
        bundle = (
            load_declarative_policy_bundle(policy_bundle)
            if isinstance(policy_bundle, (str, Path))
            else _json_ready(policy_bundle)
        )
        if not isinstance(bundle, Mapping):
            raise DeclarativePolicyGateBundleError("policy_bundle_must_be_mapping")
        evidence = _json_ready(evidence_payload)
        if not isinstance(evidence, Mapping):
            raise DeclarativePolicyGateBundleError(
                "evidence_payload_must_be_mapping"
            )
        policy_digest = compute_declarative_policy_bundle_digest(bundle)
        input_digest = _sha256_json(evidence)

        failures = list(_schema_failures(bundle))
        failed_rule_ids: list[str] = []
        if bundle.get("policy_digest") not in (None, policy_digest):
            failures.append("policy_digest_mismatch")
        expected_digest = expected_input_evidence_digest or bundle.get(
            "expected_input_evidence_digest"
        )
        if expected_digest is not None:
            if not isinstance(expected_digest, str) or not _SHA256_PATTERN.match(expected_digest):
                failures.append("expected_input_evidence_digest_invalid")
            elif expected_digest != input_digest:
                failures.append("input_evidence_digest_mismatch")

        if not failures:
            rule_results = _evaluate_rules(bundle, evidence)
            failures.extend(rule_results[0])
            failed_rule_ids.extend(rule_results[1])

        decision = "allow" if not failures and not failed_rule_ids else "deny"
        wal_record_hash = self._append_wal(
            decision=decision,
            policy_bundle_id=_string_field(bundle, "bundle_id", "unknown-policy-bundle"),
            policy_digest=policy_digest,
            input_evidence_digest=input_digest,
            failed_rule_ids=tuple(_dedupe(failed_rule_ids)),
            observed_at=observed,
        )
        receipt = DeclarativePolicyDecisionReceipt(
            decision_version=DECLARATIVE_POLICY_GATE_BUNDLE_VERSION,
            allowed=decision == "allow",
            decision=decision,
            failures=_dedupe(failures),
            failed_rule_ids=_dedupe(failed_rule_ids),
            policy_bundle_id=_string_field(bundle, "bundle_id", "unknown-policy-bundle"),
            policy_digest=policy_digest,
            input_evidence_digest=input_digest,
            wal_record_hash=wal_record_hash,
            observed_at=observed,
        )
        self._persist_decision(receipt)
        return receipt

    def _append_wal(
        self,
        *,
        decision: str,
        policy_bundle_id: str,
        policy_digest: str,
        input_evidence_digest: str,
        failed_rule_ids: tuple[str, ...],
        observed_at: str,
    ) -> str:
        wal_path = self._resolve_relpath(_WAL_RELPATH, "wal_relpath")
        wal_path.parent.mkdir(parents=True, exist_ok=True)
        failed_rule_bundle_hash = _sha256_json(failed_rule_ids)
        material = {
            "decision": decision,
            "failed_rule_bundle_hash": failed_rule_bundle_hash,
            "input_evidence_digest": input_evidence_digest,
            "policy_digest": policy_digest,
        }
        return FileBackedRealWalStorage(wal_path).append(
            record_type="SYSTEM_ACCEPTANCE_EVENT",
            task_id=_TASK_ID,
            run_id=policy_bundle_id,
            payload_hash=_sha256_json(material),
            digest_bindings={
                "failed_rule_bundle_hash": failed_rule_bundle_hash,
                "input_evidence_digest": input_evidence_digest,
                "policy_digest": policy_digest,
            },
            created_at=observed_at,
        ).record_hash

    def _persist_decision(self, receipt: DeclarativePolicyDecisionReceipt) -> None:
        report = {
            "allowed": receipt.allowed,
            "decision": receipt.decision,
            "failed_rule_ids": receipt.failed_rule_ids,
            "failures": receipt.failures,
            "input_evidence_digest": receipt.input_evidence_digest,
            "policy_bundle_id": receipt.policy_bundle_id,
            "policy_digest": receipt.policy_digest,
            "receipt_hash": receipt.receipt_hash,
            "wal_record_hash": receipt.wal_record_hash,
        }
        self._write_new_json(_REPORT_RELPATH, report)
        receipt_relpath = (
            _RECEIPT_DIR_RELPATH
            + "/"
            + receipt.receipt_hash.removeprefix("sha256:")
            + ".json"
        )
        self._write_new_json(receipt_relpath, receipt.as_dict())

    def _write_new_json(self, relpath: str, payload: object) -> None:
        path = self._resolve_relpath(relpath, "output_relpath")
        if path.exists():
            raise DeclarativePolicyGateBundleError("output_already_exists")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                _json_ready(payload),
                sort_keys=True,
                indent=2,
                ensure_ascii=True,
            )
            + "\n",
            encoding="utf-8",
        )

    def _resolve_relpath(self, relpath: str, field_name: str) -> Path:
        if not isinstance(relpath, str) or not relpath:
            raise DeclarativePolicyGateBundleError(
                field_name + "_must_be_nonempty_string"
            )
        if "\\" in relpath:
            raise DeclarativePolicyGateBundleError(
                field_name + "_backslash_forbidden"
            )
        pure = PurePosixPath(relpath)
        if pure.is_absolute() or ".." in pure.parts:
            raise DeclarativePolicyGateBundleError(
                field_name + "_must_stay_under_runtime_root"
            )
        path = (self.runtime_root / pure).resolve(strict=False)
        root = self.runtime_root.resolve()
        if path != root and root not in path.parents:
            raise DeclarativePolicyGateBundleError(
                field_name + "_escapes_runtime_root"
            )
        return path


def load_declarative_policy_bundle(path: str | Path) -> Mapping[str, object]:
    policy_path = Path(path)
    if not policy_path.is_file():
        raise DeclarativePolicyGateBundleError("policy_bundle_file_missing")
    text = policy_path.read_text(encoding="utf-8")
    suffix = policy_path.suffix.lower()
    if suffix == ".json":
        payload = json.loads(text)
    elif suffix in {".yaml", ".yml"}:
        try:
            yaml = importlib.import_module("yaml")
        except ModuleNotFoundError as exc:
            raise DeclarativePolicyGateBundleError(
                "yaml_loader_unavailable"
            ) from exc
        payload = yaml.safe_load(text)
    else:
        raise DeclarativePolicyGateBundleError("policy_bundle_extension_invalid")
    if not isinstance(payload, Mapping):
        raise DeclarativePolicyGateBundleError("policy_bundle_must_be_mapping")
    return _json_ready(payload)  # type: ignore[return-value]


def compute_declarative_policy_bundle_digest(bundle: Mapping[str, object]) -> str:
    if not isinstance(bundle, Mapping):
        raise DeclarativePolicyGateBundleError("policy_bundle_must_be_mapping")
    material = {
        key: value
        for key, value in bundle.items()
        if key != "policy_digest"
    }
    return _sha256_json(material)


def compute_declarative_policy_decision_receipt_hash(
    receipt: DeclarativePolicyDecisionReceipt,
) -> str:
    return _sha256_json(receipt.deterministic_material())


def _schema_failures(bundle: Mapping[str, object]) -> tuple[str, ...]:
    failures: list[str] = []
    if bundle.get("policy_version") != DECLARATIVE_POLICY_GATE_BUNDLE_VERSION:
        failures.append("unknown_policy_version")
    if not isinstance(bundle.get("bundle_id"), str) or not bundle.get("bundle_id"):
        failures.append("bundle_id_required")
    required_rule_ids = bundle.get("required_rule_ids")
    rules = bundle.get("rules")
    if not isinstance(required_rule_ids, Sequence) or isinstance(required_rule_ids, (str, bytes)):
        failures.append("required_rule_ids_required")
        required_ids: tuple[str, ...] = ()
    else:
        required_ids = tuple(str(rule_id) for rule_id in required_rule_ids)
        if not required_ids:
            failures.append("required_rule_ids_must_not_be_empty")
    if not isinstance(rules, Sequence) or isinstance(rules, (str, bytes)):
        failures.append("rules_required")
        rule_ids: tuple[str, ...] = ()
    else:
        seen: set[str] = set()
        rule_ids_list: list[str] = []
        for rule in rules:
            if not isinstance(rule, Mapping):
                failures.append("malformed_rule:unknown")
                continue
            rule_id = rule.get("rule_id")
            if not isinstance(rule_id, str) or not rule_id:
                failures.append("malformed_rule:missing_rule_id")
                continue
            if rule_id in seen:
                failures.append("contradiction_duplicate_rule_id:" + rule_id)
            seen.add(rule_id)
            rule_ids_list.append(rule_id)
            failures.extend(_rule_schema_failures(rule))
        rule_ids = tuple(rule_ids_list)
    for required_id in required_ids:
        if required_id not in rule_ids:
            failures.append("missing_required_rule:" + required_id)
    return tuple(_dedupe(failures))


def _rule_schema_failures(rule: Mapping[str, object]) -> tuple[str, ...]:
    rule_id = str(rule.get("rule_id", "unknown"))
    failures: list[str] = []
    operator = rule.get("operator")
    if operator not in _OPERATORS:
        failures.append("malformed_rule:" + rule_id)
    if operator == "all_present":
        paths = rule.get("paths")
        if not isinstance(paths, Sequence) or isinstance(paths, (str, bytes)) or not paths:
            failures.append("malformed_rule:" + rule_id)
        else:
            for path in paths:
                if not isinstance(path, str) or not _PATH_PATTERN.match(path):
                    failures.append("malformed_rule:" + rule_id)
    else:
        path = rule.get("path")
        if not isinstance(path, str) or not _PATH_PATTERN.match(path):
            failures.append("malformed_rule:" + rule_id)
    if operator in {"equals", "not_equals"} and "value" not in rule:
        failures.append("malformed_rule:" + rule_id)
    if operator == "status_in":
        values = rule.get("values")
        if not isinstance(values, Sequence) or isinstance(values, (str, bytes)) or not values:
            failures.append("malformed_rule:" + rule_id)
    if operator == "matches" and not isinstance(rule.get("pattern"), str):
        failures.append("malformed_rule:" + rule_id)
    return tuple(_dedupe(failures))


def _evaluate_rules(
    bundle: Mapping[str, object],
    evidence: Mapping[str, object],
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    failures: list[str] = []
    failed_rule_ids: list[str] = []
    rules = bundle.get("rules", ())
    for rule in rules:  # type: ignore[assignment]
        if not isinstance(rule, Mapping):
            continue
        rule_id = str(rule.get("rule_id"))
        if not _evaluate_rule(rule, evidence):
            failed_rule_ids.append(rule_id)
            failures.append("rule_failed:" + rule_id)
    return tuple(_dedupe(failures)), tuple(_dedupe(failed_rule_ids))


def _evaluate_rule(rule: Mapping[str, object], evidence: Mapping[str, object]) -> bool:
    operator = rule.get("operator")
    if operator == "all_present":
        return all(
            _lookup_path(evidence, str(path))[0]
            for path in rule.get("paths", ())  # type: ignore[union-attr]
        )
    exists, value = _lookup_path(evidence, str(rule.get("path", "")))
    if operator == "exists":
        return exists
    if operator == "equals":
        return exists and value == rule.get("value")
    if operator == "not_equals":
        return exists and value != rule.get("value")
    if operator == "truthy":
        return value is True
    if operator == "falsy":
        return value is False
    if operator == "sha256":
        return isinstance(value, str) and _SHA256_PATTERN.match(value) is not None
    if operator == "status_in":
        values = rule.get("values", ())
        allowed = {
            str(item).strip().lower()
            for item in values  # type: ignore[union-attr]
        }
        return isinstance(value, str) and value.strip().lower() in allowed
    if operator == "matches":
        pattern = str(rule.get("pattern", ""))
        return isinstance(value, str) and re.match(pattern, value) is not None
    return False


def _lookup_path(evidence: Mapping[str, object], path: str) -> tuple[bool, object]:
    current: object = evidence
    for part in path.split("."):
        if not isinstance(current, Mapping) or part not in current:
            return False, None
        current = current[part]
    return True, current


def _timestamp(value: str | None) -> str:
    if value is None:
        return datetime.now(timezone.utc).isoformat()
    _require_nonempty_string(value, "observed_at")
    return value


def _validate_runtime_root(path: Path) -> Path:
    resolved = path.resolve(strict=False)
    resolved.mkdir(parents=True, exist_ok=True)
    return resolved


def _json_ready(value: object) -> object:
    try:
        return json.loads(
            json.dumps(
                value,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=True,
                allow_nan=False,
            )
        )
    except (TypeError, ValueError) as exc:
        raise DeclarativePolicyGateBundleError(
            "value_must_be_json_serializable"
        ) from exc


def _sha256_json(value: object) -> str:
    encoded = json.dumps(
        _json_ready(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def _require_nonempty_string(value: object, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise DeclarativePolicyGateBundleError(
            field_name + "_must_be_nonempty_string"
        )


def _require_sha256(value: object, field_name: str) -> None:
    if not isinstance(value, str) or not _SHA256_PATTERN.match(value):
        raise DeclarativePolicyGateBundleError(field_name + "_must_be_sha256")


def _string_field(data: Mapping[str, object], field_name: str, default: str) -> str:
    value = data.get(field_name, default)
    if not isinstance(value, str) or not value.strip():
        return default
    return value


def _normalize_strings(values: Sequence[str], field_name: str) -> tuple[str, ...]:
    if not isinstance(values, Sequence) or isinstance(values, (str, bytes)):
        raise DeclarativePolicyGateBundleError(field_name + "s_must_be_sequence")
    normalized = tuple(str(value) for value in values)
    for value in normalized:
        _require_nonempty_string(value, field_name)
    return tuple(_dedupe(normalized))


def _install_or_verify_hash(instance: object, field_name: str, compute) -> None:
    current = getattr(instance, field_name)
    expected = compute(instance)
    if current in ("", None):
        object.__setattr__(instance, field_name, expected)
        return
    if current != expected:
        raise DeclarativePolicyGateBundleError(field_name + "_mismatch")


def _dedupe(values: Sequence[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    output: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            output.append(value)
    return tuple(output)
