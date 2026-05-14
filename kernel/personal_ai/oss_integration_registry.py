"""Static OSS integration registry for Personal AI Local v1."""

from pathlib import Path
from copy import deepcopy

from kernel.personal_ai.io_utils import write_json_atomically

__all__ = [
    "get_oss_integration_registry",
    "list_oss_integrations",
    "write_oss_integration_registry",
]

_REGISTRY_TYPE = "personal_ai_local_v1_oss_integration_registry"

_BOUNDARIES = {
    "local_only": True,
    "no_runtime_authority": True,
    "no_execution_capability": True,
    "no_external_tool_control": True,
    "no_network": True,
    "no_api_calls": True,
    "no_subprocess": True,
    "no_adapter_implementation": True,
    "no_dynamic_plugin_loading": True,
    "no_input_file_mutation": True,
    "no_raw_cell_value_copy": True,
    "no_spreadsheet_output_write": True,
}

_INTEGRATIONS = [
    {
        "repository": "python-jsonschema/jsonschema",
        "url": "https://github.com/python-jsonschema/jsonschema",
        "license": "MIT",
        "status": "active",
        "integration_type": "design_inspired_local_implementation",
        "local_capability": "job_package_validator",
        "dependency_added": False,
        "dynamic_loading": False,
        "external_tool_control": False,
    },
    {
        "repository": "frictionlessdata/frictionless-py",
        "url": "https://github.com/frictionlessdata/frictionless-py",
        "license": "MIT",
        "status": "active",
        "integration_type": "design_inspired_local_implementation",
        "local_capability": "package_completeness_report",
        "dependency_added": False,
        "dynamic_loading": False,
        "external_tool_control": False,
    },
    {
        "repository": "simonw/sqlite-utils",
        "url": "https://github.com/simonw/sqlite-utils",
        "license": "Apache-2.0",
        "status": "active",
        "integration_type": "design_inspired_local_implementation",
        "local_capability": "artifact_index",
        "dependency_added": False,
        "dynamic_loading": False,
        "external_tool_control": False,
    },
    {
        "repository": "syrupy-project/syrupy",
        "url": "https://github.com/syrupy-project/syrupy",
        "license": "MIT",
        "status": "active",
        "integration_type": "design_inspired_local_implementation",
        "local_capability": "snapshot_normalization",
        "dependency_added": False,
        "dynamic_loading": False,
        "external_tool_control": False,
    },
    {
        "repository": "Textualize/rich",
        "url": "https://github.com/Textualize/rich",
        "license": "MIT",
        "status": "active",
        "integration_type": "design_inspired_local_implementation",
        "local_capability": "safe_cli_result_contracts",
        "dependency_added": False,
        "dynamic_loading": False,
        "external_tool_control": False,
    },
    {
        "repository": "pallets/click",
        "url": "https://github.com/pallets/click",
        "license": "BSD-3-Clause",
        "status": "active",
        "integration_type": "design_inspired_local_implementation",
        "local_capability": "safe_cli_subcommands",
        "dependency_added": False,
        "dynamic_loading": False,
        "external_tool_control": False,
    },
    {
        "repository": "CycloneDX/cyclonedx-python-lib",
        "url": "https://github.com/CycloneDX/cyclonedx-python-lib",
        "license": "Apache-2.0",
        "status": "active",
        "integration_type": "design_inspired_local_implementation",
        "local_capability": "oss_integration_registry",
        "dependency_added": False,
        "dynamic_loading": False,
        "external_tool_control": False,
    },
    {
        "repository": "duckdb/duckdb",
        "url": "https://github.com/duckdb/duckdb",
        "license": "MIT",
        "status": "optional",
        "integration_type": "future_optional_dependency",
        "local_capability": "embedded_local_analytics",
        "dependency_added": False,
        "dynamic_loading": False,
        "external_tool_control": False,
    },
    {
        "repository": "microsoft/markitdown",
        "url": "https://github.com/microsoft/markitdown",
        "license": "MIT",
        "status": "optional",
        "integration_type": "future_optional_dependency",
        "local_capability": "document_metadata_extraction",
        "dependency_added": False,
        "dynamic_loading": False,
        "external_tool_control": False,
    },
    {
        "repository": "anchore/syft",
        "url": "https://github.com/anchore/syft",
        "license": "Apache-2.0",
        "status": "design_only",
        "integration_type": "design_inspiration_only",
        "local_capability": "local_package_inspection",
        "dependency_added": False,
        "dynamic_loading": False,
        "external_tool_control": False,
    },
    {
        "repository": "pymupdf/PyMuPDF",
        "url": "https://github.com/pymupdf/PyMuPDF",
        "license": "AGPL-3.0",
        "status": "rejected",
        "integration_type": "rejected",
        "local_capability": "document_processing",
        "dependency_added": False,
        "rejection_reason": "AGPL license is outside this sprint policy.",
        "dynamic_loading": False,
        "external_tool_control": False,
    },
    {
        "repository": "PrefectHQ/prefect",
        "url": "https://github.com/PrefectHQ/prefect",
        "license": "Apache-2.0",
        "status": "rejected",
        "integration_type": "rejected",
        "local_capability": "workflow_orchestration",
        "dependency_added": False,
        "rejection_reason": "Workflow runtime authority is outside this sprint boundary.",
        "dynamic_loading": False,
        "external_tool_control": False,
    },
]


def list_oss_integrations() -> list[dict[str, object]]:
    return deepcopy(_INTEGRATIONS)


def get_oss_integration_registry() -> dict[str, object]:
    integrations = list_oss_integrations()
    return {
        "registry_type": _REGISTRY_TYPE,
        "authority": "non_authority",
        "execution_capability": "not_introduced",
        "dependency_loading": "none",
        "dynamic_plugin_loading": False,
        "external_tool_control": False,
        "network_required": False,
        "integrations": integrations,
        "counts": _counts(integrations),
        "boundaries": dict(_BOUNDARIES),
        "next_allowed_action": "human_review_only",
    }


def write_oss_integration_registry(output_path: Path) -> dict[str, object]:
    output_file = Path(output_path)
    if not output_file.parent.exists() or not output_file.parent.is_dir():
        raise ValueError("output_path parent is missing")
    registry = get_oss_integration_registry()
    write_json_atomically(output_file, registry)
    return registry


def _counts(integrations):
    statuses = {
        "active": 0,
        "optional": 0,
        "design_only": 0,
        "rejected": 0,
    }
    for integration in integrations:
        status = integration["status"]
        if status in statuses:
            statuses[status] += 1
    statuses["total"] = len(integrations)
    return statuses
