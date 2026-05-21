"""Deterministic adapter registry for Personal AI Execution OS v2."""

from kernel.personal_ai.adapters.adapter_contract import (
    AdapterAdmissionDecision,
    AdapterAdmissionStatus,
    AdapterCapabilityRequest,
    AdapterExecutionBoundary,
    AdapterMode,
    AdapterOutputPolicy,
    AdapterRegistryEntry,
    AdapterRiskClass,
)

__all__ = [
    "DEFAULT_ADAPTER_REGISTRY",
    "admit_adapter_capability",
    "build_default_adapter_registry",
    "find_adapter_entry",
    "validate_adapter_registry_entry",
]

_REQUIRED_CONTROLS = (
    "human_approval",
    "capability_token",
    "manifest",
    "evidence_capture",
    "quarantine",
    "output_hashing",
)


def _approved_output_boundary() -> AdapterExecutionBoundary:
    return AdapterExecutionBoundary(output_write_allowed=True)


def _approved_output_policy() -> AdapterOutputPolicy:
    return AdapterOutputPolicy(output_write_allowed=True)


def build_default_adapter_registry() -> tuple[AdapterRegistryEntry, ...]:
    return (
        AdapterRegistryEntry(
            adapter_id="xlsx_readonly_runtime",
            adapter_name="XLSX Readonly Runtime",
            mode=AdapterMode.READONLY,
            risk_class=AdapterRiskClass.LOCAL_READONLY,
            admission_status=AdapterAdmissionStatus.ADMITTED,
            capabilities=("inspect_local_xlsx_metadata",),
            required_controls=_REQUIRED_CONTROLS,
            notes="Local workbook metadata inspection only.",
        ),
        AdapterRegistryEntry(
            adapter_id="xlsx_output_writer",
            adapter_name="Approved XLSX Output Writer",
            mode=AdapterMode.APPROVED_WRITE,
            risk_class=AdapterRiskClass.APPROVED_OUTPUT_WRITE,
            admission_status=AdapterAdmissionStatus.ADMITTED,
            capabilities=("create_metadata_summary_workbook",),
            required_controls=_REQUIRED_CONTROLS
            + (
                "approval_hash_binding",
                "input_hash_binding",
                "plan_hash_binding",
            ),
            boundary=_approved_output_boundary(),
            output_policy=_approved_output_policy(),
            notes="Creates new output workbooks only after hash-bound approval.",
        ),
        AdapterRegistryEntry(
            adapter_id="mock_model_typed_schema_runtime",
            adapter_name="Mock Model Typed Schema Runtime",
            mode=AdapterMode.MOCK_RUNTIME,
            risk_class=AdapterRiskClass.MOCK_MODEL,
            admission_status=AdapterAdmissionStatus.ADMITTED,
            capabilities=("classify_local_job_package", "summarize_profile"),
            required_controls=_REQUIRED_CONTROLS + ("schema_validation",),
            notes="Deterministic local mock provider; no live model access.",
        ),
        AdapterRegistryEntry(
            adapter_id="live_model_provider_boundary",
            adapter_name="Live Model Provider Boundary",
            mode=AdapterMode.FUTURE_EXTERNAL,
            risk_class=AdapterRiskClass.LIVE_MODEL_PROVIDER,
            admission_status=AdapterAdmissionStatus.DEFERRED,
            capabilities=("call_typed_schema_provider",),
            required_controls=_REQUIRED_CONTROLS
            + (
                "environment_only_api_key",
                "budget_gate",
                "timeout_policy",
                "schema_validation",
                "future_admission",
            ),
            boundary=AdapterExecutionBoundary(network_allowed=True),
            notes="Disabled-by-default live provider boundary; no real calls admitted.",
        ),
        AdapterRegistryEntry(
            adapter_id="browser_fixture_runtime",
            adapter_name="Browser Local Fixture Runtime",
            mode=AdapterMode.LOCAL_FIXTURE,
            risk_class=AdapterRiskClass.LOCAL_BROWSER_FIXTURE,
            admission_status=AdapterAdmissionStatus.ADMITTED,
            capabilities=("open_local_fixture", "inspect_fixture"),
            required_controls=_REQUIRED_CONTROLS + ("local_fixture_only",),
            notes="Local HTML fixture interpretation only; no external URLs.",
        ),
        AdapterRegistryEntry(
            adapter_id="local_asset_runtime",
            adapter_name="Local Asset Scan Controlled Launcher",
            mode=AdapterMode.LOCAL_FIXTURE,
            risk_class=AdapterRiskClass.LOCAL_READONLY,
            admission_status=AdapterAdmissionStatus.ADMITTED,
            capabilities=("launch_local_asset_scan",),
            required_controls=_REQUIRED_CONTROLS
            + (
                "read_only_input",
                "artifact_index_binding",
                "operational_receipt",
                "failure_bundle",
                "no_external_runtime",
            ),
            boundary=_approved_output_boundary(),
            output_policy=_approved_output_policy(),
            notes=(
                "Runs the controlled local asset scan launcher in fixture task "
                "graphs; writes approved output artifacts only and never mutates "
                "input assets."
            ),
        ),
        AdapterRegistryEntry(
            adapter_id="real_browser_runtime_boundary",
            adapter_name="Real Browser Runtime Boundary",
            mode=AdapterMode.FUTURE_EXTERNAL,
            risk_class=AdapterRiskClass.EXTERNAL_BROWSER,
            admission_status=AdapterAdmissionStatus.DEFERRED,
            capabilities=("drive_real_browser_with_allowlist",),
            required_controls=_REQUIRED_CONTROLS
            + (
                "domain_allowlist",
                "network_disabled_by_default",
                "form_submit_approval_gate",
                "no_credential_storage",
                "future_admission",
            ),
            boundary=AdapterExecutionBoundary(
                network_allowed=True,
                external_tool_control_allowed=True,
            ),
            notes="Disabled-by-default real browser boundary; no Playwright/Selenium runtime admitted.",
        ),
        AdapterRegistryEntry(
            adapter_id="comfyui_controlled_fixture_runtime",
            adapter_name="ComfyUI Workflow Fixture Runtime",
            mode=AdapterMode.LOCAL_FIXTURE,
            risk_class=AdapterRiskClass.LOCAL_CREATIVE_FIXTURE,
            admission_status=AdapterAdmissionStatus.ADMITTED,
            capabilities=("validate_comfyui_workflow_fixture",),
            required_controls=_REQUIRED_CONTROLS
            + (
                "workflow_validation",
                "node_allowlist",
                "input_asset_hash_binding",
                "no_external_downloads",
            ),
            notes="Validates local ComfyUI workflow fixtures only; no endpoint call.",
        ),
        AdapterRegistryEntry(
            adapter_id="comfyui_local_endpoint_boundary",
            adapter_name="ComfyUI Loopback Endpoint Boundary",
            mode=AdapterMode.FUTURE_EXTERNAL,
            risk_class=AdapterRiskClass.NETWORK_TOOL,
            admission_status=AdapterAdmissionStatus.DEFERRED,
            capabilities=("submit_comfyui_workflow_to_loopback_endpoint",),
            required_controls=_REQUIRED_CONTROLS
            + (
                "loopback_endpoint_only",
                "workflow_validation",
                "node_allowlist",
                "input_asset_hash_binding",
                "no_external_downloads",
                "future_admission",
            ),
            boundary=AdapterExecutionBoundary(network_allowed=True),
            notes="Disabled-by-default ComfyUI endpoint boundary; dry-run only until explicit admission.",
        ),
        AdapterRegistryEntry(
            adapter_id="blender_controlled_fixture_runtime",
            adapter_name="Blender Operation Plan Fixture Runtime",
            mode=AdapterMode.LOCAL_FIXTURE,
            risk_class=AdapterRiskClass.LOCAL_CREATIVE_FIXTURE,
            admission_status=AdapterAdmissionStatus.ADMITTED,
            capabilities=("validate_blender_operation_plan_fixture",),
            required_controls=_REQUIRED_CONTROLS
            + (
                "operation_allowlist",
                "scene_hash_binding",
                "source_asset_overwrite_forbidden",
                "no_arbitrary_python",
            ),
            notes="Validates local Blender operation plans only; no Blender launch.",
        ),
        AdapterRegistryEntry(
            adapter_id="blender_real_runtime_boundary",
            adapter_name="Blender Real Runtime Boundary",
            mode=AdapterMode.FUTURE_EXTERNAL,
            risk_class=AdapterRiskClass.CREATIVE_EXTERNAL_TOOL,
            admission_status=AdapterAdmissionStatus.DEFERRED,
            capabilities=("execute_blender_operation_plan",),
            required_controls=_REQUIRED_CONTROLS
            + (
                "operation_allowlist",
                "scene_hash_binding",
                "source_asset_overwrite_forbidden",
                "no_arbitrary_python",
                "future_admission",
            ),
            boundary=AdapterExecutionBoundary(
                subprocess_allowed=True,
                external_tool_control_allowed=True,
            ),
            notes="Disabled-by-default Blender runtime boundary; no subprocess launch admitted.",
        ),
        AdapterRegistryEntry(
            adapter_id="creative_handoff_package",
            adapter_name="Creative Handoff Package Builder",
            mode=AdapterMode.APPROVED_WRITE,
            risk_class=AdapterRiskClass.APPROVED_OUTPUT_WRITE,
            admission_status=AdapterAdmissionStatus.ADMITTED,
            capabilities=("build_handoff_package",),
            required_controls=_REQUIRED_CONTROLS
            + (
                "source_asset_hash_binding",
                "output_target_policy",
                "source_asset_overwrite_forbidden",
                "human_execution_instructions",
            ),
            boundary=_approved_output_boundary(),
            output_policy=_approved_output_policy(),
            notes="Builds metadata-only human handoff packages; no external tool control.",
        ),
        AdapterRegistryEntry(
            adapter_id="creative_adapter_policy",
            adapter_name="Creative Adapter Policy Foundation",
            mode=AdapterMode.POLICY_ONLY,
            risk_class=AdapterRiskClass.CREATIVE_EXTERNAL_TOOL,
            admission_status=AdapterAdmissionStatus.DEFERRED,
            capabilities=("record_future_creative_controls",),
            required_controls=_REQUIRED_CONTROLS
            + (
                "future_admission",
                "explicit_adapter_admission",
                "operation_allowlist",
                "source_asset_overwrite_forbidden",
                "preview_render_evidence",
            ),
            boundary=AdapterExecutionBoundary(external_tool_control_allowed=True),
            notes="Policy only; no creative software runtime admitted.",
        ),
    )


