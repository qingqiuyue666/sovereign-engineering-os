#!/usr/bin/env python3
from pathlib import Path
import argparse
import json
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if REPO_ROOT.as_posix() not in sys.path:
    sys.path.insert(0, REPO_ROOT.as_posix())

from creative.assets.asset_registry_builder import build_registry

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default="tests/fixtures/creative/assets")
    parser.add_argument("--output", default="reports/creative/assets/asset_registry_v3.jsonl")
    args = parser.parse_args()
    rows = build_registry(Path(args.root), Path(args.output))
    print(json.dumps({"ok": True, "asset_count": len(rows), "output": args.output}, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
