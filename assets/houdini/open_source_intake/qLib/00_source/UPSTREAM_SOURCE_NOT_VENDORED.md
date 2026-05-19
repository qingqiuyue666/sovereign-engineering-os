
# qLib Upstream Source Not Vendored

The full qLib upstream source is intentionally not vendored into this repository.

Upstream repository:

https://github.com/qLab/qLib

Reason:

qLib contains Houdini assets, examples, gallery files, OTL/HIP/GAL binaries, Houdini Python utilities, package/runtime integration files, and execution surfaces including subprocess usage, socket/urllib usage, ffmpeg helpers, hou.hipFile, hou.hda, hou.node, and hou.parm interactions.

This repository keeps qLib as an open-source intake reference, not as production-imported code.

Allowed contents in this intake:

- license copy

- upstream README copy

- file inventory generated during intake

- extension counts

- Houdini asset file inventory

- HFX mapping

- clean-room rebuild plan

- intake report

Production use remains blocked until a specific candidate is reviewed, rebuilt or wrapped under HFX conventions, preview-tested, and shot-bound validated.

Status:

intake_only

Production import:

blocked

Direct HFX Core12 merge:

blocked

Clean-room adaptation:

allowed only after candidate-specific review.

