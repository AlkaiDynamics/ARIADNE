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
