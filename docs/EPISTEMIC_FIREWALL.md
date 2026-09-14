# ARIADNE Epistemic Firewall

This policy is a hard architectural constraint.

## Core distinction

ARIADNE separates **guidance that tells us where to look** from **evidence that can support what we believe**.

The research-history timeline, chats, design rationale, working hypotheses, internal summaries, prior assistant conclusions, speculative correspondence tables, and machine-generated candidate links are normally **G0 — DISCOVERY_GUIDANCE**.

They may guide inquiry. They may not support research-object claims.

The governing rule is:

```text
G0 GUIDANCE
  -> QUESTION
  -> SEARCH
  -> E0 CANDIDATE SOURCE
  -> VERIFICATION
  -> E1 ADMISSIBLE EVIDENCE
  -> INDEPENDENT CORROBORATION
  -> E2 CORROBORATED EVIDENCE
```

The forbidden route is:

```text
G0 -> summary(G0) -> extraction(G0) -> graph(G0) -> "evidence"
```

A derivative of G0 remains G0 until an independent admissible source is acquired and verified.

## Epistemic zones

| Zone | Name | May guide search? | May support research-object claims? | May count as independent corroboration? |
|---|---|---:|---:|---:|
| **G0** | Discovery Guidance | Yes | **No** | **No** |
| **E0** | Candidate / Unverified Source | Yes | No | No |
| **E1** | Verified Admissible Evidence | Yes | **Yes** | Conditional on dependency |
| **E2** | Independently Corroborated Evidence | Yes | **Yes** | **Yes, after dependency analysis** |

`MACHINE_PREDICTION`, `USER_HYPOTHESIS`, `STRUCTURAL_ALIGNMENT`, `TOL_PREDICTION`, and `CHECKSUM_PREDICTION` are not evidence zones by themselves. They remain non-evidentiary until linked to independently verified E1/E2 records.

## Scope matters

A G0 research timeline **is admissible evidence for the history of the research program**. It can support claims such as:

> "The project adopted the preserve-both-branches rule on this date."

It cannot support claims such as:

> "The ancient source historically contained the interpretation discussed in that chat."

Every source therefore has an **admissibility scope**.

### Typical G0 admissible scopes

- `RESEARCH_HISTORY`
- `DESIGN_RATIONALE`
- `DECISION_PROVENANCE`
- `HYPOTHESIS_PROVENANCE`
- `CORRECTION_HISTORY`

### Typical G0 forbidden scopes

- `HISTORICAL_CLAIM_SUPPORT`
- `TEXTUAL_CLAIM_SUPPORT`
- `SCIENTIFIC_CLAIM_SUPPORT`
- `EMPIRICAL_VALIDATION`
- `INDEPENDENT_CORROBORATION`
- `CROSS_TRADITION_CONVERGENCE_COUNT`

## Guidance may change search priority, not belief

ARIADNE is allowed to use G0 to change:

```text
P(inspect source S_i | guidance)
```

It must not use G0 as evidentiary input to increase:

```text
P(claim C | admissible evidence)
```

In plain language: **guidance can tell ARIADNE where to look next; it cannot make the expected answer more credible before independent evidence is acquired.**

## Edge firewall

ARIADNE must distinguish the relation types:

```text
GUIDES_TO
DISCOVERED_VIA
TESTS
CONTRADICTS_GUIDANCE
VERIFIED_AS
SUPPORTS
CORROBORATES
```

A G0 object may create `GUIDES_TO`, `DISCOVERED_VIA`, or `TESTS` edges.

It may not create a `SUPPORTS` or `CORROBORATES` edge to a research-object claim.

## No evidence laundering

The following must never create multiplicity:

```text
chat says X
-> timeline says X
-> summary says X
-> graph node says X
-> generated matrix says X
```

These are one provenance family, not five supporting sources.

ARIADNE must retain provenance closure so all descendants can be traced to their G0 ancestor and assigned evidentiary weight zero for research-object claims.

## Promotion is creation, never mutation

A G0 object is never "promoted" into E1 by changing a flag on the same record.

Instead:

```text
G0 hypothesis
  --GUIDES_TO-->
E0 located source
  --VERIFIED_AS-->
E1 source-derived evidence record
```

The original G0 record remains unchanged forever.

This allows ARIADNE to answer separately:

1. **Why did we look here?** — discovery guidance.
2. **Why do we believe this?** — verified evidence.

## Independence rule

Two E1 records do not automatically become E2.

ARIADNE must check whether they share:

- the same source;
- the same manuscript witness;
- the same translation;
- the same modern author;
- the same upstream tradition;
- a direct citation/dependency relationship;
- a common machine-generated parent.

Downstream restatements never count as independent convergence.

## Default handling of the AYLI → ARIADNE timeline

`seed/AYLI_to_ARIADNE_Research_Timeline_v0.1.md` is permanently classified:

```yaml
epistemic_zone: G0
epistemic_class: DISCOVERY_GUIDANCE
evidence_eligible: false
claim_support_weight: 0
corroboration_eligible: false
citation_as_evidence: false
derivative_inherits_zone: true
```

Its contents may seed torches, questions, candidate relationships, source searches, and falsification tests.

They must not be counted as historical/scientific/textual evidence for the objects of the research.

## Non-negotiable invariants

1. **G0 cannot support a research-object claim.**
2. **G0 derivatives inherit G0.**
3. **E0 cannot support a research-object claim.**
4. **E1 must point to the independently acquired source and exact verification event.**
5. **E2 requires dependency/independence analysis.**
6. **No internal repetition creates corroboration.**
7. **Search priority and evidentiary confidence remain separate.**
8. **Research-history admissibility never leaks into historical/scientific admissibility.**
9. **Promotion creates a new record; it never rewrites provenance.**
10. **If ARIADNE cannot determine a source's epistemic zone, it defaults to E0 or G0—not E1.**
