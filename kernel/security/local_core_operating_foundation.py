"""Local core operating foundation.

Fail-closed validators for task classification, cloud-AI boundary enforcement,

and patch-only intake.  No network, no provider calls, no secret reads, no git

mutation, no file mutation.

"""

from __future__ import annotations

from dataclasses import dataclass

from typing import Mapping

import hashlib

import json

__all__ = [

    "TaskClassificationReceipt",

    "CloudAiBoundaryReceipt",

    "PatchOnlyIntakeReceipt",

    "validate_task_classification",

    "validate_cloud_ai_boundary",

    "validate_patch_only_intake",

]

VALID_ASSET_CLASSES = ("A", "B", "C")

VALID_REPOSITORY_ACCESS_MODES = (

    "none",

    "minimal_snippets",

    "patch_only",

    "temporary_low_sensitivity_clone",

    "local_only",

)

VALID_OUTPUT_MODES = (

    "draft_text",

    "unified_diff_patch",

    "localized_code_suggestion",

    "local_commit_only",

)

FORBIDDEN_ACTIONS = (

    "git_push",

    "git_merge",

    "branch_delete",

    "main_branch_modification",

    "secret_read",

    "env_read",

    "provider_live_execution",

    "vault_live_write",

    "production_autonomy",

    "deployment",

    "full_core_architecture_ingestion",

)

FORBIDDEN_INPUT_FLAGS = (

    "secrets_present",

    "env_files_present",

    "api_keys_present",

    "tokens_present",

    "ssh_private_keys_present",

    "cookies_present",

    "sessions_present",

    "real_account_data_present",

    "real_strategy_parameters_present",

    "real_provider_credentials_present",

    "real_execution_context_present",

    "full_core_architecture_context_present",

)

@dataclass(frozen=True)

class TaskClassificationReceipt:

    accepted: bool

    failures: tuple[str, ...]

    task_id: str

    asset_class: str

    cloud_ai_allowed: bool

    repository_access_mode: str

    output_mode: str

    policy_version: str = "v1"

    def as_dict(self) -> dict[str, object]:

        return {

            "accepted": self.accepted,

            "failures": list(self.failures),

            "task_id": self.task_id,

            "asset_class": self.asset_class,

            "cloud_ai_allowed": self.cloud_ai_allowed,

            "repository_access_mode": self.repository_access_mode,

            "output_mode": self.output_mode,

            "policy_version": self.policy_version,

        }

@dataclass(frozen=True)

class CloudAiBoundaryReceipt:

    accepted: bool

    failures: tuple[str, ...]

    task_id: str

    asset_class: str

    cloud_ai_allowed: bool

    repository_access_mode: str

    output_mode: str

    policy_version: str = "v1"

    def as_dict(self) -> dict[str, object]:

        return {

            "accepted": self.accepted,

            "failures": list(self.failures),

            "task_id": self.task_id,

            "asset_class": self.asset_class,

            "cloud_ai_allowed": self.cloud_ai_allowed,

            "repository_access_mode": self.repository_access_mode,

            "output_mode": self.output_mode,

            "policy_version": self.policy_version,

        }

@dataclass(frozen=True)

class PatchOnlyIntakeReceipt:

    accepted: bool

    failures: tuple[str, ...]

    patch_id: str

    task_id: str

    source_snippet_digest: str

    patch_digest: str

    policy_version: str = "v1"

    def as_dict(self) -> dict[str, object]:

        return {

            "accepted": self.accepted,

            "failures": list(self.failures),

            "patch_id": self.patch_id,

            "task_id": self.task_id,

            "source_snippet_digest": self.source_snippet_digest,

            "patch_digest": self.patch_digest,

            "policy_version": self.policy_version,

        }

def _is_nonempty_string(value: object) -> bool:

    return isinstance(value, str) and bool(value.strip())

def _is_bool(value: object) -> bool:

    return isinstance(value, bool)

def _is_digest(value: object) -> bool:

    if not isinstance(value, str):

        return False

    if not value.startswith("sha256:"):

        return False

    suffix = value.removeprefix("sha256:")

    return len(suffix) == 64 and all(ch in "0123456789abcdef" for ch in suffix)

def _digest(payload: object) -> str:

    data = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)

    return "sha256:" + hashlib.sha256(data.encode("utf-8")).hexdigest()

