# Alkai Great Work Distribution / Federation Contract

This repository is a **distribution/federation fork** of `zhenrez/ARIADNE`.

It is not itself an ARIADNE epistemic/project FORK merely because GitHub reports `fork: true`.

## Identity invariant

```text
Git repository fork
!= Git branch
!= ARIADNE epistemic/project FORK
```

Repository and branch identities describe source-control topology. ARIADNE FORK identities describe intellectual/project state: what changed, from which parent state, under which assumptions, with which invariants, controls, evidence boundaries, predictions, and return conditions.

## Responsibility split

### Canonical upstream — `zhenrez/ARIADNE`

Owns generic instrument behavior:

- evidence custody and provenance primitives;
- generic epistemic firewall;
- generic P0 / prior-art field-census machinery;
- generic Torch and checkpoint mechanisms;
- generic FORK, handoff, decision, validation-regime, and federation contracts;
- generic schemas and tests;
- synthetic fixtures and reusable specifications.

It should not require Great Work-specific research state to function.

### Great Work distribution — `AlkaiDynamics/ARIADNE`

Owns federation policy and active state for connected projects:

- AYLI;
- SUN;
- SATURN;
- Sophia;
- Argo / Lifeline;
- Harmonia-Occulta / Completed Harmony work;
- R.O.S.E.T.T.A.S.;
- future Great Work projects and adapters.

It owns project-specific questions, torches, checkpoints, adapters, decision records, frozen model snapshots, handoffs, and cross-project FORK instances.

## Governing law

```text
MECHANISM_upstream != POLICY_OR_STATE_downstream
```

A generally reusable capability discovered downstream should be generalized and proposed upstream explicitly. Research evidence, hypotheses, project state, and corpus material do not flow upstream merely because the downstream distribution discovered or uses them.

## Upstream synchronization

The distribution pins a specific upstream commit in `distribution.yaml`.

Default policy:

```text
EXPLICIT_PINNED_UPGRADE
```

Do not continuously rebase or auto-sync. An upstream engine change can itself affect research behavior and therefore must be traceable as a versioned dependency.

## ARIADNE FORK lifecycle

Durable epistemic/project forks should eventually preserve at least:

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
prior_art_gate
validation_regime
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

A Git repository or Git branch may host zero, one, or many such FORKs.

## Fork outcomes

Rejoining never erases lineage. Durable outcomes include:

```text
REJOINED
PARTIAL_REJOIN
SUPERSEDED
REFUTED
BANKED
CONTROL
DIVERGED
```

The original fork remains addressable.

## SATURN rule

SATURN consumes a pinned SUN snapshot as an application fork. SATURN may generate return proposals, contradictions, architectural consequences, or new tests, but SATURN success is not evidence that SUN is true.

```text
SATURN finding
-> ARIADNE G0 return proposal
-> SUN prior-art / test / evidence path
```

SUN changes do not silently rebase existing SATURN runs. A newer SUN snapshot may produce a new SATURN fork so downstream consequences can be compared.

## AYLI rule

AYLI owns its domain semantics and research objects. ARIADNE owns stable identities, provenance, lineage, cross-fork relationships, evidence boundaries, decision history, and generated views across project states.

AYLI tables should increasingly become generated views over normalized evidence/unit/operator/relation records rather than independent hand-maintained truth stores.

## Migration rule

The initial GitHub fork already contains Great Work-specific state inherited from upstream. Preserve and inventory that state first. Do not move runtime-sensitive files until the downstream profile/adapter mechanism can read their new locations. Purify upstream only after downstream preservation has been verified.
