#!/usr/bin/env python3
"""Validate the SEOS future-resilience program artifacts."""

from __future__ import annotations

from pathlib import Path
import json

REQUIRED_FILES = [
    "docs/roadmaps/seos_future_resilience_master_plan_v1.md",
    "docs/architecture/seos_knowledge_layer_v1.md",
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
    "scripts/knowledge_control_vault_check_v1.py",
    "tests/tracer_bullet/test_knowledge_control_vault_v1.py",
]

REQUIRED_TEXT = {
    "docs/roadmaps/seos_future_resilience_master_plan_v1.md": [
        "SEOS_FUTURE_RESILIENCE_PROGRAM_ACTIVE",
        "SEOS Core",
        "approval",
        "permit",
        "evidence",
        "replay",
    ],
    "docs/architecture/seos_knowledge_layer_v1.md": [
        "proposal",
        "mirror",
        "receipt",
        "never become an execution permit",
    ],
    "docs/reports/knowledge_layer_delivery_v1.md": [
        "SEOS_KNOWLEDGE_LAYER_P0_OBSIDIAN_READY_FOR_REVIEW",
        "Obsidian-compatible",
        "Logseq",
        "Anytype",
        "Notion",
    ],
    "pyproject.toml": ["seos-knowledge = \"kernel.knowledge.cli:main\""],
    "seos.py": ["sys.argv[1] == \"knowledge\"", "kernel.knowledge.cli"],
}

FORBIDDEN_TEXT = {
    "docs/roadmaps/seos_future_resilience_master_plan_v1.md": [
        "note becomes approval",
        "cloud tool is authority",
        "execute without approval",
    ],
}


def main() -> int:
    root = Path.cwd()
    failures: list[dict[str, object]] = []
    for rel in REQUIRED_FILES:
        if not (root / rel).exists():
            failures.append({"path": rel, "failure": "missing_required_file"})
    for rel, markers in REQUIRED_TEXT.items():
        path = root / rel
        if not path.exists():
            failures.append({"path": rel, "failure": "missing_text_check_file"})
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for marker in markers:
            if marker not in text:
                failures.append({"path": rel, "failure": "missing_required_marker", "marker": marker})
    for rel, markers in FORBIDDEN_TEXT.items():
        path = root / rel
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for marker in markers:
            if marker in text:
                failures.append({"path": rel, "failure": "forbidden_marker_present", "marker": marker})
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
