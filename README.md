# ARIADNE

**Auditable Relational Intelligence for Assertions, Discovery, Navigation & Evidence**

ARIADNE is a feed-first research engine for preserving evidence, competing interpretations, discrepancies, residuals, and research return paths while automatically generating traceable correspondence views and a ranked **Where To Look Next** queue.

## Accessibility contract

ARIADNE is designed so the operator does **not** need to build graph nodes, write database queries, or remember unresolved research branches.

The intended interaction is:

1. Put material in `inbox/`.
2. Run `python ariadne.py ingest` (or double-click `RUN_ARIADNE.bat` on Windows).
3. Open `artifacts/latest_report.html`.

Everything else is internal machinery.

## v0 guarantees

- Source custody before interpretation.
- Stable IDs for sources, assertions, discrepancies, transforms, predictions, and torches.
- Competing claims are retained rather than silently collapsed.
- Blanks are unknown, not false.
- Machine-generated connections remain `MACHINE_PREDICTION` until independently supported.
- Residuals and outliers remain first-class records.
- The system keeps a Torch Ledger and can flag old questions affected by new material.
- Generated matrices are views over evidence, not manually maintained truth tables.
- Every report can trace back to source records and ingest events.

## Current architecture

```text
FEED
  ↓
SOURCE CUSTODY
  ↓
ASSERTION / SIGNAL EXTRACTION
  ↓
EVENT LEDGER
  ↓
COMPILER PASSES
  ↓
DISCREPANCIES / TRANSFORMS / TORCHES / MATRICES
  ↓
WHERE TO LOOK NEXT
```

The canonical store is a single SQLite database at `db/ariadne.sqlite`.

## Quick start

### Windows

Double-click:

```text
SETUP_ARIADNE.bat
```

Then drop files into `inbox/` and double-click:

```text
RUN_ARIADNE.bat
```

### Command line

```bash
python ariadne.py init
python ariadne.py ingest
python ariadne.py report
```

## Supported v0 input

- `.txt`
- `.md`
- `.json`
- `.csv`
- `.html` / `.htm`

PDF/image extraction is deliberately deferred to an adapter so v0 remains installable and inspectable with the Python standard library only. The original files are still registered in custody even when their text cannot yet be extracted.

## What v0 does automatically

- Hashes and registers every source.
- Preserves source metadata and ingest history.
- Extracts lightweight candidate signals: counts, obvious `A vs B` discrepancies, transform-shaped expressions such as `TIME -> NUMBER`, research flags, and candidate residuals.
- Records automated signals as **candidates**, not truths.
- Rechecks active/banked torches against new source text.
- Produces an HTML stock-take with source custody, discrepancies, transforms, residuals, torch hits, and a deterministic investigation queue.

This v0 is intentionally conservative. It creates the durable substrate first. LLM-assisted extraction, phonology/morphology passes, lineage typing, TOL blind comparison, structural graph analytics, and external viewers can be added as adapters without replacing the ledger.

## Provenance classes

ARIADNE reserves these evidence states:

```text
SOURCE_EXPLICIT
TEXTUAL_VARIANT
SCHOLARLY_INTERPRETATION
HISTORICAL_LINK
USER_HYPOTHESIS
MACHINE_PREDICTION
STRUCTURAL_ALIGNMENT
TOL_PREDICTION
CHECKSUM_PREDICTION
FAILED_CONTROL
UNKNOWN
```

## Research navigation

For important anomalies, ARIADNE's investigation pass follows four directions:

```text
DOWN       local/source detail
SIDEWAYS   same class in other traditions
ORTHOGONAL different class at the same structural address
UP         re-evaluate the global model and old torches
```

The v0 schema and queue are already shaped so those passes can be expanded without replacing the ledger.

## Status

**v0 bootstrap** — source custody, ledger, torch matching, discrepancy/transform candidate extraction, generated report, and investigation queue.
