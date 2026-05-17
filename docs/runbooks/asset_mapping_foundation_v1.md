# Asset Mapping Foundation v1

## Purpose
Bounded local-only asset mapping foundation. Validates asset mapping
requests without making trading decisions.

## Boundaries
- no missing evidence
- no missing venue
- no missing product id
- no unsupported asset class
- no confidence overclaim (max 0.95)
- no action without friction data
- no real trading decision in v1

## Operations
1. validate_asset_mapping_request — structural validation
2. validate_asset_candidate_contract — candidate completeness
3. validate_mapping_confidence_contract — confidence bounds
4. produce_asset_mapping_receipt — full receipt production

## Scope
Contract-only. Does not make any trading decisions.
