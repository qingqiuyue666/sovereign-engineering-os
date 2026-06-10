"""Independent Final Signoff Verification Harness V1.

This verifier consumes local #529 release signoff artifacts plus immutable
caller-supplied evidence snapshots. It performs no network calls, does not
shell out to git, and only reads local JSON artifacts plus the repository HEAD
metadata needed to bind the verification to a checked-out commit.
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
    "INDEPENDENT_FINAL_SIGNOFF_VERIFICATION_VERSION",
    "ZERO_HASH",
    "FileBackedIndependentFinalSignoffVerification",
    "IndependentFinalSignoffVerificationError",
    "IndependentFinalSignoffVerificationReceipt",
    "compute_independent_evidence_snapshot_hash",
    "compute_independent_final_signoff_verification_receipt_hash",
]

INDEPENDENT_FINAL_SIGNOFF_VERIFICATION_VERSION = (
    "independent_final_signoff_verification_v1"
)
ZERO_HASH = "sha256:" + ("0" * 64)

_TASK_ID = "task-530-independent-final-signoff-verification"
_FINAL_SIGNOFF_VERSION = "release_candidate_final_signoff_v1"
_FINAL_VERDICT = "READY_TO_REVIEW_AND_MERGE"
_MERGED_STATUS = "merged and post-merge validated"
_WAL_RELPATH = (
    "independent-final-signoff-verification/verification.real-wal.jsonl"
)
_REPORT_DIR_RELPATH = "independent-final-signoff-verification/reports"
_REPORT_RELPATH = _REPORT_DIR_RELPATH + "/independent-verification-report.json"
_RECEIPT_DIR_RELPATH = "independent-final-signoff-verification/receipts"
_PRIORITY_IDS = tuple(f"#{number}" for number in range(517, 530))
_REQUIRED_RUNBOOK_LINKS = (
    "docs/runbooks/recovery_rollback_disaster_procedure_v1.md",
    "docs/runbooks/system_e2e_acceptance_v1.md",
    "docs/runbooks/security_abuse_boundary_hardening_v1.md",
)
_REQUIRED_VALIDATION_COMMANDS = (
    "PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests/tracer_bullet",
    "PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s validation/tests/acceptance",
    "PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover tests",
    "make ci",
    "git diff --check",
    "git status --short",
)
_GREEN_VALUES = frozenset({"green", "ok", "success", "clean", "passed"})
_SHA256_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")
_HEAD_PATTERN = re.compile(r"^[0-9a-f]{40}$")
_RELEASE_TAG_PATTERN = re.compile(r"^v\d+\.\d+\.\d+-rc\.529(?:\+[0-9a-f]{7,40})?$")


class IndependentFinalSignoffVerificationError(ValueError):
    """Raised when independent verification evidence is malformed."""


@dataclass(frozen=True)
class IndependentFinalSignoffVerificationReceipt:
    integration_version: str
    accepted: bool
    failures: tuple[str, ...]
    verification_id: str
    expected_main_head: str
    current_repo_head: str
    final_signoff_receipt_hash: str
    final_signoff_report_hash: str
    final_system_status_report_hash: str
    signoff_evidence_chain_hash: str
    priority_status_matrix_hash: str
    pr_status_snapshot_bundle_hash: str
    validation_transcript_bundle_hash: str
    ci_snapshot_bundle_hash: str
    worktree_evidence_hash: str
    release_tag_evidence_hash: str
    linked_runbook_hash: str
    wal_record_hash: str
    observed_at: str
    receipt_hash: str = ""

    def __post_init__(self) -> None:
        if self.integration_version != INDEPENDENT_FINAL_SIGNOFF_VERIFICATION_VERSION:
            raise IndependentFinalSignoffVerificationError(
                "integration_version_invalid"
            )
        if not isinstance(self.accepted, bool):
            raise IndependentFinalSignoffVerificationError("accepted_must_be_bool")
        object.__setattr__(self, "failures", _normalize_failures(self.failures))
        for field_name in ("verification_id", "observed_at"):
            _require_nonempty_string(getattr(self, field_name), field_name)
        for field_name in ("expected_main_head", "current_repo_head"):
            _require_head(getattr(self, field_name), field_name)
        for field_name in (
            "final_signoff_receipt_hash",
            "final_signoff_report_hash",
            "final_system_status_report_hash",
            "signoff_evidence_chain_hash",
            "priority_status_matrix_hash",
            "pr_status_snapshot_bundle_hash",
            "validation_transcript_bundle_hash",
            "ci_snapshot_bundle_hash",
            "worktree_evidence_hash",
            "release_tag_evidence_hash",
            "linked_runbook_hash",
            "wal_record_hash",
        ):
            _require_sha256(getattr(self, field_name), field_name)
        expected_acceptance = (
            not self.failures
            and self.expected_main_head == self.current_repo_head
            and self.wal_record_hash != ZERO_HASH
        )
        if self.accepted != expected_acceptance:
            raise IndependentFinalSignoffVerificationError(
                "accepted_must_match_verification_evidence"
            )
        _install_or_verify_hash(
            self,
            "receipt_hash",
            compute_independent_final_signoff_verification_receipt_hash,
        )

    def deterministic_material(self) -> dict[str, object]:
        return {
            "accepted": self.accepted,
            "ci_snapshot_bundle_hash": self.ci_snapshot_bundle_hash,
            "current_repo_head": self.current_repo_head,
            "expected_main_head": self.expected_main_head,
            "failures": self.failures,
            "final_signoff_receipt_hash": self.final_signoff_receipt_hash,
            "final_signoff_report_hash": self.final_signoff_report_hash,
            "final_system_status_report_hash": self.final_system_status_report_hash,
            "integration_version": self.integration_version,
            "linked_runbook_hash": self.linked_runbook_hash,
            "observed_at": self.observed_at,
            "pr_status_snapshot_bundle_hash": self.pr_status_snapshot_bundle_hash,
            "priority_status_matrix_hash": self.priority_status_matrix_hash,
            "release_tag_evidence_hash": self.release_tag_evidence_hash,
            "signoff_evidence_chain_hash": self.signoff_evidence_chain_hash,
            "validation_transcript_bundle_hash": self.validation_transcript_bundle_hash,
            "verification_id": self.verification_id,
            "wal_record_hash": self.wal_record_hash,
            "worktree_evidence_hash": self.worktree_evidence_hash,
        }

    def as_dict(self) -> dict[str, object]:
        payload = self.deterministic_material()
        payload["receipt_hash"] = self.receipt_hash
        return _json_ready(payload)  # type: ignore[return-value]


class FileBackedIndependentFinalSignoffVerification:
    """Local, file-backed independent verification for #529 signoff evidence."""

    def __init__(self, *, runtime_root: str | Path, repo_root: str | Path) -> None:
        self.runtime_root = _validate_runtime_root(Path(runtime_root))
        self.repo_root = Path(repo_root).resolve(strict=False)

    def verify(
        self,
        evidence: Mapping[str, object],
        *,
        observed_at: str | None = None,
    ) -> IndependentFinalSignoffVerificationReceipt:
        if not isinstance(evidence, Mapping):
            raise IndependentFinalSignoffVerificationError(
                "evidence_must_be_mapping"
            )
        observed = _timestamp(observed_at)
        data = _json_ready(evidence)
        if not isinstance(data, Mapping):
            raise IndependentFinalSignoffVerificationError(
                "evidence_must_be_mapping"
            )

        verification_id = _string_field(
            data,
            "verification_id",
            "independent-final-signoff-verification-530",
        )
        receipt = self._load_required_json(
            data, "final_signoff_receipt_relpath"
        )
        signoff_report = self._load_required_json(
            data, "final_signoff_report_relpath"
        )
        status_report = self._load_required_json(
            data, "final_system_status_report_relpath"
        )
        current_head = _current_repo_head(data, self.repo_root)
        expected_head = _string_field(data, "expected_main_head", "")

        failures: list[str] = []
        failures.extend(
            self._signoff_artifact_failures(
                receipt=receipt,
                signoff_report=signoff_report,
                status_report=status_report,
            )
        )
        failures.extend(
            _head_failures(
                expected_head=expected_head,
                current_head=current_head,
                receipt=receipt,
                signoff_report=signoff_report,
            )
        )
        failures.extend(
            _priority_snapshot_failures(
                status_report=status_report,
                snapshots=data.get("pr_status_snapshots"),
                observed_at=observed,
            )
        )
        failures.extend(
            _validation_transcript_failures(
                data.get("validation_transcripts"),
                observed_at=observed,
            )
        )
        failures.extend(
            _ci_snapshot_failures(
                data.get("ci_status_snapshots", ()),
                observed_at=observed,
            )
        )
        failures.extend(_worktree_evidence_failures(data.get("worktree_evidence")))
        failures.extend(
            _release_tag_evidence_failures(
                data.get("release_tag_evidence"),
                receipt=receipt,
                signoff_report=signoff_report,
            )
        )
        failures.extend(self._linked_runbook_failures(receipt))

        final_signoff_receipt_hash = _sha256_json(receipt)
        final_signoff_report_hash = _sha256_json(signoff_report)
        final_system_status_report_hash = _sha256_json(status_report)
        signoff_evidence_chain_hash = _sha256_json(
            {
                "final_signoff_report_hash": final_signoff_report_hash,
                "final_system_status_report_hash": final_system_status_report_hash,
                "gate_hashes": _gate_hashes(receipt),
            }
        )
        priority_status_matrix_hash = _sha256_json(
            _status_matrix_from_report(status_report)
        )
        pr_status_snapshot_bundle_hash = _snapshot_bundle_hash(
            data.get("pr_status_snapshots", ())
        )
        validation_transcript_bundle_hash = _snapshot_bundle_hash(
            data.get("validation_transcripts", ())
        )
        ci_snapshot_bundle_hash = _snapshot_bundle_hash(
            data.get("ci_status_snapshots", ())
        )
        worktree_evidence_hash = _sha256_json(data.get("worktree_evidence", {}))
        release_tag_evidence_hash = _sha256_json(
            data.get("release_tag_evidence", {})
        )
        linked_runbook_hash = _sha256_json(
            {
                "e2e_acceptance_link": receipt.get("e2e_acceptance_link"),
                "rollback_recovery_link": receipt.get("rollback_recovery_link"),
                "security_hardening_link": receipt.get("security_hardening_link"),
            }
        )

        unique_failures = _dedupe(failures)
        wal_record_hash = self._append_wal(
            accepted=not unique_failures,
            verification_id=verification_id,
            final_signoff_receipt_hash=final_signoff_receipt_hash,
            signoff_evidence_chain_hash=signoff_evidence_chain_hash,
            pr_status_snapshot_bundle_hash=pr_status_snapshot_bundle_hash,
            validation_transcript_bundle_hash=validation_transcript_bundle_hash,
            ci_snapshot_bundle_hash=ci_snapshot_bundle_hash,
            observed_at=observed,
        )
        verification_receipt = IndependentFinalSignoffVerificationReceipt(
            integration_version=INDEPENDENT_FINAL_SIGNOFF_VERIFICATION_VERSION,
            accepted=not unique_failures,
            failures=unique_failures,
            verification_id=verification_id,
            expected_main_head=expected_head,
            current_repo_head=current_head,
            final_signoff_receipt_hash=final_signoff_receipt_hash,
            final_signoff_report_hash=final_signoff_report_hash,
            final_system_status_report_hash=final_system_status_report_hash,
            signoff_evidence_chain_hash=signoff_evidence_chain_hash,
            priority_status_matrix_hash=priority_status_matrix_hash,
            pr_status_snapshot_bundle_hash=pr_status_snapshot_bundle_hash,
            validation_transcript_bundle_hash=validation_transcript_bundle_hash,
            ci_snapshot_bundle_hash=ci_snapshot_bundle_hash,
            worktree_evidence_hash=worktree_evidence_hash,
            release_tag_evidence_hash=release_tag_evidence_hash,
            linked_runbook_hash=linked_runbook_hash,
            wal_record_hash=wal_record_hash,
            observed_at=observed,
        )
        self._persist_outputs(verification_receipt, receipt, signoff_report, status_report)
        return verification_receipt

    def _signoff_artifact_failures(
        self,
        *,
        receipt: Mapping[str, object],
        signoff_report: Mapping[str, object],
        status_report: Mapping[str, object],
    ) -> tuple[str, ...]:
        failures: list[str] = []
        if receipt.get("integration_version") != _FINAL_SIGNOFF_VERSION:
            failures.append("final_signoff_receipt_version_invalid")
        if receipt.get("accepted") is not True:
            failures.append("final_signoff_receipt_not_accepted")
        if signoff_report.get("accepted") is not True:
            failures.append("final_signoff_report_not_accepted")
        if receipt.get("final_verdict") != _FINAL_VERDICT:
            failures.append("final_signoff_receipt_verdict_not_ready")
        if signoff_report.get("final_verdict") != _FINAL_VERDICT:
            failures.append("final_signoff_report_verdict_not_ready")
        if receipt.get("final_verdict") != signoff_report.get("final_verdict"):
            failures.append("contradictory_final_verdict")
        if receipt.get("release_tag_proposal") != signoff_report.get(
            "release_tag_proposal"
        ):
            failures.append("release_tag_proposal_contradiction")
        report_hash = _sha256_json(signoff_report)
        status_hash = _sha256_json(status_report)
        if receipt.get("final_signoff_report_hash") != report_hash:
            failures.append("final_signoff_report_hash_mismatch")
        if receipt.get("final_system_status_report_hash") != status_hash:
            failures.append("final_system_status_report_hash_mismatch")
        expected_chain = _sha256_json(
            {
                "final_signoff_report_hash": report_hash,
                "final_system_status_report_hash": status_hash,
                "gate_hashes": _gate_hashes(receipt),
            }
        )
        if receipt.get("evidence_chain_hash") != expected_chain:
            failures.append("signoff_evidence_chain_hash_mismatch")
        matrix = _status_matrix_from_report(status_report)
        for priority_id in _PRIORITY_IDS:
            if matrix.get(priority_id) != _MERGED_STATUS:
                failures.append("priority_not_post_merge_validated:" + priority_id)
        return tuple(_dedupe(failures))

    def _linked_runbook_failures(
        self, receipt: Mapping[str, object]
    ) -> tuple[str, ...]:
        failures: list[str] = []
        links = (
            receipt.get("rollback_recovery_link"),
            receipt.get("e2e_acceptance_link"),
            receipt.get("security_hardening_link"),
        )
        for expected, actual in zip(_REQUIRED_RUNBOOK_LINKS, links):
            if actual != expected:
                failures.append("linked_runbook_path_mismatch:" + expected)
                continue
            path = (self.repo_root / expected).resolve(strict=False)
            if not path.is_file() or self.repo_root.resolve() not in path.parents:
                failures.append("linked_runbook_missing:" + expected)
        return tuple(_dedupe(failures))

    def _load_required_json(
        self,
        evidence: Mapping[str, object],
        field_name: str,
    ) -> Mapping[str, object]:
        relpath = _string_field(evidence, field_name, "")
        path = self._resolve_relpath(relpath, field_name)
        if not path.is_file():
            raise IndependentFinalSignoffVerificationError(
                field_name + "_missing"
            )
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise IndependentFinalSignoffVerificationError(
                field_name + "_invalid_json"
            ) from exc
        if not isinstance(payload, Mapping):
            raise IndependentFinalSignoffVerificationError(
                field_name + "_must_be_json_object"
            )
        return _json_ready(payload)  # type: ignore[return-value]

    def _append_wal(
        self,
        *,
        accepted: bool,
        verification_id: str,
        final_signoff_receipt_hash: str,
        signoff_evidence_chain_hash: str,
        pr_status_snapshot_bundle_hash: str,
        validation_transcript_bundle_hash: str,
        ci_snapshot_bundle_hash: str,
        observed_at: str,
    ) -> str:
        wal_path = self._resolve_relpath(_WAL_RELPATH, "wal_relpath")
        wal_path.parent.mkdir(parents=True, exist_ok=True)
        material = {
            "accepted": accepted,
            "ci_snapshot_bundle_hash": ci_snapshot_bundle_hash,
            "final_signoff_receipt_hash": final_signoff_receipt_hash,
            "pr_status_snapshot_bundle_hash": pr_status_snapshot_bundle_hash,
            "signoff_evidence_chain_hash": signoff_evidence_chain_hash,
            "validation_transcript_bundle_hash": validation_transcript_bundle_hash,
        }
        return FileBackedRealWalStorage(wal_path).append(
            record_type="SYSTEM_ACCEPTANCE_EVENT",
            task_id=_TASK_ID,
            run_id=verification_id,
            payload_hash=_sha256_json(material),
            digest_bindings={
                "ci_snapshot_bundle_hash": ci_snapshot_bundle_hash,
                "final_signoff_receipt_hash": final_signoff_receipt_hash,
                "pr_status_snapshot_bundle_hash": pr_status_snapshot_bundle_hash,
                "signoff_evidence_chain_hash": signoff_evidence_chain_hash,
                "validation_transcript_bundle_hash": validation_transcript_bundle_hash,
            },
            created_at=observed_at,
        ).record_hash

    def _persist_outputs(
        self,
        receipt: IndependentFinalSignoffVerificationReceipt,
        final_signoff_receipt: Mapping[str, object],
        signoff_report: Mapping[str, object],
        status_report: Mapping[str, object],
    ) -> None:
        report = {
            "accepted": receipt.accepted,
            "failures": receipt.failures,
            "final_signoff_receipt_hash": receipt.final_signoff_receipt_hash,
            "final_signoff_report_hash": receipt.final_signoff_report_hash,
            "final_system_status_report_hash": receipt.final_system_status_report_hash,
            "main_head": receipt.current_repo_head,
            "receipt_hash": receipt.receipt_hash,
            "release_tag_proposal": signoff_report.get("release_tag_proposal"),
            "signoff_id": final_signoff_receipt.get("signoff_id"),
            "status_matrix_hash": _sha256_json(
                _status_matrix_from_report(status_report)
            ),
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
            raise IndependentFinalSignoffVerificationError(
                "output_already_exists"
            )
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
            raise IndependentFinalSignoffVerificationError(
                field_name + "_must_be_nonempty_string"
            )
        if "\\" in relpath:
            raise IndependentFinalSignoffVerificationError(
                field_name + "_backslash_forbidden"
            )
        pure = PurePosixPath(relpath)
        if pure.is_absolute() or ".." in pure.parts:
            raise IndependentFinalSignoffVerificationError(
                field_name + "_must_stay_under_runtime_root"
            )
        path = (self.runtime_root / pure).resolve(strict=False)
        root = self.runtime_root.resolve()
        if path != root and root not in path.parents:
            raise IndependentFinalSignoffVerificationError(
                field_name + "_escapes_runtime_root"
            )
        return path


def compute_independent_evidence_snapshot_hash(
    snapshot: Mapping[str, object],
) -> str:
    if not isinstance(snapshot, Mapping):
        raise IndependentFinalSignoffVerificationError(
            "snapshot_must_be_mapping"
        )
    material = {
        key: value
        for key, value in snapshot.items()
        if key not in {"snapshot_hash", "transcript_digest", "evidence_hash"}
    }
    return _sha256_json(material)


def compute_independent_final_signoff_verification_receipt_hash(
    receipt: IndependentFinalSignoffVerificationReceipt,
) -> str:
    return _sha256_json(receipt.deterministic_material())


def _head_failures(
    *,
    expected_head: str,
    current_head: str,
    receipt: Mapping[str, object],
    signoff_report: Mapping[str, object],
) -> tuple[str, ...]:
    failures: list[str] = []
    if not _HEAD_PATTERN.match(expected_head):
        failures.append("expected_main_head_invalid")
    if not _HEAD_PATTERN.match(current_head):
        failures.append("current_repo_head_invalid")
    if expected_head != current_head:
        failures.append("main_head_mismatch")
    if receipt.get("main_head") != expected_head:
        failures.append("receipt_main_head_mismatch")
    if signoff_report.get("main_head") != expected_head:
        failures.append("signoff_report_main_head_mismatch")
    return tuple(_dedupe(failures))


def _priority_snapshot_failures(
    *,
    status_report: Mapping[str, object],
    snapshots: object,
    observed_at: str,
) -> tuple[str, ...]:
    matrix = _status_matrix_from_report(status_report)
    if not isinstance(snapshots, Sequence) or isinstance(snapshots, (str, bytes)):
        return ("pr_status_snapshots_required",)
    by_priority: dict[str, Mapping[str, object]] = {}
    failures: list[str] = []
    for item in snapshots:
        if not isinstance(item, Mapping):
            failures.append("pr_status_snapshot_must_be_mapping")
            continue
        priority_id = item.get("priority_id")
        if not isinstance(priority_id, str):
            failures.append("pr_status_snapshot_priority_required")
            continue
        if priority_id in by_priority:
            failures.append("duplicate_pr_status_snapshot:" + priority_id)
            continue
        by_priority[priority_id] = item
        failures.extend(_snapshot_hash_failures(item, "pr_status_snapshot"))
        failures.extend(_staleness_failures(item, observed_at, "pr_status_snapshot"))
        if item.get("immutable") is not True:
            failures.append("pr_status_snapshot_not_immutable:" + priority_id)
        if item.get("status") != matrix.get(priority_id):
            failures.append("pr_status_snapshot_status_mismatch:" + priority_id)
        if item.get("status") != _MERGED_STATUS:
            failures.append("pr_status_snapshot_not_merged:" + priority_id)
        if item.get("post_merge_validation") != "green":
            failures.append("pr_status_snapshot_post_merge_not_green:" + priority_id)
    for priority_id in _PRIORITY_IDS:
        if priority_id not in by_priority:
            failures.append("pr_status_snapshot_missing:" + priority_id)
    return tuple(_dedupe(failures))


def _validation_transcript_failures(
    transcripts: object,
    *,
    observed_at: str,
) -> tuple[str, ...]:
    if not isinstance(transcripts, Sequence) or isinstance(transcripts, (str, bytes)):
        return ("validation_transcripts_required",)
    by_command: dict[str, Mapping[str, object]] = {}
    failures: list[str] = []
    for item in transcripts:
        if not isinstance(item, Mapping):
            failures.append("validation_transcript_must_be_mapping")
            continue
        command = item.get("command")
        if not isinstance(command, str) or not command:
            failures.append("validation_transcript_command_required")
            continue
        if command in by_command:
            failures.append("duplicate_validation_transcript:" + command)
            continue
        by_command[command] = item
        digest_material = {
            "command": item.get("command"),
            "status": item.get("status"),
            "transcript": item.get("transcript", ""),
        }
        if item.get("transcript_digest") != _sha256_json(digest_material):
            failures.append("validation_transcript_digest_mismatch:" + command)
        failures.extend(_staleness_failures(item, observed_at, "validation_transcript"))
        if _normalized_status(item.get("status")) not in _GREEN_VALUES:
            failures.append("validation_transcript_not_green:" + command)
    for command in _REQUIRED_VALIDATION_COMMANDS:
        if command not in by_command:
            failures.append("validation_transcript_missing:" + command)
    return tuple(_dedupe(failures))


def _ci_snapshot_failures(
    snapshots: object,
    *,
    observed_at: str,
) -> tuple[str, ...]:
    if snapshots in (None, ()):
        return ()
    if not isinstance(snapshots, Sequence) or isinstance(snapshots, (str, bytes)):
        return ("ci_status_snapshots_must_be_sequence",)
    failures: list[str] = []
    seen: set[str] = set()
    for item in snapshots:
        if not isinstance(item, Mapping):
            failures.append("ci_status_snapshot_must_be_mapping")
            continue
        check_name = item.get("check_name")
        if not isinstance(check_name, str) or not check_name:
            failures.append("ci_status_snapshot_check_name_required")
            continue
        if check_name in seen:
            failures.append("duplicate_ci_status_snapshot:" + check_name)
            continue
        seen.add(check_name)
        failures.extend(_snapshot_hash_failures(item, "ci_status_snapshot"))
        failures.extend(_staleness_failures(item, observed_at, "ci_status_snapshot"))
        if check_name == "canonical-health" and _normalized_status(
            item.get("status")
        ) != "success":
            failures.append("canonical_health_snapshot_not_success")
    if "canonical-health" not in seen:
        failures.append("canonical_health_snapshot_missing")
    return tuple(_dedupe(failures))


def _worktree_evidence_failures(evidence: object) -> tuple[str, ...]:
    if not isinstance(evidence, Mapping):
        return ("worktree_evidence_required",)
    failures: list[str] = []
    if _normalized_status(evidence.get("git_diff_check")) != "clean":
        failures.append("git_diff_check_not_clean")
    if _normalized_status(evidence.get("git_status_short")) != "clean":
        failures.append("git_status_short_not_clean")
    if evidence.get("status_short_output", "") not in ("", None):
        failures.append("git_status_short_output_not_empty")
    failures.extend(_snapshot_hash_failures(evidence, "worktree_evidence"))
    return tuple(_dedupe(failures))


def _release_tag_evidence_failures(
    evidence: object,
    *,
    receipt: Mapping[str, object],
    signoff_report: Mapping[str, object],
) -> tuple[str, ...]:
    if not isinstance(evidence, Mapping):
        return ("release_tag_evidence_required",)
    tag = evidence.get("release_tag_proposal")
    failures: list[str] = []
    if not isinstance(tag, str) or not _RELEASE_TAG_PATTERN.match(tag):
        failures.append("release_tag_proposal_invalid")
    if evidence.get("release_tag_created") is True:
        failures.append("release_tag_must_be_proposal_only")
    if tag != receipt.get("release_tag_proposal"):
        failures.append("release_tag_receipt_mismatch")
    if tag != signoff_report.get("release_tag_proposal"):
        failures.append("release_tag_report_mismatch")
    failures.extend(_snapshot_hash_failures(evidence, "release_tag_evidence"))
    return tuple(_dedupe(failures))


def _snapshot_hash_failures(
    snapshot: Mapping[str, object],
    label: str,
) -> tuple[str, ...]:
    expected = snapshot.get("snapshot_hash") or snapshot.get("evidence_hash")
    if expected is None:
        return (label + "_hash_required",)
    if expected != compute_independent_evidence_snapshot_hash(snapshot):
        return (label + "_hash_mismatch",)
    return ()


def _staleness_failures(
    snapshot: Mapping[str, object],
    observed_at: str,
    label: str,
) -> tuple[str, ...]:
    failures: list[str] = []
    if snapshot.get("stale") is True:
        failures.append(label + "_stale")
    expires_at = snapshot.get("expires_at")
    if isinstance(expires_at, str) and expires_at:
        if _parse_datetime(expires_at) < _parse_datetime(observed_at):
            failures.append(label + "_expired")
    return tuple(_dedupe(failures))


def _snapshot_bundle_hash(snapshots: object) -> str:
    if not isinstance(snapshots, Sequence) or isinstance(snapshots, (str, bytes)):
        return _sha256_json(())
    normalized = []
    for item in snapshots:
        if isinstance(item, Mapping):
            sort_key = (
                str(item.get("priority_id", "")),
                str(item.get("check_name", "")),
                str(item.get("command", "")),
            )
            normalized.append((sort_key, _json_ready(item)))
    return _sha256_json(tuple(payload for _, payload in sorted(normalized)))


def _current_repo_head(data: Mapping[str, object], repo_root: Path) -> str:
    supplied = data.get("current_repo_head")
    if isinstance(supplied, str) and supplied:
        return supplied
    return _read_local_git_head(repo_root)


def _read_local_git_head(repo_root: Path) -> str:
    git_path = repo_root / ".git"
    if git_path.is_file():
        text = git_path.read_text(encoding="utf-8").strip()
        if not text.startswith("gitdir:"):
            raise IndependentFinalSignoffVerificationError("gitdir_file_invalid")
        git_path = (repo_root / text.removeprefix("gitdir:").strip()).resolve(
            strict=False
        )
    head_path = git_path / "HEAD"
    if not head_path.is_file():
        raise IndependentFinalSignoffVerificationError("git_head_missing")
    head = head_path.read_text(encoding="utf-8").strip()
    if _HEAD_PATTERN.match(head):
        return head
    if not head.startswith("ref: "):
        raise IndependentFinalSignoffVerificationError("git_head_invalid")
    ref_name = head.removeprefix("ref: ").strip()
    ref_path = (git_path / ref_name).resolve(strict=False)
    if ref_path.is_file():
        value = ref_path.read_text(encoding="utf-8").strip()
        if _HEAD_PATTERN.match(value):
            return value
    packed_refs = git_path / "packed-refs"
    if packed_refs.is_file():
        for line in packed_refs.read_text(encoding="utf-8").splitlines():
            if not line or line.startswith("#") or line.startswith("^"):
                continue
            parts = line.split(" ", 1)
            if len(parts) == 2 and parts[1] == ref_name and _HEAD_PATTERN.match(parts[0]):
                return parts[0]
    raise IndependentFinalSignoffVerificationError("git_head_ref_unresolved")


def _status_matrix_from_report(status_report: Mapping[str, object]) -> Mapping[str, object]:
    matrix = status_report.get("priority_status_matrix")
    if not isinstance(matrix, Mapping):
        return {}
    return matrix


def _gate_hashes(receipt: Mapping[str, object]) -> tuple[object, ...]:
    gates = receipt.get("gate_results")
    if not isinstance(gates, Sequence) or isinstance(gates, (str, bytes)):
        return ()
    return tuple(
        gate.get("gate_hash")
        for gate in gates
        if isinstance(gate, Mapping) and isinstance(gate.get("gate_hash"), str)
    )


def _timestamp(value: str | None) -> str:
    if value is None:
        return datetime.now(timezone.utc).isoformat()
    _require_nonempty_string(value, "observed_at")
    _parse_datetime(value)
    return value


def _parse_datetime(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise IndependentFinalSignoffVerificationError(
            "timestamp_invalid"
        ) from exc
    if parsed.tzinfo is None:
        raise IndependentFinalSignoffVerificationError("timestamp_timezone_required")
    return parsed


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
        raise IndependentFinalSignoffVerificationError(
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
        raise IndependentFinalSignoffVerificationError(
            field_name + "_must_be_nonempty_string"
        )


def _require_sha256(value: object, field_name: str) -> None:
    if not isinstance(value, str) or not _SHA256_PATTERN.match(value):
        raise IndependentFinalSignoffVerificationError(
            field_name + "_must_be_sha256"
        )


def _require_head(value: object, field_name: str) -> None:
    if not isinstance(value, str) or not _HEAD_PATTERN.match(value):
        raise IndependentFinalSignoffVerificationError(
            field_name + "_must_be_git_sha"
        )


def _string_field(data: Mapping[str, object], field_name: str, default: str) -> str:
    value = data.get(field_name, default)
    if not isinstance(value, str) or not value.strip():
        raise IndependentFinalSignoffVerificationError(
            field_name + "_must_be_nonempty_string"
        )
    return value


def _normalize_failures(values: Sequence[str]) -> tuple[str, ...]:
    if not isinstance(values, Sequence) or isinstance(values, (str, bytes)):
        raise IndependentFinalSignoffVerificationError("failures_must_be_sequence")
    normalized = tuple(str(value) for value in values)
    for value in normalized:
        _require_nonempty_string(value, "failure")
    return tuple(_dedupe(normalized))


def _install_or_verify_hash(instance: object, field_name: str, compute) -> None:
    current = getattr(instance, field_name)
    expected = compute(instance)
    if current in ("", None):
        object.__setattr__(instance, field_name, expected)
        return
    if current != expected:
        raise IndependentFinalSignoffVerificationError(field_name + "_mismatch")


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
