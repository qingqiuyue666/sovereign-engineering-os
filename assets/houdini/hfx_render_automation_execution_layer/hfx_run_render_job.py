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
hfx.validate_render_outputs(hfx.read_json(d / 'RENDER_JOB_MANIFEST.json'), d)
print('RENDER_JOB_VALIDATED_FAIL_CLOSED')
