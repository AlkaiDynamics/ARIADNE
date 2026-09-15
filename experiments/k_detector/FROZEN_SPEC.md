# Frozen K Morphology Detector Specification

This file records the theory-side contract implemented by `detector.py`. It is intentionally narrower than any historical or domain interpretation.

## Levels

### Kcore

Given `E`, `B`, `pi:E->B`, and `tau:E->E`:

- `W_tau={x in E: tau(x) != x}` must be nonempty.
- `pi(tau(x))=pi(x)` for every evaluated `x`.
- At least one explicit hidden-displacement witness must exist.

### Kpath

Extend Kcore with a typed intermediate `Y`, `o:E->Y`, `r:Y->E`, and a preregistered nondegeneracy predicate `ND`:

- `r o = tau`.
- `ND(o,r)` must pass.

### Kgraded

For a specified composite path `gamma` and identity path `id`:

- local relational closure: `rho(gamma)=rho(id)`;
- global nonclosure: `h(gamma)!=h(id)`.

Label-level cancellation must not be interpreted as proof that the return path is the inverse path.

### KCH

There must exist `gamma_A`, `gamma_B` such that:

- they are inequivalent under the preregistered internal equivalence;
- `Phi(gamma_A)=Phi(gamma_B)`;
- `Phi` was fixed before the pair was inspected;
- `Phi` is discriminative somewhere on the admissible path set;
- the collision probability under the preregistered null is at or below the preregistered maximum.

### KACROSS

A candidate adapter between source and target K structures must preserve the relevant structure through the preregistered commutation checks for projection, core transition, typed traversal, path transport, local labels, global displacement, and CH pair compatibility where defined.

## Constitutional rules

1. No target leakage through representation choice.
2. No hidden search-path leakage.

The experiment records these as independent integrity failures. They are not additional morphology levels.

## Verdicts

Each level returns exactly one of:

`PASS`, `FAIL`, `PARTIAL`, `UNDETERMINED`.

Evaluation order is:

`Kc -> Kp -> Kg -> KCH -> KA`.

A lower `FAIL` forces all higher levels to `FAIL`. A higher `PASS` is not permitted above an `UNDETERMINED` prerequisite.

## Phase-1 boundary

This branch is verification engineering only. It may use synthetic fixtures and mutations. It must not perform blind real-domain searching or reintroduce quarantined favored structures as design inputs.
