#!/usr/bin/env python3
from pathlib import Path
import argparse
import json
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if REPO_ROOT.as_posix() not in sys.path:
    sys.path.insert(0, REPO_ROOT.as_posix())

from creative.assets.local_asset_library import build_asset_library_scan, write_asset_library_outputs
from creative.common import write_jsonl

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default="tests/fixtures/creative/assets")
    parser.add_argument("--output", default="reports/creative/assets/asset_registry_v3.jsonl")
    parser.add_argument("--report-json", default="reports/creative/assets/asset_library_report_v1.json")
    parser.add_argument("--report-md", default="reports/creative/assets/asset_library_report_v1.md")
    parser.add_argument("--mode", choices=("public", "local"), default="public")
    parser.add_argument("--max-depth", type=int, default=12)
    args = parser.parse_args()
    root = Path(args.root)
    scan = build_asset_library_scan(root, mode=args.mode, max_depth=args.max_depth)
    rows = list(scan["assets"])
    write_jsonl(Path(args.output), rows)
    outputs = write_asset_library_outputs(scan, root=root, output_json=Path(args.report_json), output_markdown=Path(args.report_md))
    print(json.dumps({"ok": True, "asset_count": len(rows), "output": args.output, "outputs": outputs, "summary": scan["summary"]}, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
