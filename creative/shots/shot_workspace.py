"""Create fixture-safe shot workspaces."""

from __future__ import annotations

from pathlib import Path
from creative.common import SCHEMA_VERSION, stable_id, write_json, utc_now

SHOT_DIRS = ("references", "assets", "ai_generations", "dcc_work", "renders", "comps", "evidence")

def create_shot_workspace(root: Path, shot_id: str, *, title: str = "Creative shot") -> dict[str, object]:
    if not shot_id.startswith("SHOT_"):
        shot_id = stable_id("SHOT", shot_id)
    shot_root = Path(root) / shot_id
    for name in SHOT_DIRS:
        (shot_root / name).mkdir(parents=True, exist_ok=True)
    contract = {
        "schema_version": SCHEMA_VERSION,
        "id": shot_id,
        "created_at": utc_now(),
        "updated_at": utc_now(),
        "source": "shot_workspace",
        "scope": "local_fixture_or_user_workspace",
        "status": "READY",
        "title": title,
        "validation": {"required_dirs": list(SHOT_DIRS)},
        "evidence": [],
        "residual_risk": "Final creative approval remains human-owned.",
        "public": False,
        "private": True,
    }
    write_json(shot_root / "shot_contract.json", contract)
    (shot_root / "replay.md").write_text("# Replay\n\nNo renders have been executed.\n", encoding="utf-8")
    (shot_root / "final_report.md").write_text("# Final Report\n\nShot workspace initialized.\n", encoding="utf-8")
    return {"ok": True, "shot_id": shot_id, "shot_root": shot_root.as_posix(), "contract": contract}
