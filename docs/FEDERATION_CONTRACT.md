# ARIADNE Federation Contract

ARIADNE may coordinate many research, model, engineering, application, and experimental lines without owning their internal domain ontologies.

## Identity invariant

```text
repository identity
!= Git branch identity
!= project identity
!= durable ARIADNE FORK identity
```

A repository answers where files live. A Git branch answers which source-control history is being edited. A project identifies an intellectual or operational line. A durable `FORK` identifies a versioned project state created under explicit assumptions, invariants, inputs, controls, and return conditions.

The existing `branches` table remains reserved for cheap research-navigation branches such as DOWN / SIDEWAYS / ORTHOGONAL / UP searches. Durable project or epistemic forks use `project_forks` and must never be collapsed into navigation branches.

## Open-world registry

The federation registry is intentionally incomplete at every finite moment.

```text
CURRENTLY DISCOVERED N != TOTAL POSSIBLE N
```

Therefore:

- discovering a project name is enough to register it;
- `CLASSIFICATION_PENDING` is a valid state;
- no repository is required to register a project;
- failure to find a repository is an unresolved mapping result, not evidence that the project does not exist;
- repository existence does not determine project meaning;
- aliases and historical names are retained;
- no parent/child, dependency, replacement, or ownership relation is inferred merely from naming, repository layout, numerical equality, or chronology;
- low-attention or unresolved projects remain retained and addressable.

This contract is designed specifically to avoid losing lines whose handling has not yet been decided.

## Repository observations

Repository discovery is stored separately from project identity. An observation may be:

```text
OBSERVED
PARTIALLY_OBSERVED
UNVERIFIED
NO_MATCH_IN_CURRENT_CENSUS
```

These are facts about the repository census, not classifications of the project itself.

## Durable FORK lifecycle

A durable fork should preserve, as applicable:

```text
fork_id
project_id
focus_id
fork_type
parent_fork
parent_snapshot
forced_focus
reason_for_fork
inherited_invariants
frozen_inputs
allowed_changes
forbidden_changes
evidence_visibility
leakage_policy
hypotheses
predictions
controls
return_conditions
merge_policy
status
decision_records
checkpoint_stream
```

Supported generic fork types are:

```text
EPISTEMIC
CORPUS
MODEL
CONTROL
APPLICATION
IMPLEMENTATION
PRESENTATION
EXPERIMENT
UNRESOLVED
```

`UNRESOLVED` exists deliberately: the system must preserve a branch before forcing a taxonomy decision.

Fork outcomes are non-destructive:

```text
ACTIVE
REJOINED
PARTIAL_REJOIN
SUPERSEDED
REFUTED
BANKED
CONTROL
DIVERGED
```

`REJOINED` does not erase the fork. It records an outcome while preserving the complete lineage.

## Validation regime is orthogonal to evidence zone

G0/E0/E1/E2 answers whether material may support a claim and with what evidentiary status. It does not by itself identify the validation method.

ARIADNE therefore supports the orthogonal regimes:

| Regime | Validation basis |
| --- | --- |
| `FORMAL` | proof, derivation, exact computation |
| `HISTORICAL_TEXTUAL` | admissible witnesses and dependency analysis |
| `EMPIRICAL` | frozen predictions, observations, controls, statistics |
| `ENGINEERING` | acceptance tests, recovery, operational outcomes |
| `NORMATIVE` | explicit human authority, value judgment, or governance decision |

A single subject may have different statuses in multiple regimes. For example, a mathematical identity may be `FORMAL: VERIFIED` while a historical-intent claim involving that identity remains `HISTORICAL_TEXTUAL: HYPOTHESIS`.

## Cross-project handoffs

Projects exchange typed handoffs rather than untyped document dumps. Every handoff preserves:

```text
from_project
to_project
source_snapshot
payload_record_ids
epistemic_zones
validation_regimes
transformation_applied
assumptions
known_failures
unresolved_items
protected_invariants
accepted_status
decision_authority
```

Payloads retain source identity. Copying an E1 record from one project to another does not create independent corroboration.

## Mechanism vs policy/state

Canonical ARIADNE owns reusable mechanisms and contracts. A downstream distribution may own actual project registries, questions, torches, checkpoints, policies, adapters, and research state.

```text
MECHANISM_upstream != POLICY_OR_STATE_downstream
```

Project-specific registries should therefore be supplied by downstream profiles/distributions rather than hard-coded into canonical ARIADNE.
