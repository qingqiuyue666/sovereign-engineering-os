"""Cycle-level contract for completed bounded local asset smoke cycles."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json

from kernel.personal_ai.hash_utils import sha256_file

__all__ = [
    "LOCAL_ASSET_BOUNDED_SMOKE_CYCLE_CONTRACT_FILE",
    "LOCAL_ASSET_BOUNDED_SMOKE_CYCLE_CONTRACT_MANIFEST_FILE",
    "LOCAL_ASSET_BOUNDED_SMOKE_CYCLE_SUMMARY_FILE",
    "LOCAL_ASSET_BOUNDED_SMOKE_CYCLE_HUMAN_REVIEW_CHECKLIST_FILE",
    "LocalAssetBoundedSmokeCycleContractResult",
    "build_local_asset_bounded_smoke_cycle_contract",
]


LOCAL_ASSET_BOUNDED_SMOKE_CYCLE_CONTRACT_FILE = (
    "local_asset_bounded_smoke_cycle_contract.json"
)
LOCAL_ASSET_BOUNDED_SMOKE_CYCLE_CONTRACT_MANIFEST_FILE = (
    "local_asset_bounded_smoke_cycle_contract_manifest.json"
)
LOCAL_ASSET_BOUNDED_SMOKE_CYCLE_SUMMARY_FILE = (
    "local_asset_bounded_smoke_cycle_summary.md"
)
LOCAL_ASSET_BOUNDED_SMOKE_CYCLE_HUMAN_REVIEW_CHECKLIST_FILE = (
    "local_asset_bounded_smoke_cycle_human_review_checklist.md"
)

_ARTIFACT_INDEX_FILE = "artifact_index.json"
_ARTIFACT_INDEX_MANIFEST_FILE = "artifact_index_manifest.json"

_CONTRACT_TYPE = "local_asset_bounded_smoke_cycle_contract_v1"
_MANIFEST_TYPE = "local_asset_bounded_smoke_cycle_contract_manifest_v1"
_INDEX_TYPE = "local_asset_bounded_smoke_cycle_contract_artifact_index_v1"
_INDEX_MANIFEST_TYPE = (
    "local_asset_bounded_smoke_cycle_contract_artifact_index_manifest_v1"
)
_AUTHORITY = "non_authority"
_EXECUTION_CAPABILITY = "local_asset_bounded_smoke_cycle_contract_only"
_NEXT_ALLOWED_ACTION = "human_review_bounded_smoke_cycle_contract"

_ALLOWED_AFTER_HUMAN_REVIEW = (
    "next_bounded_smoke_iteration",
    "stop_cycle",
    "repair_artifacts",
    "repair_cycle",
)
_DISALLOWED_ACTIONS = (
    "production_scan",
    "production_promotion",
    "automatic_approval",
    "autonomous_execution",
    "candidate_file_mutation",
    "duplicate_deletion",
    "media_organizer_behavior",
)
_CHECKLIST_DECISION_OPTIONS = (
    "approve_cycle_contract_for_next_bounded_smoke_iteration",
    "stop_cycle",
    "repair_artifacts",
    "repair_cycle",
    "inspect_quarantine",
    "inspect_duplicates",
    "inspect_incremental_changes",
    "reject_boundary_violation",
)

_OUTPUT_FILES = (
    LOCAL_ASSET_BOUNDED_SMOKE_CYCLE_CONTRACT_FILE,
    LOCAL_ASSET_BOUNDED_SMOKE_CYCLE_CONTRACT_MANIFEST_FILE,
    LOCAL_ASSET_BOUNDED_SMOKE_CYCLE_SUMMARY_FILE,
    LOCAL_ASSET_BOUNDED_SMOKE_CYCLE_HUMAN_REVIEW_CHECKLIST_FILE,
    _ARTIFACT_INDEX_FILE,
    _ARTIFACT_INDEX_MANIFEST_FILE,
)

_CONTRACT_ARTIFACTS = (
    (
        "local_asset_bounded_smoke_cycle_contract",
        LOCAL_ASSET_BOUNDED_SMOKE_CYCLE_CONTRACT_FILE,
    ),
    (
        "local_asset_bounded_smoke_cycle_contract_manifest",
        LOCAL_ASSET_BOUNDED_SMOKE_CYCLE_CONTRACT_MANIFEST_FILE,
    ),
    (
        "local_asset_bounded_smoke_cycle_summary",
        LOCAL_ASSET_BOUNDED_SMOKE_CYCLE_SUMMARY_FILE,
    ),
    (
        "local_asset_bounded_smoke_cycle_human_review_checklist",
        LOCAL_ASSET_BOUNDED_SMOKE_CYCLE_HUMAN_REVIEW_CHECKLIST_FILE,
    ),
)

_BOUNDARY_FLAGS = {
    "scan_performed": False,
    "readiness_run_performed": False,
    "human_smoke_run_performed": False,
    "smoke_review_packet_run_performed": False,
    "smoke_promotion_gate_run_performed": False,
    "bounded_smoke_iteration_performed_by_contract": False,
    "iteration_review_packet_run_performed": False,
    "iteration_promotion_gate_run_performed": False,
    "raw_candidate_content_read": False,
    "candidate_file_hashing_performed": False,
    "input_mutation_performed": False,
    "upstream_output_mutation_performed": False,
    "file_move_performed": False,
    "file_rename_performed": False,
    "file_delete_performed": False,
    "duplicate_deletion_performed": False,
    "media_organizer_behavior_performed": False,
    "output_overwrite_performed": False,
    "network_access_performed": False,
    "model_api_called": False,
    "external_runtime_invoked": False,
    "production_promotion_granted": False,
    "production_scan_approved": False,
    "production_scan_performed": False,
    "production_scan_recommended": False,
    "automatic_approval_performed": False,
    "autonomous_execution_performed": False,
}

_PRODUCTION_OR_MUTATION_FIELDS = (
    "production_promotion_granted",
    "production_scan_approved",
    "production_scan_performed",
    "production_scan_recommended",
    "automatic_approval_performed",
    "autonomous_execution_performed",
    "input_mutation_performed",
    "upstream_output_mutation_performed",
    "file_move_performed",
    "file_rename_performed",
    "file_delete_performed",
    "duplicate_deletion_performed",
    "media_organizer_behavior_performed",
    "output_overwrite_performed",
    "network_access_performed",
    "model_api_called",
    "external_runtime_invoked",
)

_SAFE_INFORMATIONAL_WARNINGS = {
    "informational_only",
    "safe_informational_warning",
}


@dataclass(frozen=True)
class _SourceArtifactSpec:
    root_key: str
    root_label: str
    artifact_role: str
    relative_path: str
    required: bool
    json_artifact: bool
    expected_field: str | None = None
    expected_value: object | None = None


_SOURCE_ARTIFACTS = (
    _SourceArtifactSpec(
        "readiness_output_dir",
        "readiness",
        "local_asset_smoke_readiness_report",
        "local_asset_smoke_readiness_report.json",
        True,
        True,
        "report_type",
        "local_asset_real_folder_smoke_readiness_report_v1",
    ),
    _SourceArtifactSpec(
        "readiness_output_dir",
        "readiness",
        "local_asset_smoke_readiness_manifest",
        "local_asset_smoke_readiness_manifest.json",
        True,
        True,
        "manifest_type",
        "local_asset_real_folder_smoke_readiness_manifest_v1",
    ),
    _SourceArtifactSpec(
        "readiness_output_dir",
        "readiness",
        "local_asset_smoke_readiness_summary",
        "local_asset_smoke_readiness_summary.md",
        True,
        False,
    ),
    _SourceArtifactSpec(
        "readiness_output_dir",
        "readiness",
        "readiness_artifact_index",
        _ARTIFACT_INDEX_FILE,
        True,
        True,
        "index_type",
        "personal_ai_local_v1_artifact_index",
    ),
    _SourceArtifactSpec(
        "readiness_output_dir",
        "readiness",
        "readiness_artifact_index_manifest",
        _ARTIFACT_INDEX_MANIFEST_FILE,
        True,
        True,
        "manifest_type",
        "personal_ai_local_v1_artifact_index_manifest",
    ),
    _SourceArtifactSpec(
        "smoke_output_dir",
        "initial_human_smoke",
        "local_asset_human_smoke_approval",
        "control/local_asset_human_smoke_approval.json",
        True,
        True,
        "artifact_type",
        "local_asset_human_smoke_approval_v1",
    ),
    _SourceArtifactSpec(
        "smoke_output_dir",
        "initial_human_smoke",
        "local_asset_human_smoke_admission_receipt",
        "control/local_asset_human_smoke_admission_receipt.json",
        True,
        True,
        "receipt_type",
        "local_asset_human_smoke_admission_receipt_v1",
    ),
    _SourceArtifactSpec(
        "smoke_output_dir",
        "initial_human_smoke",
        "initial_smoke_artifact_index",
        _ARTIFACT_INDEX_FILE,
        True,
        True,
        "index_type",
        "local_asset_human_smoke_artifact_index_v1",
    ),
    _SourceArtifactSpec(
        "smoke_output_dir",
        "initial_human_smoke",
        "initial_smoke_artifact_index_manifest",
        _ARTIFACT_INDEX_MANIFEST_FILE,
        True,
        True,
        "manifest_type",
        "local_asset_human_smoke_artifact_index_manifest_v1",
    ),
    _SourceArtifactSpec(
        "smoke_output_dir",
        "initial_human_smoke",
        "local_asset_human_smoke_run_summary",
        "local_asset_human_smoke_run_summary.md",
        True,
        False,
    ),
    _SourceArtifactSpec(
        "smoke_output_dir",
        "initial_human_smoke",
        "initial_scan_artifact_index",
        "scan/artifact_index.json",
        True,
        True,
        "index_type",
        "personal_ai_local_v1_artifact_index",
    ),
    _SourceArtifactSpec(
        "smoke_output_dir",
        "initial_human_smoke",
        "initial_scan_artifact_index_manifest",
        "scan/artifact_index_manifest.json",
        True,
        True,
        "manifest_type",
        "personal_ai_local_v1_artifact_index_manifest",
    ),
    _SourceArtifactSpec(
        "smoke_output_dir",
        "initial_human_smoke",
        "initial_scan_asset_manifest",
        "scan/asset_manifest.json",
        True,
        True,
        "manifest_type",
        "local_asset_runtime_v1_asset_manifest",
    ),
    _SourceArtifactSpec(
        "smoke_output_dir",
        "initial_human_smoke",
        "initial_scan_asset_scan_run_receipt",
        "scan/asset_scan_run_receipt.json",
        True,
        True,
        "receipt_type",
        "local_asset_scan_operational_receipt_v1",
    ),
    _SourceArtifactSpec(
        "smoke_output_dir",
        "initial_human_smoke",
        "initial_scan_asset_runtime_validation_report",
        "scan/asset_runtime_validation_report.json",
        True,
        True,
        "validation_type",
        "local_asset_runtime_v1_validation_report",
    ),
    _SourceArtifactSpec(
        "smoke_output_dir",
        "initial_human_smoke",
        "initial_scan_asset_runtime_quarantine_manifest",
        "scan/asset_runtime_quarantine_manifest.json",
        True,
        True,
        "quarantine_type",
        "local_asset_runtime_v1_quarantine_manifest",
    ),
    _SourceArtifactSpec(
        "smoke_output_dir",
        "initial_human_smoke",
        "initial_scan_duplicates_report",
        "scan/duplicates_report.json",
        True,
        True,
        "report_type",
        "local_asset_runtime_v1_duplicates_report",
    ),
    _SourceArtifactSpec(
        "smoke_output_dir",
        "initial_human_smoke",
        "initial_scan_local_asset_sqlite_index_manifest",
        "scan/local_asset_sqlite_index_manifest.json",
        False,
        True,
        "manifest_type",
        "local_asset_sqlite_index_manifest_v1",
    ),
    _SourceArtifactSpec(
        "smoke_output_dir",
        "initial_human_smoke",
        "initial_scan_local_asset_incremental_scan_plan",
        "scan/local_asset_incremental_scan_plan.json",
        False,
        True,
        "plan_type",
        "local_asset_incremental_scan_plan_v1",
    ),
    _SourceArtifactSpec(
        "smoke_review_output_dir",
        "smoke_review",
        "local_asset_smoke_review_packet",
        "local_asset_smoke_review_packet.json",
        True,
        True,
        "packet_type",
        "local_asset_smoke_review_packet_v1",
    ),
    _SourceArtifactSpec(
        "smoke_review_output_dir",
        "smoke_review",
        "local_asset_smoke_review_packet_manifest",
        "local_asset_smoke_review_packet_manifest.json",
        True,
        True,
        "manifest_type",
        "local_asset_smoke_review_packet_manifest_v1",
    ),
    _SourceArtifactSpec(
        "smoke_review_output_dir",
        "smoke_review",
        "local_asset_smoke_review_summary",
        "local_asset_smoke_review_summary.md",
        False,
        False,
    ),
    _SourceArtifactSpec(
        "smoke_review_output_dir",
        "smoke_review",
        "local_asset_smoke_human_decision_checklist",
        "local_asset_smoke_human_decision_checklist.md",
        False,
        False,
    ),
    _SourceArtifactSpec(
        "smoke_review_output_dir",
        "smoke_review",
        "smoke_review_artifact_index",
        _ARTIFACT_INDEX_FILE,
        True,
        True,
        "index_type",
        "local_asset_smoke_review_packet_artifact_index_v1",
    ),
    _SourceArtifactSpec(
        "smoke_review_output_dir",
        "smoke_review",
        "smoke_review_artifact_index_manifest",
        _ARTIFACT_INDEX_MANIFEST_FILE,
        True,
        True,
        "manifest_type",
        "local_asset_smoke_review_packet_artifact_index_manifest_v1",
    ),
    _SourceArtifactSpec(
        "smoke_promotion_output_dir",
        "smoke_promotion",
        "local_asset_smoke_promotion_decision",
        "local_asset_smoke_promotion_decision.json",
        True,
        True,
        "decision_type",
        "local_asset_smoke_promotion_decision_v1",
    ),
    _SourceArtifactSpec(
        "smoke_promotion_output_dir",
        "smoke_promotion",
        "local_asset_smoke_promotion_gate_manifest",
        "local_asset_smoke_promotion_gate_manifest.json",
        True,
        True,
        "manifest_type",
        "local_asset_smoke_promotion_gate_manifest_v1",
    ),
    _SourceArtifactSpec(
        "smoke_promotion_output_dir",
        "smoke_promotion",
        "local_asset_smoke_promotion_summary",
        "local_asset_smoke_promotion_summary.md",
        False,
        False,
    ),
    _SourceArtifactSpec(
        "smoke_promotion_output_dir",
        "smoke_promotion",
        "local_asset_smoke_promotion_human_signoff_checklist",
        "local_asset_smoke_promotion_human_signoff_checklist.md",
        False,
        False,
    ),
    _SourceArtifactSpec(
        "smoke_promotion_output_dir",
        "smoke_promotion",
        "smoke_promotion_artifact_index",
        _ARTIFACT_INDEX_FILE,
        True,
        True,
        "index_type",
        "local_asset_smoke_promotion_gate_artifact_index_v1",
    ),
    _SourceArtifactSpec(
        "smoke_promotion_output_dir",
        "smoke_promotion",
        "smoke_promotion_artifact_index_manifest",
        _ARTIFACT_INDEX_MANIFEST_FILE,
        True,
        True,
        "manifest_type",
        "local_asset_smoke_promotion_gate_artifact_index_manifest_v1",
    ),
    _SourceArtifactSpec(
        "iteration_output_dir",
        "bounded_smoke_iteration",
        "local_asset_bounded_smoke_iteration_result",
        "local_asset_bounded_smoke_iteration_result.json",
        True,
        True,
        "result_type",
        "local_asset_bounded_smoke_iteration_result_v1",
    ),
    _SourceArtifactSpec(
        "iteration_output_dir",
        "bounded_smoke_iteration",
        "local_asset_bounded_smoke_iteration_manifest",
        "local_asset_bounded_smoke_iteration_manifest.json",
        True,
        True,
        "manifest_type",
        "local_asset_bounded_smoke_iteration_manifest_v1",
    ),
    _SourceArtifactSpec(
        "iteration_output_dir",
        "bounded_smoke_iteration",
        "local_asset_bounded_smoke_iteration_summary",
        "local_asset_bounded_smoke_iteration_summary.md",
        False,
        False,
    ),
    _SourceArtifactSpec(
        "iteration_output_dir",
        "bounded_smoke_iteration",
        "local_asset_bounded_smoke_iteration_human_review_checklist",
        "local_asset_bounded_smoke_iteration_human_review_checklist.md",
        False,
        False,
    ),
    _SourceArtifactSpec(
        "iteration_output_dir",
        "bounded_smoke_iteration",
        "local_asset_bounded_smoke_iteration_signoff",
        "control/local_asset_bounded_smoke_iteration_signoff.json",
        True,
        True,
        "signoff_type",
        "local_asset_bounded_smoke_iteration_signoff_v1",
    ),
    _SourceArtifactSpec(
        "iteration_output_dir",
        "bounded_smoke_iteration",
        "local_asset_bounded_smoke_iteration_admission",
        "control/local_asset_bounded_smoke_iteration_admission.json",
        True,
        True,
        "admission_type",
        "local_asset_bounded_smoke_iteration_admission_v1",
    ),
    _SourceArtifactSpec(
        "iteration_output_dir",
        "bounded_smoke_iteration",
        "iteration_artifact_index",
        _ARTIFACT_INDEX_FILE,
        True,
        True,
        "index_type",
        "local_asset_bounded_smoke_iteration_artifact_index_v1",
    ),
    _SourceArtifactSpec(
        "iteration_output_dir",
        "bounded_smoke_iteration",
        "iteration_artifact_index_manifest",
        _ARTIFACT_INDEX_MANIFEST_FILE,
        True,
        True,
        "manifest_type",
        "local_asset_bounded_smoke_iteration_artifact_index_manifest_v1",
    ),
    _SourceArtifactSpec(
        "iteration_output_dir",
        "bounded_smoke_iteration",
        "iteration_smoke_artifact_index",
        "smoke/artifact_index.json",
        True,
        True,
        "index_type",
        "local_asset_human_smoke_artifact_index_v1",
    ),
    _SourceArtifactSpec(
        "iteration_output_dir",
        "bounded_smoke_iteration",
        "iteration_smoke_artifact_index_manifest",
        "smoke/artifact_index_manifest.json",
        True,
        True,
        "manifest_type",
        "local_asset_human_smoke_artifact_index_manifest_v1",
    ),
    _SourceArtifactSpec(
        "iteration_output_dir",
        "bounded_smoke_iteration",
        "iteration_scan_artifact_index",
        "smoke/scan/artifact_index.json",
        True,
        True,
        "index_type",
        "personal_ai_local_v1_artifact_index",
    ),
    _SourceArtifactSpec(
        "iteration_output_dir",
        "bounded_smoke_iteration",
        "iteration_scan_artifact_index_manifest",
        "smoke/scan/artifact_index_manifest.json",
        True,
        True,
        "manifest_type",
        "personal_ai_local_v1_artifact_index_manifest",
    ),
    _SourceArtifactSpec(
        "iteration_output_dir",
        "bounded_smoke_iteration",
        "iteration_scan_asset_manifest",
        "smoke/scan/asset_manifest.json",
        True,
        True,
        "manifest_type",
        "local_asset_runtime_v1_asset_manifest",
    ),
    _SourceArtifactSpec(
        "iteration_output_dir",
        "bounded_smoke_iteration",
        "iteration_scan_asset_scan_run_receipt",
        "smoke/scan/asset_scan_run_receipt.json",
        True,
        True,
        "receipt_type",
        "local_asset_scan_operational_receipt_v1",
    ),
    _SourceArtifactSpec(
        "iteration_output_dir",
        "bounded_smoke_iteration",
        "iteration_scan_asset_runtime_validation_report",
        "smoke/scan/asset_runtime_validation_report.json",
        True,
        True,
        "validation_type",
        "local_asset_runtime_v1_validation_report",
    ),
    _SourceArtifactSpec(
        "iteration_output_dir",
        "bounded_smoke_iteration",
        "iteration_scan_asset_runtime_quarantine_manifest",
        "smoke/scan/asset_runtime_quarantine_manifest.json",
        True,
        True,
        "quarantine_type",
        "local_asset_runtime_v1_quarantine_manifest",
    ),
    _SourceArtifactSpec(
        "iteration_output_dir",
        "bounded_smoke_iteration",
        "iteration_scan_duplicates_report",
        "smoke/scan/duplicates_report.json",
        True,
        True,
        "report_type",
        "local_asset_runtime_v1_duplicates_report",
    ),
    _SourceArtifactSpec(
        "iteration_output_dir",
        "bounded_smoke_iteration",
        "iteration_scan_local_asset_sqlite_index_manifest",
        "smoke/scan/local_asset_sqlite_index_manifest.json",
        False,
        True,
        "manifest_type",
        "local_asset_sqlite_index_manifest_v1",
    ),
    _SourceArtifactSpec(
        "iteration_output_dir",
        "bounded_smoke_iteration",
        "iteration_scan_local_asset_incremental_scan_plan",
        "smoke/scan/local_asset_incremental_scan_plan.json",
        False,
        True,
        "plan_type",
        "local_asset_incremental_scan_plan_v1",
    ),
    _SourceArtifactSpec(
        "iteration_review_output_dir",
        "iteration_review",
        "local_asset_smoke_iteration_review_packet",
        "local_asset_smoke_iteration_review_packet.json",
        True,
        True,
        "packet_type",
        "local_asset_smoke_iteration_review_packet_v1",
    ),
    _SourceArtifactSpec(
        "iteration_review_output_dir",
        "iteration_review",
        "local_asset_smoke_iteration_review_packet_manifest",
        "local_asset_smoke_iteration_review_packet_manifest.json",
        True,
        True,
        "manifest_type",
        "local_asset_smoke_iteration_review_packet_manifest_v1",
    ),
    _SourceArtifactSpec(
        "iteration_review_output_dir",
        "iteration_review",
        "local_asset_smoke_iteration_review_summary",
        "local_asset_smoke_iteration_review_summary.md",
        False,
        False,
    ),
    _SourceArtifactSpec(
        "iteration_review_output_dir",
        "iteration_review",
        "local_asset_smoke_iteration_human_decision_checklist",
        "local_asset_smoke_iteration_human_decision_checklist.md",
        False,
        False,
    ),
    _SourceArtifactSpec(
        "iteration_review_output_dir",
        "iteration_review",
        "iteration_review_artifact_index",
        _ARTIFACT_INDEX_FILE,
        True,
        True,
        "index_type",
        "local_asset_smoke_iteration_review_packet_artifact_index_v1",
    ),
    _SourceArtifactSpec(
        "iteration_review_output_dir",
        "iteration_review",
        "iteration_review_artifact_index_manifest",
        _ARTIFACT_INDEX_MANIFEST_FILE,
        True,
        True,
        "manifest_type",
        "local_asset_smoke_iteration_review_packet_artifact_index_manifest_v1",
    ),
    _SourceArtifactSpec(
        "iteration_promotion_output_dir",
        "iteration_promotion",
        "local_asset_iteration_promotion_decision",
        "local_asset_iteration_promotion_decision.json",
        True,
        True,
        "decision_type",
        "local_asset_iteration_promotion_decision_v1",
    ),
    _SourceArtifactSpec(
        "iteration_promotion_output_dir",
        "iteration_promotion",
        "local_asset_iteration_promotion_gate_manifest",
        "local_asset_iteration_promotion_gate_manifest.json",
        True,
        True,
        "manifest_type",
        "local_asset_iteration_promotion_gate_manifest_v1",
    ),
    _SourceArtifactSpec(
        "iteration_promotion_output_dir",
        "iteration_promotion",
        "local_asset_iteration_promotion_summary",
        "local_asset_iteration_promotion_summary.md",
        False,
        False,
    ),
    _SourceArtifactSpec(
        "iteration_promotion_output_dir",
        "iteration_promotion",
        "local_asset_iteration_promotion_human_signoff_checklist",
        "local_asset_iteration_promotion_human_signoff_checklist.md",
        False,
        False,
    ),
    _SourceArtifactSpec(
        "iteration_promotion_output_dir",
        "iteration_promotion",
        "iteration_promotion_artifact_index",
        _ARTIFACT_INDEX_FILE,
        True,
        True,
        "index_type",
        "local_asset_iteration_promotion_gate_artifact_index_v1",
    ),
    _SourceArtifactSpec(
        "iteration_promotion_output_dir",
        "iteration_promotion",
        "iteration_promotion_artifact_index_manifest",
        _ARTIFACT_INDEX_MANIFEST_FILE,
        True,
        True,
        "manifest_type",
        "local_asset_iteration_promotion_gate_artifact_index_manifest_v1",
    ),
)


@dataclass(frozen=True)
class LocalAssetBoundedSmokeCycleContractResult:
    readiness_output_dir: Path
    smoke_output_dir: Path
    smoke_review_output_dir: Path
    smoke_promotion_output_dir: Path
    iteration_output_dir: Path
    iteration_review_output_dir: Path
    iteration_promotion_output_dir: Path
    output_dir: Path
    contract_path: Path | None
    contract_manifest_path: Path | None
    summary_path: Path | None
    human_review_checklist_path: Path | None
    artifact_index_path: Path | None
    artifact_index_manifest_path: Path | None
    complete: bool
    cycle_contract_status: str
    cycle_contract_decision: str
    payload: dict[str, object]


def build_local_asset_bounded_smoke_cycle_contract(
    readiness_output_dir: Path,
    smoke_output_dir: Path,
    smoke_review_output_dir: Path,
    smoke_promotion_output_dir: Path,
    iteration_output_dir: Path,
    iteration_review_output_dir: Path,
    iteration_promotion_output_dir: Path,
    output_dir: Path,
    *,
    project_id: str | None = None,
) -> LocalAssetBoundedSmokeCycleContractResult:
    """Build a replayable metadata contract for an already-completed smoke cycle."""

    roots = _chain_roots(
        readiness_output_dir=Path(readiness_output_dir),
        smoke_output_dir=Path(smoke_output_dir),
        smoke_review_output_dir=Path(smoke_review_output_dir),
        smoke_promotion_output_dir=Path(smoke_promotion_output_dir),
        iteration_output_dir=Path(iteration_output_dir),
        iteration_review_output_dir=Path(iteration_review_output_dir),
        iteration_promotion_output_dir=Path(iteration_promotion_output_dir),
        output_dir=Path(output_dir),
    )
    paths = _output_paths(roots["output_dir"])

    preflight_error = _preflight_error(roots, paths)
    if preflight_error is not None:
        return _structured_failure_result(
            roots,
            project_id=project_id,
            failure_stage=preflight_error["failure_stage"],
            error_message=preflight_error["error_message"],
        )

    source_artifacts = _source_artifact_records(roots)
    source_payloads = _read_json_source_payloads(source_artifacts)
    _mark_trust_failures(source_artifacts, source_payloads)
    contract = _contract_payload(
        roots=roots,
        project_id=project_id,
        source_artifacts=source_artifacts,
        source_payloads=source_payloads,
    )
    summary = _summary_markdown(contract)
    checklist = _human_review_checklist_markdown(contract)

    _write_json_exclusive(paths[LOCAL_ASSET_BOUNDED_SMOKE_CYCLE_CONTRACT_FILE], contract)
    _write_text_exclusive(paths[LOCAL_ASSET_BOUNDED_SMOKE_CYCLE_SUMMARY_FILE], summary)
    _write_text_exclusive(
        paths[LOCAL_ASSET_BOUNDED_SMOKE_CYCLE_HUMAN_REVIEW_CHECKLIST_FILE],
        checklist,
    )
    manifest = _contract_manifest_payload(paths, source_artifacts, contract)
    _write_json_exclusive(
        paths[LOCAL_ASSET_BOUNDED_SMOKE_CYCLE_CONTRACT_MANIFEST_FILE],
        manifest,
    )
    artifact_index = _artifact_index_payload(roots["output_dir"], paths)
    _write_json_exclusive(paths[_ARTIFACT_INDEX_FILE], artifact_index)
    artifact_index_manifest = _artifact_index_manifest_payload(
        roots["output_dir"],
        paths,
        artifact_index,
    )
    _write_json_exclusive(paths[_ARTIFACT_INDEX_MANIFEST_FILE], artifact_index_manifest)

    complete = contract["cycle_contract_status"] in (
        "cycle_contract_ready",
        "cycle_contract_ready_with_warnings",
    )
    payload = _launcher_payload_from_contract(contract, paths, complete=complete)
    return LocalAssetBoundedSmokeCycleContractResult(
        readiness_output_dir=roots["readiness_output_dir"],
        smoke_output_dir=roots["smoke_output_dir"],
        smoke_review_output_dir=roots["smoke_review_output_dir"],
        smoke_promotion_output_dir=roots["smoke_promotion_output_dir"],
        iteration_output_dir=roots["iteration_output_dir"],
        iteration_review_output_dir=roots["iteration_review_output_dir"],
        iteration_promotion_output_dir=roots["iteration_promotion_output_dir"],
        output_dir=roots["output_dir"],
        contract_path=paths[LOCAL_ASSET_BOUNDED_SMOKE_CYCLE_CONTRACT_FILE],
        contract_manifest_path=paths[
            LOCAL_ASSET_BOUNDED_SMOKE_CYCLE_CONTRACT_MANIFEST_FILE
        ],
        summary_path=paths[LOCAL_ASSET_BOUNDED_SMOKE_CYCLE_SUMMARY_FILE],
        human_review_checklist_path=paths[
            LOCAL_ASSET_BOUNDED_SMOKE_CYCLE_HUMAN_REVIEW_CHECKLIST_FILE
        ],
        artifact_index_path=paths[_ARTIFACT_INDEX_FILE],
        artifact_index_manifest_path=paths[_ARTIFACT_INDEX_MANIFEST_FILE],
        complete=complete,
        cycle_contract_status=str(contract["cycle_contract_status"]),
        cycle_contract_decision=str(contract["cycle_contract_decision"]),
        payload=payload,
    )


def _chain_roots(**roots: Path) -> dict[str, Path]:
    return {key: Path(path) for key, path in roots.items()}


def _output_paths(output_dir: Path) -> dict[str, Path]:
    return {file_name: output_dir / file_name for file_name in _OUTPUT_FILES}


def _preflight_error(
    roots: dict[str, Path],
    paths: dict[str, Path],
) -> dict[str, str] | None:
    output_error = _real_existing_dir_error(roots["output_dir"], "output_dir")
    if output_error is not None:
        return {
            "failure_stage": "preflight_output_dir_missing",
            "error_message": output_error,
        }
    collision = _existing_output_collision(paths)
    if collision is not None:
        return {
            "failure_stage": "preflight_output_collision",
            "error_message": (
                "local asset bounded smoke cycle contract output already exists: "
                + collision
            ),
        }
    for key in _input_root_keys():
        error = _real_existing_dir_error(roots[key], key)
        if error is not None:
            return {
                "failure_stage": "preflight_input_dir_invalid",
                "error_message": error,
            }
    overlap_error = _root_overlap_error(roots)
    if overlap_error is not None:
        return {
            "failure_stage": "preflight_root_overlap",
            "error_message": overlap_error,
        }
    return None


def _real_existing_dir_error(path: Path, label: str) -> str | None:
    if not path.exists():
        return label + " is missing"
    if not path.is_dir():
        return label + " is not a directory"
    if path.is_symlink():
        return label + " must not be a symlink"
    return None


def _existing_output_collision(paths: dict[str, Path]) -> str | None:
    for file_name in sorted(paths):
        if paths[file_name].exists():
            return file_name
    return None


def _input_root_keys() -> tuple[str, ...]:
    return (
        "readiness_output_dir",
        "smoke_output_dir",
        "smoke_review_output_dir",
        "smoke_promotion_output_dir",
        "iteration_output_dir",
        "iteration_review_output_dir",
        "iteration_promotion_output_dir",
    )


def _root_overlap_error(roots: dict[str, Path]) -> str | None:
    output_path = roots["output_dir"]
    for key in _input_root_keys():
        error = _existing_dir_overlap_error(
            roots[key],
            output_path,
            left_label=key,
            right_label="output_dir",
        )
        if error is not None:
            return error
    input_keys = _input_root_keys()
    for index, left_key in enumerate(input_keys):
        for right_key in input_keys[index + 1 :]:
            error = _existing_dir_overlap_error(
                roots[left_key],
                roots[right_key],
                left_label=left_key,
                right_label=right_key,
            )
            if error is not None:
                return error
    return None


def _existing_dir_overlap_error(
    left_path: Path,
    right_path: Path,
    *,
    left_label: str,
    right_label: str,
) -> str | None:
    try:
        left_resolved = left_path.resolve(strict=True)
        right_resolved = right_path.resolve(strict=True)
    except OSError:
        return None
    if left_resolved == right_resolved:
        return right_label + " must not equal " + left_label
    if _path_is_inside(right_resolved, left_resolved):
        return right_label + " must not be inside " + left_label
    if _path_is_inside(left_resolved, right_resolved):
        return left_label + " must not be inside " + right_label
    return None


def _path_is_inside(candidate_path: Path, root_path: Path) -> bool:
    try:
        Path(candidate_path).resolve(strict=False).relative_to(
            Path(root_path).resolve(strict=False)
        )
    except (OSError, ValueError):
        return False
    return True


def _source_artifact_records(roots: dict[str, Path]) -> list[dict[str, object]]:
    records = []
    for spec in _SOURCE_ARTIFACTS:
        path = roots[spec.root_key] / spec.relative_path
        exists = path.exists()
        is_symlink = path.is_symlink()
        is_file = path.is_file() if exists and not is_symlink else False
        trusted = exists and is_file and not is_symlink
        records.append(
            {
                "role": spec.artifact_role,
                "artifact_role": spec.artifact_role,
                "root_key": spec.root_key,
                "root_label": spec.root_label,
                "relative_path": spec.relative_path,
                "path": path.as_posix(),
                "exists": exists,
                "required": spec.required,
                "json_artifact": spec.json_artifact,
                "trusted_generated_artifact": trusted,
                "is_symlink": is_symlink,
                "is_file": is_file,
                "sha256": sha256_file(path) if trusted else None,
                "size_bytes": path.stat().st_size if trusted else None,
                "content_indexed": False,
                "raw_content_copied": False,
            }
        )
    return sorted(
        records,
        key=lambda record: (
            str(record["root_key"]),
            str(record["artifact_role"]),
        ),
    )


def _read_json_source_payloads(
    source_artifacts: list[dict[str, object]],
) -> dict[str, object]:
    payloads: dict[str, object] = {}
    for record in source_artifacts:
        if record.get("json_artifact") is not True:
            continue
        if record.get("trusted_generated_artifact") is not True:
            continue
        path = Path(str(record["path"]))
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            record["parse_error"] = "json_malformed"
            continue
        if not isinstance(payload, dict):
            record["parse_error"] = "json_not_object"
            continue
        payloads[str(record["artifact_role"])] = payload
    return payloads


def _mark_trust_failures(
    source_artifacts: list[dict[str, object]],
    source_payloads: dict[str, object],
) -> None:
    records_by_role = _records_by_role(source_artifacts)
    for record in source_artifacts:
        if "parse_error" in record:
            _mark_untrusted(record, str(record["parse_error"]))
    for spec in _SOURCE_ARTIFACTS:
        if spec.expected_field is None:
            continue
        payload = _dict_payload(source_payloads, spec.artifact_role)
        if not payload:
            continue
        if payload.get(spec.expected_field) != spec.expected_value:
            _mark_untrusted(
                records_by_role[spec.artifact_role],
                "type_mismatch",
                expected_field=spec.expected_field,
                expected_value=spec.expected_value,
                actual_value=payload.get(spec.expected_field),
            )
    for role in _hash_mismatch_roles(records_by_role, source_payloads):
        if role in records_by_role:
            _mark_untrusted(records_by_role[role], "hash_mismatch")


def _hash_mismatch_roles(
    records_by_role: dict[str, dict[str, object]],
    source_payloads: dict[str, object],
) -> list[str]:
    mismatches: list[str] = []
    mismatches.extend(
        _manifest_file_hash_mismatches(
            records_by_role,
            source_payloads,
            manifest_role="local_asset_smoke_readiness_manifest",
            field_roles=(
                ("report_sha256", "local_asset_smoke_readiness_report"),
                ("summary_sha256", "local_asset_smoke_readiness_summary"),
            ),
        )
    )
    mismatches.extend(
        _manifest_file_hash_mismatches(
            records_by_role,
            source_payloads,
            manifest_role="local_asset_smoke_review_packet_manifest",
            field_roles=(
                ("packet_sha256", "local_asset_smoke_review_packet"),
                ("summary_sha256", "local_asset_smoke_review_summary"),
                (
                    "decision_checklist_sha256",
                    "local_asset_smoke_human_decision_checklist",
                ),
            ),
        )
    )
    mismatches.extend(
        _manifest_file_hash_mismatches(
            records_by_role,
            source_payloads,
            manifest_role="local_asset_smoke_promotion_gate_manifest",
            field_roles=(
                ("decision_sha256", "local_asset_smoke_promotion_decision"),
                ("summary_sha256", "local_asset_smoke_promotion_summary"),
                (
                    "human_signoff_checklist_sha256",
                    "local_asset_smoke_promotion_human_signoff_checklist",
                ),
            ),
        )
    )
    mismatches.extend(
        _manifest_file_hash_mismatches(
            records_by_role,
            source_payloads,
            manifest_role="local_asset_bounded_smoke_iteration_manifest",
            field_roles=(
                ("result_sha256", "local_asset_bounded_smoke_iteration_result"),
                ("summary_sha256", "local_asset_bounded_smoke_iteration_summary"),
                (
                    "human_review_checklist_sha256",
                    "local_asset_bounded_smoke_iteration_human_review_checklist",
                ),
                ("signoff_sha256", "local_asset_bounded_smoke_iteration_signoff"),
                ("admission_sha256", "local_asset_bounded_smoke_iteration_admission"),
            ),
        )
    )
    mismatches.extend(
        _manifest_file_hash_mismatches(
            records_by_role,
            source_payloads,
            manifest_role="local_asset_smoke_iteration_review_packet_manifest",
            field_roles=(
                ("packet_sha256", "local_asset_smoke_iteration_review_packet"),
                ("summary_sha256", "local_asset_smoke_iteration_review_summary"),
                (
                    "decision_checklist_sha256",
                    "local_asset_smoke_iteration_human_decision_checklist",
                ),
            ),
        )
    )
    mismatches.extend(
        _manifest_file_hash_mismatches(
            records_by_role,
            source_payloads,
            manifest_role="local_asset_iteration_promotion_gate_manifest",
            field_roles=(
                ("decision_sha256", "local_asset_iteration_promotion_decision"),
                ("summary_sha256", "local_asset_iteration_promotion_summary"),
                (
                    "human_signoff_checklist_sha256",
                    "local_asset_iteration_promotion_human_signoff_checklist",
                ),
            ),
        )
    )
    for index_role, manifest_role in (
        ("readiness_artifact_index", "readiness_artifact_index_manifest"),
        ("initial_smoke_artifact_index", "initial_smoke_artifact_index_manifest"),
        ("initial_scan_artifact_index", "initial_scan_artifact_index_manifest"),
        ("smoke_review_artifact_index", "smoke_review_artifact_index_manifest"),
        ("smoke_promotion_artifact_index", "smoke_promotion_artifact_index_manifest"),
        ("iteration_artifact_index", "iteration_artifact_index_manifest"),
        ("iteration_smoke_artifact_index", "iteration_smoke_artifact_index_manifest"),
        ("iteration_scan_artifact_index", "iteration_scan_artifact_index_manifest"),
        ("iteration_review_artifact_index", "iteration_review_artifact_index_manifest"),
        (
            "iteration_promotion_artifact_index",
            "iteration_promotion_artifact_index_manifest",
        ),
    ):
        mismatches.extend(
            _manifest_file_hash_mismatches(
                records_by_role,
                source_payloads,
                manifest_role=manifest_role,
                field_roles=(("artifact_index_sha256", index_role),),
            )
        )
    return sorted(set(mismatches))


def _manifest_file_hash_mismatches(
    records_by_role: dict[str, dict[str, object]],
    source_payloads: dict[str, object],
    *,
    manifest_role: str,
    field_roles: tuple[tuple[str, str], ...],
) -> list[str]:
    manifest = _dict_payload(source_payloads, manifest_role)
    if not manifest:
        return []
    mismatches = []
    for field_name, artifact_role in field_roles:
        record = records_by_role.get(artifact_role, {})
        if record.get("exists") is not True:
            continue
        expected = manifest.get(field_name)
        if expected is not None and expected != record.get("sha256"):
            mismatches.append(manifest_role)
    return mismatches


def _mark_untrusted(
    record: dict[str, object],
    reason: str,
    **extra: object,
) -> None:
    record["trusted_generated_artifact"] = False
    reasons = _string_list(record.get("trust_failure_reasons"))
    reasons.append(reason)
    record["trust_failure_reasons"] = sorted(set(reasons))
    for key, value in extra.items():
        record[key] = value


def _contract_payload(
    *,
    roots: dict[str, Path],
    project_id: str | None,
    source_artifacts: list[dict[str, object]],
    source_payloads: dict[str, object],
) -> dict[str, object]:
    missing_required = _missing_required_artifacts(source_artifacts)
    untrusted = _untrusted_artifacts(source_artifacts)
    facts = _cycle_facts(source_payloads, source_artifacts)
    blockers = _cycle_blockers(
        missing_required=missing_required,
        untrusted=untrusted,
        facts=facts,
    )
    status, decision = _status_and_decision(blockers, facts)
    project = _first_text(
        project_id,
        facts["project_id"],
    )
    chain_roots = {key: roots[key].as_posix() for key in (*_input_root_keys(), "output_dir")}
    blocker_summary = _blocker_summary(blockers)
    return {
        "contract_type": _CONTRACT_TYPE,
        "authority": _AUTHORITY,
        "execution_capability": _EXECUTION_CAPABILITY,
        "project_id": project,
        "output_dir": roots["output_dir"].as_posix(),
        "cycle_contract_status": status,
        "cycle_contract_decision": decision,
        "next_allowed_action": _NEXT_ALLOWED_ACTION,
        "allowed_after_human_review": list(_ALLOWED_AFTER_HUMAN_REVIEW),
        "disallowed_actions": list(_DISALLOWED_ACTIONS),
        "chain_roots": chain_roots,
        "chain_artifact_summary": {
            "source_artifact_count": len(source_artifacts),
            "required_source_artifact_count": sum(
                1 for artifact in source_artifacts if artifact["required"] is True
            ),
            "optional_source_artifact_count": sum(
                1 for artifact in source_artifacts if artifact["required"] is not True
            ),
            "missing_required_count": len(missing_required),
            "untrusted_count": len(untrusted),
            "artifact_roots_bound": list(_input_root_keys()),
        },
        "readiness_summary": facts["readiness_summary"],
        "initial_smoke_summary": facts["initial_smoke_summary"],
        "smoke_review_summary": facts["smoke_review_summary"],
        "smoke_promotion_summary": facts["smoke_promotion_summary"],
        "iteration_summary": facts["iteration_summary"],
        "iteration_review_summary": facts["iteration_review_summary"],
        "iteration_promotion_summary": facts["iteration_promotion_summary"],
        "duplicate_summary": facts["duplicate_summary"],
        "quarantine_summary": facts["quarantine_summary"],
        "incremental_summary": facts["incremental_summary"],
        "sqlite_summary": facts["sqlite_summary"],
        "blocker_summary": blocker_summary,
        "cycle_blockers": blockers,
        "human_review_checklist": {
            "decision_options": list(_CHECKLIST_DECISION_OPTIONS),
            "human_review_required": True,
            "human_approval_required": True,
        },
        "source_artifacts": source_artifacts,
        "missing_required_artifacts": missing_required,
        "untrusted_artifacts": untrusted,
        "deterministic_ordering": True,
        **dict(_BOUNDARY_FLAGS),
        "required_human_approval": True,
        "required_human_review": True,
    }


def _cycle_facts(
    source_payloads: dict[str, object],
    source_artifacts: list[dict[str, object]],
) -> dict[str, object]:
    readiness = _dict_payload(source_payloads, "local_asset_smoke_readiness_report")
    initial_admission = _dict_payload(
        source_payloads,
        "local_asset_human_smoke_admission_receipt",
    )
    initial_scan_receipt = _dict_payload(
        source_payloads,
        "initial_scan_asset_scan_run_receipt",
    )
    initial_asset_manifest = _dict_payload(
        source_payloads,
        "initial_scan_asset_manifest",
    )
    initial_validation = _dict_payload(
        source_payloads,
        "initial_scan_asset_runtime_validation_report",
    )
    initial_quarantine = _dict_payload(
        source_payloads,
        "initial_scan_asset_runtime_quarantine_manifest",
    )
    initial_duplicates = _dict_payload(source_payloads, "initial_scan_duplicates_report")
    initial_sqlite = _dict_payload(
        source_payloads,
        "initial_scan_local_asset_sqlite_index_manifest",
    )
    initial_incremental = _dict_payload(
        source_payloads,
        "initial_scan_local_asset_incremental_scan_plan",
    )
    smoke_review = _dict_payload(source_payloads, "local_asset_smoke_review_packet")
    smoke_promotion = _dict_payload(
        source_payloads,
        "local_asset_smoke_promotion_decision",
    )
    iteration_result = _dict_payload(
        source_payloads,
        "local_asset_bounded_smoke_iteration_result",
    )
    iteration_signoff = _dict_payload(
        source_payloads,
        "local_asset_bounded_smoke_iteration_signoff",
    )
    iteration_admission = _dict_payload(
        source_payloads,
        "local_asset_bounded_smoke_iteration_admission",
    )
    iteration_scan_receipt = _dict_payload(
        source_payloads,
        "iteration_scan_asset_scan_run_receipt",
    )
    iteration_asset_manifest = _dict_payload(
        source_payloads,
        "iteration_scan_asset_manifest",
    )
    iteration_validation = _dict_payload(
        source_payloads,
        "iteration_scan_asset_runtime_validation_report",
    )
    iteration_quarantine = _dict_payload(
        source_payloads,
        "iteration_scan_asset_runtime_quarantine_manifest",
    )
    iteration_duplicates = _dict_payload(
        source_payloads,
        "iteration_scan_duplicates_report",
    )
    iteration_sqlite = _dict_payload(
        source_payloads,
        "iteration_scan_local_asset_sqlite_index_manifest",
    )
    iteration_incremental = _dict_payload(
        source_payloads,
        "iteration_scan_local_asset_incremental_scan_plan",
    )
    iteration_review = _dict_payload(
        source_payloads,
        "local_asset_smoke_iteration_review_packet",
    )
    iteration_promotion = _dict_payload(
        source_payloads,
        "local_asset_iteration_promotion_decision",
    )
    records_by_role = _records_by_role(source_artifacts)

    initial_duplicate_count = _duplicate_group_count(
        initial_scan_receipt,
        initial_asset_manifest,
        initial_validation,
        initial_duplicates,
        smoke_review,
        smoke_promotion,
    )
    iteration_duplicate_count = _duplicate_group_count(
        iteration_scan_receipt,
        iteration_asset_manifest,
        iteration_validation,
        iteration_duplicates,
        iteration_review,
        iteration_promotion,
    )
    initial_quarantine_count = _quarantined_path_count(
        initial_scan_receipt,
        initial_asset_manifest,
        initial_validation,
        initial_quarantine,
        smoke_review,
        smoke_promotion,
    )
    iteration_quarantine_count = _quarantined_path_count(
        iteration_scan_receipt,
        iteration_asset_manifest,
        iteration_validation,
        iteration_quarantine,
        iteration_review,
        iteration_promotion,
    )
    initial_incremental_counts = _incremental_counts(initial_incremental, smoke_review)
    iteration_incremental_counts = _incremental_counts(
        iteration_incremental,
        iteration_review,
        iteration_promotion,
    )
    warning_items = _warning_items(smoke_review, iteration_review)
    boundary_violations = _boundary_violations(source_payloads)
    initial_smoke_summary = {
        "admission_present": bool(
            records_by_role["local_asset_human_smoke_admission_receipt"]["exists"]
        ),
        "admitted": _first_bool(initial_admission.get("admitted"), default=False),
        "scan_launcher_invoked": _first_bool(
            initial_admission.get("scan_launcher_invoked"),
            default=False,
        ),
        "smoke_run_complete": _first_bool(
            initial_admission.get("bounded_smoke_run_performed"),
            default=False,
        ),
        "scan_complete": _first_bool(
            initial_admission.get("scan_complete"),
            initial_scan_receipt.get("status") == "completed",
            default=False,
        ),
        "files_scanned": _first_int(
            initial_scan_receipt.get("files_scanned"),
            _dict_or_empty(initial_asset_manifest.get("counts")).get("files_scanned"),
        ),
        "bytes_scanned": _first_int(
            initial_scan_receipt.get("bytes_scanned"),
            _dict_or_empty(initial_asset_manifest.get("counts")).get("bytes_scanned"),
        ),
    }
    iteration_summary = {
        "iteration_status": _first_text(iteration_result.get("iteration_status")),
        "iteration_decision": _first_text(iteration_result.get("iteration_decision")),
        "iteration_completed": _first_text(
            iteration_result.get("iteration_status")
        )
        == "iteration_completed",
        "bounded_smoke_iteration_allowed": _first_bool(
            iteration_result.get("bounded_smoke_iteration_allowed"),
            iteration_admission.get("bounded_smoke_iteration_allowed"),
            default=False,
        ),
        "bounded_smoke_iteration_performed": _first_bool(
            iteration_result.get("bounded_smoke_iteration_performed"),
            iteration_admission.get("bounded_smoke_iteration_performed"),
            default=False,
        ),
        "human_signoff_valid": _first_bool(
            iteration_result.get("human_signoff_valid"),
            iteration_signoff.get("signoff_valid"),
            default=False,
        ),
        "admitted": _first_bool(iteration_admission.get("admitted"), default=False),
        "delegated_smoke_run_complete": _first_bool(
            iteration_result.get("smoke_run_complete"),
            iteration_scan_receipt.get("status") == "completed",
            default=False,
        ),
        "delegated_scan_complete": _first_bool(
            iteration_result.get("scan_complete"),
            iteration_scan_receipt.get("status") == "completed",
            default=False,
        ),
    }
    facts = {
        "project_id": _first_text(
            readiness.get("project_id"),
            initial_admission.get("project_id"),
            initial_scan_receipt.get("project_id"),
            smoke_review.get("project_id"),
            smoke_promotion.get("project_id"),
            iteration_result.get("project_id"),
            iteration_review.get("project_id"),
            iteration_promotion.get("project_id"),
        ),
        "readiness_summary": {
            "readiness_status": _first_text(readiness.get("readiness_status")),
            "readiness_decision": _first_text(readiness.get("readiness_decision")),
            "metadata_only": _first_bool(readiness.get("metadata_only"), default=False),
            "required_human_approval": _first_bool(
                readiness.get("required_human_approval"),
                default=False,
            ),
            "inspected_entry_count": _first_int(readiness.get("inspected_entry_count")),
            "inspected_file_count": _first_int(readiness.get("inspected_file_count")),
            "estimated_total_size_bytes": _first_int(
                readiness.get("estimated_total_size_bytes")
            ),
        },
        "initial_smoke_summary": initial_smoke_summary,
        "smoke_review_summary": {
            "review_packet_status": _first_text(
                smoke_review.get("review_packet_status"),
                smoke_review.get("smoke_review_status"),
            ),
            "recommended_human_decision": _first_text(
                smoke_review.get("recommended_human_decision")
            ),
            "smoke_run_complete": _first_bool(
                smoke_review.get("smoke_run_complete"),
                _dict_or_empty(smoke_review.get("smoke_run_summary")).get(
                    "smoke_run_complete"
                ),
                default=False,
            ),
            "scan_complete": _first_bool(smoke_review.get("scan_complete"), default=False),
            "warning_count": _first_int(smoke_review.get("warning_count"), default=0),
        },
        "smoke_promotion_summary": {
            "promotion_gate_status": _first_text(
                smoke_promotion.get("promotion_gate_status")
            ),
            "promotion_decision": _first_text(smoke_promotion.get("promotion_decision")),
            "next_bounded_smoke_iteration_allowed": _first_bool(
                smoke_promotion.get("next_bounded_smoke_iteration_allowed"),
                default=False,
            ),
        },
        "iteration_summary": iteration_summary,
        "iteration_review_summary": {
            "iteration_review_status": _first_text(
                iteration_review.get("iteration_review_status")
            ),
            "recommended_human_decision": _first_text(
                iteration_review.get("recommended_human_decision"),
                iteration_review.get("iteration_review_recommended_human_decision"),
            ),
            "review_ready": _first_text(
                iteration_review.get("iteration_review_status")
            )
            == "review_ready",
            "warning_count": _first_int(iteration_review.get("warning_count"), default=0),
        },
        "iteration_promotion_summary": {
            "iteration_promotion_gate_status": _first_text(
                iteration_promotion.get("iteration_promotion_gate_status")
            ),
            "iteration_promotion_decision": _first_text(
                iteration_promotion.get("iteration_promotion_decision")
            ),
            "next_bounded_smoke_iteration_allowed": _first_bool(
                iteration_promotion.get("next_bounded_smoke_iteration_allowed"),
                default=False,
            ),
        },
        "duplicate_summary": {
            "initial_duplicate_group_count": initial_duplicate_count,
            "iteration_duplicate_group_count": iteration_duplicate_count,
            "total_duplicate_group_count": (
                initial_duplicate_count + iteration_duplicate_count
            ),
            "duplicate_deletion_performed": False,
            "recommended_action": "human_inspect_only"
            if initial_duplicate_count + iteration_duplicate_count > 0
            else "none",
        },
        "quarantine_summary": {
            "initial_quarantined_path_count": initial_quarantine_count,
            "iteration_quarantined_path_count": iteration_quarantine_count,
            "total_quarantined_path_count": (
                initial_quarantine_count + iteration_quarantine_count
            ),
        },
        "incremental_summary": {
            "initial": initial_incremental_counts,
            "iteration": iteration_incremental_counts,
            "total_changed_asset_count": (
                initial_incremental_counts["changed_asset_count"]
                + iteration_incremental_counts["changed_asset_count"]
            ),
            "total_new_asset_count": (
                initial_incremental_counts["new_asset_count"]
                + iteration_incremental_counts["new_asset_count"]
            ),
            "total_missing_asset_count": (
                initial_incremental_counts["missing_asset_count"]
                + iteration_incremental_counts["missing_asset_count"]
            ),
            "total_suspicious_change_count": (
                initial_incremental_counts["suspicious_change_count"]
                + iteration_incremental_counts["suspicious_change_count"]
            ),
            "inspection_required": _incremental_requires_inspection(
                initial_incremental_counts
            )
            or _incremental_requires_inspection(iteration_incremental_counts),
        },
        "sqlite_summary": {
            "initial_manifest_present": bool(
                records_by_role[
                    "initial_scan_local_asset_sqlite_index_manifest"
                ]["exists"]
            ),
            "iteration_manifest_present": bool(
                records_by_role[
                    "iteration_scan_local_asset_sqlite_index_manifest"
                ]["exists"]
            ),
            "initial_row_counts": _dict_or_empty(initial_sqlite.get("row_counts")),
            "iteration_row_counts": _dict_or_empty(iteration_sqlite.get("row_counts")),
            "database_opened": False,
            "candidate_files_opened": False,
            "global_database_state_used": False,
        },
        "warning_items": warning_items,
        "safe_informational_warning_count": len(
            [warning for warning in warning_items if _warning_is_safe(warning)]
        ),
        "blocking_warning_count": len(
            [warning for warning in warning_items if not _warning_is_safe(warning)]
        ),
        "boundary_violations": boundary_violations,
    }
    return facts


def _cycle_blockers(
    *,
    missing_required: list[dict[str, object]],
    untrusted: list[dict[str, object]],
    facts: dict[str, object],
) -> list[dict[str, object]]:
    blockers = []
    if missing_required:
        blockers.append(
            _blocker(
                "missing_required_artifacts",
                "required generated chain artifacts are missing",
                artifacts=[item["artifact_role"] for item in missing_required],
            )
        )
    if untrusted:
        blockers.append(
            _blocker(
                "untrusted_artifacts",
                "generated chain artifacts are untrusted, malformed, or hash mismatched",
                artifacts=[item["artifact_role"] for item in untrusted],
            )
        )
    if facts["boundary_violations"]:
        blockers.append(
            _blocker(
                "production_or_mutation_boundary_violation",
                "an upstream generated artifact claims a disallowed production or mutation action",
                violations=facts["boundary_violations"],
            )
        )
    if facts["quarantine_summary"]["total_quarantined_path_count"] > 0:
        blockers.append(
            _blocker(
                "quarantine_present",
                "quarantined paths require human inspection",
                count=facts["quarantine_summary"]["total_quarantined_path_count"],
            )
        )
    if facts["duplicate_summary"]["total_duplicate_group_count"] > 0:
        blockers.append(
            _blocker(
                "duplicate_groups_present",
                "duplicate groups require human inspection",
                count=facts["duplicate_summary"]["total_duplicate_group_count"],
            )
        )
    if facts["incremental_summary"]["inspection_required"] is True:
        blockers.append(
            _blocker(
                "incremental_changes_require_inspection",
                "incremental scan changes require human inspection",
                suspicious_change_count=facts["incremental_summary"][
                    "total_suspicious_change_count"
                ],
            )
        )
    blockers.extend(_incomplete_cycle_blockers(facts))
    if facts["blocking_warning_count"] > 0:
        blockers.append(
            _blocker(
                "blocking_warnings_present",
                "review warnings require repair before the cycle contract is ready",
                warning_count=facts["blocking_warning_count"],
            )
        )
    return sorted(blockers, key=lambda item: str(item["blocker_role"]))


def _incomplete_cycle_blockers(facts: dict[str, object]) -> list[dict[str, object]]:
    readiness = facts["readiness_summary"]
    initial_smoke = facts["initial_smoke_summary"]
    smoke_review = facts["smoke_review_summary"]
    smoke_promotion = facts["smoke_promotion_summary"]
    iteration = facts["iteration_summary"]
    iteration_review = facts["iteration_review_summary"]
    iteration_promotion = facts["iteration_promotion_summary"]
    checks = (
        (
            readiness["readiness_status"] in ("ready", "ready_with_warnings"),
            "readiness_not_ready",
            "readiness report is not ready",
            readiness["readiness_status"],
        ),
        (
            readiness["readiness_decision"] == "allow_human_review_for_future_smoke",
            "readiness_decision_not_allowed",
            "readiness decision does not allow human smoke review",
            readiness["readiness_decision"],
        ),
        (
            initial_smoke["admitted"] is True,
            "initial_smoke_not_admitted",
            "initial human smoke admission was not admitted",
            initial_smoke["admitted"],
        ),
        (
            initial_smoke["scan_complete"] is True,
            "initial_smoke_scan_incomplete",
            "initial human smoke scan is incomplete",
            initial_smoke["scan_complete"],
        ),
        (
            smoke_review["review_packet_status"] == "review_ready",
            "smoke_review_not_ready",
            "smoke review packet is not review_ready",
            smoke_review["review_packet_status"],
        ),
        (
            smoke_review["recommended_human_decision"]
            == "approve_next_bounded_smoke_iteration",
            "smoke_review_decision_not_bounded_iteration",
            "smoke review does not recommend bounded iteration only",
            smoke_review["recommended_human_decision"],
        ),
        (
            smoke_promotion["promotion_gate_status"] == "promotion_candidate",
            "smoke_promotion_not_candidate",
            "smoke promotion gate is not a promotion candidate",
            smoke_promotion["promotion_gate_status"],
        ),
        (
            smoke_promotion["promotion_decision"] == "allow_next_bounded_smoke_iteration",
            "smoke_promotion_decision_not_bounded_iteration",
            "smoke promotion did not allow bounded iteration",
            smoke_promotion["promotion_decision"],
        ),
        (
            smoke_promotion["next_bounded_smoke_iteration_allowed"] is True,
            "smoke_promotion_next_iteration_not_allowed",
            "smoke promotion did not allow next bounded smoke iteration",
            smoke_promotion["next_bounded_smoke_iteration_allowed"],
        ),
        (
            iteration["iteration_completed"] is True,
            "iteration_not_completed",
            "bounded smoke iteration is not complete",
            iteration["iteration_status"],
        ),
        (
            iteration["human_signoff_valid"] is True,
            "iteration_signoff_invalid",
            "bounded smoke iteration signoff is not valid",
            iteration["human_signoff_valid"],
        ),
        (
            iteration["delegated_smoke_run_complete"] is True,
            "delegated_smoke_run_incomplete",
            "delegated iteration smoke run is incomplete",
            iteration["delegated_smoke_run_complete"],
        ),
        (
            iteration["delegated_scan_complete"] is True,
            "delegated_iteration_scan_incomplete",
            "delegated iteration scan is incomplete",
            iteration["delegated_scan_complete"],
        ),
        (
            iteration_review["iteration_review_status"] == "review_ready",
            "iteration_review_not_ready",
            "iteration review packet is not review_ready",
            iteration_review["iteration_review_status"],
        ),
        (
            iteration_review["recommended_human_decision"]
            == "generate_promotion_gate_for_iteration",
            "iteration_review_decision_not_promotion_gate",
            "iteration review does not recommend promotion gate generation",
            iteration_review["recommended_human_decision"],
        ),
        (
            iteration_promotion["iteration_promotion_gate_status"]
            == "iteration_promotion_candidate",
            "iteration_promotion_not_candidate",
            "iteration promotion gate is not a candidate",
            iteration_promotion["iteration_promotion_gate_status"],
        ),
        (
            iteration_promotion["iteration_promotion_decision"]
            == "allow_next_bounded_smoke_iteration",
            "iteration_promotion_decision_not_bounded_iteration",
            "iteration promotion did not allow next bounded smoke iteration",
            iteration_promotion["iteration_promotion_decision"],
        ),
        (
            iteration_promotion["next_bounded_smoke_iteration_allowed"] is True,
            "iteration_promotion_next_iteration_not_allowed",
            "iteration promotion did not allow next bounded smoke iteration",
            iteration_promotion["next_bounded_smoke_iteration_allowed"],
        ),
    )
    blockers = []
    for passed, role, detail, value in checks:
        if not passed:
            blockers.append(_blocker(role, detail, value=value))
    return blockers


def _status_and_decision(
    blockers: list[dict[str, object]],
    facts: dict[str, object],
) -> tuple[str, str]:
    roles = {str(blocker["blocker_role"]) for blocker in blockers}
    if "missing_required_artifacts" in roles:
        return "blocked_missing_required_artifacts", "reject_and_repair_artifacts"
    if "untrusted_artifacts" in roles:
        return "blocked_untrusted_artifacts", "reject_and_repair_artifacts"
    if "production_or_mutation_boundary_violation" in roles:
        return (
            "blocked_production_boundary_violation",
            "reject_boundary_violation",
        )
    if "quarantine_present" in roles:
        return "blocked_quarantine", "inspect_quarantine"
    if "duplicate_groups_present" in roles:
        return "blocked_duplicates", "inspect_duplicates"
    if "incremental_changes_require_inspection" in roles:
        return "blocked_incremental_changes", "inspect_incremental_changes"
    incomplete_roles = roles - {"blocking_warnings_present"}
    if incomplete_roles:
        return "blocked_incomplete_cycle", "reject_and_repair_cycle"
    if "blocking_warnings_present" in roles:
        return "blocked_incomplete_cycle", "reject_and_repair_cycle"
    if facts["safe_informational_warning_count"] > 0:
        return (
            "cycle_contract_ready_with_warnings",
            "bind_completed_cycle_with_human_warnings",
        )
    return "cycle_contract_ready", "bind_completed_bounded_smoke_cycle"


def _missing_required_artifacts(
    source_artifacts: list[dict[str, object]],
) -> list[dict[str, object]]:
    return [
        {
            "artifact_role": artifact["artifact_role"],
            "root_key": artifact["root_key"],
            "relative_path": artifact["relative_path"],
            "required": artifact["required"],
        }
        for artifact in source_artifacts
        if artifact.get("required") is True and artifact.get("exists") is not True
    ]


def _untrusted_artifacts(
    source_artifacts: list[dict[str, object]],
) -> list[dict[str, object]]:
    return [
        {
            "artifact_role": artifact["artifact_role"],
            "root_key": artifact["root_key"],
            "relative_path": artifact["relative_path"],
            "required": artifact["required"],
            "trust_failure_reasons": artifact.get("trust_failure_reasons", []),
        }
        for artifact in source_artifacts
        if artifact.get("exists") is True
        and artifact.get("trusted_generated_artifact") is not True
    ]


def _duplicate_group_count(*payloads: dict[str, object]) -> int:
    values = []
    for payload in payloads:
        counts = _dict_or_empty(payload.get("counts"))
        duplicate_summary = _dict_or_empty(payload.get("duplicate_summary"))
        delegated_scan = _dict_or_empty(payload.get("delegated_scan_summary"))
        groups = payload.get("duplicate_groups")
        values.extend(
            [
                payload.get("duplicate_group_count"),
                payload.get("duplicate_groups")
                if not isinstance(payload.get("duplicate_groups"), list)
                else None,
                payload.get("duplicate_sha256_group_count"),
                counts.get("duplicate_sha256_groups"),
                duplicate_summary.get("duplicate_group_count"),
                delegated_scan.get("duplicate_group_count"),
                len(groups) if isinstance(groups, list) else None,
            ]
        )
    return max([_coerce_int(value, default=0) for value in values] or [0])


def _quarantined_path_count(*payloads: dict[str, object]) -> int:
    values = []
    for payload in payloads:
        counts = _dict_or_empty(payload.get("counts"))
        quarantine_summary = _dict_or_empty(payload.get("quarantine_summary"))
        delegated_scan = _dict_or_empty(payload.get("delegated_scan_summary"))
        values.extend(
            [
                payload.get("quarantined_path_count"),
                payload.get("quarantined_paths"),
                counts.get("quarantined_paths"),
                quarantine_summary.get("quarantined_path_count"),
                delegated_scan.get("quarantined_path_count"),
            ]
        )
    return max([_coerce_int(value, default=0) for value in values] or [0])


def _incremental_counts(
    incremental_plan: dict[str, object],
    *summary_payloads: dict[str, object],
) -> dict[str, object]:
    summaries = [_dict_or_empty(payload.get("incremental_summary")) for payload in summary_payloads]
    return {
        "plan_present": bool(incremental_plan),
        "plan_mode": _first_text(
            incremental_plan.get("plan_mode"),
            *[summary.get("plan_mode") for summary in summaries],
        ),
        "unchanged_asset_count": _first_int(
            incremental_plan.get("unchanged_asset_count"),
            *[summary.get("unchanged_asset_count") for summary in summaries],
            default=0,
        ),
        "changed_asset_count": _first_int(
            incremental_plan.get("changed_asset_count"),
            *[summary.get("changed_asset_count") for summary in summaries],
            default=0,
        ),
        "new_asset_count": _first_int(
            incremental_plan.get("new_asset_count"),
            *[summary.get("new_asset_count") for summary in summaries],
            default=0,
        ),
        "missing_asset_count": _first_int(
            incremental_plan.get("missing_asset_count"),
            *[summary.get("missing_asset_count") for summary in summaries],
            default=0,
        ),
        "suspicious_change_count": _first_int(
            incremental_plan.get("suspicious_change_count"),
            *[summary.get("suspicious_change_count") for summary in summaries],
            default=0,
        ),
    }


def _incremental_requires_inspection(counts: dict[str, object]) -> bool:
    if int(counts["suspicious_change_count"]) > 0:
        return True
    return counts["plan_mode"] == "compare_previous_scan" and (
        int(counts["changed_asset_count"]) > 0
        or int(counts["new_asset_count"]) > 0
        or int(counts["missing_asset_count"]) > 0
    )


def _warning_items(*payloads: dict[str, object]) -> list[str]:
    warnings: list[str] = []
    for payload in payloads:
        warning_summary = _dict_or_empty(payload.get("warning_summary"))
        warnings.extend(_string_list(payload.get("warnings")))
        warnings.extend(_string_list(warning_summary.get("warnings")))
    return sorted(set(warnings))


def _warning_is_safe(warning: str) -> bool:
    text = str(warning)
    return (
        text in _SAFE_INFORMATIONAL_WARNINGS
        or text.startswith("informational:")
        or text.startswith("info:")
    )


def _boundary_violations(source_payloads: dict[str, object]) -> list[dict[str, object]]:
    violations = []
    for role in sorted(source_payloads):
        payload = _dict_payload(source_payloads, role)
        for field_name in _PRODUCTION_OR_MUTATION_FIELDS:
            if payload.get(field_name) is True:
                violations.append(
                    {
                        "artifact_role": role,
                        "field": field_name,
                        "value": True,
                    }
                )
    return violations


def _blocker(blocker_role: str, detail: str, **extra: object) -> dict[str, object]:
    item = {
        "blocker_role": blocker_role,
        "severity": "blocking",
        "detail": detail,
    }
    item.update(extra)
    return item


def _blocker_summary(blockers: list[dict[str, object]]) -> dict[str, object]:
    roles = [str(blocker["blocker_role"]) for blocker in blockers]
    return {
        "cycle_blocker_count": len(blockers),
        "blocker_count": len(blockers),
        "blocker_roles": sorted(roles),
        "has_blockers": bool(blockers),
    }


def _summary_markdown(contract: dict[str, object]) -> str:
    chain_roots = _dict_or_empty(contract["chain_roots"])
    blocker_summary = _dict_or_empty(contract["blocker_summary"])
    lines = [
        "# Local Asset Bounded Smoke Cycle Contract",
        "",
        "Cycle contract status: " + str(contract["cycle_contract_status"]),
        "Cycle contract decision: " + str(contract["cycle_contract_decision"]),
        "Next allowed action: " + str(contract["next_allowed_action"]),
        "Allowed after human review: "
        + ", ".join(_string_list(contract["allowed_after_human_review"])),
        "Disallowed actions: " + ", ".join(_string_list(contract["disallowed_actions"])),
        "",
        "## Chain Roots",
    ]
    for key in sorted(chain_roots):
        lines.append("- " + key + ": " + str(chain_roots[key]))
    lines.extend(
        [
            "",
            "## Stage Summaries",
            "- Readiness: " + _compact_json(contract["readiness_summary"]),
            "- Initial smoke: " + _compact_json(contract["initial_smoke_summary"]),
            "- Smoke review: " + _compact_json(contract["smoke_review_summary"]),
            "- Smoke promotion: " + _compact_json(contract["smoke_promotion_summary"]),
            "- Iteration: " + _compact_json(contract["iteration_summary"]),
            "- Iteration review: " + _compact_json(contract["iteration_review_summary"]),
            "- Iteration promotion: "
            + _compact_json(contract["iteration_promotion_summary"]),
            "",
            "## Risk Summaries",
            "- Duplicate summary: " + _compact_json(contract["duplicate_summary"]),
            "- Quarantine summary: " + _compact_json(contract["quarantine_summary"]),
            "- Incremental summary: " + _compact_json(contract["incremental_summary"]),
            "- SQLite summary: " + _compact_json(contract["sqlite_summary"]),
            "- Blocker summary: " + _compact_json(blocker_summary),
            "",
            "Source artifact count: "
            + str(_dict_or_empty(contract["chain_artifact_summary"]).get("source_artifact_count")),
            "Missing required count: "
            + str(_dict_or_empty(contract["chain_artifact_summary"]).get("missing_required_count")),
            "Untrusted count: "
            + str(_dict_or_empty(contract["chain_artifact_summary"]).get("untrusted_count")),
            "",
            "## Explicit Boundaries",
            "- no runtime stage executed",
            "- no raw candidate content read",
            "- no candidate hashing",
            "- no upstream mutation",
            "- no file mutation",
            "- no duplicate deletion",
            "- no media organizer",
            "- no network",
            "- no model API",
            "- no external runtime",
            "- no production scan approval",
            "- no production promotion",
            "- no automatic approval",
            "- human review required",
        ]
    )
    return "\n".join(lines) + "\n"


def _human_review_checklist_markdown(contract: dict[str, object]) -> str:
    lines = [
        "# Local Asset Bounded Smoke Cycle Human Review Checklist",
        "",
        "- [ ] Verify all stage artifacts exist and are trusted.",
        "- [ ] Verify initial smoke admitted and complete.",
        "- [ ] Verify smoke review status.",
        "- [ ] Verify smoke promotion allowed bounded iteration only.",
        "- [ ] Verify iteration completed.",
        "- [ ] Verify iteration signoff valid.",
        "- [ ] Verify iteration review status review_ready.",
        "- [ ] Verify iteration promotion candidate.",
        "- [ ] Verify next bounded smoke iteration allowed only after human review.",
        "- [ ] Verify production flags are false.",
        "- [ ] Verify mutation flags are false.",
        "- [ ] Verify quarantine count is zero.",
        "- [ ] Verify duplicate group count is zero.",
        "- [ ] Verify suspicious incremental change count is zero.",
        "- [ ] Verify no blocker exists.",
        "- [ ] Verify no raw private content included.",
        "",
        "## Decision Options",
    ]
    lines.extend("- " + option for option in _CHECKLIST_DECISION_OPTIONS)
    lines.extend(
        [
            "",
            "Cycle contract status: " + str(contract["cycle_contract_status"]),
            "Cycle contract decision: " + str(contract["cycle_contract_decision"]),
        ]
    )
    return "\n".join(lines) + "\n"


def _contract_manifest_payload(
    paths: dict[str, Path],
    source_artifacts: list[dict[str, object]],
    contract: dict[str, object],
) -> dict[str, object]:
    contract_path = paths[LOCAL_ASSET_BOUNDED_SMOKE_CYCLE_CONTRACT_FILE]
    summary_path = paths[LOCAL_ASSET_BOUNDED_SMOKE_CYCLE_SUMMARY_FILE]
    checklist_path = paths[LOCAL_ASSET_BOUNDED_SMOKE_CYCLE_HUMAN_REVIEW_CHECKLIST_FILE]
    manifest = {
        "manifest_type": _MANIFEST_TYPE,
        "authority": _AUTHORITY,
        "contract_path": contract_path.as_posix(),
        "summary_path": summary_path.as_posix(),
        "human_review_checklist_path": checklist_path.as_posix(),
        "contract_sha256": sha256_file(contract_path),
        "summary_sha256": sha256_file(summary_path),
        "human_review_checklist_sha256": sha256_file(checklist_path),
        "source_artifacts": [
            {
                "role": artifact["artifact_role"],
                "artifact_role": artifact["artifact_role"],
                "path": artifact["path"],
                "sha256": artifact["sha256"],
                "size_bytes": artifact["size_bytes"],
                "exists": artifact["exists"],
                "required": artifact["required"],
                "trusted_generated_artifact": artifact[
                    "trusted_generated_artifact"
                ],
            }
            for artifact in source_artifacts
        ],
        "cycle_contract_status": contract["cycle_contract_status"],
        "cycle_contract_decision": contract["cycle_contract_decision"],
        "deterministic_ordering": True,
        **dict(_BOUNDARY_FLAGS),
        "required_human_approval": True,
        "required_human_review": True,
        "next_allowed_action": _NEXT_ALLOWED_ACTION,
    }
    return manifest


def _artifact_index_payload(
    output_dir: Path,
    paths: dict[str, Path],
) -> dict[str, object]:
    entries = [
        _artifact_entry(output_dir, role, paths[file_name])
        for role, file_name in _CONTRACT_ARTIFACTS
    ]
    return {
        "index_type": _INDEX_TYPE,
        "authority": _AUTHORITY,
        "execution_capability": _EXECUTION_CAPABILITY,
        "job_dir": output_dir.as_posix(),
        "artifact_index_strategy": "explicit_cycle_contract_artifacts_only",
        "indexed_artifacts": len(entries),
        "entries": entries,
        "content_indexed": False,
        "raw_content_copied": False,
        "candidate_input_files_indexed": False,
        "upstream_artifacts_recursively_indexed": False,
        "deterministic_ordering": True,
        **dict(_BOUNDARY_FLAGS),
        "required_human_approval": True,
        "required_human_review": True,
        "next_allowed_action": _NEXT_ALLOWED_ACTION,
    }


def _artifact_index_manifest_payload(
    output_dir: Path,
    paths: dict[str, Path],
    artifact_index: dict[str, object],
) -> dict[str, object]:
    entries = artifact_index["entries"]
    return {
        "manifest_type": _INDEX_MANIFEST_TYPE,
        "authority": _AUTHORITY,
        "artifact_index_path": paths[_ARTIFACT_INDEX_FILE].as_posix(),
        "artifact_index_sha256": sha256_file(paths[_ARTIFACT_INDEX_FILE]),
        "indexed_artifacts": len(entries),
        "artifact_roles": {
            str(entry["artifact_role"]): str(entry["path"]) for entry in entries
        },
        "indexed_relative_paths": [str(entry["relative_path"]) for entry in entries],
        "job_dir": output_dir.as_posix(),
        "deterministic_ordering": True,
        "content_indexed": False,
        "raw_content_copied": False,
        "candidate_input_files_indexed": False,
        "upstream_artifacts_recursively_indexed": False,
        **dict(_BOUNDARY_FLAGS),
        "required_human_approval": True,
        "required_human_review": True,
        "next_allowed_action": _NEXT_ALLOWED_ACTION,
    }


def _artifact_entry(output_dir: Path, role: str, path: Path) -> dict[str, object]:
    return {
        "artifact_role": role,
        "path": path.as_posix(),
        "relative_path": path.relative_to(output_dir).as_posix(),
        "sha256": sha256_file(path),
        "size_bytes": path.stat().st_size,
        "exists": path.exists(),
        "content_indexed": False,
        "raw_content_copied": False,
    }


def _launcher_payload_from_contract(
    contract: dict[str, object],
    paths: dict[str, Path],
    *,
    complete: bool,
) -> dict[str, object]:
    chain_roots = _dict_or_empty(contract["chain_roots"])
    payload = {
        "complete": complete,
        "artifacts_written": True,
        "local_asset_bounded_smoke_cycle_contract_path": paths[
            LOCAL_ASSET_BOUNDED_SMOKE_CYCLE_CONTRACT_FILE
        ].as_posix(),
        "local_asset_bounded_smoke_cycle_contract_manifest_path": paths[
            LOCAL_ASSET_BOUNDED_SMOKE_CYCLE_CONTRACT_MANIFEST_FILE
        ].as_posix(),
        "local_asset_bounded_smoke_cycle_summary_path": paths[
            LOCAL_ASSET_BOUNDED_SMOKE_CYCLE_SUMMARY_FILE
        ].as_posix(),
        "local_asset_bounded_smoke_cycle_human_review_checklist_path": paths[
            LOCAL_ASSET_BOUNDED_SMOKE_CYCLE_HUMAN_REVIEW_CHECKLIST_FILE
        ].as_posix(),
        "artifact_index_path": paths[_ARTIFACT_INDEX_FILE].as_posix(),
        "artifact_index_manifest_path": paths[_ARTIFACT_INDEX_MANIFEST_FILE].as_posix(),
        "project_id": contract["project_id"],
        "cycle_contract_status": contract["cycle_contract_status"],
        "cycle_contract_decision": contract["cycle_contract_decision"],
        "next_allowed_action": contract["next_allowed_action"],
        "allowed_after_human_review": contract["allowed_after_human_review"],
        "disallowed_actions": contract["disallowed_actions"],
        "cycle_blocker_count": _dict_or_empty(contract["blocker_summary"])[
            "cycle_blocker_count"
        ],
        "cycle_blockers": contract["cycle_blockers"],
        "required_human_approval": True,
        "required_human_review": True,
    }
    for key in (*_input_root_keys(), "output_dir"):
        payload[key] = chain_roots.get(key)
    payload.update(_BOUNDARY_FLAGS)
    return payload


def _structured_failure_result(
    roots: dict[str, Path],
    *,
    project_id: str | None,
    failure_stage: str,
    error_message: str,
) -> LocalAssetBoundedSmokeCycleContractResult:
    blocker = _blocker("preflight_failure", error_message)
    status = "blocked_unknown"
    decision = "reject_and_repair_artifacts"
    payload = {
        "complete": False,
        "artifacts_written": False,
        "contract_type": _CONTRACT_TYPE,
        "authority": _AUTHORITY,
        "execution_capability": _EXECUTION_CAPABILITY,
        "project_id": project_id,
        "output_dir": roots["output_dir"].as_posix(),
        "chain_roots": {
            key: roots[key].as_posix() for key in (*_input_root_keys(), "output_dir")
        },
        "cycle_contract_status": status,
        "cycle_contract_decision": decision,
        "next_allowed_action": "repair_cycle_contract_preflight",
        "allowed_after_human_review": list(_ALLOWED_AFTER_HUMAN_REVIEW),
        "disallowed_actions": list(_DISALLOWED_ACTIONS),
        "cycle_blocker_count": 1,
        "cycle_blockers": [blocker],
        "blocker_summary": _blocker_summary([blocker]),
        "failure_stage": failure_stage,
        "error_type": "ValueError",
        "error_message": error_message,
        "local_asset_bounded_smoke_cycle_contract_path": None,
        "local_asset_bounded_smoke_cycle_contract_manifest_path": None,
        "local_asset_bounded_smoke_cycle_summary_path": None,
        "local_asset_bounded_smoke_cycle_human_review_checklist_path": None,
        "artifact_index_path": None,
        "artifact_index_manifest_path": None,
        **dict(_BOUNDARY_FLAGS),
        "required_human_approval": True,
        "required_human_review": True,
    }
    return LocalAssetBoundedSmokeCycleContractResult(
        readiness_output_dir=roots["readiness_output_dir"],
        smoke_output_dir=roots["smoke_output_dir"],
        smoke_review_output_dir=roots["smoke_review_output_dir"],
        smoke_promotion_output_dir=roots["smoke_promotion_output_dir"],
        iteration_output_dir=roots["iteration_output_dir"],
        iteration_review_output_dir=roots["iteration_review_output_dir"],
        iteration_promotion_output_dir=roots["iteration_promotion_output_dir"],
        output_dir=roots["output_dir"],
        contract_path=None,
        contract_manifest_path=None,
        summary_path=None,
        human_review_checklist_path=None,
        artifact_index_path=None,
        artifact_index_manifest_path=None,
        complete=False,
        cycle_contract_status=status,
        cycle_contract_decision=decision,
        payload=payload,
    )


def _records_by_role(
    source_artifacts: list[dict[str, object]],
) -> dict[str, dict[str, object]]:
    return {str(record["artifact_role"]): record for record in source_artifacts}


def _dict_payload(
    source_payloads: dict[str, object],
    role: str,
) -> dict[str, object]:
    return _dict_or_empty(source_payloads.get(role))


def _dict_or_empty(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def _list_or_empty(value: object) -> list[object]:
    return value if isinstance(value, list) else []


def _string_list(value: object) -> list[str]:
    return [str(item) for item in _list_or_empty(value)]


def _first_text(*values: object) -> str | None:
    for value in values:
        if isinstance(value, str) and value:
            return value
    return None


def _first_bool(*values: object, default: bool | None = None) -> bool | None:
    for value in values:
        if isinstance(value, bool):
            return value
    return default


def _first_int(*values: object, default: int | None = None) -> int | None:
    for value in values:
        coerced = _coerce_int(value, default=None)
        if coerced is not None:
            return coerced
    return default


def _coerce_int(value: object, *, default: int | None = None) -> int | None:
    if isinstance(value, bool):
        return default
    if isinstance(value, int):
        return value
    return default


def _compact_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _write_json_exclusive(path: Path, payload: dict[str, object]) -> None:
    with path.open("x", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")


def _write_text_exclusive(path: Path, content: str) -> None:
    with path.open("x", encoding="utf-8") as handle:
        handle.write(content)
