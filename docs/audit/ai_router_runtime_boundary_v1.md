# AI Router Runtime Boundary V1

## Scope

Priority #522 adds a file-backed runtime boundary around the deterministic AI
worker router. The boundary treats AI as a proposal source only: it can emit
plans, proposals, patch candidates, or review packets, then binds them to local
review evidence. It does not call providers, execute tools, apply patches,
merge, push, mutate `main`, start daemons, or read credential-bearing state.

## Runtime Boundary

`FileBackedAIRouterRuntimeBoundary` coordinates these existing contract
surfaces:

- deterministic AI worker route plans
- model routing receipts with provider/tool/network authority flags set false
- real WAL records of type `AI_ROUTER_EVENT`
- artifact-store `audit_json` evidence with digest-only bindings
- durable review queue submission and queueing
- persisted runtime receipts for replayable local audit

Accepted requests must be human-invoked, digest-only, and limited to supported
proposal actions. The queued review job requires human review and approval
before any later controlled execution boundary can act on the proposal.

## Fail-Closed Properties

The runtime rejects before writing WAL, artifacts, receipts, or queue records
when:

- payloads contain raw prompt/response, command, tool, provider, network, path,
  environment, credential, token, or secret-like fields
- the requested action is unsupported
- the requested action would mutate runtime state, merge, push, apply patches,
  or target `main`
- declared effects claim provider calls, direct execution, queue execution, or
  other hallucinated actions outside the proposal-only action
- the output kind does not match the requested proposal action
- the review queue is missing or not a durable queue instance

## Evidence

Tracer and acceptance coverage exercise:

- successful proposal routing to a model worker without provider execution
- model receipt, WAL, artifact, review queue, and persisted receipt evidence
- fail-closed unsafe tool request, unsupported action, runtime mutation action,
  hallucinated provider effect, and sensitive field handling
- source guard coverage for provider, browser, network, process launch,
  environment, loop, merge, and push surfaces

The artifact payload stores only digests, hashes of selected labels, and boolean
review/approval requirements. It does not persist raw AI input, output, prompts,
provider responses, commands, paths, environment values, or credentials.
