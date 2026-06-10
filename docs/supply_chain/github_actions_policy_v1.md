# GitHub Actions Policy V1

GitHub Actions workflows must be minimal and reviewable.

Requirements:

- use minimal CI permissions; default repository content access is read-only
- avoid `pull_request_target` unless a later security review explicitly allows it
- avoid secret access in pull request checks
- keep workflow commands visible in YAML
- run observation, identity, installability, contract, claim, failure-path, and
  canonical health gates
- document any action version changes in the PR
- follow the action pinning policy: prefer commit SHA pinning for sensitive or
  third-party actions; first-party version tags may be used only with review and
  periodic upgrade checks

This policy does not authorize publishing releases or changing tags.
