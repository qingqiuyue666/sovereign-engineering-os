"""
Acceptance test harness for the first narrow signable path.

Foundation reference: v11_narrow_path_implementation_foundation.md Section 5.
Constitutional reference: v11 Section 24 (Acceptance Tests + Invariants).

This package contains executable acceptance tests mapped 1:1 to AT-IDs
from the constitution. Each test file targets exactly one AT-ID and
documents:
  - which INV-IDs it covers
  - which constitutional sections justify the check
  - what the test proves

All tests run against in-memory SQLite (no filesystem side effects)
and wire real kernel services (no mocks except the ModelAdapter).
"""
