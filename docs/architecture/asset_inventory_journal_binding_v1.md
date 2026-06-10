# Asset Inventory Journal Binding V1

## Purpose

Bind Minimal Asset Inventory scans into an append-only evidence journal so asset
awareness is auditable and replayable without mutating source files.

## Journal Shape

The command WAL journal has fixed admission, quarantine, and execution receipt
tables, so this binding uses a minimal SQLite WAL adapter table for
`ASSET_INVENTORY_SCAN` events. Each event records:

- `scan_id`
- `root_ids`
- `asset_count`
- `aggregate_inventory_hash`
- `per_asset_content_hashes`
- `created_at`
- `previous_hash`
- `content_hash`

## Boundary

All filesystem traversal, root rejection, symlink escape rejection, media
classification, and streaming file hashing remain owned by
`scan_asset_inventory()`. The binding only converts the resulting record digests
into one append-only journal event.

## Non-Goals

This does not scan home or filesystem root, follow symlink escapes, compute
embeddings, use LanceDB, run OpenUSD, call network, call providers, automate a
browser, launch DCC tools, launch ComfyUI, or mutate source files.
