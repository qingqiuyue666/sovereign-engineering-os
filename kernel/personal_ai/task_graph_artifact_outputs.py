"""Graph-level artifact output binding for local task graph fixtures."""

from pathlib import Path
import json

from kernel.personal_ai.hash_utils import sha256_canonical_json, sha256_file
from kernel.personal_ai.io_utils import write_json_atomically

__all__ = [
    "TASK_GRAPH_ARTIFACT_OUTPUTS_FILE",
    "build_task_graph_artifact_outputs_manifest",
    "task_graph_artifact_outputs_projection_sha256",
    "write_task_graph_artifact_outputs_manifest",
]

TASK_GRAPH_ARTIFACT_OUTPUTS_FILE = "task_graph_artifact_outputs.json"

_MANIFEST_TYPE = "personal_ai_task_graph_artifact_outputs_v1"
_GRAPH_ARTIFACT_NODE_ID = "__task_graph__"
_GRAPH_ARTIFACT_ADAPTER_ID = "task_graph_fixture"
_GRAPH_ARTIFACT_CAPABILITY = "write_task_graph_artifact_outputs"
_LOCAL_ASSET_ADAPTER_ID = "local_asset_runtime"
_LOCAL_ASSET_CAPABILITY = "launch_local_asset_scan"
_LOCAL_ASSET_SMOKE_READINESS_CAPABILITY = "launch_local_asset_smoke_readiness"
_LOCAL_ASSET_HUMAN_SMOKE_CAPABILITY = "launch_local_asset_human_smoke_run"
_LOCAL_ASSET_BOUNDED_SMOKE_ITERATION_CAPABILITY = (
    "launch_local_asset_bounded_smoke_iteration"
)
_LOCAL_ASSET_SMOKE_REVIEW_PACKET_CAPABILITY = (
    "launch_local_asset_smoke_review_packet"
)
_LOCAL_ASSET_SMOKE_ITERATION_REVIEW_PACKET_CAPABILITY = (
    "launch_local_asset_smoke_iteration_review_packet"
)
_LOCAL_ASSET_SMOKE_PROMOTION_GATE_CAPABILITY = (
    "launch_local_asset_smoke_promotion_gate"
)
_LOCAL_ASSET_ITERATION_PROMOTION_GATE_CAPABILITY = (
    "launch_local_asset_iteration_promotion_gate"
)
_LOCAL_ASSET_BOUNDED_SMOKE_CYCLE_CONTRACT_CAPABILITY = (
    "launch_local_asset_bounded_smoke_cycle_contract"
)
_LOCAL_ASSET_BOUNDED_SMOKE_CYCLE_HUMAN_REVIEW_CAPABILITY = (
    "launch_local_asset_bounded_smoke_cycle_human_review"
)
_LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_ADMISSION_CAPABILITY = (
    "launch_local_asset_next_bounded_smoke_iteration_admission"
)
_LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_EXECUTION_REQUEST_CAPABILITY = (
    "launch_local_asset_next_bounded_smoke_iteration_execution_request"
)
_LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUNNER_ADMISSION_CAPABILITY = (
    "launch_local_asset_next_bounded_smoke_iteration_runner_admission"
)
_LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUNNER_CAPABILITY = (
    "launch_local_asset_next_bounded_smoke_iteration_runner"
)
_LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUN_REVIEW_PACKET_CAPABILITY = (
    "launch_local_asset_next_bounded_smoke_iteration_run_review_packet"
)
_LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUN_PROMOTION_GATE_CAPABILITY = (
    "launch_local_asset_next_bounded_smoke_iteration_run_promotion_gate"
)
_LOCAL_ASSET_NEXT_BOUNDED_SMOKE_CYCLE_CONTRACT_FROM_RUN_PROMOTION_GATE_CAPABILITY = (
    "launch_local_asset_next_bounded_smoke_cycle_contract_from_run_promotion_gate"
)
_LOCAL_ASSET_NEXT_BOUNDED_SMOKE_CYCLE_CONTRACT_HUMAN_REVIEW_FROM_RUN_PROMOTION_GATE_CAPABILITY = (
    "launch_local_asset_next_bounded_smoke_cycle_contract_human_review_from_run_promotion_gate"
)
_GITHUB_CAPABILITY_ADAPTER_ID = "github_capability_intake_packet"
_GITHUB_CAPABILITY_INTAKE_PACKET_CAPABILITY = (
    "launch_github_capability_intake_packet"
)
_PLAYWRIGHT_SMOKE_ADAPTER_ID = "playwright_local_fixture_sandbox_smoke"
_PLAYWRIGHT_SMOKE_CAPABILITY = "launch_playwright_local_fixture_sandbox_smoke"
_BOUNDED_PLAYWRIGHT_ADAPTER_DRAFT_ID = "bounded_playwright_worker_adapter_draft"
_BOUNDED_PLAYWRIGHT_ADAPTER_DRAFT_CAPABILITY = (
    "launch_bounded_playwright_worker_adapter_draft"
)
_OPERATOR_PLAYWRIGHT_RECEIPT_ADAPTER_ID = (
    "operator_provided_playwright_execution_receipt"
)
_OPERATOR_PLAYWRIGHT_RECEIPT_CAPABILITY = (
    "launch_operator_provided_playwright_execution_receipt"
)
_LOCAL_FIXTURE_PLAYWRIGHT_ADMISSION_GATE_ADAPTER_ID = (
    "local_fixture_playwright_adapter_admission_gate"
)
_LOCAL_FIXTURE_PLAYWRIGHT_ADMISSION_GATE_CAPABILITY = (
    "launch_local_fixture_playwright_adapter_admission_gate"
)
_LOCAL_ONLY_PLAYWRIGHT_FIXTURE_SCENARIO_SUITE_ADAPTER_ID = (
    "local_only_playwright_fixture_scenario_suite"
)
_LOCAL_ONLY_PLAYWRIGHT_FIXTURE_SCENARIO_SUITE_CAPABILITY = (
    "launch_local_only_playwright_fixture_scenario_suite"
)
_PLAYWRIGHT_LOCAL_ADMISSION_RECEIPT_AGGREGATION_ADAPTER_ID = (
    "playwright_local_admission_receipt_aggregation"
)
_PLAYWRIGHT_LOCAL_ADMISSION_RECEIPT_AGGREGATION_CAPABILITY = (
    "launch_playwright_local_admission_receipt_aggregation"
)
_ADMISSION_GATED_LOCAL_ADAPTER_REGISTRY_PROMOTION_ADAPTER_ID = (
    "admission_gated_local_adapter_registry_promotion"
)
_ADMISSION_GATED_LOCAL_ADAPTER_REGISTRY_PROMOTION_CAPABILITY = (
    "launch_admission_gated_local_adapter_registry_promotion"
)
_LOCAL_FIXTURE_ADAPTER_USAGE_RECEIPT_ADAPTER_ID = (
    "local_fixture_adapter_usage_receipt"
)
_LOCAL_FIXTURE_ADAPTER_USAGE_RECEIPT_CAPABILITY = (
    "launch_local_fixture_adapter_usage_receipt"
)
_LOCAL_FIXTURE_ADAPTER_DRY_RUN_INVOCATION_PLAN_ADAPTER_ID = (
    "local_fixture_adapter_dry_run_invocation_plan"
)
_LOCAL_FIXTURE_ADAPTER_DRY_RUN_INVOCATION_PLAN_CAPABILITY = (
    "launch_local_fixture_adapter_dry_run_invocation_plan"
)
_LOCAL_FIXTURE_ADAPTER_EXECUTION_GATE_PLAN_ADAPTER_ID = (
    "local_fixture_adapter_execution_gate_plan"
)
_LOCAL_FIXTURE_ADAPTER_EXECUTION_GATE_PLAN_CAPABILITY = (
    "launch_local_fixture_adapter_execution_gate_plan"
)
_LOCAL_FIXTURE_HUMAN_APPROVAL_ARTIFACT_ADAPTER_ID = (
    "local_fixture_human_approval_artifact"
)
_LOCAL_FIXTURE_HUMAN_APPROVAL_ARTIFACT_CAPABILITY = (
    "launch_local_fixture_human_approval_artifact"
)
_LOCAL_FIXTURE_RUNNER_CONTRACT_DRAFT_ADAPTER_ID = (
    "local_fixture_runner_contract_draft"
)
_LOCAL_FIXTURE_RUNNER_CONTRACT_DRAFT_CAPABILITY = (
    "launch_local_fixture_runner_contract_draft"
)
_LOCAL_FIXTURE_RUNNER_STUB_ADMISSION_GATE_ADAPTER_ID = (
    "local_fixture_runner_stub_admission_gate"
)
_LOCAL_FIXTURE_RUNNER_STUB_ADMISSION_GATE_CAPABILITY = (
    "launch_local_fixture_runner_stub_admission_gate"
)
_LOCAL_FIXTURE_RUNNER_RECEIPT_CONTRACT_DRAFT_ADAPTER_ID = (
    "local_fixture_runner_receipt_contract_draft"
)
_LOCAL_FIXTURE_RUNNER_RECEIPT_CONTRACT_DRAFT_CAPABILITY = (
    "launch_local_fixture_runner_receipt_contract_draft"
)
_LOCAL_FIXTURE_RUNNER_RECEIPT_PREFLIGHT_VERIFIER_ADAPTER_ID = (
    "local_fixture_runner_receipt_preflight_verifier"
)
_LOCAL_FIXTURE_RUNNER_RECEIPT_PREFLIGHT_VERIFIER_CAPABILITY = (
    "launch_local_fixture_runner_receipt_preflight_verifier"
)
_LOCAL_FIXTURE_RUNNER_RECEIPT_METADATA_ARTIFACT_ADAPTER_ID = (
    "local_fixture_runner_receipt_metadata_artifact"
)
_LOCAL_FIXTURE_RUNNER_RECEIPT_METADATA_ARTIFACT_CAPABILITY = (
    "launch_local_fixture_runner_receipt_metadata_artifact"
)
_DELIVERY_ADAPTER_ID = "runtime_delivery_package"
_DELIVERY_CAPABILITY = "validate_runtime_delivery"

_LOCAL_ASSET_DIRECT_PATH_FIELDS = (
    ("asset_scan_run_receipt", "asset_scan_run_receipt_path"),
    ("asset_scan_failure_bundle", "asset_scan_failure_bundle_path"),
    ("asset_scan_failure_summary", "asset_scan_failure_summary_path"),
    ("artifact_index", "artifact_index_path"),
    ("artifact_index_manifest", "artifact_index_manifest_path"),
    ("local_asset_sqlite_index", "local_asset_sqlite_index_path"),
    (
        "local_asset_sqlite_index_manifest",
        "local_asset_sqlite_index_manifest_path",
    ),
    ("local_asset_sqlite_query_summary", "local_asset_sqlite_query_summary_path"),
    (
        "local_asset_incremental_scan_plan",
        "local_asset_incremental_scan_plan_path",
    ),
    (
        "local_asset_incremental_scan_manifest",
        "local_asset_incremental_scan_manifest_path",
    ),
    (
        "local_asset_incremental_scan_summary",
        "local_asset_incremental_scan_summary_path",
    ),
    ("asset_manifest", "asset_manifest_path"),
    ("asset_index", "asset_index_path"),
    ("duplicates_report", "duplicates_report_path"),
    ("media_inventory", "media_inventory_path"),
    ("asset_runtime_audit_log", "asset_runtime_audit_log_path"),
    ("asset_runtime_validation_report", "asset_runtime_validation_report_path"),
    ("asset_runtime_quarantine_manifest", "asset_runtime_quarantine_manifest_path"),
    ("launcher_summary", "launcher_summary_path"),
)

_LOCAL_ASSET_OUTPUT_FILE_ROLES = {
    "asset_manifest.json": "asset_manifest",
    "asset_index.json": "asset_index",
    "duplicates_report.json": "duplicates_report",
    "media_inventory.md": "media_inventory",
    "asset_runtime_audit_log.jsonl": "asset_runtime_audit_log",
    "asset_runtime_validation_report.json": "asset_runtime_validation_report",
    "asset_runtime_quarantine_manifest.json": "asset_runtime_quarantine_manifest",
}

