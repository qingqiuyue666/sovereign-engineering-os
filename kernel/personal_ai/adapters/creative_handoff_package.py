"""Safe creative software handoff packages."""

from dataclasses import dataclass
from pathlib import Path

from kernel.personal_ai.adapters.creative_adapter_contract import (
    CreativeAdapterFamily,
    policy_for_family,
    validate_creative_adapter_policy,
)
from kernel.personal_ai.hash_utils import sha256_file
from kernel.personal_ai.io_utils import write_json_atomically
from kernel.personal_ai.job_package import validate_job_id
from kernel.personal_ai.markdown_utils import write_markdown_atomically

__all__ = [
    "CreativeHandoffPackageResult",
    "build_creative_handoff_package",
]

_PACKAGE_MANIFEST_FILE = "creative_handoff_manifest.json"
_TOOL_MANIFEST_FILE = "creative_handoff_tool_manifest.json"
_INSTRUCTIONS_FILE = "creative_handoff_instructions.md"
_OUTPUT_TARGET_DIR = "handoff_outputs"


@dataclass(frozen=True)
class CreativeHandoffPackageResult:
    family: str
    package_id: str
    package_dir: Path
    package_manifest_path: Path
    tool_manifest_path: Path
    instructions_path: Path
    output_target_dir: Path
    source_asset_count: int
    complete: bool
    required_human_approval: bool


def build_creative_handoff_package(
    family: str,
    source_asset_paths: tuple[Path, ...],
    output_root_dir: Path,
    *,
    package_id: str,
    requested_output_targets: tuple[Path, ...] = (),
) -> CreativeHandoffPackageResult:
    output_root = Path(output_root_dir)
    if not output_root.exists() or not output_root.is_dir():
        raise ValueError("output_root_dir is missing")
    validate_job_id(package_id)
    policy = policy_for_family(family)
    failures = validate_creative_adapter_policy(policy)
    if failures:
        raise ValueError("creative adapter policy is invalid: " + ",".join(failures))
    source_assets = _source_asset_records(source_asset_paths)
    package_dir = output_root / package_id
    if package_dir.exists():
        raise ValueError("creative handoff package_dir already exists")
    output_target_dir = package_dir / _OUTPUT_TARGET_DIR
    _validate_requested_output_targets(
        requested_output_targets,
        source_asset_paths,
        output_target_dir,
    )
    package_dir.mkdir()
    output_target_dir.mkdir()

    tool_manifest_path = package_dir / _TOOL_MANIFEST_FILE
    instructions_path = package_dir / _INSTRUCTIONS_FILE
    package_manifest_path = package_dir / _PACKAGE_MANIFEST_FILE
    tool_manifest = {
        "manifest_type": "personal_ai_creative_handoff_tool_manifest_v1",
        "authority": "non_authority",
        "execution_capability": "human_handoff_package_only",
        "family": family,
        "proposed_adapter": policy.proposed_adapter,
        "runtime_admitted": False,
        "external_tool_control_performed": False,
        "automatic_external_tool_control_allowed": False,
        "source_asset_hash_binding_required": True,
        "source_assets": source_assets,
        "output_target_policy": _output_target_policy(output_target_dir),
        "operation_allowlist_required": True,
        "operation_allowlist": sorted(policy.operation_allowlist),
        "preview_render_evidence_required": True,
        "human_execution_required": True,
        "source_asset_overwrite_allowed": False,
        "source_asset_overwrite_performed": False,
        "required_human_approval": True,
        "next_allowed_action": "human_runs_creative_tool_manually",
    }
    write_json_atomically(tool_manifest_path, tool_manifest)
    write_markdown_atomically(
        instructions_path,
        _render_instructions(family, policy.proposed_adapter),
    )
    package_manifest = {
        "manifest_type": "personal_ai_creative_handoff_package_manifest_v1",
        "authority": "non_authority",
        "execution_capability": "human_handoff_package_only",
        "family": family,
        "package_id": package_id,
        "package_dir": package_dir.as_posix(),
        "tool_manifest_path": tool_manifest_path.as_posix(),
        "tool_manifest_sha256": sha256_file(tool_manifest_path),
        "instructions_path": instructions_path.as_posix(),
        "instructions_sha256": sha256_file(instructions_path),
        "output_target_dir": output_target_dir.as_posix(),
        "source_asset_hashes": {
            asset["path"]: asset["sha256"] for asset in source_assets
        },
        "source_asset_count": len(source_assets),
        "runtime_admitted": False,
        "external_tool_control_performed": False,
        "source_asset_overwrite_performed": False,
        "preview_render_evidence_required": True,
        "required_human_approval": True,
        "complete": True,
    }
    write_json_atomically(package_manifest_path, package_manifest)
    return CreativeHandoffPackageResult(
        family=family,
        package_id=package_id,
        package_dir=package_dir,
        package_manifest_path=package_manifest_path,
        tool_manifest_path=tool_manifest_path,
        instructions_path=instructions_path,
        output_target_dir=output_target_dir,
        source_asset_count=len(source_assets),
        complete=True,
        required_human_approval=True,
    )


