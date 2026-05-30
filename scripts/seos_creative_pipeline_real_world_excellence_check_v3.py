#!/usr/bin/env python3
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if REPO_ROOT.as_posix() not in sys.path:
    sys.path.insert(0, REPO_ROOT.as_posix())

from creative.validation import main_for

if __name__ == "__main__":
    raise SystemExit(main_for("seos_creative_pipeline_real_world_excellence_check_v3"))
