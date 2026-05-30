# Red-Team Checklist V1

External review required: yes.

Use this checklist to challenge the packet before any recognition claim is
considered.

## Claim Boundary

- Try to find wording that claims final public recognition.
- Try to find wording that implies external verification already happened.
- Confirm non-goals are not contradicted by examples or scripts.

## Evidence Integrity

- Verify all evidence refs in the packet and claim matrix exist.
- Verify PR URLs #540 through #548 resolve to the stated work.
- Verify merge commits for Waves 1 through 8 match the packet.
- Verify `v0.1.0-rc3` resolves to the stated target.

## Security And Secret Safety

- Run secret/context safety checks.
- Review security-control docs against CI behavior.
- Confirm no `.env` values, API keys, keychain values, or token stores are
  required for validation.

## Supply Chain

- Review dependency policy and GitHub Actions permissions.
- Confirm CI uses minimal repository permissions.
- Confirm package/install smoke paths do not require private services.

## Runtime And AI Governance

- Confirm live provider execution is not admitted.
- Confirm AI provider policies require proposal-first handling and secret-ref
  boundaries.
- Confirm no RPA or computer-control capability is introduced.

## Reliability And Operations

- Run the reliability benchmark.
- Review incident, rollback, maintenance, cleanup, and interrupted-run policies.
- Confirm the benchmark does not rewrite tracked files.

## Risks And Blockers

- Review accepted risk register.
- Review residual risk register.
- Confirm blockers for final recognition remain visible and not hidden.
