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
reg=hfx.read_json(hfx.layer_dir(hfx.repo_root_from(__file__), 'resource_ingest') / 'RESOURCE_REGISTRY.json')
hfx.bind_resources_to_shot(reg, d)
print('SHOT_RESOURCE_BINDING_COMPLETE')
