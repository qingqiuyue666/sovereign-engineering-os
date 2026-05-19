# Operator Daily Loop Usage

This usage path is read-only and non-Houdini. It does not execute providers, brokers, servers, creative tools, or VFX applications.

## Steps
- Read `docs/operator/generated/operator_daily_loop_report.md`.
- Check stop conditions before continuing.
- Use `docs/operator/generated/code_audit_real_run_001/next_action_queue.md` for the current queue.
- Record exact command results in the final operator report.

## Stop Conditions
- Blocked capability regression.
- Protected file mutation.
- Failed verification command.
- Any request to execute Houdini/VFX work in this slice.
