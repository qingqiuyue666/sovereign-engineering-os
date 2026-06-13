# High-Risk Human Gates

Agents must stop and request explicit human approval before actions in this
file.

## Merge and Mainline Authority

- Merge a final PR unless explicitly authorized.
- Push directly to `main`.
- Change branch protection or release policy.
- Retarget a PR when the target branch changes the review boundary.

## Destructive Repository Actions

- Delete branches still referenced by open or stacked PRs.
- Delete assets, reports, checkpoints, or generated artifacts.
- Remove preserved local files.
- Rewrite public history.
- Run irreversible destructive commands.

## Production and External Actions

- Deploy to production or external infrastructure.
- Contact real users, buyers, customers, auditors, partners, or communities.
- Send outreach, pricing, delivery, or acceptance communications.
- Start any real-world validation action.

## Secret, Token, Account, and Credential Handling

- Read, copy, move, print, transform, store, or rotate secrets.
- Create or modify credentials, tokens, keys, accounts, or secret stores.
- Place secrets in prompts, docs, reports, PRs, logs, comments, examples, or
  context bundles.

## Evidence and Claim Authority

- Claim paid signal, revenue, customer adoption, customer feedback, customer
  acceptance, delivery completion, real validation, production readiness, or
  commercial validation.
- Upgrade repository readiness into external validation.
- Convert templates into proof without source records.

## Architecture and Capability Boundaries

- Change architecture authority boundaries.
- Introduce new dependencies, services, vendors, network permissions, live
  providers, production controls, or automation authority.
- Expand runtime permissions beyond existing documented gates.
- Convert an internal workbench specification into a deployed app.

## Default

When in doubt, stop at the gate and provide a concise approval request with the
reason, risk, evidence available, and exact next action.
