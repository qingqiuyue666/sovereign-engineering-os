import ast
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]

CHAIN_MODULES = {
    "execution_gate_plan": REPO_ROOT
    / "kernel"
    / "capabilities"
    / "local_fixture_adapter_execution_gate_plan.py",
    "human_approval_artifact": REPO_ROOT
    / "kernel"
    / "capabilities"
    / "local_fixture_human_approval_artifact.py",
    "runner_contract_draft": REPO_ROOT
    / "kernel"
    / "capabilities"
    / "local_fixture_runner_contract_draft.py",
}

MERGED_TESTS = (
    REPO_ROOT
    / "tests"
    / "tracer_bullet"
    / "test_local_fixture_adapter_execution_gate_plan.py",
    REPO_ROOT
    / "tests"
    / "tracer_bullet"
    / "test_local_fixture_human_approval_artifact.py",
    REPO_ROOT
    / "tests"
    / "tracer_bullet"
    / "test_local_fixture_runner_contract_draft.py",
)

MERGED_DECISION_DOCS = (
    REPO_ROOT
    / "docs"
    / "decisions"
    / "local_fixture_adapter_execution_gate_plan_v1.md",
    REPO_ROOT
    / "docs"
    / "decisions"
    / "local_fixture_human_approval_artifact_v1.md",
    REPO_ROOT
    / "docs"
    / "decisions"
    / "local_fixture_runner_contract_draft_v1.md",
)

PRESWEEP_DOCS = (
    REPO_ROOT
    / "docs"
    / "decisions"
    / "local_fixture_human_runner_chain_status_v1.md",
    REPO_ROOT
    / "docs"
    / "runbooks"
    / "local_fixture_human_runner_chain_presweep_v1.md",
)

ARTIFACT_INDEX_OUTPUTS = {
    "artifact_index.json",
    "artifact_index_manifest.json",
}

DANGEROUS_IMPORT_ROOTS = {
    "httpx",
    "playwright",
    "requests",
    "selenium",
    "socket",
    "subprocess",
    "urllib",
    "webbrowser",
}

DANGEROUS_CALL_NAMES = {
    "Popen",
    "async_playwright",
    "create_connection",
    "goto",
    "launch",
    "open_new",
    "popen",
    "run",
    "sync_playwright",
    "system",
    "urlopen",
}

HUMAN_APPROVAL_REQUIRED_LITERALS = {
    "adapter_execution_performed",
    "approval_token_issued",
    "autonomous_execution_performed",
    "browser_open_performed",
    "execution_token_issued",
    "future_execution_requires_separate_runner_receipt",
    "future_runner_requires_separate_pr",
    "live_website_access_performed",
    "metadata_only",
    "network_access_performed",
    "playwright_execution_performed",
    "production_promotion_granted",
    "required_human_approval",
    "required_human_review",
    "runnable_job_created",
    "runner_created",
    "source_execution_gate_plan_sha256",
}

RUNNER_CONTRACT_REQUIRED_LITERALS = {
    "adapter_execution_performed",
    "approval_token_issued",
    "artifact_index.json",
    "autonomous_execution_performed",
    "browser_open_performed",
    "contract_only",
    "execution_token_issued",
    "future_runner_requires_artifact_index",
    "future_runner_requires_runner_receipt",
    "future_runner_requires_separate_implementation_pr",
    "future_runner_requires_verified_execution_gate_plan",
    "future_runner_requires_verified_human_approval_artifact",
    "live_website_access_performed",
    "metadata_only",
    "network_access_performed",
    "playwright_execution_performed",
    "production_promotion_granted",
    "runnable_job_created",
    "runner_created",
}

DOC_REQUIRED_FRAGMENTS = (
    "local-fixture only",
    "non-production only",
    "no live website admission",
    "no general browser automation admission",
    "no autonomous execution",
    "no token issuance",
    "no approval token",
    "no execution token",
    "no runner",
    "no runnable job",
    "no browser open",
    "no network access",
    "no adapter execution",
    "no playwright execution",
    "future runner requires separate pr",
    "future runner receipt required",
    "human review remains required",
)


def parse_module(path):
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def string_literals(path):
    tree = parse_module(path)
    return {
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    }


def normalized_doc_text(path):
    return " ".join(path.read_text(encoding="utf-8").split()).lower()


def dangerous_imports(tree):
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".", 1)[0]
                if root in DANGEROUS_IMPORT_ROOTS:
                    imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            root = node.module.split(".", 1)[0]
            if root in DANGEROUS_IMPORT_ROOTS:
                imports.append(node.module)
    return imports


def call_name(call):
    func = call.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def dangerous_calls(tree):
    calls = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            name = call_name(node)
            if name in DANGEROUS_CALL_NAMES:
                calls.append((name, node.lineno))
    return calls


class LocalFixtureHumanRunnerChainPresweepTests(unittest.TestCase):
    def test_required_merged_modules_tests_and_decision_docs_exist(self):
        required_paths = (
            tuple(CHAIN_MODULES.values())
            + MERGED_TESTS
            + MERGED_DECISION_DOCS
            + PRESWEEP_DOCS
        )

        for path in required_paths:
            with self.subTest(path=path):
                self.assertTrue(path.is_file(), path)

    def test_human_approval_artifact_module_preserves_static_boundaries(self):
        literals = string_literals(CHAIN_MODULES["human_approval_artifact"])
        missing = HUMAN_APPROVAL_REQUIRED_LITERALS - literals

        self.assertEqual(missing, set())

    def test_runner_contract_draft_module_preserves_static_boundaries(self):
        literals = string_literals(CHAIN_MODULES["runner_contract_draft"])
        missing = RUNNER_CONTRACT_REQUIRED_LITERALS - literals

        self.assertEqual(missing, set())

    def test_chain_modules_keep_artifact_index_output_pattern(self):
        for label, path in CHAIN_MODULES.items():
            with self.subTest(module=label):
                literals = string_literals(path)
                missing = ARTIFACT_INDEX_OUTPUTS - literals
                self.assertEqual(missing, set())

    def test_chain_modules_avoid_dangerous_runtime_imports_and_calls(self):
        for label, path in CHAIN_MODULES.items():
            with self.subTest(module=label):
                tree = parse_module(path)

                self.assertEqual(dangerous_imports(tree), [])
                self.assertEqual(dangerous_calls(tree), [])

    def test_chain_presweep_docs_state_non_runtime_boundary(self):
        for doc_path in PRESWEEP_DOCS:
            with self.subTest(doc=doc_path):
                text = normalized_doc_text(doc_path)
                for fragment in DOC_REQUIRED_FRAGMENTS:
                    self.assertIn(fragment, text)


if __name__ == "__main__":
    unittest.main()
