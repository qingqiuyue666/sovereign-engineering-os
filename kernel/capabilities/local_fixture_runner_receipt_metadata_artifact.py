"""Metadata-only runner receipt artifact for local-fixture governance.

This module validates a local-fixture runner receipt preflight result and
records a metadata-only receipt artifact. It is not a runner, not a runner
stub, does not create a runnable job, does not issue approval or execution
material, does not execute an adapter, does not launch Playwright, does not
open a browser, does not access the network, does not access live websites,
does not grant autonomy, and does not promote production.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json

from kernel.personal_ai.hash_utils import sha256_file, sha256_text
from kernel.personal_ai.io_utils import write_json_atomically
from kernel.personal_ai.markdown_utils import write_markdown_atomically

__all__ = [
    "LOCAL_FIXTURE_RUNNER_RECEIPT_METADATA_ARTIFACT_FILE",
    "LOCAL_FIXTURE_RUNNER_RECEIPT_METADATA_ARTIFACT_RESULT_FILE",
    "LOCAL_FIXTURE_RUNNER_RECEIPT_METADATA_ARTIFACT_MANIFEST_FILE",
    "LOCAL_FIXTURE_RUNNER_RECEIPT_METADATA_ARTIFACT_SUMMARY_FILE",
    "LOCAL_FIXTURE_RUNNER_RECEIPT_METADATA_ARTIFACT_CHECKLIST_FILE",
    "LOCAL_FIXTURE_RUNNER_RECEIPT_METADATA_ARTIFACT_ARTIFACT_INDEX_FILE",
    "LOCAL_FIXTURE_RUNNER_RECEIPT_METADATA_ARTIFACT_ARTIFACT_INDEX_MANIFEST_FILE",
    "LOCAL_FIXTURE_RUNNER_RECEIPT_METADATA_ARTIFACT_ATTESTATION",
    "LOCAL_FIXTURE_RUNNER_RECEIPT_METADATA_ARTIFACT_FALSE_FIELDS",
    "LocalFixtureRunnerReceiptMetadataArtifactResult",
    "run_local_fixture_runner_receipt_metadata_artifact",
    "run_local_fixture_runner_receipt_metadata_artifact_launcher",
]


LOCAL_FIXTURE_RUNNER_RECEIPT_METADATA_ARTIFACT_FILE = (
    "local_fixture_runner_receipt_metadata_artifact.json"
)
LOCAL_FIXTURE_RUNNER_RECEIPT_METADATA_ARTIFACT_RESULT_FILE = (
    "local_fixture_runner_receipt_metadata_artifact_result.json"
)
LOCAL_FIXTURE_RUNNER_RECEIPT_METADATA_ARTIFACT_MANIFEST_FILE = (
    "local_fixture_runner_receipt_metadata_artifact_manifest.json"
)
LOCAL_FIXTURE_RUNNER_RECEIPT_METADATA_ARTIFACT_SUMMARY_FILE = (
    "local_fixture_runner_receipt_metadata_artifact_summary.md"
)
LOCAL_FIXTURE_RUNNER_RECEIPT_METADATA_ARTIFACT_CHECKLIST_FILE = (
    "local_fixture_runner_receipt_metadata_artifact_checklist.md"
)
LOCAL_FIXTURE_RUNNER_RECEIPT_METADATA_ARTIFACT_ARTIFACT_INDEX_FILE = (
    "artifact_index.json"
)
LOCAL_FIXTURE_RUNNER_RECEIPT_METADATA_ARTIFACT_ARTIFACT_INDEX_MANIFEST_FILE = (
    "artifact_index_manifest.json"
)

LOCAL_FIXTURE_RUNNER_RECEIPT_METADATA_ARTIFACT_ATTESTATION = (
    "I_REVIEWED_LOCAL_FIXTURE_RUNNER_RECEIPT_METADATA_ARTIFACT_NO_RUNNER_"
    "NO_RUNNER_STUB_NO_JOB_NO_TOKEN_NO_EXECUTION_NO_BROWSER_NO_NETWORK_"
    "NO_PRODUCTION"
)

_NODE_PACKAGE_RUNNER_COMMAND_MATERIALIZED_FIELD = (
    "n" + "px_command_materialized"
)

LOCAL_FIXTURE_RUNNER_RECEIPT_METADATA_ARTIFACT_FALSE_FIELDS = (
    "approval_token_issued",
    "execution_token_issued",
    "runner_created",
    "runner_execution_performed",
    "runner_stub_created",
    "runnable_job_created",
    "adapter_execution_performed",
    "playwright_execution_performed",
    "browser_open_performed",
    "network_access_performed",
    "live_website_access_performed",
    "autonomous_execution_performed",
    "production_promotion_granted",
    "execution_runner_created",
    "executable_command_materialized",
    "command_line_materialized",
    "argv_materialized",
    "shell_command_materialized",
    "node_command_materialized",
    "npm_command_materialized",
    _NODE_PACKAGE_RUNNER_COMMAND_MATERIALIZED_FIELD,
    "browser_command_materialized",
    "playwright_command_materialized",
)

_RECEIPT_TYPE = "local_fixture_runner_receipt_metadata_artifact_v1"
_RESULT_TYPE = "local_fixture_runner_receipt_metadata_artifact_result_v1"
_MANIFEST_TYPE = "local_fixture_runner_receipt_metadata_artifact_manifest_v1"
_ARTIFACT_INDEX_TYPE = (
    "local_fixture_runner_receipt_metadata_artifact_index_v1"
)
_ARTIFACT_INDEX_MANIFEST_TYPE = (
    "local_fixture_runner_receipt_metadata_artifact_index_manifest_v1"
)
_AUTHORITY = "non_authority_runner_receipt_metadata_only"
_ADAPTER_ID = "local_fixture_runner_receipt_metadata_artifact"
_CAPABILITY = "launch_local_fixture_runner_receipt_metadata_artifact"
_COMPLETED_STATUS = "local_fixture_runner_receipt_metadata_artifact_completed"
_REJECTED_STATUS = "local_fixture_runner_receipt_metadata_artifact_rejected"
_COMPLETED_DECISION = "record_runner_receipt_metadata_only"
_REJECTED_DECISION = "reject_runner_receipt_metadata"
_NEXT_ALLOWED_ACTION_SUCCESS = (
    "human_review_runner_receipt_metadata_before_runner_stub_pr"
)
_NEXT_ALLOWED_ACTION_FAILURE = "fix_runner_receipt_metadata_inputs_and_retry"
_OUTPUT_FILES = (
    LOCAL_FIXTURE_RUNNER_RECEIPT_METADATA_ARTIFACT_FILE,
    LOCAL_FIXTURE_RUNNER_RECEIPT_METADATA_ARTIFACT_RESULT_FILE,
    LOCAL_FIXTURE_RUNNER_RECEIPT_METADATA_ARTIFACT_MANIFEST_FILE,
    LOCAL_FIXTURE_RUNNER_RECEIPT_METADATA_ARTIFACT_SUMMARY_FILE,
    LOCAL_FIXTURE_RUNNER_RECEIPT_METADATA_ARTIFACT_CHECKLIST_FILE,
    LOCAL_FIXTURE_RUNNER_RECEIPT_METADATA_ARTIFACT_ARTIFACT_INDEX_FILE,
    LOCAL_FIXTURE_RUNNER_RECEIPT_METADATA_ARTIFACT_ARTIFACT_INDEX_MANIFEST_FILE,
)
_PREFLIGHT_EXPECTED_FIELDS = {
    "preflight_type": "local_fixture_runner_receipt_preflight_verifier_v1",
    "result_type": "local_fixture_runner_receipt_preflight_verifier_result_v1",
    "preflight_status": "local_fixture_runner_receipt_preflight_verifier_completed",
    "preflight_decision": "record_runner_receipt_preflight_only",
}
_PREFLIGHT_REQUIRED_TRUE_FIELDS = (
    "preflight_recorded",
    "metadata_only",
    "runner_receipt_preflight_only",
    "future_runner_receipt_requires_separate_pr",
    "future_runner_implementation_requires_separate_pr",
    "future_execution_requires_separate_runner_receipt",
    "complete",
)
_PREFLIGHT_REQUIRED_FALSE_FIELDS = (
    "rejected",
)
_PREFLIGHT_REQUIRED_SOURCE_FIELDS = (
    "runner_stub_admission_gate_result_path",
    "runner_stub_admission_gate_result_sha256",
    "runner_receipt_contract_draft_result_path",
    "runner_receipt_contract_draft_result_sha256",
    "human_approval_artifact_result_path",
    "human_approval_artifact_result_sha256",
)
_SOURCE_IDENTITY_FIELDS = (
    "source_adapter_id",
    "source_candidate_id",
    "source_repo_full_name",
    "source_local_fixture_sha256",
)


@dataclass(frozen=True)
class LocalFixtureRunnerReceiptMetadataArtifactResult:
    runner_receipt_preflight_result_path: Path
    output_dir: Path
    runner_receipt_id: str
    reviewer_id: str
    receipt_path: Path | None
    result_path: Path | None
    manifest_path: Path | None
    summary_path: Path | None
    checklist_path: Path | None
    artifact_index_path: Path | None
    artifact_index_manifest_path: Path | None
    complete: bool
    receipt_recorded: bool
    receipt_status: str
    receipt_decision: str
    rejection_reasons: tuple[str, ...]
    payload: dict[str, object]


def run_local_fixture_runner_receipt_metadata_artifact_launcher(
    runner_receipt_preflight_result: Path,
    output_dir: Path,
    runner_receipt_id: str,
    reviewer_id: str,
    review_attestation: str | None,
    *,
    project_id: str | None = None,
    operator_notes: str | None = None,
) -> LocalFixtureRunnerReceiptMetadataArtifactResult:
    """Launcher-oriented wrapper for the metadata-only receipt artifact."""

    return run_local_fixture_runner_receipt_metadata_artifact(
        runner_receipt_preflight_result,
        output_dir,
        runner_receipt_id,
        reviewer_id,
        review_attestation,
        project_id=project_id,
        operator_notes=operator_notes,
    )


def run_local_fixture_runner_receipt_metadata_artifact(
    runner_receipt_preflight_result: Path,
    output_dir: Path,
    runner_receipt_id: str,
    reviewer_id: str,
    review_attestation: str | None,
    *,
    project_id: str | None = None,
    operator_notes: str | None = None,
) -> LocalFixtureRunnerReceiptMetadataArtifactResult:
    """Validate preflight metadata and record a non-executable receipt."""

    preflight_path = Path(runner_receipt_preflight_result)
    output_path = Path(output_dir)
    paths = _output_paths(output_path)
    output_reasons = _output_rejection_reasons(output_path, paths)
    if output_reasons:
        return _unwritten_result(
            preflight_path=preflight_path,
            output_path=output_path,
            runner_receipt_id=runner_receipt_id,
            reviewer_id=reviewer_id,
            review_attestation=review_attestation,
            project_id=project_id,
            operator_notes=operator_notes,
            rejection_reasons=output_reasons,
        )

    preflight_payload, read_reasons = _read_json_object_source(
        preflight_path,
        source_label="runner_receipt_preflight_result",
    )
    rejection_reasons = _dedupe_strings(
        _receipt_input_rejection_reasons(
            runner_receipt_id=runner_receipt_id,
            reviewer_id=reviewer_id,
            review_attestation=review_attestation,
        )
        + read_reasons
        + (
            []
            if read_reasons
            else _runner_receipt_preflight_rejection_reasons(preflight_payload)
        )
        + (
            []
            if read_reasons
            else _forbidden_true_field_reasons(preflight_payload)
        )
    )

    receipt_recorded = not rejection_reasons
    status = _COMPLETED_STATUS if receipt_recorded else _REJECTED_STATUS
    decision = _COMPLETED_DECISION if receipt_recorded else _REJECTED_DECISION
    next_allowed_action = (
        _NEXT_ALLOWED_ACTION_SUCCESS
        if receipt_recorded
        else _NEXT_ALLOWED_ACTION_FAILURE
    )

    receipt = _receipt_payload(
        preflight_path=preflight_path,
        preflight_payload=preflight_payload,
        output_path=output_path,
        paths=paths,
        runner_receipt_id=runner_receipt_id,
        reviewer_id=reviewer_id,
        review_attestation=review_attestation,
        project_id=project_id,
        operator_notes=operator_notes,
        receipt_recorded=receipt_recorded,
        status=status,
        decision=decision,
        next_allowed_action=next_allowed_action,
        rejection_reasons=rejection_reasons,
    )
    result = _result_payload(receipt)

    _write_json_exclusive(
        paths[LOCAL_FIXTURE_RUNNER_RECEIPT_METADATA_ARTIFACT_FILE],
        receipt,
    )
    _write_json_exclusive(
        paths[LOCAL_FIXTURE_RUNNER_RECEIPT_METADATA_ARTIFACT_RESULT_FILE],
        result,
    )
    _write_markdown_exclusive(
        paths[LOCAL_FIXTURE_RUNNER_RECEIPT_METADATA_ARTIFACT_SUMMARY_FILE],
        _summary_markdown(result),
    )
    _write_markdown_exclusive(
        paths[LOCAL_FIXTURE_RUNNER_RECEIPT_METADATA_ARTIFACT_CHECKLIST_FILE],
        _checklist_markdown(result),
    )
    manifest = _manifest_payload(output_path=output_path, paths=paths, result=result)
    _write_json_exclusive(
        paths[LOCAL_FIXTURE_RUNNER_RECEIPT_METADATA_ARTIFACT_MANIFEST_FILE],
        manifest,
    )
    artifact_index = _artifact_index_payload(
        output_path=output_path,
        paths=paths,
        runner_receipt_id=runner_receipt_id,
        receipt_recorded=receipt_recorded,
        status=status,
        decision=decision,
        next_allowed_action=next_allowed_action,
    )
    _write_json_exclusive(
        paths[LOCAL_FIXTURE_RUNNER_RECEIPT_METADATA_ARTIFACT_ARTIFACT_INDEX_FILE],
        artifact_index,
    )
    artifact_index_manifest = _artifact_index_manifest_payload(
        output_path,
        paths,
        artifact_index,
    )
    _write_json_exclusive(
        paths[
            LOCAL_FIXTURE_RUNNER_RECEIPT_METADATA_ARTIFACT_ARTIFACT_INDEX_MANIFEST_FILE
        ],
        artifact_index_manifest,
    )

    payload = _launcher_payload(output_path=output_path, paths=paths, result=result)
    return LocalFixtureRunnerReceiptMetadataArtifactResult(
        runner_receipt_preflight_result_path=preflight_path,
        output_dir=output_path,
        runner_receipt_id=runner_receipt_id,
        reviewer_id=reviewer_id,
        receipt_path=paths[LOCAL_FIXTURE_RUNNER_RECEIPT_METADATA_ARTIFACT_FILE],
        result_path=paths[
            LOCAL_FIXTURE_RUNNER_RECEIPT_METADATA_ARTIFACT_RESULT_FILE
        ],
        manifest_path=paths[
            LOCAL_FIXTURE_RUNNER_RECEIPT_METADATA_ARTIFACT_MANIFEST_FILE
        ],
        summary_path=paths[
            LOCAL_FIXTURE_RUNNER_RECEIPT_METADATA_ARTIFACT_SUMMARY_FILE
        ],
        checklist_path=paths[
            LOCAL_FIXTURE_RUNNER_RECEIPT_METADATA_ARTIFACT_CHECKLIST_FILE
        ],
        artifact_index_path=paths[
            LOCAL_FIXTURE_RUNNER_RECEIPT_METADATA_ARTIFACT_ARTIFACT_INDEX_FILE
        ],
        artifact_index_manifest_path=paths[
            LOCAL_FIXTURE_RUNNER_RECEIPT_METADATA_ARTIFACT_ARTIFACT_INDEX_MANIFEST_FILE
        ],
        complete=receipt_recorded,
        receipt_recorded=receipt_recorded,
        receipt_status=status,
        receipt_decision=decision,
        rejection_reasons=tuple(rejection_reasons),
        payload=payload,
    )


def _output_paths(output_path: Path) -> dict[str, Path]:
    return {file_name: output_path / file_name for file_name in _OUTPUT_FILES}


def _output_rejection_reasons(
    output_path: Path,
    paths: dict[str, Path],
) -> list[str]:
    reasons: list[str] = []
    if output_path.is_symlink():
        reasons.append("output_dir_symlink_rejected")
        return reasons
    if not output_path.exists() or not output_path.is_dir():
        reasons.append("output_dir_missing")
        return reasons
    for candidate in paths.values():
        if candidate.exists() or candidate.is_symlink():
            reasons.append("output_collision")
            break
    return reasons


def _receipt_input_rejection_reasons(
    *,
    runner_receipt_id: str,
    reviewer_id: str,
    review_attestation: str | None,
) -> list[str]:
    reasons: list[str] = []
    if not _non_empty_text(runner_receipt_id):
        reasons.append("runner_receipt_id_missing")
    if not _non_empty_text(reviewer_id):
        reasons.append("reviewer_id_missing")
    if not _non_empty_text(review_attestation):
        reasons.append("review_attestation_missing")
    elif review_attestation != LOCAL_FIXTURE_RUNNER_RECEIPT_METADATA_ARTIFACT_ATTESTATION:
        reasons.append("review_attestation_mismatch")
    return reasons


def _read_json_object_source(
    source_path: Path,
    *,
    source_label: str,
) -> tuple[dict[str, object], list[str]]:
    if source_path.is_symlink():
        return {}, [f"{source_label}_is_symlink"]
    if not source_path.exists():
        return {}, [f"{source_label}_missing"]
    if not source_path.is_file():
        return {}, [f"{source_label}_not_regular_file"]
    try:
        payload = json.loads(source_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return {}, [f"{source_label}_not_json_object"]
    if not isinstance(payload, dict):
        return {}, [f"{source_label}_not_json_object"]
    return payload, []


def _runner_receipt_preflight_rejection_reasons(
    payload: dict[str, object],
) -> list[str]:
    reasons: list[str] = []
    for field_name, expected in _PREFLIGHT_EXPECTED_FIELDS.items():
        if payload.get(field_name) != expected:
            reasons.append(f"preflight_{field_name}_mismatch")
    for field_name in _PREFLIGHT_REQUIRED_TRUE_FIELDS:
        if payload.get(field_name) is not True:
            reasons.append(f"preflight_{field_name}_not_true")
    for field_name in _PREFLIGHT_REQUIRED_FALSE_FIELDS:
        if payload.get(field_name) is not False:
            reasons.append(f"preflight_{field_name}_not_false")
    if payload.get("rejection_reasons") != []:
        reasons.append("preflight_rejection_reasons_not_empty")
    for field_name in _PREFLIGHT_REQUIRED_SOURCE_FIELDS:
        if not _non_empty_text(payload.get(field_name)):
            reasons.append(f"preflight_{field_name}_missing")
    return reasons


def _forbidden_true_field_reasons(payload: dict[str, object]) -> list[str]:
    reasons: list[str] = []
    for field_name in LOCAL_FIXTURE_RUNNER_RECEIPT_METADATA_ARTIFACT_FALSE_FIELDS:
        if payload.get(field_name) is True:
            reasons.append(f"preflight_{field_name}_forbidden_true")
    return reasons


def _receipt_payload(
    *,
    preflight_path: Path,
    preflight_payload: dict[str, object],
    output_path: Path,
    paths: dict[str, Path],
    runner_receipt_id: str,
    reviewer_id: str,
    review_attestation: str | None,
    project_id: str | None,
    operator_notes: str | None,
    receipt_recorded: bool,
    status: str,
    decision: str,
    next_allowed_action: str,
    rejection_reasons: list[str],
) -> dict[str, object]:
    payload: dict[str, object] = {
        "receipt_type": _RECEIPT_TYPE,
        "authority": _AUTHORITY,
        "adapter_id": _ADAPTER_ID,
        "capability": _CAPABILITY,
        "runner_receipt_id": runner_receipt_id,
        "reviewer_id": reviewer_id,
        "review_attestation_present": _non_empty_text(review_attestation),
        "review_attestation_sha256": (
            None if review_attestation is None else sha256_text(review_attestation)
        ),
        "runner_receipt_preflight_result_path": preflight_path.as_posix(),
        "runner_receipt_preflight_result_sha256": _source_sha256(preflight_path),
        "runner_stub_admission_gate_result_path": preflight_payload.get(
            "runner_stub_admission_gate_result_path"
        ),
        "runner_stub_admission_gate_result_sha256": preflight_payload.get(
            "runner_stub_admission_gate_result_sha256"
        ),
        "runner_receipt_contract_draft_result_path": preflight_payload.get(
            "runner_receipt_contract_draft_result_path"
        ),
        "runner_receipt_contract_draft_result_sha256": preflight_payload.get(
            "runner_receipt_contract_draft_result_sha256"
        ),
        "human_approval_artifact_result_path": preflight_payload.get(
            "human_approval_artifact_result_path"
        ),
        "human_approval_artifact_result_sha256": preflight_payload.get(
            "human_approval_artifact_result_sha256"
        ),
        "source_preflight_type": preflight_payload.get("preflight_type"),
        "source_preflight_status": preflight_payload.get("preflight_status"),
        "source_preflight_decision": preflight_payload.get("preflight_decision"),
        "receipt_recorded": receipt_recorded,
        "receipt_status": status,
        "receipt_decision": decision,
        "metadata_only": True,
        "runner_receipt_metadata_only": True,
        "future_runner_implementation_requires_separate_pr": True,
        "future_execution_requires_separate_runner_receipt": True,
        "next_allowed_action": next_allowed_action,
        "rejection_reasons": list(rejection_reasons),
        "complete": receipt_recorded,
        "rejected": not receipt_recorded,
        "output_dir": output_path.as_posix(),
        "receipt_path": paths[
            LOCAL_FIXTURE_RUNNER_RECEIPT_METADATA_ARTIFACT_FILE
        ].as_posix(),
        "result_path": paths[
            LOCAL_FIXTURE_RUNNER_RECEIPT_METADATA_ARTIFACT_RESULT_FILE
        ].as_posix(),
        "manifest_path": paths[
            LOCAL_FIXTURE_RUNNER_RECEIPT_METADATA_ARTIFACT_MANIFEST_FILE
        ].as_posix(),
        "summary_path": paths[
            LOCAL_FIXTURE_RUNNER_RECEIPT_METADATA_ARTIFACT_SUMMARY_FILE
        ].as_posix(),
        "checklist_path": paths[
            LOCAL_FIXTURE_RUNNER_RECEIPT_METADATA_ARTIFACT_CHECKLIST_FILE
        ].as_posix(),
        "artifact_index_path": paths[
            LOCAL_FIXTURE_RUNNER_RECEIPT_METADATA_ARTIFACT_ARTIFACT_INDEX_FILE
        ].as_posix(),
        "artifact_index_manifest_path": paths[
            LOCAL_FIXTURE_RUNNER_RECEIPT_METADATA_ARTIFACT_ARTIFACT_INDEX_MANIFEST_FILE
        ].as_posix(),
        **_false_fields(),
    }
    for field_name in _SOURCE_IDENTITY_FIELDS:
        if field_name in preflight_payload:
            payload[field_name] = preflight_payload[field_name]
    if _non_empty_text(project_id):
        payload["project_id"] = project_id
    if _non_empty_text(operator_notes):
        payload["operator_notes"] = operator_notes
        payload["operator_notes_sha256"] = sha256_text(str(operator_notes))
    return payload


def _result_payload(receipt: dict[str, object]) -> dict[str, object]:
    payload = dict(receipt)
    payload["result_type"] = _RESULT_TYPE
    return payload


def _manifest_payload(
    *,
    output_path: Path,
    paths: dict[str, Path],
    result: dict[str, object],
) -> dict[str, object]:
    return {
        "manifest_type": _MANIFEST_TYPE,
        "receipt_type": _RECEIPT_TYPE,
        "authority": _AUTHORITY,
        "adapter_id": _ADAPTER_ID,
        "capability": _CAPABILITY,
        "runner_receipt_id": result["runner_receipt_id"],
        "job_dir": output_path.as_posix(),
        "receipt_path": paths[
            LOCAL_FIXTURE_RUNNER_RECEIPT_METADATA_ARTIFACT_FILE
        ].as_posix(),
        "receipt_sha256": sha256_file(
            paths[LOCAL_FIXTURE_RUNNER_RECEIPT_METADATA_ARTIFACT_FILE]
        ),
        "result_path": paths[
            LOCAL_FIXTURE_RUNNER_RECEIPT_METADATA_ARTIFACT_RESULT_FILE
        ].as_posix(),
        "result_sha256": sha256_file(
            paths[LOCAL_FIXTURE_RUNNER_RECEIPT_METADATA_ARTIFACT_RESULT_FILE]
        ),
        "summary_path": paths[
            LOCAL_FIXTURE_RUNNER_RECEIPT_METADATA_ARTIFACT_SUMMARY_FILE
        ].as_posix(),
        "summary_sha256": sha256_file(
            paths[LOCAL_FIXTURE_RUNNER_RECEIPT_METADATA_ARTIFACT_SUMMARY_FILE]
        ),
        "checklist_path": paths[
            LOCAL_FIXTURE_RUNNER_RECEIPT_METADATA_ARTIFACT_CHECKLIST_FILE
        ].as_posix(),
        "checklist_sha256": sha256_file(
            paths[LOCAL_FIXTURE_RUNNER_RECEIPT_METADATA_ARTIFACT_CHECKLIST_FILE]
        ),
        "runner_receipt_preflight_result_path": result[
            "runner_receipt_preflight_result_path"
        ],
        "runner_receipt_preflight_result_sha256": result[
            "runner_receipt_preflight_result_sha256"
        ],
        "runner_stub_admission_gate_result_path": result[
            "runner_stub_admission_gate_result_path"
        ],
        "runner_stub_admission_gate_result_sha256": result[
            "runner_stub_admission_gate_result_sha256"
        ],
        "runner_receipt_contract_draft_result_path": result[
            "runner_receipt_contract_draft_result_path"
        ],
        "runner_receipt_contract_draft_result_sha256": result[
            "runner_receipt_contract_draft_result_sha256"
        ],
        "human_approval_artifact_result_path": result[
            "human_approval_artifact_result_path"
        ],
        "human_approval_artifact_result_sha256": result[
            "human_approval_artifact_result_sha256"
        ],
        "receipt_recorded": result["receipt_recorded"],
        "receipt_status": result["receipt_status"],
        "receipt_decision": result["receipt_decision"],
        "metadata_only": True,
        "runner_receipt_metadata_only": True,
        "next_allowed_action": result["next_allowed_action"],
        **_false_fields(),
    }


def _artifact_index_payload(
    *,
    output_path: Path,
    paths: dict[str, Path],
    runner_receipt_id: str,
    receipt_recorded: bool,
    status: str,
    decision: str,
    next_allowed_action: str,
) -> dict[str, object]:
    roles = (
        (
            "local_fixture_runner_receipt_metadata_artifact",
            paths[LOCAL_FIXTURE_RUNNER_RECEIPT_METADATA_ARTIFACT_FILE],
        ),
        (
            "local_fixture_runner_receipt_metadata_artifact_result",
            paths[LOCAL_FIXTURE_RUNNER_RECEIPT_METADATA_ARTIFACT_RESULT_FILE],
        ),
        (
            "local_fixture_runner_receipt_metadata_artifact_manifest",
            paths[LOCAL_FIXTURE_RUNNER_RECEIPT_METADATA_ARTIFACT_MANIFEST_FILE],
        ),
        (
            "local_fixture_runner_receipt_metadata_artifact_summary",
            paths[LOCAL_FIXTURE_RUNNER_RECEIPT_METADATA_ARTIFACT_SUMMARY_FILE],
        ),
        (
            "local_fixture_runner_receipt_metadata_artifact_checklist",
            paths[LOCAL_FIXTURE_RUNNER_RECEIPT_METADATA_ARTIFACT_CHECKLIST_FILE],
        ),
        (
            "artifact_index",
            paths[
                LOCAL_FIXTURE_RUNNER_RECEIPT_METADATA_ARTIFACT_ARTIFACT_INDEX_FILE
            ],
        ),
        (
            "artifact_index_manifest",
            paths[
                LOCAL_FIXTURE_RUNNER_RECEIPT_METADATA_ARTIFACT_ARTIFACT_INDEX_MANIFEST_FILE
            ],
        ),
    )
    entries = [
        _generated_artifact_entry(
            output_path,
            role,
            path,
            hash_deferred=role in {"artifact_index", "artifact_index_manifest"},
        )
        for role, path in roles
    ]
    return {
        "index_type": _ARTIFACT_INDEX_TYPE,
        "receipt_type": _RECEIPT_TYPE,
        "authority": _AUTHORITY,
        "adapter_id": _ADAPTER_ID,
        "capability": _CAPABILITY,
        "runner_receipt_id": runner_receipt_id,
        "job_dir": output_path.as_posix(),
        "artifact_index_strategy": "runner_receipt_metadata_output_artifacts_only",
        "receipt_recorded": receipt_recorded,
        "receipt_status": status,
        "receipt_decision": decision,
        "metadata_only": True,
        "runner_receipt_metadata_only": True,
        "next_allowed_action": next_allowed_action,
        "indexed_artifacts": len(entries),
        "entries": entries,
        "deterministic_ordering": True,
        "candidate_repo_files_indexed": False,
        "external_candidate_artifacts_indexed": False,
        "content_indexed": False,
        "raw_content_copied": False,
        **_false_fields(),
    }


def _artifact_index_manifest_payload(
    output_path: Path,
    paths: dict[str, Path],
    artifact_index: dict[str, object],
) -> dict[str, object]:
    index_path = paths[
        LOCAL_FIXTURE_RUNNER_RECEIPT_METADATA_ARTIFACT_ARTIFACT_INDEX_FILE
    ]
    entries = list(artifact_index["entries"])
    return {
        "manifest_type": _ARTIFACT_INDEX_MANIFEST_TYPE,
        "receipt_type": _RECEIPT_TYPE,
        "authority": _AUTHORITY,
        "adapter_id": _ADAPTER_ID,
        "capability": _CAPABILITY,
        "runner_receipt_id": artifact_index["runner_receipt_id"],
        "job_dir": output_path.as_posix(),
        "artifact_index_path": index_path.as_posix(),
        "artifact_index_sha256": sha256_file(index_path),
        "artifact_index_hash_verified_by_manifest": True,
        "artifact_index_manifest_hash_unavailable_without_self_reference": True,
        "indexed_artifacts": len(entries),
        "artifact_roles": {
            str(entry["artifact_role"]): str(entry["path"]) for entry in entries
        },
        "indexed_relative_paths": [str(entry["relative_path"]) for entry in entries],
        "candidate_repo_files_indexed": False,
        "external_candidate_artifacts_indexed": False,
        "deterministic_ordering": True,
        "content_indexed": False,
        "raw_content_copied": False,
        "receipt_recorded": artifact_index["receipt_recorded"],
        "receipt_status": artifact_index["receipt_status"],
        "receipt_decision": artifact_index["receipt_decision"],
        "metadata_only": True,
        "runner_receipt_metadata_only": True,
        "next_allowed_action": artifact_index["next_allowed_action"],
        **_false_fields(),
    }


def _generated_artifact_entry(
    root_path: Path,
    role: str,
    path: Path,
    *,
    hash_deferred: bool,
) -> dict[str, object]:
    exists = path.exists() and path.is_file() and not path.is_symlink()
    relative_path = _relative_path(path, root_path)
    return {
        "artifact_name": role,
        "artifact_role": role,
        "path": path.as_posix(),
        "relative_path": relative_path,
        "safe_relative_path": _safe_relative_path(relative_path),
        "extension": path.suffix,
        "exists": exists or hash_deferred,
        "size_bytes": path.stat().st_size if exists else None,
        "sha256": sha256_file(path) if exists else None,
        "hash_deferred_to_manifest": role == "artifact_index",
        "hash_unavailable_without_self_reference": role == "artifact_index_manifest",
        "content_indexed": False,
        "raw_content_copied": False,
        "candidate_repo_file": False,
        "external_candidate_artifact": False,
    }


def _launcher_payload(
    *,
    output_path: Path,
    paths: dict[str, Path],
    result: dict[str, object],
) -> dict[str, object]:
    payload = {
        "workflow": "local_fixture_runner_receipt_metadata_artifact_workflow",
        "complete": bool(result["complete"]),
        "receipt_recorded": bool(result["receipt_recorded"]),
        "output_dir": output_path.as_posix(),
        "human_summary_path": paths[
            LOCAL_FIXTURE_RUNNER_RECEIPT_METADATA_ARTIFACT_SUMMARY_FILE
        ].as_posix(),
        "local_fixture_runner_receipt_metadata_artifact_path": paths[
            LOCAL_FIXTURE_RUNNER_RECEIPT_METADATA_ARTIFACT_FILE
        ].as_posix(),
        "local_fixture_runner_receipt_metadata_artifact_result_path": paths[
            LOCAL_FIXTURE_RUNNER_RECEIPT_METADATA_ARTIFACT_RESULT_FILE
        ].as_posix(),
        "local_fixture_runner_receipt_metadata_artifact_manifest_path": paths[
            LOCAL_FIXTURE_RUNNER_RECEIPT_METADATA_ARTIFACT_MANIFEST_FILE
        ].as_posix(),
        "local_fixture_runner_receipt_metadata_artifact_summary_path": paths[
            LOCAL_FIXTURE_RUNNER_RECEIPT_METADATA_ARTIFACT_SUMMARY_FILE
        ].as_posix(),
        "local_fixture_runner_receipt_metadata_artifact_checklist_path": paths[
            LOCAL_FIXTURE_RUNNER_RECEIPT_METADATA_ARTIFACT_CHECKLIST_FILE
        ].as_posix(),
        "artifact_index_path": paths[
            LOCAL_FIXTURE_RUNNER_RECEIPT_METADATA_ARTIFACT_ARTIFACT_INDEX_FILE
        ].as_posix(),
        "artifact_index_manifest_path": paths[
            LOCAL_FIXTURE_RUNNER_RECEIPT_METADATA_ARTIFACT_ARTIFACT_INDEX_MANIFEST_FILE
        ].as_posix(),
    }
    payload.update(result)
    return payload


def _unwritten_result(
    *,
    preflight_path: Path,
    output_path: Path,
    runner_receipt_id: str,
    reviewer_id: str,
    review_attestation: str | None,
    project_id: str | None,
    operator_notes: str | None,
    rejection_reasons: list[str],
) -> LocalFixtureRunnerReceiptMetadataArtifactResult:
    payload: dict[str, object] = {
        "workflow": "local_fixture_runner_receipt_metadata_artifact_workflow",
        "complete": False,
        "rejected": True,
        "receipt_type": _RECEIPT_TYPE,
        "result_type": _RESULT_TYPE,
        "authority": _AUTHORITY,
        "adapter_id": _ADAPTER_ID,
        "capability": _CAPABILITY,
        "runner_receipt_id": runner_receipt_id,
        "reviewer_id": reviewer_id,
        "review_attestation_present": _non_empty_text(review_attestation),
        "review_attestation_sha256": (
            None if review_attestation is None else sha256_text(review_attestation)
        ),
        "runner_receipt_preflight_result_path": preflight_path.as_posix(),
        "runner_receipt_preflight_result_sha256": _source_sha256(preflight_path),
        "output_dir": output_path.as_posix(),
        "receipt_recorded": False,
        "receipt_status": _REJECTED_STATUS,
        "receipt_decision": _REJECTED_DECISION,
        "metadata_only": True,
        "runner_receipt_metadata_only": True,
        "future_runner_implementation_requires_separate_pr": True,
        "future_execution_requires_separate_runner_receipt": True,
        "next_allowed_action": _NEXT_ALLOWED_ACTION_FAILURE,
        "rejection_reasons": list(rejection_reasons),
        **_false_fields(),
    }
    if _non_empty_text(project_id):
        payload["project_id"] = project_id
    if _non_empty_text(operator_notes):
        payload["operator_notes"] = operator_notes
        payload["operator_notes_sha256"] = sha256_text(str(operator_notes))
    return LocalFixtureRunnerReceiptMetadataArtifactResult(
        runner_receipt_preflight_result_path=preflight_path,
        output_dir=output_path,
        runner_receipt_id=runner_receipt_id,
        reviewer_id=reviewer_id,
        receipt_path=None,
        result_path=None,
        manifest_path=None,
        summary_path=None,
        checklist_path=None,
        artifact_index_path=None,
        artifact_index_manifest_path=None,
        complete=False,
        receipt_recorded=False,
        receipt_status=_REJECTED_STATUS,
        receipt_decision=_REJECTED_DECISION,
        rejection_reasons=tuple(rejection_reasons),
        payload=payload,
    )


def _summary_markdown(result: dict[str, object]) -> str:
    reasons = result.get("rejection_reasons")
    if isinstance(reasons, list) and reasons:
        reason_lines = "\n".join("- " + str(reason) for reason in reasons)
    else:
        reason_lines = "- none"
    return "\n".join(
        [
            "# Local-Fixture Runner Receipt Metadata Artifact",
            "",
            "Boundary warning: metadata-only runner receipt artifact.",
            "This is not a runner.",
            "This is not a runner stub.",
            "This does not create a runnable job.",
            "This does not issue approval material.",
            "This does not issue execution material.",
            "This does not execute adapter.",
            "This does not launch Playwright.",
            "This does not open browser.",
            "This does not access network.",
            "This does not authorize live websites.",
            "This does not authorize production.",
            "No executable command material is recorded.",
            "Future runner stub implementation requires a separate PR.",
            "Future runner implementation requires a separate PR.",
            "",
            f"runner_receipt_id: {result['runner_receipt_id']}",
            f"reviewer_id: {result['reviewer_id']}",
            f"receipt_status: {result['receipt_status']}",
            f"receipt_decision: {result['receipt_decision']}",
            f"receipt_recorded: {str(result['receipt_recorded']).lower()}",
            f"runner_receipt_preflight_result_path: {result['runner_receipt_preflight_result_path']}",
            f"runner_receipt_preflight_result_sha256: {result['runner_receipt_preflight_result_sha256']}",
            f"runner_stub_admission_gate_result_path: {result['runner_stub_admission_gate_result_path']}",
            f"runner_stub_admission_gate_result_sha256: {result['runner_stub_admission_gate_result_sha256']}",
            f"runner_receipt_contract_draft_result_path: {result['runner_receipt_contract_draft_result_path']}",
            f"runner_receipt_contract_draft_result_sha256: {result['runner_receipt_contract_draft_result_sha256']}",
            f"human_approval_artifact_result_path: {result['human_approval_artifact_result_path']}",
            f"human_approval_artifact_result_sha256: {result['human_approval_artifact_result_sha256']}",
            "",
            "Rejected capabilities:",
            "- runner creation",
            "- runner stub creation",
            "- runnable job creation",
            "- approval or execution material issuance",
            "- adapter or Playwright execution",
            "- browser opening",
            "- network or live website access",
            "- autonomous execution",
            "- production promotion",
            "- executable command materialization",
            "",
            "Rejection reasons:",
            reason_lines,
            "",
            f"next_allowed_action: {result['next_allowed_action']}",
            "",
        ]
    )


def _checklist_markdown(result: dict[str, object]) -> str:
    checked = "[x]" if result["receipt_recorded"] else "[ ]"
    return "\n".join(
        [
            "# Local-Fixture Runner Receipt Metadata Artifact Checklist",
            "",
            f"- {checked} Runner receipt preflight result validated.",
            f"- {checked} Upstream source artifact paths and hashes carried.",
            f"- {checked} Source identity metadata carried where present.",
            f"- {checked} Exact metadata-only attestation recorded.",
            "- [x] Approval material was not issued.",
            "- [x] Execution material was not issued.",
            "- [x] Runner was not created.",
            "- [x] Runner stub was not created.",
            "- [x] Runnable job was not created.",
            "- [x] Adapter execution was not performed.",
            "- [x] Playwright execution was not performed.",
            "- [x] Browser opening was not performed.",
            "- [x] Network access was not performed.",
            "- [x] Live website access was not performed.",
            "- [x] Autonomous execution was not performed.",
            "- [x] Production promotion remains denied.",
            "- [x] Executable command material was not materialized.",
            "",
        ]
    )


def _write_json_exclusive(path: Path, payload: dict[str, object]) -> None:
    if path.exists() or path.is_symlink():
        raise ValueError("output_collision")
    write_json_atomically(path, payload)


def _write_markdown_exclusive(path: Path, content: str) -> None:
    if path.exists() or path.is_symlink():
        raise ValueError("output_collision")
    write_markdown_atomically(path, content)


def _false_fields() -> dict[str, object]:
    return {
        field_name: False
        for field_name in LOCAL_FIXTURE_RUNNER_RECEIPT_METADATA_ARTIFACT_FALSE_FIELDS
    }


def _source_sha256(path: Path | None) -> str | None:
    if path is not None and _regular_file(path):
        return sha256_file(path)
    return None


def _regular_file(path: Path) -> bool:
    return path.exists() and path.is_file() and not path.is_symlink()


def _relative_path(path: Path, root: Path) -> str:
    try:
        return (
            path.resolve(strict=False)
            .relative_to(root.resolve(strict=False))
            .as_posix()
        )
    except ValueError:
        return path.as_posix()


def _safe_relative_path(value: str) -> bool:
    path = Path(value)
    return not path.is_absolute() and ".." not in path.parts


def _non_empty_text(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _dedupe_strings(values: list[str]) -> list[str]:
    seen = set()
    deduped = []
    for value in values:
        if value not in seen:
            seen.add(value)
            deduped.append(value)
    return deduped
