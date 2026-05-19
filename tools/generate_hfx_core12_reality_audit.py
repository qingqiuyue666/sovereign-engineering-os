"""Generate HFX Core12 reality audit, standard, and ledger artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from kernel.runtime.hfx_core12_completion_ledger import (
    build_hfx_core12_completion_ledger,
    render_hfx_core12_completion_ledger_markdown,
)
from kernel.runtime.hfx_core12_reality_audit import (
    collect_hfx_core12_audit_material,
    build_hfx_core12_reality_audit,
    render_hfx_core12_reality_audit_markdown,
)
from kernel.runtime.hfx_gold_asset_standard import (
    build_hfx_gold_asset_standard,
    default_hfx_gold_asset_standard_material,
    render_hfx_gold_asset_standard_markdown,
)

REPOSITORY_URL = "https://github.com/qqyqqyqqy666-wq/sovereign-engineering-os"
HFX_ROOT = ROOT / "assets/houdini/hfx_factory_core12"
HFX_SOURCE_ROOT_LABEL = "assets/houdini/hfx_factory_core12"
INDEX_ROOT = HFX_ROOT / "00_INDEX_资产索引"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--main-commit", required=True)
    args = parser.parse_args()

    INDEX_ROOT.mkdir(parents=True, exist_ok=True)
    audit_material = collect_hfx_core12_audit_material(
        HFX_ROOT,
        audit_id="hfx-core12-reality-audit-v1",
        repository_url=REPOSITORY_URL,
        main_commit=args.main_commit,
    )
    audit_material["source_root"] = HFX_SOURCE_ROOT_LABEL
    audit = build_hfx_core12_reality_audit(audit_material)
    _write_json(INDEX_ROOT / "HFX_CORE12_REALITY_AUDIT.json", audit.as_dict())
    _write_text(INDEX_ROOT / "HFX_CORE12_REALITY_AUDIT.md", render_hfx_core12_reality_audit_markdown(audit))

    standard = build_hfx_gold_asset_standard(
        default_hfx_gold_asset_standard_material(
            repository_url=REPOSITORY_URL,
            main_commit=args.main_commit,
        )
    )
    _write_text(INDEX_ROOT / "HFX_GOLD_ASSET_STANDARD.md", render_hfx_gold_asset_standard_markdown(standard))

    ledger = build_hfx_core12_completion_ledger(_ledger_material(audit, args.main_commit))
    _write_json(INDEX_ROOT / "HFX_CORE12_COMPLETION_LEDGER.json", ledger.as_dict())
    _write_text(INDEX_ROOT / "HFX_CORE12_COMPLETION_LEDGER.md", render_hfx_core12_completion_ledger_markdown(ledger))
    return 0


def _ledger_material(audit, main_commit: str) -> dict[str, object]:
    core12_assets: list[dict[str, object]] = []
    gold_assets: list[str] = []
    production_candidates: list[str] = []
    partial_candidates: list[str] = []
    shell_only_assets: list[str] = []
    blocked_assets: list[str] = []
    for asset in audit.core12_assets:
        asset_id = str(asset["asset_id"])
        asset_name = str(asset["asset_name"])
        if asset_id == "HFX_008":
            completion_status = "gold_complete"
            gold_assets.append(asset_id)
        elif asset["status"] == "blocked":
            completion_status = "blocked"
            blocked_assets.append(asset_id)
        elif asset["status"] == "shell_only":
            completion_status = "shell_only"
            shell_only_assets.append(asset_id)
        elif asset["status"] == "partial_candidate":
            completion_status = "partial_candidate"
            partial_candidates.append(asset_id)
        else:
            completion_status = "production_candidate"
            production_candidates.append(asset_id)
        core12_assets.append(
            {
                "asset_id": asset_id,
                "asset_name": asset_name,
                "completion_status": completion_status,
                "validated_evidence": completion_status not in {"blocked", "shell_only"},
            }
        )
    return {
        "ledger_id": "hfx-core12-completion-ledger-v1",
        "repository_url": REPOSITORY_URL,
        "main_commit": main_commit,
        "core12_assets": core12_assets,
        "gold_assets": gold_assets,
        "production_candidates": production_candidates,
        "partial_candidates": partial_candidates,
        "shell_only_assets": shell_only_assets,
        "blocked_assets": blocked_assets,
        "external_asset_policy": (
            "Deferred; no GitHub storage decision made; external friend assets are out of scope, "
            "and future review defaults to local-first until license review."
        ),
        "next_required_actions": [
            "Complete explicit gold-gate closure for every Core12 asset.",
            "Create or document rebuild plans for assets without HDA source.",
            "Add shot-bound validation and preview/render proof plans without launching Houdini in this branch.",
            "Keep external raw assets out of this branch until internal closure and license review finish.",
        ],
        "completion_decision": "audit_complete_assets_incomplete",
        "policy_version": "hfx-core12-completion-ledger-v1",
        "code_version": "0.1.0",
    }


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
