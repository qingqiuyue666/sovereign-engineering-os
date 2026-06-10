# Independent Verification Runbook V1

External review required: yes.

This runbook is for a reviewer who starts from the public repository and does
not rely on chat context.

## Inputs

- Repository: `qqyqqyqqy666-wq/sovereign-engineering-os`
- External audit packet: `docs/audits/external_audit_packet_v1.md`
- Machine-readable packet: `reports/audits/external_audit_packet_v1.json`
- Claim matrix: `reports/audits/claim_to_evidence_matrix_v1.json`

## Verification Commands

Run these commands from a clean clone:

```bash
git rev-parse HEAD
git rev-parse 'v0.1.0-rc3^{}'
python3 scripts/external_audit_packet_check_v1.py
python3 scripts/claim_to_evidence_check_v1.py
python3 scripts/security_control_check_v1.py
python3 scripts/supply_chain_check_v1.py
python3 scripts/ai_admission_check_v1.py
python3 scripts/dogfood_evidence_check_v1.py
python3 scripts/reliability_benchmark_v1.py
make verify
make ci
```

## Review Steps

1. Confirm `v0.1.0-rc3` still resolves to
   `9a363f95b85602ffc598db463dc6181a9bbbdf3c`.
2. Review PRs #540 through #548 and confirm each PR was merged through GitHub.
3. Compare each claim in the claim matrix with its evidence references.
4. Run the external audit packet check and inspect any failure before using
   the packet for review.
5. Review accepted risks, residual risks, and final blocker table.
6. Confirm the required non-certification statements are present.
7. Decide independently whether more evidence is required.

## Boundaries

Do not request or inspect secret values. Do not require live AI provider
credentials. Do not treat this packet as final signoff or public recognition.
