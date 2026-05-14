# Model Typed-Schema Runtime v1

## Status

- runtime: deterministic local mock provider only
- adapter: `mock_model_typed_schema_runtime`
- live provider runtime: not introduced
- API keys: not accepted
- network/API calls: not introduced
- file edits: not admitted
- tool calls: not admitted
- authority grants from model output: rejected

## Supported Fixture Schemas

- `job_route_classification_v1`
- `artifact_profile_summary_v1`
- `next_step_recommendation_v1`

The runtime reads a local JSON request artifact, verifies the input artifact hash,
generates or parses a deterministic fixture response, validates the typed schema,
and writes one of:

- `model_inference_artifact.json`
- `model_failure_bundle.json`

Failure bundles are produced for malformed fixture JSON, schema validation
failures, attempted authority grants, live-provider requests, API key requests,
network-enabled requests, file-edit requests, and tool-call requests.
