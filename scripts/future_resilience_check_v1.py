#!/usr/bin/env python3
"""Validate SEOS future-resilience artifacts are present.

This gate is deliberately stable: it fails when core future-resilience artifacts
are missing, while detailed wording and behavior are covered by the dedicated
knowledge and agent-intake tracer-bullet tests.
"""

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


def main() -> int:
    root = Path.cwd()
    failures: list[dict[str, object]] = []
    present: list[str] = []
    for rel in REQUIRED_FILES:
        if (root / rel).exists():
            present.append(rel)
        else:
            failures.append({"path": rel, "failure": "missing_required_file"})
    payload = {
        "ok": not failures,
        "schema": "seos_future_resilience_check_v1",
        "required_file_count": len(REQUIRED_FILES),
        "present_file_count": len(present),
        "failure_count": len(failures),
        "failures": failures,
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
