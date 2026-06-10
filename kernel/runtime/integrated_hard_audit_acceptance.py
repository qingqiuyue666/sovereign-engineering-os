"""Integrated Hard Audit Acceptance V1.

Verifies the post-#529 evidence chain as one local acceptance surface:
final signoff, independent verification, transparency proof, declarative
policy decision, deterministic fault simulation, and release ceremony. The
verifier emits operator-readable audit reports and a digest-only WAL event. It
does not call networks, execute git, publish releases, or inspect secrets.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
from typing import Mapping, Sequence

from kernel.runtime.evidence_transparency_merkle_proof import (
    EvidenceTransparencyError,
    verify_evidence_transparency_inclusion_proof,
)
from kernel.stores.real_wal_storage import FileBackedRealWalStorage

__all__ = [
    "INTEGRATED_HARD_AUDIT_ACCEPTANCE_VERSION",
    "ZERO_HASH",
    "FileBackedIntegratedHardAuditAcceptance",
    "IntegratedHardAuditError",
    "IntegratedHardAuditReceipt",
    "compute_integrated_hard_audit_receipt_hash",
]

INTEGRATED_HARD_AUDIT_ACCEPTANCE_VERSION = "integrated_hard_audit_acceptance_v1"
ZERO_HASH = "sha256:" + ("0" * 64)

_TASK_ID = "task-535-integrated-hard-audit-acceptance"
_WAL_RELPATH = "integrated-hard-audit/hard-audit.real-wal.jsonl"
_REPORT_JSON_RELPATH = "integrated-hard-audit/reports/integrated-hard-audit-report.json"
_REPORT_MD_RELPATH = "integrated-hard-audit/reports/integrated-hard-audit-report.md"
_RECEIPT_DIR_RELPATH = "integrated-hard-audit/receipts"
_SHA256_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")

_UPSTREAM_KEYS = (
    "final_signoff_receipt",
    "independent_verification_receipt",
    "transparency_root_receipt",
    "policy_decision_receipt",
    "fault_simulation_report",
    "release_ceremony_receipt",
)
_REQUIRED_RUNBOOK_LINKS = {
    "rollback_recovery_link": "docs/runbooks/recovery_rollback_disaster_procedure_v1.md",
    "e2e_acceptance_link": "docs/runbooks/system_e2e_acceptance_v1.md",
    "security_hardening_link": "docs/runbooks/security_abuse_boundary_hardening_v1.md",
}
_EXPECTED_VERSIONS = {
    "final_signoff_receipt": "release_candidate_final_signoff_v1",
    "independent_verification_receipt": "independent_final_signoff_verification_v1",
    "transparency_root_receipt": "evidence_transparency_merkle_proof_v1",
    "policy_decision_receipt": "declarative_policy_gate_bundle_v1",
    "fault_simulation_report": "deterministic_fault_simulation_harness_v1",
    "release_ceremony_receipt": "release_ceremony_tagging_artifact_gate_v1",
}


class IntegratedHardAuditError(ValueError):
    """Raised when integrated hard audit evidence is malformed."""


@dataclass(frozen=True)
class IntegratedHardAuditReceipt:
    audit_version: str
    accepted: bool
    failures: tuple[str, ...]
    audit_id: str
    sequence_receipt_hashes: tuple[str, ...]
    wal_event_chain_hash: str
    artifact_report_digest_hash: str
    transparency_proof_verification_hash: str
    operator_report_digest: str
    operator_report_relpath: str
    runbook_link_digest: str
    release_ceremony_receipt_hash: str
    wal_record_hash: str
    observed_at: str
    receipt_hash: str = ""

    def __post_init__(self) -> None:
        if self.audit_version != INTEGRATED_HARD_AUDIT_ACCEPTANCE_VERSION:
            raise IntegratedHardAuditError("audit_version_invalid")
        if not isinstance(self.accepted, bool):
            raise IntegratedHardAuditError("accepted_must_be_bool")
        object.__setattr__(self, "failures", _normalize_strings(self.failures, "failure"))
        object.__setattr__(
            self,
            "sequence_receipt_hashes",
            _normalize_hashes(self.sequence_receipt_hashes, "sequence_receipt_hash"),
        )
        _require_nonempty_string(self.audit_id, "audit_id")
        for field_name in (
            "wal_event_chain_hash",
            "artifact_report_digest_hash",
            "transparency_proof_verification_hash",
            "operator_report_digest",
            "runbook_link_digest",
            "release_ceremony_receipt_hash",
            "wal_record_hash",
        ):
            _require_sha256(getattr(self, field_name), field_name)
        _require_nonempty_string(self.operator_report_relpath, "operator_report_relpath")
        _require_nonempty_string(self.observed_at, "observed_at")
        expected_acceptance = (
            not self.failures
            and len(self.sequence_receipt_hashes) == len(_UPSTREAM_KEYS)
            and all(value != ZERO_HASH for value in self.sequence_receipt_hashes)
            and self.wal_event_chain_hash != ZERO_HASH
            and self.artifact_report_digest_hash != ZERO_HASH
            and self.transparency_proof_verification_hash != ZERO_HASH
            and self.operator_report_digest != ZERO_HASH
            and self.runbook_link_digest != ZERO_HASH
            and self.release_ceremony_receipt_hash != ZERO_HASH
            and self.wal_record_hash != ZERO_HASH
        )
        if self.accepted != expected_acceptance:
            raise IntegratedHardAuditError(
                "accepted_must_match_integrated_audit_evidence"
            )
        _install_or_verify_hash(self, "receipt_hash", compute_integrated_hard_audit_receipt_hash)

    def deterministic_material(self) -> dict[str, object]:
        return {
            "accepted": self.accepted,
            "artifact_report_digest_hash": self.artifact_report_digest_hash,
            "audit_id": self.audit_id,
            "audit_version": self.audit_version,
            "failures": self.failures,
            "observed_at": self.observed_at,
            "operator_report_digest": self.operator_report_digest,
            "operator_report_relpath": self.operator_report_relpath,
            "release_ceremony_receipt_hash": self.release_ceremony_receipt_hash,
            "runbook_link_digest": self.runbook_link_digest,
            "sequence_receipt_hashes": self.sequence_receipt_hashes,
            "transparency_proof_verification_hash": self.transparency_proof_verification_hash,
            "wal_event_chain_hash": self.wal_event_chain_hash,
            "wal_record_hash": self.wal_record_hash,
        }

    def as_dict(self) -> dict[str, object]:
        payload = self.deterministic_material()
        payload["receipt_hash"] = self.receipt_hash
        return _json_ready(payload)  # type: ignore[return-value]


class FileBackedIntegratedHardAuditAcceptance:
    """Verifies the complete post-#529 local evidence chain."""

    def __init__(
        self,
        *,
        runtime_root: str | Path,
        repo_root: str | Path | None = None,
    ) -> None:
        self.runtime_root = _validate_runtime_root(Path(runtime_root))
        self.repo_root = Path(repo_root or Path.cwd()).resolve(strict=False)

    def verify(
        self,
        evidence: Mapping[str, object],
        *,
        observed_at: str | None = None,
    ) -> IntegratedHardAuditReceipt:
        if not isinstance(evidence, Mapping):
            raise IntegratedHardAuditError("evidence_must_be_mapping")
        observed = _timestamp(observed_at)
        data = _json_ready(evidence)
        if not isinstance(data, Mapping):
            raise IntegratedHardAuditError("evidence_must_be_mapping")

        audit_id = _string_field(data, "audit_id", "post-529-integrated-hard-audit-535")
        upstreams = {key: self._load_upstream_mapping(data, key) for key in _UPSTREAM_KEYS}
        failures: list[str] = []
        for key, value in upstreams.items():
            if value is None:
                failures.append("missing_upstream_receipt:" + key)

        final_signoff = upstreams["final_signoff_receipt"] or {}
        independent = upstreams["independent_verification_receipt"] or {}
        transparency = upstreams["transparency_root_receipt"] or {}
        policy = upstreams["policy_decision_receipt"] or {}
        fault = upstreams["fault_simulation_report"] or {}
        release = upstreams["release_ceremony_receipt"] or {}

        final_hash, final_failures = _verify_final_signoff(final_signoff)
        independent_hash, independent_failures = _verify_independent(independent)
        transparency_receipt_hash, transparency_failures = _verify_transparency(transparency)
        policy_hash, policy_failures, policy_allowed = _verify_policy(policy)
        fault_hash, fault_failures, fault_accepted = _verify_fault_simulation(fault)
        release_hash, release_failures, release_accepted = _verify_release_ceremony(release)
        failures.extend(final_failures)
        failures.extend(independent_failures)
        failures.extend(transparency_failures)
        failures.extend(policy_failures)
        failures.extend(fault_failures)
        failures.extend(release_failures)
        if policy_allowed is False and release_accepted is True:
            failures.append("release_ceremony_should_not_accept_failed_policy")
        if fault_accepted is False and release_accepted is True:
            failures.append("release_ceremony_should_not_accept_failed_simulation")

        proof_hash, proof_failures = _verify_transparency_proof(
            data.get("transparency_inclusion_proof"),
            data.get("transparency_inclusion_proofs"),
            transparency,
        )
        failures.extend(proof_failures)

        wal_hashes, wal_failures = _wal_hashes_for_chain(upstreams)
        failures.extend(wal_failures)
        wal_event_chain_hash = _sha256_json(wal_hashes) if wal_hashes else ZERO_HASH
        artifact_digest_hash, artifact_failures = _artifact_report_digest_hash(
            final_signoff=final_signoff,
            independent=independent,
            release=release,
        )
        failures.extend(artifact_failures)
        runbook_link_digest, runbook_failures = self._runbook_link_digest(final_signoff)
        failures.extend(runbook_failures)

        sequence_receipt_hashes = (
            final_hash,
            independent_hash,
            transparency_receipt_hash,
            policy_hash,
            fault_hash,
            release_hash,
        )
        unique_failures = _dedupe(failures)
        report_text = _operator_report_text(
            audit_id=audit_id,
            accepted=not unique_failures,
            failures=unique_failures,
            observed_at=observed,
            sequence_receipt_hashes=sequence_receipt_hashes,
            wal_event_chain_hash=wal_event_chain_hash,
            artifact_report_digest_hash=artifact_digest_hash,
            runbook_link_digest=runbook_link_digest,
        )
        operator_report_digest = _sha256_text(report_text)
        wal_record_hash = self._append_wal(
            accepted=not unique_failures,
            audit_id=audit_id,
            sequence_receipt_hashes=sequence_receipt_hashes,
            wal_event_chain_hash=wal_event_chain_hash,
            artifact_report_digest_hash=artifact_digest_hash,
            proof_verification_hash=proof_hash,
            operator_report_digest=operator_report_digest,
            runbook_link_digest=runbook_link_digest,
            observed_at=observed,
        )
        receipt = IntegratedHardAuditReceipt(
            audit_version=INTEGRATED_HARD_AUDIT_ACCEPTANCE_VERSION,
            accepted=not unique_failures,
            failures=unique_failures,
            audit_id=audit_id,
            sequence_receipt_hashes=sequence_receipt_hashes,
            wal_event_chain_hash=wal_event_chain_hash,
            artifact_report_digest_hash=artifact_digest_hash,
            transparency_proof_verification_hash=proof_hash,
            operator_report_digest=operator_report_digest,
            operator_report_relpath=_REPORT_MD_RELPATH,
            runbook_link_digest=runbook_link_digest,
            release_ceremony_receipt_hash=release_hash,
            wal_record_hash=wal_record_hash,
            observed_at=observed,
        )
        self._persist_outputs(receipt, report_text)
        return receipt

    def _load_upstream_mapping(
        self,
        evidence: Mapping[str, object],
        key: str,
    ) -> Mapping[str, object] | None:
        value = evidence.get(key)
        if isinstance(value, Mapping):
            return _json_ready(value)  # type: ignore[return-value]
        relpath_value = evidence.get(key + "_relpath")
        if relpath_value is None:
            return None
        relpath = _string_value(relpath_value, key + "_relpath")
        path = self._resolve_relpath(relpath, key + "_relpath")
        if not path.is_file():
            raise IntegratedHardAuditError(key + "_relpath_missing")
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise IntegratedHardAuditError(key + "_relpath_invalid_json") from exc
        if not isinstance(payload, Mapping):
            raise IntegratedHardAuditError(key + "_relpath_must_be_json_object")
        return _json_ready(payload)  # type: ignore[return-value]

    def _runbook_link_digest(
        self,
        final_signoff: Mapping[str, object],
    ) -> tuple[str, tuple[str, ...]]:
        failures: list[str] = []
        links: dict[str, str] = {}
        for field_name, expected in _REQUIRED_RUNBOOK_LINKS.items():
            actual = final_signoff.get(field_name)
            if actual != expected:
                failures.append("runbook_link_mismatch:" + field_name)
                continue
            path = (self.repo_root / expected).resolve(strict=False)
            if not path.is_file() or self.repo_root.resolve() not in path.parents:
                failures.append("runbook_link_missing:" + expected)
                continue
            links[field_name] = expected
        if failures:
            return ZERO_HASH, tuple(_dedupe(failures))
        return _sha256_json(links), ()

    def _append_wal(
        self,
        *,
        accepted: bool,
        audit_id: str,
        sequence_receipt_hashes: tuple[str, ...],
        wal_event_chain_hash: str,
        artifact_report_digest_hash: str,
        proof_verification_hash: str,
        operator_report_digest: str,
        runbook_link_digest: str,
        observed_at: str,
    ) -> str:
        wal_path = self._resolve_relpath(_WAL_RELPATH, "wal_relpath")
        wal_path.parent.mkdir(parents=True, exist_ok=True)
        sequence_hash = _sha256_json(sequence_receipt_hashes)
        material = {
            "accepted": accepted,
            "artifact_report_digest_hash": artifact_report_digest_hash,
            "operator_report_digest": operator_report_digest,
            "proof_verification_hash": proof_verification_hash,
            "runbook_link_digest": runbook_link_digest,
            "sequence_hash": sequence_hash,
            "wal_event_chain_hash": wal_event_chain_hash,
        }
        return FileBackedRealWalStorage(wal_path).append(
            record_type="SYSTEM_ACCEPTANCE_EVENT",
            task_id=_TASK_ID,
            run_id=audit_id,
            payload_hash=_sha256_json(material),
            digest_bindings={
                "artifact_report_digest_hash": artifact_report_digest_hash,
                "operator_report_digest": operator_report_digest,
                "proof_verification_hash": proof_verification_hash,
                "runbook_link_digest": runbook_link_digest,
                "sequence_hash": sequence_hash,
                "wal_event_chain_hash": wal_event_chain_hash,
            },
            created_at=observed_at,
        ).record_hash

    def _persist_outputs(
        self,
        receipt: IntegratedHardAuditReceipt,
        report_text: str,
    ) -> None:
        self._write_new_text(_REPORT_MD_RELPATH, report_text)
        self._write_new_json(
            _REPORT_JSON_RELPATH,
            {
                "accepted": receipt.accepted,
                "artifact_report_digest_hash": receipt.artifact_report_digest_hash,
                "failures": receipt.failures,
                "operator_report_digest": receipt.operator_report_digest,
                "operator_report_relpath": receipt.operator_report_relpath,
                "receipt_hash": receipt.receipt_hash,
                "release_ceremony_receipt_hash": receipt.release_ceremony_receipt_hash,
                "runbook_link_digest": receipt.runbook_link_digest,
                "transparency_proof_verification_hash": receipt.transparency_proof_verification_hash,
                "wal_event_chain_hash": receipt.wal_event_chain_hash,
                "wal_record_hash": receipt.wal_record_hash,
            },
        )
        receipt_relpath = (
            _RECEIPT_DIR_RELPATH
            + "/"
            + receipt.receipt_hash.removeprefix("sha256:")
            + ".json"
        )
        self._write_new_json(receipt_relpath, receipt.as_dict())

    def _write_new_json(self, relpath: str, payload: object) -> None:
        self._write_new_text(
            relpath,
            json.dumps(
                _json_ready(payload),
                sort_keys=True,
                indent=2,
                ensure_ascii=True,
            )
            + "\n",
        )

    def _write_new_text(self, relpath: str, text: str) -> None:
        path = self._resolve_relpath(relpath, "output_relpath")
        if path.exists():
            raise IntegratedHardAuditError("output_already_exists")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def _resolve_relpath(self, relpath: str, field_name: str) -> Path:
        if not isinstance(relpath, str) or not relpath:
            raise IntegratedHardAuditError(
                field_name + "_must_be_nonempty_string"
            )
        if "\\" in relpath:
            raise IntegratedHardAuditError(field_name + "_backslash_forbidden")
        pure = PurePosixPath(relpath)
        if pure.is_absolute() or ".." in pure.parts:
            raise IntegratedHardAuditError(
                field_name + "_must_stay_under_runtime_root"
            )
        path = (self.runtime_root / pure).resolve(strict=False)
        root = self.runtime_root.resolve()
        if path != root and root not in path.parents:
            raise IntegratedHardAuditError(field_name + "_escapes_runtime_root")
        return path


