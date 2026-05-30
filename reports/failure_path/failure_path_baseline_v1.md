# Failure Path Baseline V1

This report records the Wave 4 fail-closed and adversarial coverage baseline.
It is repository evidence only and does not claim external recognition.

| Case ID | Risk Covered | Expected Safe Result |
| --- | --- | --- |
| missing_task | Missing task reference | Command exits nonzero and creates no execution receipt. |
| bad_workspace | Uninitialized workspace | Command exits nonzero with workspace error. |
| duplicate_task_id | Duplicate task id | Second create fails closed and does not overwrite. |
| missing_approval | Run before approval | Run exits nonzero with approval required. |
| rejected_task_cannot_run | Rejected task run attempt | Run exits nonzero with task rejected. |
| corrupted_receipt | Malformed receipt JSON | Receipt read fails closed. |
| corrupted_observation_json | Malformed observation JSON | JSON parse fails closed. |
| missing_evidence | Missing evidence reference | Evidence command exits nonzero. |
| replay_impossible_not_reconstructable | Incomplete replay | Replay does not claim reconstructable. |
| tag_mismatch | Wrong expected tag target | Mismatch is detectable without moving the tag. |
| network_failure_no_pass | Failed network-like command | Failed command cannot print PASSED. |
| interrupted_script_no_success_marker | Interrupted script | Success marker is absent after interruption. |
| invalid_cli_args | Bad CLI arguments | CLI exits nonzero. |
| fake_pass_log_rejected | Fake PASS log | Failed command log is not accepted as success. |
| path_leak | Evidence path outside workspace | Path is rejected. |
| shell_metacharacters | Metacharacters in identifier | Identifier is rejected. |
| path_traversal | Traversal in identifier | Identifier is rejected. |
| unicode_emoji_long_fields | Unicode, emoji, and long objective fields | Data remains data and does not grant execution. |
| prompt_injection_no_authority | Objective asks to bypass approval | Text does not become executable authority. |

Validation commands:

- `bash scripts/failure_path_smoke_v1.sh`
- `python3 scripts/adversarial_smoke_v1.py`
- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.tracer_bullet.test_failure_path_hardening_v1`
- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests/adversarial`

