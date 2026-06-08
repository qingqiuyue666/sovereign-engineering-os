# ComfyUI Workflow Smoke Runner V1

## Purpose

Use this runner to prove that SEOS can submit an approved API-format workflow to
a running local ComfyUI service and collect bounded output evidence. It is a
local workstation smoke, not a cloud runner and not a ComfyUI installer.

## External Behavior References

- Official ComfyUI server overview: https://docs.comfy.org/development/comfyui-server/comms_overview
- Official ComfyUI routes: https://docs.comfy.org/development/comfyui-server/comms_routes
- Official workflow API format: https://docs.comfy.org/development/api-development/workflow-api-format
- Official `EmptyImage` built-in node: https://docs.comfy.org/built-in-nodes/EmptyImage

These references justify the runner's assumptions that local ComfyUI normally
serves HTTP on `http://127.0.0.1:8188`, accepts workflow submission at
`POST /prompt`, exposes history at `GET /history/{prompt_id}`, exposes output
files through `GET /view`, and expects workflows exported in API format.

## Operator Command

Start ComfyUI separately, then run:

```bash
python3 seos.py creative comfyui-smoke \
  --workflow-json tests/fixtures/creative/comfyui/api_workflow_fixture_v1.json \
  --endpoint http://127.0.0.1:8188 \
  --output-root work/creative_runs/comfyui_smoke \
  --approve-local-execution \
  --approval-id approval-comfyui-smoke-local-001 \
  --timeout-seconds 120 \
  --result-json reports/creative/comfyui/comfyui_smoke_result.local.json \
  --materialization-json reports/creative/comfyui/comfyui_smoke_materialization.local.json
```

The bundled fixture uses `EmptyImage` and `SaveImage` so it can smoke-test a
working local service without model downloads. For production use, pass a
workflow exported from ComfyUI with `File -> Export Workflow (API)`.

## Safety Contract

- Only loopback HTTP endpoints are accepted.
- SEOS does not start ComfyUI, install nodes, download models, or contact cloud
  services.
- `GET /system_stats` may be used for service preflight.
- `POST /prompt` requires `--approve-local-execution` and a safe
  `--approval-id`.
- Raw workflow JSON, raw prompt payloads, and raw history payloads are not
  persisted by SEOS reports; summaries and hashes are persisted instead.
- Output downloads from `/view` are bounded by count and byte limits.
- Custom nodes may still have local side effects. Operator approval is required
  because SEOS cannot prove every installed ComfyUI node is harmless.

## Truthful Statuses

- `ENV_NOT_FOUND`: the workflow JSON is missing.
- `SERVICE_UNAVAILABLE`: the loopback service does not answer `/system_stats`.
- `USER_APPROVAL_REQUIRED`: service and workflow are ready, but posting to
  `/prompt` has not been approved.
- `EXECUTED`: the workflow was accepted, reached history with success, and
  evidence summaries were written.
- `LONG_TASK_BLOCKED`: the prompt was accepted but did not reach history before
  timeout.
- `EXECUTION_FAILED`: ComfyUI rejected the prompt or history reported a failed
  execution.

## Validation

```bash
make creative-comfyui-runner-check
python3 -m unittest discover -s tests/creative -p 'test_comfyui_local_runner_v1.py' -v
python3 scripts/creative_comfyui_workflow_smoke_v1.py \
  --workflow-json tests/fixtures/creative/comfyui/api_workflow_fixture_v1.json \
  --output-root work/creative_runs/comfyui_service_unavailable \
  --observed-at 2026-06-08T00:00:00Z \
  --fixture-service-unavailable \
  --result-json reports/creative/comfyui/comfyui_smoke_service_unavailable_v1.json \
  --materialization-json reports/creative/comfyui/comfyui_smoke_materialization_v1.json
```

Default CI does not require ComfyUI to be installed or running.
