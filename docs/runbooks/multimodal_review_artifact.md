# Multimodal Review Artifact Runbook

## Command

```bash
python3 seos.py review create <shot_id> --json
```

The command writes `review_artifact.json` and `review_packet.md` under `work/review_artifacts/`. Media remains represented as ArtifactRefs grouped into text, image, video, audio, and data slots.