def compute_integrated_hard_audit_receipt_hash(
    receipt: IntegratedHardAuditReceipt,
) -> str:
    return _sha256_json(receipt.deterministic_material())


def _verify_final_signoff(receipt: Mapping[str, object]) -> tuple[str, tuple[str, ...]]:
    failures: list[str] = []
    receipt_hash = _hash_field(receipt, "receipt_hash", failures)
    if receipt.get("integration_version") != _EXPECTED_VERSIONS["final_signoff_receipt"]:
        failures.append("final_signoff_version_invalid")
    if receipt.get("accepted") is not True:
        failures.append("final_signoff_receipt_not_accepted")
    if receipt.get("final_verdict") != "READY_TO_REVIEW_AND_MERGE":
        failures.append("final_signoff_verdict_not_ready")
    for field_name in ("final_signoff_report_hash", "final_system_status_report_hash"):
        _hash_field(receipt, field_name, failures)
    return receipt_hash, tuple(_dedupe(failures))


def _verify_independent(receipt: Mapping[str, object]) -> tuple[str, tuple[str, ...]]:
    failures: list[str] = []
    receipt_hash = _hash_field(receipt, "receipt_hash", failures)
    if receipt.get("integration_version") != _EXPECTED_VERSIONS["independent_verification_receipt"]:
        failures.append("independent_verification_version_invalid")
    if receipt.get("accepted") is not True:
        failures.append("independent_verification_receipt_not_accepted")
    return receipt_hash, tuple(_dedupe(failures))


