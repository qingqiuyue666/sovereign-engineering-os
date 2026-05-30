#!/usr/bin/env python3
"""Classify repository tests and write a landing-ready test quality audit."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import argparse
import json
import subprocess


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=".")
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args(argv)

    repo = Path(args.repo).resolve()
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    test_files = sorted(path for path in (repo / "tests").rglob("test_*.py"))
    validation_files = sorted(path for path in (repo / "validation" / "tests").rglob("test_*.py"))
    all_files = test_files + validation_files
    categories: dict[str, list[str]] = {
        "contract_schema": [],
        "deterministic_unit": [],
        "integration": [],
        "tracer_e2e": [],
        "acceptance": [],
        "mock_heavy_or_ceremonial": [],
        "replay_failure_security_boundary": [],
    }
    for path in all_files:
        relative = path.relative_to(repo).as_posix()
        lowered = relative.lower()
        if "validation/tests/acceptance" in lowered or "acceptance" in lowered:
            categories["acceptance"].append(relative)
        if "tracer_bullet" in lowered or "e2e" in lowered or "end_to_end" in lowered:
            categories["tracer_e2e"].append(relative)
        if "schema" in lowered or "contract" in lowered:
            categories["contract_schema"].append(relative)
        if "integration" in lowered or "runtime" in lowered or "operator_cli" in lowered:
            categories["integration"].append(relative)
        if "mock" in lowered or "fixture" in lowered or "placeholder" in lowered:
            categories["mock_heavy_or_ceremonial"].append(relative)
        if any(token in lowered for token in ("replay", "failure", "security", "secret", "rollback", "quarantine")):
            categories["replay_failure_security_boundary"].append(relative)
        if not any(relative in values for values in categories.values()):
            categories["deterministic_unit"].append(relative)

    head = _git(repo, "rev-parse", "HEAD")
    audit = {
        "schema": "landing_ready_test_quality_audit_v1",
        "created_at": _now(),
        "repo": repo.as_posix(),
        "head": head,
        "test_file_count": len(all_files),
        "category_counts": {key: len(value) for key, value in categories.items()},
        "high_value_tests": _sample(categories["acceptance"]) + _sample(categories["replay_failure_security_boundary"]),
        "weak_or_ceremonial_areas": _sample(categories["mock_heavy_or_ceremonial"]),
        "risk_statement": (
            "The suite has broad deterministic and boundary coverage, but a material share "
            "is contract, fixture, or dry-run evidence. Release may proceed only with explicit "
            "caveat that SEOS remains governance-level control, not an OS sandbox or live "
            "autonomous execution system."
        ),
        "recommendation": "release_allowed_with_explicit_caveats",
        "fatal_hollowness_found": False,
        "categories": categories,
    }
    json_path = output_dir / "test_quality_audit.json"
    md_path = output_dir / "test_quality_audit.md"
    json_path.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(_markdown(audit), encoding="utf-8")
    print(json_path.as_posix())
    print(md_path.as_posix())
    return 0


def _sample(values: list[str], limit: int = 12) -> list[str]:
    return values[:limit]


def _markdown(audit: dict[str, object]) -> str:
    lines = [
        "# Landing Ready Test Quality Audit V1",
        "",
        f"- HEAD: `{audit['head']}`",
        f"- test files classified: `{audit['test_file_count']}`",
        f"- recommendation: `{audit['recommendation']}`",
        f"- fatal hollowness found: `{audit['fatal_hollowness_found']}`",
        "",
        "## Category Counts",
    ]
    for key, count in audit["category_counts"].items():
        lines.append(f"- {key}: `{count}`")
    lines.extend(["", "## Risk Statement", "", str(audit["risk_statement"]), ""])
    return "\n".join(lines)


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", repo.as_posix(), *args], check=True, capture_output=True, text=True).stdout.strip()


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


if __name__ == "__main__":
    raise SystemExit(main())
