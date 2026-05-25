"""Contract-only foundation for future local domain adapters.

The foundation describes future adapter state, operation, asset, output,
provenance, replay, and admission contracts. It does not launch tools, inspect
live projects, mutate source assets, or authorize runtime execution.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping
import re

from kernel.audit.hashchain import digest_payload

__all__ = [
    "AdapterAdmissionRules",
    "AssetHashBinding",
    "DomainAdapterContract",
    "DomainAdapterFamily",
    "DomainOperationClass",
    "OperationPlanDescriptor",
    "OutputManifestContract",
    "ProvenancePolicy",
    "ReplayPolicy",
    "StateProxyDescriptor",
    "build_default_domain_adapter_contracts",
    "build_domain_adapter_contract",
    "validate_asset_hash_binding",
    "validate_domain_adapter_contract",
]

_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_DEFAULT_DIGEST = "sha256:" + ("0" * 64)


class DomainAdapterFamily:
    """Known adapter families covered by the contract foundation."""

    COMFYUI = "comfyui"
    HOUDINI = "houdini"
    BLENDER = "blender"
    UNREAL = "unreal"
    DAVINCI_RESOLVE = "davinci_resolve"
    AFTER_EFFECTS = "after_effects"
    GENERIC_LOCAL = "generic_local"

    @classmethod
    def all(cls) -> tuple[str, ...]:
        return (
            cls.COMFYUI,
            cls.HOUDINI,
            cls.BLENDER,
            cls.UNREAL,
            cls.DAVINCI_RESOLVE,
            cls.AFTER_EFFECTS,
            cls.GENERIC_LOCAL,
        )


class DomainOperationClass:
    """Operation classes are declarative and non-executing."""

    READ_STATE_PROXY = "read_state_proxy"
    VALIDATE_OPERATION_PLAN = "validate_operation_plan"
    BIND_ASSET_HASHES = "bind_asset_hashes"
    DECLARE_OUTPUT_MANIFEST = "declare_output_manifest"
    RECORD_PROVENANCE = "record_provenance"
    PREPARE_REPLAY = "prepare_replay"

    @classmethod
    def all(cls) -> tuple[str, ...]:
        return (
            cls.READ_STATE_PROXY,
            cls.VALIDATE_OPERATION_PLAN,
            cls.BIND_ASSET_HASHES,
            cls.DECLARE_OUTPUT_MANIFEST,
            cls.RECORD_PROVENANCE,
            cls.PREPARE_REPLAY,
        )


@dataclass(frozen=True)
class AssetHashBinding:
    """Digest-only reference to an input, source, or output asset."""

    asset_id: str
    asset_role: str
    digest: str
    asset_ref: str = ""
    source_mutation_allowed: bool = False
    source_overwrite_allowed: bool = False

    def to_dict(self) -> dict[str, object]:
        return {
            "asset_id": self.asset_id,
            "asset_ref": self.asset_ref,
            "asset_role": self.asset_role,
            "digest": self.digest,
            "source_mutation_allowed": self.source_mutation_allowed,
            "source_overwrite_allowed": self.source_overwrite_allowed,
        }


@dataclass(frozen=True)
class StateProxyDescriptor:
    """Read-only state summary descriptor for a future local adapter."""

    proxy_id: str
    adapter_family: str
    asset_bindings: tuple[AssetHashBinding, ...]
    observed_state_digest: str
    allowed_observation_classes: tuple[str, ...] = (
        "asset_reference_summary",
        "metadata_summary",
        "state_graph_summary",
    )
    raw_state_persistence_allowed: bool = False
    live_process_access_allowed: bool = False
    network_access_allowed: bool = False

    def to_dict(self) -> dict[str, object]:
        return {
            "adapter_family": self.adapter_family,
            "allowed_observation_classes": list(self.allowed_observation_classes),
            "asset_bindings": [binding.to_dict() for binding in self.asset_bindings],
            "live_process_access_allowed": self.live_process_access_allowed,
            "network_access_allowed": self.network_access_allowed,
            "observed_state_digest": self.observed_state_digest,
            "proxy_id": self.proxy_id,
            "raw_state_persistence_allowed": self.raw_state_persistence_allowed,
        }


@dataclass(frozen=True)
class OperationPlanDescriptor:
    """Declarative plan for a future local adapter operation."""

    plan_id: str
    adapter_family: str
    operation_class: str
    operation_name: str
    input_asset_bindings: tuple[AssetHashBinding, ...]
    planned_output_refs: tuple[str, ...]
    operation_steps: tuple[str, ...]
    requires_human_approval: bool = True
    requires_capability_token: bool = True
    live_execution_allowed: bool = False
    process_launch_allowed: bool = False
    network_access_allowed: bool = False
    source_asset_overwrite_allowed: bool = False
    arbitrary_command_allowed: bool = False
    arbitrary_python_allowed: bool = False

    def deterministic_material(self) -> dict[str, object]:
        return {
            "adapter_family": self.adapter_family,
            "arbitrary_command_allowed": self.arbitrary_command_allowed,
            "arbitrary_python_allowed": self.arbitrary_python_allowed,
            "input_asset_bindings": [
                binding.to_dict() for binding in self.input_asset_bindings
            ],
            "live_execution_allowed": self.live_execution_allowed,
            "network_access_allowed": self.network_access_allowed,
            "operation_class": self.operation_class,
            "operation_name": self.operation_name,
            "operation_steps": list(self.operation_steps),
            "plan_id": self.plan_id,
            "planned_output_refs": list(self.planned_output_refs),
            "process_launch_allowed": self.process_launch_allowed,
            "requires_capability_token": self.requires_capability_token,
            "requires_human_approval": self.requires_human_approval,
            "source_asset_overwrite_allowed": self.source_asset_overwrite_allowed,
        }

    def content_hash(self) -> str:
        return digest_payload(self.deterministic_material())

    def to_dict(self) -> dict[str, object]:
        payload = self.deterministic_material()
        payload["content_hash"] = self.content_hash()
        return payload


@dataclass(frozen=True)
class OutputManifestContract:
    """Hash-bound output contract for future adapter artifacts."""

    manifest_id: str
    plan_id: str
    output_asset_bindings: tuple[AssetHashBinding, ...]
    output_directory_policy: str = "new_artifact_directory_only"
    output_manifest_required: bool = True
    output_hashing_required: bool = True
    source_asset_overwrite_allowed: bool = False
    existing_output_overwrite_allowed: bool = False
    raw_payload_storage_allowed: bool = False

    def to_dict(self) -> dict[str, object]:
        return {
            "existing_output_overwrite_allowed": (
                self.existing_output_overwrite_allowed
            ),
            "manifest_id": self.manifest_id,
            "output_asset_bindings": [
                binding.to_dict() for binding in self.output_asset_bindings
            ],
            "output_directory_policy": self.output_directory_policy,
            "output_hashing_required": self.output_hashing_required,
            "output_manifest_required": self.output_manifest_required,
            "plan_id": self.plan_id,
            "raw_payload_storage_allowed": self.raw_payload_storage_allowed,
            "source_asset_overwrite_allowed": self.source_asset_overwrite_allowed,
        }


@dataclass(frozen=True)
class ProvenancePolicy:
    """Required provenance evidence for future adapter admission."""

    source_asset_hashes_required: bool = True
    operation_plan_hash_required: bool = True
    output_manifest_required: bool = True
    adapter_version_required: bool = True
    human_approval_ref_required: bool = True
    no_raw_secret_display_required: bool = True

    def to_dict(self) -> dict[str, object]:
        return _dataclass_dict(self)


@dataclass(frozen=True)
class ReplayPolicy:
    """Replay requirements without automatic re-execution."""

    replay_descriptor_required: bool = True
    command_or_operation_id_match_required: bool = True
    asset_digest_match_required: bool = True
    environment_digest_required: bool = True
    output_digest_comparison_required: bool = True
    automatic_reexecution_allowed: bool = False

    def to_dict(self) -> dict[str, object]:
        return _dataclass_dict(self)


@dataclass(frozen=True)
class AdapterAdmissionRules:
    """Admission rules shared by future domain adapters."""

    admission_status: str = "candidate"
    runtime_admitted: bool = False
    live_dcc_execution_allowed: bool = False
    process_launch_allowed: bool = False
    network_access_allowed: bool = False
    source_asset_overwrite_allowed: bool = False
    explicit_future_admission_required: bool = True
    human_approval_required: bool = True
    capability_token_required: bool = True
    output_manifest_required: bool = True
    provenance_required: bool = True
    replay_policy_required: bool = True

    def to_dict(self) -> dict[str, object]:
        return _dataclass_dict(self)


@dataclass(frozen=True)
class DomainAdapterContract:
    """Complete contract bundle for one domain adapter family."""

    adapter_id: str
    adapter_family: str
    state_proxy: StateProxyDescriptor
    operation_plan: OperationPlanDescriptor
    output_manifest: OutputManifestContract
    provenance_policy: ProvenancePolicy = field(default_factory=ProvenancePolicy)
    replay_policy: ReplayPolicy = field(default_factory=ReplayPolicy)
    admission_rules: AdapterAdmissionRules = field(default_factory=AdapterAdmissionRules)

    def to_dict(self) -> dict[str, object]:
        return {
            "adapter_family": self.adapter_family,
            "adapter_id": self.adapter_id,
            "admission_rules": self.admission_rules.to_dict(),
            "operation_plan": self.operation_plan.to_dict(),
            "output_manifest": self.output_manifest.to_dict(),
            "provenance_policy": self.provenance_policy.to_dict(),
            "replay_policy": self.replay_policy.to_dict(),
            "state_proxy": self.state_proxy.to_dict(),
        }


def build_domain_adapter_contract(family: str) -> DomainAdapterContract:
    """Build a deterministic contract-only adapter descriptor for a family."""

    if family not in DomainAdapterFamily.all():
        raise ValueError("domain_adapter_family_unknown")
    input_binding = AssetHashBinding(
        asset_id=f"{family}-source-asset",
        asset_role="source",
        asset_ref=f"{family}:source",
        digest=_DEFAULT_DIGEST,
    )
    output_binding = AssetHashBinding(
        asset_id=f"{family}-planned-output",
        asset_role="planned_output",
        asset_ref=f"{family}:planned-output",
        digest=_DEFAULT_DIGEST,
    )
    operation_plan = OperationPlanDescriptor(
        plan_id=f"{family}-operation-plan-v1",
        adapter_family=family,
        operation_class=DomainOperationClass.VALIDATE_OPERATION_PLAN,
        operation_name="validate_descriptor_only",
        input_asset_bindings=(input_binding,),
        planned_output_refs=(output_binding.asset_ref,),
        operation_steps=(
            "validate state proxy descriptor",
            "bind input asset digests",
            "declare output manifest contract",
            "record provenance and replay requirements",
        ),
    )
    return DomainAdapterContract(
        adapter_id=f"{family}-domain-adapter-contract-v1",
        adapter_family=family,
        state_proxy=StateProxyDescriptor(
            proxy_id=f"{family}-state-proxy-v1",
            adapter_family=family,
            asset_bindings=(input_binding,),
            observed_state_digest=_DEFAULT_DIGEST,
        ),
        operation_plan=operation_plan,
        output_manifest=OutputManifestContract(
            manifest_id=f"{family}-output-manifest-contract-v1",
            plan_id=operation_plan.plan_id,
            output_asset_bindings=(output_binding,),
        ),
    )


def build_default_domain_adapter_contracts() -> tuple[DomainAdapterContract, ...]:
    return tuple(
        build_domain_adapter_contract(family)
        for family in DomainAdapterFamily.all()
    )


def validate_asset_hash_binding(binding: AssetHashBinding) -> tuple[str, ...]:
    failures: list[str] = []
    if not isinstance(binding, AssetHashBinding):
        return ("asset_hash_binding_must_be_typed",)
    if not binding.asset_id:
        failures.append("asset_id_required")
    if not binding.asset_role:
        failures.append("asset_role_required")
    if not _valid_digest(binding.digest):
        failures.append("asset_digest_must_be_sha256")
    if binding.source_mutation_allowed:
        failures.append("source_mutation_forbidden")
    if binding.source_overwrite_allowed:
        failures.append("source_overwrite_forbidden")
    return tuple(sorted(set(failures)))


def validate_domain_adapter_contract(
    contract: DomainAdapterContract,
) -> tuple[str, ...]:
    """Validate a domain adapter contract without running any adapter."""

    if not isinstance(contract, DomainAdapterContract):
        return ("domain_adapter_contract_must_be_typed",)
    failures: list[str] = []
    failures.extend(_validate_contract_identity(contract))
    failures.extend(_validate_state_proxy(contract.state_proxy, contract.adapter_family))
    failures.extend(_validate_operation_plan(contract.operation_plan, contract.adapter_family))
    failures.extend(_validate_output_manifest(contract.output_manifest, contract.operation_plan.plan_id))
    failures.extend(_validate_provenance_policy(contract.provenance_policy))
    failures.extend(_validate_replay_policy(contract.replay_policy))
    failures.extend(_validate_admission_rules(contract.admission_rules))
    return tuple(sorted(set(failures)))


def _validate_contract_identity(contract: DomainAdapterContract) -> tuple[str, ...]:
    failures: list[str] = []
    if not contract.adapter_id:
        failures.append("adapter_id_required")
    if contract.adapter_family not in DomainAdapterFamily.all():
        failures.append("adapter_family_unknown")
    return tuple(failures)


def _validate_state_proxy(
    proxy: StateProxyDescriptor,
    expected_family: str,
) -> tuple[str, ...]:
    failures: list[str] = []
    if not proxy.proxy_id:
        failures.append("state_proxy_id_required")
    if proxy.adapter_family != expected_family:
        failures.append("state_proxy_family_mismatch")
    if not proxy.asset_bindings:
        failures.append("state_proxy_asset_bindings_required")
    for binding in proxy.asset_bindings:
        failures.extend(validate_asset_hash_binding(binding))
    if not _valid_digest(proxy.observed_state_digest):
        failures.append("observed_state_digest_must_be_sha256")
    if not proxy.allowed_observation_classes:
        failures.append("allowed_observation_classes_required")
    if proxy.raw_state_persistence_allowed:
        failures.append("raw_state_persistence_forbidden")
    if proxy.live_process_access_allowed:
        failures.append("live_process_access_forbidden")
    if proxy.network_access_allowed:
        failures.append("state_proxy_network_forbidden")
    return tuple(failures)


def _validate_operation_plan(
    plan: OperationPlanDescriptor,
    expected_family: str,
) -> tuple[str, ...]:
    failures: list[str] = []
    if not plan.plan_id:
        failures.append("operation_plan_id_required")
    if plan.adapter_family != expected_family:
        failures.append("operation_plan_family_mismatch")
    if plan.operation_class not in DomainOperationClass.all():
        failures.append("operation_class_unknown")
    if not plan.operation_name:
        failures.append("operation_name_required")
    if not plan.input_asset_bindings:
        failures.append("operation_input_asset_bindings_required")
    for binding in plan.input_asset_bindings:
        failures.extend(validate_asset_hash_binding(binding))
    if not plan.planned_output_refs:
        failures.append("planned_output_refs_required")
    if not plan.operation_steps:
        failures.append("operation_steps_required")
    if not plan.requires_human_approval:
        failures.append("human_approval_required")
    if not plan.requires_capability_token:
        failures.append("capability_token_required")
    if plan.live_execution_allowed:
        failures.append("live_execution_forbidden")
    if plan.process_launch_allowed:
        failures.append("process_launch_forbidden")
    if plan.network_access_allowed:
        failures.append("operation_network_forbidden")
    if plan.source_asset_overwrite_allowed:
        failures.append("source_asset_overwrite_forbidden")
    if plan.arbitrary_command_allowed:
        failures.append("arbitrary_command_forbidden")
    if plan.arbitrary_python_allowed:
        failures.append("arbitrary_python_forbidden")
    return tuple(failures)


def _validate_output_manifest(
    manifest: OutputManifestContract,
    expected_plan_id: str,
) -> tuple[str, ...]:
    failures: list[str] = []
    if not manifest.manifest_id:
        failures.append("output_manifest_id_required")
    if manifest.plan_id != expected_plan_id:
        failures.append("output_manifest_plan_mismatch")
    if not manifest.output_asset_bindings:
        failures.append("output_asset_bindings_required")
    for binding in manifest.output_asset_bindings:
        failures.extend(validate_asset_hash_binding(binding))
    if manifest.output_directory_policy != "new_artifact_directory_only":
        failures.append("output_directory_policy_must_be_new_artifact_directory_only")
    if not manifest.output_manifest_required:
        failures.append("output_manifest_required")
    if not manifest.output_hashing_required:
        failures.append("output_hashing_required")
    if manifest.source_asset_overwrite_allowed:
        failures.append("source_asset_overwrite_forbidden")
    if manifest.existing_output_overwrite_allowed:
        failures.append("output_overwrite_forbidden")
    if manifest.raw_payload_storage_allowed:
        failures.append("raw_payload_storage_forbidden")
    return tuple(failures)


def _validate_provenance_policy(policy: ProvenancePolicy) -> tuple[str, ...]:
    failures = []
    for field_name, value in policy.to_dict().items():
        if value is not True:
            failures.append(field_name + "_required")
    return tuple(failures)


def _validate_replay_policy(policy: ReplayPolicy) -> tuple[str, ...]:
    failures = []
    for field_name, value in policy.to_dict().items():
        if field_name == "automatic_reexecution_allowed":
            if value is not False:
                failures.append("automatic_reexecution_forbidden")
        elif value is not True:
            failures.append(field_name + "_required")
    return tuple(failures)


def _validate_admission_rules(rules: AdapterAdmissionRules) -> tuple[str, ...]:
    failures: list[str] = []
    if rules.admission_status != "candidate":
        failures.append("admission_status_must_remain_candidate")
    forbidden_true_fields = (
        "runtime_admitted",
        "live_dcc_execution_allowed",
        "process_launch_allowed",
        "network_access_allowed",
        "source_asset_overwrite_allowed",
    )
    for field_name in forbidden_true_fields:
        if getattr(rules, field_name) is not False:
            failures.append(field_name + "_forbidden")
    required_true_fields = (
        "explicit_future_admission_required",
        "human_approval_required",
        "capability_token_required",
        "output_manifest_required",
        "provenance_required",
        "replay_policy_required",
    )
    for field_name in required_true_fields:
        if getattr(rules, field_name) is not True:
            failures.append(field_name + "_required")
    return tuple(failures)


def _valid_digest(value: object) -> bool:
    return isinstance(value, str) and bool(_SHA256_RE.fullmatch(value))


def _dataclass_dict(instance: object) -> dict[str, object]:
    return {
        field_name: getattr(instance, field_name)
        for field_name in instance.__dataclass_fields__
    }