DEFAULT_ADAPTER_REGISTRY = build_default_adapter_registry()


def validate_adapter_registry_entry(entry: AdapterRegistryEntry) -> tuple[str, ...]:
    failures = []
    if not entry.adapter_id:
        failures.append("adapter_id_missing")
    if not entry.adapter_name:
        failures.append("adapter_name_missing")
    if not entry.capabilities:
        failures.append("capabilities_missing")
    missing_controls = [
        control
        for control in _REQUIRED_CONTROLS
        if control not in entry.required_controls
    ]
    if missing_controls:
        failures.append("required_controls_missing")
    if (
        entry.admission_status == AdapterAdmissionStatus.ADMITTED
        and not entry.boundary.is_runtime_safe_for_current_branch()
    ):
        failures.append("admitted_boundary_is_not_safe")
    if (
        entry.boundary.output_write_allowed
        and not entry.boundary.rejects_unapproved_output_write()
    ):
        failures.append("output_write_controls_missing")
    if (
        entry.boundary.requires_explicit_future_admission()
        and entry.admission_status == AdapterAdmissionStatus.ADMITTED
        and entry.risk_class
        not in (
            AdapterRiskClass.APPROVED_OUTPUT_WRITE,
            AdapterRiskClass.LOCAL_BROWSER_FIXTURE,
        )
    ):
        failures.append("future_admission_required")
    return tuple(sorted(failures))


