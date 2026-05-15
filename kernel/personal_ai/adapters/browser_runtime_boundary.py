"""Product-grade browser runtime boundary helpers."""

from dataclasses import dataclass
from pathlib import Path

from kernel.personal_ai.adapters.browser_adapter_contract import BrowserFixtureActions
from kernel.personal_ai.hash_utils import sha256_file
from kernel.personal_ai.io_utils import write_json_atomically
from kernel.personal_ai.runtime_admission_gate import runtime_policy_for_class

__all__ = [
    "BrowserRuntimeAdmissionArtifacts",
    "BrowserRuntimeBoundary",
    "boundary_for_browser_runtime",
    "build_browser_runtime_boundaries",
    "validate_browser_runtime_boundary",
    "write_browser_runtime_admission_artifacts",
]

_CONFIG_TYPE = "personal_ai_runtime_config_v1"
_APPROVAL_TYPE = "personal_ai_runtime_human_approval_v1"
_MANIFEST_TYPE = "personal_ai_runtime_manifest_v1"
_APPROVED_ACTION = "admit_runtime_execution"
_DEFAULT_REAL_ALLOWED_DOMAINS = ("127.0.0.1", "localhost")
_FORBIDDEN_ACTIONS = (
    "account_creation",
    "checkout",
    "credential_storage",
    "login",
    "payment",
    "purchase",
    "register",
)


@dataclass(frozen=True)
class BrowserRuntimeBoundary:
    runtime_id: str
    adapter_id: str
    capability: str
    runtime_class: str
    local_fixture_default: bool
    real_browser_runtime: bool
    enabled_by_default: bool
    admitted_by_default: bool
    allowed_actions: tuple[str, ...]
    allowed_domains: tuple[str, ...]
    timeout_seconds_max: int = 30

    def to_dict(self) -> dict[str, object]:
        return {
            "runtime_id": self.runtime_id,
            "adapter_id": self.adapter_id,
            "capability": self.capability,
            "runtime_class": self.runtime_class,
            "local_fixture_default": self.local_fixture_default,
            "real_browser_runtime": self.real_browser_runtime,
            "enabled_by_default": self.enabled_by_default,
            "admitted_by_default": self.admitted_by_default,
            "allowed_actions": list(self.allowed_actions),
            "allowed_domains": list(self.allowed_domains),
            "forbidden_actions": list(_FORBIDDEN_ACTIONS),
            "timeout_seconds_max": self.timeout_seconds_max,
            "playwright_boundary_declared": self.real_browser_runtime,
            "selenium_boundary_declared": self.real_browser_runtime,
            "credential_persistence_allowed": False,
            "external_url_allowed_by_default": False,
            "login_allowed_by_default": False,
            "payment_allowed_by_default": False,
            "account_creation_allowed_by_default": False,
            "screenshot_evidence_required": True,
            "runtime_admission_required_for_real_browser": self.real_browser_runtime,
        }


@dataclass(frozen=True)
class BrowserRuntimeAdmissionArtifacts:
    config_path: Path
    human_approval_path: Path
    manifest_path: Path
    config_sha256: str
    human_approval_sha256: str
    manifest_sha256: str


def build_browser_runtime_boundaries() -> tuple[BrowserRuntimeBoundary, ...]:
    return (
        BrowserRuntimeBoundary(
            runtime_id="local_fixture_browser",
            adapter_id="browser_fixture_runtime",
            capability="open_local_fixture",
            runtime_class="local_fixture",
            local_fixture_default=True,
            real_browser_runtime=False,
            enabled_by_default=True,
            admitted_by_default=True,
            allowed_actions=BrowserFixtureActions.allowed(),
            allowed_domains=(),
        ),
        BrowserRuntimeBoundary(
            runtime_id="real_browser_boundary",
            adapter_id="real_browser_runtime_boundary",
            capability="drive_real_browser_with_allowlist",
            runtime_class="external_browser",
            local_fixture_default=False,
            real_browser_runtime=True,
            enabled_by_default=False,
            admitted_by_default=False,
            allowed_actions=(
                "navigate",
                "inspect_title",
                "inspect_links",
                "capture_screenshot",
            ),
            allowed_domains=_DEFAULT_REAL_ALLOWED_DOMAINS,
        ),
    )


def boundary_for_browser_runtime(runtime_id: str) -> BrowserRuntimeBoundary:
    for boundary in build_browser_runtime_boundaries():
        if boundary.runtime_id == runtime_id:
            return boundary
    raise ValueError("browser runtime is not registered")