def _source_asset_records(source_asset_paths: tuple[Path, ...]) -> list[dict[str, object]]:
    if not source_asset_paths:
        raise ValueError("source_asset_paths are required")
    records = []
    seen = set()
    for source_asset_path in source_asset_paths:
        path = Path(source_asset_path)
        if not path.exists() or not path.is_file():
            raise ValueError("source asset path is missing")
        if path.is_symlink():
            raise ValueError("source asset path must not be a symlink")
        resolved = path.resolve(strict=True)
        if resolved in seen:
            raise ValueError("source asset path is duplicated")
        seen.add(resolved)
        records.append(
            {
                "path": path.as_posix(),
                "file_name": path.name,
                "sha256": sha256_file(path),
                "source_asset_overwrite_allowed": False,
            }
        )
    return records


def _validate_requested_output_targets(
    requested_output_targets: tuple[Path, ...],
    source_asset_paths: tuple[Path, ...],
    output_target_dir: Path,
) -> None:
    source_resolved = {
        Path(path).resolve(strict=True)
        for path in source_asset_paths
        if Path(path).exists()
    }
    output_root_resolved = output_target_dir.resolve(strict=False)
    for target in requested_output_targets:
        target_path = Path(target)
        target_resolved = target_path.resolve(strict=False)
        if target_resolved in source_resolved:
            raise ValueError("creative handoff target must not overwrite source asset")
        try:
            target_resolved.relative_to(output_root_resolved)
        except ValueError as error:
            raise ValueError(
                "creative handoff target must stay inside package output target dir"
            ) from error


def _output_target_policy(output_target_dir: Path) -> dict[str, object]:
    return {
        "output_target_dir": output_target_dir.as_posix(),
        "outputs_must_stay_inside_package": True,
        "overwrite_existing_allowed": False,
        "source_asset_overwrite_allowed": False,
        "source_asset_overwrite_performed": False,
        "human_review_before_copy_out": True,
    }


def _render_instructions(family: str, proposed_adapter: str) -> str:
    title = _family_label(family)
    return "\n".join(
        [
            "# " + title + " Handoff Instructions",
            "",
            "- Runtime: human handoff package only",
            "- Proposed adapter: `" + proposed_adapter + "`",
            "- Automatic external tool control: false",
            "- Source asset overwrite allowed: false",
            "- Preview/render evidence required: true",
            "- Required human approval: true",
            "- Next action: a human may open the source assets in the named tool and write any derived outputs only under `handoff_outputs/`.",
            "",
        ]
    )


def _family_label(family: str) -> str:
    labels = {
        CreativeAdapterFamily.AFTER_EFFECTS: "After Effects",
        CreativeAdapterFamily.UNREAL: "Unreal Engine",
        CreativeAdapterFamily.HOUDINI: "Houdini",
        CreativeAdapterFamily.ZBRUSH: "ZBrush",
        CreativeAdapterFamily.BLENDER: "Blender",
        CreativeAdapterFamily.COMFYUI: "ComfyUI",
    }
    return labels[family]