_LOCAL_ASSET_SMOKE_READINESS_DIRECT_PATH_FIELDS = (
    (
        "local_asset_smoke_readiness_report",
        "local_asset_smoke_readiness_report_path",
    ),
    (
        "local_asset_smoke_readiness_manifest",
        "local_asset_smoke_readiness_manifest_path",
    ),
    (
        "local_asset_smoke_readiness_summary",
        "local_asset_smoke_readiness_summary_path",
    ),
    ("artifact_index", "artifact_index_path"),
    ("artifact_index_manifest", "artifact_index_manifest_path"),
    ("launcher_summary", "launcher_summary_path"),
)

_LOCAL_ASSET_HUMAN_SMOKE_DIRECT_PATH_FIELDS = (
    (
        "local_asset_human_smoke_approval",
        "local_asset_human_smoke_approval_path",
    ),
    (
        "local_asset_human_smoke_admission_receipt",
        "local_asset_human_smoke_admission_receipt_path",
    ),
    (
        "local_asset_human_smoke_run_summary",
        "local_asset_human_smoke_run_summary_path",
    ),
    (
        "local_asset_human_smoke_scan_artifact_index",
        "scan_artifact_index_path",
    ),
    (
        "local_asset_human_smoke_scan_artifact_index_manifest",
        "scan_artifact_index_manifest_path",
    ),
    ("artifact_index", "artifact_index_path"),
    ("artifact_index_manifest", "artifact_index_manifest_path"),
)

_LOCAL_ASSET_BOUNDED_SMOKE_ITERATION_DIRECT_PATH_FIELDS = (
    (
        "local_asset_bounded_smoke_iteration_result",
        "local_asset_bounded_smoke_iteration_result_path",
    ),
    (
        "local_asset_bounded_smoke_iteration_manifest",
        "local_asset_bounded_smoke_iteration_manifest_path",
    ),
    (
        "local_asset_bounded_smoke_iteration_summary",
        "local_asset_bounded_smoke_iteration_summary_path",
    ),
    (
        "local_asset_bounded_smoke_iteration_human_review_checklist",
        "local_asset_bounded_smoke_iteration_human_review_checklist_path",
    ),
    (
        "local_asset_bounded_smoke_iteration_signoff",
        "local_asset_bounded_smoke_iteration_signoff_path",
    ),
    (
        "local_asset_bounded_smoke_iteration_admission",
        "local_asset_bounded_smoke_iteration_admission_path",
    ),
    ("artifact_index", "artifact_index_path"),
    ("artifact_index_manifest", "artifact_index_manifest_path"),
)

_LOCAL_ASSET_SMOKE_REVIEW_PACKET_DIRECT_PATH_FIELDS = (
    (
        "local_asset_smoke_review_packet",
        "local_asset_smoke_review_packet_path",
    ),
    (
        "local_asset_smoke_review_packet_manifest",
        "local_asset_smoke_review_packet_manifest_path",
    ),
    (
        "local_asset_smoke_review_summary",
        "local_asset_smoke_review_summary_path",
    ),
    (
        "local_asset_smoke_human_decision_checklist",
        "local_asset_smoke_human_decision_checklist_path",
    ),
    ("artifact_index", "artifact_index_path"),
    ("artifact_index_manifest", "artifact_index_manifest_path"),
)

_LOCAL_ASSET_SMOKE_ITERATION_REVIEW_PACKET_DIRECT_PATH_FIELDS = (
    (
        "local_asset_smoke_iteration_review_packet",
        "local_asset_smoke_iteration_review_packet_path",
    ),
    (
        "local_asset_smoke_iteration_review_packet_manifest",
        "local_asset_smoke_iteration_review_packet_manifest_path",
    ),
    (
        "local_asset_smoke_iteration_review_summary",
        "local_asset_smoke_iteration_review_summary_path",
    ),
    (
        "local_asset_smoke_iteration_human_decision_checklist",
        "local_asset_smoke_iteration_human_decision_checklist_path",
    ),
    ("artifact_index", "artifact_index_path"),
    ("artifact_index_manifest", "artifact_index_manifest_path"),
)

_LOCAL_ASSET_SMOKE_PROMOTION_GATE_DIRECT_PATH_FIELDS = (
    (
        "local_asset_smoke_promotion_decision",
        "local_asset_smoke_promotion_decision_path",
    ),
    (
        "local_asset_smoke_promotion_gate_manifest",
        "local_asset_smoke_promotion_gate_manifest_path",
    ),
    (
        "local_asset_smoke_promotion_summary",
        "local_asset_smoke_promotion_summary_path",
    ),
    (
        "local_asset_smoke_promotion_human_signoff_checklist",
        "local_asset_smoke_promotion_human_signoff_checklist_path",
    ),
    ("artifact_index", "artifact_index_path"),
    ("artifact_index_manifest", "artifact_index_manifest_path"),
)

_LOCAL_ASSET_ITERATION_PROMOTION_GATE_DIRECT_PATH_FIELDS = (
    (
        "local_asset_iteration_promotion_decision",
        "local_asset_iteration_promotion_decision_path",
    ),
    (
        "local_asset_iteration_promotion_gate_manifest",
        "local_asset_iteration_promotion_gate_manifest_path",
    ),
    (
        "local_asset_iteration_promotion_summary",
        "local_asset_iteration_promotion_summary_path",
    ),
    (
        "local_asset_iteration_promotion_human_signoff_checklist",
        "local_asset_iteration_promotion_human_signoff_checklist_path",
    ),
    ("artifact_index", "artifact_index_path"),
    ("artifact_index_manifest", "artifact_index_manifest_path"),
)

_LOCAL_ASSET_BOUNDED_SMOKE_CYCLE_CONTRACT_DIRECT_PATH_FIELDS = (
    (
        "local_asset_bounded_smoke_cycle_contract",
        "local_asset_bounded_smoke_cycle_contract_path",
    ),
    (
        "local_asset_bounded_smoke_cycle_contract_manifest",
        "local_asset_bounded_smoke_cycle_contract_manifest_path",
    ),
    (
        "local_asset_bounded_smoke_cycle_summary",
        "local_asset_bounded_smoke_cycle_summary_path",
    ),
    (
        "local_asset_bounded_smoke_cycle_human_review_checklist",
        "local_asset_bounded_smoke_cycle_human_review_checklist_path",
    ),
    ("artifact_index", "artifact_index_path"),
    ("artifact_index_manifest", "artifact_index_manifest_path"),
)

_LOCAL_ASSET_BOUNDED_SMOKE_CYCLE_HUMAN_REVIEW_DIRECT_PATH_FIELDS = (
    (
        "local_asset_bounded_smoke_cycle_human_review_decision",
        "local_asset_bounded_smoke_cycle_human_review_decision_path",
    ),
    (
        "local_asset_bounded_smoke_cycle_human_review_manifest",
        "local_asset_bounded_smoke_cycle_human_review_manifest_path",
    ),
    (
        "local_asset_bounded_smoke_cycle_human_review_summary",
        "local_asset_bounded_smoke_cycle_human_review_summary_path",
    ),
    (
        "local_asset_bounded_smoke_cycle_human_review_checklist",
        "local_asset_bounded_smoke_cycle_human_review_checklist_path",
    ),
    ("artifact_index", "artifact_index_path"),
    ("artifact_index_manifest", "artifact_index_manifest_path"),
)

_LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_ADMISSION_DIRECT_PATH_FIELDS = (
    (
        "local_asset_next_bounded_smoke_iteration_admission",
        "local_asset_next_bounded_smoke_iteration_admission_path",
    ),
    (
        "local_asset_next_bounded_smoke_iteration_admission_manifest",
        "local_asset_next_bounded_smoke_iteration_admission_manifest_path",
    ),
    (
        "local_asset_next_bounded_smoke_iteration_admission_summary",
        "local_asset_next_bounded_smoke_iteration_admission_summary_path",
    ),
    (
        "local_asset_next_bounded_smoke_iteration_admission_checklist",
        "local_asset_next_bounded_smoke_iteration_admission_checklist_path",
    ),
    ("artifact_index", "artifact_index_path"),
    ("artifact_index_manifest", "artifact_index_manifest_path"),
)

_LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_EXECUTION_REQUEST_DIRECT_PATH_FIELDS = (
    (
        "local_asset_next_bounded_smoke_iteration_execution_request",
        "local_asset_next_bounded_smoke_iteration_execution_request_path",
    ),
    (
        "local_asset_next_bounded_smoke_iteration_execution_request_manifest",
        "local_asset_next_bounded_smoke_iteration_execution_request_manifest_path",
    ),
    (
        "local_asset_next_bounded_smoke_iteration_execution_request_summary",
        "local_asset_next_bounded_smoke_iteration_execution_request_summary_path",
    ),
    (
        "local_asset_next_bounded_smoke_iteration_execution_request_checklist",
        "local_asset_next_bounded_smoke_iteration_execution_request_checklist_path",
    ),
    ("artifact_index", "artifact_index_path"),
    ("artifact_index_manifest", "artifact_index_manifest_path"),
)

_LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUNNER_ADMISSION_DIRECT_PATH_FIELDS = (
    (
        "local_asset_next_bounded_smoke_iteration_runner_admission",
        "local_asset_next_bounded_smoke_iteration_runner_admission_path",
    ),
    (
        "local_asset_next_bounded_smoke_iteration_runner_admission_manifest",
        "local_asset_next_bounded_smoke_iteration_runner_admission_manifest_path",
    ),
    (
        "local_asset_next_bounded_smoke_iteration_runner_admission_summary",
        "local_asset_next_bounded_smoke_iteration_runner_admission_summary_path",
    ),
    (
        "local_asset_next_bounded_smoke_iteration_runner_admission_checklist",
        "local_asset_next_bounded_smoke_iteration_runner_admission_checklist_path",
    ),
    ("artifact_index", "artifact_index_path"),
    ("artifact_index_manifest", "artifact_index_manifest_path"),
)

_LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUNNER_DIRECT_PATH_FIELDS = (
    (
        "local_asset_next_bounded_smoke_iteration_runner",
        "local_asset_next_bounded_smoke_iteration_runner_path",
    ),
    (
        "local_asset_next_bounded_smoke_iteration_runner_manifest",
        "local_asset_next_bounded_smoke_iteration_runner_manifest_path",
    ),
    (
        "local_asset_next_bounded_smoke_iteration_runner_summary",
        "local_asset_next_bounded_smoke_iteration_runner_summary_path",
    ),
    (
        "local_asset_next_bounded_smoke_iteration_runner_checklist",
        "local_asset_next_bounded_smoke_iteration_runner_checklist_path",
    ),
    ("artifact_index", "artifact_index_path"),
    ("artifact_index_manifest", "artifact_index_manifest_path"),
)

_LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUN_REVIEW_PACKET_DIRECT_PATH_FIELDS = (
    (
        "local_asset_next_bounded_smoke_iteration_run_review_packet",
        "local_asset_next_bounded_smoke_iteration_run_review_packet_path",
    ),
    (
        "local_asset_next_bounded_smoke_iteration_run_review_packet_manifest",
        "local_asset_next_bounded_smoke_iteration_run_review_packet_manifest_path",
    ),
    (
        "local_asset_next_bounded_smoke_iteration_run_review_packet_summary",
        "local_asset_next_bounded_smoke_iteration_run_review_packet_summary_path",
    ),
    (
        "local_asset_next_bounded_smoke_iteration_run_review_packet_checklist",
        "local_asset_next_bounded_smoke_iteration_run_review_packet_checklist_path",
    ),
    ("artifact_index", "artifact_index_path"),
    ("artifact_index_manifest", "artifact_index_manifest_path"),
)

_LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUN_PROMOTION_GATE_DIRECT_PATH_FIELDS = (
    (
        "local_asset_next_bounded_smoke_iteration_run_promotion_gate",
        "local_asset_next_bounded_smoke_iteration_run_promotion_gate_path",
    ),
    (
        "local_asset_next_bounded_smoke_iteration_run_promotion_gate_manifest",
        "local_asset_next_bounded_smoke_iteration_run_promotion_gate_manifest_path",
    ),
    (
        "local_asset_next_bounded_smoke_iteration_run_promotion_gate_summary",
        "local_asset_next_bounded_smoke_iteration_run_promotion_gate_summary_path",
    ),
    (
        "local_asset_next_bounded_smoke_iteration_run_promotion_gate_checklist",
        "local_asset_next_bounded_smoke_iteration_run_promotion_gate_checklist_path",
    ),
    ("artifact_index", "artifact_index_path"),
    ("artifact_index_manifest", "artifact_index_manifest_path"),
)

_LOCAL_ASSET_NEXT_BOUNDED_SMOKE_CYCLE_CONTRACT_FROM_RUN_PROMOTION_GATE_DIRECT_PATH_FIELDS = (
    (
        "local_asset_next_bounded_smoke_cycle_contract_from_run_promotion_gate",
        "local_asset_next_bounded_smoke_cycle_contract_from_run_promotion_gate_path",
    ),
    (
        "local_asset_next_bounded_smoke_cycle_contract_from_run_promotion_gate_manifest",
        "local_asset_next_bounded_smoke_cycle_contract_from_run_promotion_gate_manifest_path",
    ),
    (
        "local_asset_next_bounded_smoke_cycle_contract_from_run_promotion_gate_summary",
        "local_asset_next_bounded_smoke_cycle_contract_from_run_promotion_gate_summary_path",
    ),
    (
        "local_asset_next_bounded_smoke_cycle_contract_from_run_promotion_gate_checklist",
        "local_asset_next_bounded_smoke_cycle_contract_from_run_promotion_gate_checklist_path",
    ),
    ("artifact_index", "artifact_index_path"),
    ("artifact_index_manifest", "artifact_index_manifest_path"),
)

_LOCAL_ASSET_NEXT_BOUNDED_SMOKE_CYCLE_CONTRACT_HUMAN_REVIEW_FROM_RUN_PROMOTION_GATE_DIRECT_PATH_FIELDS = (
    (
        "local_asset_next_bounded_smoke_cycle_contract_human_review_from_run_promotion_gate",
        "local_asset_next_bounded_smoke_cycle_contract_human_review_from_run_promotion_gate_path",
    ),
    (
        "local_asset_next_bounded_smoke_cycle_contract_human_review_from_run_promotion_gate_manifest",
        "local_asset_next_bounded_smoke_cycle_contract_human_review_from_run_promotion_gate_manifest_path",
    ),
    (
        "local_asset_next_bounded_smoke_cycle_contract_human_review_from_run_promotion_gate_summary",
        "local_asset_next_bounded_smoke_cycle_contract_human_review_from_run_promotion_gate_summary_path",
    ),
    (
        "local_asset_next_bounded_smoke_cycle_contract_human_review_from_run_promotion_gate_checklist",
        "local_asset_next_bounded_smoke_cycle_contract_human_review_from_run_promotion_gate_checklist_path",
    ),
    ("artifact_index", "artifact_index_path"),
    ("artifact_index_manifest", "artifact_index_manifest_path"),
)

_GITHUB_CAPABILITY_INTAKE_PACKET_DIRECT_PATH_FIELDS = (
    (
        "github_capability_intake_packet",
        "github_capability_intake_packet_path",
    ),
    (
        "github_capability_intake_packet_manifest",
        "github_capability_intake_packet_manifest_path",
    ),
    (
        "github_capability_intake_packet_summary",
        "github_capability_intake_packet_summary_path",
    ),
    (
        "github_capability_intake_packet_checklist",
        "github_capability_intake_packet_checklist_path",
    ),
    ("artifact_index", "artifact_index_path"),
    ("artifact_index_manifest", "artifact_index_manifest_path"),
)

_PLAYWRIGHT_SMOKE_DIRECT_PATH_FIELDS = (
    (
        "playwright_local_fixture_sandbox_smoke_plan",
        "playwright_local_fixture_sandbox_smoke_plan_path",
    ),
    (
        "playwright_local_fixture_sandbox_smoke_manifest",
        "playwright_local_fixture_sandbox_smoke_manifest_path",
    ),
    (
        "playwright_local_fixture_sandbox_smoke_summary",
        "playwright_local_fixture_sandbox_smoke_summary_path",
    ),
    (
        "playwright_local_fixture_sandbox_smoke_checklist",
        "playwright_local_fixture_sandbox_smoke_checklist_path",
    ),
    (
        "playwright_local_fixture_sandbox_smoke_result",
        "playwright_local_fixture_sandbox_smoke_result_path",
    ),
    (
        "playwright_local_fixture_sandbox_smoke_runner_output",
        "playwright_local_fixture_sandbox_smoke_runner_output_path",
    ),
    (
        "playwright_local_fixture_sandbox_smoke_screenshot",
        "playwright_local_fixture_sandbox_smoke_screenshot_path",
    ),
    ("playwright_local_fixture_index_html", "fixture_index_path"),
    ("playwright_local_fixture_app_js", "fixture_app_js_path"),
    ("playwright_local_fixture_style_css", "fixture_style_css_path"),
    ("artifact_index", "artifact_index_path"),
    ("artifact_index_manifest", "artifact_index_manifest_path"),
)

_BOUNDED_PLAYWRIGHT_ADAPTER_DRAFT_DIRECT_PATH_FIELDS = (
    (
        "bounded_playwright_worker_adapter_draft_plan",
        "bounded_playwright_worker_adapter_draft_plan_path",
    ),
    (
        "bounded_playwright_worker_adapter_draft_manifest",
        "bounded_playwright_worker_adapter_draft_manifest_path",
    ),
    (
        "bounded_playwright_worker_adapter_draft_summary",
        "bounded_playwright_worker_adapter_draft_summary_path",
    ),
    (
        "bounded_playwright_worker_adapter_draft_checklist",
        "bounded_playwright_worker_adapter_draft_checklist_path",
    ),
    (
        "bounded_playwright_worker_adapter_draft_result",
        "bounded_playwright_worker_adapter_draft_result_path",
    ),
    (
        "embedded_playwright_local_fixture_sandbox_smoke_plan",
        "embedded_smoke_plan_path",
    ),
    (
        "embedded_playwright_local_fixture_sandbox_smoke_manifest",
        "embedded_smoke_manifest_path",
    ),
    (
        "embedded_playwright_local_fixture_sandbox_smoke_summary",
        "embedded_smoke_summary_path",
    ),
    (
        "embedded_playwright_local_fixture_sandbox_smoke_checklist",
        "embedded_smoke_checklist_path",
    ),
    (
        "embedded_playwright_local_fixture_sandbox_smoke_result",
        "embedded_smoke_result_path",
    ),
    (
        "embedded_playwright_local_fixture_sandbox_smoke_runner_output",
        "embedded_smoke_runner_output_path",
    ),
    (
        "embedded_playwright_local_fixture_sandbox_smoke_screenshot",
        "embedded_smoke_screenshot_path",
    ),
    ("embedded_fixture_index_html", "embedded_fixture_index_path"),
    ("embedded_fixture_app_js", "embedded_fixture_app_js_path"),
    ("embedded_fixture_style_css", "embedded_fixture_style_css_path"),
    ("artifact_index", "artifact_index_path"),
    ("artifact_index_manifest", "artifact_index_manifest_path"),
)

_OPERATOR_PLAYWRIGHT_RECEIPT_DIRECT_PATH_FIELDS = (
    (
        "operator_provided_playwright_execution_receipt_plan",
        "operator_provided_playwright_execution_receipt_plan_path",
    ),
    (
        "operator_provided_playwright_execution_receipt_manifest",
        "operator_provided_playwright_execution_receipt_manifest_path",
    ),
    (
        "operator_provided_playwright_execution_receipt_summary",
        "operator_provided_playwright_execution_receipt_summary_path",
    ),
    (
        "operator_provided_playwright_execution_receipt_checklist",
        "operator_provided_playwright_execution_receipt_checklist_path",
    ),
    (
        "operator_provided_playwright_execution_receipt_result",
        "operator_provided_playwright_execution_receipt_result_path",
    ),
    ("bounded_playwright_worker_adapter_draft_plan", "adapter_draft_plan_path"),
    (
        "bounded_playwright_worker_adapter_draft_manifest",
        "adapter_draft_manifest_path",
    ),
    ("bounded_playwright_worker_adapter_draft_summary", "adapter_draft_summary_path"),
    (
        "bounded_playwright_worker_adapter_draft_checklist",
        "adapter_draft_checklist_path",
    ),
    ("bounded_playwright_worker_adapter_draft_result", "adapter_draft_result_path"),
    (
        "embedded_playwright_local_fixture_sandbox_smoke_plan",
        "embedded_smoke_plan_path",
    ),
    (
        "embedded_playwright_local_fixture_sandbox_smoke_manifest",
        "embedded_smoke_manifest_path",
    ),
    (
        "embedded_playwright_local_fixture_sandbox_smoke_summary",
        "embedded_smoke_summary_path",
    ),
    (
        "embedded_playwright_local_fixture_sandbox_smoke_checklist",
        "embedded_smoke_checklist_path",
    ),
    (
        "embedded_playwright_local_fixture_sandbox_smoke_result",
        "embedded_smoke_result_path",
    ),
    (
        "embedded_playwright_local_fixture_sandbox_smoke_runner_output",
        "embedded_smoke_runner_output_path",
    ),
    (
        "embedded_playwright_local_fixture_sandbox_smoke_screenshot",
        "embedded_smoke_screenshot_path",
    ),
    ("embedded_fixture_index_html", "embedded_fixture_index_path"),
    ("embedded_fixture_app_js", "embedded_fixture_app_js_path"),
    ("embedded_fixture_style_css", "embedded_fixture_style_css_path"),
    ("artifact_index", "artifact_index_path"),
    ("artifact_index_manifest", "artifact_index_manifest_path"),
)

_LOCAL_FIXTURE_PLAYWRIGHT_ADMISSION_GATE_DIRECT_PATH_FIELDS = (
    (
        "local_fixture_playwright_adapter_admission_gate_plan",
        "local_fixture_playwright_adapter_admission_gate_plan_path",
    ),
    (
        "local_fixture_playwright_adapter_admission_gate_manifest",
        "local_fixture_playwright_adapter_admission_gate_manifest_path",
    ),
    (
        "local_fixture_playwright_adapter_admission_gate_summary",
        "local_fixture_playwright_adapter_admission_gate_summary_path",
    ),
    (
        "local_fixture_playwright_adapter_admission_gate_checklist",
        "local_fixture_playwright_adapter_admission_gate_checklist_path",
    ),
    (
        "local_fixture_playwright_adapter_admission_gate_decision",
        "local_fixture_playwright_adapter_admission_gate_decision_path",
    ),
    ("artifact_index", "artifact_index_path"),
    ("artifact_index_manifest", "artifact_index_manifest_path"),
)

_LOCAL_ONLY_PLAYWRIGHT_FIXTURE_SCENARIO_SUITE_DIRECT_PATH_FIELDS = (
    (
        "local_only_playwright_fixture_scenario_suite_plan",
        "local_only_playwright_fixture_scenario_suite_plan_path",
    ),
    (
        "local_only_playwright_fixture_scenario_suite_manifest",
        "local_only_playwright_fixture_scenario_suite_manifest_path",
    ),
    (
        "local_only_playwright_fixture_scenario_suite_summary",
        "local_only_playwright_fixture_scenario_suite_summary_path",
    ),
    (
        "local_only_playwright_fixture_scenario_suite_checklist",
        "local_only_playwright_fixture_scenario_suite_checklist_path",
    ),
    (
        "local_only_playwright_fixture_scenario_suite_result",
        "local_only_playwright_fixture_scenario_suite_result_path",
    ),
    ("artifact_index", "artifact_index_path"),
    ("artifact_index_manifest", "artifact_index_manifest_path"),
)

