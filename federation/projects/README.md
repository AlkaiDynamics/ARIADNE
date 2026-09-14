# Great Work project and branch registry

The federation registry is intentionally open-world.

ARIADNE must preserve a known line before it knows what that line *is*.

```text
DISCOVERED
  -> INVENTORIED
  -> CLASSIFICATION_PENDING
  -> CLASSIFIED
  -> REGISTERED
```

A line may remain `CLASSIFICATION_PENDING` indefinitely without losing visibility, priority, provenance, or investigative rights.

## What the registry does not assume

An inventory entry does not establish that the item is:

- an independent project;
- an epistemic fork;
- a software subsystem;
- a product;
- a repository;
- a research program;
- a protocol;
- a historical alias of another item.

Those are separate decisions.

## Identity dimensions

Keep at least these distinct:

```text
PROJECT / SYSTEM IDENTITY
REPOSITORY IDENTITY
GIT FORK IDENTITY
GIT BRANCH IDENTITY
HISTORICAL NAME / ALIAS
ARTIFACT VERSION
EPISTEMIC FORK IDENTITY
```

Never infer one from another.

## Open-N rule

Enumeration is an inventory operation, not a closure operation.

```text
CURRENTLY KNOWN N != TOTAL POSSIBLE N
```

New lines are added before classification. Missing registry entries are not evidence that a line does not exist.

## Classification decisions

When the handling of an unresolved line is eventually decided, record the decision as a new federation event and preserve the prior unresolved state. Do not rewrite the historical registry as if the classification had always been known.
