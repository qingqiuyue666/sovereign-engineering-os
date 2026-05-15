# Model Provider Explicit Transport Suite v1

## Verdict

`MODEL_PROVIDER_EXPLICIT_TRANSPORT_SUITE_READY_FOR_LOCAL_TESTS`

This branch introduces a controlled explicit transport suite for the model provider live-smoke path.

It does not make normal tests call a real model API. It does not persist or log API key values. It does not allow tool calls or file edits from model output.

## Implemented

- Model provider transport request/response contract.
- Transport validation report writer.
- Disabled-by-default OpenAI explicit transport adapter.
- Stdlib OpenAI Responses API helper available only by explicit injection.
- Tests for disabled-by-default transport behavior.
- Tests proving no normal-test API key requirement.
- Tests proving runner integration can use an injected explicit transport adapter.

## Not Implemented

- Default live provider API execution.
- Normal tests calling OpenAI.
- SDK dependency.
- Credential persistence.
- Credential logging.
- Tool execution from model output.
- File edits from model output.
- Raw provider response persistence.

## Required Gates Before OpenAI Explicit Transport Can Call HTTP

All must be true:

1. Transport request validates.
2. `allow_network=True` is passed by the caller.
3. `SEOS_ENABLE_OPENAI_EXPLICIT_TRANSPORT=true` exists in the supplied environment.
4. `OPENAI_API_KEY` exists in the supplied environment.
5. Explicit `http_transport` callable is supplied.

If any gate is missing, the adapter writes a denial result and performs no HTTP transport call.

## Normal Test Boundary

Normal tests use injected fake transports only.

The stdlib helper `stdlib_openai_responses_transport` exists for a future manually authorized live smoke, but it is never called unless the caller passes it explicitly.

## Local Verification Commands

```bash
python3 -m unittest tests.personal_ai.test_model_provider_explicit_transport_suite -v
python3 -m unittest tests.personal_ai.test_model_provider_disabled_live_smoke_runner -v
python3 -m unittest discover -s tests/personal_ai -v
make ci
git diff --check
git status --short
```

## Merge Gate

This branch is merge-ready only if:

- all targeted tests pass
- full Personal AI tests pass
- `make ci` passes
- the branch does not add hardcoded secrets
- the branch does not persist or log API key values
- the branch does not introduce default network execution
- the branch does not allow tool calls or file edits from model output

## Next Branch

A future branch may add a manually invoked live-smoke CLI command, but it must remain disabled by default and require explicit environment flags, approval/admission artifacts, timeout, budget, schema validation, and failure quarantine.
