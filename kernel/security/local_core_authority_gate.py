"""Local core authority gate.

Local-only validators for authority-side branch, diff, CI, and protected
asset checks. No network execution helpers, no provider calls, no secret reads,
no git mutation, no file mutation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

__all__ = [
    "PROTECTED_ASSET_IDS",
    "LocalAuthorityReceipt",
    "CoreAssetProtectionReceipt",
    "validate_local_authority_gate",
    "validate_core_asset_protection",
]

PROTECTED_ASSET_IDS = (
    "system_architecture_core",
    "runtime_spine_design",
    "provider_architecture",
    "replay_architecture",
    "evidence_vault_architecture",
    "osint_asset_mapping_architecture",
    "decision_engine",
    "real_provider_implementation",
    "real_strategy_parameters",
    "real_execution_logic",
    "real_deployment_scripts",
    "real_run_history",
    "real_evidence_vault",
    "real_kms_or_keyring",
)

FORBIDDEN_AUTHORITY_DELEGATIONS = (
    "cloud_ai_git_authority",
    "cloud_ai_merge_authority",
    "cloud_ai_push_authority",
    "cloud_ai_branch_delete_authority",
    "cloud_ai_final_ci_authority",
    "cloud_ai_production_execution_authority",
)


@dataclass(frozen=True)
class LocalAuthorityReceipt:
    accepted: bool
    failures: tuple[str, ...]
    branch_name: str
    clean_base_required: bool
    local_ci_passed: bool
    human_review_required: bool
    policy_version: str = "v1"

    def as_dict(self) -> dict[str, object]:
        return {
            "accepted": self.accepted,
            "failures": list(self.failures),
            "branch_name": self.branch_name,
            "clean_base_required": self.clean_base_required,
            "local_ci_passed": self.local_ci_passed,
            "human_review_required": self.human_review_required,
            "policy_version": self.policy_version,
        }


@dataclass(frozen=True)
class CoreAssetProtectionReceipt:
    accepted: bool
    failures: tuple[str, ...]
    asset_id: str
    asset_class: str
    local_only_required: bool
    cloud_ai_allowed: bool
    policy_version: str = "v1"

    def as_dict(self) -> dict[str, object]:
        return {
            "accepted": self.accepted,
            "failures": list(self.failures),
            "asset_id": self.asset_id,
            "asset_class": self.asset_class,
            "local_only_required": self.local_only_required,
            "cloud_ai_allowed": self.cloud_ai_allowed,
            "policy_version": self.policy_version,
        }


def _is_nonempty_string(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _is_bool(value: object) -> bool:
    return isinstance(value, bool)


def validate_local_authority_gate(payload: Mapping[str, object]) -> LocalAuthorityReceipt:
    if not isinstance(payload, Mapping):
        raise TypeError("payload_must_be_mapping")

    failures: list[str] = []
    branch_name = payload.get("branch_name", "")

    if not _is_nonempty_string(branch_name):
        failures.append("branch_name_required_nonempty_string")
    elif branch_name == "main":
        failures.append("main_branch_direct_work_forbidden")

    for field in (
        "clean_base_required",
        "dirty_worktree_before_apply",
        "git_diff_check_passed",
        "local_tests_passed",
        "local_ci_passed",
        "human_review_required",
        "cloud_ai_is_authority",
    ):
        if not _is_bool(payload.get(field)):
            failures.append(f"{field}_required_bool")

    if payload.get("clean_base_required") is not True:
        failures.append("clean_base_required_must_be_true")
    if payload.get("dirty_worktree_before_apply") is True:
        failures.append("dirty_worktree_before_apply_forbidden")
    if payload.get("git_diff_check_passed") is not True:
        failures.append("git_diff_check_must_pass")
    if payload.get("local_tests_passed") is not True:
        failures.append("local_tests_must_pass")
    if payload.get("local_ci_passed") is not True:
        failures.append("local_ci_must_pass")
    if payload.get("human_review_required") is not True:
        failures.append("human_review_required_must_be_true")
    if payload.get("cloud_ai_is_authority") is True:
        failures.append("cloud_ai_must_not_be_authority")

    delegations = payload.get("authority_delegations", ())
    if not isinstance(delegations, (list, tuple)):
        failures.append("authority_delegations_must_be_sequence")
        delegations = ()

    for item in delegations:
        if not isinstance(item, str):
            failures.append("authority_delegation_must_be_string")
        elif item in FORBIDDEN_AUTHORITY_DELEGATIONS:
            failures.append(f"{item}_forbidden")

    return LocalAuthorityReceipt(
        accepted=not failures,
        failures=tuple(failures),
        branch_name=branch_name if isinstance(branch_name, str) else "",
        clean_base_required=payload.get("clean_base_required") if isinstance(payload.get("clean_base_required"), bool) else False,
        local_ci_passed=payload.get("local_ci_passed") if isinstance(payload.get("local_ci_passed"), bool) else False,
        human_review_required=payload.get("human_review_required") if isinstance(payload.get("human_review_required"), bool) else False,
    )


def validate_core_asset_protection(payload: Mapping[str, object]) -> CoreAssetProtectionReceipt:
    if not isinstance(payload, Mapping):
        raise TypeError("payload_must_be_mapping")

    failures: list[str] = []
    asset_id = payload.get("asset_id", "")
    asset_class = payload.get("asset_class", "")
    local_only_required = payload.get("local_only_required", False)
    cloud_ai_allowed = payload.get("cloud_ai_allowed", False)
    exposure_mode = payload.get("exposure_mode", "")

    if not _is_nonempty_string(asset_id):
        failures.append("asset_id_required_nonempty_string")
    if asset_id not in PROTECTED_ASSET_IDS:
        failures.append("asset_id_not_registered_protected_asset")
    if asset_class != "C":
        failures.append("protected_asset_must_be_c_layer")
    if not _is_bool(local_only_required):
        failures.append("local_only_required_must_be_bool")
    elif local_only_required is not True:
        failures.append("protected_asset_requires_local_only")
    if not _is_bool(cloud_ai_allowed):
        failures.append("cloud_ai_allowed_must_be_bool")
    elif cloud_ai_allowed is True:
        failures.append("protected_asset_forbids_cloud_ai")
    if exposure_mode != "local_only":
        failures.append("exposure_mode_must_be_local_only")

    return CoreAssetProtectionReceipt(
        accepted=not failures,
        failures=tuple(failures),
        asset_id=asset_id if isinstance(asset_id, str) else "",
        asset_class=asset_class if isinstance(asset_class, str) else "",
        local_only_required=local_only_required if isinstance(local_only_required, bool) else False,
        cloud_ai_allowed=cloud_ai_allowed if isinstance(cloud_ai_allowed, bool) else False,
    )
