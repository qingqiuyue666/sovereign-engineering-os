"""Central fail-closed runtime admission gate for Personal AI."""

from dataclasses import dataclass, field
from pathlib import Path
import json

from kernel.personal_ai.hash_utils import sha256_file
from kernel.personal_ai.io_utils import write_json_atomically

__all__ = [
    "RuntimeAdmissionDecision",
    "RuntimeAdmissionRequest",
    "RuntimeClassPolicy",
    "build_runtime_class_policies",
    "evaluate_runtime_admission",
    "runtime_policy_for_class",
    "write_runtime_admission_decision",
]

_DECISION_TYPE = "personal_ai_runtime_admission_decision_v1"
_CONFIG_TYPE = "personal_ai_runtime_config_v1"
_APPROVAL_TYPE = "personal_ai_runtime_human_approval_v1"
_MANIFEST_TYPE = "personal_ai_runtime_manifest_v1"
_APPROVED_ACTION = "admit_runtime_execution"

_HUMAN_AUTHORITY_SOURCES = {
    "human_approval_artifact",
    "human_review",
}
_NON_AUTHORITY_SOURCES = {
    "model_output",
    "task_graph",
    "cli_flag",
}
_FORBIDDEN_SECRET_KEYS = {
    "api_key",
    "access_token",
    "authorization",
    "bearer_token",
    "client_secret",
    "cookie",
    "password",
    "refresh_token",
    "secret",
    "token",
}


@dataclass(frozen=True)
class RuntimeClassPolicy:
    runtime_class: str
    activation_allowed_by_default: bool
    dry_run_allowed: bool = True
    real_runtime: bool = False
    network_allowed: bool = False
    subprocess_allowed: bool = False
    browser_control_allowed: bool = False
    model_api_allowed: bool = False
    creative_tool_control_allowed: bool = False
    requires_future_admission: bool = False

    def to_dict(self) -> dict[str, object]:
        return {
            "runtime_class": self.runtime_class,
            "activation_allowed_by_default": self.activation_allowed_by_default,
            "dry_run_allowed": self.dry_run_allowed,
            "real_runtime": self.real_runtime,
            "network_allowed": self.network_allowed,
            "subprocess_allowed": self.subprocess_allowed,
            "browser_control_allowed": self.browser_control_allowed,
            "model_api_allowed": self.model_api_allowed,
            "creative_tool_control_allowed": self.creative_tool_control_allowed,
            "requires_future_admission": self.requires_future_admission,
        }


@dataclass(frozen=True)
class RuntimeAdmissionRequest:
    adapter_id: str = ""
    capability: str = ""
    runtime_class: str = ""
    config_artifact_path: Path | None = None
    human_approval_artifact_path: Path | None = None
    manifest_artifact_path: Path | None = None
    dry_run: bool = True
    activation_sources: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class RuntimeAdmissionDecision:
    decision_type: str
    adapter_id: str
    capability: str
    runtime_class: str
    admitted: bool
    activation_allowed: bool
    dry_run: bool
    reason_codes: tuple[str, ...]
    artifact_hashes: dict[str, str]
    manifest_hash_bound: bool
    runtime_class_policy: dict[str, object]
    activation_sources: tuple[str, ...]
    required_human_approval: bool = True

    def to_dict(self) -> dict[str, object]:
        return {
            "decision_type": self.decision_type,
            "adapter_id": self.adapter_id,
            "capability": self.capability,
            "runtime_class": self.runtime_class,
            "admitted": self.admitted,
            "activation_allowed": self.activation_allowed,
            "dry_run": self.dry_run,
            "reason_codes": list(self.reason_codes),
            "artifact_hashes": {
                key: self.artifact_hashes[key]
                for key in sorted(self.artifact_hashes)
            },
            "manifest_hash_bound": self.manifest_hash_bound,
            "runtime_class_policy": dict(self.runtime_class_policy),
            "activation_sources": list(self.activation_sources),
            "required_human_approval": self.required_human_approval,
            "model_output_can_activate_runtime": False,
            "task_graph_can_activate_runtime": False,
            "cli_flag_can_activate_runtime": False,
            "next_allowed_action": "human_review_runtime_admission_decision",
        }