_PLAYWRIGHT_LOCAL_ADMISSION_RECEIPT_AGGREGATION_DIRECT_PATH_FIELDS = (
    (
        "playwright_local_admission_receipt_aggregation_plan",
        "playwright_local_admission_receipt_aggregation_plan_path",
    ),
    (
        "playwright_local_admission_receipt_aggregation_manifest",
        "playwright_local_admission_receipt_aggregation_manifest_path",
    ),
    (
        "playwright_local_admission_receipt_aggregation_summary",
        "playwright_local_admission_receipt_aggregation_summary_path",
    ),
    (
        "playwright_local_admission_receipt_aggregation_checklist",
        "playwright_local_admission_receipt_aggregation_checklist_path",
    ),
    (
        "playwright_local_admission_receipt_aggregation_result",
        "playwright_local_admission_receipt_aggregation_result_path",
    ),
    ("artifact_index", "artifact_index_path"),
    ("artifact_index_manifest", "artifact_index_manifest_path"),
)

_ADMISSION_GATED_LOCAL_ADAPTER_REGISTRY_PROMOTION_DIRECT_PATH_FIELDS = (
    (
        "admission_gated_local_adapter_registry_promotion_plan",
        "admission_gated_local_adapter_registry_promotion_plan_path",
    ),
    (
        "admission_gated_local_adapter_registry_promotion_result",
        "admission_gated_local_adapter_registry_promotion_result_path",
    ),
    (
        "admission_gated_local_adapter_registry_promotion_manifest",
        "admission_gated_local_adapter_registry_promotion_manifest_path",
    ),
    (
        "admission_gated_local_adapter_registry_promotion_summary",
        "admission_gated_local_adapter_registry_promotion_summary_path",
    ),
    (
        "admission_gated_local_adapter_registry_promotion_checklist",
        "admission_gated_local_adapter_registry_promotion_checklist_path",
    ),
    ("local_fixture_only_adapter_registry_entry", "registry_output_path"),
    ("artifact_index", "artifact_index_path"),
    ("artifact_index_manifest", "artifact_index_manifest_path"),
)

_LOCAL_FIXTURE_ADAPTER_USAGE_RECEIPT_DIRECT_PATH_FIELDS = (
    (
        "local_fixture_adapter_usage_receipt_plan",
        "local_fixture_adapter_usage_receipt_plan_path",
    ),
    (
        "local_fixture_adapter_usage_receipt_result",
        "local_fixture_adapter_usage_receipt_result_path",
    ),
    (
        "local_fixture_adapter_usage_receipt_manifest",
        "local_fixture_adapter_usage_receipt_manifest_path",
    ),
    (
        "local_fixture_adapter_usage_receipt_summary",
        "local_fixture_adapter_usage_receipt_summary_path",
    ),
    (
        "local_fixture_adapter_usage_receipt_checklist",
        "local_fixture_adapter_usage_receipt_checklist_path",
    ),
    ("artifact_index", "artifact_index_path"),
    ("artifact_index_manifest", "artifact_index_manifest_path"),
)

_LOCAL_FIXTURE_ADAPTER_DRY_RUN_INVOCATION_PLAN_DIRECT_PATH_FIELDS = (
    (
        "local_fixture_adapter_dry_run_invocation_plan_plan",
        "local_fixture_adapter_dry_run_invocation_plan_plan_path",
    ),
    (
        "local_fixture_adapter_dry_run_invocation_plan_result",
        "local_fixture_adapter_dry_run_invocation_plan_result_path",
    ),
    (
        "local_fixture_adapter_dry_run_invocation_plan_manifest",
        "local_fixture_adapter_dry_run_invocation_plan_manifest_path",
    ),
    (
        "local_fixture_adapter_dry_run_invocation_plan_summary",
        "local_fixture_adapter_dry_run_invocation_plan_summary_path",
    ),
    (
        "local_fixture_adapter_dry_run_invocation_plan_checklist",
        "local_fixture_adapter_dry_run_invocation_plan_checklist_path",
    ),
    ("artifact_index", "artifact_index_path"),
    ("artifact_index_manifest", "artifact_index_manifest_path"),
)

_LOCAL_FIXTURE_ADAPTER_EXECUTION_GATE_PLAN_DIRECT_PATH_FIELDS = (
    (
        "local_fixture_adapter_execution_gate_plan_plan",
        "local_fixture_adapter_execution_gate_plan_plan_path",
    ),
    (
        "local_fixture_adapter_execution_gate_plan_result",
        "local_fixture_adapter_execution_gate_plan_result_path",
    ),
    (
        "local_fixture_adapter_execution_gate_plan_manifest",
        "local_fixture_adapter_execution_gate_plan_manifest_path",
    ),
    (
        "local_fixture_adapter_execution_gate_plan_human_approval_request",
        "local_fixture_adapter_execution_gate_plan_human_approval_request_path",
    ),
    (
        "local_fixture_adapter_execution_gate_plan_summary",
        "local_fixture_adapter_execution_gate_plan_summary_path",
    ),
    (
        "local_fixture_adapter_execution_gate_plan_checklist",
        "local_fixture_adapter_execution_gate_plan_checklist_path",
    ),
    ("artifact_index", "artifact_index_path"),
    ("artifact_index_manifest", "artifact_index_manifest_path"),
)

_LOCAL_FIXTURE_HUMAN_APPROVAL_ARTIFACT_DIRECT_PATH_FIELDS = (
    (
        "local_fixture_human_approval_artifact",
        "local_fixture_human_approval_artifact_path",
    ),
    (
        "local_fixture_human_approval_artifact_result",
        "local_fixture_human_approval_artifact_result_path",
    ),
    (
        "local_fixture_human_approval_artifact_manifest",
        "local_fixture_human_approval_artifact_manifest_path",
    ),
    (
        "local_fixture_human_approval_artifact_summary",
        "local_fixture_human_approval_artifact_summary_path",
    ),
    (
        "local_fixture_human_approval_artifact_checklist",
        "local_fixture_human_approval_artifact_checklist_path",
    ),
    ("artifact_index", "artifact_index_path"),
    ("artifact_index_manifest", "artifact_index_manifest_path"),
)

_LOCAL_FIXTURE_RUNNER_CONTRACT_DRAFT_DIRECT_PATH_FIELDS = (
    ("local_fixture_runner_contract_draft", "contract_path"),
    ("local_fixture_runner_contract_draft_result", "result_path"),
    ("local_fixture_runner_contract_draft_manifest", "manifest_path"),
    ("local_fixture_runner_contract_draft_summary", "summary_path"),
    ("local_fixture_runner_contract_draft_checklist", "checklist_path"),
    ("artifact_index", "artifact_index_path"),
    ("artifact_index_manifest", "artifact_index_manifest_path"),
)

_LOCAL_FIXTURE_RUNNER_STUB_ADMISSION_GATE_DIRECT_PATH_FIELDS = (
    ("local_fixture_runner_stub_admission_gate", "gate_path"),
    ("local_fixture_runner_stub_admission_gate_result", "result_path"),
    ("local_fixture_runner_stub_admission_gate_manifest", "manifest_path"),
    ("local_fixture_runner_stub_admission_gate_summary", "summary_path"),
    ("local_fixture_runner_stub_admission_gate_checklist", "checklist_path"),
    ("artifact_index", "artifact_index_path"),
    ("artifact_index_manifest", "artifact_index_manifest_path"),
)

_LOCAL_FIXTURE_RUNNER_RECEIPT_CONTRACT_DRAFT_DIRECT_PATH_FIELDS = (
    ("local_fixture_runner_receipt_contract_draft", "contract_path"),
    ("local_fixture_runner_receipt_contract_draft_result", "result_path"),
    ("local_fixture_runner_receipt_contract_draft_manifest", "manifest_path"),
    ("local_fixture_runner_receipt_contract_draft_summary", "summary_path"),
    ("local_fixture_runner_receipt_contract_draft_checklist", "checklist_path"),
    ("artifact_index", "artifact_index_path"),
    ("artifact_index_manifest", "artifact_index_manifest_path"),
)

_LOCAL_FIXTURE_RUNNER_RECEIPT_PREFLIGHT_VERIFIER_DIRECT_PATH_FIELDS = (
    ("local_fixture_runner_receipt_preflight_verifier", "preflight_path"),
    ("local_fixture_runner_receipt_preflight_verifier_result", "result_path"),
    ("local_fixture_runner_receipt_preflight_verifier_manifest", "manifest_path"),
    ("local_fixture_runner_receipt_preflight_verifier_summary", "summary_path"),
    ("local_fixture_runner_receipt_preflight_verifier_checklist", "checklist_path"),
    ("artifact_index", "artifact_index_path"),
    ("artifact_index_manifest", "artifact_index_manifest_path"),
)

_LOCAL_FIXTURE_RUNNER_RECEIPT_METADATA_ARTIFACT_DIRECT_PATH_FIELDS = (
    ("local_fixture_runner_receipt_metadata_artifact", "receipt_path"),
    ("local_fixture_runner_receipt_metadata_artifact_result", "result_path"),
    ("local_fixture_runner_receipt_metadata_artifact_manifest", "manifest_path"),
    ("local_fixture_runner_receipt_metadata_artifact_summary", "summary_path"),
    ("local_fixture_runner_receipt_metadata_artifact_checklist", "checklist_path"),
    ("artifact_index", "artifact_index_path"),
    ("artifact_index_manifest", "artifact_index_manifest_path"),
)

_DELIVERY_PATH_FIELDS = (
    ("runtime_delivery_manifest", "runtime_delivery_manifest_path"),
    ("runtime_delivery_validation", "runtime_delivery_validation_path"),
)

_GRAPH_ARTIFACTS = (
    ("task_graph_execution_manifest", "execution_manifest_path"),
    ("task_graph_replay_manifest", "replay_manifest_path"),
    ("task_graph_failure_bundle", "failure_bundle_path"),
)

