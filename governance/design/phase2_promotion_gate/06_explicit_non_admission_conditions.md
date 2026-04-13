# 06 — Explicit Non-Admission Conditions

Scope: the **conditions under which phase-2 implementation is forbidden
even if the roadmap looks attractive**. Where `01`/`02`/`03`/`04`/`05`
enumerate what must hold for admission, this file enumerates what, if
true, is an automatic denial regardless of how otherwise appealing the
candidate appears.

These are not informational warnings. They are denials.

Constitutional anchors: §3.1, §3.10, §3.12, §3.13, §3.14, §27, §31.

---

## 6.1. Authority cannot move out of the Python control plane

**Denial trigger:** any proposal that places any of the following in a
substrate that is not the Python control plane host process:

- capability issuance (`CapabilityToken` minting)
- approval barrier adjudication (C22.3)
- seal ordering adjudication (C22.1 / C22.2)
- `ReplayAnchor` minting
- `AuditRecord` authoring
- `Revision` / `SnapshotRoot` minting
- `signoff_gate` evaluation
- `replay_classifier` adjudication
- `version_tuple` composition policy (the hash kernel may move; the
  composition cannot)

**Why:** §3.1 truth sovereignty; kernel singularity. Authority in a
substrate is no longer the kernel.

**No exceptions.** Performance, ergonomics, and elegance are not
grounds.

---

## 6.2. Substrate C admitted without local-path saturation evidence

**Denial trigger:** any attempt to admit Linux/KVM sidecar or remote
worker when substrates A+B have **not** been measured insufficient for
a specific, named, reproducible workload.

**Why:** §27 (mature-first), §5.2, and the C-ENTRY-1 entry criterion.
Network introduces a new failure-and-drift surface; it is not allowed
as a convenience.

**No exceptions** for distributed execution roadmaps, cluster
coordination plans, or "we might need it later" arguments. Those are
Phase-3+ design questions, not Phase-2 admissions.

---

## 6.3. `exact` replay claims without the §04 evidence matrix

**Denial trigger:** any substrate admission that claims or enables a
`ReplayAnchor` class of `exact` for a workload whose four-dimension
evidence (time, randomness, worker determinism, audit binding; see
`04`) is incomplete.

**Why:** §3.3, §3.12, §22.5. "Exact" is an honesty claim; it is
narrower under Phase-2 substrates, not broader.

**No exceptions** for "the substrate is probably deterministic" or
"we've tested it a lot". Evidence is per the §04 matrix.

---

## 6.4. Substrate admission that silently widens exact class

**Denial trigger:** any change that takes a workload currently
classified at `semantic` (or below) and *quietly* moves it to
`exact` as a side effect of substrate admission, without the TLA-5
closure (see `05`) and without the §04 evidence matrix.

**Why:** §3.12 downgrade discipline applies in both directions.
Silent class *raises* are as dishonest as silent class *drops*.

---

## 6.5. Admission PR that bundles non-scope changes

**Denial trigger:** a phase-2 admission PR that also includes changes
to any of: UI, dashboards, project shell, lane orchestration
ergonomics, plugin surfaces, extension API, marketplace, multi-vendor
routing breadth, benchmark breadth, fairness scheduler, distributed
execution, cluster coordination, remote sync protocols, release /
packaging / notarization breadth.

**Why:** one of the §27 classic failure modes is internalizing a
substrate *and* expanding surface in one step, so neither is
reviewable.

**No exceptions.** Each of these is a separate design increment; none
is bundled.

---

## 6.6. Admission PR that modifies the constitution or foundation

**Denial trigger:** the admission PR modifies
`governance/constitution/sovereign_engineering_operating_system_master_plan_v11.txt`
or `governance/implementation/v11_narrow_path_implementation_foundation.md`.

**Why:** §3.10. Changes to the authority base land first, separately,
and the gate is re-evaluated against the new baseline.

---

## 6.7. Admission PR that deletes the Python reference prematurely

**Denial trigger:** a Rust downshift admission PR that removes the
Python reference before the A/B harness has shown byte-for-byte or
classification-equivalent agreement across the corpus for the
declared N consecutive runs (CF-R-3 / CF-R-4).

