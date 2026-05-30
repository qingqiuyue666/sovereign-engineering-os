"""Shot report helpers."""

from __future__ import annotations

from pathlib import Path
import json

def build_shot_report(shot_root: Path) -> dict[str, object]:
    contract_path = Path(shot_root) / "shot_contract.json"
    contract = json.loads(contract_path.read_text(encoding="utf-8")) if contract_path.exists() else {}
    return {
        "ok": bool(contract),
        "shot_id": contract.get("id"),
        "dirs_present": sorted(path.name for path in Path(shot_root).iterdir()) if Path(shot_root).exists() else [],
        "render_execution_performed": False,
    }
