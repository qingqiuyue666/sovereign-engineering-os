# Personal AI Execution OS v2 Demo

This demo is local-only and uses generated temporary fixtures in the test suite.
It exercises the v2 runtime foundation without secrets, external network calls,
live model providers, real browser automation, creative software control, input
mutation, or output overwrite.

## Flow

1. Create a local fixture `.xlsx` workbook.
2. Inspect the workbook with `inspect-xlsx`.
3. Plan an approved metadata summary workbook with `plan-xlsx-output`.
4. Create a hash-bound approval artifact with `approve-xlsx-output`.
5. Generate the approved summary workbook with `create-approved-xlsx-output`.
6. Validate the generated workbook with `validate-xlsx-output`.
7. Run a deterministic mock typed-schema model fixture with `run-model-fixture`.
8. Run a deterministic local HTML fixture with `run-browser-fixture`.
9. Build and validate a runtime delivery package.

The acceptance test for this demo is:

```bash
python3 -m unittest tests.personal_ai.test_v2_runtime_demo_end_to_end -v
```