def validate_task_classification(payload: Mapping[str, object]) -> TaskClassificationReceipt:

    if not isinstance(payload, Mapping):

        raise TypeError("payload_must_be_mapping")

    failures: list[str] = []

    task_id = payload.get("task_id", "")

    asset_class = payload.get("asset_class", "")

    cloud_ai_allowed = payload.get("cloud_ai_allowed", False)

    repository_access_mode = payload.get("repository_access_mode", "")

    output_mode = payload.get("expected_output_mode", payload.get("output_mode", ""))

    for field in (

        "task_id",

        "task_name",

        "asset_class",

        "repository_access_mode",

        "secret_exposure_check",

        "core_architecture_exposure",

        "expected_output_mode",

    ):

        if not _is_nonempty_string(payload.get(field)):

            failures.append(f"{field}_required_nonempty_string")

    for field in ("cloud_ai_allowed", "human_review_required"):

        if not _is_bool(payload.get(field)):

            failures.append(f"{field}_required_bool")

    if asset_class not in VALID_ASSET_CLASSES:

        failures.append("asset_class_invalid")

    if repository_access_mode not in VALID_REPOSITORY_ACCESS_MODES:

        failures.append("repository_access_mode_invalid")

    if output_mode not in VALID_OUTPUT_MODES:

        failures.append("output_mode_invalid")

    if asset_class == "C" and cloud_ai_allowed is True:

        failures.append("c_layer_must_be_local_only")

    if asset_class == "B" and repository_access_mode == "full_repo_mount":

        failures.append("b_layer_requires_patch_only")

    if payload.get("secret_exposure_check") == "present" and cloud_ai_allowed is True:

        failures.append("secrets_forbid_cloud_ai")

    if payload.get("core_architecture_exposure") == "full_context" and cloud_ai_allowed is True:

        failures.append("core_architecture_full_context_forbids_cloud_ai")

    return TaskClassificationReceipt(

        accepted=not failures,

        failures=tuple(failures),

        task_id=task_id if isinstance(task_id, str) else "",

        asset_class=asset_class if isinstance(asset_class, str) else "",

        cloud_ai_allowed=cloud_ai_allowed if isinstance(cloud_ai_allowed, bool) else False,

        repository_access_mode=repository_access_mode if isinstance(repository_access_mode, str) else "",

        output_mode=output_mode if isinstance(output_mode, str) else "",

    )

def validate_cloud_ai_boundary(payload: Mapping[str, object]) -> CloudAiBoundaryReceipt:

    if not isinstance(payload, Mapping):

        raise TypeError("payload_must_be_mapping")

    classification = validate_task_classification(payload)

    failures = list(classification.failures)

    requested_actions = payload.get("requested_actions", ())

    if not isinstance(requested_actions, (list, tuple)):

        failures.append("requested_actions_must_be_sequence")

        requested_actions = ()

    for action in requested_actions:

        if not isinstance(action, str):

            failures.append("requested_action_must_be_string")

        elif action in FORBIDDEN_ACTIONS:

            failures.append(f"{action}_forbidden_for_cloud_ai")

    for flag in FORBIDDEN_INPUT_FLAGS:

        value = payload.get(flag, False)

        if not isinstance(value, bool):

            failures.append(f"{flag}_must_be_bool")

        elif value is True and payload.get("cloud_ai_allowed") is True:

            failures.append(f"{flag}_forbids_cloud_ai")

    if payload.get("asset_class") == "C" and payload.get("cloud_ai_allowed") is True:

        failures.append("c_layer_cloud_ai_boundary_violation")

    return CloudAiBoundaryReceipt(

        accepted=not failures,

        failures=tuple(failures),

        task_id=classification.task_id,

        asset_class=classification.asset_class,

        cloud_ai_allowed=classification.cloud_ai_allowed,

        repository_access_mode=classification.repository_access_mode,

        output_mode=classification.output_mode,

    )

def validate_patch_only_intake(payload: Mapping[str, object]) -> PatchOnlyIntakeReceipt:

    if not isinstance(payload, Mapping):

        raise TypeError("payload_must_be_mapping")

    failures: list[str] = []

    for field in ("patch_id", "task_id"):

        if not _is_nonempty_string(payload.get(field)):

            failures.append(f"{field}_required_nonempty_string")

    for field in ("source_snippet_digest", "patch_digest"):

        if not _is_digest(payload.get(field)):

            failures.append(f"{field}_required_sha256_digest")

    required_values = {

        "output_mode": "unified_diff_patch",

        "repository_access_mode": "minimal_snippets",

        "cloud_ai_role": "draft_worker_only",

        "human_review_required": True,

        "local_apply_required": True,

        "local_ci_required": True,

    }

    for field, expected in required_values.items():

        if payload.get(field) != expected:

            failures.append(f"{field}_must_be_{expected}")

    forbidden_content = payload.get("forbidden_content_flags", ())

    if not isinstance(forbidden_content, (list, tuple)):

        failures.append("forbidden_content_flags_must_be_sequence")

        forbidden_content = ()

    for item in forbidden_content:

        if not isinstance(item, str):

            failures.append("forbidden_content_flag_must_be_string")

        elif item in (

            "secrets",

            "env_reads",

            "git_push",

            "git_merge",

            "provider_live_execution",

            "vault_live_write",

            "production_autonomy",

        ):

            failures.append(f"{item}_forbidden_in_patch")

    return PatchOnlyIntakeReceipt(

        accepted=not failures,

        failures=tuple(failures),

        patch_id=payload.get("patch_id", "") if isinstance(payload.get("patch_id", ""), str) else "",

        task_id=payload.get("task_id", "") if isinstance(payload.get("task_id", ""), str) else "",

        source_snippet_digest=payload.get("source_snippet_digest", "") if isinstance(payload.get("source_snippet_digest", ""), str) else "",

        patch_digest=payload.get("patch_digest", "") if isinstance(payload.get("patch_digest", ""), str) else "",

    )

