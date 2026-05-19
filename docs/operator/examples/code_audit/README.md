# Code Audit Sample Pack v1

This directory contains a private sample-only pack for the existing Code Audit operational workflow.

## Scope

- Sample-only.
- Caller-provided material only.
- Private-safe and public-safe synthetic content only.
- No secrets, no credentials, no tokens, and no raw prompts.
- No live repository verification is performed by these files.
- Nothing here proves live execution readiness, merge readiness, or post-merge truth.

## Contents

- `branch_audit_sample_material.json` and `branch_audit_sample_report.md`
- `merge_readiness_sample_material.json` and `merge_readiness_sample_report.md`
- `ai_worker_result_review_sample_material.json` and `ai_worker_result_review_sample_report.md`
- `post_merge_retrospective_sample_material.json` and `post_merge_retrospective_sample_report.md`
- `code_audit_daily_sample_material.json` and `code_audit_daily_sample_report.md`
- `code_audit_operational_loop_sample_material.json` and `code_audit_operational_loop_sample_report.md`

## Generation

The checked-in sample reports are generated locally from the matching JSON material by `tools/generate_code_audit_sample_pack.py`.

The generator is local-only and deterministic:

- It does not run git.
- It does not run tests.
- It does not inspect GitHub.
- It does not use network, subprocess, environment reads, or SQLite.
- It writes only the sample files in this directory.

## Use

Use this pack as a structural reference for future private operator reporting. For real branch or merge work, build fresh reports from caller-provided current material and run the required verification outside these sample assets.
