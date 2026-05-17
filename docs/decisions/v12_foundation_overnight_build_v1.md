# V12 Foundation Overnight Build Decision v1

Decision: continue with the branch-local V12 foundation draft as a contract-only
and dry-run-only implementation line.

The branch intentionally does not merge main, create tags, modify checkpoint
tags, add live provider calls, send live Telegram notifications, read real
secret values, access real vault/keyring/KMS systems, start a daemon, ingest
OSINT live data, run a dashboard server, or perform database migrations.
In short: no live provider runtime is authorized by this decision.

Next allowed branches are hardening branches only: focused test expansion,
documentation alignment, deterministic failure coverage, and source-boundary
audits. Live runtime activation remains outside this decision.
