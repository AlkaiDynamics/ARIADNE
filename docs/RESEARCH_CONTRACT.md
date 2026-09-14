# ARIADNE Research Contract

These are architectural rules, not optional UI preferences.

## 1. Preserve disagreement

A discrepancy is never represented only by its preferred reading. Competing readings remain separately addressable and retain their own source, date, interpretation, and downstream consequences.

## 2. Separate the layers

Where applicable, keep these distinct:

```text
EVENT
UTTERANCE / SYMBOLIC CARRIER
DECODER / READING RULE
ABSTRACTION CLASS
SYSTEM CONSEQUENCE
```

Changing a decoder does not silently change the underlying event.

## 3. Sound is a first-class variable

Preserve, when evidence permits:

```text
script / graphemes
pronunciation / phonology
morphology
literal translation
contextual translation
abstraction class
system behavior
historical witness
```

Never invent morphology merely because a string can be visually subdivided.

## 4. Residuals are data

Missing, extra, withheld, duplicated, unpaired, untranslated, failed, and unknown units remain first-class records. Storage for outliers is not capped by the shape of a correspondence matrix.

## 5. Blank is not false

An empty cell means unresolved / not represented in the current view unless evidence explicitly establishes absence.

## 6. Equal counts do not imply equal operators

`36→72`, `12×6→72`, `36+36→72`, `70+2→72`, and any other numerically equal constructions remain distinct transforms unless evidence supports equivalence.

## 7. Downstream checksums are not independent convergence

Later angel/demon/decan/zodiac/TOL or other completed grids can provide search priors and functional profiles. They do not become independent ancient evidence merely because they fit.

## 8. Evidence support and diagnostic value are independent

A clue may have low epistemic support but extreme diagnostic value. Low support must never make a clue invisible; it changes its evidence status, not its right to be investigated.

## 9. Machine predictions are quarantined

Automated extractions and generated links default to `MACHINE_PREDICTION` unless a stronger provenance class is explicitly assigned from evidence.

## 10. TOL is a blind discriminator

When competing readings are tested against TOL, both are mapped independently. ARIADNE must not assume whether TOL preserves the better reading or the inherited distortion.

## 11. Lineage is typed

At minimum distinguish:

```text
BIOLOGICAL
TRIBAL
LEGAL
PRIESTLY
SUCCESSION
TEACHER
TEXTUAL
SYMBOLIC
RECEPTION
ADOPTIVE / INCORPORATIVE
```

## 12. Research navigation is recursive

For a consequential anomaly, preserve four search directions:

```text
DOWN       inspect local/source detail
SIDEWAYS   inspect the same class elsewhere
ORTHOGONAL inspect a different class at the same structural address
UP         reassess global architecture and old torches
```

No rabbit hole without breadcrumbs. No global leap without a return address.

## 13. Torches are never silently forgotten

A major thread is either:

```text
BURNING
BANKED
REIGNITED
```

A banked torch carries a reason, dependencies, and a return trigger.

## 14. Theory is disposable; custody is not

Original sources, source hashes, evidence locations, extraction outputs, event history, and explicit human decisions outrank every generated model or matrix. Current theory can be rebuilt; source custody must remain stable.

## 15. Accessibility is part of correctness

ARIADNE fails if its research state depends on the operator remembering branch names, manually reconstructing context, building graph nodes, or learning database/query tooling. The intended user interaction remains:

```text
FEED MATERIAL
LOOK AT FINDINGS
TRACE WHY (when desired)
```

## 16. Content identity, claim identity, and evidential authority are separate

This is a permanent architectural invariant:

```text
CONTENT IDENTITY != CLAIM IDENTITY != EVIDENTIAL AUTHORITY
```

A content hash answers whether the same bytes or normalized object are already stored. A claim identity answers whether two records concern the same proposition, occurrence, reading, transform, or assertion. Evidential authority answers what a source may actually support, under which scope, provenance, and dependency conditions.

No one of these may stand in for another. Duplicate content does not create a duplicate claim. A matching claim does not imply equal authority. A highly authoritative source for one scope may be inadmissible for another.

## 17. Epistemic guidance is firewalled from evidence

Research-history timelines, chats, design rationale, hypothesis histories, working correspondence tables, machine predictions, structural alignments, TOL predictions, checksum predictions, and field-census metadata are discovery guidance unless independently verified for the claim scope at issue.

The governing path is:

```text
G0 DISCOVERY_GUIDANCE
  -> QUESTION
  -> SEARCH
  -> E0 CANDIDATE SOURCE
  -> VERIFICATION
  -> E1 VERIFIED ADMISSIBLE EVIDENCE
  -> DEPENDENCY / INDEPENDENCE ANALYSIS
  -> E2 INDEPENDENTLY CORROBORATED EVIDENCE
```

A derivative of G0 remains G0. Internal repetition, summarization, extraction, graphing, or matrix generation cannot launder guidance into evidence or create independent corroboration.

Guidance may change **where ARIADNE looks next**. It may not increase evidentiary confidence in the answer it expects to find.

Promotion is never mutation: a G0 record remains G0 forever. Independently acquired and verified evidence is represented as a new E1/E2 record linked back through discovery provenance.

See `docs/EPISTEMIC_FIREWALL.md` and `config/epistemic_policy.json`.

## 18. Conversation progress is checkpointed every ten exchanges

Global project rule `GPR-001` applies across The Great Work and its connected branches.

After every:

```text
10 user inputs
+
10 assistant outputs
=
20 conversation-visible messages
```

all project progress since the prior checkpoint must be pushed into ARIADNE as a G0 continuity artifact.

The operator is not responsible for remembering, summarizing, classifying, or pushing the checkpoint. This is an assistant/system responsibility.

A checkpoint must preserve new discoveries, source acquisitions, hypothesis changes, corrections, decisions, rules, transforms, torch changes, bright-red items, failures, residuals, repo/artifact changes, recontextualized old threads, unresolved questions, return triggers, and forward/recursive paths.

Tool calls and hidden/system messages do not count toward the cadence. If exact counting becomes uncertain, checkpoint early rather than late.

Checkpoint files live under `checkpoints/YYYY-MM-DD/` and remain permanently `G0 — DISCOVERY_GUIDANCE`.

See `docs/GLOBAL_PROJECT_RULES.md`, `config/project_rules.json`, and `checkpoints/README.md`.

## 19. Research the research before original deep-source synthesis

Global project rule `GPR-003` is mandatory for every new major research question.

ARIADNE first asks who has already pursued the idea, what fields and terminology contain it, what reviews and bibliographies map it, what canonical authors and sources recur, what competing explanations and failed approaches exist, and what unresolved boundary remains.

The default order is:

```text
QUESTION
-> FIELD CENSUS
-> PRIOR ART
-> VOCABULARY
-> KNOWN RESULTS / KNOWN FAILURES
-> SOURCE MAP
-> ORIGINAL INVESTIGATION
-> CONTRIBUTION DELTA
```

Original deep-source synthesis begins only after either a reasonable field map is established or a documented bounded search reaches saturation without applicable prior art.

Bibliographic index results are G0 discovery metadata. A scholar's paper may be primary evidence that the scholar proposed a theory; it is not automatically primary evidence that the historical subject discussed in that paper intended the same theory.

A failed search is retained as a negative search record. It is never upgraded directly into a novelty claim.

Operating rule:

```text
Never rediscover manually what a field has already spent centuries organizing.
```

Use original effort where the field ends, disagrees, fragments, fails, or never connected the relevant pieces.
