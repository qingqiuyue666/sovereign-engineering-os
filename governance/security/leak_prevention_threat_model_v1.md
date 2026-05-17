# V12 Leak Prevention Threat Model v1

V12 starts with default-deny leak prevention. The implemented threat model is
local, deterministic, and read-only: classify material, detect secret-like
content, sanitize environment-shaped mappings, preserve JSON shape for AI
context redaction, block contaminated outbound payloads, and reject repository
hygiene hazards.

Forbidden surfaces remain absent: live provider calls, live Telegram sends,
real vault/keyring/KMS access, daemon execution, destructive filesystem cleanup,
raw prompt persistence, and raw provider response persistence.

Known fake markers are valid only under `tests/` and
`governance/security/fixtures/`. Outside those paths, fake markers are treated
as contamination so examples cannot leak into operator or runtime surfaces.
