# KEYSTONE / K Morphology Detector — Phase-1 Implementation Revision v2

Status: **PROGRAM FREEZE PRESERVED / EXECUTABLE VERIFIER REVISION / REAL-DOMAIN SEARCH CLOSED**

Baseline preserved at canonical commit:

```text
6fbf6483d78e2d098a1bdf9e393376d75a615beb
```

This revision reconciles the implementation with the later Phase-1 gate without extending the frozen morphology.

## Scope

KEYSTONE remains representation-neutral but morphology-specific. It evaluates only the frozen cumulative structure:

```text
Kcore -> Kpath -> Kgraded -> KCH -> KACROSS
```

Failure against this detector is not failure of every possible relational theory.

No SUN, Saturn, MONOCHORD, COUNTERPOINT, Tree-of-Life, harmonic, historical, or other favored-domain material is used as detector input in this revision.

## Why v2 exists

The baseline implementation correctly passed its own oracle but combined several concerns that the revised gate requires to remain separate:

1. experiment-integrity failures changed morphology verdicts;
2. missing required data could become `FAIL` merely because a field was absent;
3. `PARTIAL` prerequisites did not block higher cumulative `PASS`;
4. independent higher-level failures were not explicitly separated from prerequisite-propagated failures;
5. nondegeneracy could be supplied as a Boolean answer;
6. graded labels did not have executable composition laws;
7. CH collision probability could be supplied rather than computed from a frozen finite experiment;
8. ACROSS compatibility could be supplied as Boolean flags instead of derived from adapter maps;
9. higher levels lacked an explicit common anchor preventing unrelated witness stitching;
10. permutation/renaming/serialization invariance was not a completion-gate requirement.

These are verifier-completion obligations, not theory changes.

## Versioned objects

```text
DETECTOR_SPEC_VERSION = 2.0.0
ND_POLICY = ND_V1_REQUIRED_TRANSITION_RELATION
```

The original files remain historical baseline artifacts. v2 lives in separate modules so the old oracle remains reproducible.

## Morphology vs experiment integrity

`detect(X)` now returns two distinct products:

```text
morphology = (Kc, Kp, Kg, KCH, KA)
integrity   = target leakage / search leakage / ledger / stopping rule
```

Integrity failure does not rewrite morphology coordinates. A candidate can therefore have:

```text
morphology = (PASS,PASS,PASS,PASS,PASS)
integrity  = FAIL
```

Such a run is unusable as evidence but still reports what the morphology predicates themselves did.

## Verdict semantics

Each level retains both:

- `independent_verdict`: result of that level's own predicates;
- `verdict`: cumulative verdict after prerequisite propagation.

`PARTIAL` has one defined meaning:

> At least one required predicate is established true, no required predicate is established false, and at least one required predicate remains unresolved.

`UNDETERMINED` means that the level has no sufficient evaluated predicate basis for either a positive or negative determination.

Cumulative rules:

- an independent `FAIL` is always retained;
- a failed lower prerequisite forces cumulative higher `FAIL`, but the higher independent result remains visible;
- a lower `PARTIAL` or `UNDETERMINED` blocks a higher independent `PASS`, demoting the cumulative higher result to `PARTIAL`;
- missing data never becomes a counterexample merely because a field is absent.

## ND v1

A Boolean `nd=True` is no longer a certificate.

`ND_V1_REQUIRED_TRANSITION_RELATION` requires a preregistered relation on the intermediate state space and checks that the lifted transition of each moved source state is represented by that relation. A bare tagged copy with no required relation fails.

The policy is deliberately versioned. It is a bounded operational definition for Phase 1, not a theorem that exhausts every possible notion of nondegeneracy.

## Connected certificates

Each supplied level carries the same declared `anchor_id`. Kgraded additionally verifies that its gamma uses the same outward/return path-channel identifiers supplied by Kpath. KACROSS maps the source anchor to the target anchor and explicitly preserves the designated moving witness.

This blocks success assembled from unrelated regions of a larger candidate system.

## Executable graded labels

Kgraded uses finite monoids for `rho` and `h` and verifies:

- monoid closure, identity, and associativity;
- the declared path composition;
- `rho` homomorphism on the selected composite;
- `h` homomorphism on the selected composite;
- local closure in `rho`;
- nontrivial displacement in `h`.

Therefore arbitrary labels cannot manufacture closure/nonclosure without satisfying the frozen composition rules.

## Executable CH collision test

The synthetic CH experiment freezes:

- exact equality;
- a fixed selected pair;
- a finite null-pair population;
- search budget;
- selection procedure;
- maximum collision probability;
- preregistration status.

The detector computes the collision rate from the supplied finite null pairs. It does not accept a caller-supplied collision-rate answer.

## Executable ACROSS

ACROSS now receives actual finite maps for:

- source states;
- observational classes;
- intermediate states;
- paths;
- rho labels;
- holonomy labels;
- anchors.

It computes the commutation checks. It additionally requires that the designated moved witness remains moved after translation. A collapsing adapter can therefore satisfy a transition square at a stationary image and still fail ACROSS because it erased the movement under test.

## Fixture and control gate

The revision preserves the identities `A0` through `A14` while changing the oracle where the gate changed:

- A8 target leakage: morphology remains a KCH pass; experiment integrity fails.
- A13 hidden search-path leakage: morphology remains a KACROSS pass; experiment integrity fails.

Every A fixture retains a paired mutation.

A separate predicate-isolation suite contains one mutation at each level whose intended failing predicate is the only false predicate at that level.

Five cumulative positive controls are supplied:

```text
C_KC   -> PASS, U, U, U, U
C_KP   -> PASS, PASS, U, U, U
C_KG   -> PASS, PASS, PASS, U, U
C_KCH  -> PASS, PASS, PASS, PASS, U
C_KA   -> PASS, PASS, PASS, PASS, PASS
```

The R->S1 covering calibration is explicitly sample-scoped. The universal covering identity is a separate proof claim and is not inferred from the finite calibration.

## Representation invariance

Phase-1 completion now explicitly tests:

- state-order permutation invariance;
- semantics-preserving renaming through KCH;
- JSON serialization/deserialization round-trip invariance.

These are mandatory completion checks.

## Phase-1 prohibition

Passing this implementation suite establishes only that KEYSTONE behaves according to the frozen synthetic verifier contract.

It does **not** establish:

- CHORD;
- THREAD;
- MONOCHORD historical attribution;
- COUNTERPOINT independence;
- universality of K;
- applicability to any real natural or historical system;
- absence of leakage in the earlier research history.

Real-domain search remains closed until the clean completion evidence is accepted.
