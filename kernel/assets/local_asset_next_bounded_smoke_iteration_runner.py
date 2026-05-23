"""Execute one admitted next bounded local asset smoke iteration."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import hashlib
import json
import os

from kernel.personal_ai.hash_utils import sha256_file

__all__ = [
    "LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUNNER_FILE",
    "LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUNNER_MANIFEST_FILE",
    "LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUNNER_SUMMARY_FILE",
    "LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUNNER_CHECKLIST_FILE",
    "LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUN_FILE",
    "LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUN_MANIFEST_FILE",
    "LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_CANDIDATE_MANIFEST_FILE",
    "LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_SUMMARY_FILE",
    "LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_CHECKLIST_FILE",
    "REQUIRED_LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUNNER_ACKNOWLEDGEMENT_PHRASE",
    "LocalAssetNextBoundedSmokeIterationRunnerResult",
    "build_local_asset_next_bounded_smoke_iteration_runner",
]


LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUNNER_FILE = (
    "local_asset_next_bounded_smoke_iteration_runner.json"
)
LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUNNER_MANIFEST_FILE = (
    "local_asset_next_bounded_smoke_iteration_runner_manifest.json"
)
LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUNNER_SUMMARY_FILE = (
    "local_asset_next_bounded_smoke_iteration_runner_summary.md"
)
LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUNNER_CHECKLIST_FILE = (
    "local_asset_next_bounded_smoke_iteration_runner_checklist.md"
)

LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUN_FILE = (
    "local_asset_next_bounded_smoke_iteration_run.json"
)
LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUN_MANIFEST_FILE = (
    "local_asset_next_bounded_smoke_iteration_run_manifest.json"
)
LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_CANDIDATE_MANIFEST_FILE = (
    "local_asset_next_bounded_smoke_iteration_candidate_manifest.json"
)
LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_SUMMARY_FILE = (
    "local_asset_next_bounded_smoke_iteration_summary.md"
)
LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_CHECKLIST_FILE = (
    "local_asset_next_bounded_smoke_iteration_checklist.md"
)

REQUIRED_LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUNNER_ACKNOWLEDGEMENT_PHRASE = (
    "I_EXECUTE_LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_UNDER_ADMITTED_LIMITS"
)

_ARTIFACT_INDEX_FILE = "artifact_index.json"
_ARTIFACT_INDEX_MANIFEST_FILE = "artifact_index_manifest.json"

_RUNNER_TYPE = "local_asset_next_bounded_smoke_iteration_runner_v1"
_RUNNER_MANIFEST_TYPE = "local_asset_next_bounded_smoke_iteration_runner_manifest_v1"
_RUNNER_INDEX_TYPE = "local_asset_next_bounded_smoke_iteration_runner_artifact_index_v1"
_RUNNER_INDEX_MANIFEST_TYPE = (
    "local_asset_next_bounded_smoke_iteration_runner_artifact_index_manifest_v1"
)
_ITERATION_RUN_TYPE = "local_asset_next_bounded_smoke_iteration_run_v1"
_ITERATION_RUN_MANIFEST_TYPE = (
    "local_asset_next_bounded_smoke_iteration_run_manifest_v1"
)
_CANDIDATE_MANIFEST_TYPE = (
    "local_asset_next_bounded_smoke_iteration_candidate_manifest_v1"
)
_ITERATION_INDEX_TYPE = (
    "local_asset_next_bounded_smoke_iteration_artifact_index_v1"
)
_ITERATION_INDEX_MANIFEST_TYPE = (
    "local_asset_next_bounded_smoke_iteration_artifact_index_manifest_v1"
)
_AUTHORITY = "bounded_smoke_runner_record"
_EXECUTION_CAPABILITY = "local_asset_next_bounded_smoke_iteration_runner_only"

_SOURCE_ADMISSION_TYPE = "local_asset_next_bounded_smoke_iteration_runner_admission_v1"
_SOURCE_ADMISSION_MANIFEST_TYPE = (
    "local_asset_next_bounded_smoke_iteration_runner_admission_manifest_v1"
)
_SOURCE_ADMISSION_INDEX_TYPE = (
    "local_asset_next_bounded_smoke_iteration_runner_admission_artifact_index_v1"
)
_SOURCE_ADMISSION_INDEX_MANIFEST_TYPE = (
    "local_asset_next_bounded_smoke_iteration_runner_admission_artifact_index_manifest_v1"
)
_SOURCE_READY_STATUS = "next_bounded_smoke_iteration_runner_admission_ready"
_SOURCE_READY_DECISION = "admit_runner_to_consume_future_execution_request"
_SOURCE_READY_NEXT_ACTION = "await_separate_bounded_smoke_iteration_runner_execution"

_COMPLETED_STATUS = "next_bounded_smoke_iteration_runner_completed"
_COMPLETED_DECISION = "executed_bounded_smoke_iteration_under_admitted_limits"
_COMPLETED_NEXT_ACTION = "review_next_bounded_smoke_iteration_run"

_RUNNER_OUTPUT_FILES = (
    LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUNNER_FILE,
    LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUNNER_MANIFEST_FILE,
    LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUNNER_SUMMARY_FILE,
    LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUNNER_CHECKLIST_FILE,
    _ARTIFACT_INDEX_FILE,
    _ARTIFACT_INDEX_MANIFEST_FILE,
)

_ITERATION_OUTPUT_FILES = (
    LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUN_FILE,
    LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUN_MANIFEST_FILE,
    LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_CANDIDATE_MANIFEST_FILE,
    LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_SUMMARY_FILE,
    LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_CHECKLIST_FILE,
    _ARTIFACT_INDEX_FILE,
    _ARTIFACT_INDEX_MANIFEST_FILE,
)

_RUNNER_ARTIFACTS = (
    (
        "local_asset_next_bounded_smoke_iteration_runner",
        LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUNNER_FILE,
    ),
    (
        "local_asset_next_bounded_smoke_iteration_runner_manifest",
        LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUNNER_MANIFEST_FILE,
    ),
    (
        "local_asset_next_bounded_smoke_iteration_runner_summary",
        LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUNNER_SUMMARY_FILE,
    ),
    (
        "local_asset_next_bounded_smoke_iteration_runner_checklist",
        LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUNNER_CHECKLIST_FILE,
    ),
)

_ITERATION_ARTIFACTS = (
    (
        "local_asset_next_bounded_smoke_iteration_run",
        LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUN_FILE,
    ),
    (
        "local_asset_next_bounded_smoke_iteration_run_manifest",
        LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUN_MANIFEST_FILE,
    ),
    (
        "local_asset_next_bounded_smoke_iteration_candidate_manifest",
        LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_CANDIDATE_MANIFEST_FILE,
    ),
    (
        "local_asset_next_bounded_smoke_iteration_summary",
        LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_SUMMARY_FILE,
    ),
    (
        "local_asset_next_bounded_smoke_iteration_checklist",
        LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_CHECKLIST_FILE,
    ),
)

_SOURCE_ARTIFACT_SPECS = (
    (
        "local_asset_next_bounded_smoke_iteration_runner_admission",
        "local_asset_next_bounded_smoke_iteration_runner_admission.json",
        True,
        "admission_type",
        _SOURCE_ADMISSION_TYPE,
    ),
    (
        "local_asset_next_bounded_smoke_iteration_runner_admission_manifest",
        "local_asset_next_bounded_smoke_iteration_runner_admission_manifest.json",
        True,
        "manifest_type",
        _SOURCE_ADMISSION_MANIFEST_TYPE,
    ),
    (
        "local_asset_next_bounded_smoke_iteration_runner_admission_artifact_index",
        "artifact_index.json",
        True,
        "index_type",
        _SOURCE_ADMISSION_INDEX_TYPE,
    ),
    (
        "local_asset_next_bounded_smoke_iteration_runner_admission_artifact_index_manifest",
        "artifact_index_manifest.json",
        True,
        "manifest_type",
        _SOURCE_ADMISSION_INDEX_MANIFEST_TYPE,
    ),
    (
        "local_asset_next_bounded_smoke_iteration_runner_admission_summary",
        "local_asset_next_bounded_smoke_iteration_runner_admission_summary.md",
        False,
        None,
        None,
    ),
    (
        "local_asset_next_bounded_smoke_iteration_runner_admission_checklist",
        "local_asset_next_bounded_smoke_iteration_runner_admission_checklist.md",
        False,
        None,
        None,
    ),
)

_DISALLOWED_ACTIONS = (
    "production_scan",
    "production_promotion",
    "automatic_approval",
    "autonomous_execution",
    "candidate_file_mutation",
    "file_move",
    "file_rename",
    "file_delete",
    "duplicate_deletion",
    "media_organizer_behavior",
    "network_access",
    "model_api_call",
    "external_runtime_invocation",
)

_BOUNDARY_FALSE_FLAGS = {
    "scan_performed": False,
    "readiness_run_performed": False,
    "human_smoke_run_performed": False,
    "smoke_review_packet_run_performed": False,
    "smoke_promotion_gate_run_performed": False,
    "iteration_review_packet_run_performed": False,
    "iteration_promotion_gate_run_performed": False,
    "cycle_contract_run_performed": False,
    "cycle_human_review_run_performed": False,
    "next_admission_run_performed": False,
    "execution_request_run_performed": False,
    "runner_admission_run_performed": False,
    "raw_candidate_content_copied": False,
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
    "production_scan_performed": False,
    "production_scan_recommended": False,
    "production_scan_approved": False,
    "production_promotion_granted": False,
    "automatic_approval_performed": False,
    "autonomous_execution_performed": False,
}

_SOURCE_FALSE_FIELDS = (
    "runner_execution_allowed",
    "next_bounded_smoke_iteration_execute_allowed",
    "next_bounded_smoke_iteration_executed",
    "next_iteration_output_dir_created",
    "requested_next_iteration_output_dir_created",
    "candidate_input_path_checked",
    "candidate_input_path_listed",
    "candidate_input_file_read",
    "candidate_input_file_hashing_performed",
    "production_scan_approved",
    "production_promotion_granted",
    "automatic_approval_performed",
    "autonomous_execution_performed",
)

_SOURCE_CANDIDATE_ACCESS_FIELDS = (
    "candidate_input_path_checked",
    "candidate_input_path_listed",
    "candidate_input_file_read",
    "candidate_input_file_hashing_performed",
)

_SOURCE_EXECUTION_ALREADY_ALLOWED_FIELDS = (
    "runner_execution_allowed",
    "next_bounded_smoke_iteration_execute_allowed",
)

_SOURCE_OUTPUT_CREATED_FIELDS = (
    "next_iteration_output_dir_created",
    "requested_next_iteration_output_dir_created",
)

_SOURCE_PRODUCTION_FIELDS = (
    "production_scan_approved",
    "production_promotion_granted",
    "automatic_approval_performed",
    "autonomous_execution_performed",
)

_SOURCE_TRUE_FIELDS = (
    "required_human_approval",
    "required_human_review",
)

_SOURCE_REQUIRED_BOOLEAN_FIELDS = _SOURCE_FALSE_FIELDS + _SOURCE_TRUE_FIELDS


@dataclass(frozen=True)
class LocalAssetNextBoundedSmokeIterationRunnerResult:
    runner_admission_output_dir: Path
    runner_output_dir: Path
    actual_next_iteration_output_dir: Path
    runner_path: Path | None
    runner_manifest_path: Path | None
    runner_summary_path: Path | None
    runner_checklist_path: Path | None
    artifact_index_path: Path | None
    artifact_index_manifest_path: Path | None
    actual_iteration_artifacts: list[dict[str, object]]
    complete: bool
    runner_status: str
    runner_decision: str
    payload: dict[str, object]


def build_local_asset_next_bounded_smoke_iteration_runner(
    runner_admission_output_dir: Path,
    runner_output_dir: Path,
    actual_next_iteration_output_dir: Path,
    *,
    runner_execution_id: str,
    runner_operator_id: str,
    runner_execution_acknowledgement_phrase: str,
    project_id: str | None = None,
    operator_notes: str | None = None,
) -> LocalAssetNextBoundedSmokeIterationRunnerResult:
    """Execute one bounded next smoke iteration after runner admission."""

    roots = {
        "runner_admission_output_dir": Path(runner_admission_output_dir),
        "runner_output_dir": Path(runner_output_dir),
        "actual_next_iteration_output_dir": Path(actual_next_iteration_output_dir),
    }
    runner_paths = _runner_output_paths(roots["runner_output_dir"])
    actual_paths = _iteration_output_paths(roots["actual_next_iteration_output_dir"])
    inputs = _runner_inputs(
        runner_execution_id=runner_execution_id,
        runner_operator_id=runner_operator_id,
        runner_execution_acknowledgement_phrase=(
            runner_execution_acknowledgement_phrase
        ),
        project_id=project_id,
        operator_notes=operator_notes,
    )

    runner_preflight_error = _runner_output_preflight_error(roots, runner_paths)
    if runner_preflight_error is not None:
        return _structured_failure_result(
            roots,
            inputs,
            failure_stage=runner_preflight_error["failure_stage"],
            error_message=runner_preflight_error["error_message"],
        )

    hard_overlap_error = _hard_overlap_preflight_error(roots)
    if hard_overlap_error is not None:
        return _structured_failure_result(
            roots,
            inputs,
            failure_stage=hard_overlap_error["failure_stage"],
            error_message=hard_overlap_error["error_message"],
        )

    source_root_error = _real_existing_dir_error(
        roots["runner_admission_output_dir"],
        "runner_admission_output_dir",
    )
    source_artifacts = _source_artifact_records(
        roots["runner_admission_output_dir"],
        source_root_error=source_root_error,
    )
    source_payloads = _read_json_source_payloads(source_artifacts)
    _mark_source_trust(source_artifacts, source_payloads)
    admission = _dict_payload(
        source_payloads,
        "local_asset_next_bounded_smoke_iteration_runner_admission",
    )

    candidate_state = _empty_candidate_state()
    actual_iteration_artifacts: list[dict[str, object]] = []
    status, decision, next_action, blockers = _pre_candidate_outcome(
        roots=roots,
        inputs=inputs,
        source_root_error=source_root_error,
        source_artifacts=source_artifacts,
        admission=admission,
        actual_paths=actual_paths,
    )

    if status == _COMPLETED_STATUS:
        candidate_state = _discover_candidate_files(
            Path(str(admission["requested_candidate_input_dir"])),
            _admitted_limits(admission),
        )
        if candidate_state["blocked"]:
            status = str(candidate_state["blocked_status"])
            decision, next_action = _blocked_decision_and_action(status)
            blockers = list(candidate_state["blockers"])

    if status == _COMPLETED_STATUS:
        try:
            actual_iteration_artifacts = _write_actual_iteration_artifacts(
                roots=roots,
                actual_paths=actual_paths,
                inputs=inputs,
                admission=admission,
                candidate_state=candidate_state,
            )
        except Exception as exc:  # pragma: no cover - defensive fail-closed path
            status = "blocked_iteration_execution_failure"
            decision, next_action = _blocked_decision_and_action(status)
            blockers = [
                _blocker(
                    "iteration_artifact_write_failed",
                    "actual iteration artifacts could not be written",
                    error_message=str(exc),
                )
            ]
            actual_iteration_artifacts = []

    runner_payload = _runner_payload(
        roots=roots,
        inputs=inputs,
        admission=admission,
        source_artifacts=source_artifacts,
        candidate_state=candidate_state,
        actual_iteration_artifacts=actual_iteration_artifacts,
        status=status,
        decision=decision,
        next_action=next_action,
        blockers=blockers,
    )
    _write_runner_artifacts(
        roots=roots,
        runner_paths=runner_paths,
        runner_payload=runner_payload,
        source_artifacts=source_artifacts,
        actual_iteration_artifacts=actual_iteration_artifacts,
    )
    complete = status == _COMPLETED_STATUS
    payload = _launcher_payload_from_runner(
        runner_payload,
        runner_paths,
        actual_iteration_artifacts,
        complete=complete,
        artifacts_written=True,
    )
    return LocalAssetNextBoundedSmokeIterationRunnerResult(
        runner_admission_output_dir=roots["runner_admission_output_dir"],
        runner_output_dir=roots["runner_output_dir"],
        actual_next_iteration_output_dir=roots["actual_next_iteration_output_dir"],
        runner_path=runner_paths[LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUNNER_FILE],
        runner_manifest_path=runner_paths[
            LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUNNER_MANIFEST_FILE
        ],
        runner_summary_path=runner_paths[
            LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUNNER_SUMMARY_FILE
        ],
        runner_checklist_path=runner_paths[
            LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUNNER_CHECKLIST_FILE
        ],
        artifact_index_path=runner_paths[_ARTIFACT_INDEX_FILE],
        artifact_index_manifest_path=runner_paths[_ARTIFACT_INDEX_MANIFEST_FILE],
        actual_iteration_artifacts=actual_iteration_artifacts,
        complete=complete,
        runner_status=status,
        runner_decision=decision,
        payload=payload,
    )


def _runner_inputs(
    *,
    runner_execution_id: object,
    runner_operator_id: object,
    runner_execution_acknowledgement_phrase: object,
    project_id: object,
    operator_notes: object,
) -> dict[str, object]:
    phrase = (
        runner_execution_acknowledgement_phrase
        if isinstance(runner_execution_acknowledgement_phrase, str)
        else ""
    )
    return {
        "runner_execution_id": runner_execution_id,
        "runner_operator_id": runner_operator_id,
        "runner_execution_acknowledgement_phrase_sha256": _sha256_text(phrase),
        "runner_execution_acknowledgement_phrase_valid": (
            runner_execution_acknowledgement_phrase
            == REQUIRED_LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUNNER_ACKNOWLEDGEMENT_PHRASE
        ),
        "project_id": project_id,
        "operator_notes": operator_notes,
        "operator_notes_present": operator_notes is not None,
    }


def _runner_output_paths(output_dir: Path) -> dict[str, Path]:
    return {file_name: output_dir / file_name for file_name in _RUNNER_OUTPUT_FILES}


def _iteration_output_paths(output_dir: Path) -> dict[str, Path]:
    return {file_name: output_dir / file_name for file_name in _ITERATION_OUTPUT_FILES}


def _runner_output_preflight_error(
    roots: dict[str, Path],
    paths: dict[str, Path],
) -> dict[str, str] | None:
    output_error = _real_existing_dir_error(
        roots["runner_output_dir"],
        "runner_output_dir",
    )
    if output_error is not None:
        return {
            "failure_stage": "preflight_runner_output_dir",
            "error_message": output_error,
        }
    collision = _existing_output_collision(paths)
    if collision is not None:
        return {
            "failure_stage": "preflight_runner_output_collision",
            "error_message": "runner output artifact already exists: " + collision,
        }
    return None


def _hard_overlap_preflight_error(roots: dict[str, Path]) -> dict[str, str] | None:
    checks = (
        (
            "runner_output_dir",
            "runner_admission_output_dir",
            "runner_output_dir must not equal runner_admission_output_dir",
        ),
        (
            "actual_next_iteration_output_dir",
            "runner_output_dir",
            "actual_next_iteration_output_dir must not equal runner_output_dir",
        ),
        (
            "actual_next_iteration_output_dir",
            "runner_admission_output_dir",
            "actual_next_iteration_output_dir must not equal runner_admission_output_dir",
        ),
    )
    for first, second, message in checks:
        if _same_path_text(roots[first], roots[second]):
            return {
                "failure_stage": "preflight_output_overlap",
                "error_message": message,
            }
    inside_checks = (
        (
            "runner_output_dir",
            "runner_admission_output_dir",
            "runner_output_dir must not be inside runner_admission_output_dir",
        ),
        (
            "runner_admission_output_dir",
            "runner_output_dir",
            "runner_admission_output_dir must not be inside runner_output_dir",
        ),
        (
            "actual_next_iteration_output_dir",
            "runner_output_dir",
            "actual_next_iteration_output_dir must not be inside runner_output_dir",
        ),
        (
            "runner_output_dir",
            "actual_next_iteration_output_dir",
            "runner_output_dir must not be inside actual_next_iteration_output_dir",
        ),
        (
            "actual_next_iteration_output_dir",
            "runner_admission_output_dir",
            "actual_next_iteration_output_dir must not be inside runner_admission_output_dir",
        ),
        (
            "runner_admission_output_dir",
            "actual_next_iteration_output_dir",
            "runner_admission_output_dir must not be inside actual_next_iteration_output_dir",
        ),
    )
    for candidate, root, message in inside_checks:
        if _path_is_inside(roots[candidate], roots[root]):
            return {
                "failure_stage": "preflight_output_overlap",
                "error_message": message,
            }
    return None


def _pre_candidate_outcome(
    *,
    roots: dict[str, Path],
    inputs: dict[str, object],
    source_root_error: str | None,
    source_artifacts: list[dict[str, object]],
    admission: dict[str, object],
    actual_paths: dict[str, Path],
) -> tuple[str, str, str, list[dict[str, object]]]:
    missing_required = _missing_required_artifacts(source_artifacts)
    untrusted = _untrusted_artifacts(source_artifacts)
    invalid_metadata = _invalid_runner_metadata(inputs)
    invalid_record = _invalid_runner_admission_record(admission)
    invalid_limits = _invalid_admitted_limits(admission)
    source_candidate_access = _source_true_fields(
        admission,
        _SOURCE_CANDIDATE_ACCESS_FIELDS,
    )
    source_production_boundary = _source_true_fields(
        admission,
        _SOURCE_PRODUCTION_FIELDS,
    )

    if missing_required:
        status = "blocked_missing_required_artifacts"
        blockers = list(missing_required)
    elif untrusted:
        status = "blocked_untrusted_artifacts"
        blockers = list(untrusted)
    elif inputs["runner_execution_acknowledgement_phrase_valid"] is not True:
        status = "blocked_invalid_runner_execution_acknowledgement"
        blockers = [
            _blocker(
                "invalid_runner_execution_acknowledgement",
                "runner execution acknowledgement phrase did not exactly match",
            )
        ]
    elif invalid_metadata:
        status = "blocked_invalid_runner_metadata"
        blockers = invalid_metadata
    elif invalid_record or invalid_limits:
        status = "blocked_invalid_runner_admission_record"
        blockers = invalid_record + invalid_limits
    elif admission.get("admission_status") != _SOURCE_READY_STATUS:
        status = "blocked_runner_admission_not_ready"
        blockers = [
            _blocker(
                "runner_admission_not_ready",
                "runner admission status is not ready",
                actual_status=admission.get("admission_status"),
            )
        ]
    elif admission.get("admission_decision") != _SOURCE_READY_DECISION:
        status = "blocked_runner_admission_not_ready"
        blockers = [
            _blocker(
                "runner_admission_decision_not_ready",
                "runner admission decision does not admit runner consumption",
                actual_decision=admission.get("admission_decision"),
            )
        ]
    elif admission.get("next_allowed_action") != _SOURCE_READY_NEXT_ACTION:
        status = "blocked_runner_admission_not_ready"
        blockers = [
            _blocker(
                "runner_admission_next_action_not_ready",
                "runner admission next allowed action is not runner execution",
                actual_next_allowed_action=admission.get("next_allowed_action"),
            )
        ]
    elif admission.get("runner_consume_request_admitted") is not True:
        status = "blocked_runner_consumption_not_admitted"
        blockers = [
            _blocker(
                "runner_consumption_not_admitted",
                "runner admission did not admit request consumption",
            )
        ]
    elif _source_true_fields(admission, _SOURCE_EXECUTION_ALREADY_ALLOWED_FIELDS):
        status = "blocked_execution_already_allowed"
        blockers = _source_true_fields(
            admission,
            _SOURCE_EXECUTION_ALREADY_ALLOWED_FIELDS,
        )
    elif admission.get("next_bounded_smoke_iteration_executed") is True:
        status = "blocked_iteration_already_executed"
        blockers = [
            _blocker(
                "source_iteration_already_executed",
                "runner admission already records an executed next iteration",
            )
        ]
    elif _source_true_fields(admission, _SOURCE_OUTPUT_CREATED_FIELDS):
        status = "blocked_next_iteration_output_already_created"
        blockers = _source_true_fields(admission, _SOURCE_OUTPUT_CREATED_FIELDS)
    elif source_candidate_access:
        status = "blocked_candidate_access_precondition_violation"
        blockers = source_candidate_access
    elif source_production_boundary:
        status = "blocked_production_boundary_violation"
        blockers = source_production_boundary
    elif not _paths_match_textually(
        roots["actual_next_iteration_output_dir"],
        admission.get("requested_next_iteration_output_dir"),
    ):
        status = "blocked_actual_output_dir_mismatch"
        blockers = [
            _blocker(
                "actual_next_iteration_output_dir_mismatch",
                "actual output dir does not match requested output dir",
                actual_next_iteration_output_dir=roots[
                    "actual_next_iteration_output_dir"
                ].as_posix(),
                requested_next_iteration_output_dir=admission.get(
                    "requested_next_iteration_output_dir"
                ),
            )
        ]
    else:
        actual_error = _real_existing_dir_error(
            roots["actual_next_iteration_output_dir"],
            "actual_next_iteration_output_dir",
        )
        if actual_error is not None:
            status = "blocked_actual_output_dir_unsafe"
            blockers = [
                _blocker(
                    "actual_next_iteration_output_dir_unsafe",
                    actual_error,
                )
            ]
        elif (
            actual_output_collision := _existing_output_collision(actual_paths)
        ) is not None:
            status = "blocked_output_collision"
            blockers = [
                _blocker(
                    "actual_iteration_output_collision",
                    "actual iteration output artifact already exists",
                    path=actual_paths[actual_output_collision].as_posix(),
                )
            ]
        elif source_root_error is not None:
            status = "blocked_missing_required_artifacts"
            blockers = [
                _blocker(
                    "runner_admission_output_dir_unsafe",
                    source_root_error,
                )
            ]
        else:
            status = _COMPLETED_STATUS
            blockers = []

    decision, next_action = (
        (_COMPLETED_DECISION, _COMPLETED_NEXT_ACTION)
        if status == _COMPLETED_STATUS
        else _blocked_decision_and_action(status)
    )
    return status, decision, next_action, blockers


def _discover_candidate_files(
    candidate_root: Path,
    limits: dict[str, int],
) -> dict[str, object]:
    state = _empty_candidate_state()
    state["candidate_input_path_checked"] = True
    root_error = _real_existing_dir_error(candidate_root, "candidate_input_dir")
    if root_error is not None:
        state["blocked"] = True
        state["blocked_status"] = "blocked_candidate_input_dir_unsafe"
        state["blockers"] = [
            _blocker("candidate_input_dir_unsafe", root_error),
        ]
        return state

    records: list[dict[str, object]] = []
    total_bytes = 0
    max_depth_observed = 0
    symlinks: list[str] = []
    blocked_status: str | None = None
    blockers: list[dict[str, object]] = []
    stack: list[tuple[Path, int]] = [(candidate_root, -1)]
    state["candidate_input_path_listed"] = True

    while stack and blocked_status is None:
        current_dir, current_depth = stack.pop()
        try:
            with os.scandir(current_dir) as scan_entries:
                entries = sorted(scan_entries, key=lambda entry: entry.name)
        except OSError as exc:
            blocked_status = "blocked_candidate_input_dir_unsafe"
            blockers.append(
                _blocker(
                    "candidate_directory_unreadable",
                    "candidate directory could not be listed",
                    path=current_dir.as_posix(),
                    error_message=str(exc),
                )
            )
            break
        for entry in entries:
            entry_path = Path(entry.path)
            relative_path = entry_path.relative_to(candidate_root).as_posix()
            entry_depth = len(Path(relative_path).parts) - 1
            max_depth_observed = max(max_depth_observed, entry_depth)
            if entry.is_symlink():
                symlinks.append(relative_path)
                blocked_status = "blocked_candidate_symlink_detected"
                blockers.append(
                    _blocker(
                        "candidate_symlink_detected",
                        "candidate traversal encountered a symlink",
                        relative_path=relative_path,
                    )
                )
                break
            if entry_depth > limits["admitted_max_depth"]:
                blocked_status = "blocked_candidate_limits_exceeded"
                blockers.append(
                    _blocker(
                        "candidate_max_depth_exceeded",
                        "candidate depth exceeds admitted max depth",
                        relative_path=relative_path,
                        observed_depth=entry_depth,
                        admitted_max_depth=limits["admitted_max_depth"],
                    )
                )
                break
            if entry.is_dir(follow_symlinks=False):
                stack.append((entry_path, entry_depth))
                continue
            if not entry.is_file(follow_symlinks=False):
                blocked_status = "blocked_candidate_input_dir_unsafe"
                blockers.append(
                    _blocker(
                        "candidate_entry_type_unsupported",
                        "candidate traversal encountered a non-file entry",
                        relative_path=relative_path,
                    )
                )
                break
            try:
                stat_result = entry.stat(follow_symlinks=False)
            except OSError as exc:
                blocked_status = "blocked_candidate_input_dir_unsafe"
                blockers.append(
                    _blocker(
                        "candidate_file_stat_failed",
                        "candidate file metadata could not be read",
                        relative_path=relative_path,
                        error_message=str(exc),
                    )
                )
                break
            file_size = int(stat_result.st_size)
            if len(records) + 1 > limits["admitted_max_files"]:
                blocked_status = "blocked_candidate_limits_exceeded"
                blockers.append(
                    _blocker(
                        "candidate_max_files_exceeded",
                        "candidate file count exceeds admitted max files",
                        admitted_max_files=limits["admitted_max_files"],
                    )
                )
                break
            if total_bytes + file_size > limits["admitted_max_total_bytes"]:
                blocked_status = "blocked_candidate_limits_exceeded"
                blockers.append(
                    _blocker(
                        "candidate_max_total_bytes_exceeded",
                        "candidate total bytes exceeds admitted max total bytes",
                        relative_path=relative_path,
                        admitted_max_total_bytes=limits[
                            "admitted_max_total_bytes"
                        ],
                    )
                )
                break
            try:
                file_sha256 = _sha256_regular_file(entry_path)
            except OSError as exc:
                blocked_status = "blocked_candidate_input_dir_unsafe"
                blockers.append(
                    _blocker(
                        "candidate_file_hash_failed",
                        "candidate file hash could not be computed",
                        relative_path=relative_path,
                        error_message=str(exc),
                    )
                )
                break
            total_bytes += file_size
            records.append(
                {
                    "relative_path": relative_path,
                    "size_bytes": file_size,
                    "sha256": file_sha256,
                    "depth": entry_depth,
                    "is_symlink": False,
                    "content_copied": False,
                    "raw_content_copied": False,
                }
            )

    records = sorted(records, key=lambda record: str(record["relative_path"]))
    state.update(
        {
            "blocked": blocked_status is not None,
            "blocked_status": blocked_status,
            "blockers": blockers,
            "candidate_file_count": len(records),
            "candidate_total_bytes": total_bytes,
            "candidate_max_depth_observed": max_depth_observed,
            "candidate_symlinks_detected": symlinks,
            "bounded_file_records": records,
            "candidate_input_file_read": bool(records),
            "candidate_input_file_hashing_performed": bool(records),
        }
    )
    return state


def _write_actual_iteration_artifacts(
    *,
    roots: dict[str, Path],
    actual_paths: dict[str, Path],
    inputs: dict[str, object],
    admission: dict[str, object],
    candidate_state: dict[str, object],
) -> list[dict[str, object]]:
    run_payload = _actual_run_payload(
        roots=roots,
        inputs=inputs,
        admission=admission,
        candidate_state=candidate_state,
    )
    candidate_manifest = _candidate_manifest_payload(admission, candidate_state)
    summary = _iteration_summary_markdown(run_payload)
    checklist = _iteration_checklist_markdown()
    _write_json_exclusive(
        actual_paths[LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUN_FILE],
        run_payload,
    )
    _write_json_exclusive(
        actual_paths[LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_CANDIDATE_MANIFEST_FILE],
        candidate_manifest,
    )
    _write_text_exclusive(
        actual_paths[LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_SUMMARY_FILE],
        summary,
    )
    _write_text_exclusive(
        actual_paths[LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_CHECKLIST_FILE],
        checklist,
    )
    run_manifest = _actual_run_manifest_payload(actual_paths, run_payload)
    _write_json_exclusive(
        actual_paths[LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUN_MANIFEST_FILE],
        run_manifest,
    )
    artifact_index = _iteration_artifact_index_payload(
        roots["actual_next_iteration_output_dir"],
        actual_paths,
    )
    _write_json_exclusive(actual_paths[_ARTIFACT_INDEX_FILE], artifact_index)
    artifact_index_manifest = _iteration_artifact_index_manifest_payload(
        roots["actual_next_iteration_output_dir"],
        actual_paths,
        artifact_index,
    )
    _write_json_exclusive(
        actual_paths[_ARTIFACT_INDEX_MANIFEST_FILE],
        artifact_index_manifest,
    )
    return [
        _artifact_ref(role, actual_paths[file_name])
        for role, file_name in (
            _ITERATION_ARTIFACTS
            + (
                ("artifact_index", _ARTIFACT_INDEX_FILE),
                ("artifact_index_manifest", _ARTIFACT_INDEX_MANIFEST_FILE),
            )
        )
    ]


def _write_runner_artifacts(
    *,
    roots: dict[str, Path],
    runner_paths: dict[str, Path],
    runner_payload: dict[str, object],
    source_artifacts: list[dict[str, object]],
    actual_iteration_artifacts: list[dict[str, object]],
) -> None:
    summary = _runner_summary_markdown(runner_payload)
    checklist = _runner_checklist_markdown()
    _write_json_exclusive(
        runner_paths[LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUNNER_FILE],
        runner_payload,
    )
    _write_text_exclusive(
        runner_paths[LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUNNER_SUMMARY_FILE],
        summary,
    )
    _write_text_exclusive(
        runner_paths[LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUNNER_CHECKLIST_FILE],
        checklist,
    )
    manifest = _runner_manifest_payload(
        runner_paths=runner_paths,
        runner_payload=runner_payload,
        source_artifacts=source_artifacts,
        actual_iteration_artifacts=actual_iteration_artifacts,
    )
    _write_json_exclusive(
        runner_paths[LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUNNER_MANIFEST_FILE],
        manifest,
    )
    artifact_index = _runner_artifact_index_payload(
        roots["runner_output_dir"],
        runner_paths,
    )
    _write_json_exclusive(runner_paths[_ARTIFACT_INDEX_FILE], artifact_index)
    artifact_index_manifest = _runner_artifact_index_manifest_payload(
        roots["runner_output_dir"],
        runner_paths,
        artifact_index,
    )
    _write_json_exclusive(
        runner_paths[_ARTIFACT_INDEX_MANIFEST_FILE],
        artifact_index_manifest,
    )


def _runner_payload(
    *,
    roots: dict[str, Path],
    inputs: dict[str, object],
    admission: dict[str, object],
    source_artifacts: list[dict[str, object]],
    candidate_state: dict[str, object],
    actual_iteration_artifacts: list[dict[str, object]],
    status: str,
    decision: str,
    next_action: str,
    blockers: list[dict[str, object]],
) -> dict[str, object]:
    missing_required = _missing_required_artifacts(source_artifacts)
    untrusted = _untrusted_artifacts(source_artifacts)
    complete = status == _COMPLETED_STATUS
    payload = {
        "runner_type": _RUNNER_TYPE,
        "authority": _AUTHORITY,
        "execution_capability": _EXECUTION_CAPABILITY,
        "project_id": _first_text(inputs.get("project_id"), admission.get("project_id")),
        "runner_execution_id": inputs["runner_execution_id"],
        "runner_operator_id": inputs["runner_operator_id"],
        "runner_execution_acknowledgement_phrase_sha256": inputs[
            "runner_execution_acknowledgement_phrase_sha256"
        ],
        "runner_execution_acknowledgement_phrase_persisted": False,
        "runner_admission_output_dir": roots["runner_admission_output_dir"].as_posix(),
        "runner_output_dir": roots["runner_output_dir"].as_posix(),
        "actual_next_iteration_output_dir": roots[
            "actual_next_iteration_output_dir"
        ].as_posix(),
        "runner_admission_id": admission.get("runner_admission_id"),
        "admitted_runner_id": admission.get("admitted_runner_id"),
        "admitted_runner_version": admission.get("admitted_runner_version"),
        "requested_next_iteration_id": admission.get("requested_next_iteration_id"),
        "requested_candidate_input_dir": admission.get("requested_candidate_input_dir"),
        "requested_next_iteration_output_dir": admission.get(
            "requested_next_iteration_output_dir"
        ),
        "requested_compare_previous_scan_manifest_path": admission.get(
            "requested_compare_previous_scan_manifest_path"
        ),
        "requested_previous_iteration_artifact_index_path": admission.get(
            "requested_previous_iteration_artifact_index_path"
        ),
        "requested_limits": _requested_limits(admission),
        "admitted_limits": _admitted_limits(admission),
        "admission_status": admission.get("admission_status"),
        "admission_decision": admission.get("admission_decision"),
        "admission_next_allowed_action": admission.get("next_allowed_action"),
        "runner_consume_request_admitted": admission.get(
            "runner_consume_request_admitted"
        ),
        "source_runner_execution_allowed": admission.get("runner_execution_allowed"),
        "source_next_bounded_smoke_iteration_execute_allowed": admission.get(
            "next_bounded_smoke_iteration_execute_allowed"
        ),
        "source_next_bounded_smoke_iteration_executed": admission.get(
            "next_bounded_smoke_iteration_executed"
        ),
        "source_next_iteration_output_dir_created": admission.get(
            "next_iteration_output_dir_created"
        ),
        "source_requested_next_iteration_output_dir_created": admission.get(
            "requested_next_iteration_output_dir_created"
        ),
        "source_candidate_input_path_checked": admission.get(
            "candidate_input_path_checked"
        ),
        "source_candidate_input_path_listed": admission.get(
            "candidate_input_path_listed"
        ),
        "source_candidate_input_file_read": admission.get(
            "candidate_input_file_read"
        ),
        "source_candidate_input_file_hashing_performed": admission.get(
            "candidate_input_file_hashing_performed"
        ),
        "source_production_scan_approved": admission.get("production_scan_approved"),
        "source_production_promotion_granted": admission.get(
            "production_promotion_granted"
        ),
        "source_automatic_approval_performed": admission.get(
            "automatic_approval_performed"
        ),
        "source_autonomous_execution_performed": admission.get(
            "autonomous_execution_performed"
        ),
        "runner_status": status,
        "runner_decision": decision,
        "next_allowed_action": next_action,
        "runner_execution_performed": complete,
        "next_bounded_smoke_iteration_executed": complete,
        "next_iteration_output_dir_created": False,
        "actual_next_iteration_output_dir_created": False,
        "candidate_input_path_checked": candidate_state[
            "candidate_input_path_checked"
        ],
        "candidate_input_path_listed": candidate_state[
            "candidate_input_path_listed"
        ],
        "candidate_input_file_read": candidate_state["candidate_input_file_read"],
        "candidate_input_file_hashing_performed": candidate_state[
            "candidate_input_file_hashing_performed"
        ],
        "candidate_file_hashing_performed": candidate_state[
            "candidate_input_file_hashing_performed"
        ],
        "candidate_file_count": candidate_state["candidate_file_count"],
        "candidate_total_bytes": candidate_state["candidate_total_bytes"],
        "candidate_max_depth_observed": candidate_state[
            "candidate_max_depth_observed"
        ],
        "candidate_limit_enforced": True,
        "candidate_symlinks_detected": candidate_state[
            "candidate_symlinks_detected"
        ],
        "bounded_file_records": candidate_state["bounded_file_records"],
        "actual_iteration_artifacts": actual_iteration_artifacts,
        "source_artifacts": [
            _public_source_artifact_ref(artifact) for artifact in source_artifacts
        ],
        "missing_required_artifacts": missing_required,
        "untrusted_artifacts": untrusted,
        "runner_blockers": blockers,
        "deterministic_ordering": True,
        "required_human_approval": True,
        "required_human_review": True,
        "disallowed_actions": list(_DISALLOWED_ACTIONS),
        "bounded_smoke_iteration_performed_by_runner": complete,
        "raw_content_copied": False,
    }
    if inputs["operator_notes_present"] is True:
        payload["operator_notes"] = inputs["operator_notes"]
    payload.update(_BOUNDARY_FALSE_FLAGS)
    payload["bounded_smoke_iteration_performed_by_runner"] = complete
    return payload


def _actual_run_payload(
    *,
    roots: dict[str, Path],
    inputs: dict[str, object],
    admission: dict[str, object],
    candidate_state: dict[str, object],
) -> dict[str, object]:
    return {
        "run_type": _ITERATION_RUN_TYPE,
        "authority": _AUTHORITY,
        "execution_capability": _EXECUTION_CAPABILITY,
        "project_id": _first_text(inputs.get("project_id"), admission.get("project_id")),
        "runner_execution_id": inputs["runner_execution_id"],
        "runner_operator_id": inputs["runner_operator_id"],
        "runner_admission_id": admission.get("runner_admission_id"),
        "admitted_runner_id": admission.get("admitted_runner_id"),
        "admitted_runner_version": admission.get("admitted_runner_version"),
        "requested_next_iteration_id": admission.get("requested_next_iteration_id"),
        "requested_candidate_input_dir": admission.get("requested_candidate_input_dir"),
        "requested_next_iteration_output_dir": admission.get(
            "requested_next_iteration_output_dir"
        ),
        "actual_next_iteration_output_dir": roots[
            "actual_next_iteration_output_dir"
        ].as_posix(),
        "requested_limits": _requested_limits(admission),
        "admitted_limits": _admitted_limits(admission),
        "runner_status": _COMPLETED_STATUS,
        "runner_decision": _COMPLETED_DECISION,
        "next_allowed_action": _COMPLETED_NEXT_ACTION,
        "runner_execution_performed": True,
        "next_bounded_smoke_iteration_executed": True,
        "next_iteration_output_dir_created": False,
        "actual_next_iteration_output_dir_created": False,
        "candidate_input_path_checked": True,
        "candidate_input_path_listed": True,
        "candidate_input_file_read": candidate_state["candidate_input_file_read"],
        "candidate_input_file_hashing_performed": candidate_state[
            "candidate_input_file_hashing_performed"
        ],
        "candidate_file_count": candidate_state["candidate_file_count"],
        "candidate_total_bytes": candidate_state["candidate_total_bytes"],
        "candidate_max_depth_observed": candidate_state[
            "candidate_max_depth_observed"
        ],
        "candidate_limit_enforced": True,
        "candidate_symlinks_detected": candidate_state[
            "candidate_symlinks_detected"
        ],
        "bounded_file_records": candidate_state["bounded_file_records"],
        "raw_content_copied": False,
        "deterministic_ordering": True,
        "required_human_approval": True,
        "required_human_review": True,
        "disallowed_actions": list(_DISALLOWED_ACTIONS),
        "bounded_smoke_iteration_performed_by_runner": True,
        **_BOUNDARY_FALSE_FLAGS,
    }


def _candidate_manifest_payload(
    admission: dict[str, object],
    candidate_state: dict[str, object],
) -> dict[str, object]:
    return {
        "manifest_type": _CANDIDATE_MANIFEST_TYPE,
        "authority": _AUTHORITY,
        "requested_candidate_input_dir": admission.get("requested_candidate_input_dir"),
        "admitted_limits": _admitted_limits(admission),
        "candidate_file_count": candidate_state["candidate_file_count"],
        "candidate_total_bytes": candidate_state["candidate_total_bytes"],
        "candidate_max_depth_observed": candidate_state[
            "candidate_max_depth_observed"
        ],
        "candidate_limit_enforced": True,
        "symlink_policy": "fail_closed",
        "candidate_symlinks_detected": candidate_state[
            "candidate_symlinks_detected"
        ],
        "bounded_file_records": candidate_state["bounded_file_records"],
        "raw_content_copied": False,
        "deterministic_ordering": True,
        "required_human_approval": True,
        "required_human_review": True,
    }


def _actual_run_manifest_payload(
    paths: dict[str, Path],
    run_payload: dict[str, object],
) -> dict[str, object]:
    run_path = paths[LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUN_FILE]
    candidate_path = paths[
        LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_CANDIDATE_MANIFEST_FILE
    ]
    summary_path = paths[LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_SUMMARY_FILE]
    checklist_path = paths[LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_CHECKLIST_FILE]
    payload = {
        "manifest_type": _ITERATION_RUN_MANIFEST_TYPE,
        "authority": _AUTHORITY,
        "run_path": run_path.as_posix(),
        "candidate_manifest_path": candidate_path.as_posix(),
        "summary_path": summary_path.as_posix(),
        "checklist_path": checklist_path.as_posix(),
        "run_sha256": sha256_file(run_path),
        "candidate_manifest_sha256": sha256_file(candidate_path),
        "summary_sha256": sha256_file(summary_path),
        "checklist_sha256": sha256_file(checklist_path),
        "runner_status": run_payload["runner_status"],
        "runner_decision": run_payload["runner_decision"],
        "next_allowed_action": run_payload["next_allowed_action"],
        "runner_execution_performed": True,
        "next_bounded_smoke_iteration_executed": True,
        "next_iteration_output_dir_created": False,
        "actual_next_iteration_output_dir_created": False,
        "candidate_input_path_checked": True,
        "candidate_input_path_listed": True,
        "candidate_input_file_read": run_payload["candidate_input_file_read"],
        "candidate_input_file_hashing_performed": run_payload[
            "candidate_input_file_hashing_performed"
        ],
        "candidate_file_count": run_payload["candidate_file_count"],
        "candidate_total_bytes": run_payload["candidate_total_bytes"],
        "candidate_limit_enforced": True,
        "deterministic_ordering": True,
        "required_human_approval": True,
        "required_human_review": True,
    }
    payload.update(_BOUNDARY_FALSE_FLAGS)
    payload["bounded_smoke_iteration_performed_by_runner"] = True
    return payload


def _runner_manifest_payload(
    *,
    runner_paths: dict[str, Path],
    runner_payload: dict[str, object],
    source_artifacts: list[dict[str, object]],
    actual_iteration_artifacts: list[dict[str, object]],
) -> dict[str, object]:
    runner_path = runner_paths[LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUNNER_FILE]
    summary_path = runner_paths[
        LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUNNER_SUMMARY_FILE
    ]
    checklist_path = runner_paths[
        LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUNNER_CHECKLIST_FILE
    ]
    payload = {
        "manifest_type": _RUNNER_MANIFEST_TYPE,
        "authority": _AUTHORITY,
        "runner_path": runner_path.as_posix(),
        "summary_path": summary_path.as_posix(),
        "checklist_path": checklist_path.as_posix(),
        "runner_sha256": sha256_file(runner_path),
        "summary_sha256": sha256_file(summary_path),
        "checklist_sha256": sha256_file(checklist_path),
        "actual_iteration_artifacts": actual_iteration_artifacts,
        "source_artifacts": [
            _public_source_artifact_ref(artifact) for artifact in source_artifacts
        ],
        "runner_status": runner_payload["runner_status"],
        "runner_decision": runner_payload["runner_decision"],
        "next_allowed_action": runner_payload["next_allowed_action"],
        "runner_execution_performed": runner_payload["runner_execution_performed"],
        "next_bounded_smoke_iteration_executed": runner_payload[
            "next_bounded_smoke_iteration_executed"
        ],
        "next_iteration_output_dir_created": False,
        "actual_next_iteration_output_dir_created": False,
        "candidate_input_path_checked": runner_payload[
            "candidate_input_path_checked"
        ],
        "candidate_input_path_listed": runner_payload[
            "candidate_input_path_listed"
        ],
        "candidate_input_file_read": runner_payload["candidate_input_file_read"],
        "candidate_input_file_hashing_performed": runner_payload[
            "candidate_input_file_hashing_performed"
        ],
        "candidate_file_count": runner_payload["candidate_file_count"],
        "candidate_total_bytes": runner_payload["candidate_total_bytes"],
        "candidate_limit_enforced": True,
        "deterministic_ordering": True,
        "required_human_approval": True,
        "required_human_review": True,
        "runner_execution_acknowledgement_phrase_persisted": False,
    }
    payload.update(_BOUNDARY_FALSE_FLAGS)
    payload["bounded_smoke_iteration_performed_by_runner"] = runner_payload[
        "bounded_smoke_iteration_performed_by_runner"
    ]
    return payload


def _iteration_artifact_index_payload(
    output_dir: Path,
    paths: dict[str, Path],
) -> dict[str, object]:
    entries = [
        _artifact_index_entry(output_dir, role, paths[file_name])
        for role, file_name in _ITERATION_ARTIFACTS
    ]
    return {
        "index_type": _ITERATION_INDEX_TYPE,
        "authority": _AUTHORITY,
        "execution_capability": _EXECUTION_CAPABILITY,
        "job_dir": output_dir.as_posix(),
        "artifact_index_strategy": "explicit_next_bounded_smoke_iteration_artifacts_only",
        "indexed_artifacts": len(entries),
        "entries": entries,
        "candidate_input_files_indexed": False,
        "candidate_file_records_bound_in_candidate_manifest": True,
        "raw_content_copied": False,
        "deterministic_ordering": True,
        "required_human_approval": True,
        "required_human_review": True,
    }


def _iteration_artifact_index_manifest_payload(
    output_dir: Path,
    paths: dict[str, Path],
    artifact_index: dict[str, object],
) -> dict[str, object]:
    entries = artifact_index["entries"]
    return {
        "manifest_type": _ITERATION_INDEX_MANIFEST_TYPE,
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
        "candidate_input_files_indexed": False,
        "raw_content_copied": False,
        "required_human_approval": True,
        "required_human_review": True,
    }


def _runner_artifact_index_payload(
    output_dir: Path,
    paths: dict[str, Path],
) -> dict[str, object]:
    entries = [
        _artifact_index_entry(output_dir, role, paths[file_name])
        for role, file_name in _RUNNER_ARTIFACTS
    ]
    payload = {
        "index_type": _RUNNER_INDEX_TYPE,
        "authority": _AUTHORITY,
        "execution_capability": _EXECUTION_CAPABILITY,
        "job_dir": output_dir.as_posix(),
        "artifact_index_strategy": "explicit_next_bounded_smoke_iteration_runner_artifacts_only",
        "indexed_artifacts": len(entries),
        "entries": entries,
        "candidate_input_files_indexed": False,
        "runner_admission_output_recursively_indexed": False,
        "execution_request_output_recursively_indexed": False,
        "actual_next_iteration_output_recursively_indexed": False,
        "upstream_artifacts_recursively_indexed": False,
        "raw_content_copied": False,
        "deterministic_ordering": True,
        "required_human_approval": True,
        "required_human_review": True,
    }
    payload.update(_BOUNDARY_FALSE_FLAGS)
    return payload


def _runner_artifact_index_manifest_payload(
    output_dir: Path,
    paths: dict[str, Path],
    artifact_index: dict[str, object],
) -> dict[str, object]:
    entries = artifact_index["entries"]
    payload = {
        "manifest_type": _RUNNER_INDEX_MANIFEST_TYPE,
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
        "candidate_input_files_indexed": False,
        "runner_admission_output_recursively_indexed": False,
        "execution_request_output_recursively_indexed": False,
        "actual_next_iteration_output_recursively_indexed": False,
        "upstream_artifacts_recursively_indexed": False,
        "raw_content_copied": False,
        "required_human_approval": True,
        "required_human_review": True,
    }
    payload.update(_BOUNDARY_FALSE_FLAGS)
    return payload


def _source_artifact_records(
    root: Path,
    *,
    source_root_error: str | None,
) -> list[dict[str, object]]:
    records = []
    for role, relative_path, required, _field, _expected in _SOURCE_ARTIFACT_SPECS:
        path = root / relative_path
        exists = (
            source_root_error is None
            and path.exists()
            and path.is_file()
            and not path.is_symlink()
        )
        records.append(
            {
                "role": role,
                "artifact_role": role,
                "relative_path": relative_path,
                "path": path.as_posix(),
                "exists": exists,
                "required": required,
                "sha256": sha256_file(path) if exists else None,
                "size_bytes": path.stat().st_size if exists else None,
                "trusted_generated_artifact": False,
                "trust_failures": [],
                "json_artifact": _field is not None,
                "expected_field": _field,
                "expected_value": _expected,
            }
        )
    return records


def _read_json_source_payloads(
    source_artifacts: list[dict[str, object]],
) -> dict[str, object]:
    payloads: dict[str, object] = {}
    for artifact in source_artifacts:
        if artifact["exists"] is not True or artifact["json_artifact"] is not True:
            continue
        try:
            with Path(str(artifact["path"])).open("r", encoding="utf-8") as handle:
                payloads[str(artifact["role"])] = json.load(handle)
        except (json.JSONDecodeError, OSError) as exc:
            artifact["trust_failures"].append(
                _blocker(
                    "malformed_json",
                    "source JSON artifact is malformed",
                    error_message=str(exc),
                )
            )
    return payloads


def _mark_source_trust(
    source_artifacts: list[dict[str, object]],
    source_payloads: dict[str, object],
) -> None:
    records = {str(record["role"]): record for record in source_artifacts}
    for artifact in source_artifacts:
        if artifact["exists"] is not True:
            continue
        expected_field = artifact.get("expected_field")
        if expected_field is not None:
            payload = source_payloads.get(str(artifact["role"]))
            if not isinstance(payload, dict):
                artifact["trust_failures"].append(
                    _blocker(
                        "malformed_json",
                        "source JSON artifact could not be trusted",
                    )
                )
            elif payload.get(str(expected_field)) != artifact.get("expected_value"):
                artifact["trust_failures"].append(
                    _blocker(
                        "type_mismatch",
                        "source artifact type field did not match expected value",
                        expected_field=expected_field,
                        expected_value=artifact.get("expected_value"),
                        actual_value=payload.get(str(expected_field)),
                    )
                )

    admission = source_payloads.get(
        "local_asset_next_bounded_smoke_iteration_runner_admission"
    )
    manifest = source_payloads.get(
        "local_asset_next_bounded_smoke_iteration_runner_admission_manifest"
    )
    artifact_index_manifest = source_payloads.get(
        "local_asset_next_bounded_smoke_iteration_runner_admission_artifact_index_manifest"
    )
    if isinstance(manifest, dict):
        _mark_manifest_hash(
            records,
            manifest,
            "admission_sha256",
            "local_asset_next_bounded_smoke_iteration_runner_admission",
        )
        _mark_manifest_hash(
            records,
            manifest,
            "summary_sha256",
            "local_asset_next_bounded_smoke_iteration_runner_admission_summary",
            optional=True,
        )
        _mark_manifest_hash(
            records,
            manifest,
            "checklist_sha256",
            "local_asset_next_bounded_smoke_iteration_runner_admission_checklist",
            optional=True,
        )
    if isinstance(artifact_index_manifest, dict):
        _mark_manifest_hash(
            records,
            artifact_index_manifest,
            "artifact_index_sha256",
            "local_asset_next_bounded_smoke_iteration_runner_admission_artifact_index",
        )
    if not isinstance(admission, dict):
        record = records.get("local_asset_next_bounded_smoke_iteration_runner_admission")
        if record is not None and record["exists"] is True:
            record["trust_failures"].append(
                _blocker("malformed_json", "runner admission JSON is malformed")
            )
    for artifact in source_artifacts:
        if artifact["exists"] is True and not artifact["trust_failures"]:
            artifact["trusted_generated_artifact"] = True


def _mark_manifest_hash(
    records: dict[str, dict[str, object]],
    manifest: dict[str, object],
    field_name: str,
    role: str,
    *,
    optional: bool = False,
) -> None:
    record = records.get(role)
    if record is None or record["exists"] is not True:
        return
    expected_hash = manifest.get(field_name)
    actual_hash = record.get("sha256")
    if expected_hash != actual_hash:
        if optional and expected_hash is None:
            return
        record["trust_failures"].append(
            _blocker(
                "hash_mismatch",
                "source manifest hash did not match source artifact",
                hash_field=field_name,
                expected_sha256=expected_hash,
                actual_sha256=actual_hash,
            )
        )


def _invalid_runner_metadata(inputs: dict[str, object]) -> list[dict[str, object]]:
    invalid = []
    for field_name in ("runner_execution_id", "runner_operator_id"):
        value = inputs.get(field_name)
        if not isinstance(value, str) or not value:
            invalid.append(
                _blocker(
                    "invalid_runner_metadata",
                    "runner execution metadata is missing or not text",
                    field=field_name,
                )
            )
    project_id = inputs.get("project_id")
    if project_id is not None and (not isinstance(project_id, str) or not project_id):
        invalid.append(
            _blocker(
                "invalid_runner_metadata",
                "project_id must be absent or non-empty text",
                field="project_id",
            )
        )
    operator_notes = inputs.get("operator_notes")
    if operator_notes is not None and not isinstance(operator_notes, str):
        invalid.append(
            _blocker(
                "invalid_runner_metadata",
                "operator_notes must be text when present",
                field="operator_notes",
            )
        )
    return sorted(invalid, key=lambda item: str(item.get("field")))


def _invalid_runner_admission_record(
    admission: dict[str, object],
) -> list[dict[str, object]]:
    invalid = []
    required_text_fields = (
        "requested_candidate_input_dir",
        "requested_next_iteration_output_dir",
        "runner_admission_id",
        "admitted_runner_id",
        "admitted_runner_version",
        "requested_next_iteration_id",
    )
    for field_name in required_text_fields:
        value = admission.get(field_name)
        if not isinstance(value, str) or not value:
            invalid.append(
                _blocker(
                    "invalid_runner_admission_record",
                    "runner admission required text field is missing",
                    field=field_name,
                )
            )
    if not isinstance(admission.get("requested_limits"), dict):
        invalid.append(
            _blocker(
                "invalid_runner_admission_record",
                "requested_limits is missing or malformed",
                field="requested_limits",
            )
        )
    if not isinstance(admission.get("admitted_limits"), dict):
        invalid.append(
            _blocker(
                "invalid_runner_admission_record",
                "admitted_limits is missing or malformed",
                field="admitted_limits",
            )
        )
    for field_name in _SOURCE_REQUIRED_BOOLEAN_FIELDS:
        if field_name not in admission:
            invalid.append(
                _blocker(
                    "invalid_runner_admission_record",
                    "runner admission required boolean field is missing",
                    field=field_name,
                )
            )
            continue
        value = admission[field_name]
        if not isinstance(value, bool):
            invalid.append(
                _blocker(
                    "invalid_runner_admission_record",
                    "runner admission required boundary field must be boolean",
                    field=field_name,
                    actual_value=value,
                )
            )
            continue
        if field_name in _SOURCE_TRUE_FIELDS and value is not True:
            invalid.append(
                _blocker(
                    "invalid_runner_admission_record",
                    "runner admission required human gate field must be true",
                    field=field_name,
                    actual_value=value,
                )
            )
    return sorted(invalid, key=lambda item: str(item.get("field")))


def _invalid_admitted_limits(
    admission: dict[str, object],
) -> list[dict[str, object]]:
    limits = admission.get("admitted_limits")
    if not isinstance(limits, dict):
        return []
    invalid = []
    specs = (
        ("admitted_max_files", 1),
        ("admitted_max_total_bytes", 1),
        ("admitted_max_depth", 0),
    )
    for field_name, minimum in specs:
        value = limits.get(field_name)
        if not isinstance(value, int) or isinstance(value, bool) or value < minimum:
            invalid.append(
                _blocker(
                    "invalid_admitted_limit",
                    "admitted limit is missing or outside allowed bounds",
                    field=field_name,
                    minimum=minimum,
                    actual_value=value,
                )
            )
    return sorted(invalid, key=lambda item: str(item.get("field")))


def _real_existing_dir_error(path_value: object, label: str) -> str | None:
    path = Path(path_value)
    if path.is_symlink():
        return label + " must not be a symlink"
    if not path.exists():
        return label + " must already exist"
    if not path.is_dir():
        return label + " must be a directory"
    return None


def _existing_output_collision(paths: dict[str, Path]) -> str | None:
    for file_name in sorted(paths):
        if paths[file_name].exists() or paths[file_name].is_symlink():
            return file_name
    return None


def _same_path_text(first: Path, second: Path) -> bool:
    return _normalize_path_text(first) == _normalize_path_text(second)


def _paths_match_textually(path_value: Path, expected_value: object) -> bool:
    if not isinstance(expected_value, str) or not expected_value:
        return False
    return _normalize_path_text(path_value) == _normalize_path_text(Path(expected_value))


def _normalize_path_text(path_value: Path) -> str:
    return os.path.normpath(Path(path_value).expanduser().as_posix())


def _path_is_inside(candidate_path: Path, root_path: Path) -> bool:
    if _same_path_text(candidate_path, root_path):
        return False
    try:
        Path(candidate_path).resolve(strict=False).relative_to(
            Path(root_path).resolve(strict=False)
        )
        return True
    except ValueError:
        return False


def _missing_required_artifacts(
    source_artifacts: list[dict[str, object]],
) -> list[dict[str, object]]:
    return [
        _blocker(
            "missing_required_artifact",
            "required runner admission artifact is missing",
            artifact_role=artifact["artifact_role"],
            path=artifact["path"],
        )
        for artifact in source_artifacts
        if artifact["required"] is True and artifact["exists"] is not True
    ]


def _untrusted_artifacts(
    source_artifacts: list[dict[str, object]],
) -> list[dict[str, object]]:
    untrusted = []
    for artifact in source_artifacts:
        if artifact["exists"] is True and artifact["trusted_generated_artifact"] is not True:
            untrusted.append(
                _blocker(
                    "untrusted_source_artifact",
                    "source artifact failed generated-artifact trust checks",
                    artifact_role=artifact["artifact_role"],
                    path=artifact["path"],
                    trust_failures=artifact["trust_failures"],
                )
            )
    return untrusted


def _source_true_fields(
    admission: dict[str, object],
    field_names: tuple[str, ...],
) -> list[dict[str, object]]:
    return [
        _blocker(
            "source_boundary_flag_true",
            "runner admission source boundary flag is true",
            field=field_name,
        )
        for field_name in field_names
        if admission.get(field_name) is True
    ]


def _public_source_artifact_ref(artifact: dict[str, object]) -> dict[str, object]:
    return {
        "role": artifact["role"],
        "artifact_role": artifact["artifact_role"],
        "path": artifact["path"],
        "sha256": artifact["sha256"],
        "size_bytes": artifact["size_bytes"],
        "exists": artifact["exists"],
        "required": artifact["required"],
        "trusted_generated_artifact": artifact["trusted_generated_artifact"],
    }


def _blocked_decision_and_action(status: str) -> tuple[str, str]:
    if status in (
        "blocked_actual_output_dir_mismatch",
        "blocked_candidate_symlink_detected",
        "blocked_candidate_access_precondition_violation",
        "blocked_production_boundary_violation",
        "blocked_execution_already_allowed",
        "blocked_iteration_already_executed",
        "blocked_next_iteration_output_already_created",
    ):
        return ("reject_boundary_violation", "reject_boundary_violation")
    if status in (
        "blocked_missing_required_artifacts",
        "blocked_untrusted_artifacts",
        "blocked_output_collision",
    ):
        return ("reject_and_repair_artifacts", "repair_artifacts")
    if status in (
        "blocked_runner_admission_not_ready",
        "blocked_runner_consumption_not_admitted",
        "blocked_invalid_runner_admission_record",
    ):
        return ("reject_and_repair_runner_admission", "repair_runner_admission")
    return ("reject_and_repair_runner", "repair_runner")


def _empty_candidate_state() -> dict[str, object]:
    return {
        "blocked": False,
        "blocked_status": None,
        "blockers": [],
        "candidate_input_path_checked": False,
        "candidate_input_path_listed": False,
        "candidate_input_file_read": False,
        "candidate_input_file_hashing_performed": False,
        "candidate_file_count": 0,
        "candidate_total_bytes": 0,
        "candidate_max_depth_observed": 0,
        "candidate_symlinks_detected": [],
        "bounded_file_records": [],
    }


def _requested_limits(admission: dict[str, object]) -> dict[str, object]:
    value = admission.get("requested_limits")
    return dict(value) if isinstance(value, dict) else {}


def _admitted_limits(admission: dict[str, object]) -> dict[str, int]:
    value = admission.get("admitted_limits")
    if not isinstance(value, dict):
        return {
            "admitted_max_files": 0,
            "admitted_max_total_bytes": 0,
            "admitted_max_depth": -1,
        }
    return {
        "admitted_max_files": _safe_int(value.get("admitted_max_files"), 0),
        "admitted_max_total_bytes": _safe_int(
            value.get("admitted_max_total_bytes"),
            0,
        ),
        "admitted_max_depth": _safe_int(value.get("admitted_max_depth"), -1),
    }


def _artifact_ref(role: str, path: Path) -> dict[str, object]:
    return {
        "role": role,
        "path": path.as_posix(),
        "sha256": sha256_file(path),
        "size_bytes": path.stat().st_size,
    }


def _artifact_index_entry(output_dir: Path, role: str, path: Path) -> dict[str, object]:
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


def _runner_summary_markdown(runner: dict[str, object]) -> str:
    requested_limits = _dict_or_empty(runner.get("requested_limits"))
    admitted_limits = _dict_or_empty(runner.get("admitted_limits"))
    lines = [
        "# Local Asset Next Bounded Smoke Iteration Runner",
        "",
        "- Runner status: " + str(runner["runner_status"]),
        "- Runner decision: " + str(runner["runner_decision"]),
        "- Next allowed action: " + str(runner["next_allowed_action"]),
        "- Runner execution id: " + str(runner["runner_execution_id"]),
        "- Runner operator id: " + str(runner["runner_operator_id"]),
        "- Runner acknowledgement hash present: true",
        "- Runner acknowledgement phrase persisted: false",
        "- Runner admission id: " + str(runner["runner_admission_id"]),
        "- Admitted runner id: " + str(runner["admitted_runner_id"]),
        "- Admitted runner version: " + str(runner["admitted_runner_version"]),
        "- Requested next iteration id: "
        + str(runner["requested_next_iteration_id"]),
        "- Requested candidate input dir: `"
        + str(runner["requested_candidate_input_dir"])
        + "`",
        "- Requested next iteration output dir: `"
        + str(runner["requested_next_iteration_output_dir"])
        + "`",
        "- Actual next iteration output dir: `"
        + str(runner["actual_next_iteration_output_dir"])
        + "`",
        "- Requested limits: " + json.dumps(requested_limits, sort_keys=True),
        "- Admitted limits: " + json.dumps(admitted_limits, sort_keys=True),
        "- Candidate file count: " + str(runner["candidate_file_count"]),
        "- Candidate total bytes: " + str(runner["candidate_total_bytes"]),
        "- Max depth observed: " + str(runner["candidate_max_depth_observed"]),
        "- Candidate limit enforced: true",
        "- Candidate symlinks detected: "
        + str(len(_list_or_empty(runner.get("candidate_symlinks_detected")))),
        "- Runner execution performed: "
        + _bool_text(runner["runner_execution_performed"]),
        "- Next bounded smoke iteration executed: "
        + _bool_text(runner["next_bounded_smoke_iteration_executed"]),
        "- Next iteration output dir created: false",
        "- Actual next iteration output dir created: false",
        "- Production scan approved: false",
        "- Production promotion granted: false",
        "- Missing required count: "
        + str(len(_list_or_empty(runner.get("missing_required_artifacts")))),
        "- Untrusted count: "
        + str(len(_list_or_empty(runner.get("untrusted_artifacts")))),
        "- Blocker count: " + str(len(_list_or_empty(runner.get("runner_blockers")))),
        "",
        "## Explicit Boundaries",
        "",
        "- bounded local smoke runner only",
        "- no production scan",
        "- no production promotion",
        "- no media organizer",
        "- no file move",
        "- no file rename",
        "- no file deletion",
        "- no duplicate deletion",
        "- no raw private content copied",
        "- no network",
        "- no model API",
        "- no external runtime",
        "- no automatic approval",
        "- no autonomy",
    ]
    return "\n".join(lines) + "\n"


def _runner_checklist_markdown() -> str:
    items = [
        "verify runner admission artifact exists and is trusted",
        "verify runner admission status is ready",
        "verify runner admission decision admits runner consumption",
        "verify runner acknowledgement phrase was valid",
        "verify plaintext runner execution acknowledgement was not persisted",
        "verify actual output dir equals requested output dir",
        "verify actual output dir was not created by runner",
        "verify candidate input dir exists and is not symlink",
        "verify candidate traversal did not follow symlinks",
        "verify candidate limits were enforced",
        "verify candidate file count <= admitted max files",
        "verify candidate total bytes <= admitted max total bytes",
        "verify candidate max depth <= admitted max depth",
        "verify bounded smoke iteration executed exactly once",
        "verify production scan is not approved",
        "verify production promotion is not granted",
        "verify no file move/rename/delete occurred",
        "verify no duplicate deletion occurred",
        "verify no media organizer behavior occurred",
        "verify no raw private content was copied",
        "verify no network/model/external runtime was used",
    ]
    return "# Runner Checklist\n\n" + "\n".join(
        "- [ ] " + item for item in items
    ) + "\n"


def _iteration_summary_markdown(run_payload: dict[str, object]) -> str:
    lines = [
        "# Local Asset Next Bounded Smoke Iteration Run",
        "",
        "- Runner status: " + str(run_payload["runner_status"]),
        "- Runner decision: " + str(run_payload["runner_decision"]),
        "- Next allowed action: " + str(run_payload["next_allowed_action"]),
        "- Requested candidate input dir: `"
        + str(run_payload["requested_candidate_input_dir"])
        + "`",
        "- Actual next iteration output dir: `"
        + str(run_payload["actual_next_iteration_output_dir"])
        + "`",
        "- Candidate file count: " + str(run_payload["candidate_file_count"]),
        "- Candidate total bytes: " + str(run_payload["candidate_total_bytes"]),
        "- Candidate max depth observed: "
        + str(run_payload["candidate_max_depth_observed"]),
        "- Candidate limit enforced: true",
        "- Candidate symlinks detected: "
        + str(len(_list_or_empty(run_payload.get("candidate_symlinks_detected")))),
        "- Raw content copied: false",
        "- Production scan approved: false",
        "- Production promotion granted: false",
    ]
    return "\n".join(lines) + "\n"


def _iteration_checklist_markdown() -> str:
    items = [
        "verify actual iteration artifacts were written exclusively",
        "verify candidate manifest contains bounded metadata only",
        "verify candidate records are deterministically ordered",
        "verify candidate limits were enforced",
        "verify candidate traversal did not follow symlinks",
        "verify no raw private content was copied",
        "verify no production scan or promotion was approved",
    ]
    return "# Next Iteration Checklist\n\n" + "\n".join(
        "- [ ] " + item for item in items
    ) + "\n"


def _launcher_payload_from_runner(
    runner: dict[str, object],
    paths: dict[str, Path],
    actual_iteration_artifacts: list[dict[str, object]],
    *,
    complete: bool,
    artifacts_written: bool,
) -> dict[str, object]:
    payload = {
        "complete": complete,
        "artifacts_written": artifacts_written,
        "local_asset_next_bounded_smoke_iteration_runner_path": _path_text_or_none(
            paths.get(LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUNNER_FILE)
        ),
        "local_asset_next_bounded_smoke_iteration_runner_manifest_path": (
            _path_text_or_none(
                paths.get(
                    LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUNNER_MANIFEST_FILE
                )
            )
        ),
        "local_asset_next_bounded_smoke_iteration_runner_summary_path": (
            _path_text_or_none(
                paths.get(
                    LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUNNER_SUMMARY_FILE
                )
            )
        ),
        "local_asset_next_bounded_smoke_iteration_runner_checklist_path": (
            _path_text_or_none(
                paths.get(
                    LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUNNER_CHECKLIST_FILE
                )
            )
        ),
        "artifact_index_path": _path_text_or_none(paths.get(_ARTIFACT_INDEX_FILE)),
        "artifact_index_manifest_path": _path_text_or_none(
            paths.get(_ARTIFACT_INDEX_MANIFEST_FILE)
        ),
        "actual_iteration_artifacts": actual_iteration_artifacts,
        "runner_admission_output_dir": runner["runner_admission_output_dir"],
        "runner_output_dir": runner["runner_output_dir"],
        "actual_next_iteration_output_dir": runner[
            "actual_next_iteration_output_dir"
        ],
        "project_id": runner["project_id"],
        "runner_execution_id": runner["runner_execution_id"],
        "runner_operator_id": runner["runner_operator_id"],
        "runner_admission_id": runner["runner_admission_id"],
        "admitted_runner_id": runner["admitted_runner_id"],
        "admitted_runner_version": runner["admitted_runner_version"],
        "requested_next_iteration_id": runner["requested_next_iteration_id"],
        "requested_candidate_input_dir": runner["requested_candidate_input_dir"],
        "requested_next_iteration_output_dir": runner[
            "requested_next_iteration_output_dir"
        ],
        "requested_limits": runner["requested_limits"],
        "admitted_limits": runner["admitted_limits"],
        "runner_status": runner["runner_status"],
        "runner_decision": runner["runner_decision"],
        "next_allowed_action": runner["next_allowed_action"],
        "runner_execution_performed": runner["runner_execution_performed"],
        "next_bounded_smoke_iteration_executed": runner[
            "next_bounded_smoke_iteration_executed"
        ],
        "next_iteration_output_dir_created": False,
        "actual_next_iteration_output_dir_created": False,
        "candidate_input_path_checked": runner["candidate_input_path_checked"],
        "candidate_input_path_listed": runner["candidate_input_path_listed"],
        "candidate_input_file_read": runner["candidate_input_file_read"],
        "candidate_input_file_hashing_performed": runner[
            "candidate_input_file_hashing_performed"
        ],
        "candidate_file_count": runner["candidate_file_count"],
        "candidate_total_bytes": runner["candidate_total_bytes"],
        "candidate_limit_enforced": runner["candidate_limit_enforced"],
        "production_scan_approved": False,
        "production_promotion_granted": False,
        "automatic_approval_performed": False,
        "autonomous_execution_performed": False,
        "required_human_approval": True,
        "required_human_review": True,
    }
    payload.update(_BOUNDARY_FALSE_FLAGS)
    payload["bounded_smoke_iteration_performed_by_runner"] = runner[
        "bounded_smoke_iteration_performed_by_runner"
    ]
    return payload


def _structured_failure_result(
    roots: dict[str, Path],
    inputs: dict[str, object],
    *,
    failure_stage: str,
    error_message: str,
) -> LocalAssetNextBoundedSmokeIterationRunnerResult:
    payload = {
        "complete": False,
        "artifacts_written": False,
        "runner_admission_output_dir": roots[
            "runner_admission_output_dir"
        ].as_posix(),
        "runner_output_dir": roots["runner_output_dir"].as_posix(),
        "actual_next_iteration_output_dir": roots[
            "actual_next_iteration_output_dir"
        ].as_posix(),
        "project_id": inputs.get("project_id"),
        "runner_execution_id": inputs.get("runner_execution_id"),
        "runner_operator_id": inputs.get("runner_operator_id"),
        "runner_status": "blocked_output_collision"
        if "collision" in failure_stage
        else "blocked_unknown",
        "runner_decision": "reject_and_repair_runner",
        "next_allowed_action": "repair_runner",
        "failure_stage": failure_stage,
        "error_message": error_message,
        "runner_execution_performed": False,
        "next_bounded_smoke_iteration_executed": False,
        "next_iteration_output_dir_created": False,
        "actual_next_iteration_output_dir_created": False,
        "candidate_input_path_checked": False,
        "candidate_input_path_listed": False,
        "candidate_input_file_read": False,
        "candidate_input_file_hashing_performed": False,
        "candidate_file_count": 0,
        "candidate_total_bytes": 0,
        "candidate_limit_enforced": True,
        "production_scan_approved": False,
        "production_promotion_granted": False,
        "automatic_approval_performed": False,
        "autonomous_execution_performed": False,
        "required_human_approval": True,
        "required_human_review": True,
        "actual_iteration_artifacts": [],
    }
    payload.update(_BOUNDARY_FALSE_FLAGS)
    return LocalAssetNextBoundedSmokeIterationRunnerResult(
        runner_admission_output_dir=roots["runner_admission_output_dir"],
        runner_output_dir=roots["runner_output_dir"],
        actual_next_iteration_output_dir=roots["actual_next_iteration_output_dir"],
        runner_path=None,
        runner_manifest_path=None,
        runner_summary_path=None,
        runner_checklist_path=None,
        artifact_index_path=None,
        artifact_index_manifest_path=None,
        actual_iteration_artifacts=[],
        complete=False,
        runner_status=str(payload["runner_status"]),
        runner_decision=str(payload["runner_decision"]),
        payload=payload,
    )


def _blocker(blocker_role: str, message: str, **extra: object) -> dict[str, object]:
    payload = {
        "blocker_role": blocker_role,
        "message": message,
    }
    payload.update(extra)
    return payload


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _sha256_regular_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _dict_payload(payloads: dict[str, object], role: str) -> dict[str, object]:
    payload = payloads.get(role)
    return payload if isinstance(payload, dict) else {}


def _dict_or_empty(value: object) -> dict[str, object]:
    return dict(value) if isinstance(value, dict) else {}


def _list_or_empty(value: object) -> list[object]:
    return list(value) if isinstance(value, list) else []


def _first_text(*values: object) -> str | None:
    for value in values:
        if isinstance(value, str) and value:
            return value
    return None


def _safe_int(value: object, default: int) -> int:
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    return default


def _bool_text(value: object) -> str:
    return "true" if value is True else "false"


def _path_text_or_none(path: Path | None) -> str | None:
    return None if path is None else path.as_posix()


def _write_json_exclusive(path: Path, payload: dict[str, object]) -> None:
    with path.open("x", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")


def _write_text_exclusive(path: Path, content: str) -> None:
    with path.open("x", encoding="utf-8") as handle:
        handle.write(content)
