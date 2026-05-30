#!/usr/bin/env python3
import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if REPO_ROOT.as_posix() not in sys.path:
    sys.path.insert(0, REPO_ROOT.as_posix())

from creative.reports.dashboard import build_dashboard

if __name__ == "__main__":
    print(json.dumps(build_dashboard(Path("reports/creative/dashboard")), sort_keys=True))
