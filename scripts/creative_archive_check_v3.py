#!/usr/bin/env python3
from pathlib import Path
import json
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if REPO_ROOT.as_posix() not in sys.path:
    sys.path.insert(0, REPO_ROOT.as_posix())

from creative.assets.asset_registry_builder import build_registry
from creative.assets.archive_group_detector import detect_archive_groups
from creative.assets.missing_part_detector import detect_missing_parts

def main() -> int:
    rows = build_registry(Path("tests/fixtures/creative/archives"))
    groups = detect_archive_groups(rows)
    missing = detect_missing_parts(groups)
    print(json.dumps({"ok": not missing, "archive_group_count": len(groups), "missing": missing}, sort_keys=True))
    return 0 if not missing else 1

if __name__ == "__main__":
    raise SystemExit(main())