_ROLE_ARTIFACT_TYPES = {
    "asset_runtime_audit_log": "jsonl",
    "asset_scan_failure_summary": "markdown",
    "launcher_summary": "markdown",
    "local_asset_incremental_scan_summary": "markdown",
    "local_asset_human_smoke_run_summary": "markdown",
    "local_asset_bounded_smoke_iteration_summary": "markdown",
    "local_asset_bounded_smoke_iteration_human_review_checklist": "markdown",
    "local_asset_smoke_promotion_human_signoff_checklist": "markdown",
    "local_asset_smoke_promotion_summary": "markdown",
    "local_asset_iteration_promotion_human_signoff_checklist": "markdown",
    "local_asset_iteration_promotion_summary": "markdown",
    "local_asset_bounded_smoke_cycle_summary": "markdown",
    "local_asset_bounded_smoke_cycle_human_review_checklist": "markdown",
    "local_asset_bounded_smoke_cycle_human_review_summary": "markdown",
    "local_asset_bounded_smoke_cycle_human_review_checklist": "markdown",
    "local_asset_next_bounded_smoke_iteration_admission_summary": "markdown",
    "local_asset_next_bounded_smoke_iteration_admission_checklist": "markdown",
    "local_asset_next_bounded_smoke_iteration_execution_request_summary": "markdown",
    "local_asset_next_bounded_smoke_iteration_execution_request_checklist": "markdown",
    "local_asset_next_bounded_smoke_iteration_runner_admission_summary": "markdown",
    "local_asset_next_bounded_smoke_iteration_runner_admission_checklist": "markdown",
    "local_asset_next_bounded_smoke_iteration_runner_summary": "markdown",
    "local_asset_next_bounded_smoke_iteration_runner_checklist": "markdown",
    "local_asset_next_bounded_smoke_iteration_run_review_packet_summary": "markdown",
    "local_asset_next_bounded_smoke_iteration_run_review_packet_checklist": "markdown",
    "local_asset_next_bounded_smoke_iteration_run_promotion_gate_summary": "markdown",
    "local_asset_next_bounded_smoke_iteration_run_promotion_gate_checklist": "markdown",
    "local_asset_next_bounded_smoke_cycle_contract_from_run_promotion_gate_summary": "markdown",
    "local_asset_next_bounded_smoke_cycle_contract_from_run_promotion_gate_checklist": "markdown",
    "local_asset_next_bounded_smoke_cycle_contract_human_review_from_run_promotion_gate_summary": "markdown",
    "local_asset_next_bounded_smoke_cycle_contract_human_review_from_run_promotion_gate_checklist": "markdown",
    "github_capability_intake_packet_summary": "markdown",
    "github_capability_intake_packet_checklist": "markdown",
    "playwright_local_fixture_sandbox_smoke_summary": "markdown",
    "playwright_local_fixture_sandbox_smoke_checklist": "markdown",
    "playwright_local_fixture_sandbox_smoke_screenshot": "png",
    "playwright_local_fixture_index_html": "html",
    "playwright_local_fixture_app_js": "javascript",
    "playwright_local_fixture_style_css": "css",
    "bounded_playwright_worker_adapter_draft_summary": "markdown",
    "bounded_playwright_worker_adapter_draft_checklist": "markdown",
    "operator_provided_playwright_execution_receipt_summary": "markdown",
    "operator_provided_playwright_execution_receipt_checklist": "markdown",
    "local_fixture_playwright_adapter_admission_gate_summary": "markdown",
    "local_fixture_playwright_adapter_admission_gate_checklist": "markdown",
    "local_only_playwright_fixture_scenario_suite_summary": "markdown",
    "local_only_playwright_fixture_scenario_suite_checklist": "markdown",
    "local_only_playwright_fixture_scenario_suite_scenario_result": "json",
    "playwright_local_admission_receipt_aggregation_summary": "markdown",
    "playwright_local_admission_receipt_aggregation_checklist": "markdown",
    "admission_gated_local_adapter_registry_promotion_summary": "markdown",
    "admission_gated_local_adapter_registry_promotion_checklist": "markdown",
    "local_fixture_adapter_usage_receipt_summary": "markdown",
    "local_fixture_adapter_usage_receipt_checklist": "markdown",
    "local_fixture_adapter_dry_run_invocation_plan_summary": "markdown",
    "local_fixture_adapter_dry_run_invocation_plan_checklist": "markdown",
    "local_fixture_adapter_execution_gate_plan_human_approval_request": "markdown",
    "local_fixture_adapter_execution_gate_plan_summary": "markdown",
    "local_fixture_adapter_execution_gate_plan_checklist": "markdown",
    "local_fixture_human_approval_artifact_summary": "markdown",
    "local_fixture_human_approval_artifact_checklist": "markdown",
    "local_fixture_runner_contract_draft_summary": "markdown",
    "local_fixture_runner_contract_draft_checklist": "markdown",
    "local_fixture_runner_stub_admission_gate_summary": "markdown",
    "local_fixture_runner_stub_admission_gate_checklist": "markdown",
    "local_fixture_runner_receipt_contract_draft_summary": "markdown",
    "local_fixture_runner_receipt_contract_draft_checklist": "markdown",
    "local_fixture_runner_receipt_preflight_verifier_summary": "markdown",
    "local_fixture_runner_receipt_preflight_verifier_checklist": "markdown",
    "local_fixture_runner_receipt_metadata_artifact_summary": "markdown",
    "local_fixture_runner_receipt_metadata_artifact_checklist": "markdown",
    "embedded_playwright_local_fixture_sandbox_smoke_summary": "markdown",
    "embedded_playwright_local_fixture_sandbox_smoke_checklist": "markdown",
    "embedded_playwright_local_fixture_sandbox_smoke_screenshot": "png",
    "embedded_fixture_index_html": "html",
    "embedded_fixture_app_js": "javascript",
    "embedded_fixture_style_css": "css",
    "local_asset_smoke_human_decision_checklist": "markdown",
    "local_asset_sqlite_query_summary": "markdown",
    "local_asset_smoke_readiness_summary": "markdown",
    "local_asset_smoke_review_summary": "markdown",
    "local_asset_smoke_iteration_review_summary": "markdown",
    "local_asset_smoke_iteration_human_decision_checklist": "markdown",
    "media_inventory": "markdown",
}


def build_task_graph_artifact_outputs_manifest(
    *,
    graph_id: str,
    graph_path: Path,
    graph_sha256: str,
    graph_execution_mode: str,
    graph_success: bool,
    node_order: tuple[str, ...],
    executed_nodes: list[dict],
    output_dir: Path,
    execution_manifest_path: Path,
    replay_manifest_path: Path,
    failure_bundle_path: Path | None,
) -> dict:
    """Build a metadata-only task graph artifact output manifest."""

    output_path = Path(output_dir)
    ordered_nodes = _ordered_nodes(executed_nodes, node_order)
    artifact_candidates = []
    for node in ordered_nodes:
        artifact_candidates.extend(_node_artifact_candidates(node, output_path))
    artifact_candidates.extend(
        _graph_artifact_candidates(
            graph_success=graph_success,
            output_dir=output_path,
            execution_manifest_path=execution_manifest_path,
            replay_manifest_path=replay_manifest_path,
            failure_bundle_path=failure_bundle_path,
        )
    )
    artifacts = _assign_artifact_ids(artifact_candidates)
    node_artifact_counts = {
        node_id: sum(1 for artifact in artifacts if artifact["node_id"] == node_id)
        for node_id in node_order
    }
    failed_node_ids = {
        node["node_id"] for node in ordered_nodes if node.get("status") == "failed"
    }
    failed_node_artifacts = [
        _failed_node_artifact_ref(artifact)
        for artifact in artifacts
        if artifact["node_id"] in failed_node_ids
    ]
    return {
        "manifest_type": _MANIFEST_TYPE,
        "authority": "non_authority",
        "execution_capability": "local_task_graph_fixture_only",
        "graph_id": graph_id,
        "graph_path": Path(graph_path).as_posix(),
        "graph_sha256": graph_sha256,
        "graph_execution_mode": graph_execution_mode,
        "graph_success": graph_success,
        "node_order": list(node_order),
        "artifact_count": len(artifacts),
        "artifacts": artifacts,
        "node_artifact_counts": node_artifact_counts,
        "failed_node_artifacts": failed_node_artifacts,
        "skipped_nodes": _skipped_node_refs(ordered_nodes),
        "input_mutation_performed": False,
        "file_move_performed": False,
        "file_rename_performed": False,
        "file_delete_performed": False,
        "media_organizer_behavior_performed": False,
        "output_overwrite_performed": False,
        "network_access_performed": False,
        "model_api_called": False,
        "external_runtime_invoked": False,
        "required_human_approval": True,
        "next_allowed_action": "human_review_task_graph_artifacts",
    }


def task_graph_artifact_outputs_projection_sha256(manifest: dict) -> str:
    """Hash a non-circular manifest projection for replay binding.

    The final artifact-output manifest includes the replay manifest file hash.
    The replay manifest therefore binds a canonical projection that normalizes
    only that self-referential artifact's file existence, size, and hash.
    """

    projection = json.loads(json.dumps(manifest, sort_keys=True))
    for artifact in projection.get("artifacts", []):
        if (
            artifact.get("node_id") == _GRAPH_ARTIFACT_NODE_ID
            and artifact.get("artifact_role") == "task_graph_replay_manifest"
        ):
            artifact["exists"] = False
            artifact["sha256"] = None
            artifact["size_bytes"] = None
    return sha256_canonical_json(projection)


def write_task_graph_artifact_outputs_manifest(
    output_path: Path,
    manifest: dict,
) -> None:
    output_file = Path(output_path)
    if output_file.exists():
        raise ValueError("task graph artifact outputs already exists")
    write_json_atomically(output_file, manifest)


def _ordered_nodes(executed_nodes, node_order):
    by_id = {node["node_id"]: node for node in executed_nodes}
    return [by_id[node_id] for node_id in node_order if node_id in by_id]


