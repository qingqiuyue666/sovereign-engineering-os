# Error Convergence And Retry Runbook

## Command

```bash
python3 seos.py rpc invoke examples/rpc/retry_convergence_service_probe.json --json
```

## Expected Local Behavior

The command runs the real `comfyui_local.service_probe` adapter through the convergence wrapper. If ComfyUI is unavailable, the adapter failure remains truthful, and the runtime writes:

```text
work/rpc/retry_convergence_service_probe/retry_records.json
work/rpc/retry_convergence_service_probe/failure_convergence.json
work/rpc/retry_convergence_service_probe/failure_bundle.json
work/rpc/retry_convergence_service_probe/execution_receipt.json
```

`retry_records.json` records each attempt and whether it retried, succeeded, recommended patch repair, or became terminal. `failure_convergence.json` contains the normalized failure code, taxonomy category, retry budget, terminal classifier, and repair hint.

## CI-Safe Path

`tests/tracer_bullet/test_error_convergence_retry_v1.py` injects dispatch functions that fail once and then succeed, exhaust retry budget, and produce code-level repairable failures without requiring external DCC applications.
