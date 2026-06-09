# Skill System Runbook

## Commands

```bash
python3 seos.py skill list --json
python3 seos.py skill show cross_dcc_workflow --json
```

Skills are repository-local manifests under `skills/<skill_name>/skill.json`. The registry validates schema version, name, description, command list, and runbook path before returning entries.
