# Local Operator Dashboard Runbook

## Command

```bash
python3 seos.py dashboard build --json
```

The command writes:

```text
work/operator_dashboard/index.html
work/operator_dashboard/dashboard_state.json
```

The dashboard is static and local. It reads production runtime state, package manifests, and repair ledger events; it does not start a server or call external services.