def validate_browser_runtime_boundary(
    boundary: BrowserRuntimeBoundary,
) -> tuple[str, ...]:
    failures = []
    if not boundary.runtime_id:
        failures.append("runtime_id_missing")
    if not boundary.adapter_id:
        failures.append("adapter_id_missing")
    if not boundary.capability:
        failures.append("capability_missing")
    if boundary.runtime_class not in ("local_fixture", "external_browser"):
        failures.append("runtime_class_invalid")
    if not boundary.allowed_actions:
        failures.append("allowed_actions_missing")
    if boundary.timeout_seconds_max <= 0:
        failures.append("timeout_invalid")
    if boundary.real_browser_runtime:
        if boundary.enabled_by_default:
            failures.append("real_browser_enabled_by_default")
        if boundary.admitted_by_default:
            failures.append("real_browser_admitted_by_default")
        if not boundary.allowed_domains:
            failures.append("domain_allowlist_missing")
        for domain in boundary.allowed_domains:
            if "/" in domain or ":" in domain or not domain:
                failures.append("domain_allowlist_malformed")
    else:
        if not boundary.local_fixture_default:
            failures.append("fixture_default_missing")
        if not boundary.enabled_by_default:
            failures.append("fixture_disabled")
        if not boundary.admitted_by_default:
            failures.append("fixture_not_admitted")
    return tuple(sorted(set(failures)))


def write_browser_runtime_admission_artifacts(
    output_dir: Path,
    *,
    runtime_id: str = "real_browser_boundary",
    dry_run: bool = True,
    allowed_domains: tuple[str, ...] = _DEFAULT_REAL_ALLOWED_DOMAINS,
    reviewer_id: str = "human-reviewer",
) -> BrowserRuntimeAdmissionArtifacts:
    output_path = Path(output_dir)
    if not output_path.exists() or not output_path.is_dir():
        raise ValueError("output_dir is missing")
    boundary = boundary_for_browser_runtime(runtime_id)
    failures = validate_browser_runtime_boundary(boundary)
    if failures:
        raise ValueError("browser runtime boundary is invalid: " + ",".join(failures))
    _validate_domains(allowed_domains)
    if not reviewer_id.strip():
        raise ValueError("reviewer_id is required")

    config_path = output_path / "browser_runtime_config.json"
    manifest_path = output_path / "browser_runtime_manifest.json"
    approval_path = output_path / "browser_runtime_approval.json"
    _require_no_overwrite(config_path)
    _require_no_overwrite(manifest_path)
    _require_no_overwrite(approval_path)

    policy = runtime_policy_for_class(boundary.runtime_class).to_dict()
    config = {
        "config_type": _CONFIG_TYPE,
        "adapter_id": boundary.adapter_id,
        "capability": boundary.capability,
        "runtime_class": boundary.runtime_class,
        "runtime_id": boundary.runtime_id,
        "dry_run": dry_run,
        "real_runtime_enabled": False,
        "runtime_class_policy": policy,
        "allowed_domains": list(allowed_domains),
        "allowed_actions": list(boundary.allowed_actions),
        "forbidden_actions": list(_FORBIDDEN_ACTIONS),
        "playwright_boundary_declared": boundary.real_browser_runtime,
        "selenium_boundary_declared": boundary.real_browser_runtime,
        "external_url_allowed_by_default": False,
        "credential_persistence_allowed": False,
        "login_allowed": False,
        "payment_allowed": False,
        "account_creation_allowed": False,
        "screenshot_evidence_required": True,
        "timeout_seconds_max": boundary.timeout_seconds_max,
        "required_human_approval": True,
    }
    write_json_atomically(config_path, config)
    config_sha256 = sha256_file(config_path)

    manifest = {
        "manifest_type": _MANIFEST_TYPE,
        "adapter_id": boundary.adapter_id,
        "capability": boundary.capability,
        "runtime_class": boundary.runtime_class,
        "runtime_id": boundary.runtime_id,
        "dry_run": dry_run,
        "config_sha256": config_sha256,
        "browser_result_manifest_required": True,
        "screenshot_evidence_required": True,
        "failure_quarantine_required": True,
        "real_browser_runtime_called": False,
        "external_network_used": False,
        "credential_persistence_used": False,
        "required_human_approval": True,
    }
    write_json_atomically(manifest_path, manifest)
    manifest_sha256 = sha256_file(manifest_path)

    approval = {
        "approval_type": _APPROVAL_TYPE,
        "adapter_id": boundary.adapter_id,
        "capability": boundary.capability,
        "runtime_class": boundary.runtime_class,
        "runtime_id": boundary.runtime_id,
        "approved_action": _APPROVED_ACTION,
        "approved": True,
        "human_reviewed": True,
        "reviewer_id": reviewer_id.strip(),
        "config_sha256": config_sha256,
        "manifest_sha256": manifest_sha256,
        "required_human_approval": True,
    }
    write_json_atomically(approval_path, approval)
    return BrowserRuntimeAdmissionArtifacts(
        config_path=config_path,
        human_approval_path=approval_path,
        manifest_path=manifest_path,
        config_sha256=config_sha256,
        human_approval_sha256=sha256_file(approval_path),
        manifest_sha256=manifest_sha256,
    )


def _validate_domains(domains: tuple[str, ...]) -> None:
    if not isinstance(domains, tuple):
        raise ValueError("allowed_domains must be a tuple")
    for domain in domains:
        if not isinstance(domain, str) or not domain or "/" in domain or ":" in domain:
            raise ValueError("allowed domain is malformed")


def _require_no_overwrite(path: Path) -> None:
    if path.exists():
        raise ValueError("browser runtime admission artifact already exists")
