"""Personal AI local-only non-authority foundation surfaces."""

from kernel.personal_ai.artifact_profiler import (
    ArtifactProfileResult,
    build_artifact_profile,
)
from kernel.personal_ai.artifact_index import (
    ArtifactIndexResult,
    build_artifact_index,
)
from kernel.personal_ai.approval_gate import (
    OutputApprovalDecisionResult,
    OutputApprovalRequestResult,
    approval_request_sha256_excluding_self,
    build_output_approval_request,
    validate_output_approval_decision,
)
from kernel.personal_ai.approval_provenance import (
    ApprovalProvenanceChainResult,
    build_approval_provenance_chain,
)
from kernel.personal_ai.hash_utils import (
    canonical_json_bytes,
    hash_artifact_set,
    sha256_canonical_json,
    sha256_file,
    sha256_text,
)
from kernel.personal_ai.local_file_intake import (
    LocalFileIntakeResult,
    build_local_file_intake_ledger,
)
from kernel.personal_ai.local_mvp_runner import (
    PersonalAILocalMVPResult,
    run_personal_ai_local_mvp,
)
from kernel.personal_ai.output_package import (
    ApprovedOutputPackageResult,
    build_approved_output_package,
)
from kernel.personal_ai.output_package_manifest import (
    ApprovedOutputManifestResult,
    build_approved_output_manifest,
)
from kernel.personal_ai.output_validator import (
    ApprovedOutputValidationResult,
    build_approved_output_validation,
)
from kernel.personal_ai.oss_integration_registry import (
    get_oss_integration_registry,
    list_oss_integrations,
    write_oss_integration_registry,
)
from kernel.personal_ai.package_validator import (
    JobPackageValidationResult,
    build_job_package_validation,
)
from kernel.personal_ai.review_packet import (
    ReviewPacketResult,
    build_review_packet,
)
from kernel.personal_ai.snapshot_utils import (
    canonical_snapshot_json,
    normalize_snapshot_payload,
)
from kernel.personal_ai.work_order import (
    WorkOrderProposalResult,
    build_work_order_proposal,
)

__all__ = [
    "ApprovedOutputManifestResult",
    "ApprovedOutputPackageResult",
    "ApprovalProvenanceChainResult",
    "ArtifactProfileResult",
    "ArtifactIndexResult",
    "ApprovedOutputValidationResult",
    "JobPackageValidationResult",
    "LocalFileIntakeResult",
    "OutputApprovalDecisionResult",
    "OutputApprovalRequestResult",
    "PersonalAILocalMVPResult",
    "ReviewPacketResult",
    "WorkOrderProposalResult",
    "approval_request_sha256_excluding_self",
    "build_artifact_index",
    "build_approval_provenance_chain",
    "build_approved_output_manifest",
    "build_approved_output_package",
    "build_approved_output_validation",
    "build_artifact_profile",
    "build_job_package_validation",
    "build_local_file_intake_ledger",
    "build_output_approval_request",
    "canonical_snapshot_json",
    "canonical_json_bytes",
    "get_oss_integration_registry",
    "hash_artifact_set",
    "build_review_packet",
    "list_oss_integrations",
    "normalize_snapshot_payload",
    "run_personal_ai_local_mvp",
    "sha256_canonical_json",
    "sha256_file",
    "sha256_text",
    "validate_output_approval_decision",
    "write_oss_integration_registry",
    "build_work_order_proposal",
]
