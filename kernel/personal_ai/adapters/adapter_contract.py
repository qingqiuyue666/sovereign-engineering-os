"""Fail-closed adapter contracts for Personal AI Execution OS v2."""

from dataclasses import dataclass, field
from enum import Enum
from types import MappingProxyType
from typing import Mapping

__all__ = [
    "AdapterAdmissionDecision",
    "AdapterAdmissionStatus",
    "AdapterCapabilityRequest",
    "AdapterEvidenceRequirement",
    "AdapterExecutionBoundary",
    "AdapterMode",
    "AdapterOutputPolicy",
    "AdapterQuarantinePolicy",
    "AdapterRegistryEntry",
    "AdapterResultManifest",
    "AdapterRiskClass",
]


class AdapterRiskClass(str, Enum):
    LOCAL_READONLY = "local_readonly"
    APPROVED_OUTPUT_WRITE = "approved_output_write"
    MOCK_MODEL = "mock_model"
    LOCAL_BROWSER_FIXTURE = "local_browser_fixture"
    LOCAL_CREATIVE_FIXTURE = "local_creative_fixture"
    EXTERNAL_BROWSER = "external_browser"
    LIVE_MODEL_PROVIDER = "live_model_provider"
    CREATIVE_EXTERNAL_TOOL = "creative_external_tool"
    SUBPROCESS_TOOL = "subprocess_tool"
    NETWORK_TOOL = "network_tool"


class AdapterMode(str, Enum):
    READONLY = "readonly"
    APPROVED_WRITE = "approved_write"
    MOCK_RUNTIME = "mock_runtime"
    LOCAL_FIXTURE = "local_fixture"
    POLICY_ONLY = "policy_only"
    REFERENCE_ONLY = "reference_only"
    FUTURE_EXTERNAL = "future_external"


class AdapterAdmissionStatus(str, Enum):
    ADMITTED = "admitted"
    CANDIDATE = "candidate"
    DEFERRED = "deferred"
    REJECTED = "rejected"
    REFERENCE_ONLY = "reference_only"


@dataclass(frozen=True)
class AdapterEvidenceRequirement:
    requires_manifest: bool = True
    requires_evidence_capture: bool = True
    requires_output_hashing: bool = True
    requires_input_hash: bool = True
    requires_plan_hash: bool = True
    requires_approval_hash: bool = True
    requires_validation_report: bool = True
    requires_provenance_reference: bool = True


@dataclass(frozen=True)
class AdapterQuarantinePolicy:
    requires_quarantine: bool = True
    quarantine_parse_failures: bool = True
    quarantine_validation_failures: bool = True
    quarantine_unsafe_requests: bool = True


@dataclass(frozen=True)
class AdapterOutputPolicy:
    output_write_allowed: bool = False
    overwrite_existing_allowed: bool = False
    output_must_be_outside_input_dir: bool = True
    raw_value_copy_allowed: bool = False
    requires_output_hashing: bool = True
    requires_manifest: bool = True
    requires_validation_report: bool = True


@dataclass(frozen=True)
class AdapterExecutionBoundary:
    network_allowed: bool = False
    subprocess_allowed: bool = False
    external_tool_control_allowed: bool = False
    input_mutation_allowed: bool = False
    overwrite_existing_allowed: bool = False
    raw_value_copy_allowed: bool = False
    output_write_allowed: bool = False
    requires_human_approval: bool = True
    requires_capability_token: bool = True
    requires_manifest: bool = True
    requires_evidence_capture: bool = True
    requires_quarantine: bool = True
    requires_output_hashing: bool = True

    def is_runtime_safe_for_current_branch(self) -> bool:
        return all(
            (
                self.rejects_unapproved_external_control(),
                self.rejects_raw_value_leakage(),
                self.rejects_input_mutation(),
                self.rejects_unapproved_output_write(),
                self.rejects_network_runtime(),
                self.rejects_subprocess_runtime(),
                self.requires_human_approval,
                self.requires_capability_token,
                self.requires_manifest,
                self.requires_evidence_capture,
                self.requires_quarantine,
                self.requires_hash_bound_outputs(),
            )
        )

    def requires_explicit_future_admission(self) -> bool:
        return any(
            (
                self.network_allowed,
                self.subprocess_allowed,
                self.external_tool_control_allowed,
                self.input_mutation_allowed,
                self.overwrite_existing_allowed,
                self.raw_value_copy_allowed,
            )
        )

    def rejects_unapproved_external_control(self) -> bool:
        return self.external_tool_control_allowed is False

    def rejects_raw_value_leakage(self) -> bool:
        return self.raw_value_copy_allowed is False

    def rejects_input_mutation(self) -> bool:
        return (
            self.input_mutation_allowed is False
            and self.overwrite_existing_allowed is False
        )

    def rejects_unapproved_output_write(self) -> bool:
        if self.output_write_allowed is False:
            return True
        return all(
            (
                self.requires_human_approval,
                self.requires_capability_token,
                self.requires_manifest,
                self.requires_evidence_capture,
                self.requires_output_hashing,
                self.overwrite_existing_allowed is False,
            )
        )

    def rejects_network_runtime(self) -> bool:
        return self.network_allowed is False

    def rejects_subprocess_runtime(self) -> bool:
        return self.subprocess_allowed is False

    def requires_hash_bound_outputs(self) -> bool:
        return self.requires_manifest and self.requires_output_hashing


