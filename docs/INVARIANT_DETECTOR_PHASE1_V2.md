# Invariant Detector — Phase-1 Implementation Reconciliation v2

Status: **IMPLEMENTATION REVISION / CONSTITUTION UNCHANGED**

Baseline preserved at upstream commit `6fbf6483d78e2d098a1bdf9e393376d75a615beb`.

This document records the versioned implementation revision required to reconcile the original detector scaffold with the later frozen Phase-1 gate. It does not add a sixth morphology level, alter the five-level K hierarchy, or open real-domain search.

## 1. Morphology and experiment integrity are separate

The morphology result remains:

`D(X) = (Kc, Kp, Kg, KCH, KA)`.

`NO_TARGET_LEAKAGE` and `NO_HIDDEN_SEARCH_PATH_LEAKAGE` are experiment-integrity constraints. They are reported separately in `DetectorResult.integrity` and do not alter the five-coordinate morphology vector.

A system may therefore have a morphology vector that passes while the experiment is rejected for leakage. This is intentional: the morphology and the trustworthiness of the experiment are distinct objects.

## 2. Missing information is not disconfirmation

Required input that is absent is represented as unknown rather than false. A missing projection, transition, ND result, adapter map, or other required observation cannot by itself create a morphology `FAIL`.

Propagation rules:

1. Lower `FAIL` propagates upward as `FAIL`.
2. Lower `PARTIAL` or `UNDETERMINED` blocks any higher `PASS`; that higher `PASS` is demoted to `PARTIAL`.
3. Missing information is retained as incompleteness rather than rewritten as contradiction.

## 3. Fixture-oracle reconciliation

The synthetic fixture library keeps A0–A14 but separates its morphology and integrity expectations.

- A8 now retains its underlying morphology `(PASS,PASS,PASS,PASS,UNDETERMINED)` while independently failing the target-leakage integrity gate.
- A13 retains `(PASS,PASS,PASS,PASS,PASS)` while independently failing the hidden-search-path integrity gate.
- A12 remains a morphology-level ACROSS failure because its adapter-preregistration predicate is explicitly false in the ACROSS specification; this is distinct from the separate provenance leakage flags.

The fixture mutations remain synthetic oracle checks. They do not constitute independent mathematical verification.

## 4. Positive-control ladder

Five bounded controls are now explicit:

- `Pc = (PASS,U,U,U,U)`
- `Pp = (PASS,PASS,U,U,U)`
- `Pg = (PASS,PASS,PASS,U,U)`
- `Pch = (PASS,PASS,PASS,PASS,U)`
- `Pa = (PASS,PASS,PASS,PASS,PASS)`

The `R -> S1` covering calibration remains sample-scoped in code. Its general mathematical identity is separate from the finite executable sample.

The purpose of the ladder is to verify that evidence at one level never auto-promotes a candidate upward.

## 5. Computed ACROSS compatibility

Boolean compatibility flags remain supported only as synthetic scaffold evidence.

For the independently checked positive ACROSS control, `AcrossAdapter` supplies actual maps between source and target systems. The detector computes:

- projection compatibility,
- transition compatibility,
- outgoing traversal compatibility,
- return traversal compatibility,
- label compatibility,
- holonomy compatibility,
- target CH status,
- CH-pair compatibility.

A claimed computed control therefore depends on the supplied maps, not merely on preasserted compatibility booleans.

## 6. Predicate-isolating controls

Additional mutations isolate a declared boundary predicate from an otherwise valid candidate:

- `Kc`: projection invariance,
- `Kp`: nondegeneracy,
- `Kg`: local closure,
- `KCH`: null collision,
- `KA`: label transport computed from adapter maps.

These complement, rather than replace, the A0–A14 paired fixture mutations.

## 7. Representation invariance

The Phase-1 suite explicitly verifies that semantics-preserving changes do not alter the detector verdict, including:

- candidate renaming,
- state-order reversal,
- intermediate-state serialization order,
- CH-path serialization order.

This requirement is part of the completion gate.

## 8. Executable gate

`tools/run_phase1_gate.py` checks four groups:

1. A0–A14 fixture vectors and integrity verdicts,
2. paired fixture mutations,
3. five level-specific positive controls,
4. predicate-isolating mutations.

It emits machine-readable JSON and exits nonzero on mismatch. Its output always retains:

`"real_domain_search_allowed": false`

because synthetic Phase-1 success never authorizes or validates a real-domain K instance by itself.

## 9. Completion boundary

This revision does **not** by itself certify the whole Phase-1 freeze. Final certification still requires a clean run against the repository revision, compilation/regression checks, and a Completion Evidence record identifying the exact commit and environment.

No real-domain evidence is introduced by this revision. No claim is made that earlier historical development was completely unexposed to real-domain information; the verification gate applies to the frozen experiment from this version forward.
