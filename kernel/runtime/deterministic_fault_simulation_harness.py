"""Deterministic Fault Simulation Harness V1.

Runs local, seeded fault simulations against file-backed runtime surfaces. The
harness writes only under its runtime root, emits deterministic reports and
scenario receipts, and fails closed when a simulated recovery is unsafe.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
from typing import Mapping, Sequence

from kernel.stores.real_wal_storage import FileBackedRealWalStorage

__all__ = [
    "DETERMINISTIC_FAULT_SIMULATION_VERSION",
    "ZERO_HASH",
    "DeterministicFaultSimulationError",
    "FaultSimulationReport",
    "FaultSimulationResult",
    "FaultSimulationScenarioReceipt",
    "FileBackedDeterministicFaultSimulationHarness",
    "compute_fault_simulation_report_hash",
    "compute_fault_simulation_result_hash",
    "compute_fault_simulation_scenario_digest",
    "compute_fault_simulation_scenario_receipt_hash",
]

DETERMINISTIC_FAULT_SIMULATION_VERSION = "deterministic_fault_simulation_harness_v1"
ZERO_HASH = "sha256:" + ("0" * 64)

_TASK_ID = "task-533-deterministic-fault-simulation-harness"
_WAL_RELPATH = "deterministic-fault-simulation/simulation.real-wal.jsonl"
_REPORT_RELPATH = "deterministic-fault-simulation/reports/fault-simulation-report.json"
_SCENARIO_RECEIPT_DIR_RELPATH = "deterministic-fault-simulation/scenario-receipts"
_REPORT_RECEIPT_DIR_RELPATH = "deterministic-fault-simulation/report-receipts"
_WORKSPACE_RELPATH = "deterministic-fault-simulation/workspace"
_SHA256_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")
_FAULT_TYPES = frozenset(
    {
        "corrupted_jsonl",
        "corrupted_recovery_source",
        "crash_before_write",
        "expired_approval",
        "hash_mismatch",
        "missing_approval",
        "missing_artifact",
        "partial_write",
        "replay_missing_record",
        "reused_capability",
        "revoked_approval",
        "revoked_capability",
        "stale_queue_lease",
        "watchdog_timeout",
    }
)
_RECOVERY_ACTIONS = {
    "corrupted_jsonl": "reject_corrupted_wal",
    "corrupted_recovery_source": "quarantine_recovery_source",
    "crash_before_write": "block_before_write",
    "expired_approval": "deny_expired_approval",
    "hash_mismatch": "reject_hash_mismatch",
    "missing_approval": "deny_missing_approval",
    "missing_artifact": "reject_missing_artifact",
    "partial_write": "recover_from_last_complete_record",
    "replay_missing_record": "reject_replay_gap",
    "reused_capability": "deny_reused_capability",
    "revoked_approval": "deny_revoked_approval",
    "revoked_capability": "deny_revoked_capability",
    "stale_queue_lease": "reclaim_stale_lease",
    "watchdog_timeout": "quarantine_timed_out_run",
}


class DeterministicFaultSimulationError(ValueError):
    """Raised when a fault simulation scenario is malformed."""


@dataclass(frozen=True)
class FaultSimulationResult:
    fault_id: str
    fault_type: str
    target: str
    detected: bool
    recovery_action: str
    safe_recovery: bool
    quarantine_required: bool
    output_digest: str
    result_hash: str = ""

    def __post_init__(self) -> None:
        _require_nonempty_string(self.fault_id, "fault_id")
        if self.fault_type not in _FAULT_TYPES:
            raise DeterministicFaultSimulationError("fault_type_invalid")
        _require_nonempty_string(self.target, "target")
        if not isinstance(self.detected, bool):
            raise DeterministicFaultSimulationError("detected_must_be_bool")
        _require_nonempty_string(self.recovery_action, "recovery_action")
        if not isinstance(self.safe_recovery, bool):
            raise DeterministicFaultSimulationError("safe_recovery_must_be_bool")
        if not isinstance(self.quarantine_required, bool):
            raise DeterministicFaultSimulationError(
                "quarantine_required_must_be_bool"
            )
        _require_sha256(self.output_digest, "output_digest")
        if self.safe_recovery and not self.detected:
            raise DeterministicFaultSimulationError(
                "safe_recovery_requires_detection"
            )
        _install_or_verify_hash(
            self,
            "result_hash",
            compute_fault_simulation_result_hash,
        )

    def deterministic_material(self) -> dict[str, object]:
        return {
            "detected": self.detected,
            "fault_id": self.fault_id,
            "fault_type": self.fault_type,
            "output_digest": self.output_digest,
            "quarantine_required": self.quarantine_required,
            "recovery_action": self.recovery_action,
            "safe_recovery": self.safe_recovery,
            "target": self.target,
        }

    def as_dict(self) -> dict[str, object]:
        payload = self.deterministic_material()
        payload["result_hash"] = self.result_hash
        return _json_ready(payload)  # type: ignore[return-value]


@dataclass(frozen=True)
class FaultSimulationScenarioReceipt:
    scenario_version: str
    scenario_id: str
    seed: str
    scenario_digest: str
    fault_count: int
    observed_at: str
    receipt_hash: str = ""

    def __post_init__(self) -> None:
        if self.scenario_version != DETERMINISTIC_FAULT_SIMULATION_VERSION:
            raise DeterministicFaultSimulationError("scenario_version_invalid")
        _require_nonempty_string(self.scenario_id, "scenario_id")
        _require_nonempty_string(self.seed, "seed")
        _require_sha256(self.scenario_digest, "scenario_digest")
        if not isinstance(self.fault_count, int) or isinstance(self.fault_count, bool):
            raise DeterministicFaultSimulationError("fault_count_must_be_int")
        if self.fault_count <= 0:
            raise DeterministicFaultSimulationError("fault_count_must_be_positive")
        _require_nonempty_string(self.observed_at, "observed_at")
        _install_or_verify_hash(
            self,
            "receipt_hash",
            compute_fault_simulation_scenario_receipt_hash,
        )

    def deterministic_material(self) -> dict[str, object]:
        return {
            "fault_count": self.fault_count,
            "observed_at": self.observed_at,
            "scenario_digest": self.scenario_digest,
            "scenario_id": self.scenario_id,
            "scenario_version": self.scenario_version,
            "seed": self.seed,
        }

    def as_dict(self) -> dict[str, object]:
        payload = self.deterministic_material()
        payload["receipt_hash"] = self.receipt_hash
        return _json_ready(payload)  # type: ignore[return-value]


@dataclass(frozen=True)
class FaultSimulationReport:
    simulation_version: str
    accepted: bool
    failures: tuple[str, ...]
    scenario_receipt_hash: str
    scenario_digest: str
    result_hashes: tuple[str, ...]
    fault_results: tuple[FaultSimulationResult, ...]
    wal_record_hash: str
    observed_at: str
    report_hash: str = ""

    def __post_init__(self) -> None:
        if self.simulation_version != DETERMINISTIC_FAULT_SIMULATION_VERSION:
            raise DeterministicFaultSimulationError("simulation_version_invalid")
        if not isinstance(self.accepted, bool):
            raise DeterministicFaultSimulationError("accepted_must_be_bool")
        object.__setattr__(self, "failures", _normalize_strings(self.failures, "failure"))
        _require_sha256(self.scenario_receipt_hash, "scenario_receipt_hash")
        _require_sha256(self.scenario_digest, "scenario_digest")
        object.__setattr__(
            self,
            "fault_results",
            _normalize_results(self.fault_results),
        )
        object.__setattr__(
            self,
            "result_hashes",
            _normalize_hashes(self.result_hashes, "result_hash"),
        )
        if self.result_hashes != tuple(result.result_hash for result in self.fault_results):
            raise DeterministicFaultSimulationError("result_hashes_mismatch")
        _require_sha256(self.wal_record_hash, "wal_record_hash")
        _require_nonempty_string(self.observed_at, "observed_at")
        expected_acceptance = (
            not self.failures
            and bool(self.fault_results)
            and all(result.detected and result.safe_recovery for result in self.fault_results)
            and self.wal_record_hash != ZERO_HASH
        )
        if self.accepted != expected_acceptance:
            raise DeterministicFaultSimulationError(
                "accepted_must_match_fault_results"
            )
        _install_or_verify_hash(self, "report_hash", compute_fault_simulation_report_hash)

    def deterministic_material(self) -> dict[str, object]:
        return {
            "accepted": self.accepted,
            "failures": self.failures,
            "fault_results": tuple(result.as_dict() for result in self.fault_results),
            "observed_at": self.observed_at,
            "result_hashes": self.result_hashes,
            "scenario_digest": self.scenario_digest,
            "scenario_receipt_hash": self.scenario_receipt_hash,
            "simulation_version": self.simulation_version,
            "wal_record_hash": self.wal_record_hash,
        }

    def as_dict(self) -> dict[str, object]:
        payload = self.deterministic_material()
        payload["report_hash"] = self.report_hash
        return _json_ready(payload)  # type: ignore[return-value]


class FileBackedDeterministicFaultSimulationHarness:
    """Runs deterministic local fault simulations under a runtime root."""

    def __init__(self, *, runtime_root: str | Path) -> None:
        self.runtime_root = _validate_runtime_root(Path(runtime_root))

    def simulate(
        self,
        scenario: Mapping[str, object],
        *,
        observed_at: str | None = None,
    ) -> FaultSimulationReport:
        if not isinstance(scenario, Mapping):
            raise DeterministicFaultSimulationError("scenario_must_be_mapping")
        observed = _timestamp(observed_at)
        data = _json_ready(scenario)
        if not isinstance(data, Mapping):
            raise DeterministicFaultSimulationError("scenario_must_be_mapping")
        scenario_id = _string_field(data, "scenario_id", "fault-simulation-533")
        seed = _string_field(data, "seed", "")
        faults = data.get("faults")
        if not isinstance(faults, Sequence) or isinstance(faults, (str, bytes)) or not faults:
            raise DeterministicFaultSimulationError("faults_must_be_nonempty_sequence")
        normalized_faults, scenario_failures = _normalize_faults(faults)
        scenario_digest = compute_fault_simulation_scenario_digest(data)
        scenario_receipt = FaultSimulationScenarioReceipt(
            scenario_version=DETERMINISTIC_FAULT_SIMULATION_VERSION,
            scenario_id=scenario_id,
            seed=seed,
            scenario_digest=scenario_digest,
            fault_count=len(normalized_faults),
            observed_at=observed,
        )
        results = tuple(
            self._simulate_fault(
                fault,
                seed=seed,
                scenario_id=scenario_id,
                index=index,
            )
            for index, fault in enumerate(normalized_faults)
        )
        failures = list(scenario_failures)
        for result in results:
            if not result.detected:
                failures.append("fault_not_detected:" + result.fault_id)
            if not result.safe_recovery:
                failures.append("unsafe_recovery:" + result.fault_id)
        result_hashes = tuple(result.result_hash for result in results)
        wal_record_hash = self._append_wal(
            accepted=not failures and bool(results),
            scenario_id=scenario_id,
            scenario_digest=scenario_digest,
            scenario_receipt_hash=scenario_receipt.receipt_hash,
            result_hashes=result_hashes,
            observed_at=observed,
        )
        report = FaultSimulationReport(
            simulation_version=DETERMINISTIC_FAULT_SIMULATION_VERSION,
            accepted=not failures and bool(results),
            failures=_dedupe(failures),
            scenario_receipt_hash=scenario_receipt.receipt_hash,
            scenario_digest=scenario_digest,
            result_hashes=result_hashes,
            fault_results=results,
            wal_record_hash=wal_record_hash,
            observed_at=observed,
        )
        self._persist_outputs(scenario_receipt, report)
        return report

    def _simulate_fault(
        self,
        fault: Mapping[str, object],
        *,
        seed: str,
        scenario_id: str,
        index: int,
    ) -> FaultSimulationResult:
        fault_type = str(fault["fault_type"])
        fault_id = str(fault["fault_id"])
        target = str(fault["target"])
        surface_dir = self._workspace_dir(scenario_id) / _safe_name(fault_id)
        surface_dir.mkdir(parents=True, exist_ok=True)
        probe_digest = self._materialize_probe(
            surface_dir=surface_dir,
            fault=fault,
            seed=seed,
            index=index,
        )
        forced_unsafe = fault.get("force_unsafe_recovery") is True
        quarantine_required = fault_type in {
            "corrupted_jsonl",
            "corrupted_recovery_source",
            "partial_write",
            "watchdog_timeout",
        }
        recovery_action = (
            "unsafe_recovery_attempt"
            if forced_unsafe
            else _RECOVERY_ACTIONS[fault_type]
        )
        detected = True
        safe_recovery = not forced_unsafe
        output_digest = _sha256_json(
            {
                "detected": detected,
                "fault_id": fault_id,
                "fault_type": fault_type,
                "probe_digest": probe_digest,
                "quarantine_required": quarantine_required,
                "recovery_action": recovery_action,
                "safe_recovery": safe_recovery,
                "seed": seed,
                "target": target,
            }
        )
        return FaultSimulationResult(
            fault_id=fault_id,
            fault_type=fault_type,
            target=target,
            detected=detected,
            recovery_action=recovery_action,
            safe_recovery=safe_recovery,
            quarantine_required=quarantine_required,
            output_digest=output_digest,
        )

    def _materialize_probe(
        self,
        *,
        surface_dir: Path,
        fault: Mapping[str, object],
        seed: str,
        index: int,
    ) -> str:
        fault_type = str(fault["fault_type"])
        target = str(fault["target"])
        probe_id = _sha256_json(
            {
                "fault_id": fault["fault_id"],
                "fault_type": fault_type,
                "index": index,
                "seed": seed,
                "target": target,
            }
        )
        if fault_type == "crash_before_write":
            return _sha256_json({"probe_id": probe_id, "write_performed": False})
        if fault_type == "partial_write":
            return self._write_probe(surface_dir / "partial.json", '{"partial":')
        if fault_type == "corrupted_jsonl":
            return self._write_probe(surface_dir / "wal.jsonl", '{"record": 1}\nnot-json\n')
        if fault_type == "hash_mismatch":
            payload = {"actual": probe_id, "expected": ZERO_HASH}
            return self._write_probe(surface_dir / "artifact.json", json.dumps(payload, sort_keys=True))
        if fault_type == "missing_artifact":
            return _sha256_json({"artifact_exists": False, "probe_id": probe_id})
        if fault_type == "stale_queue_lease":
            return self._write_probe(surface_dir / "lease.json", json.dumps({"lease": "stale", "probe_id": probe_id}, sort_keys=True))
        if fault_type in {"missing_approval", "revoked_approval", "expired_approval"}:
            return self._write_probe(surface_dir / "approval.json", json.dumps({"approval_state": fault_type, "probe_id": probe_id}, sort_keys=True))
        if fault_type in {"revoked_capability", "reused_capability"}:
            return self._write_probe(surface_dir / "capability.json", json.dumps({"capability_state": fault_type, "probe_id": probe_id}, sort_keys=True))
        if fault_type == "watchdog_timeout":
            return self._write_probe(surface_dir / "watchdog.json", json.dumps({"timed_out": True, "probe_id": probe_id}, sort_keys=True))
        if fault_type == "replay_missing_record":
            return self._write_probe(surface_dir / "replay.json", json.dumps({"missing_sequence": 3, "probe_id": probe_id}, sort_keys=True))
        if fault_type == "corrupted_recovery_source":
            return self._write_probe(surface_dir / "recovery-source.json", '{"recovery": "corrupt"')
        raise DeterministicFaultSimulationError("fault_type_invalid")

    def _write_probe(self, path: Path, text: str) -> str:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return _sha256_json({"path": path.relative_to(self.runtime_root).as_posix(), "text": text})

    def _append_wal(
        self,
        *,
        accepted: bool,
        scenario_id: str,
        scenario_digest: str,
        scenario_receipt_hash: str,
        result_hashes: tuple[str, ...],
        observed_at: str,
    ) -> str:
        wal_path = self._resolve_relpath(_WAL_RELPATH, "wal_relpath")
        wal_path.parent.mkdir(parents=True, exist_ok=True)
        result_bundle_hash = _sha256_json(result_hashes)
        material = {
            "accepted": accepted,
            "result_bundle_hash": result_bundle_hash,
            "scenario_digest": scenario_digest,
            "scenario_receipt_hash": scenario_receipt_hash,
        }
        return FileBackedRealWalStorage(wal_path).append(
            record_type="SYSTEM_ACCEPTANCE_EVENT",
            task_id=_TASK_ID,
            run_id=scenario_id,
            payload_hash=_sha256_json(material),
            digest_bindings={
                "fault_result_bundle_hash": result_bundle_hash,
                "scenario_digest": scenario_digest,
                "scenario_receipt_hash": scenario_receipt_hash,
            },
            created_at=observed_at,
        ).record_hash

    def _persist_outputs(
        self,
        scenario_receipt: FaultSimulationScenarioReceipt,
        report: FaultSimulationReport,
    ) -> None:
        self._write_new_json(_REPORT_RELPATH, report.as_dict())
        scenario_relpath = (
            _SCENARIO_RECEIPT_DIR_RELPATH
            + "/"
            + scenario_receipt.receipt_hash.removeprefix("sha256:")
            + ".json"
        )
        self._write_new_json(scenario_relpath, scenario_receipt.as_dict())
        report_relpath = (
            _REPORT_RECEIPT_DIR_RELPATH
            + "/"
            + report.report_hash.removeprefix("sha256:")
            + ".json"
        )
        self._write_new_json(report_relpath, report.as_dict())

    def _workspace_dir(self, scenario_id: str) -> Path:
        return self._resolve_relpath(
            _WORKSPACE_RELPATH + "/" + _safe_name(scenario_id),
            "workspace_relpath",
        )

    def _write_new_json(self, relpath: str, payload: object) -> None:
        path = self._resolve_relpath(relpath, "output_relpath")
        if path.exists():
            raise DeterministicFaultSimulationError("output_already_exists")
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
            raise DeterministicFaultSimulationError(
                field_name + "_must_be_nonempty_string"
            )
        if "\\" in relpath:
            raise DeterministicFaultSimulationError(
                field_name + "_backslash_forbidden"
            )
        pure = PurePosixPath(relpath)
        if pure.is_absolute() or ".." in pure.parts:
            raise DeterministicFaultSimulationError(
                field_name + "_must_stay_under_runtime_root"
            )
        path = (self.runtime_root / pure).resolve(strict=False)
        root = self.runtime_root.resolve()
        if path != root and root not in path.parents:
            raise DeterministicFaultSimulationError(
                field_name + "_escapes_runtime_root"
            )
        return path


def compute_fault_simulation_result_hash(result: FaultSimulationResult) -> str:
    return _sha256_json(result.deterministic_material())


def compute_fault_simulation_scenario_digest(scenario: Mapping[str, object]) -> str:
    if not isinstance(scenario, Mapping):
        raise DeterministicFaultSimulationError("scenario_must_be_mapping")
    return _sha256_json(_json_ready(scenario))


def compute_fault_simulation_scenario_receipt_hash(
    receipt: FaultSimulationScenarioReceipt,
) -> str:
    return _sha256_json(receipt.deterministic_material())


def compute_fault_simulation_report_hash(report: FaultSimulationReport) -> str:
    return _sha256_json(report.deterministic_material())


def _normalize_faults(
    faults: Sequence[object],
) -> tuple[tuple[dict[str, object], ...], tuple[str, ...]]:
    normalized: list[dict[str, object]] = []
    failures: list[str] = []
    seen_ids: set[str] = set()
    for index, fault in enumerate(faults, start=1):
        if not isinstance(fault, Mapping):
            failures.append("fault_must_be_mapping:" + str(index))
            continue
        fault_id = fault.get("fault_id", f"fault-{index}")
        fault_type = fault.get("fault_type")
        target = fault.get("target", "runtime")
        if not isinstance(fault_id, str) or not fault_id.strip():
            failures.append("fault_id_required:" + str(index))
            continue
        if fault_id in seen_ids:
            failures.append("duplicate_fault_id:" + fault_id)
            continue
        seen_ids.add(fault_id)
        if fault_type not in _FAULT_TYPES:
            failures.append("fault_type_invalid:" + fault_id)
            continue
        if not isinstance(target, str) or not target.strip():
            failures.append("fault_target_required:" + fault_id)
            continue
        normalized.append(
            {
                "fault_id": fault_id,
                "fault_type": fault_type,
                "force_unsafe_recovery": fault.get("force_unsafe_recovery") is True,
                "target": target,
            }
        )
    return tuple(normalized), tuple(_dedupe(failures))


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
        raise DeterministicFaultSimulationError(
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
        raise DeterministicFaultSimulationError(
            field_name + "_must_be_nonempty_string"
        )


def _require_sha256(value: object, field_name: str) -> None:
    if not isinstance(value, str) or not _SHA256_PATTERN.match(value):
        raise DeterministicFaultSimulationError(field_name + "_must_be_sha256")


def _string_field(data: Mapping[str, object], field_name: str, default: str) -> str:
    value = data.get(field_name, default)
    if not isinstance(value, str) or not value.strip():
        raise DeterministicFaultSimulationError(
            field_name + "_must_be_nonempty_string"
        )
    return value


def _normalize_results(
    values: Sequence[FaultSimulationResult],
) -> tuple[FaultSimulationResult, ...]:
    if not isinstance(values, Sequence) or isinstance(values, (str, bytes)):
        raise DeterministicFaultSimulationError("fault_results_must_be_sequence")
    results = tuple(values)
    for result in results:
        if not isinstance(result, FaultSimulationResult):
            raise DeterministicFaultSimulationError(
                "fault_result_must_be_fault_simulation_result"
            )
    return results


def _normalize_strings(values: Sequence[str], field_name: str) -> tuple[str, ...]:
    if not isinstance(values, Sequence) or isinstance(values, (str, bytes)):
        raise DeterministicFaultSimulationError(field_name + "s_must_be_sequence")
    normalized = tuple(str(value) for value in values)
    for value in normalized:
        _require_nonempty_string(value, field_name)
    return tuple(_dedupe(normalized))


def _normalize_hashes(values: Sequence[str], field_name: str) -> tuple[str, ...]:
    normalized = _normalize_strings(values, field_name)
    for value in normalized:
        _require_sha256(value, field_name)
    return normalized


def _install_or_verify_hash(instance: object, field_name: str, compute) -> None:
    current = getattr(instance, field_name)
    expected = compute(instance)
    if current in ("", None):
        object.__setattr__(instance, field_name, expected)
        return
    if current != expected:
        raise DeterministicFaultSimulationError(field_name + "_mismatch")


def _safe_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "-", value).strip("-") or "fault"


def _dedupe(values: Sequence[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    output: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            output.append(value)
    return tuple(output)
