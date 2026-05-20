#!/usr/bin/env python3
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve()
for parent in ROOT.parents:
    candidate = parent / "hfx_real_pipeline_lib"
    if candidate.exists():
        sys.path.insert(0, str(parent))
        break
from hfx_real_pipeline_lib import hfx_real_pipeline as hfx

d=pathlib.Path(__file__).resolve().parent
print(hfx.validate_color_management(hfx.read_json(d/'COLOR_MANAGEMENT_CONFIG.json'))['status'])
