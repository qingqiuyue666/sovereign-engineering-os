# Local-Only Playwright Regression Pack v1

This decision adds local-only regression scenario definitions and validation on
top of the existing local Playwright fixture receipt chain.

The regression pack remains file fixture only. It delegates through the
operator-provided local execution receipt path and validates the resulting
receipt, adapter draft, embedded smoke, runner output, screenshot, and artifact
index evidence.

This decision does not enable live websites. It does not enable arbitrary URLs.
It does not enable account/login/registration flows. It does not enable scraping.
It does not enable bypass/captcha workflows. It does not access secrets/cookies.

This decision does not run npm/npx/install/browser download workflows.
This decision does not execute candidate repository code. It does not import
candidate repository code, register a production adapter, grant production
promotion, or create autonomy.

Regression boundaries:

- regression success is not production admission
- regression success is not live website admission
- regression success is not general browser automation admission
- future live website work remains blocked by separate policy, legal, network,
  credential, and human-approval gates