def build_runtime_class_policies() -> tuple[RuntimeClassPolicy, ...]:
    return (
        RuntimeClassPolicy("readonly", activation_allowed_by_default=True),
        RuntimeClassPolicy(
            "approved_output_write",
            activation_allowed_by_default=True,
        ),
        RuntimeClassPolicy("mock_model", activation_allowed_by_default=True),
        RuntimeClassPolicy("local_fixture", activation_allowed_by_default=True),
        RuntimeClassPolicy(
            "live_model_provider",
            activation_allowed_by_default=False,
            real_runtime=True,
            network_allowed=True,
            model_api_allowed=True,
            requires_future_admission=True,
        ),
        RuntimeClassPolicy(
            "external_browser",
            activation_allowed_by_default=False,
            real_runtime=True,
            network_allowed=True,
            browser_control_allowed=True,
            requires_future_admission=True,
        ),
        RuntimeClassPolicy(
            "comfyui_endpoint",
            activation_allowed_by_default=False,
            real_runtime=True,
            network_allowed=True,
            requires_future_admission=True,
        ),
        RuntimeClassPolicy(
            "blender_runtime",
            activation_allowed_by_default=False,
            real_runtime=True,
            subprocess_allowed=True,
            creative_tool_control_allowed=True,
            requires_future_admission=True,
        ),
        RuntimeClassPolicy(
            "creative_external_tool",
            activation_allowed_by_default=False,
            real_runtime=True,
            subprocess_allowed=True,
            creative_tool_control_allowed=True,
            requires_future_admission=True,
        ),
        RuntimeClassPolicy(
            "unrestricted_network",
            activation_allowed_by_default=False,
            dry_run_allowed=False,
            real_runtime=True,
            network_allowed=True,
            requires_future_admission=True,
        ),
        RuntimeClassPolicy(
            "unrestricted_subprocess",
            activation_allowed_by_default=False,
            dry_run_allowed=False,
            real_runtime=True,
            subprocess_allowed=True,
            requires_future_admission=True,
        ),
    )


def runtime_policy_for_class(runtime_class: str) -> RuntimeClassPolicy:
    for policy in build_runtime_class_policies():
        if policy.runtime_class == runtime_class:
            return policy
    raise ValueError("runtime_class is not registered")


def evaluate_runtime_admission(
    request: RuntimeAdmissionRequest,
) -> RuntimeAdmissionDecision:
    reason_codes: list[str] = []
    artifact_hashes: dict[str, str] = {}

    if not request.adapter_id:
        reason_codes.append("adapter_id_required")
    if not request.capability:
        reason_codes.append("capability_required")
    if not request.runtime_class:
        reason_codes.append("runtime_class_required")

    policy = _policy_or_rejected(request.runtime_class, reason_codes)

    config = _read_required_artifact(
        request.config_artifact_path,
        "config",
        artifact_hashes,
        reason_codes,
    )
    approval = _read_required_artifact(
        request.human_approval_artifact_path,
        "human_approval",
        artifact_hashes,
        reason_codes,
    )
    manifest = _read_required_artifact(
        request.manifest_artifact_path,
        "manifest",
        artifact_hashes,
        reason_codes,
    )

    _validate_activation_sources(request.activation_sources, reason_codes)
    _validate_artifact_shapes(request, config, approval, manifest, reason_codes)
    manifest_hash_bound = _validate_hash_bindings(
        config,
        approval,
        manifest,
        artifact_hashes,
        reason_codes,
    )
    _validate_runtime_class_policy(request, policy, config, reason_codes)
    _reject_secret_material(config, "config", reason_codes)
    _reject_secret_material(approval, "human_approval", reason_codes)
    _reject_secret_material(manifest, "manifest", reason_codes)

    admitted = not reason_codes
    activation_allowed = (
        admitted
        and request.dry_run is False
        and policy.activation_allowed_by_default
    )
    return RuntimeAdmissionDecision(
        decision_type=_DECISION_TYPE,
        adapter_id=request.adapter_id,
        capability=request.capability,
        runtime_class=request.runtime_class,
        admitted=admitted,
        activation_allowed=activation_allowed,
        dry_run=request.dry_run,
        reason_codes=tuple(sorted(set(reason_codes))),
        artifact_hashes=artifact_hashes,
        manifest_hash_bound=manifest_hash_bound,
        runtime_class_policy=policy.to_dict(),
        activation_sources=tuple(request.activation_sources),
        required_human_approval=True,
    )