**Why:** §3.14 replacement-by-evidence; the Python reference is the
reference until evidence reverses that relationship.

**Rule:** removal of the Python reference is a *second* gate, not
part of the admission. The admission PR adds Rust behind the wrapper;
a later PR (after the agreement period) removes Python.

---

## 6.8. Admission PR that skips the pre-registered demotion trigger

**Denial trigger:** an admission PR that does not name, in its
description, the specific kind of failure that would demote the
candidate back to `defer-pending-evidence`.

**Why:** §3.14 and the `00` principles. Admissions without a known
reversal path are irreversible admissions, which are exactly what
§27 forbids.

---

## 6.9. Admission on aesthetic or roadmap-anticipation grounds

**Denial trigger:** the admission PR's justification is, explicitly
or implicitly, one or more of:

- "Rust is faster" (without a measurement on the real corpus)
- "Wasm is cleaner" (without a determinism or throughput win)
- "The roadmap implies we'll need this" (without evidence)
- "Other projects do it this way" (irrelevant under §3.14)
- "The CI is already slow" (substrate admission is not a CI fix)
- "This will be useful later" (Phase-2 is not a Phase-3 dress
  rehearsal)

**Why:** §3.14 and §27 both forbid ideological internalization. A
justification that is an aesthetic claim is a denial.

---

## 6.10. Admission while the narrow path is unstable

**Denial trigger:** admission PR proposed while `main` has an open
narrow-path regression, a flaking AT on the tracer-bullet suite, or
an unresolved drift incident in `delta_register.yaml`.

**Why:** §27 forbids internalizing substrates on a shaky base.
Stabilize first; admit later.

---

## 6.11. Admission that moves authority into a lane

**Denial trigger:** any proposal that introduces multi-lane execution
with independent authority per lane, distributed consensus on
truth, or cluster-local authority state.

**Why:** §3.1 kernel singularity; this is distributed execution and
is explicitly non-scope.

**No exceptions** for "same-host multi-lane" either; lanes remain
subordinate to the single control plane.

---

## 6.12. Admission where the substrate's enter/exit path isn't test-covered

**Denial trigger:** admission PR whose substrate enter/exit
`AuditRecord` path is not covered by a test that forces the
`exited_failed` and `exited_tainted` transitions.

**Why:** CF-4 in `02`. A substrate whose failure path is untested is
admitted on faith, not evidence.

---

## 6.13. Admission that changes receipt shape

**Denial trigger:** admission PR that modifies the shape of
`ReplayAnchor`, `ValidationReceipt`, `AuditRecord`,
`DriftEventRecord`, `CapabilityToken`, `ApprovalArtifact`,
`Revision`, or `SnapshotRoot`.

**Why:** schema changes are governance changes. They are not bundled
with substrate admissions.

**Rule:** if a field must be added (e.g., a substrate id in
`environment_fingerprint`), it is a *separate* design + governance
increment, landed first. The admission PR then depends on that
increment being merged.

---

## 6.14. Admission that broadens mutation classes

**Denial trigger:** admission PR that, directly or as a side effect,
introduces a new mutation class (e.g., multi-file patches where the
current class is single-file; network-enabled validators where the
current class is network-off; subprocess-enabled Wasm guests).

**Why:** substrate admissions execute existing classes under
different conditions. Broadening classes is a separate, governed
increment (§30.6 broadening rule).

---

## 6.15. Admission without a named sign-off

**Denial trigger:** admission merged without a §31 sign-off record
that names the candidate, the matching gate, the evidence artifact,
the reversibility path, and the demotion trigger.

**Why:** §31. A sign-off that does not say what it signs off on is
not a sign-off.

---

## Summary posture

These conditions are not exhaustive edge cases. They are the standard
denials a reviewer should check before reaching the per-candidate
gates. An admission PR that survives every one of §§6.1–6.15 has
earned the right to be evaluated against `02`/`03`/`04`/`05`; an
admission PR that trips any one of them is denied, regardless of how
attractive the roadmap, the calendar, or the engineering aesthetic
makes it look.
