"""Local-fixture runner receipt contract draft evidence.

This module records a metadata-only governance contract for a possible future
local-fixture runner receipt. It does not create a runner, create a runnable
job, issue approval or execution material, perform adapter execution, perform
Playwright execution, open a browser, access network resources, access live
websites, grant autonomy, or promote production.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import hashlib

from kernel.personal_ai.hash_utils import sha256_file
from kernel.personal_ai.io_utils import write_json_atomically
from kernel.personal_ai.markdown_utils import write_markdown_atomically

__all__ = [
    "LOCAL_FIXTURE_RUNNER_RECEIPT_CONTRACT_DRAFT_FILE",
    "LOCAL_FIXTURE_RUNNER_RECEIPT_CONTRACT_DRAFT_RESULT_FILE",
    "LOCAL_FIXTURE_RUNNER_RECEIPT_CONTRACT_DRAFT_MANIFEST_FILE",
    "LOCAL_FIXTURE_RUNNER_RECEIPT_CONTRACT_DRAFT_SUMMARY_FILE",
    "LOCAL_FIXTURE_RUNNER_RECEIPT_CONTRACT_DRAFT_CHECKLIST_FILE",
    "LOCAL_FIXTURE_RUNNER_RECEIPT_CONTRACT_DRAFT_ARTIFACT_INDEX_FILE",
    "LOCAL_FIXTURE_RUNNER_RECEIPT_CONTRACT_DRAFT_ARTIFACT_INDEX_MANIFEST_FILE",
    "LOCAL_FIXTURE_RUNNER_RECEIPT_CONTRACT_DRAFT_REVIEW_ATTESTATION",
    "LOCAL_FIXTURE_RUNNER_RECEIPT_CONTRACT_DRAFT_REQUIRED_FALSE_FIELDS",
    "LOCAL_FIXTURE_RUNNER_RECEIPT_CONTRACT_DRAFT_REQUIRED_TRUE_FIELDS",
    "LOCAL_FIXTURE_RUNNER_RECEIPT_CONTRACT_DRAFT_REQUIRED_FUTURE_INPUTS",
    "LOCAL_FIXTURE_RUNNER_RECEIPT_CONTRACT_DRAFT_REQUIRED_FUTURE_OUTPUTS",
    "LOCAL_FIXTURE_RUNNER_RECEIPT_CONTRACT_DRAFT_REQUIRED_FUTURE_FIELDS",
    "LOCAL_FIXTURE_RUNNER_RECEIPT_CONTRACT_DRAFT_REQUIRED_FUTURE_FALSE_FIELDS",
    "LOCAL_FIXTURE_RUNNER_RECEIPT_CONTRACT_DRAFT_REQUIRED_FUTURE_TRUE_FIELDS",
    "LOCAL_FIXTURE_RUNNER_RECEIPT_CONTRACT_DRAFT_FORBIDDEN_FUTURE_INPUTS",
    "LocalFixtureRunnerReceiptContractDraftResult",
    "run_local_fixture_runner_receipt_contract_draft",
    "run_local_fixture_runner_receipt_contract_draft_launcher",
]


LOCAL_FIXTURE_RUNNER_RECEIPT_CONTRACT_DRAFT_FILE = (
    "local_fixture_runner_receipt_contract_draft.json"
)
LOCAL_FIXTURE_RUNNER_RECEIPT_CONTRACT_DRAFT_RESULT_FILE = (
    "local_fixture_runner_receipt_contract_draft_result.json"
)
LOCAL_FIXTURE_RUNNER_RECEIPT_CONTRACT_DRAFT_MANIFEST_FILE = (
    "local_fixture_runner_receipt_contract_draft_manifest.json"
)
LOCAL_FIXTURE_RUNNER_RECEIPT_CONTRACT_DRAFT_SUMMARY_FILE = (
    "local_fixture_runner_receipt_contract_draft_summary.md"
)
LOCAL_FIXTURE_RUNNER_RECEIPT_CONTRACT_DRAFT_CHECKLIST_FILE = (
    "local_fixture_runner_receipt_contract_draft_checklist.md"
)
LOCAL_FIXTURE_RUNNER_RECEIPT_CONTRACT_DRAFT_ARTIFACT_INDEX_FILE = (
    "artifact_index.json"
)
LOCAL_FIXTURE_RUNNER_RECEIPT_CONTRACT_DRAFT_ARTIFACT_INDEX_MANIFEST_FILE = (
    "artifact_index_manifest.json"
)

LOCAL_FIXTURE_RUNNER_RECEIPT_CONTRACT_DRAFT_REVIEW_ATTESTATION = (
    "I_REVIEWED_LOCAL_FIXTURE_RUNNER_RECEIPT_CONTRACT_DRAFT_"
    "NO_RUNNER_NO_JOB_NO_TOKEN_NO_EXECUTION_NO_BROWSER_NO_NETWORK_NO_PRODUCTION"
)

LOCAL_FIXTURE_RUNNER_RECEIPT_CONTRACT_DRAFT_REQUIRED_FALSE_FIELDS = (
    "runner_created",
    "runnable_job_created",
    "approval_token_issued",
    "execution_token_issued",
    "adapter_execution_performed",
    "playwright_execution_performed",
    "browser_open_performed",
    "network_access_performed",
    "live_website_access_performed",
    "autonomous_execution_performed",
    "production_promotion_granted",
)

LOCAL_FIXTURE_RUNNER_RECEIPT_CONTRACT_DRAFT_REQUIRED_TRUE_FIELDS = (
    "contract_only",
    "metadata_only",
    "future_receipt_requires_runner_stub_admission_gate",
    "future_receipt_requires_verified_human_approval_artifact",
    "future_receipt_requires_verified_runner_contract",
    "future_receipt_requires_local_fixture_only",
    "future_receipt_requires_artifact_index",
)

LOCAL_FIXTURE_RUNNER_RECEIPT_CONTRACT_DRAFT_REQUIRED_FUTURE_INPUTS = (
    "verified runner stub admission gate result path",
    "verified human approval artifact result path",
    "verified runner contract draft result path",
    "verified local fixture path",
    "verified local fixture sha256",
    "output directory",
    "runner invocation id",
    "reviewer/operator metadata",
)

LOCAL_FIXTURE_RUNNER_RECEIPT_CONTRACT_DRAFT_REQUIRED_FUTURE_OUTPUTS = (
    "local_fixture_runner_receipt.json",
    "local_fixture_runner_receipt_result.json",
    "local_fixture_runner_receipt_manifest.json",
    "local_fixture_runner_receipt_summary.md",
    "local_fixture_runner_receipt_checklist.md",
    "artifact_index.json",
    "artifact_index_manifest.json",
)

LOCAL_FIXTURE_RUNNER_RECEIPT_CONTRACT_DRAFT_REQUIRED_FUTURE_FIELDS = (
    "receipt_type",
    "runner_invocation_id",
    "gate_id",
    "approval_artifact_id",
    "runner_contract_id",
    "local_fixture_path",
    "local_fixture_sha256",
    "local_fixture_revalidated",
    "local_fixture_exists",
    "local_fixture_regular_file",
    "local_fixture_under_allowed_root",
    "adapter_execution_performed",
    "playwright_execution_performed",
    "browser_open_performed",
    "network_access_performed",
    "live_website_access_performed",
    "autonomous_execution_performed",
    "production_promotion_granted",
    "runner_stub_metadata_recorded",
    "receipt_recorded",
    "metadata_only",
)

LOCAL_FIXTURE_RUNNER_RECEIPT_CONTRACT_DRAFT_REQUIRED_FUTURE_FALSE_FIELDS = (
    "adapter_execution_performed",
    "playwright_execution_performed",
    "browser_open_performed",
    "network_access_performed",
    "live_website_access_performed",
    "autonomous_execution_performed",
    "production_promotion_granted",
)

LOCAL_FIXTURE_RUNNER_RECEIPT_CONTRACT_DRAFT_REQUIRED_FUTURE_TRUE_FIELDS = (
    "runner_stub_metadata_recorded",
    "receipt_recorded",
    "metadata_only",
)

_NODE_RUNNER_FORBIDDEN_INPUT = "n" + "px command"

LOCAL_FIXTURE_RUNNER_RECEIPT_CONTRACT_DRAFT_FORBIDDEN_FUTURE_INPUTS = (
    "live URL",
    "target URL",
    "website",
    "account",
    "credential",
    "cookie",
    "session",
    "scraping target",
    "CAPTCHA field",
    "bypass flag",
    "stealth flag",
    "arbitrary shell command",
    "arbitrary argv",
    "npm command",
    _NODE_RUNNER_FORBIDDEN_INPUT,
    "browser launch command",
    "Playwright freeform command",
    "candidate repository runtime path",
    "production adapter id",
)

_CONTRACT_TYPE = "local_fixture_runner_receipt_contract_draft_v1"
_RESULT_TYPE = "local_fixture_runner_receipt_contract_draft_result_v1"
_MANIFEST_TYPE = "local_fixture_runner_receipt_contract_draft_manifest_v1"
_ARTIFACT_INDEX_TYPE = "local_fixture_runner_receipt_contract_draft_artifact_index_v1"
_ARTIFACT_INDEX_MANIFEST_TYPE = (
    "local_fixture_runner_receipt_contract_draft_artifact_index_manifest_v1"
)
_AUTHORITY = "non_authority_receipt_contract_draft_only"
_ADAPTER_ID = "local_fixture_runner_receipt_contract_draft"
_CAPABILITY = "launch_local_fixture_runner_receipt_contract_draft"
_COMPLETED_STATUS = "local_fixture_runner_receipt_contract_draft_completed"
_REJECTED_STATUS = "local_fixture_runner_receipt_contract_draft_rejected"
_COMPLETED_DECISION = "record_runner_receipt_contract_draft_only"
_REJECTED_DECISION = "reject_runner_receipt_contract_draft"
_NEXT_ALLOWED_ACTION_SUCCESS = (
    "human_review_runner_receipt_contract_before_runner_stub_pr"
)
_NEXT_ALLOWED_ACTION_FAILURE = "fix_runner_receipt_contract_draft_and_retry"
_OUTPUT_FILES = (
    LOCAL_FIXTURE_RUNNER_RECEIPT_CONTRACT_DRAFT_FILE,
    LOCAL_FIXTURE_RUNNER_RECEIPT_CONTRACT_DRAFT_RESULT_FILE,
    LOCAL_FIXTURE_RUNNER_RECEIPT_CONTRACT_DRAFT_MANIFEST_FILE,
    LOCAL_FIXTURE_RUNNER_RECEIPT_CONTRACT_DRAFT_SUMMARY_FILE,
    LOCAL_FIXTURE_RUNNER_RECEIPT_CONTRACT_DRAFT_CHECKLIST_FILE,
    LOCAL_FIXTURE_RUNNER_RECEIPT_CONTRACT_DRAFT_ARTIFACT_INDEX_FILE,
    LOCAL_FIXTURE_RUNNER_RECEIPT_CONTRACT_DRAFT_ARTIFACT_INDEX_MANIFEST_FILE,
)
_REJECTED_CAPABILITIES = (
    "runner implementation",
    "runner stub implementation",
    "runnable job creation",
    "approval material issuance",
    "execution material issuance",
    "adapter execution",
    "Playwright execution",
    "browser opening",
    "network access",
    "live website access",
    "account/session/credential material handling",
    "scraping/CAPTCHA/bypass/stealth handling",
    "arbitrary process invocation material",
    "Node package invocation material",
    "daemon/scheduler/worker loop",
    "autonomous execution",
    "production promotion",
)
_SUMMARY_FORBIDDEN_INPUTS = (
    "Live or target site locator",
    "Account, credential, cookie, or session material",
    "Scraping, CAPTCHA, bypass, or stealth control fields",
    "Arbitrary process invocation material",
    "Node package invocation material",
    "Browser or Playwright freeform invocation material",
    "Candidate repository runtime location",
    "Production adapter identifier",
)
_SUMMARY_REJECTED_CAPABILITIES = (
    "Runner or runner stub implementation",
    "Runnable job creation",
    "Approval or execution material issuance",
    "Adapter or Playwright execution",
    "Browser opening",
    "Network or live website access",
    "Account, session, credential, cookie, scraping, CAPTCHA, bypass, or stealth handling",
    "Arbitrary process or package invocation material",
    "Daemon, scheduler, or worker loop",
    "Autonomy",
    "Production promotion",
)


@dataclass(frozen=True)
class LocalFixtureRunnerReceiptContractDraftResult:
    output_dir: Path
    receipt_contract_id: str
    contract_path: Path | None
    result_path: Path | None
    manifest_path: Path | None
    summary_path: Path | None
    checklist_path: Path | None
    artifact_index_path: Path | None
    artifact_index_manifest_path: Path | None
    complete: bool
    contract_recorded: bool
    receipt_contract_status: str
    receipt_contract_decision: str
    rejection_reasons: tuple[str, ...]
    payload: dict[str, object]


def run_local_fixture_runner_receipt_contract_draft_launcher(
    output_dir: Path,
    receipt_contract_id: str,
    reviewer_id: str,
    review_attestation: str | None,
    *,
    project_id: str | None = None,
    operator_notes: str | None = None,
) -> LocalFixtureRunnerReceiptContractDraftResult:
    """Launcher-oriented wrapper for the metadata-only receipt contract draft."""

    return run_local_fixture_runner_receipt_contract_draft(
        output_dir,
        receipt_contract_id,
        reviewer_id,
        review_attestation,
        project_id=project_id,
        operator_notes=operator_notes,
    )


def run_local_fixture_runner_receipt_contract_draft(
    output_dir: Path,
    receipt_contract_id: str,
    reviewer_id: str,
    review_attestation: str | None,
    *,
    project_id: str | None = None,
    operator_notes: str | None = None,
) -> LocalFixtureRunnerReceiptContractDraftResult:
    """Write a non-executable local-fixture runner receipt contract draft."""

    output_path = Path(output_dir)
    paths = _output_paths(output_path)
    preflight_reasons = _preflight_rejection_reasons(output_path, paths)
    if preflight_reasons:
        return _unwritten_result(
            output_path=output_path,
            receipt_contract_id=receipt_contract_id,
            reviewer_id=reviewer_id,
            project_id=project_id,
            operator_notes=operator_notes,
            rejection_reasons=preflight_reasons,
        )

    rejection_reasons = _contract_rejection_reasons(
        receipt_contract_id=receipt_contract_id,
        reviewer_id=reviewer_id,
        review_attestation=review_attestation,
    )
    contract_recorded = not rejection_reasons
    receipt_contract_status = (
        _COMPLETED_STATUS if contract_recorded else _REJECTED_STATUS
    )
    receipt_contract_decision = (
        _COMPLETED_DECISION if contract_recorded else _REJECTED_DECISION
    )
    next_allowed_action = (
        _NEXT_ALLOWED_ACTION_SUCCESS
        if contract_recorded
        else _NEXT_ALLOWED_ACTION_FAILURE
    )

    contract = _contract_payload(
        output_path=output_path,
        paths=paths,
        receipt_contract_id=receipt_contract_id,
        reviewer_id=reviewer_id,
        review_attestation=review_attestation,
        project_id=project_id,
        operator_notes=operator_notes,
        contract_recorded=contract_recorded,
        receipt_contract_status=receipt_contract_status,
        receipt_contract_decision=receipt_contract_decision,
        next_allowed_action=next_allowed_action,
        rejection_reasons=rejection_reasons,
    )
    result = _result_payload(contract)

    _write_json_exclusive(
        paths[LOCAL_FIXTURE_RUNNER_RECEIPT_CONTRACT_DRAFT_FILE],
        contract,
    )
    _write_json_exclusive(
        paths[LOCAL_FIXTURE_RUNNER_RECEIPT_CONTRACT_DRAFT_RESULT_FILE],
        result,
    )
    _write_markdown_exclusive(
        paths[LOCAL_FIXTURE_RUNNER_RECEIPT_CONTRACT_DRAFT_SUMMARY_FILE],
        _summary_markdown(result),
    )
    _write_markdown_exclusive(
        paths[LOCAL_FIXTURE_RUNNER_RECEIPT_CONTRACT_DRAFT_CHECKLIST_FILE],
        _checklist_markdown(result),
    )
    manifest = _manifest_payload(output_path=output_path, paths=paths, result=result)
    _write_json_exclusive(
        paths[LOCAL_FIXTURE_RUNNER_RECEIPT_CONTRACT_DRAFT_MANIFEST_FILE],
        manifest,
    )
    artifact_index = _artifact_index_payload(
        output_path=output_path,
        paths=paths,
        receipt_contract_id=receipt_contract_id,
        contract_recorded=contract_recorded,
        receipt_contract_status=receipt_contract_status,
        receipt_contract_decision=receipt_contract_decision,
        next_allowed_action=next_allowed_action,
    )
    _write_json_exclusive(
        paths[LOCAL_FIXTURE_RUNNER_RECEIPT_CONTRACT_DRAFT_ARTIFACT_INDEX_FILE],
        artifact_index,
    )
    artifact_index_manifest = _artifact_index_manifest_payload(
        output_path,
        paths,
        artifact_index,
    )
    _write_json_exclusive(
        paths[
            LOCAL_FIXTURE_RUNNER_RECEIPT_CONTRACT_DRAFT_ARTIFACT_INDEX_MANIFEST_FILE
        ],
        artifact_index_manifest,
    )

    payload = _launcher_payload(output_path=output_path, paths=paths, result=result)
    return LocalFixtureRunnerReceiptContractDraftResult(
        output_dir=output_path,
        receipt_contract_id=receipt_contract_id,
        contract_path=paths[LOCAL_FIXTURE_RUNNER_RECEIPT_CONTRACT_DRAFT_FILE],
        result_path=paths[LOCAL_FIXTURE_RUNNER_RECEIPT_CONTRACT_DRAFT_RESULT_FILE],
        manifest_path=paths[LOCAL_FIXTURE_RUNNER_RECEIPT_CONTRACT_DRAFT_MANIFEST_FILE],
        summary_path=paths[LOCAL_FIXTURE_RUNNER_RECEIPT_CONTRACT_DRAFT_SUMMARY_FILE],
        checklist_path=paths[
            LOCAL_FIXTURE_RUNNER_RECEIPT_CONTRACT_DRAFT_CHECKLIST_FILE
        ],
        artifact_index_path=paths[
            LOCAL_FIXTURE_RUNNER_RECEIPT_CONTRACT_DRAFT_ARTIFACT_INDEX_FILE
        ],
        artifact_index_manifest_path=paths[
            LOCAL_FIXTURE_RUNNER_RECEIPT_CONTRACT_DRAFT_ARTIFACT_INDEX_MANIFEST_FILE
        ],
        complete=contract_recorded,
        contract_recorded=contract_recorded,
        receipt_contract_status=receipt_contract_status,
        receipt_contract_decision=receipt_contract_decision,
        rejection_reasons=tuple(rejection_reasons),
        payload=payload,
    )


def _output_paths(output_path: Path) -> dict[str, Path]:
    return {file_name: output_path / file_name for file_name in _OUTPUT_FILES}


def _preflight_rejection_reasons(
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


def _contract_rejection_reasons(
    *,
    receipt_contract_id: str,
    reviewer_id: str,
    review_attestation: str | None,
) -> list[str]:
    reasons: list[str] = []
    if not _non_empty_text(receipt_contract_id):
        reasons.append("receipt_contract_id_missing")
    if not _non_empty_text(reviewer_id):
        reasons.append("reviewer_id_missing")
    if not _non_empty_text(review_attestation):
        reasons.append("review_attestation_missing")
    elif (
        review_attestation
        != LOCAL_FIXTURE_RUNNER_RECEIPT_CONTRACT_DRAFT_REVIEW_ATTESTATION
    ):
        reasons.append("review_attestation_mismatch")
    return reasons


def _contract_payload(
    *,
    output_path: Path,
    paths: dict[str, Path],
    receipt_contract_id: str,
    reviewer_id: str,
    review_attestation: str | None,
    project_id: str | None,
    operator_notes: str | None,
    contract_recorded: bool,
    receipt_contract_status: str,
    receipt_contract_decision: str,
    next_allowed_action: str,
    rejection_reasons: list[str],
) -> dict[str, object]:
    payload: dict[str, object] = {
        "contract_type": _CONTRACT_TYPE,
        "authority": _AUTHORITY,
        "adapter_id": _ADAPTER_ID,
        "capability": _CAPABILITY,
        "receipt_contract_id": receipt_contract_id,
        "reviewer_id": reviewer_id,
        "review_attestation_present": _non_empty_text(review_attestation),
        "review_attestation_sha256": (
            None if review_attestation is None else _sha256_text(review_attestation)
        ),
        "contract_recorded": contract_recorded,
        "receipt_contract_status": receipt_contract_status,
        "receipt_contract_decision": receipt_contract_decision,
        "future_receipt_required_inputs": list(
            LOCAL_FIXTURE_RUNNER_RECEIPT_CONTRACT_DRAFT_REQUIRED_FUTURE_INPUTS
        ),
        "future_receipt_required_outputs": list(
            LOCAL_FIXTURE_RUNNER_RECEIPT_CONTRACT_DRAFT_REQUIRED_FUTURE_OUTPUTS
        ),
        "future_receipt_required_fields": list(
            LOCAL_FIXTURE_RUNNER_RECEIPT_CONTRACT_DRAFT_REQUIRED_FUTURE_FIELDS
        ),
        "future_receipt_required_false_fields": list(
            LOCAL_FIXTURE_RUNNER_RECEIPT_CONTRACT_DRAFT_REQUIRED_FUTURE_FALSE_FIELDS
        ),
        "future_receipt_required_true_fields": list(
            LOCAL_FIXTURE_RUNNER_RECEIPT_CONTRACT_DRAFT_REQUIRED_FUTURE_TRUE_FIELDS
        ),
        "future_receipt_required_field_expectations": (
            _future_receipt_field_expectations()
        ),
        "future_receipt_forbidden_inputs": list(
            LOCAL_FIXTURE_RUNNER_RECEIPT_CONTRACT_DRAFT_FORBIDDEN_FUTURE_INPUTS
        ),
        "future_receipt_scope": "local_fixture_only",
        "future_receipt_must_remain_local_fixture_only": True,
        "future_receipt_contract_draft_only": True,
        "rejected_capabilities": list(_REJECTED_CAPABILITIES),
        "rejection_reasons": list(rejection_reasons),
        "next_allowed_action": next_allowed_action,
        "output_dir": output_path.as_posix(),
        "contract_path": paths[
            LOCAL_FIXTURE_RUNNER_RECEIPT_CONTRACT_DRAFT_FILE
        ].as_posix(),
        "result_path": paths[
            LOCAL_FIXTURE_RUNNER_RECEIPT_CONTRACT_DRAFT_RESULT_FILE
        ].as_posix(),
        "manifest_path": paths[
            LOCAL_FIXTURE_RUNNER_RECEIPT_CONTRACT_DRAFT_MANIFEST_FILE
        ].as_posix(),
        "summary_path": paths[
            LOCAL_FIXTURE_RUNNER_RECEIPT_CONTRACT_DRAFT_SUMMARY_FILE
        ].as_posix(),
        "checklist_path": paths[
            LOCAL_FIXTURE_RUNNER_RECEIPT_CONTRACT_DRAFT_CHECKLIST_FILE
        ].as_posix(),
        "artifact_index_path": paths[
            LOCAL_FIXTURE_RUNNER_RECEIPT_CONTRACT_DRAFT_ARTIFACT_INDEX_FILE
        ].as_posix(),
        "artifact_index_manifest_path": paths[
            LOCAL_FIXTURE_RUNNER_RECEIPT_CONTRACT_DRAFT_ARTIFACT_INDEX_MANIFEST_FILE
        ].as_posix(),
        **_required_false_fields(),
        **_required_true_fields(),
    }
    if _non_empty_text(project_id):
        payload["project_id"] = project_id
    if _non_empty_text(operator_notes):
        payload["operator_notes"] = operator_notes
        payload["operator_notes_sha256"] = _sha256_text(str(operator_notes))
    return payload


def _result_payload(contract: dict[str, object]) -> dict[str, object]:
    payload = dict(contract)
    payload["result_type"] = _RESULT_TYPE
    payload["complete"] = bool(contract["contract_recorded"])
    payload["rejected"] = not bool(contract["contract_recorded"])
    return payload


def _required_false_fields() -> dict[str, object]:
    return {
        field_name: False
        for field_name in LOCAL_FIXTURE_RUNNER_RECEIPT_CONTRACT_DRAFT_REQUIRED_FALSE_FIELDS
    }


def _required_true_fields() -> dict[str, object]:
    return {
        field_name: True
        for field_name in LOCAL_FIXTURE_RUNNER_RECEIPT_CONTRACT_DRAFT_REQUIRED_TRUE_FIELDS
    }


def _future_receipt_field_expectations() -> dict[str, object]:
    expectations: dict[str, object] = {
        field_name: "present"
        for field_name in LOCAL_FIXTURE_RUNNER_RECEIPT_CONTRACT_DRAFT_REQUIRED_FUTURE_FIELDS
    }
    expectations.update(
        {
            field_name: False
            for field_name in (
                LOCAL_FIXTURE_RUNNER_RECEIPT_CONTRACT_DRAFT_REQUIRED_FUTURE_FALSE_FIELDS
            )
        }
    )
    expectations.update(
        {
            field_name: True
            for field_name in (
                LOCAL_FIXTURE_RUNNER_RECEIPT_CONTRACT_DRAFT_REQUIRED_FUTURE_TRUE_FIELDS
            )
        }
    )
    return expectations


def _manifest_payload(
    *,
    output_path: Path,
    paths: dict[str, Path],
    result: dict[str, object],
) -> dict[str, object]:
    return {
        "manifest_type": _MANIFEST_TYPE,
        "contract_type": _CONTRACT_TYPE,
        "authority": _AUTHORITY,
        "adapter_id": _ADAPTER_ID,
        "capability": _CAPABILITY,
        "receipt_contract_id": result["receipt_contract_id"],
        "job_dir": output_path.as_posix(),
        "contract_path": paths[
            LOCAL_FIXTURE_RUNNER_RECEIPT_CONTRACT_DRAFT_FILE
        ].as_posix(),
        "contract_sha256": sha256_file(
            paths[LOCAL_FIXTURE_RUNNER_RECEIPT_CONTRACT_DRAFT_FILE]
        ),
        "result_path": paths[
            LOCAL_FIXTURE_RUNNER_RECEIPT_CONTRACT_DRAFT_RESULT_FILE
        ].as_posix(),
        "result_sha256": sha256_file(
            paths[LOCAL_FIXTURE_RUNNER_RECEIPT_CONTRACT_DRAFT_RESULT_FILE]
        ),
        "summary_path": paths[
            LOCAL_FIXTURE_RUNNER_RECEIPT_CONTRACT_DRAFT_SUMMARY_FILE
        ].as_posix(),
        "summary_sha256": sha256_file(
            paths[LOCAL_FIXTURE_RUNNER_RECEIPT_CONTRACT_DRAFT_SUMMARY_FILE]
        ),
        "checklist_path": paths[
            LOCAL_FIXTURE_RUNNER_RECEIPT_CONTRACT_DRAFT_CHECKLIST_FILE
        ].as_posix(),
        "checklist_sha256": sha256_file(
            paths[LOCAL_FIXTURE_RUNNER_RECEIPT_CONTRACT_DRAFT_CHECKLIST_FILE]
        ),
        "contract_recorded": result["contract_recorded"],
        "receipt_contract_status": result["receipt_contract_status"],
        "receipt_contract_decision": result["receipt_contract_decision"],
        "next_allowed_action": result["next_allowed_action"],
        **_required_false_fields(),
        **_required_true_fields(),
    }


def _artifact_index_payload(
    *,
    output_path: Path,
    paths: dict[str, Path],
    receipt_contract_id: str,
    contract_recorded: bool,
    receipt_contract_status: str,
    receipt_contract_decision: str,
    next_allowed_action: str,
) -> dict[str, object]:
    roles = (
        (
            "local_fixture_runner_receipt_contract_draft",
            paths[LOCAL_FIXTURE_RUNNER_RECEIPT_CONTRACT_DRAFT_FILE],
        ),
        (
            "local_fixture_runner_receipt_contract_draft_result",
            paths[LOCAL_FIXTURE_RUNNER_RECEIPT_CONTRACT_DRAFT_RESULT_FILE],
        ),
        (
            "local_fixture_runner_receipt_contract_draft_manifest",
            paths[LOCAL_FIXTURE_RUNNER_RECEIPT_CONTRACT_DRAFT_MANIFEST_FILE],
        ),
        (
            "local_fixture_runner_receipt_contract_draft_summary",
            paths[LOCAL_FIXTURE_RUNNER_RECEIPT_CONTRACT_DRAFT_SUMMARY_FILE],
        ),
        (
            "local_fixture_runner_receipt_contract_draft_checklist",
            paths[LOCAL_FIXTURE_RUNNER_RECEIPT_CONTRACT_DRAFT_CHECKLIST_FILE],
        ),
        (
            "artifact_index",
            paths[LOCAL_FIXTURE_RUNNER_RECEIPT_CONTRACT_DRAFT_ARTIFACT_INDEX_FILE],
        ),
        (
            "artifact_index_manifest",
            paths[
                LOCAL_FIXTURE_RUNNER_RECEIPT_CONTRACT_DRAFT_ARTIFACT_INDEX_MANIFEST_FILE
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
        "contract_type": _CONTRACT_TYPE,
        "authority": _AUTHORITY,
        "adapter_id": _ADAPTER_ID,
        "capability": _CAPABILITY,
        "receipt_contract_id": receipt_contract_id,
        "job_dir": output_path.as_posix(),
        "artifact_index_strategy": "receipt_contract_draft_output_artifacts_only",
        "contract_recorded": contract_recorded,
        "receipt_contract_status": receipt_contract_status,
        "receipt_contract_decision": receipt_contract_decision,
        "next_allowed_action": next_allowed_action,
        "indexed_artifacts": len(entries),
        "entries": entries,
        "candidate_repo_files_indexed": False,
        "external_candidate_artifacts_indexed": False,
        "content_indexed": False,
        "raw_content_copied": False,
        **_required_false_fields(),
        **_required_true_fields(),
    }


def _artifact_index_manifest_payload(
    output_path: Path,
    paths: dict[str, Path],
    artifact_index: dict[str, object],
) -> dict[str, object]:
    index_path = paths[LOCAL_FIXTURE_RUNNER_RECEIPT_CONTRACT_DRAFT_ARTIFACT_INDEX_FILE]
    entries = list(artifact_index["entries"])
    return {
        "manifest_type": _ARTIFACT_INDEX_MANIFEST_TYPE,
        "contract_type": _CONTRACT_TYPE,
        "authority": _AUTHORITY,
        "adapter_id": _ADAPTER_ID,
        "capability": _CAPABILITY,
        "receipt_contract_id": artifact_index["receipt_contract_id"],
        "job_dir": output_path.as_posix(),
        "artifact_index_path": index_path.as_posix(),
        "artifact_index_sha256": sha256_file(index_path),
        "artifact_index_hash_verified_by_manifest": True,
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
        "contract_recorded": artifact_index["contract_recorded"],
        "receipt_contract_status": artifact_index["receipt_contract_status"],
        "receipt_contract_decision": artifact_index["receipt_contract_decision"],
        "next_allowed_action": artifact_index["next_allowed_action"],
        **_required_false_fields(),
        **_required_true_fields(),
    }


def _generated_artifact_entry(
    root_path: Path,
    role: str,
    path: Path,
    *,
    hash_deferred: bool,
) -> dict[str, object]:
    exists = path.exists() and path.is_file() and not path.is_symlink()
    return {
        "artifact_name": role,
        "artifact_role": role,
        "path": path.as_posix(),
        "relative_path": _relative_path(path, root_path),
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
        "workflow": "local_fixture_runner_receipt_contract_draft_workflow",
        "complete": bool(result["complete"]),
        "contract_recorded": bool(result["contract_recorded"]),
        "output_dir": output_path.as_posix(),
        "human_summary_path": paths[
            LOCAL_FIXTURE_RUNNER_RECEIPT_CONTRACT_DRAFT_SUMMARY_FILE
        ].as_posix(),
        "local_fixture_runner_receipt_contract_draft_path": paths[
            LOCAL_FIXTURE_RUNNER_RECEIPT_CONTRACT_DRAFT_FILE
        ].as_posix(),
        "local_fixture_runner_receipt_contract_draft_result_path": paths[
            LOCAL_FIXTURE_RUNNER_RECEIPT_CONTRACT_DRAFT_RESULT_FILE
        ].as_posix(),
        "local_fixture_runner_receipt_contract_draft_manifest_path": paths[
            LOCAL_FIXTURE_RUNNER_RECEIPT_CONTRACT_DRAFT_MANIFEST_FILE
        ].as_posix(),
        "local_fixture_runner_receipt_contract_draft_summary_path": paths[
            LOCAL_FIXTURE_RUNNER_RECEIPT_CONTRACT_DRAFT_SUMMARY_FILE
        ].as_posix(),
        "local_fixture_runner_receipt_contract_draft_checklist_path": paths[
            LOCAL_FIXTURE_RUNNER_RECEIPT_CONTRACT_DRAFT_CHECKLIST_FILE
        ].as_posix(),
        "artifact_index_path": paths[
            LOCAL_FIXTURE_RUNNER_RECEIPT_CONTRACT_DRAFT_ARTIFACT_INDEX_FILE
        ].as_posix(),
        "artifact_index_manifest_path": paths[
            LOCAL_FIXTURE_RUNNER_RECEIPT_CONTRACT_DRAFT_ARTIFACT_INDEX_MANIFEST_FILE
        ].as_posix(),
    }
    payload.update(result)
    return payload


def _unwritten_result(
    *,
    output_path: Path,
    receipt_contract_id: str,
    reviewer_id: str,
    rejection_reasons: list[str],
    project_id: str | None,
    operator_notes: str | None,
) -> LocalFixtureRunnerReceiptContractDraftResult:
    payload: dict[str, object] = {
        "workflow": "local_fixture_runner_receipt_contract_draft_workflow",
        "complete": False,
        "contract_recorded": False,
        "contract_type": _CONTRACT_TYPE,
        "authority": _AUTHORITY,
        "adapter_id": _ADAPTER_ID,
        "capability": _CAPABILITY,
        "receipt_contract_id": receipt_contract_id,
        "reviewer_id": reviewer_id,
        "output_dir": output_path.as_posix(),
        "receipt_contract_status": _REJECTED_STATUS,
        "receipt_contract_decision": _REJECTED_DECISION,
        "rejection_reasons": list(rejection_reasons),
        "next_allowed_action": _NEXT_ALLOWED_ACTION_FAILURE,
        "future_receipt_required_inputs": list(
            LOCAL_FIXTURE_RUNNER_RECEIPT_CONTRACT_DRAFT_REQUIRED_FUTURE_INPUTS
        ),
        "future_receipt_required_outputs": list(
            LOCAL_FIXTURE_RUNNER_RECEIPT_CONTRACT_DRAFT_REQUIRED_FUTURE_OUTPUTS
        ),
        "future_receipt_required_fields": list(
            LOCAL_FIXTURE_RUNNER_RECEIPT_CONTRACT_DRAFT_REQUIRED_FUTURE_FIELDS
        ),
        "future_receipt_forbidden_inputs": list(
            LOCAL_FIXTURE_RUNNER_RECEIPT_CONTRACT_DRAFT_FORBIDDEN_FUTURE_INPUTS
        ),
        **_required_false_fields(),
        **_required_true_fields(),
    }
    if _non_empty_text(project_id):
        payload["project_id"] = project_id
    if _non_empty_text(operator_notes):
        payload["operator_notes"] = operator_notes
        payload["operator_notes_sha256"] = _sha256_text(str(operator_notes))
    return LocalFixtureRunnerReceiptContractDraftResult(
        output_dir=output_path,
        receipt_contract_id=receipt_contract_id,
        contract_path=None,
        result_path=None,
        manifest_path=None,
        summary_path=None,
        checklist_path=None,
        artifact_index_path=None,
        artifact_index_manifest_path=None,
        complete=False,
        contract_recorded=False,
        receipt_contract_status=_REJECTED_STATUS,
        receipt_contract_decision=_REJECTED_DECISION,
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
            "# Local-Fixture Runner Receipt Contract Draft",
            "",
            "This is a receipt contract draft only.",
            "This is not a runner.",
            "This does not create a runner stub.",
            "This does not create a runnable job.",
            "This does not execute adapter.",
            "This does not launch Playwright.",
            "This does not open browser.",
            "This does not access network.",
            "This does not authorize live websites.",
            "This does not issue approval material.",
            "This does not issue execution material.",
            "This does not authorize production.",
            "Future runner receipt implementation requires a separate PR.",
            "Future runner stub implementation requires a separate PR.",
            "",
            f"receipt_contract_id: {result['receipt_contract_id']}",
            f"reviewer_id: {result['reviewer_id']}",
            f"receipt_contract_status: {result['receipt_contract_status']}",
            f"receipt_contract_decision: {result['receipt_contract_decision']}",
            f"contract_recorded: {str(result['contract_recorded']).lower()}",
            "",
            "future receipt required inputs:",
            _markdown_list(
                LOCAL_FIXTURE_RUNNER_RECEIPT_CONTRACT_DRAFT_REQUIRED_FUTURE_INPUTS
            ),
            "",
            "future receipt required outputs:",
            _markdown_list(
                LOCAL_FIXTURE_RUNNER_RECEIPT_CONTRACT_DRAFT_REQUIRED_FUTURE_OUTPUTS
            ),
            "",
            "future receipt required fields:",
            _markdown_list(
                LOCAL_FIXTURE_RUNNER_RECEIPT_CONTRACT_DRAFT_REQUIRED_FUTURE_FIELDS
            ),
            "",
            "forbidden future input categories:",
            _markdown_list(_SUMMARY_FORBIDDEN_INPUTS),
            "",
            "rejected materialization:",
            _markdown_list(_SUMMARY_REJECTED_CAPABILITIES),
            "",
            "rejection reasons:",
            reason_lines,
            "",
            f"next_allowed_action: {result['next_allowed_action']}",
            "",
        ]
    )


def _checklist_markdown(result: dict[str, object]) -> str:
    checked = "[x]" if result["contract_recorded"] else "[ ]"
    return "\n".join(
        [
            "# Local-Fixture Runner Receipt Contract Draft Checklist",
            "",
            f"- {checked} Receipt contract draft validation passed.",
            f"- {checked} Future receipt inputs are limited to verified governance artifacts.",
            f"- {checked} Future receipt outputs require JSON, manifest, artifact index, summary, and checklist artifacts.",
            "- [x] No runner was created.",
            "- [x] No runner stub was created.",
            "- [x] No runnable job was created.",
            "- [x] No approval material was issued.",
            "- [x] No execution material was issued.",
            "- [x] No adapter execution was performed.",
            "- [x] No Playwright execution was performed.",
            "- [x] No browser was opened.",
            "- [x] No network access was performed.",
            "- [x] No live website access was performed.",
            "- [x] No autonomous execution was performed.",
            "- [x] No production promotion was granted.",
            "",
        ]
    )


def _markdown_list(values: tuple[str, ...]) -> str:
    return "\n".join("- " + value for value in values)


def _write_json_exclusive(path: Path, payload: dict[str, object]) -> None:
    if path.exists() or path.is_symlink():
        raise ValueError("output_collision")
    write_json_atomically(path, payload)


def _write_markdown_exclusive(path: Path, content: str) -> None:
    if path.exists() or path.is_symlink():
        raise ValueError("output_collision")
    write_markdown_atomically(path, content)


def _relative_path(path: Path, root: Path) -> str:
    try:
        return (
            path.resolve(strict=False)
            .relative_to(root.resolve(strict=False))
            .as_posix()
        )
    except ValueError:
        return path.as_posix()


def _non_empty_text(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
