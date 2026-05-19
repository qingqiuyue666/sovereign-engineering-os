"""Generate HFX_015 production candidate closure artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from kernel.runtime.hfx_asset_closure import build_hfx_asset_closure, render_hfx_asset_closure_markdown
from kernel.runtime.hfx_gold_asset_standard import GOLD_ASSET_GATES

REPOSITORY_URL = "https://github.com/qqyqqyqqy666-wq/sovereign-engineering-os"
OUTPUT_ROOT = ROOT / "assets/houdini/hfx_factory_core12/300_PRODUCTION_UPGRADE/HFX_015_PORTAL_RING"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--main-commit", required=True)
    args = parser.parse_args()
    closure = build_hfx_asset_closure(_closure_material(args.main_commit))
    _write_json(OUTPUT_ROOT / "HFX_015_PRODUCTION_CANDIDATE_CLOSURE.json", closure.as_dict())
    _write_text(OUTPUT_ROOT / "HFX_015_PRODUCTION_CANDIDATE_CLOSURE.md", render_hfx_asset_closure_markdown(closure))
    return 0


def _closure_material(main_commit: str) -> dict[str, object]:
    gates = {gate: True for gate in GOLD_ASSET_GATES}
    gates["rollback_or_quarantine_route_exists"] = False
    return {
        "closure_id": "hfx-015-production-candidate-closure-v1",
        "asset_id": "HFX_015",
        "asset_name": "Portal Ring",
        "repository_url": REPOSITORY_URL,
        "main_commit": main_commit,
        "closure_status": "production_candidate",
        "evidence_gates": gates,
        "evidence_notes": [
            "Portal Ring has internal preview, mid, final candidate HIP, validation, shot-bound template, and render/comp contract evidence.",
            "Gold status is not claimed because an explicit rollback or quarantine route is not yet present in the closure evidence.",
            "The final asset seal records all_houdini_fx_top_tier_complete as false, so this remains a production candidate.",
        ],
        "boundary_conditions": [
            "no_houdini_launch",
            "no_hython_execution",
            "no_render_execution",
            "no_hip_or_hda_mutation",
            "no_external_raw_asset_commit",
        ],
        "policy_version": "hfx-asset-closure-v1",
        "code_version": "0.1.0",
    }


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