def _verify_transparency(receipt: Mapping[str, object]) -> tuple[str, tuple[str, ...]]:
    failures: list[str] = []
    receipt_hash = _hash_field(receipt, "receipt_hash", failures)
    _hash_field(receipt, "root_hash", failures)
    if receipt.get("transparency_version") != _EXPECTED_VERSIONS["transparency_root_receipt"]:
        failures.append("transparency_root_version_invalid")
    if receipt.get("accepted") is not True:
        failures.append("transparency_root_receipt_not_accepted")
    return receipt_hash, tuple(_dedupe(failures))


def _verify_policy(
    receipt: Mapping[str, object],
) -> tuple[str, tuple[str, ...], bool | None]:
    failures: list[str] = []
    receipt_hash = _hash_field(receipt, "receipt_hash", failures)
    if receipt.get("decision_version") != _EXPECTED_VERSIONS["policy_decision_receipt"]:
        failures.append("policy_decision_version_invalid")
    allowed = receipt.get("allowed")
    if allowed is not True or receipt.get("decision") != "allow":
        failures.append("policy_decision_not_allowed")
    return receipt_hash, tuple(_dedupe(failures)), allowed if isinstance(allowed, bool) else None


def _verify_fault_simulation(
    report: Mapping[str, object],
) -> tuple[str, tuple[str, ...], bool | None]:
    failures: list[str] = []
    report_hash = _hash_field(report, "report_hash", failures)
    if report.get("simulation_version") != _EXPECTED_VERSIONS["fault_simulation_report"]:
        failures.append("fault_simulation_version_invalid")
    accepted = report.get("accepted")
    if accepted is not True:
        failures.append("fault_simulation_report_not_accepted")
    results = report.get("fault_results", ())
    if not isinstance(results, Sequence) or isinstance(results, (str, bytes)) or not results:
        failures.append("fault_simulation_results_required")
    else:
        for index, result in enumerate(results, start=1):
            if not isinstance(result, Mapping):
                failures.append("fault_simulation_result_must_be_mapping:" + str(index))
                continue
            fault_id = str(result.get("fault_id", index))
            if result.get("detected") is not True:
                failures.append("fault_simulation_not_detected:" + fault_id)
            if result.get("safe_recovery") is not True:
                failures.append("fault_simulation_unsafe_recovery:" + fault_id)
    return report_hash, tuple(_dedupe(failures)), accepted if isinstance(accepted, bool) else None


