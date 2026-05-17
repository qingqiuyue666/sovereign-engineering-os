# Alert Delivery Foundation v1

## Purpose
Bounded local-only alert delivery foundation. Validates alert delivery
requests without sending any real messages.

## Boundaries
- no real Telegram/send/network delivery in v1
- no secret token
- no missing operator acknowledgement
- no missing evidence reference
- no production autonomy
- no real message sending in v1

## Operations
1. validate_alert_delivery_request — structural validation
2. validate_alert_channel_policy — channel policy check
3. validate_alert_payload_contract — payload completeness
4. produce_alert_delivery_receipt — full receipt production

## Scope
Contract-only. Does not send any messages.
