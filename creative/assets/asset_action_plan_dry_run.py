"""Produce dry-run-only asset action plans."""

from __future__ import annotations

def build_action_plan(records: list[dict[str, object]], missing_parts: list[dict[str, object]], duplicates: list[dict[str, object]]) -> dict[str, object]:
    return {
        "dry_run": True,
        "destructive_actions_performed": False,
        "asset_count": len(records),
        "missing_archive_part_groups": len(missing_parts),
        "duplicate_candidate_groups": len(duplicates),
        "recommended_actions": [
            "Review archive gaps before extraction.",
            "Review duplicate candidates manually before deletion.",
            "Keep license status unknown/private until verified.",
        ],
    }
