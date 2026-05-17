# V12 Foundation Overnight Build Runbook v1

This runbook records the V12 foundation draft built on
`v12-leak-prevention-foundation-v1`.

Implemented surfaces are local and deterministic: security gates, truth
substrate contracts, task intake, CLI foundation, dry-run runtime, replay,
audit export, status reporting, provider mock, Telegram mock, vault/keyring
metadata contracts, daemon/scheduler metadata contracts, domain pipeline
skeleton, and dashboard data model.

Forbidden runtime surfaces remain absent: no live provider runtime, no live
Telegram send, no real vault/KMS/keyring runtime, no daemon runtime, no real WAL
reader, no real SQLite migration, no OSINT live ingestion, and no dashboard
runtime.

The intended health path is `make test-v12-foundation`, tracer-bullet discovery,
`make ci`, and `git diff --check`.
