"""Repository-local skill registry."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from creative.common import load_json


def load_skill_registry(root: str | Path = "skills") -> dict[str, Any]:
    skills_root = Path(root)
    skills = []
    if skills_root.exists():
        for manifest_path in sorted(skills_root.glob("*/skill.json")):
            manifest = load_json(manifest_path)
            _validate_skill_manifest(manifest, manifest_path)
            skills.append({**manifest, "manifest_path": manifest_path.as_posix()})
    return {"schema_version": "seos.skill_registry.v1", "skill_count": len(skills), "skills": skills}


def get_skill(skill_name: str, root: str | Path = "skills") -> dict[str, Any]:
    registry = load_skill_registry(root)
    for skill in registry["skills"]:
        if skill["name"] == skill_name:
            return skill
    raise KeyError(f"skill_not_found:{skill_name}")


def _validate_skill_manifest(manifest: dict[str, Any], path: Path) -> None:
    required = {"schema_version", "name", "description", "commands", "runbook"}
    missing = sorted(required.difference(manifest))
    if missing:
        raise ValueError(f"skill_manifest_missing:{path}:{','.join(missing)}")
    if manifest["schema_version"] != "seos.skill.v1":
        raise ValueError(f"skill_manifest_schema_unsupported:{path}")
    if not isinstance(manifest.get("commands"), list) or not manifest["commands"]:
        raise ValueError(f"skill_manifest_commands_required:{path}")
