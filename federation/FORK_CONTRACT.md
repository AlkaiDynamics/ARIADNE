# ARIADNE Project Fork Contract

This contract governs epistemic/project forks tracked by the Great Work distribution. It is distinct from Git repository forking.

```text
Git repository fork != ARIADNE epistemic/project FORK
```

## Fork object

A project fork is represented as:

```text
F = (P, I, Delta, A, C, D, R, X)
```

where:

- `P` — parent artifact/version/fork;
- `I` — inherited invariants;
- `Delta` — what this fork may change;
- `A` — assumptions introduced by the fork;
- `C` — epistemic and admissibility contract;
- `D` — dependencies on other forks/results;
- `R` — return, review, merge-candidate, or reopen conditions;
- `X` — outputs exposed through the boundary envelope.

## When to create a project fork

Create a first-class fork when at least one of these changes materially:

- frozen model or invariant;
- epistemic/admissibility rules;
- research objective;
- allowed transformation set;
- intended use;
- fundamental interpretation of the same evidence.

A new manuscript witness, competing reading, or search direction does not by itself require a project fork. Those remain ordinary ARIADNE variants, branches, torches, or research records unless one of the criteria above changes.

## Non-destructive import rule

A merge means that one project accepts a versioned result from another as an input. Projects are not collapsed into one narrative or evidence state.

```text
PROJECT_A --IMPORTS_RESULT--> PROJECT_B:ARTIFACT@VERSION
```

Imported results retain their original provenance, epistemic zone, admissibility scope, assumptions, dependencies, and residuals.

## Boundary envelope

Every inter-project handoff should expose, when applicable:

- Artifact ID
- Project/Fork ID
- Parent version
- Result
- Claim type
- Epistemic zone
- Admissibility scope
- Provenance
- Inputs/dependencies
- Inherited invariants
- Introduced assumptions
- Operator/transform
- Residuals/failures
- Prior-art status
- Prediction status
- Confidence/uncertainty
- Return trigger
- Candidate consumers

## Relation types

The federation reserves at least these inter-project relations:

```text
DERIVES_FROM
OPENS_FOCUS
FORKS_FROM
IMPORTS_RESULT
DEPENDS_ON
TESTS
PREDICTS
CONTRADICTS
SUPERSEDES
REINTERPRETS
MERGE_CANDIDATE
RETURN_WHEN
PING
```

A `PING` is a convergence event worth further testing. It is not automatic identity or validation.

## Prior-art gate at fork boundaries

When a handoff or completed artifact opens a materially new forced focus, run P0 before deep original synthesis. Reuse the existing field map when the new focus remains inside it; otherwise open a new full census.

```text
ARTIFACT
  -> RELATION SURFACE
  -> FORCED FOCUS
  -> P0 FULL or P0 DELTA
  -> INVESTIGATION
  -> NEW ARTIFACT
```

## Hard invariants

1. Preserve project identity, repository identity, and Git branch identity separately.
2. Preserve upstream mechanism separately from downstream policy/state.
3. Never let downstream project state silently modify canonical ARIADNE mechanism.
4. Never let SATURN silently amend SUN.
5. Never let Rosetta/operator work silently rewrite the frozen Fludd/Kepler/Completed Harmony historical layer.
6. No research data flows upstream merely because a downstream fork discovered it.
7. Generic improvements may be proposed upstream only after they are stripped of Great Work-specific research state.
8. All upstream upgrades are explicit and pinned.
