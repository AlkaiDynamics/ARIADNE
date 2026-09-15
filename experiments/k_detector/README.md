# K Morphology Detector — Phase 1 Verification Engineering

Status: **FROZEN SPEC / SYNTHETIC VERIFICATION ONLY**

This experiment implements the already-frozen five-level morphology detector:

```text
Kcore -> Kpath -> Kgraded -> KCH -> KACROSS
```

It does not add a new mathematical layer and it does not test real historical, natural, musical, TOL, or other favored domains.

## Frozen detector

The detector returns:

```text
(Kc, Kp, Kg, KCH, KA)
```

with coordinate verdicts:

```text
PASS | FAIL | PARTIAL | UNDETERMINED
```

Failure propagates monotonically upward. A lower `FAIL` forces every higher level to `FAIL`. A higher level cannot be promoted to `PASS` above an `UNDETERMINED` prerequisite.

## Constitutional integrity guards

Two experiment-wide guards run before morphology scoring:

1. **No target leakage through representation choice.**
2. **No hidden search-path leakage.**

A fixture that intentionally violates either guard is constitutionally rejected rather than counted as a morphology hit.

## A0–A14 synthetic fixture suite

| Fixture | Intended boundary |
|---|---|
| A0 | `Kcore` — pure identity / no hidden displacement |
| A1 | `Kcore` — change remains observationally visible |
| A2 | `Kpath` — trivial factorization rejected by preregistered `ND` |
| A3 | `Kpath` — traversal does not compose to `tau` |
| A4 | `Kgraded` — local relational closure fails |
| A5 | `Kgraded` — global displacement is trivial |
| A6 | `KCH` — claimed paths are internally equivalent |
| A7 | `KCH` — fake collision from nondiscriminative `Phi` |
| A8 | `KCH` — collision is too common under preregistered null |
| A9 | `KCH` — `Phi` selected after observing the pair |
| A10 | `KACROSS` — projection square does not commute |
| A11 | `KACROSS` — traversal square does not commute |
| A12 | Constitutional — target encoded in representation choice |
| A13 | Constitutional — unlogged search-path / p-hack |
| A14 | Positive control — all five levels satisfied by construction |

Every negative fixture is a one-predicate perturbation of the positive construction where practical, so the failure boundary is explicit rather than inferred from a broadly different example.

## Mutation harness

The mutation harness starts from A14 and flips one frozen predicate at a time at `Kc`, `Kp`, `Kg`, `KCH`, and `KA`, plus independent target-leakage and search-leakage mutations. The expected monotone demotion vector is asserted exactly.

## Scope boundary

Passing this synthetic gate does **not** validate the theory or any real-world instance. It establishes only that the implementation recognizes the formal positive control and rejects the specified impostors at the intended boundaries.

Real-domain candidate extraction remains forbidden until the Phase-1 gate passes.

## Run

From this directory:

```bash
python -m unittest -v test_detector.py
python run_gate.py
```

The implementation uses only the Python standard library.
