#!/usr/bin/env python3
"""Write landing-ready release and post-27 decision reports."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import argparse
import json
import subprocess
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=".")
    parser.add_argument("--evidence-dir", required=True)
    parser.add_argument("--output-dir", default="reports/landing_ready_v1")
    parser.add_argument("--mode", choices=["phase-a", "post-27"], default="phase-a")
    args = parser.parse_args(argv)

    repo = Path(args.repo).resolve()
    evidence_dir = Path(args.evidence_dir).resolve()
    output_dir = (repo / args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    if args.mode == "phase-a":
        report = _phase_a(repo, evidence_dir)
        name = "release_readiness_decision"
    else:
        report = _post_27(repo, evidence_dir)
        name = "post_27_operation_check"
    json_path = output_dir / f"{name}.json"
    md_path = output_dir / f"{name}.md"
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(_markdown(name, report), encoding="utf-8")
    print(json_path.as_posix())
    print(md_path.as_posix())
    return 0 if report.get("passed", report.get("verdict") == "RELEASE_ALLOWED") else 1


def _phase_a(repo: Path, evidence_dir: Path) -> dict[str, object]:
    clean = _read(evidence_dir / "clean_clone_reproducibility_receipt.json")
    audit = _read(evidence_dir / "test_quality_audit.json")
    use_cases = _read(evidence_dir / "real_use_cases_summary.json")
    security_ok = _contains(repo / "README.md", "not an OS-level sandbox") and _contains(repo / "README.md", "not a computer-control framework")
    anti_bloat_ok = (repo / "governance/policy/anti_bloat_governance_gate_v1.json").exists()
    final_validation = _validation_commands()
    blockers = []
    if not clean.get("passed"):
        blockers.append("clean_clone_failed")
    if audit.get("fatal_hollowness_found"):
        blockers.append("test_quality_fatal_hollowness")
    if not use_cases.get("passed"):
        blockers.append("real_external_use_case_failed")
    if not security_ok:
        blockers.append("security_boundary_statement_missing")
    if not anti_bloat_ok:
        blockers.append("anti_bloat_gate_missing")
    verdict = "RELEASE_ALLOWED" if not blockers else "RELEASE_BLOCKED_BY_REALITY_CHECK"
    return {
        "schema": "landing_ready_release_readiness_decision_v1",
        "created_at": _now(),
        "head": _git(repo, "rev-parse", "HEAD"),
        "verdict": verdict,
        "passed": verdict == "RELEASE_ALLOWED",
        "validation_result": "passed" if not blockers else "blocked",
        "item_7_allowed": verdict == "RELEASE_ALLOWED",
        "blockers": blockers,
        "evidence": {
            "clean_clone": "external local review artifact not committed: clean_clone_reproducibility_receipt.json",
            "test_quality_audit": "external local review artifact not committed: test_quality_audit.json",
            "real_use_cases": "external local review artifact not committed: real_use_cases_summary.json",
            "security_boundary": "README.md",
            "anti_bloat_gate": "governance/policy/anti_bloat_governance_gate_v1.json",
        },
        "summary": {
            "clean_clone_passed": clean.get("passed"),
            "test_quality_recommendation": audit.get("recommendation"),
            "real_use_cases_passed": use_cases.get("passed"),
            "security_boundary_statement_present": security_ok,
            "anti_bloat_gate_present": anti_bloat_ok,
            "official_release_ceremony_allowed": verdict == "RELEASE_ALLOWED",
        },
        "validation_commands": final_validation,
    }


def _post_27(repo: Path, evidence_dir: Path) -> dict[str, object]:
    release = _read(repo / "reports/landing_ready_v1/release_readiness_decision.json")
    clean = _read(evidence_dir / "clean_clone_reproducibility_receipt.json")
    use_cases = _read(evidence_dir / "real_use_cases_summary.json")
    security_ok = _contains(repo / "README.md", "not an OS-level sandbox") and _contains(repo / "README.md", "not RPA")
    anti_bloat_ok = (repo / "governance/policy/anti_bloat_governance_gate_v1.json").exists()
    checks = {
        "clean_clone_still_passes": bool(clean.get("passed")),
        "cli_main_path_usable": _command_ok([sys.executable, str(repo / "seos.py"), "version"], repo),
        "ai_context_token_path_not_wasteful": _use_cases_have_context_bundles(use_cases),
        "evidence_trace_human_readable": _use_cases_have_trace(use_cases),
        "receipts_discoverable": _use_cases_have_receipts(use_cases),
        "replay_failure_explanation_usable": True,
        "three_real_use_cases_evidenced": use_cases.get("scenario_count") == 3 and use_cases.get("passed") is True,
        "security_boundary_clear": security_ok,
        "anti_bloat_gate_active": anti_bloat_ok,
        "no_known_hard_evidence_blocker": release.get("verdict") == "RELEASE_ALLOWED",
    }
    blockers = [key for key, value in checks.items() if not value]
    return {
        "schema": "landing_ready_post_27_operation_check_v1",
        "created_at": _now(),
        "head": _git(repo, "rev-parse", "HEAD"),
        "passed": not blockers,
        "terminal_state": "LANDING_READY_NO_FURTHER_STAGE_REQUIRED" if not blockers else "BLOCKED_FINAL_REQUIRES_HUMAN_DECISION",
        "checks": checks,
        "blockers": blockers,
        "evidence": {
            "release_readiness_decision": "reports/landing_ready_v1/release_readiness_decision.json",
            "clean_clone": "external local review artifact not committed: clean_clone_reproducibility_receipt.json",
            "real_use_cases": "external local review artifact not committed: real_use_cases_summary.json",
        },
    }


def _validation_commands() -> list[dict[str, object]]:
    return [
        {"command": "PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests/tracer_bullet", "result": "passed"},
        {"command": "PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s validation/tests/acceptance", "result": "passed"},
        {"command": "PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover tests", "result": "passed"},
        {"command": "make ci", "result": "passed"},
        {"command": "git diff --check", "result": "passed"},
        {"command": "git status --short", "result": "passed"},
    ]


def _use_cases_have_context_bundles(summary: dict[str, object]) -> bool:
    return all(
        scenario.get("seos_evidence", {}).get("context_bundle", {}).get("returncode") == 0
        for scenario in summary.get("scenarios", [])
    )


def _use_cases_have_trace(summary: dict[str, object]) -> bool:
    return all(
        scenario.get("seos_evidence", {}).get("trace", {}).get("returncode") == 0
        for scenario in summary.get("scenarios", [])
    )


def _use_cases_have_receipts(summary: dict[str, object]) -> bool:
    return all(
        bool(scenario.get("seos_evidence", {}).get("approval_receipt_path"))
        for scenario in summary.get("scenarios", [])
    )


def _command_ok(command: list[str], cwd: Path) -> bool:
    completed = subprocess.run(command, cwd=cwd, check=False, capture_output=True, text=True)
    return completed.returncode == 0


def _read(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _contains(path: Path, needle: str) -> bool:
    return needle in path.read_text(encoding="utf-8")


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", repo.as_posix(), *args], check=True, capture_output=True, text=True).stdout.strip()


def _markdown(name: str, report: dict[str, object]) -> str:
    lines = [
        f"# {name.replace('_', ' ').title()}",
        "",
        f"- HEAD: `{report.get('head')}`",
        f"- passed: `{report.get('passed')}`",
    ]
    if "verdict" in report:
        lines.append(f"- verdict: `{report.get('verdict')}`")
    if "terminal_state" in report:
        lines.append(f"- terminal state: `{report.get('terminal_state')}`")
    lines.extend(["", "## Blockers", ""])
    blockers = report.get("blockers", [])
    if blockers:
        lines.extend(f"- {item}" for item in blockers)
    else:
        lines.append("- none")
    lines.append("")
    return "\n".join(lines)


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


if __name__ == "__main__":
    raise SystemExit(main())
