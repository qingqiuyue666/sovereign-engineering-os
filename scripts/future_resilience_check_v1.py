#!/usr/bin/env python3
"""Validate SEOS future-resilience artifacts are present."""

from __future__ import annotations

from pathlib import Path
import json

REQUIRED_FILES = [
    "docs/roadmaps/seos_future_resilience_master_plan_v1.md",
    "docs/architecture/seos_knowledge_layer_v1.md",
    "docs/architecture/seos_agent_intake_boundary_v1.md",
    "docs/runbooks/knowledge_control_vault_v1.md",
    "docs/reports/knowledge_layer_delivery_v1.md",
    "kernel/knowledge/object_model.py",
    "kernel/knowledge/graph.py",
    "kernel/knowledge/vault.py",
    "kernel/knowledge/vault_scanner.py",
    "kernel/knowledge/proposal_ingest.py",
    "kernel/knowledge/adapters/logseq.py",
    "kernel/knowledge/adapters/anytype.py",
    "kernel/knowledge/adapters/notion.py",
    "kernel/agent_intake/boundary.py",
    "kernel/agent_intake/proposals.py",
    "kernel/agent_intake/mcp_manifest.py",
    "kernel/agent_intake/cli.py",
    "scripts/knowledge_control_vault_check_v1.py",
    "tests/tracer_bullet/test_knowledge_control_vault_v1.py",
    "tests/tracer_bullet/test_agent_intake_boundary_v1.py",
]

REQUIRED_MARKERS = {
    "docs/roadmaps/seos_future_resilience_master_plan_v1.md": [
        "SEOS_FUTURE_RESILIENCE_PROGRAM_ACTIVE",
        "approval",
        "permit",
        "evidence",
        "replay",
    ],
    "docs/architecture/seos_agent_intake_boundary_v1.md": [
        "SEOS_AGENT_INTAKE_BOUNDARY_READY_FOR_REVIEW",
        "ACCEPTED_AS_PROPOSAL",
        "REJECTED_BY_AGENT_BOUNDARY",
    ],
    "docs/reports/knowledge_layer_delivery_v1.md": [
        "SEOS_KNOWLEDGE_AND_AGENT_INTAKE_READY_FOR_REVIEW",
        "Obsidian-compatible",
        "Logseq",
        "Anytype",
        "Notion",
    ],
    "pyproject.toml": [
        "seos-agent = \"kernel.agent_intake.cli:main\"",
        "seos-knowledge = \"kernel.knowledge.cli:main\"",
    ],
    "seos.py": ["sys.argv[1] == \"agent\"", "sys.argv[1] == \"knowledge\""],
}


def main() -> int:
    root = Path.cwd()
    failures: list[dict[str, object]] = []
    for rel in REQUIRED_FILES:
        if not (root / rel).exists():
            failures.append({"path": rel, "failure": "missing_required_file"})
    for rel, markers in REQUIRED_MARKERS.items():
        path = root / rel
        if not path.exists():
            failures.append({"path": rel, "failure": "missing_marker_check_file"})
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for marker in markers:
            if marker not in text:
                failures.append({"path": rel, "failure": "missing_required_marker", "marker": marker})
    payload = {
        "ok": not failures,
        "schema": "seos_future_resilience_check_v1",
        "required_file_count": len(REQUIRED_FILES),
        "failure_count": len(failures),
        "failures": failures,
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