def _verify_release_ceremony(
    receipt: Mapping[str, object],
) -> tuple[str, tuple[str, ...], bool | None]:
    failures: list[str] = []
    receipt_hash = _hash_field(receipt, "receipt_hash", failures)
    if receipt.get("release_version") != _EXPECTED_VERSIONS["release_ceremony_receipt"]:
        failures.append("release_ceremony_version_invalid")
    accepted = receipt.get("accepted")
    if accepted is not True:
        failures.append("release_ceremony_receipt_not_accepted")
    if receipt.get("tag_created") is not False:
        failures.append("release_ceremony_tag_created")
    if receipt.get("tag_pushed") is not False:
        failures.append("release_ceremony_tag_pushed")
    if receipt.get("external_artifacts_published") is not False:
        failures.append("release_ceremony_external_publish")
    return receipt_hash, tuple(_dedupe(failures)), accepted if isinstance(accepted, bool) else None


def _verify_transparency_proof(
    proof: object,
    proofs: object,
    root_receipt: Mapping[str, object],
) -> tuple[str, tuple[str, ...]]:
    selected = proof
    if selected is None and isinstance(proofs, Sequence) and not isinstance(proofs, (str, bytes)) and proofs:
        selected = proofs[0]
    if selected is None:
        return ZERO_HASH, ("transparency_inclusion_proof_required",)
    try:
        result = verify_evidence_transparency_inclusion_proof(
            selected,  # type: ignore[arg-type]
            root_receipt,
        )
    except (EvidenceTransparencyError, TypeError, ValueError):
        return ZERO_HASH, ("transparency_proof_invalid",)
    failures: list[str] = []
    if not result.accepted:
        failures.append("corrupted_transparency_proof")
        failures.extend("transparency_proof_" + failure for failure in result.failures)
    return result.verification_hash, tuple(_dedupe(failures))


