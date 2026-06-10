# Landing Ready Reproducibility V1

Run from the repository root:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 scripts/landing_ready_reproducibility.py \
  --repo . \
  --output-dir /tmp/seos-landing-ready-repro
```

The script creates a fresh clean clone, records source and clone HEAD values,
runs the minimum meaningful CLI and operator flow validation suite, runs
`git diff --check`, and writes `clean_clone_reproducibility_receipt.json`.

The clean-clone receipt is evidence for reproducibility only. It does not read
secrets, call AI providers, perform network services after clone creation, push
branches, publish releases, or claim OS-level isolation.
