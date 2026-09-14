# P0 — Prior-art and field-census gate

ARIADNE now treats **researching the research field** as a prerequisite to ordinary original synthesis for a registered major research question.

## Why this exists

AYLI exposed a basic process failure: ARIADNE could spend substantial effort interpreting old sources and constructing connections before asking whether a mature field, earlier author, review literature, or parallel discipline had already organized the same problem.

P0 reverses that order.

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

## Current executable scope

The algorithm-only Warden can perform the cheap first layer without a model:

1. register a research question and seed terms;
2. search multiple public bibliographic indexes;
3. preserve every query and failed/blocked acquisition outcome;
4. deduplicate candidate works without collapsing provider provenance;
5. extract recurring vocabulary from titles and subject metadata;
6. run a second vocabulary-expanded search round;
7. measure final-round bibliographic novelty as a bounded search diagnostic;
8. surface a diverse prior-art shortlist while retaining the complete candidate set;
9. queue surfaced scholarly works as acquisition leads;
10. keep bibliographic index payloads in `G0 — DISCOVERY_GUIDANCE`.

The default providers are OpenAlex, Crossref, and Open Library. Provider failure is recorded; it is not interpreted as absence of prior art.

## What the gate means

A question begins in:

```text
CENSUS
```

Ordinary `warden.py run` / continuous Warden analysis is held while any registered question remains in that state.

After the configured bounded rounds and minimum provider coverage, the question becomes:

```text
READY
```

or, when the final bounded round adds sufficiently little new bibliographic material:

```text
SATURATED
```

`SATURATED` means only **this configured bibliographic search reached its stopping criterion**. It does not mean the open world is exhausted.

A sparse or empty result is retained explicitly. It does not by itself establish novelty.

## Epistemic boundary

Bibliographic metadata may support claims such as:

```text
INDEX I CONTAINED A RECORD TITLED X
AUTHOR P IS LISTED ON RECORD X
DOI D IS ASSOCIATED WITH RECORD X
```

It does not automatically support:

```text
THE HISTORICAL SUBJECT DISCUSSED BY X INTENDED CLAIM Y
CLAIM Y IS TRUE
X IS INDEPENDENT OF SOURCE Z
```

The permanent invariant is:

```text
CONTENT IDENTITY != CLAIM IDENTITY != EVIDENTIAL AUTHORITY
```

The acquired scholarly work itself enters as a candidate source and still requires scope-specific verification. A paper can be primary evidence that its own author proposed a model while remaining secondary evidence about an earlier historical figure discussed in the paper.

## Important current limitation

The executable P0 pass maps **bibliographic identity, field vocabulary, likely reviews, authors, and source leads**. It does not pretend that title/subject metadata alone yields a trustworthy semantic account of every paper's results, criticisms, or unresolved problems.

Those deeper fields remain `UNKNOWN` until the surfaced literature is actually acquired and examined. P0 exists to make that examination start from the organized field rather than from an arbitrary historical rabbit hole.

## Current seeded question

`config/research_questions.json` contains the current Completed Harmony / MI–FA boundary question concerning local closure or reciprocal return with global register/octave/generation change.

It can be inspected with:

```bash
python warden.py field-map
```

A new major question can be registered with:

```bash
python warden.py question "Who has proposed this structure before?" \
  --scope "short scope statement" \
  --term "known synonym" \
  --term "adjacent-field term"
```

The continuous Warden will then prioritize the census automatically before resuming ordinary synthesis.