def _wal_hashes_for_chain(
    upstreams: Mapping[str, Mapping[str, object] | None],
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    failures: list[str] = []
    hashes: list[str] = []
    for key in _UPSTREAM_KEYS:
        payload = upstreams.get(key) or {}
        field_name = "wal_record_hash"
        value = payload.get(field_name)
        if not isinstance(value, str) or not _SHA256_PATTERN.match(value) or value == ZERO_HASH:
            failures.append("wal_record_hash_invalid:" + key)
            continue
        hashes.append(value)
    return tuple(hashes), tuple(_dedupe(failures))


def _artifact_report_digest_hash(
    *,
    final_signoff: Mapping[str, object],
    independent: Mapping[str, object],
    release: Mapping[str, object],
) -> tuple[str, tuple[str, ...]]:
    failures: list[str] = []
    fields = {
        "final_signoff_report_hash": final_signoff.get("final_signoff_report_hash"),
        "final_system_status_report_hash": final_signoff.get("final_system_status_report_hash"),
        "independent_final_signoff_report_hash": independent.get("final_signoff_report_hash"),
        "release_notes_digest": release.get("release_notes_digest"),
        "tag_command_digest": release.get("tag_command_digest"),
    }
    for key, value in fields.items():
        if not isinstance(value, str) or not _SHA256_PATTERN.match(value) or value == ZERO_HASH:
            failures.append("artifact_digest_invalid:" + key)
    if failures:
        return ZERO_HASH, tuple(_dedupe(failures))
    return _sha256_json(fields), ()


def _operator_report_text(
    *,
    audit_id: str,
    accepted: bool,
    failures: tuple[str, ...],
    observed_at: str,
    sequence_receipt_hashes: tuple[str, ...],
    wal_event_chain_hash: str,
    artifact_report_digest_hash: str,
    runbook_link_digest: str,
) -> str:
    lines = [
        "# Integrated Hard Audit Report",
        "",
        f"Audit ID: {audit_id}",
        f"Accepted: {str(accepted).lower()}",
        f"Observed at: {observed_at}",
        "",
        "Evidence sequence:",
    ]
    for index, receipt_hash in enumerate(sequence_receipt_hashes, start=1):
        lines.append(f"- Step {index}: {receipt_hash}")
    lines.extend(
        [
            "",
            f"WAL event chain hash: {wal_event_chain_hash}",
            f"Artifact/report digest hash: {artifact_report_digest_hash}",
            f"Runbook link digest: {runbook_link_digest}",
            "",
            "Failures:",
        ]
    )
    if failures:
        for failure in failures:
            lines.append(f"- {failure}")
    else:
        lines.append("- none")
    lines.append("")
    return "\n".join(lines)


def _hash_field(
    payload: Mapping[str, object],
    field_name: str,
    failures: list[str],
) -> str:
    value = payload.get(field_name)
    if not isinstance(value, str) or not _SHA256_PATTERN.match(value):
        failures.append(field_name + "_invalid")
        return ZERO_HASH
    return value


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
        raise IntegratedHardAuditError("value_must_be_json_serializable") from exc


def _sha256_json(value: object) -> str:
    encoded = json.dumps(
        _json_ready(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def _sha256_text(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def _require_nonempty_string(value: object, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise IntegratedHardAuditError(field_name + "_must_be_nonempty_string")


def _require_sha256(value: object, field_name: str) -> None:
    if not isinstance(value, str) or not _SHA256_PATTERN.match(value):
        raise IntegratedHardAuditError(field_name + "_must_be_sha256")


def _string_field(data: Mapping[str, object], field_name: str, default: str) -> str:
    value = data.get(field_name, default)
    if not isinstance(value, str) or not value.strip():
        return default
    return value


def _string_value(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise IntegratedHardAuditError(field_name + "_must_be_nonempty_string")
    return value


def _normalize_strings(values: Sequence[str], field_name: str) -> tuple[str, ...]:
    if not isinstance(values, Sequence) or isinstance(values, (str, bytes)):
        raise IntegratedHardAuditError(field_name + "s_must_be_sequence")
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
        raise IntegratedHardAuditError(field_name + "_mismatch")


def _dedupe(values: Sequence[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    output: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            output.append(value)
    return tuple(output)
