import ast
import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]

CAPABILITY_MODULES = (
    "kernel/capabilities/github_capability_intake_packet.py",
    "kernel/capabilities/playwright_local_fixture_sandbox_smoke.py",
    "kernel/capabilities/bounded_playwright_worker_adapter_draft.py",
    "kernel/capabilities/operator_provided_playwright_execution_receipt.py",
    "kernel/capabilities/local_fixture_playwright_adapter_admission_gate.py",
    "kernel/capabilities/local_only_playwright_fixture_scenario_suite.py",
    "kernel/capabilities/playwright_local_admission_receipt_aggregation.py",
    "kernel/capabilities/admission_gated_local_adapter_registry_promotion.py",
    "kernel/capabilities/local_fixture_adapter_usage_receipt.py",
    "kernel/capabilities/local_fixture_adapter_dry_run_invocation_plan.py",
    "kernel/capabilities/local_fixture_adapter_execution_gate_plan.py",
)

CHAIN_SOURCE_FILES = CAPABILITY_MODULES + (
    "tools/playwright/local_fixture_smoke_runner.js",
)

DECISION_DOCS = (
    "docs/decisions/github_capability_intake_packet_lite_v1.md",
    "docs/decisions/real_github_candidate_evaluation_pack_v1.md",
    "docs/decisions/playwright_local_fixture_bounded_sandbox_smoke_v1.md",
    "docs/decisions/bounded_playwright_worker_adapter_draft_v1.md",
    "docs/decisions/operator_provided_playwright_execution_receipt_v1.md",
    "docs/decisions/local_fixture_playwright_adapter_admission_gate_v1.md",
    "docs/decisions/local_only_playwright_fixture_scenario_suite_v1.md",
    "docs/decisions/playwright_local_admission_receipt_aggregation_v1.md",
    "docs/decisions/local_only_playwright_regression_pack_v1.md",
    "docs/decisions/playwright_suite_aggregation_admission_gate_binding_v1.md",
    "docs/decisions/admission_gated_local_adapter_registry_promotion_v1.md",
    "docs/decisions/local_fixture_adapter_usage_receipt_v1.md",
    "docs/decisions/local_fixture_adapter_dry_run_invocation_plan_v1.md",
    "docs/decisions/local_fixture_adapter_execution_gate_plan_v1.md",
    "docs/decisions/local_fixture_chain_status_v1.md",
)

FORBIDDEN_CLI_FLAGS = (
    "--url",
    "--target-url",
    "--website",
    "--account",
    "--credential",
    "--cookie",
    "--scrape",
    "--bypass",
    "--captcha",
    "--execute",
    "--approve",
    "--approval-token",
    "--browser",
    "--open-browser",
    "--playwright",
)

FORBIDDEN_FLAG_PATTERN = re.compile(
    r"(?<![\w-])("
    + "|".join(re.escape(flag) for flag in sorted(FORBIDDEN_CLI_FLAGS, key=len, reverse=True))
    + r")(?![\w-])"
)

EXECUTION_GATE_MODULE = (
    REPO_ROOT
    / "kernel"
    / "capabilities"
    / "local_fixture_adapter_execution_gate_plan.py"
)
DRY_RUN_MODULE = (
    REPO_ROOT
    / "kernel"
    / "capabilities"
    / "local_fixture_adapter_dry_run_invocation_plan.py"
)
USAGE_RECEIPT_MODULE = (
    REPO_ROOT
    / "kernel"
    / "capabilities"
    / "local_fixture_adapter_usage_receipt.py"
)
EXECUTION_GATE_TEST = (
    REPO_ROOT
    / "tests"
    / "tracer_bullet"
    / "test_local_fixture_adapter_execution_gate_plan.py"
)
STATUS_DOC = REPO_ROOT / "docs" / "decisions" / "local_fixture_chain_status_v1.md"
RUNBOOK = (
    REPO_ROOT
    / "docs"
    / "runbooks"
    / "local_fixture_chain_regression_presweep_v1.md"
)


def read_repo_text(relative_path):
    return (REPO_ROOT / relative_path).read_text(encoding="utf-8")


