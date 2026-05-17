# OSINT Ingestion Foundation v1

## Purpose
Bounded local-only OSINT ingestion foundation. Validates ingestion
requests without performing real data ingestion.

## Boundaries
- no live network ingestion in v1
- no weak source without downgrade
- no missing source tier
- no missing timestamp
- no missing evidence hash
- no conflict without WAIT/NO_TRADE downgrade
- no real ingestion in v1

## Source Tiers
TIER_1_PRIMARY, TIER_2_SECONDARY, TIER_3_TERTIARY

## Operations
1. validate_osint_ingestion_request — structural validation
2. validate_source_tier_contract — tier-based rules
3. validate_freshness_contract — timestamp freshness
4. produce_osint_ingestion_receipt — full receipt production

## Scope
Contract-only. Does not perform any real data ingestion.