def find_adapter_entry(
    adapter_id: str,
    registry: tuple[AdapterRegistryEntry, ...] = DEFAULT_ADAPTER_REGISTRY,
) -> AdapterRegistryEntry:
    for entry in registry:
        if entry.adapter_id == adapter_id:
            return entry
    raise ValueError("adapter_id is not registered")


def admit_adapter_capability(
    request: AdapterCapabilityRequest,
    registry: tuple[AdapterRegistryEntry, ...] = DEFAULT_ADAPTER_REGISTRY,
) -> AdapterAdmissionDecision:
    entry = find_adapter_entry(request.adapter_id, registry)
    entry_failures = validate_adapter_registry_entry(entry)
    reason_codes = list(entry_failures)

    if request.capability not in entry.capabilities:
        reason_codes.append("capability_not_registered")
    if request.mode != entry.mode:
        reason_codes.append("adapter_mode_mismatch")
    if request.risk_class != entry.risk_class:
        reason_codes.append("risk_class_mismatch")
    if not request.boundary.is_runtime_safe_for_current_branch():
        reason_codes.append("request_boundary_is_not_safe")
    if entry.admission_status != AdapterAdmissionStatus.ADMITTED:
        reason_codes.append("adapter_not_admitted")

    admitted = not reason_codes
    status = (
        AdapterAdmissionStatus.ADMITTED
        if admitted
        else AdapterAdmissionStatus.REJECTED
    )
    return AdapterAdmissionDecision(
        adapter_id=request.adapter_id,
        capability=request.capability,
        admission_status=status,
        admitted=admitted,
        reason_codes=tuple(sorted(reason_codes)),
        boundary=entry.boundary,
        evidence_requirement=entry.evidence_requirement,
        quarantine_policy=entry.quarantine_policy,
        output_policy=entry.output_policy,
    )
