"""Tracer-bullet tests for the HFX Core12 completion ledger."""

from __future__ import annotations

from pathlib import Path
import json
import unittest

from kernel.audit.hashchain import digest_payload
from kernel.runtime.hfx_core12_completion_ledger import (
    HFXCore12CompletionLedger,
    build_hfx_core12_completion_ledger,
    render_hfx_core12_completion_ledger_markdown,
)
from kernel.runtime.hfx_core12_reality_audit import HFX_CORE12_ASSETS


LEDGER_JSON = Path("assets/houdini/hfx_factory_core12/00_INDEX_资产索引/HFX_CORE12_COMPLETION_LEDGER.json")
LEDGER_MD = Path("assets/houdini/hfx_factory_core12/00_INDEX_资产索引/HFX_CORE12_COMPLETION_LEDGER.md")
DEFERRED_MD = Path("assets/houdini/hfx_factory_core12/00_INDEX_资产索引/HFX_EXTERNAL_ASSET_DECISION_DEFERRED.md")
PLAN_MD = Path("assets/houdini/hfx_factory_core12/00_INDEX_资产索引/HFX_100_PERCENT_COMPLETION_PLAN.md")


def valid_material() -> dict[str, object]:
    assets = []
    for spec in HFX_CORE12_ASSETS:
        assets.append(
            {
                "asset_id": spec["asset_id"],
                "asset_name": spec["asset_name"],
                "completion_status": "gold_complete",
                "validated_evidence": True,
            }
        )
    return {
        "ledger_id": "hfx-core12-ledger-test",
        "repository_url": "https://github.com/qqyqqyqqy666-wq/sovereign-engineering-os",
        "main_commit": "d13e9aa8f65c8b64d3da08b9a55ff5087b87beb3",
        "core12_assets": assets,
        "gold_assets": [asset["asset_id"] for asset in assets],
        "production_candidates": [],
        "partial_candidates": [],
        "shell_only_assets": [],
        "blocked_assets": [],
        "external_asset_policy": "Deferred; no GitHub storage decision made; local-first until license review.",
        "next_required_actions": ["Continue internal closure."],
        "completion_decision": "complete",
        "policy_version": "hfx-core12-completion-ledger-v1",
        "code_version": "0.1.0",
    }


class HFXCore12CompletionLedgerTests(unittest.TestCase):
    def test_valid_ledger_builds_deterministic_object(self):
        ledger = build_hfx_core12_completion_ledger(valid_material())

        self.assertIsInstance(ledger, HFXCore12CompletionLedger)
        self.assertEqual(ledger.content_hash, digest_payload(ledger.deterministic_material()))

    def test_content_hash_excludes_observed_at(self):
        self.assertEqual(
            build_hfx_core12_completion_ledger(valid_material(), observed_at="one").content_hash,
            build_hfx_core12_completion_ledger(valid_material(), observed_at="two").content_hash,
        )

    def test_markdown_deterministic(self):
        ledger = build_hfx_core12_completion_ledger(valid_material())

        self.assertEqual(
            render_hfx_core12_completion_ledger_markdown(ledger),
            render_hfx_core12_completion_ledger_markdown(ledger),
        )

    def test_incomplete_asset_blocks_complete(self):
        material = valid_material()
        material["core12_assets"][1]["completion_status"] = "production_candidate"

        with self.assertRaises(ValueError):
            build_hfx_core12_completion_ledger(material)

    def test_generated_ledger_exists(self):
        self.assertTrue(LEDGER_JSON.is_file())
        self.assertTrue(LEDGER_MD.is_file())

    def test_ledger_lists_all_12_assets(self):
        payload = json.loads(LEDGER_JSON.read_text(encoding="utf-8"))
        asset_ids = [asset["asset_id"] for asset in payload["core12_assets"]]

        self.assertEqual(asset_ids, [spec["asset_id"] for spec in HFX_CORE12_ASSETS])

    def test_ledger_does_not_decide_external_asset_github_policy(self):
        payload = json.loads(LEDGER_JSON.read_text(encoding="utf-8"))
        policy = payload["external_asset_policy"].lower()

        self.assertIn("deferred", policy)
        self.assertIn("no github storage decision", policy)
        self.assertNotIn("commit external raw assets", policy)

    def test_deferred_external_asset_record_exists(self):
        text = DEFERRED_MD.read_text(encoding="utf-8").lower()

        self.assertIn("external friend assets are not part of this branch", text)
        self.assertIn("no github storage decision is made", text)
        self.assertIn("local-first", text)

    def test_completion_plan_does_not_claim_current_100_percent(self):
        text = PLAN_MD.read_text(encoding="utf-8").lower()

        self.assertIn("does not claim current 100%", text)
        self.assertIn("no fake film-grade claims", text)

    def test_source_safety_passes(self):
        source = Path("kernel/runtime/hfx_core12_completion_ledger.py").read_text(encoding="utf-8")
        for marker in ("subprocess", "socket", "requests", "httpx", "sqlite3", "os.environ", "os.getenv", "load_dotenv"):
            self.assertNotIn(marker, source)


if __name__ == "__main__":
    unittest.main()
