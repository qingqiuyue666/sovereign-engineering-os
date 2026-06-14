# Skipped Risk Register

## Target

`END_TO_END_EXECUTION_SYSTEM_V1_INTERNAL_READY`

## Register

| Skipped item | Risk type | Reason | Downgrade attempted | Continuing safe? | Next human action |
| --- | --- | --- | --- | --- | --- |
| Delete, move, overwrite, or stage `reports/creative/production_spine_v1/` | Preserved local user work | The directory existed before this task and is not required for this target | Leave untouched and use explicit staging paths | Yes | Human may separately decide whether to keep, archive, or stage it |
| Push directly to `main` | Mainline authority | The task requires branch and draft PR, not direct main mutation | Dedicated feature branch | Yes | Human reviewer may merge after review |
| Merge PR | Mainline authority | Merge is explicitly outside the execution boundary | Draft PR only | Yes | Human reviewer must approve and merge if desired |
| Production deployment | External operational authority | No deployment target, approval, or source evidence exists | Delivery protocol and final report only | Yes | Human must authorize and run deployment separately |
| Real-world outreach or validation | External business authority | No human-approved outreach action or source record exists | Validation boundary and non-claim statement | Yes | Human must perform or authorize real-world action |
| Live paid API calls | Cost and external side effect | Not required for documentation/protocol target | Local static validation and fixtures | Yes | Human must authorize any paid/live API use |
| Secret, token, account, or permission handling | Credential authority | Not required and explicitly prohibited | Do not access or print secrets | Yes | Human must handle credentials outside this run |
