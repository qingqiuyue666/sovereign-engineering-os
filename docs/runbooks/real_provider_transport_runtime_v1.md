# Real Provider Transport Runtime v1

## Purpose
Local-only, deterministic, dry-run provider transport boundary. Validates and
produces receipts for provider transport requests without making real provider
calls. All execution is local and deterministic.

## Boundaries
- no network execution
- no live provider calls
- no subprocess spawning
- no socket connections
- no HTTP/HTTPS requests (no requests, httpx, urllib, urllib3)
- no cloud AI API calls
- no trading or production actions
- no secrets read
- no .env files read
- no raw payload persistence
- no wall-clock in receipt hashes
- no non-deterministic values in receipts
- no live mode
- no network mode
- dry-run only

## Architecture

### ProviderAdapterRegistry
Registers provider adapter descriptors. Only known providers (mock-finance,
mock-market-data, mock-news, mock-weather) are accepted. Forbidden providers
(live-broker, live-exchange, live-payment, live-bank) are permanently rejected.

### ProviderRequestContract
Validates incoming provider transport requests. Enforces: provider_id,
request_id, capability_token, evidence_binding, dry_run=true, live_mode=false,
network_mode=false. Rejects raw payloads, secrets, .env markers.

### ProviderTransportPreflight
Runs gate checks before provider execution: provider known, capability allowed,
dry-run only, no network, no secrets, evidence binding present, budget/rate
limits within bounds. All gates must pass.

### ProviderDryRunReceipt
Deterministic receipt for successful dry-run transports. Contains hashes and
metadata only. No raw payload. No wall-clock (created_at is epoch sentinel).
Same inputs always produce the same receipt.

### ProviderFailureReceipt
Deterministic failure receipt for rejected transports. Captures failure reason
and the gate at which execution was rejected. Same failure scenario always
produces the same receipt.

### CapabilityBoundary
Enforces provider-specific capability allowlists. Each provider has a fixed set
of allowed capabilities. Forbidden capabilities (live_trade, live_transfer,
etc.) are always rejected.

### EvidenceBindingPlaceholder
Validates evidence binding presence. In v1, verifies the binding is present and
well-formed. Future branches will validate against the Evidence Vault.

### RateLimitBudgetContract
Hard enforcement of budget and rate limits. Budget is a float, rate limit is
an integer. Exceeding either limit rejects the transport.

### NoNetworkEnforcement
Verifies no forbidden network modules are loaded at runtime. Forbidden modules:
socket, requests, httpx, urllib*, http.client, subprocess, and more.

### ProviderTransportRuntime
Main orchestrator. Ties all validation layers together in a fixed 7-step
pipeline and produces either a dry-run receipt or failure receipt.

## Execution Pipeline
1. No-network enforcement
2. Request validation (contract)
3. Preflight gate checks
4. Capability boundary validation
5. Evidence binding validation
6. Budget/rate-limit validation
7. Receipt production (dry-run or failure)

## Scope
Local validation only. Does not execute provider logic. Does not make network
calls. Does not read secrets. Produces deterministic receipts for audit and
spine integration only.

## Spine Integration
ProviderDryRunReceipt is designed to link into Runtime Receipt Spine in a
future branch. The canonical_hash field is compatible with the spine's
hash chain format. No modification to existing Runtime Spine is required
in this branch.
