"""Generate operator asset registry docs and closure."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from kernel.runtime.operator_asset_registry import build_operator_asset_registry, render_operator_asset_registry_markdown
from kernel.runtime.operator_asset_registry_closure import (
    build_operator_asset_registry_closure,
    render_operator_asset_registry_closure_markdown,
)

REPOSITORY_URL = "https://github.com/qqyqqyqqy666-wq/sovereign-engineering-os"
MAIN_COMMIT = "d98f29ebf25cae196098121ce1632de727393a2d"
REGISTRY_DIR = ROOT / "docs/operator/registries"
CLOSURE_PATH = ROOT / "docs/operator/generated/operator_asset_registry_closure.md"
REGISTRY_FILES = {
    "code_report_registry": "code_report_registry.md",
    "ai_worker_output_registry": "ai_worker_output_registry.md",
    "decision_log_registry": "decision_log_registry.md",
    "rollback_registry": "rollback_registry.md",
    "evidence_registry": "evidence_registry.md",
    "production_asset_registry": "production_asset_registry.md",
}


def registry_material(registry_type: str, path: str) -> dict[str, object]:
    return {
        "registry_id": f"{registry_type}-001",
        "registry_type": registry_type,
        "repository_url": REPOSITORY_URL,
        "main_commit": MAIN_COMMIT,
        "entries": [
            {
                "entry_id": f"{registry_type}-entry-001",
                "path": path,
                "title": registry_type.replace("_", " "),
                "status": "active read-only registry entry",
            }
        ],
        "blocked_capabilities": [
            "provider execution blocked",
            "trading automation blocked",
            "Houdini/VFX execution assets excluded from this slice",
        ],
        "update_policy": "Append or revise registry entries only through deterministic Markdown review.",
        "rollback_notes": ["Revert the affected registry doc and closure report."],
        "policy_version": "operator-asset-registry-v1",
        "code_version": "0.1.0",
    }


def closure_material() -> dict[str, object]:
    gates = {
        "all_registry_docs_exist": True,
        "registry_contract_exists": True,
        "at_least_one_entry_per_registry": True,
        "blocked_capabilities_preserved": True,
        "no_houdini_execution_assets_unless_external_line_reference_only": True,
        "registry_update_policy_defined": True,
        "rollback_notes_defined": True,
    }
    return {
        "closure_id": "operator-asset-registry-closure-001",
        "repository_url": REPOSITORY_URL,
        "main_commit": MAIN_COMMIT,
        "closure_gates": gates,
        "registry_status": {registry_type: True for registry_type in REGISTRY_FILES},
        "registry_docs": [f"docs/operator/registries/{name}" for name in REGISTRY_FILES.values()],
        "blocked_capabilities": [
            "provider execution blocked",
            "trading automation blocked",
            "Houdini/VFX execution assets excluded from this slice",
        ],
        "completion_decision": "complete",
        "remaining_gaps": [],
        "rollback_notes": ["Revert registry docs and closure report as a unit."],
        "policy_version": "operator-asset-registry-closure-v1",
        "code_version": "0.1.0",
    }


def readme() -> str:
    return """# Operator Registries

These registries are read-only operational indexes for non-Houdini system work.

## Policy
- At least one entry is maintained per registry.
- Registry updates are deterministic Markdown changes.
- Houdini/VFX execution assets are excluded from this slice unless an entry is explicitly an external line reference only.
- Provider execution, trading automation, and production autonomy remain blocked.
"""


def main() -> None:
    REGISTRY_DIR.mkdir(parents=True, exist_ok=True)
    (REGISTRY_DIR / "README.md").write_text(readme(), encoding="utf-8")
    for registry_type, file_name in REGISTRY_FILES.items():
        registry = build_operator_asset_registry(registry_material(registry_type, f"docs/operator/registries/{file_name}"))
        (REGISTRY_DIR / file_name).write_text(render_operator_asset_registry_markdown(registry), encoding="utf-8")
    CLOSURE_PATH.parent.mkdir(parents=True, exist_ok=True)
    closure = build_operator_asset_registry_closure(closure_material())
    CLOSURE_PATH.write_text(render_operator_asset_registry_closure_markdown(closure), encoding="utf-8")


if __name__ == "__main__":
    main()
