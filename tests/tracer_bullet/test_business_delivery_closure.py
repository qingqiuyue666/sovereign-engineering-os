"""Tracer-bullet tests for business delivery closure."""

from __future__ import annotations

from pathlib import Path
import unittest

from kernel.audit.hashchain import digest_payload
from kernel.runtime.business_delivery_closure import (
    BusinessDeliveryClosure,
    build_business_delivery_closure,
    render_business_delivery_closure_markdown,
)


BUSINESS_DOCS = (
    "docs/operator/business_delivery/README.md",
    "docs/operator/business_delivery/code_audit_delivery_package.md",
    "docs/operator/business_delivery/private_engineering_audit_service_scope.md",
    "docs/operator/business_delivery/operator_system_delivery_package.md",
    "docs/operator/business_delivery/client_intake_private_system_review.md",
    "docs/operator/business_delivery/quote_scope_template.md",
    "docs/operator/business_delivery/delivery_checklist.md",
    "docs/operator/business_delivery/case_study_template_real_system_use_run.md",
    "docs/operator/business_delivery/do_not_offer_list.md",
)


def valid_material() -> dict[str, object]:
    gates = {
        "delivery_package_exists": True,
        "service_scope_exists": True,
        "client_intake_exists": True,
        "quote_scope_template_exists": True,
        "delivery_checklist_exists": True,
        "case_study_template_exists": True,
        "do_not_offer_list_exists": True,
        "no_trading_service_offered": True,
        "no_provider_execution_claim": True,
        "no_production_autonomy_claim": True,
        "no_houdini_vfx_delivery_claim_in_this_slice": True,
        "human_review_required": True,
    }
    return {
        "closure_id": "business-delivery-closure-test",
        "repository_url": "https://github.com/qqyqqyqqy666-wq/sovereign-engineering-os",
        "main_commit": "d98f29ebf25cae196098121ce1632de727393a2d",
        "closure_gates": gates,
        "delivery_docs": ["delivery package", "service scope", "client intake", "do-not-offer list"],
        "blocked_capabilities": ["provider execution blocked", "trading automation blocked"],
        "human_review_required": True,
        "completion_decision": "complete",
        "remaining_gaps": [],
        "rollback_notes": ["revert business docs"],
        "policy_version": "business-delivery-closure-v1",
        "code_version": "0.1.0",
    }


class BusinessDeliveryClosureTests(unittest.TestCase):
    def test_valid_closure_builds_deterministic_object(self):
        closure = build_business_delivery_closure(valid_material())

        self.assertIsInstance(closure, BusinessDeliveryClosure)
        self.assertEqual(closure.content_hash, digest_payload(closure.deterministic_material()))

    def test_content_hash_excludes_observed_at(self):
        self.assertEqual(
            build_business_delivery_closure(valid_material(), observed_at="one").content_hash,
            build_business_delivery_closure(valid_material(), observed_at="two").content_hash,
        )

    def test_markdown_deterministic(self):
        closure = build_business_delivery_closure(valid_material())

        self.assertEqual(render_business_delivery_closure_markdown(closure), render_business_delivery_closure_markdown(closure))

    def test_missing_delivery_package_blocks_complete(self):
        material = valid_material()
        material["closure_gates"]["delivery_package_exists"] = False

        with self.assertRaises(ValueError):
            build_business_delivery_closure(material)

    def test_missing_do_not_offer_list_blocks_complete(self):
        material = valid_material()
        material["closure_gates"]["do_not_offer_list_exists"] = False

        with self.assertRaises(ValueError):
            build_business_delivery_closure(material)

    def test_trading_service_claim_blocks_complete(self):
        material = valid_material()
        material["delivery_docs"].append("we offer trading service")

        with self.assertRaises(ValueError):
            build_business_delivery_closure(material)

    def test_provider_execution_claim_blocks_complete(self):
        material = valid_material()
        material["delivery_docs"].append("provider execution included")

        with self.assertRaises(ValueError):
            build_business_delivery_closure(material)

    def test_generated_docs_exist(self):
        for path in BUSINESS_DOCS:
            self.assertTrue(Path(path).is_file(), path)
        self.assertTrue(Path("docs/operator/generated/business_delivery_closure.md").is_file())

    def test_readme_says_private_delivery_only(self):
        text = Path("docs/operator/business_delivery/README.md").read_text(encoding="utf-8").lower()

        self.assertIn("private delivery only", text)

    def test_runtime_source_safety_passes(self):
        source = Path("kernel/runtime/business_delivery_closure.py").read_text(encoding="utf-8")
        for marker in ("subprocess", "socket", "requests", "httpx", "sqlite3", "os.environ", "os.getenv", "load_dotenv"):
            self.assertNotIn(marker, source)


if __name__ == "__main__":
    unittest.main()
