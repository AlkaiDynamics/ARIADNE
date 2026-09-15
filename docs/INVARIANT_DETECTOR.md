# Invariant Detector — Frozen Constitution and Phase-1 Gate

Status: **CONSTITUTION FROZEN / DETECTOR SPECIFICATION FROZEN**

This document operationalizes the frozen research program without adding new mathematical layers. The detector exists to distinguish the compound morphology from nearby impostors before any blind real-domain ACROSS search is allowed.

## 1. Frozen five-level morphology

### Kcore — hidden state change inside observational equivalence

Data:

- complete state space `E`
- observational space `B`
- projection `pi: E -> B`
- transition `tau: E -> E`
- moved-state witness set `W_tau = {x in E | tau(x) != x}`

Required:

- `W_tau != empty`
- `pi(tau(x)) = pi(x)` for the tested state space
- each instantiated claim has a moved witness whose projection is unchanged

### Kpath — nondegenerate typed traversal

Add an intermediate space `Y` and maps:

`E --o--> Y --r--> E`

with:

- `r(o(x)) = tau(x)`
- preregistered `ND(o,r)` true

`ND` is the constitutional guard against vacuous/trivial factorization.

### Kgraded — local cancellation without complete cancellation

For a specified path `gamma` and identity path `id_E`, add path observables:

- `rho`: local relational label
- `h`: complete displacement / holonomy

Required:

- `rho(gamma) = rho(id_E)`
- `h(gamma) != h(id_E)`
- label reciprocity does not imply actual path inversion

The detector does not assume that the codomains of `rho` or `h` are groups.

### KCH — inequivalent internal generation with convergent realization

Add:

- independently fixed internal equivalence relation `~int`
- independently fixed realization map `Phi`
- preregistered null ensemble / collision threshold

Required for a CH pair `(gamma_A, gamma_B)`:

- `gamma_A !~int gamma_B`
- `Phi(gamma_A) = Phi(gamma_B)`
- `Phi` is discriminative
- `Phi` and `~int` were preregistered
- null collision rate is small

### KACROSS — structure-preserving transport

A candidate adapter between two fully equipped domains must preserve:

- projection structure
- core transition
- outgoing traversal
- return traversal
- local relational labels
- holonomy/displacement
- CH structure where applicable

The adapter must be preregistered, low-complexity under the declared criterion, and survive held-out checks.

## 2. Detector semantics

`D(X) = (Kc, Kp, Kg, KCH, KA)`

Each coordinate is one of:

- `PASS`
- `FAIL`
- `PARTIAL`
- `UNDETERMINED`

Evaluation order:

`Kc -> Kp -> Kg -> KCH -> KA`

Rules:

1. `FAIL` propagates upward.
2. A lower `UNDETERMINED` blocks a higher `PASS`; the higher verdict is demoted to `PARTIAL` unless independent contradiction makes it `FAIL`.
3. `PARTIAL` is retained as evidence-bearing incompleteness.
4. Higher-level evidence never upgrades an explicitly failed lower level.

## 3. Constitutional provenance gates

Every level may carry provenance.

### No target leakage

A level fails when its result depends on target information being embedded or selected through the representation.

### No hidden search-path leakage

A level fails when a broad search/tuning process is incompletely logged or successes are selected after unreported trial-and-error.

These failures occur at the level whose evidence was contaminated and then propagate upward.

## 4. Phase-1 fixture oracle

The synthetic suite is deliberately ordered from core impostors to full ACROSS controls.

| Fixture | Purpose | Expected vector |
|---|---|---|
| A0 | pure identity | FAIL, FAIL, FAIL, FAIL, FAIL |
| A1 | visible change | FAIL, FAIL, FAIL, FAIL, FAIL |
| A2 | hidden displacement only | PASS, FAIL, FAIL, FAIL, FAIL |
| A3 | trivial/degenerate factorization | PASS, FAIL, FAIL, FAIL, FAIL |
| A4 | genuine path, wrong local closure | PASS, PASS, FAIL, FAIL, FAIL |
| A5 | local closure, no global displacement | PASS, PASS, FAIL, FAIL, FAIL |
| A6 | graded morphology, no CH pair | PASS, PASS, PASS, FAIL, FAIL |
| A7 | fake CH from coarse realization / high null collision | PASS, PASS, PASS, FAIL, FAIL |
| A8 | fake CH from target leakage | PASS, PASS, PASS, FAIL, FAIL |
| A9 | genuine CH, no ACROSS attempted | PASS, PASS, PASS, PASS, UNDETERMINED |
| A10 | numerical-lookalike ACROSS impostor | PASS, PASS, PASS, PASS, FAIL |
| A11 | partial ACROSS transport | PASS, PASS, PASS, PASS, FAIL |
| A12 | overfit/unpreregistered adapter | PASS, PASS, PASS, PASS, FAIL |
| A13 | search-path p-hack | PASS, PASS, PASS, PASS, FAIL |
| A14 | genuine synthetic ACROSS | PASS, PASS, PASS, PASS, PASS |

A finite exact-sampling version of the standard `R -> S1` cover is included as a `Kcore` calibration only. It must not be promoted to higher levels without additional evidence.

## 5. Mutation harness

Each fixture has at least one paired mutation with a frozen expected verdict. Mutation tests verify that the detector is responding to the intended constitutional predicate rather than to incidental features of the synthetic example.

Examples include:

- adding hidden displacement to A0/A1
- adding an admissible path to A2
- repairing ND in A3
- repairing local closure or holonomy in A4/A5
- adding a valid CH event to A6
- lowering the null collision rate in A7
- removing target leakage in A8
- adding a valid ACROSS adapter to A9
- repairing one transport predicate in A10/A11
- preregistering the adapter in A12
- recording the complete search path in A13
- breaking one transport predicate in A14

## 6. Advancement gate

No exploratory real-domain ACROSS search is permitted until all of the following hold:

- A0–A13 are rejected at the intended level
- A14 is accepted at all five levels
- the core-only calibration remains core-only
- mutation tests demote/promote exactly as expected
- target leakage independently causes rejection
- hidden search-path leakage independently causes rejection

Passing this gate validates the detector methodology only. It does **not** establish a real-world KACROSS instance.

## 7. Quarantined structures

The following remain outside the detector definition and may re-enter only by derivation under logged assumption and search provenance:

`12`, `V4`, `phi`, Fibonacci, primes, Tree of Life, music-specific ratios, and other favored structures.

Their presence may be inspected only after a blind detector result has been produced.
