# Browser Local Fixture Runtime v1

## Status

- runtime: deterministic local HTML fixture interpreter
- real browser automation: not introduced
- external network: forbidden
- credentials: not stored
- login/payment/account creation/destructive actions: forbidden
- form submission: rejected unless the fixture button policy explicitly allows it

## Allowed Actions

- `open_local_fixture`
- `inspect_title`
- `inspect_links`
- `fill_allowed_field`
- `click_allowed_button`

The fixture policy must mark fillable inputs with
`data-seos-allowed-field="true"` and clickable buttons with
`data-seos-allowed-button="true"`. Submit buttons additionally require
`data-seos-allow-submit="true"`.

## Artifacts

- `browser_action_log.json`
- `browser_evidence_manifest.json`

The runtime records before/after DOM metadata, action results, fixture hashes,
and hashed filled-field values. Raw filled values are not stored.