def _node_artifact_candidates(node, output_dir):
    if (
        node["adapter_id"] == _LOCAL_ASSET_ADAPTER_ID
        and node["capability"] == _LOCAL_ASSET_CAPABILITY
    ):
        return _local_asset_artifact_candidates(node, output_dir)
    if (
        node["adapter_id"] == _LOCAL_ASSET_ADAPTER_ID
        and node["capability"] == _LOCAL_ASSET_SMOKE_READINESS_CAPABILITY
    ):
        return _local_asset_smoke_readiness_artifact_candidates(node, output_dir)
    if (
        node["adapter_id"] == _LOCAL_ASSET_ADAPTER_ID
        and node["capability"] == _LOCAL_ASSET_HUMAN_SMOKE_CAPABILITY
    ):
        return _local_asset_human_smoke_artifact_candidates(node, output_dir)
    if (
        node["adapter_id"] == _LOCAL_ASSET_ADAPTER_ID
        and node["capability"] == _LOCAL_ASSET_BOUNDED_SMOKE_ITERATION_CAPABILITY
    ):
        return _local_asset_bounded_smoke_iteration_artifact_candidates(
            node,
            output_dir,
        )
    if (
        node["adapter_id"] == _LOCAL_ASSET_ADAPTER_ID
        and node["capability"] == _LOCAL_ASSET_SMOKE_REVIEW_PACKET_CAPABILITY
    ):
        return _local_asset_smoke_review_packet_artifact_candidates(
            node,
            output_dir,
        )
    if (
        node["adapter_id"] == _LOCAL_ASSET_ADAPTER_ID
        and node["capability"]
        == _LOCAL_ASSET_SMOKE_ITERATION_REVIEW_PACKET_CAPABILITY
    ):
        return _local_asset_smoke_iteration_review_packet_artifact_candidates(
            node,
            output_dir,
        )
    if (
        node["adapter_id"] == _LOCAL_ASSET_ADAPTER_ID
        and node["capability"] == _LOCAL_ASSET_SMOKE_PROMOTION_GATE_CAPABILITY
    ):
        return _local_asset_smoke_promotion_gate_artifact_candidates(
            node,
            output_dir,
        )
    if (
        node["adapter_id"] == _LOCAL_ASSET_ADAPTER_ID
        and node["capability"] == _LOCAL_ASSET_ITERATION_PROMOTION_GATE_CAPABILITY
    ):
        return _local_asset_iteration_promotion_gate_artifact_candidates(
            node,
            output_dir,
        )
    if (
        node["adapter_id"] == _LOCAL_ASSET_ADAPTER_ID
        and node["capability"]
        == _LOCAL_ASSET_BOUNDED_SMOKE_CYCLE_CONTRACT_CAPABILITY
    ):
        return _local_asset_bounded_smoke_cycle_contract_artifact_candidates(
            node,
            output_dir,
        )
    if (
        node["adapter_id"] == _LOCAL_ASSET_ADAPTER_ID
        and node["capability"]
        == _LOCAL_ASSET_BOUNDED_SMOKE_CYCLE_HUMAN_REVIEW_CAPABILITY
    ):
        return _local_asset_bounded_smoke_cycle_human_review_artifact_candidates(
            node,
            output_dir,
        )
    if (
        node["adapter_id"] == _LOCAL_ASSET_ADAPTER_ID
        and node["capability"]
        == _LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_ADMISSION_CAPABILITY
    ):
        return _local_asset_next_bounded_smoke_iteration_admission_artifact_candidates(
            node,
            output_dir,
        )
    if (
        node["adapter_id"] == _LOCAL_ASSET_ADAPTER_ID
        and node["capability"]
        == _LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_EXECUTION_REQUEST_CAPABILITY
    ):
        return _local_asset_next_bounded_smoke_iteration_execution_request_artifact_candidates(
            node,
            output_dir,
        )
    if (
        node["adapter_id"] == _LOCAL_ASSET_ADAPTER_ID
        and node["capability"]
        == _LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUNNER_ADMISSION_CAPABILITY
    ):
        return _local_asset_next_bounded_smoke_iteration_runner_admission_artifact_candidates(
            node,
            output_dir,
        )
    if (
        node["adapter_id"] == _LOCAL_ASSET_ADAPTER_ID
        and node["capability"]
        == _LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUNNER_CAPABILITY
    ):
        return _local_asset_next_bounded_smoke_iteration_runner_artifact_candidates(
            node,
            output_dir,
        )
    if (
        node["adapter_id"] == _LOCAL_ASSET_ADAPTER_ID
        and node["capability"]
        == _LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUN_REVIEW_PACKET_CAPABILITY
    ):
        return _local_asset_next_bounded_smoke_iteration_run_review_packet_artifact_candidates(
            node,
            output_dir,
        )
    if (
        node["adapter_id"] == _LOCAL_ASSET_ADAPTER_ID
        and node["capability"]
        == _LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUN_PROMOTION_GATE_CAPABILITY
    ):
        return _local_asset_next_bounded_smoke_iteration_run_promotion_gate_artifact_candidates(
            node,
            output_dir,
        )
    if (
        node["adapter_id"] == _LOCAL_ASSET_ADAPTER_ID
        and node["capability"]
        == _LOCAL_ASSET_NEXT_BOUNDED_SMOKE_CYCLE_CONTRACT_FROM_RUN_PROMOTION_GATE_CAPABILITY
    ):
        return _local_asset_next_bounded_smoke_cycle_contract_from_run_promotion_gate_artifact_candidates(
            node,
            output_dir,
        )
    if (
        node["adapter_id"] == _LOCAL_ASSET_ADAPTER_ID
        and node["capability"]
        == _LOCAL_ASSET_NEXT_BOUNDED_SMOKE_CYCLE_CONTRACT_HUMAN_REVIEW_FROM_RUN_PROMOTION_GATE_CAPABILITY
    ):
        return _local_asset_next_bounded_smoke_cycle_contract_human_review_from_run_promotion_gate_artifact_candidates(
            node,
            output_dir,
        )
    if (
        node["adapter_id"] == _GITHUB_CAPABILITY_ADAPTER_ID
        and node["capability"] == _GITHUB_CAPABILITY_INTAKE_PACKET_CAPABILITY
    ):
        return _github_capability_intake_packet_artifact_candidates(
            node,
            output_dir,
        )
    if (
        node["adapter_id"] == _PLAYWRIGHT_SMOKE_ADAPTER_ID
        and node["capability"] == _PLAYWRIGHT_SMOKE_CAPABILITY
    ):
        return _playwright_smoke_artifact_candidates(node, output_dir)
    if (
        node["adapter_id"] == _BOUNDED_PLAYWRIGHT_ADAPTER_DRAFT_ID
        and node["capability"] == _BOUNDED_PLAYWRIGHT_ADAPTER_DRAFT_CAPABILITY
    ):
        return _bounded_playwright_adapter_draft_artifact_candidates(
            node,
            output_dir,
        )
    if (
        node["adapter_id"] == _OPERATOR_PLAYWRIGHT_RECEIPT_ADAPTER_ID
        and node["capability"] == _OPERATOR_PLAYWRIGHT_RECEIPT_CAPABILITY
    ):
        return _operator_playwright_receipt_artifact_candidates(node, output_dir)
    if (
        node["adapter_id"] == _LOCAL_FIXTURE_PLAYWRIGHT_ADMISSION_GATE_ADAPTER_ID
        and node["capability"] == _LOCAL_FIXTURE_PLAYWRIGHT_ADMISSION_GATE_CAPABILITY
    ):
        return _local_fixture_playwright_admission_gate_artifact_candidates(
            node,
            output_dir,
        )
    if (
        node["adapter_id"] == _LOCAL_ONLY_PLAYWRIGHT_FIXTURE_SCENARIO_SUITE_ADAPTER_ID
        and node["capability"] == _LOCAL_ONLY_PLAYWRIGHT_FIXTURE_SCENARIO_SUITE_CAPABILITY
    ):
        return _local_only_playwright_fixture_scenario_suite_artifact_candidates(
            node,
            output_dir,
        )
    if (
        node["adapter_id"] == _PLAYWRIGHT_LOCAL_ADMISSION_RECEIPT_AGGREGATION_ADAPTER_ID
        and node["capability"]
        == _PLAYWRIGHT_LOCAL_ADMISSION_RECEIPT_AGGREGATION_CAPABILITY
    ):
        return _playwright_local_admission_receipt_aggregation_artifact_candidates(
            node,
            output_dir,
        )
    if (
        node["adapter_id"]
        == _ADMISSION_GATED_LOCAL_ADAPTER_REGISTRY_PROMOTION_ADAPTER_ID
        and node["capability"]
        == _ADMISSION_GATED_LOCAL_ADAPTER_REGISTRY_PROMOTION_CAPABILITY
    ):
        return _admission_gated_local_adapter_registry_promotion_artifact_candidates(
            node,
            output_dir,
        )
    if (
        node["adapter_id"] == _LOCAL_FIXTURE_ADAPTER_USAGE_RECEIPT_ADAPTER_ID
        and node["capability"] == _LOCAL_FIXTURE_ADAPTER_USAGE_RECEIPT_CAPABILITY
    ):
        return _local_fixture_adapter_usage_receipt_artifact_candidates(
            node,
            output_dir,
        )
    if (
        node["adapter_id"]
        == _LOCAL_FIXTURE_ADAPTER_DRY_RUN_INVOCATION_PLAN_ADAPTER_ID
        and node["capability"]
        == _LOCAL_FIXTURE_ADAPTER_DRY_RUN_INVOCATION_PLAN_CAPABILITY
    ):
        return _local_fixture_adapter_dry_run_invocation_plan_artifact_candidates(
            node,
            output_dir,
        )
    if (
        node["adapter_id"] == _LOCAL_FIXTURE_ADAPTER_EXECUTION_GATE_PLAN_ADAPTER_ID
        and node["capability"] == _LOCAL_FIXTURE_ADAPTER_EXECUTION_GATE_PLAN_CAPABILITY
    ):
        return _local_fixture_adapter_execution_gate_plan_artifact_candidates(
            node,
            output_dir,
        )
    if (
        node["adapter_id"] == _LOCAL_FIXTURE_HUMAN_APPROVAL_ARTIFACT_ADAPTER_ID
        and node["capability"] == _LOCAL_FIXTURE_HUMAN_APPROVAL_ARTIFACT_CAPABILITY
    ):
        return _local_fixture_human_approval_artifact_candidates(
            node,
            output_dir,
        )
    if (
        node["adapter_id"] == _LOCAL_FIXTURE_RUNNER_CONTRACT_DRAFT_ADAPTER_ID
        and node["capability"] == _LOCAL_FIXTURE_RUNNER_CONTRACT_DRAFT_CAPABILITY
    ):
        return _local_fixture_runner_contract_draft_artifact_candidates(
            node,
            output_dir,
        )
    if (
        node["adapter_id"] == _LOCAL_FIXTURE_RUNNER_STUB_ADMISSION_GATE_ADAPTER_ID
        and node["capability"]
        == _LOCAL_FIXTURE_RUNNER_STUB_ADMISSION_GATE_CAPABILITY
    ):
        return _local_fixture_runner_stub_admission_gate_artifact_candidates(
            node,
            output_dir,
        )
    if (
        node["adapter_id"]
        == _LOCAL_FIXTURE_RUNNER_RECEIPT_CONTRACT_DRAFT_ADAPTER_ID
        and node["capability"]
        == _LOCAL_FIXTURE_RUNNER_RECEIPT_CONTRACT_DRAFT_CAPABILITY
    ):
        return _local_fixture_runner_receipt_contract_draft_artifact_candidates(
            node,
            output_dir,
        )
    if (
        node["adapter_id"]
        == _LOCAL_FIXTURE_RUNNER_RECEIPT_PREFLIGHT_VERIFIER_ADAPTER_ID
        and node["capability"]
        == _LOCAL_FIXTURE_RUNNER_RECEIPT_PREFLIGHT_VERIFIER_CAPABILITY
    ):
        return _local_fixture_runner_receipt_preflight_verifier_artifact_candidates(
            node,
            output_dir,
        )
    if (
        node["adapter_id"]
        == _LOCAL_FIXTURE_RUNNER_RECEIPT_METADATA_ARTIFACT_ADAPTER_ID
        and node["capability"]
        == _LOCAL_FIXTURE_RUNNER_RECEIPT_METADATA_ARTIFACT_CAPABILITY
    ):
        return _local_fixture_runner_receipt_metadata_artifact_candidates(
            node,
            output_dir,
        )
    if (
        node["adapter_id"] == _DELIVERY_ADAPTER_ID
        and node["capability"] == _DELIVERY_CAPABILITY
    ):
        return _delivery_artifact_candidates(node, output_dir)
    return []


def _local_asset_artifact_candidates(node, output_dir):
    role_paths = []
    seen_roles = set()
    for role, field_name in _LOCAL_ASSET_DIRECT_PATH_FIELDS:
        path_value = node.get(field_name)
        if _add_role_path(role_paths, seen_roles, role, path_value):
            continue
    output_paths = node.get("asset_runtime_output_paths")
    if isinstance(output_paths, dict):
        for file_name in sorted(output_paths):
            role = _LOCAL_ASSET_OUTPUT_FILE_ROLES.get(file_name)
            if role is not None:
                _add_role_path(role_paths, seen_roles, role, output_paths[file_name])
    return [
        _artifact_record(
            node_id=node["node_id"],
            adapter_id=node["adapter_id"],
            capability=node["capability"],
            node_status=node["status"],
            artifact_role=role,
            path_value=path_value,
            output_dir=output_dir,
        )
        for role, path_value in role_paths
    ]


def _local_asset_smoke_readiness_artifact_candidates(node, output_dir):
    role_paths = []
    seen_roles = set()
    for role, field_name in _LOCAL_ASSET_SMOKE_READINESS_DIRECT_PATH_FIELDS:
        _add_role_path(role_paths, seen_roles, role, node.get(field_name))
    return [
        _artifact_record(
            node_id=node["node_id"],
            adapter_id=node["adapter_id"],
            capability=node["capability"],
            node_status=node["status"],
            artifact_role=role,
            path_value=path_value,
            output_dir=output_dir,
        )
        for role, path_value in role_paths
    ]


def _local_asset_human_smoke_artifact_candidates(node, output_dir):
    role_paths = []
    seen_roles = set()
    for role, field_name in _LOCAL_ASSET_HUMAN_SMOKE_DIRECT_PATH_FIELDS:
        _add_role_path(role_paths, seen_roles, role, node.get(field_name))
    return [
        _artifact_record(
            node_id=node["node_id"],
            adapter_id=node["adapter_id"],
            capability=node["capability"],
            node_status=node["status"],
            artifact_role=role,
            path_value=path_value,
            output_dir=output_dir,
        )
        for role, path_value in role_paths
    ]


def _github_capability_intake_packet_artifact_candidates(node, output_dir):
    role_paths = []
    seen_roles = set()
    for role, field_name in _GITHUB_CAPABILITY_INTAKE_PACKET_DIRECT_PATH_FIELDS:
        _add_role_path(role_paths, seen_roles, role, node.get(field_name))
    return [
        _artifact_record(
            node_id=node["node_id"],
            adapter_id=node["adapter_id"],
            capability=node["capability"],
            node_status=node["status"],
            artifact_role=role,
            path_value=path_value,
            output_dir=output_dir,
        )
        for role, path_value in role_paths
    ]


def _playwright_smoke_artifact_candidates(node, output_dir):
    role_paths = []
    seen_roles = set()
    for role, field_name in _PLAYWRIGHT_SMOKE_DIRECT_PATH_FIELDS:
        _add_role_path(role_paths, seen_roles, role, node.get(field_name))
    return [
        _artifact_record(
            node_id=node["node_id"],
            adapter_id=node["adapter_id"],
            capability=node["capability"],
            node_status=node["status"],
            artifact_role=role,
            path_value=path_value,
            output_dir=output_dir,
        )
        for role, path_value in role_paths
    ]


