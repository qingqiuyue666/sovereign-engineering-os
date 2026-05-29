"""Release Candidate / Final Signoff V1.

This module closes the final-system landing by validating caller-supplied
release evidence, writing digest-only signoff reports, and appending one local
WAL event. It does not execute tests, call providers, inspect credentials, or
modify repository state.
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
    "RELEASE_CANDIDATE_FINAL_SIGNOFF_VERSION",
    "ZERO_HASH",
    "FileBackedReleaseCandidateFinalSignoff",
    "ReleaseCandidateFinalSignoffError",
    "ReleaseCandidateFinalSignoffReceipt",
    "ReleaseCandidateGateResult",
    "compute_release_candidate_final_signoff_receipt_hash",
    "compute_release_candidate_gate_result_hash",
]

RELEASE_CANDIDATE_FINAL_SIGNOFF_VERSION = "release_candidate_final_signoff_v1"
ZERO_HASH = "sha256:" + ("0" * 64)

_TASK_ID = "task-529-release-candidate-final-signoff"
_WAL_RELPATH = "release-candidate-final-signoff/signoff.real-wal.jsonl"
_REPORT_DIR_RELPATH = "release-candidate-final-signoff/reports"
_SIGNOFF_REPORT_RELPATH = _REPORT_DIR_RELPATH + "/final-signoff-report.json"
_SYSTEM_STATUS_REPORT_RELPATH = _REPORT_DIR_RELPATH + "/final-system-status-report.json"
_RECEIPT_DIR_RELPATH = "release-candidate-final-signoff/receipts"
_FINAL_VERDICT = "READY_TO_REVIEW_AND_MERGE"
_MERGED_STATUS = "merged and post-merge validated"
_RELEASE_TAG_PATTERN = re.compile(r"^v\d+\.\d+\.\d+-rc\.529(?:\+[0-9a-f]{7,40})?$")
_SHA256_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")

_PRIORITY_IDS = tuple(f"#{number}" for number in range(517, 530))
_REQUIRED_DOC_LINKS = {
    "rollback_recovery_link": "docs/runbooks/recovery_rollback_disaster_procedure_v1.md",
    "e2e_acceptance_link": "docs/runbooks/system_e2e_acceptance_v1.md",
    "security_hardening_link": "docs/runbooks/security_abuse_boundary_hardening_v1.md",
}
_REQUIRED_AUDIT_LINKS = {
    "rollback_recovery_audit_link": "docs/audit/recovery_rollback_disaster_procedure_v1.md",
    "e2e_acceptance_audit_link": "docs/audit/system_e2e_acceptance_v1.md",
    "security_hardening_audit_link": "docs/audit/security_abuse_boundary_hardening_v1.md",
}
_REQUIRED_INVARIANTS = (
    "evidence_first",
    "contract_first",
    "test_first",
    "failure_path_first",
    "fail_closed_by_default",
    "local_first",
    "deterministic_replay",
    "no_silent_repair",
    "no_fake_acceptance",
    "no_direct_main_mutation",
    "no_hidden_runtime_autonomy",
    "no_unsafe_process_launch",
    "no_hidden_network_calls",
    "no_credential_access",
    "no_uncontrolled_dependencies",
    "no_external_code_copying",
)
_REQUIRED_ACCEPTANCE_KEYS = (
    "focused_release_candidate_tests",
    "tracer_bullet_discovery",
    "full_unittest_discovery",
    "make_ci",
    "git_diff_check",
    "git_status_short",
)
_GREEN_VALUES = frozenset({"green", "ok", "success", "clean", "passed"})
_REQUIRED_GATE_IDS = (
    "version_tuple_freeze",
    "schema_freeze_check",
    "acceptance_matrix",
    "invariant_sweep",
    "docs_runbook_alignment",
    "stale_pr_body_docs_cleanup",
    "no_todo_as_implementation",
    "no_placeholder_blockers",
    "no_known_untriaged_blocker",
    "full_test_suite_green",
    "ci_green",
    "local_worktree_clean",
    "release_tag_proposal",
    "final_signoff_report",
    "final_system_status_report",
    "rollback_recovery_linked",
    "e2e_acceptance_linked",
    "security_hardening_linked",
    "priority_matrix_closed",
)


class ReleaseCandidateFinalSignoffError(ValueError):
    """Raised when final signoff evidence fails closed."""


@dataclass(frozen=True)
class ReleaseCandidateGateResult:
    gate_id: str
    accepted: bool
    evidence_hash: str
    failures: tuple[str, ...]
    gate_hash: str = ""

    def __post_init__(self) -> None:
        if self.gate_id not in _REQUIRED_GATE_IDS:
            raise ReleaseCandidateFinalSignoffError("gate_id_invalid")
        if not isinstance(self.accepted, bool):
            raise ReleaseCandidateFinalSignoffError("accepted_must_be_bool")
        _require_sha256(self.evidence_hash, "evidence_hash")
        object.__setattr__(self, "failures", _normalize_failures(self.failures))
        if self.accepted and self.failures:
            raise ReleaseCandidateFinalSignoffError("accepted_gate_has_failures")
        if not self.accepted and not self.failures:
            raise ReleaseCandidateFinalSignoffError("rejected_gate_requires_failures")
        _install_or_verify_hash(self, "gate_hash", compute_release_candidate_gate_result_hash)

    def as_dict(self) -> dict[str, object]:
        return _json_ready(asdict(self))  # type: ignore[return-value]


@dataclass(frozen=True)
class ReleaseCandidateFinalSignoffReceipt:
    integration_version: str
    accepted: bool
    failures: tuple[str, ...]
    signoff_id: str
    repository_url: str
    main_head: str
    branch: str
    release_tag_proposal: str
    final_verdict: str
    gate_results: tuple[ReleaseCandidateGateResult, ...]
    version_tuple_hash: str
    schema_freeze_hash: str
    acceptance_matrix_hash: str
    invariant_sweep_hash: str
    docs_alignment_hash: str
    cleanup_evidence_hash: str
    priority_status_matrix_hash: str
    final_signoff_report_hash: str
    final_system_status_report_hash: str
    evidence_chain_hash: str
    wal_record_hash: str
    rollback_recovery_link: str
    e2e_acceptance_link: str
    security_hardening_link: str
    observed_at: str
    receipt_hash: str = ""

    def __post_init__(self) -> None:
        if self.integration_version != RELEASE_CANDIDATE_FINAL_SIGNOFF_VERSION:
            raise ReleaseCandidateFinalSignoffError("integration_version_invalid")
        if not isinstance(self.accepted, bool):
            raise ReleaseCandidateFinalSignoffError("accepted_must_be_bool")
        object.__setattr__(self, "failures", _normalize_failures(self.failures))
        object.__setattr__(self, "gate_results", _normalize_gate_results(self.gate_results))
        for field_name in (
            "signoff_id",
            "repository_url",
            "main_head",
            "branch",
            "release_tag_proposal",
            "final_verdict",
            "rollback_recovery_link",
            "e2e_acceptance_link",
            "security_hardening_link",
            "observed_at",
        ):
            _require_nonempty_string(getattr(self, field_name), field_name)
        for field_name in (
            "version_tuple_hash",
            "schema_freeze_hash",
            "acceptance_matrix_hash",
            "invariant_sweep_hash",
            "docs_alignment_hash",
            "cleanup_evidence_hash",
            "priority_status_matrix_hash",
            "final_signoff_report_hash",
            "final_system_status_report_hash",
            "evidence_chain_hash",
            "wal_record_hash",
        ):
            _require_sha256(getattr(self, field_name), field_name)
        expected_acceptance = (
            not self.failures
            and all(gate.accepted for gate in self.gate_results)
            and self.final_verdict == _FINAL_VERDICT
            and self.wal_record_hash != ZERO_HASH
        )
        if self.accepted != expected_acceptance:
            raise ReleaseCandidateFinalSignoffError("accepted_must_match_gate_evidence")
        if self.accepted:
            if self.final_verdict != _FINAL_VERDICT:
                raise ReleaseCandidateFinalSignoffError("final_verdict_invalid")
            if not _RELEASE_TAG_PATTERN.match(self.release_tag_proposal):
                raise ReleaseCandidateFinalSignoffError("release_tag_proposal_invalid")
            if self.rollback_recovery_link != _REQUIRED_DOC_LINKS["rollback_recovery_link"]:
                raise ReleaseCandidateFinalSignoffError("rollback_recovery_link_invalid")
            if self.e2e_acceptance_link != _REQUIRED_DOC_LINKS["e2e_acceptance_link"]:
                raise ReleaseCandidateFinalSignoffError("e2e_acceptance_link_invalid")
            if self.security_hardening_link != _REQUIRED_DOC_LINKS["security_hardening_link"]:
                raise ReleaseCandidateFinalSignoffError("security_hardening_link_invalid")
        _install_or_verify_hash(
            self,
            "receipt_hash",
            compute_release_candidate_final_signoff_receipt_hash,
        )

    def deterministic_material(self) -> dict[str, object]:
        return {
            "acceptance_matrix_hash": self.acceptance_matrix_hash,
            "accepted": self.accepted,
            "branch": self.branch,
            "cleanup_evidence_hash": self.cleanup_evidence_hash,
            "docs_alignment_hash": self.docs_alignment_hash,
            "e2e_acceptance_link": self.e2e_acceptance_link,
            "evidence_chain_hash": self.evidence_chain_hash,
            "failures": self.failures,
            "final_signoff_report_hash": self.final_signoff_report_hash,
            "final_system_status_report_hash": self.final_system_status_report_hash,
            "final_verdict": self.final_verdict,
            "gate_results": tuple(gate.as_dict() for gate in self.gate_results),
            "integration_version": self.integration_version,
            "invariant_sweep_hash": self.invariant_sweep_hash,
            "main_head": self.main_head,
            "observed_at": self.observed_at,
            "priority_status_matrix_hash": self.priority_status_matrix_hash,
            "release_tag_proposal": self.release_tag_proposal,
            "repository_url": self.repository_url,
            "rollback_recovery_link": self.rollback_recovery_link,
            "schema_freeze_hash": self.schema_freeze_hash,
            "security_hardening_link": self.security_hardening_link,
            "signoff_id": self.signoff_id,
            "version_tuple_hash": self.version_tuple_hash,
            "wal_record_hash": self.wal_record_hash,
        }

    def as_dict(self) -> dict[str, object]:
        payload = self.deterministic_material()
        payload["receipt_hash"] = self.receipt_hash
        return _json_ready(payload)  # type: ignore[return-value]


class FileBackedReleaseCandidateFinalSignoff:
    """File-backed, digest-only final signoff evaluator."""

    def __init__(self, *, runtime_root: str | Path) -> None:
        self.runtime_root = _validate_runtime_root(Path(runtime_root))

    def close(
        self,
        evidence: Mapping[str, object],
        *,
        observed_at: str | None = None,
    ) -> ReleaseCandidateFinalSignoffReceipt:
        if not isinstance(evidence, Mapping):
            raise ReleaseCandidateFinalSignoffError("evidence_must_be_mapping")
        observed = _timestamp(observed_at)
        data = _json_ready(evidence)
        if not isinstance(data, Mapping):
            raise ReleaseCandidateFinalSignoffError("evidence_must_be_mapping")

        gate_results = self._evaluate_gates(data)
        failures = tuple(
            failure
            for gate in gate_results
            if not gate.accepted
            for failure in gate.failures
        )
        report_material = self._build_report_material(data, gate_results, failures)
        final_signoff_report_hash = _sha256_json(report_material["final_signoff_report"])
        final_system_status_report_hash = _sha256_json(report_material["final_system_status_report"])
        evidence_chain_hash = _sha256_json(
            {
                "gate_hashes": tuple(gate.gate_hash for gate in gate_results),
                "final_signoff_report_hash": final_signoff_report_hash,
                "final_system_status_report_hash": final_system_status_report_hash,
            }
        )
        wal_record_hash = self._append_wal(
            accepted=not failures,
            evidence_chain_hash=evidence_chain_hash,
            final_signoff_report_hash=final_signoff_report_hash,
            final_system_status_report_hash=final_system_status_report_hash,
            observed_at=observed,
            run_id=_string_field(data, "signoff_id", "release-candidate-final-signoff-529"),
        )
        receipt = ReleaseCandidateFinalSignoffReceipt(
            integration_version=RELEASE_CANDIDATE_FINAL_SIGNOFF_VERSION,
            accepted=not failures,
            failures=failures,
            signoff_id=_string_field(data, "signoff_id", "release-candidate-final-signoff-529"),
            repository_url=_string_field(data, "repository_url", "https://github.com/qqyqqyqqy666-wq/sovereign-engineering-os"),
            main_head=_string_field(data, "main_head", "unknown"),
            branch=_string_field(data, "branch", "codex/529-release-candidate-final-signoff-v1"),
            release_tag_proposal=_string_field(data, "release_tag_proposal", "v0.1.0-rc.529"),
            final_verdict=_string_field(data, "final_verdict", _FINAL_VERDICT),
            gate_results=gate_results,
            version_tuple_hash=_sha256_json(data.get("version_tuple", {})),
            schema_freeze_hash=_sha256_json(data.get("schema_freeze", {})),
            acceptance_matrix_hash=_sha256_json(data.get("acceptance_matrix", {})),
            invariant_sweep_hash=_sha256_json(data.get("invariant_sweep", {})),
            docs_alignment_hash=_sha256_json(data.get("docs_runbook_alignment", {})),
            cleanup_evidence_hash=_sha256_json(data.get("cleanup_status", {})),
            priority_status_matrix_hash=_sha256_json(data.get("priority_status_matrix", {})),
            final_signoff_report_hash=final_signoff_report_hash,
            final_system_status_report_hash=final_system_status_report_hash,
            evidence_chain_hash=evidence_chain_hash,
            wal_record_hash=wal_record_hash,
            rollback_recovery_link=_string_field(data, "rollback_recovery_link", ""),
            e2e_acceptance_link=_string_field(data, "e2e_acceptance_link", ""),
            security_hardening_link=_string_field(data, "security_hardening_link", ""),
            observed_at=observed,
        )
        self._persist_reports(receipt, report_material)
        return receipt

    def _evaluate_gates(self, data: Mapping[str, object]) -> tuple[ReleaseCandidateGateResult, ...]:
        gates = {
            "version_tuple_freeze": self._version_tuple_failures(data),
            "schema_freeze_check": self._schema_freeze_failures(data),
            "acceptance_matrix": self._acceptance_matrix_failures(data),
            "invariant_sweep": self._invariant_sweep_failures(data),
            "docs_runbook_alignment": self._docs_alignment_failures(data),
            "stale_pr_body_docs_cleanup": self._cleanup_gate_failures(
                data,
                (
                    "stale_pr_body_text_removed",
                    "stale_docs_aligned",
                    "single_priority_scope_confirmed",
                ),
            ),
            "no_todo_as_implementation": self._negative_cleanup_failures(
                data,
                "todo_as_implementation_found",
            ),
            "no_placeholder_blockers": self._negative_cleanup_failures(
                data,
                "placeholder_blockers_hidden",
            ),
            "no_known_untriaged_blocker": self._untriaged_blocker_failures(data),
            "full_test_suite_green": self._full_test_suite_failures(data),
            "ci_green": self._ci_failures(data),
            "local_worktree_clean": self._worktree_failures(data),
            "release_tag_proposal": self._release_tag_failures(data),
            "final_signoff_report": self._final_signoff_report_failures(data),
            "final_system_status_report": self._final_status_report_failures(data),
            "rollback_recovery_linked": self._exact_link_failures(
                data,
                "rollback_recovery_link",
                _REQUIRED_DOC_LINKS["rollback_recovery_link"],
            ),
            "e2e_acceptance_linked": self._exact_link_failures(
                data,
                "e2e_acceptance_link",
                _REQUIRED_DOC_LINKS["e2e_acceptance_link"],
            ),
            "security_hardening_linked": self._exact_link_failures(
                data,
                "security_hardening_link",
                _REQUIRED_DOC_LINKS["security_hardening_link"],
            ),
            "priority_matrix_closed": self._priority_matrix_failures(data),
        }
        return tuple(
            ReleaseCandidateGateResult(
                gate_id=gate_id,
                accepted=not gates[gate_id],
                failures=gates[gate_id],
                evidence_hash=_sha256_json({"gate_id": gate_id, "evidence": _gate_evidence(data, gate_id)}),
            )
            for gate_id in _REQUIRED_GATE_IDS
        )

    def _version_tuple_failures(self, data: Mapping[str, object]) -> tuple[str, ...]:
        version_tuple = data.get("version_tuple")
        if not isinstance(version_tuple, Mapping):
            return ("version_tuple_required",)
        failures = []
        expected = {
            "product": "sovereign-engineering-os",
            "release_candidate": "0.1.0-rc.529",
            "priority_range": "#517-#529",
            "schema_bundle": "schema-freeze-v1",
        }
        for key, expected_value in expected.items():
            if version_tuple.get(key) != expected_value:
                failures.append("version_tuple_mismatch:" + key)
        if version_tuple.get("frozen") is not True:
            failures.append("version_tuple_frozen_true_required")
        return tuple(_dedupe(failures))

    def _schema_freeze_failures(self, data: Mapping[str, object]) -> tuple[str, ...]:
        schema_freeze = data.get("schema_freeze")
        if not isinstance(schema_freeze, Mapping):
            return ("schema_freeze_required",)
        failures = []
        if schema_freeze.get("status") != "frozen":
            failures.append("schema_freeze_status_frozen_required")
        if schema_freeze.get("unknown_schema_rejected") is not True:
            failures.append("unknown_schema_rejected_required")
        if schema_freeze.get("schema_drift_detected") is not False:
            failures.append("schema_drift_detected_must_be_false")
        changed = schema_freeze.get("changed_schema_files")
        if not isinstance(changed, Sequence) or isinstance(changed, (str, bytes)):
            failures.append("changed_schema_files_list_required")
        elif changed:
            failures.append("changed_schema_files_must_be_empty")
        return tuple(_dedupe(failures))

    def _acceptance_matrix_failures(self, data: Mapping[str, object]) -> tuple[str, ...]:
        matrix = data.get("acceptance_matrix")
        if not isinstance(matrix, Mapping):
            return ("acceptance_matrix_required",)
        failures = []
        for key in _REQUIRED_ACCEPTANCE_KEYS:
            if _normalized_status(matrix.get(key)) not in _GREEN_VALUES:
                failures.append("acceptance_matrix_not_green:" + key)
        return tuple(_dedupe(failures))

    def _invariant_sweep_failures(self, data: Mapping[str, object]) -> tuple[str, ...]:
        sweep = data.get("invariant_sweep")
        if not isinstance(sweep, Mapping):
            return ("invariant_sweep_required",)
        failures = []
        for invariant in _REQUIRED_INVARIANTS:
            if sweep.get(invariant) is not True:
                failures.append("invariant_not_confirmed:" + invariant)
        return tuple(_dedupe(failures))

    def _docs_alignment_failures(self, data: Mapping[str, object]) -> tuple[str, ...]:
        alignment = data.get("docs_runbook_alignment")
        if not isinstance(alignment, Mapping):
            return ("docs_runbook_alignment_required",)
        failures = []
        expected = {**_REQUIRED_DOC_LINKS, **_REQUIRED_AUDIT_LINKS}
        for key, expected_value in expected.items():
            if alignment.get(key) != expected_value:
                failures.append("docs_alignment_missing:" + key)
        if alignment.get("runbooks_match_runtime_boundaries") is not True:
            failures.append("runbooks_match_runtime_boundaries_required")
        if alignment.get("audit_notes_match_validation") is not True:
            failures.append("audit_notes_match_validation_required")
        return tuple(_dedupe(failures))

    def _cleanup_gate_failures(
        self,
        data: Mapping[str, object],
        required_true_flags: Sequence[str],
    ) -> tuple[str, ...]:
        cleanup = data.get("cleanup_status")
        if not isinstance(cleanup, Mapping):
            return ("cleanup_status_required",)
        return tuple(
            "cleanup_flag_not_confirmed:" + flag
            for flag in required_true_flags
            if cleanup.get(flag) is not True
        )

    def _negative_cleanup_failures(self, data: Mapping[str, object], flag: str) -> tuple[str, ...]:
        cleanup = data.get("cleanup_status")
        if not isinstance(cleanup, Mapping):
            return ("cleanup_status_required",)
        if cleanup.get(flag) is not False:
            return (flag + "_must_be_false",)
        return ()

    def _untriaged_blocker_failures(self, data: Mapping[str, object]) -> tuple[str, ...]:
        failures = list(self._negative_cleanup_failures(data, "known_untriaged_blockers"))
        blockers = data.get("known_blockers")
        if not isinstance(blockers, list):
            failures.append("known_blockers_list_required")
        elif blockers:
            failures.append("known_blockers_must_be_empty")
        return tuple(_dedupe(failures))

    def _full_test_suite_failures(self, data: Mapping[str, object]) -> tuple[str, ...]:
        failures = list(self._acceptance_matrix_failures(data))
        commands = data.get("validation_commands")
        if not isinstance(commands, list) or not commands:
            failures.append("validation_commands_required")
        else:
            command_statuses = {
                item.get("command"): _normalized_status(item.get("status"))
                for item in commands
                if isinstance(item, Mapping)
            }
            for required in (
                "PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests/tracer_bullet",
                "PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover tests",
                "make ci",
                "git diff --check",
                "git status --short",
            ):
                if command_statuses.get(required) not in _GREEN_VALUES:
                    failures.append("validation_command_not_green:" + required)
        return tuple(_dedupe(failures))

    def _ci_failures(self, data: Mapping[str, object]) -> tuple[str, ...]:
        ci_status = data.get("ci_status")
        if not isinstance(ci_status, Mapping):
            return ("ci_status_required",)
        if _normalized_status(ci_status.get("canonical-health")) != "success":
            return ("canonical_health_success_required",)
        return ()

    def _worktree_failures(self, data: Mapping[str, object]) -> tuple[str, ...]:
        worktree = data.get("worktree_status")
        if not isinstance(worktree, Mapping):
            return ("worktree_status_required",)
        failures = []
        if _normalized_status(worktree.get("git_diff_check")) != "clean":
            failures.append("git_diff_check_clean_required")
        if _normalized_status(worktree.get("git_status_short")) != "clean":
            failures.append("git_status_short_clean_required")
        return tuple(_dedupe(failures))

    def _release_tag_failures(self, data: Mapping[str, object]) -> tuple[str, ...]:
        release_tag = data.get("release_tag_proposal")
        if not isinstance(release_tag, str) or not _RELEASE_TAG_PATTERN.match(release_tag):
            return ("release_tag_proposal_invalid",)
        if data.get("release_tag_created") is True:
            return ("release_tag_must_be_proposal_only",)
        return ()

    def _final_signoff_report_failures(self, data: Mapping[str, object]) -> tuple[str, ...]:
        failures = []
        if data.get("final_verdict") != _FINAL_VERDICT:
            failures.append("final_verdict_ready_required")
        if data.get("final_signoff_report_ready") is not True:
            failures.append("final_signoff_report_ready_required")
        return tuple(_dedupe(failures))

    def _final_status_report_failures(self, data: Mapping[str, object]) -> tuple[str, ...]:
        failures = list(self._priority_matrix_failures(data))
        if data.get("final_system_status_report_ready") is not True:
            failures.append("final_system_status_report_ready_required")
        return tuple(_dedupe(failures))

    def _exact_link_failures(
        self,
        data: Mapping[str, object],
        field_name: str,
        expected: str,
    ) -> tuple[str, ...]:
        if data.get(field_name) != expected:
            return (field_name + "_invalid",)
        return ()

    def _priority_matrix_failures(self, data: Mapping[str, object]) -> tuple[str, ...]:
        matrix = data.get("priority_status_matrix")
        if not isinstance(matrix, Mapping):
            return ("priority_status_matrix_required",)
        failures = []
        for priority_id in _PRIORITY_IDS:
            if matrix.get(priority_id) != _MERGED_STATUS:
                failures.append("priority_not_post_merge_validated:" + priority_id)
        return tuple(_dedupe(failures))

    def _build_report_material(
        self,
        data: Mapping[str, object],
        gate_results: tuple[ReleaseCandidateGateResult, ...],
        failures: tuple[str, ...],
    ) -> dict[str, object]:
        gate_summary = tuple(gate.as_dict() for gate in gate_results)
        final_signoff_report = {
            "signoff_id": _string_field(data, "signoff_id", "release-candidate-final-signoff-529"),
            "repository_url": _string_field(data, "repository_url", "https://github.com/qqyqqyqqy666-wq/sovereign-engineering-os"),
            "main_head": _string_field(data, "main_head", "unknown"),
            "branch": _string_field(data, "branch", "codex/529-release-candidate-final-signoff-v1"),
            "release_tag_proposal": _string_field(data, "release_tag_proposal", "v0.1.0-rc.529"),
            "accepted": not failures,
            "failures": failures,
            "final_verdict": _string_field(data, "final_verdict", _FINAL_VERDICT),
            "gate_hashes": tuple(gate.gate_hash for gate in gate_results),
            "rollback_recovery_link": _string_field(data, "rollback_recovery_link", ""),
            "e2e_acceptance_link": _string_field(data, "e2e_acceptance_link", ""),
            "security_hardening_link": _string_field(data, "security_hardening_link", ""),
        }
        final_system_status_report = {
            "priority_status_matrix": data.get("priority_status_matrix", {}),
            "acceptance_matrix_hash": _sha256_json(data.get("acceptance_matrix", {})),
            "docs_alignment_hash": _sha256_json(data.get("docs_runbook_alignment", {})),
            "gate_summary": gate_summary,
            "known_blockers": data.get("known_blockers", []),
        }
        return {
            "final_signoff_report": _json_ready(final_signoff_report),
            "final_system_status_report": _json_ready(final_system_status_report),
        }

    def _append_wal(
        self,
        *,
        accepted: bool,
        evidence_chain_hash: str,
        final_signoff_report_hash: str,
        final_system_status_report_hash: str,
        observed_at: str,
        run_id: str,
    ) -> str:
        wal_path = self._resolve_relpath(_WAL_RELPATH, "wal_relpath")
        wal_path.parent.mkdir(parents=True, exist_ok=True)
        material = {
            "accepted": accepted,
            "evidence_chain_hash": evidence_chain_hash,
            "final_signoff_report_hash": final_signoff_report_hash,
            "final_system_status_report_hash": final_system_status_report_hash,
        }
        return FileBackedRealWalStorage(wal_path).append(
            record_type="SYSTEM_ACCEPTANCE_EVENT",
            task_id=_TASK_ID,
            run_id=run_id,
            payload_hash=_sha256_json(material),
            digest_bindings={
                "evidence_chain_hash": evidence_chain_hash,
                "final_signoff_report_hash": final_signoff_report_hash,
                "final_system_status_report_hash": final_system_status_report_hash,
            },
            created_at=observed_at,
        ).record_hash

    def _persist_reports(
        self,
        receipt: ReleaseCandidateFinalSignoffReceipt,
        report_material: Mapping[str, object],
    ) -> None:
        self._write_new_json(_SIGNOFF_REPORT_RELPATH, report_material["final_signoff_report"])
        self._write_new_json(_SYSTEM_STATUS_REPORT_RELPATH, report_material["final_system_status_report"])
        receipt_relpath = _RECEIPT_DIR_RELPATH + "/" + receipt.receipt_hash.removeprefix("sha256:") + ".json"
        self._write_new_json(receipt_relpath, receipt.as_dict())

    def _write_new_json(self, relpath: str, payload: object) -> None:
        path = self._resolve_relpath(relpath, "report_relpath")
        if path.exists():
            raise ReleaseCandidateFinalSignoffError("report_already_exists")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(_json_ready(payload), sort_keys=True, indent=2, ensure_ascii=True) + "\n",
            encoding="utf-8",
        )

    def _resolve_relpath(self, relpath: str, field_name: str) -> Path:
        if not isinstance(relpath, str) or not relpath:
            raise ReleaseCandidateFinalSignoffError(field_name + "_must_be_nonempty_string")
        if "\\" in relpath:
            raise ReleaseCandidateFinalSignoffError(field_name + "_backslash_forbidden")
        pure = PurePosixPath(relpath)
        if pure.is_absolute() or ".." in pure.parts:
            raise ReleaseCandidateFinalSignoffError(field_name + "_must_stay_under_runtime_root")
        path = (self.runtime_root / pure).resolve(strict=False)
        root = self.runtime_root.resolve()
        if path != root and root not in path.parents:
            raise ReleaseCandidateFinalSignoffError(field_name + "_escapes_runtime_root")
        return path


def compute_release_candidate_gate_result_hash(gate: ReleaseCandidateGateResult) -> str:
    return _sha256_json(
        {
            "accepted": gate.accepted,
            "evidence_hash": gate.evidence_hash,
            "failures": gate.failures,
            "gate_id": gate.gate_id,
        }
    )


def compute_release_candidate_final_signoff_receipt_hash(
    receipt: ReleaseCandidateFinalSignoffReceipt,
) -> str:
    return _sha256_json(receipt.deterministic_material())


def _gate_evidence(data: Mapping[str, object], gate_id: str) -> object:
    if gate_id == "version_tuple_freeze":
        return data.get("version_tuple", {})
    if gate_id == "schema_freeze_check":
        return data.get("schema_freeze", {})
    if gate_id in {
        "acceptance_matrix",
        "full_test_suite_green",
        "local_worktree_clean",
    }:
        return {
            "acceptance_matrix": data.get("acceptance_matrix", {}),
            "validation_commands": data.get("validation_commands", []),
            "worktree_status": data.get("worktree_status", {}),
        }
    if gate_id == "invariant_sweep":
        return data.get("invariant_sweep", {})
    if gate_id in {
        "docs_runbook_alignment",
        "rollback_recovery_linked",
        "e2e_acceptance_linked",
        "security_hardening_linked",
    }:
        return {
            "docs_runbook_alignment": data.get("docs_runbook_alignment", {}),
            "rollback_recovery_link": data.get("rollback_recovery_link", ""),
            "e2e_acceptance_link": data.get("e2e_acceptance_link", ""),
            "security_hardening_link": data.get("security_hardening_link", ""),
        }
    if gate_id in {
        "stale_pr_body_docs_cleanup",
        "no_todo_as_implementation",
        "no_placeholder_blockers",
        "no_known_untriaged_blocker",
    }:
        return {
            "cleanup_status": data.get("cleanup_status", {}),
            "known_blockers": data.get("known_blockers", []),
        }
    if gate_id == "ci_green":
        return data.get("ci_status", {})
    if gate_id == "release_tag_proposal":
        return {
            "release_tag_proposal": data.get("release_tag_proposal", ""),
            "release_tag_created": data.get("release_tag_created", False),
        }
    if gate_id == "final_signoff_report":
        return {
            "final_signoff_report_ready": data.get("final_signoff_report_ready", False),
            "final_verdict": data.get("final_verdict", ""),
        }
    if gate_id in {"final_system_status_report", "priority_matrix_closed"}:
        return {
            "final_system_status_report_ready": data.get("final_system_status_report_ready", False),
            "priority_status_matrix": data.get("priority_status_matrix", {}),
        }
    return data


def _timestamp(value: str | None) -> str:
    if value is None:
        return datetime.now(timezone.utc).isoformat()
    _require_nonempty_string(value, "observed_at")
    return value


def _validate_runtime_root(path: Path) -> Path:
    if not isinstance(path, Path):
        raise ReleaseCandidateFinalSignoffError("runtime_root_must_be_path")
    resolved = path.resolve(strict=False)
    resolved.mkdir(parents=True, exist_ok=True)
    return resolved


def _json_ready(value: object) -> object:
    try:
        return json.loads(
            json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)
        )
    except (TypeError, ValueError) as exc:
        raise ReleaseCandidateFinalSignoffError("value_must_be_json_serializable") from exc


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
        raise ReleaseCandidateFinalSignoffError(field_name + "_must_be_nonempty_string")


def _require_sha256(value: object, field_name: str) -> None:
    if not isinstance(value, str) or not _SHA256_PATTERN.match(value):
        raise ReleaseCandidateFinalSignoffError(field_name + "_must_be_sha256")


def _string_field(data: Mapping[str, object], field_name: str, default: str) -> str:
    value = data.get(field_name, default)
    if not isinstance(value, str) or not value.strip():
        raise ReleaseCandidateFinalSignoffError(field_name + "_must_be_nonempty_string")
    return value


def _normalize_failures(values: Sequence[str]) -> tuple[str, ...]:
    if not isinstance(values, Sequence) or isinstance(values, (str, bytes)):
        raise ReleaseCandidateFinalSignoffError("failures_must_be_sequence")
    normalized = tuple(str(value) for value in values)
    for value in normalized:
        _require_nonempty_string(value, "failure")
    return tuple(_dedupe(normalized))


def _normalize_gate_results(
    values: Sequence[ReleaseCandidateGateResult],
) -> tuple[ReleaseCandidateGateResult, ...]:
    if not isinstance(values, Sequence) or isinstance(values, (str, bytes)):
        raise ReleaseCandidateFinalSignoffError("gate_results_must_be_sequence")
    normalized = tuple(values)
    gate_ids = tuple(gate.gate_id for gate in normalized)
    if gate_ids != _REQUIRED_GATE_IDS:
        raise ReleaseCandidateFinalSignoffError("gate_results_order_invalid")
    return normalized


def _install_or_verify_hash(
    instance: object,
    field_name: str,
    compute,
) -> None:
    current = getattr(instance, field_name)
    expected = compute(instance)
    if current in ("", None):
        object.__setattr__(instance, field_name, expected)
        return
    if current != expected:
        raise ReleaseCandidateFinalSignoffError(field_name + "_mismatch")


def _normalized_status(value: object) -> str:
    if isinstance(value, str):
        return value.strip().lower()
    return ""


def _dedupe(values: Sequence[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    output: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            output.append(value)
    return tuple(output)
