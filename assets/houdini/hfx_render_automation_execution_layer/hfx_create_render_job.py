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

hfx.create_render_job(pathlib.Path(__file__).resolve().parent)
print('RENDER_JOB_CREATED')