def _bounded_playwright_adapter_draft_artifact_candidates(node, output_dir):
    role_paths = []
    seen_roles = set()
    for role, field_name in _BOUNDED_PLAYWRIGHT_ADAPTER_DRAFT_DIRECT_PATH_FIELDS:
        _add_role_path(role_paths, seen_roles, role, node.get(field_name))
    return [
        _artifact_record(
            node_id=node["node_id"],
            adapter_id=node["adapter_id"],
            capability=node["capability"],
            node_status=node["status"],
            artifact_role=role,
            path_value=path_value,
            output_dir=output_dir,
        )
        for role, path_value in role_paths
    ]


def _operator_playwright_receipt_artifact_candidates(node, output_dir):
    role_paths = []
    seen_roles = set()
    for role, field_name in _OPERATOR_PLAYWRIGHT_RECEIPT_DIRECT_PATH_FIELDS:
        _add_role_path(role_paths, seen_roles, role, node.get(field_name))
    return [
        _artifact_record(
            node_id=node["node_id"],
            adapter_id=node["adapter_id"],
            capability=node["capability"],
            node_status=node["status"],
            artifact_role=role,
            path_value=path_value,
            output_dir=output_dir,
        )
        for role, path_value in role_paths
    ]


def _local_fixture_playwright_admission_gate_artifact_candidates(node, output_dir):
    role_paths = []
    seen_roles = set()
    for role, field_name in _LOCAL_FIXTURE_PLAYWRIGHT_ADMISSION_GATE_DIRECT_PATH_FIELDS:
        _add_role_path(role_paths, seen_roles, role, node.get(field_name))
    return [
        _artifact_record(
            node_id=node["node_id"],
            adapter_id=node["adapter_id"],
            capability=node["capability"],
            node_status=node["status"],
            artifact_role=role,
            path_value=path_value,
            output_dir=output_dir,
        )
        for role, path_value in role_paths
    ]


def _local_only_playwright_fixture_scenario_suite_artifact_candidates(node, output_dir):
    role_paths = []
    seen_roles = set()
    for role, field_name in (
        _LOCAL_ONLY_PLAYWRIGHT_FIXTURE_SCENARIO_SUITE_DIRECT_PATH_FIELDS
    ):
        _add_role_path(role_paths, seen_roles, role, node.get(field_name))
    scenario_result_paths = node.get("scenario_result_paths")
    if isinstance(scenario_result_paths, list):
        for index, path_value in enumerate(scenario_result_paths, start=1):
            if isinstance(path_value, str) and path_value:
                _add_role_path(
                    role_paths,
                    seen_roles,
                    "local_only_playwright_fixture_scenario_suite_scenario_result_"
                    + str(index),
                    path_value,
                )
    return [
        _artifact_record(
            node_id=node["node_id"],
            adapter_id=node["adapter_id"],
            capability=node["capability"],
            node_status=node["status"],
            artifact_role=role,
            path_value=path_value,
            output_dir=output_dir,
        )
        for role, path_value in role_paths
    ]


def _playwright_local_admission_receipt_aggregation_artifact_candidates(
    node,
    output_dir,
):
    role_paths = []
    seen_roles = set()
    for role, field_name in (
        _PLAYWRIGHT_LOCAL_ADMISSION_RECEIPT_AGGREGATION_DIRECT_PATH_FIELDS
    ):
        _add_role_path(role_paths, seen_roles, role, node.get(field_name))
    return [
        _artifact_record(
            node_id=node["node_id"],
            adapter_id=node["adapter_id"],
            capability=node["capability"],
            node_status=node["status"],
            artifact_role=role,
            path_value=path_value,
            output_dir=output_dir,
        )
        for role, path_value in role_paths
    ]


def _admission_gated_local_adapter_registry_promotion_artifact_candidates(
    node,
    output_dir,
):
    role_paths = []
    seen_roles = set()
    for role, field_name in (
        _ADMISSION_GATED_LOCAL_ADAPTER_REGISTRY_PROMOTION_DIRECT_PATH_FIELDS
    ):
        _add_role_path(role_paths, seen_roles, role, node.get(field_name))
    return [
        _artifact_record(
            node_id=node["node_id"],
            adapter_id=node["adapter_id"],
            capability=node["capability"],
            node_status=node["status"],
            artifact_role=role,
            path_value=path_value,
            output_dir=output_dir,
        )
        for role, path_value in role_paths
    ]


def _local_fixture_adapter_usage_receipt_artifact_candidates(node, output_dir):
    role_paths = []
    seen_roles = set()
    for role, field_name in _LOCAL_FIXTURE_ADAPTER_USAGE_RECEIPT_DIRECT_PATH_FIELDS:
        _add_role_path(role_paths, seen_roles, role, node.get(field_name))
    return [
        _artifact_record(
            node_id=node["node_id"],
            adapter_id=node["adapter_id"],
            capability=node["capability"],
            node_status=node["status"],
            artifact_role=role,
            path_value=path_value,
            output_dir=output_dir,
        )
        for role, path_value in role_paths
    ]


def _local_fixture_adapter_dry_run_invocation_plan_artifact_candidates(
    node,
    output_dir,
):
    role_paths = []
    seen_roles = set()
    for role, field_name in (
        _LOCAL_FIXTURE_ADAPTER_DRY_RUN_INVOCATION_PLAN_DIRECT_PATH_FIELDS
    ):
        _add_role_path(role_paths, seen_roles, role, node.get(field_name))
    return [
        _artifact_record(
            node_id=node["node_id"],
            adapter_id=node["adapter_id"],
            capability=node["capability"],
            node_status=node["status"],
            artifact_role=role,
            path_value=path_value,
            output_dir=output_dir,
        )
        for role, path_value in role_paths
    ]


def _local_fixture_adapter_execution_gate_plan_artifact_candidates(
    node,
    output_dir,
):
    role_paths = []
    seen_roles = set()
    for role, field_name in (
        _LOCAL_FIXTURE_ADAPTER_EXECUTION_GATE_PLAN_DIRECT_PATH_FIELDS
    ):
        _add_role_path(role_paths, seen_roles, role, node.get(field_name))
    return [
        _artifact_record(
            node_id=node["node_id"],
            adapter_id=node["adapter_id"],
            capability=node["capability"],
            node_status=node["status"],
            artifact_role=role,
            path_value=path_value,
            output_dir=output_dir,
        )
        for role, path_value in role_paths
    ]


def _local_fixture_human_approval_artifact_candidates(
    node,
    output_dir,
):
    role_paths = []
    seen_roles = set()
    for role, field_name in (
        _LOCAL_FIXTURE_HUMAN_APPROVAL_ARTIFACT_DIRECT_PATH_FIELDS
    ):
        _add_role_path(role_paths, seen_roles, role, node.get(field_name))
    return [
        _artifact_record(
            node_id=node["node_id"],
            adapter_id=node["adapter_id"],
            capability=node["capability"],
            node_status=node["status"],
            artifact_role=role,
            path_value=path_value,
            output_dir=output_dir,
        )
        for role, path_value in role_paths
    ]


def _local_fixture_runner_contract_draft_artifact_candidates(node, output_dir):
    return _direct_path_artifact_candidates(
        node,
        output_dir,
        _LOCAL_FIXTURE_RUNNER_CONTRACT_DRAFT_DIRECT_PATH_FIELDS,
    )


def _local_fixture_runner_stub_admission_gate_artifact_candidates(
    node,
    output_dir,
):
    return _direct_path_artifact_candidates(
        node,
        output_dir,
        _LOCAL_FIXTURE_RUNNER_STUB_ADMISSION_GATE_DIRECT_PATH_FIELDS,
    )


def _local_fixture_runner_receipt_contract_draft_artifact_candidates(
    node,
    output_dir,
):
    return _direct_path_artifact_candidates(
        node,
        output_dir,
        _LOCAL_FIXTURE_RUNNER_RECEIPT_CONTRACT_DRAFT_DIRECT_PATH_FIELDS,
    )


def _local_fixture_runner_receipt_preflight_verifier_artifact_candidates(
    node,
    output_dir,
):
    return _direct_path_artifact_candidates(
        node,
        output_dir,
        _LOCAL_FIXTURE_RUNNER_RECEIPT_PREFLIGHT_VERIFIER_DIRECT_PATH_FIELDS,
    )


def _local_fixture_runner_receipt_metadata_artifact_candidates(node, output_dir):
    return _direct_path_artifact_candidates(
        node,
        output_dir,
        _LOCAL_FIXTURE_RUNNER_RECEIPT_METADATA_ARTIFACT_DIRECT_PATH_FIELDS,
    )


def _direct_path_artifact_candidates(node, output_dir, direct_path_fields):
    role_paths = []
    seen_roles = set()
    for role, field_name in direct_path_fields:
        _add_role_path(role_paths, seen_roles, role, node.get(field_name))
    return [
        _artifact_record(
            node_id=node["node_id"],
            adapter_id=node["adapter_id"],
            capability=node["capability"],
            node_status=node["status"],
            artifact_role=role,
            path_value=path_value,
            output_dir=output_dir,
        )
        for role, path_value in role_paths
    ]


def _local_asset_bounded_smoke_iteration_artifact_candidates(node, output_dir):
    role_paths = []
    seen_roles = set()
    for role, field_name in _LOCAL_ASSET_BOUNDED_SMOKE_ITERATION_DIRECT_PATH_FIELDS:
        _add_role_path(role_paths, seen_roles, role, node.get(field_name))
    return [
        _artifact_record(
            node_id=node["node_id"],
            adapter_id=node["adapter_id"],
            capability=node["capability"],
            node_status=node["status"],
            artifact_role=role,
            path_value=path_value,
            output_dir=output_dir,
        )
        for role, path_value in role_paths
    ]


def _local_asset_smoke_review_packet_artifact_candidates(node, output_dir):
    role_paths = []
    seen_roles = set()
    for role, field_name in _LOCAL_ASSET_SMOKE_REVIEW_PACKET_DIRECT_PATH_FIELDS:
        _add_role_path(role_paths, seen_roles, role, node.get(field_name))
    return [
        _artifact_record(
            node_id=node["node_id"],
            adapter_id=node["adapter_id"],
            capability=node["capability"],
            node_status=node["status"],
            artifact_role=role,
            path_value=path_value,
            output_dir=output_dir,
        )
        for role, path_value in role_paths
    ]


def _local_asset_smoke_iteration_review_packet_artifact_candidates(node, output_dir):
    role_paths = []
    seen_roles = set()
    for role, field_name in (
        _LOCAL_ASSET_SMOKE_ITERATION_REVIEW_PACKET_DIRECT_PATH_FIELDS
    ):
        _add_role_path(role_paths, seen_roles, role, node.get(field_name))
    return [
        _artifact_record(
            node_id=node["node_id"],
            adapter_id=node["adapter_id"],
            capability=node["capability"],
            node_status=node["status"],
            artifact_role=role,
            path_value=path_value,
            output_dir=output_dir,
        )
        for role, path_value in role_paths
    ]


def _local_asset_smoke_promotion_gate_artifact_candidates(node, output_dir):
    role_paths = []
    seen_roles = set()
    for role, field_name in _LOCAL_ASSET_SMOKE_PROMOTION_GATE_DIRECT_PATH_FIELDS:
        _add_role_path(role_paths, seen_roles, role, node.get(field_name))
    return [
        _artifact_record(
            node_id=node["node_id"],
            adapter_id=node["adapter_id"],
            capability=node["capability"],
            node_status=node["status"],
            artifact_role=role,
            path_value=path_value,
            output_dir=output_dir,
        )
        for role, path_value in role_paths
    ]


