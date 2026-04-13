# 01 — The Exact Permitted Claim Classes

Scope: the closed set of class names the Sovereign Engineering
Operating System uses when it talks about replayability, determinism,
evidence sufficiency, or execution-result trust.

Constitutional anchors: §3.10 (no unauthorized scope creep), §22.5
(replay fidelity contract), §23.12 (ReplayAnchor), §24.2 (INV-010
claim may not exceed captured evidence, INV-011 uncertified
equivalence is never exact replay).

---

## 1. The five classes

Exactly five classes exist. The set is closed. No other string may
appear in `ReplayAnchor.replay_class_claim`.

| # | String value       | Short label     |
|---|--------------------|-----------------|
| 1 | `exact`            | Exact replay    |
| 2 | `diagnostic`       | Diagnostic      |
| 3 | `semantic`         | Semantic        |
| 4 | `degraded`         | Degraded        |
| 5 | `unreplayable`     | Unreplayable    |

These are the exact strings written into the receipt. They are
lower-case, single-word, ASCII, no aliasing, no shortening.

## 2. Source-of-truth pin

The class set is not invented by this package. It is the intersection
of two already-frozen surfaces:

- `kernel/schemas/replay_anchor.schema.json`
  →
  ```json
  "replay_class_claim": {
    "type": "string",
    "enum": ["exact", "diagnostic", "semantic", "degraded", "unreplayable"]
  }
  ```
- `kernel/replay/replay_classifier.py`
  →
  ```python
  class ReplayClass(str, Enum):
      EXACT = "exact"
      DIAGNOSTIC = "diagnostic"
      SEMANTIC = "semantic"
      DEGRADED = "degraded"
      UNREPLAYABLE = "unreplayable"
  ```

This package constrains the **use** of those two surfaces. It does
not edit them, add to them, or rename their members.

## 3. Ordering

The classes have a partial order for the purpose of downgrades only.
From strongest evidence commitment to weakest:

    exact  >  diagnostic  >  semantic  >  degraded  >  unreplayable

This ordering is used by `04` to declare the permitted downgrade
transitions. It is **not** a numeric score, a user-visible severity
rank, or a priority weight. A caller that interprets `degraded` as
"smaller number = better" is misusing the taxonomy (see `07 §4`).

## 4. What each class is not

Each class name is used for exactly one purpose: to declare how much
a later replay can honestly prove. None of the five classes is:

- a validator-quality score
- a test-pass rate
- a confidence level
- a reviewer sentiment
- a workflow stage identifier
- a coverage metric
- a performance tier

A validator or reviewer surface that wants such a metric must
introduce a separate field; it may not overload `replay_class_claim`.
See `07 §5`.

## 5. Closure

The set `{exact, diagnostic, semantic, degraded, unreplayable}` is
closed under this package. Any proposal to:

- add a sixth class (for example, `provisional`, `attested`,
  `partial`, `tentative`);
- rename any of the five (for example, `exact` → `bit-exact`);
- merge two of the five (for example, treat `degraded` and
  `diagnostic` as one);
- split one of the five (for example, `semantic_equivalent` vs
  `semantic_regressed`)

is a **constitutional change** (§3.10) and must route through the
master plan, not through a design increment.

## 6. What this file does not do

- It does not define the classes. Definitions live in `02`.
- It does not say what evidence each class requires. That lives in
  `03`.
- It does not describe downgrade transitions. Those live in `04`.
- It does not list forbidden combinations. Those live in `07`.

This file is the **name set**. Nothing more.
