#!/usr/bin/env python3
"""Validate Wave 6 AI-provider admission safety evidence."""

from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

REQUIRED_DOCS = (
    Path("docs/ai_admission/ai_provider_admission_policy_v1.md"),
    Path("docs/ai_admission/proposal_first_policy_v1.md"),
    Path("docs/ai_admission/provider_secret_ref_policy_v1.md"),
    Path("docs/ai_admission/context_redaction_policy_v1.md"),
    Path("docs/ai_admission/token_budget_policy_v1.md"),
    Path("docs/ai_admission/model_output_artifact_policy_v1.md"),
    Path("docs/ai_admission/human_approval_before_patch_policy_v1.md"),
    Path("docs/ai_admission/provider_failure_policy_v1.md"),
)

REQUIRED_TERMS = (
    "providers disabled by default",
    "secret-ref only",
    "no API key printing",
    "no `.env` reading by default",
    "request envelope",
    "response receipt",
    "network access receipt",
    "token budget ceiling",
    "context redaction",
    "prompt provenance",
    "model output artifact",
    "proposal-first",
    "patch requires human approval",
    "validation before PR",
    "deterministic mock provider only unless explicit future admission",
    "no direct AI execution",
)

FORBIDDEN_CLAIMS = (
    "GLOBAL_RECOGNITION_CONFIRMED",
    "externally certified",
    "world class confirmed",
)

LOCAL_PATH_MARKERS = (
    "/" + "Users" + "/" + "qqy",
    "Documents" + "/" + "Codex",
    "." + "codex",
    "files-mentioned" + "-by-the-user",
)


def main() -> int:
    errors: list[str] = []
    texts = _load_docs(errors)
    _check_required_terms(texts, errors)
    _check_public_safety(texts, errors)
    _check_provider_registry(errors)
    _check_ci_gate(errors)

    if errors:
        print("ai_admission_check_v1: FAIL")
        for error in errors:
            print(f"- {error}")
        return 1

    print("ai_admission_check_v1: PASS")
    return 0


def _load_docs(errors: list[str]) -> dict[Path, str]:
    texts: dict[Path, str] = {}
    for relative_path in REQUIRED_DOCS:
        path = REPO_ROOT / relative_path
        if not path.exists():
            errors.append(f"missing AI admission doc: {relative_path.as_posix()}")
            continue
        texts[relative_path] = path.read_text(encoding="utf-8")
    return texts


def _check_required_terms(texts: dict[Path, str], errors: list[str]) -> None:
    combined = "\n".join(texts.values())
    combined_lower = combined.lower()
    for term in REQUIRED_TERMS:
        if term.lower() not in combined_lower:
            errors.append(f"missing AI admission safety term: {term}")


def _check_public_safety(texts: dict[Path, str], errors: list[str]) -> None:
    for relative_path, text in texts.items():
        lower = text.lower()
        for marker in LOCAL_PATH_MARKERS:
            if marker in text:
                errors.append(f"{relative_path.as_posix()} contains local path marker: {marker}")
        for claim in FORBIDDEN_CLAIMS:
            if claim.lower() in lower:
                errors.append(f"{relative_path.as_posix()} contains forbidden claim: {claim}")
        if "external review" not in lower and relative_path.name == "ai_provider_admission_policy_v1.md":
            errors.append(f"{relative_path.as_posix()} missing external review boundary")


def _check_provider_registry(errors: list[str]) -> None:
    from kernel.personal_ai.adapters.model_adapter_contract import build_model_provider_registry

    providers = {entry.provider_id: entry for entry in build_model_provider_registry()}
    mock = providers.get("deterministic_mock")
    if mock is None:
        errors.append("provider registry missing deterministic_mock")
    elif not mock.admitted or not mock.enabled_by_default or mock.live_provider_runtime:
        errors.append("deterministic_mock must be the only default admitted non-live provider")

    for provider_id, provider in providers.items():
        policy = provider.policy
        if provider.live_provider_runtime:
            if provider.admitted or provider.enabled_by_default:
                errors.append(f"live provider must be disabled by default: {provider_id}")
            if policy.get("real_provider_calls_allowed") is not False:
                errors.append(f"live provider real calls must remain disabled: {provider_id}")
            if policy.get("api_key_persistence_allowed") is not False:
                errors.append(f"live provider API key persistence must be disabled: {provider_id}")
            if policy.get("api_key_logging_allowed") is not False:
                errors.append(f"live provider API key logging must be disabled: {provider_id}")
        if policy.get("network_allowed_by_default") is not False:
            errors.append(f"provider network must be disabled by default: {provider_id}")


def _check_ci_gate(errors: list[str]) -> None:
    ci_path = REPO_ROOT / ".github" / "workflows" / "ci.yml"
    makefile_path = REPO_ROOT / "Makefile"
    ci_text = ci_path.read_text(encoding="utf-8") if ci_path.exists() else ""
    makefile_text = makefile_path.read_text(encoding="utf-8") if makefile_path.exists() else ""
    for path, text in ((ci_path, ci_text), (makefile_path, makefile_text)):
        if "scripts/ai_admission_check_v1.py" not in text:
            errors.append(f"{path.relative_to(REPO_ROOT).as_posix()} missing AI admission gate")


if __name__ == "__main__":
    raise SystemExit(main())