def _local_asset_iteration_promotion_gate_artifact_candidates(node, output_dir):
    role_paths = []
    seen_roles = set()
    for role, field_name in (
        _LOCAL_ASSET_ITERATION_PROMOTION_GATE_DIRECT_PATH_FIELDS
    ):
        _add_role_path(role_paths, seen_roles, role, node.get(field_name))
    return [
        _artifact_record(
            node_id=node["node_id"],
            adapter_id=node["adapter_id"],
            capability=node["capability"],
            node_status=node["status"],
            artifact_role=role,
            path_value=path_value,
            output_dir=output_dir,
        )
        for role, path_value in role_paths
    ]


def _local_asset_bounded_smoke_cycle_contract_artifact_candidates(node, output_dir):
    role_paths = []
    seen_roles = set()
    for role, field_name in (
        _LOCAL_ASSET_BOUNDED_SMOKE_CYCLE_CONTRACT_DIRECT_PATH_FIELDS
    ):
        _add_role_path(role_paths, seen_roles, role, node.get(field_name))
    return [
        _artifact_record(
            node_id=node["node_id"],
            adapter_id=node["adapter_id"],
            capability=node["capability"],
            node_status=node["status"],
            artifact_role=role,
            path_value=path_value,
            output_dir=output_dir,
        )
        for role, path_value in role_paths
    ]


def _local_asset_bounded_smoke_cycle_human_review_artifact_candidates(
    node,
    output_dir,
):
    role_paths = []
    seen_roles = set()
    for role, field_name in (
        _LOCAL_ASSET_BOUNDED_SMOKE_CYCLE_HUMAN_REVIEW_DIRECT_PATH_FIELDS
    ):
        _add_role_path(role_paths, seen_roles, role, node.get(field_name))
    return [
        _artifact_record(
            node_id=node["node_id"],
            adapter_id=node["adapter_id"],
            capability=node["capability"],
            node_status=node["status"],
            artifact_role=role,
            path_value=path_value,
            output_dir=output_dir,
        )
        for role, path_value in role_paths
    ]


def _local_asset_next_bounded_smoke_iteration_admission_artifact_candidates(
    node,
    output_dir,
):
    role_paths = []
    seen_roles = set()
    for role, field_name in (
        _LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_ADMISSION_DIRECT_PATH_FIELDS
    ):
        _add_role_path(role_paths, seen_roles, role, node.get(field_name))
    return [
        _artifact_record(
            node_id=node["node_id"],
            adapter_id=node["adapter_id"],
            capability=node["capability"],
            node_status=node["status"],
            artifact_role=role,
            path_value=path_value,
            output_dir=output_dir,
        )
        for role, path_value in role_paths
    ]


def _local_asset_next_bounded_smoke_iteration_execution_request_artifact_candidates(
    node,
    output_dir,
):
    role_paths = []
    seen_roles = set()
    for role, field_name in (
        _LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_EXECUTION_REQUEST_DIRECT_PATH_FIELDS
    ):
        _add_role_path(role_paths, seen_roles, role, node.get(field_name))
    return [
        _artifact_record(
            node_id=node["node_id"],
            adapter_id=node["adapter_id"],
            capability=node["capability"],
            node_status=node["status"],
            artifact_role=role,
            path_value=path_value,
            output_dir=output_dir,
        )
        for role, path_value in role_paths
    ]


def _local_asset_next_bounded_smoke_iteration_runner_admission_artifact_candidates(
    node,
    output_dir,
):
    role_paths = []
    seen_roles = set()
    for role, field_name in (
        _LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUNNER_ADMISSION_DIRECT_PATH_FIELDS
    ):
        _add_role_path(role_paths, seen_roles, role, node.get(field_name))
    return [
        _artifact_record(
            node_id=node["node_id"],
            adapter_id=node["adapter_id"],
            capability=node["capability"],
            node_status=node["status"],
            artifact_role=role,
            path_value=path_value,
            output_dir=output_dir,
        )
        for role, path_value in role_paths
    ]


def _local_asset_next_bounded_smoke_iteration_runner_artifact_candidates(
    node,
    output_dir,
):
    role_paths = []
    seen_roles = set()
    for role, field_name in (
        _LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUNNER_DIRECT_PATH_FIELDS
    ):
        _add_role_path(role_paths, seen_roles, role, node.get(field_name))
    return [
        _artifact_record(
            node_id=node["node_id"],
            adapter_id=node["adapter_id"],
            capability=node["capability"],
            node_status=node["status"],
            artifact_role=role,
            path_value=path_value,
            output_dir=output_dir,
        )
        for role, path_value in role_paths
    ]


def _local_asset_next_bounded_smoke_iteration_run_review_packet_artifact_candidates(
    node,
    output_dir,
):
    role_paths = []
    seen_roles = set()
    for role, field_name in (
        _LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUN_REVIEW_PACKET_DIRECT_PATH_FIELDS
    ):
        _add_role_path(role_paths, seen_roles, role, node.get(field_name))
    return [
        _artifact_record(
            node_id=node["node_id"],
            adapter_id=node["adapter_id"],
            capability=node["capability"],
            node_status=node["status"],
            artifact_role=role,
            path_value=path_value,
            output_dir=output_dir,
        )
        for role, path_value in role_paths
    ]


def _local_asset_next_bounded_smoke_iteration_run_promotion_gate_artifact_candidates(
    node,
    output_dir,
):
    role_paths = []
    seen_roles = set()
    for role, field_name in (
        _LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUN_PROMOTION_GATE_DIRECT_PATH_FIELDS
    ):
        _add_role_path(role_paths, seen_roles, role, node.get(field_name))
    return [
        _artifact_record(
            node_id=node["node_id"],
            adapter_id=node["adapter_id"],
            capability=node["capability"],
            node_status=node["status"],
            artifact_role=role,
            path_value=path_value,
            output_dir=output_dir,
        )
        for role, path_value in role_paths
    ]


def _local_asset_next_bounded_smoke_cycle_contract_from_run_promotion_gate_artifact_candidates(
    node,
    output_dir,
):
    role_paths = []
    seen_roles = set()
    for role, field_name in (
        _LOCAL_ASSET_NEXT_BOUNDED_SMOKE_CYCLE_CONTRACT_FROM_RUN_PROMOTION_GATE_DIRECT_PATH_FIELDS
    ):
        _add_role_path(role_paths, seen_roles, role, node.get(field_name))
    return [
        _artifact_record(
            node_id=node["node_id"],
            adapter_id=node["adapter_id"],
            capability=node["capability"],
            node_status=node["status"],
            artifact_role=role,
            path_value=path_value,
            output_dir=output_dir,
        )
        for role, path_value in role_paths
    ]


def _local_asset_next_bounded_smoke_cycle_contract_human_review_from_run_promotion_gate_artifact_candidates(
    node,
    output_dir,
):
    role_paths = []
    seen_roles = set()
    for role, field_name in (
        _LOCAL_ASSET_NEXT_BOUNDED_SMOKE_CYCLE_CONTRACT_HUMAN_REVIEW_FROM_RUN_PROMOTION_GATE_DIRECT_PATH_FIELDS
    ):
        _add_role_path(role_paths, seen_roles, role, node.get(field_name))
    return [
        _artifact_record(
            node_id=node["node_id"],
            adapter_id=node["adapter_id"],
            capability=node["capability"],
            node_status=node["status"],
            artifact_role=role,
            path_value=path_value,
            output_dir=output_dir,
        )
        for role, path_value in role_paths
    ]


def _delivery_artifact_candidates(node, output_dir):
    delivery_validation = node.get("delivery_validation")
    if not isinstance(delivery_validation, dict):
        return []
    role_paths = []
    seen_roles = set()
    for role, field_name in _DELIVERY_PATH_FIELDS:
        _add_role_path(
            role_paths,
            seen_roles,
            role,
            delivery_validation.get(field_name),
        )
    return [
        _artifact_record(
            node_id=node["node_id"],
            adapter_id=node["adapter_id"],
            capability=node["capability"],
            node_status=node["status"],
            artifact_role=role,
            path_value=path_value,
            output_dir=output_dir,
        )
        for role, path_value in role_paths
    ]


def _graph_artifact_candidates(
    *,
    graph_success,
    output_dir,
    execution_manifest_path,
    replay_manifest_path,
    failure_bundle_path,
):
    graph_status = "completed" if graph_success else "failed"
    paths_by_name = {
        "execution_manifest_path": execution_manifest_path,
        "replay_manifest_path": replay_manifest_path,
        "failure_bundle_path": failure_bundle_path,
    }
    candidates = []
    for role, path_name in _GRAPH_ARTIFACTS:
        path_value = paths_by_name[path_name]
        if role == "task_graph_failure_bundle" and path_value is None:
            continue
        candidates.append(
            _artifact_record(
                node_id=_GRAPH_ARTIFACT_NODE_ID,
                adapter_id=_GRAPH_ARTIFACT_ADAPTER_ID,
                capability=_GRAPH_ARTIFACT_CAPABILITY,
                node_status=graph_status,
                artifact_role=role,
                path_value=path_value,
                output_dir=output_dir,
            )
        )
    return candidates


def _add_role_path(role_paths, seen_roles, role, path_value):
    if not isinstance(path_value, str) or not path_value:
        return False
    if role in seen_roles:
        return False
    seen_roles.add(role)
    role_paths.append((role, path_value))
    return True


def _artifact_record(
    *,
    node_id,
    adapter_id,
    capability,
    node_status,
    artifact_role,
    path_value,
    output_dir,
):
    path = Path(path_value)
    exists = path.exists() and path.is_file() and not path.is_symlink()
    return {
        "node_id": node_id,
        "adapter_id": adapter_id,
        "capability": capability,
        "node_status": node_status,
        "artifact_role": artifact_role,
        "artifact_type": _artifact_type(artifact_role, path),
        "path": path.as_posix(),
        "relative_path": _relative_path(path, output_dir),
        "sha256": sha256_file(path) if exists else None,
        "size_bytes": path.stat().st_size if exists else None,
        "exists": exists,
        "content_indexed": False,
        "raw_content_copied": False,
        "producer": "task_graph_node_output",
        "required_human_approval": True,
    }


def _assign_artifact_ids(artifact_candidates):
    groups = {}
    for artifact in artifact_candidates:
        base_id = _base_artifact_id(artifact)
        groups.setdefault(base_id, []).append(artifact)

    artifacts = []
    for artifact in artifact_candidates:
        base_id = _base_artifact_id(artifact)
        if len(groups[base_id]) == 1:
            artifact_id = base_id
        else:
            suffix = sha256_canonical_json(
                {
                    "artifact_role": artifact["artifact_role"],
                    "path": artifact["path"],
                }
            )[:12]
            artifact_id = base_id + "::" + suffix
        artifact_with_id = {"artifact_id": artifact_id}
        artifact_with_id.update(artifact)
        artifacts.append(artifact_with_id)
    return artifacts


def _base_artifact_id(artifact):
    return "artifact::" + artifact["node_id"] + "::" + artifact["artifact_role"]


def _artifact_type(role, path):
    if role in _ROLE_ARTIFACT_TYPES:
        return _ROLE_ARTIFACT_TYPES[role]
    suffix = path.suffix.lower()
    if suffix == ".json":
        return "json"
    if suffix == ".jsonl":
        return "jsonl"
    if suffix in (".md", ".markdown"):
        return "markdown"
    return suffix[1:] if suffix else "file"


def _relative_path(path, output_dir):
    try:
        return (
            Path(path)
            .resolve(strict=False)
            .relative_to(Path(output_dir).resolve(strict=False))
            .as_posix()
        )
    except (OSError, ValueError):
        return None


def _failed_node_artifact_ref(artifact):
    return {
        "artifact_id": artifact["artifact_id"],
        "node_id": artifact["node_id"],
        "artifact_role": artifact["artifact_role"],
        "path": artifact["path"],
        "sha256": artifact["sha256"],
        "size_bytes": artifact["size_bytes"],
        "exists": artifact["exists"],
    }


def _skipped_node_refs(ordered_nodes):
    return [
        {
            "node_id": node["node_id"],
            "blocked_dependencies": list(node.get("blocked_dependencies", [])),
            "status": node["status"],
        }
        for node in ordered_nodes
        if node.get("status") == "skipped"
    ]