class LocalFixtureChainHealthPresweepTests(unittest.TestCase):
    def test_relevant_capability_modules_exist(self):
        for relative_path in CAPABILITY_MODULES:
            self.assertTrue((REPO_ROOT / relative_path).is_file(), relative_path)

    def test_relevant_decision_docs_exist_for_latest_merged_chain(self):
        for relative_path in DECISION_DOCS:
            self.assertTrue((REPO_ROOT / relative_path).is_file(), relative_path)

    def test_status_doc_records_required_presweep_boundaries(self):
        text = " ".join(STATUS_DOC.read_text(encoding="utf-8").lower().split())
        required_fragments = (
            "local fixture only",
            "non-production only",
            "no live website admission",
            "no general browser automation admission",
            "no autonomous execution",
            "no approval token",
            "no execution token",
            "no runner",
            "no runnable job",
            "no browser open",
            "no network access",
            "no adapter execution",
            "no playwright execution",
            "human review is required before future execution",
            "future runner requires separate pr",
            "future runner receipt required",
            "artifact index / manifest pattern",
            "deterministic rejection reasons",
        )
        for fragment in required_fragments:
            self.assertIn(fragment, text)

    def test_presweep_runbook_exists_and_stays_non_executable(self):
        text = " ".join(RUNBOOK.read_text(encoding="utf-8").lower().split())
        required_fragments = (
            "local-only evidence review",
            "does not create a runner",
            "does not create a token",
            "does not create a runnable job",
            "does not create a browser session",
            "does not create a network path",
            "does not create a playwright execution path",
            "future runner requires separate pr",
            "future runner receipt required",
        )
        for fragment in required_fragments:
            self.assertIn(fragment, text)

    def test_execution_gate_module_has_no_execution_affordance_imports_or_calls(self):
        source = EXECUTION_GATE_MODULE.read_text(encoding="utf-8")
        tree = ast.parse(source)
        forbidden_import_roots = {
            "http",
            "os",
            "playwright",
            "requests",
            "selenium",
            "socket",
            "subprocess",
            "urllib",
            "webbrowser",
        }
        imported_roots = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_roots.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported_roots.add(node.module.split(".")[0])
        self.assertFalse(forbidden_import_roots & imported_roots)

        forbidden_call_names = {
            "async_playwright",
            "call",
            "check_call",
            "check_output",
            "connect_over_cdp",
            "create_connection",
            "launch",
            "open_new",
            "open_new_tab",
            "Popen",
            "popen",
            "run",
            "startfile",
            "sync_playwright",
            "system",
            "urlopen",
        }
        seen_calls = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func = node.func
                if isinstance(func, ast.Name):
                    seen_calls.add(func.id)
                elif isinstance(func, ast.Attribute):
                    seen_calls.add(func.attr)
        self.assertFalse(forbidden_call_names & seen_calls)
        self.assertNotIn("execution_token", source)

    def test_execution_gate_tests_retain_usage_receipt_hash_and_root_bindings(self):
        source = EXECUTION_GATE_TEST.read_text(encoding="utf-8")
        required_fragments = (
            "test_usage_receipt_sha_mismatch_rejects",
            "usage_receipt_sha_mismatch",
            "test_usage_receipt_path_widening_cannot_admit_outside_fixture",
            "usage_receipt_type_mismatch",
            "usage_receipt_not_granted",
            "test_local_fixture_allowed_root_mismatch_rejects",
            "dry_run_plan_local_fixture_allowed_root_mismatch",
            "test_local_fixture_allowed_root_widening_cannot_admit_outside_fixture",
            "local_fixture_path_outside_allowed_root",
        )
        for fragment in required_fragments:
            self.assertIn(fragment, source)

    def test_dry_run_and_execution_gate_modules_retain_output_dir_mismatch_protection(self):
        dry_run_source = DRY_RUN_MODULE.read_text(encoding="utf-8")
        execution_gate_source = EXECUTION_GATE_MODULE.read_text(encoding="utf-8")

        self.assertIn("_usage_receipt_output_dir_rejection_reasons", dry_run_source)
        self.assertIn("usage_receipt_output_dir_mismatch", dry_run_source)
        self.assertIn("source_path.parent", dry_run_source)

        self.assertIn("_dry_run_plan_output_dir_rejection_reasons", execution_gate_source)
        self.assertIn("dry_run_plan_output_dir_mismatch", execution_gate_source)
        self.assertIn("source_path.parent", execution_gate_source)

    def test_future_execution_gate_strings_are_present(self):
        source = EXECUTION_GATE_MODULE.read_text(encoding="utf-8")
        status_doc = STATUS_DOC.read_text(encoding="utf-8")
        for text in (source, status_doc):
            self.assertIn(
                "future_execution_requires_separate_human_approval_artifact",
                text,
            )
            self.assertIn(
                "future_execution_requires_separate_execution_runner_pr",
                text,
            )

    def test_capability_outputs_keep_artifact_index_manifest_pattern(self):
        for relative_path in CAPABILITY_MODULES:
            source = read_repo_text(relative_path)
            self.assertIn("artifact_index.json", source, relative_path)
            self.assertIn("artifact_index_manifest.json", source, relative_path)

    def test_deterministic_rejection_reasons_cover_critical_boundaries(self):
        combined = "\n".join(
            path.read_text(encoding="utf-8")
            for path in (USAGE_RECEIPT_MODULE, DRY_RUN_MODULE, EXECUTION_GATE_MODULE)
        )
        required_reasons = (
            "forbidden_admission_claimed",
            "performed_forbidden_action",
            "local_fixture_reference_forbidden_scheme",
            "local_fixture_path_outside_allowed_root",
            "usage_receipt_output_dir_mismatch",
            "dry_run_plan_output_dir_mismatch",
            "approval_material_claimed",
            "runnable_job_claimed",
        )
        for reason in required_reasons:
            self.assertIn(reason, combined)

    def test_local_fixture_chain_source_contains_no_forbidden_cli_flags(self):
        for relative_path in CHAIN_SOURCE_FILES:
            source = read_repo_text(relative_path)
            matches = sorted(set(FORBIDDEN_FLAG_PATTERN.findall(source)))
            self.assertEqual([], matches, relative_path)


if __name__ == "__main__":
    unittest.main()
