# AI Worker Router V1

Status: implemented as a non-executing independent router slice.

## Scope

AI Worker Router V1 adds deterministic route-plan generation for future AI
worker handoffs. It turns symbolic task metadata into a bounded route plan with
candidate workers, rejected workers, rejection reasons, handoff requirements,
and a deterministic content hash.

Implemented surfaces:

- `kernel/runtime/ai_worker_router.py`
- focused tracer-bullet tests
- acceptance coverage for handoff-only routing and forbidden prompt rejection

## Worker Declarations

The default declaration set includes:

- `local_python`
- `codex`
- `claude`
- `gemini`
- `gpt`
- `deepseek`

Declarations include provider family, supported task classes, capabilities,
timeout metadata, budget policy references, evidence requirements, hallucination
boundaries, and human-review requirements.

## Routing Behavior

The router accepts only symbolic route material:

- `route_id`
- `task_id`
- `task_class`
- `risk_level`
- `required_capabilities`
- optional `requested_worker_id`
- optional `blocked_worker_ids`

It selects deterministic candidates by task class and required capability set.
Rejected workers are retained with stable rejection reasons.

## Boundaries

This slice does not:

- dispatch a worker
- call providers
- read credentials
- access networks
- execute tools
- launch browsers
- mutate storage
- grant production autonomy
- accept raw prompts, raw responses, environment material, credentials, tokens,
  API keys, passwords, private keys, or authorization material

Every route plan explicitly records false values for provider execution,
worker dispatch, credential access, tool execution, network access, and
production autonomy.

## Failure Paths

Invalid route material fails closed through deterministic exceptions:

- missing route id, task id, or task class
- invalid risk level
- malformed capability or worker-id lists
- forbidden raw prompt/response/provider/secret/env/credential fields
- unsafe declarations
- duplicate worker declarations

When no worker can satisfy the symbolic task constraints, the route plan is
`blocked_no_candidate`.

## Dependency Blockers Recorded

The open draft PRs #497 through #505 remain unmerged. This router does not
depend on or duplicate those contract PRs. It is a non-executing route-plan
layer and does not implement worker registry admission from #503.

## Validation

Focused validation:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.tracer_bullet.test_ai_worker_router -v
```

Acceptance validation:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest validation.tests.acceptance.test_ai_worker_router_v1 -v
```