def write_runtime_admission_decision(
    request: RuntimeAdmissionRequest,
    output_path: Path,
) -> RuntimeAdmissionDecision:
    decision_path = Path(output_path)
    if decision_path.exists():
        raise ValueError("runtime admission decision output already exists")
    if not decision_path.parent.exists() or not decision_path.parent.is_dir():
        raise ValueError("runtime admission decision parent is missing")
    decision = evaluate_runtime_admission(request)
    write_json_atomically(decision_path, decision.to_dict())
    return decision


def _policy_or_rejected(
    runtime_class: str,
    reason_codes: list[str],
) -> RuntimeClassPolicy:
    if not runtime_class:
        return RuntimeClassPolicy("", activation_allowed_by_default=False)
    try:
        return runtime_policy_for_class(runtime_class)
    except ValueError:
        reason_codes.append("runtime_class_not_registered")
        return RuntimeClassPolicy(runtime_class, activation_allowed_by_default=False)


def _read_required_artifact(
    path: Path | None,
    label: str,
    artifact_hashes: dict[str, str],
    reason_codes: list[str],
) -> dict[str, object]:
    if path is None:
        reason_codes.append(label + "_artifact_required")
        return {}
    artifact_path = Path(path)
    if not artifact_path.exists() or not artifact_path.is_file():
        reason_codes.append(label + "_artifact_required")
        return {}
    try:
        payload = json.loads(artifact_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        reason_codes.append(label + "_artifact_malformed")
        return {}
    if not isinstance(payload, dict):
        reason_codes.append(label + "_artifact_malformed")
        return {}
    artifact_hashes[label + "_sha256"] = sha256_file(artifact_path)
    return payload


def _validate_activation_sources(
    activation_sources: tuple[str, ...],
    reason_codes: list[str],
) -> None:
    if not activation_sources:
        reason_codes.append("activation_sources_required")
        return
    if not all(isinstance(source, str) and source for source in activation_sources):
        reason_codes.append("activation_sources_malformed")
        return
    source_set = set(activation_sources)
    if source_set.issubset(_NON_AUTHORITY_SOURCES):
        reason_codes.append("activation_source_lacks_human_approval")
    if source_set.intersection(_NON_AUTHORITY_SOURCES) and not source_set.intersection(
        _HUMAN_AUTHORITY_SOURCES
    ):
        reason_codes.append("model_task_cli_sources_are_not_authority")


def _validate_artifact_shapes(
    request: RuntimeAdmissionRequest,
    config: dict[str, object],
    approval: dict[str, object],
    manifest: dict[str, object],
    reason_codes: list[str],
) -> None:
    _validate_common_artifact_fields(
        request,
        config,
        expected_type=_CONFIG_TYPE,
        type_field="config_type",
        label="config",
        reason_codes=reason_codes,
    )
    _validate_common_artifact_fields(
        request,
        approval,
        expected_type=_APPROVAL_TYPE,
        type_field="approval_type",
        label="human_approval",
        reason_codes=reason_codes,
    )
    _validate_common_artifact_fields(
        request,
        manifest,
        expected_type=_MANIFEST_TYPE,
        type_field="manifest_type",
        label="manifest",
        reason_codes=reason_codes,
    )
    if approval and approval.get("approved_action") != _APPROVED_ACTION:
        reason_codes.append("human_approval_action_mismatch")
    if approval and approval.get("approved") is not True:
        reason_codes.append("human_approval_approved_true_required")
    if approval and approval.get("human_reviewed") is not True:
        reason_codes.append("human_approval_reviewed_true_required")
    if config and config.get("dry_run") is not request.dry_run:
        reason_codes.append("config_dry_run_mismatch")
    if manifest and manifest.get("dry_run") is not request.dry_run:
        reason_codes.append("manifest_dry_run_mismatch")


def _validate_common_artifact_fields(
    request: RuntimeAdmissionRequest,
    payload: dict[str, object],
    *,
    expected_type: str,
    type_field: str,
    label: str,
    reason_codes: list[str],
) -> None:
    if not payload:
        return
    if payload.get(type_field) != expected_type:
        reason_codes.append(label + "_type_mismatch")
    if payload.get("adapter_id") != request.adapter_id:
        reason_codes.append(label + "_adapter_id_mismatch")
    if payload.get("capability") != request.capability:
        reason_codes.append(label + "_capability_mismatch")
    if payload.get("runtime_class") != request.runtime_class:
        reason_codes.append(label + "_runtime_class_mismatch")
    if payload.get("required_human_approval") is not True:
        reason_codes.append(label + "_requires_human_approval")


def _validate_hash_bindings(
    config: dict[str, object],
    approval: dict[str, object],
    manifest: dict[str, object],
    artifact_hashes: dict[str, str],
    reason_codes: list[str],
) -> bool:
    config_hash = artifact_hashes.get("config_sha256")
    manifest_hash = artifact_hashes.get("manifest_sha256")
    if not config_hash or not manifest_hash or not approval:
        reason_codes.append("manifest_hash_binding_missing")
        return False

    hash_binding_ok = True
    if approval.get("config_sha256") != config_hash:
        reason_codes.append("human_approval_config_hash_mismatch")
        hash_binding_ok = False
    if approval.get("manifest_sha256") != manifest_hash:
        reason_codes.append("human_approval_manifest_hash_mismatch")
        hash_binding_ok = False
    if manifest.get("config_sha256") != config_hash:
        reason_codes.append("manifest_config_hash_mismatch")
        hash_binding_ok = False
    return hash_binding_ok


def _validate_runtime_class_policy(
    request: RuntimeAdmissionRequest,
    policy: RuntimeClassPolicy,
    config: dict[str, object],
    reason_codes: list[str],
) -> None:
    if request.dry_run and not policy.dry_run_allowed:
        reason_codes.append("runtime_class_dry_run_not_allowed")
    if not request.dry_run and not policy.activation_allowed_by_default:
        reason_codes.append("runtime_class_not_activation_admitted")
    if policy.real_runtime and config.get("real_runtime_enabled") is True:
        reason_codes.append("real_runtime_activation_deferred")
    if config and config.get("runtime_class_policy") not in (None, policy.to_dict()):
        reason_codes.append("config_runtime_class_policy_mismatch")


def _reject_secret_material(
    payload: dict[str, object],
    label: str,
    reason_codes: list[str],
) -> None:
    if _contains_forbidden_secret_key(payload):
        reason_codes.append(label + "_contains_secret_material")


def _contains_forbidden_secret_key(value: object) -> bool:
    if isinstance(value, dict):
        for key, item in value.items():
            if str(key).lower() in _FORBIDDEN_SECRET_KEYS:
                return True
            if _contains_forbidden_secret_key(item):
                return True
    if isinstance(value, list):
        return any(_contains_forbidden_secret_key(item) for item in value)
    return False