@dataclass(frozen=True)
class AdapterCapabilityRequest:
    adapter_id: str
    capability: str
    mode: AdapterMode
    risk_class: AdapterRiskClass
    requested_operations: tuple[str, ...] = ()
    boundary: AdapterExecutionBoundary = field(
        default_factory=AdapterExecutionBoundary
    )
    evidence_requirement: AdapterEvidenceRequirement = field(
        default_factory=AdapterEvidenceRequirement
    )


@dataclass(frozen=True)
class AdapterAdmissionDecision:
    adapter_id: str
    capability: str
    admission_status: AdapterAdmissionStatus
    admitted: bool
    reason_codes: tuple[str, ...]
    boundary: AdapterExecutionBoundary = field(
        default_factory=AdapterExecutionBoundary
    )
    evidence_requirement: AdapterEvidenceRequirement = field(
        default_factory=AdapterEvidenceRequirement
    )
    quarantine_policy: AdapterQuarantinePolicy = field(
        default_factory=AdapterQuarantinePolicy
    )
    output_policy: AdapterOutputPolicy = field(default_factory=AdapterOutputPolicy)

    def is_runtime_safe_for_current_branch(self) -> bool:
        return (
            self.admitted is True
            and self.admission_status == AdapterAdmissionStatus.ADMITTED
            and self.boundary.is_runtime_safe_for_current_branch()
            and self.quarantine_policy.requires_quarantine
            and self.output_policy.requires_output_hashing
            and self.output_policy.requires_manifest
        )


@dataclass(frozen=True)
class AdapterResultManifest:
    adapter_id: str
    capability: str
    manifest_type: str
    artifact_paths: tuple[str, ...]
    artifact_hashes: Mapping[str, str] = field(default_factory=dict)
    authority: str = "non_authority"
    execution_capability: str = "bounded_local_runtime"
    required_human_approval: bool = True
    input_mutation_performed: bool = False
    overwrite_performed: bool = False
    raw_value_copy_performed: bool = False

    def to_dict(self) -> dict[str, object]:
        return {
            "adapter_id": self.adapter_id,
            "capability": self.capability,
            "manifest_type": self.manifest_type,
            "artifact_paths": list(self.artifact_paths),
            "artifact_hashes": {
                key: self.artifact_hashes[key]
                for key in sorted(self.artifact_hashes)
            },
            "authority": self.authority,
            "execution_capability": self.execution_capability,
            "required_human_approval": self.required_human_approval,
            "input_mutation_performed": self.input_mutation_performed,
            "overwrite_performed": self.overwrite_performed,
            "raw_value_copy_performed": self.raw_value_copy_performed,
        }


@dataclass(frozen=True)
class AdapterRegistryEntry:
    adapter_id: str
    adapter_name: str
    mode: AdapterMode
    risk_class: AdapterRiskClass
    admission_status: AdapterAdmissionStatus
    capabilities: tuple[str, ...]
    required_controls: tuple[str, ...]
    boundary: AdapterExecutionBoundary = field(
        default_factory=AdapterExecutionBoundary
    )
    evidence_requirement: AdapterEvidenceRequirement = field(
        default_factory=AdapterEvidenceRequirement
    )
    quarantine_policy: AdapterQuarantinePolicy = field(
        default_factory=AdapterQuarantinePolicy
    )
    output_policy: AdapterOutputPolicy = field(default_factory=AdapterOutputPolicy)
    notes: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "adapter_id": self.adapter_id,
            "adapter_name": self.adapter_name,
            "mode": self.mode.value,
            "risk_class": self.risk_class.value,
            "admission_status": self.admission_status.value,
            "capabilities": list(self.capabilities),
            "required_controls": list(self.required_controls),
            "boundary": dict(_field_mapping(self.boundary)),
            "evidence_requirement": dict(_field_mapping(self.evidence_requirement)),
            "quarantine_policy": dict(_field_mapping(self.quarantine_policy)),
            "output_policy": dict(_field_mapping(self.output_policy)),
            "notes": self.notes,
        }


def _field_mapping(instance) -> Mapping[str, object]:
    return MappingProxyType(
        {
            field_name: getattr(instance, field_name)
            for field_name in instance.__dataclass_fields__
        }
    )
