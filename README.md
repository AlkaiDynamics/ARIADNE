# ARIADNE

**Auditable Relational Intelligence for Assertions, Discovery, Navigation & Evidence**

ARIADNE is a feed-first research engine for preserving evidence, competing interpretations, discrepancies, residuals, and research return paths while automatically generating traceable correspondence views and a ranked **Where To Look Next** queue.

## Accessibility contract

ARIADNE is designed so the operator does **not** need to build graph nodes, write database queries, or remember unresolved research branches.

The everyday interaction is:

1. Start `python warden.py serve` (or double-click `OPEN_ARIADNE.bat` on Windows).
2. Open http://127.0.0.1:8765 and drop files or paste a resource list.
3. Watch progress; open **View findings** when you want the evidence details.

The browser page stays small. The local worker handles custody, acquisition,
indexing, candidate graph connections, and version history. Closing the tab does
not stop the worker; keep the process and computer running.

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

## Algorithm Warden

The repository now includes an algorithm-only Warden, a local feed interface,
continuous acquisition/discovery, and versioned epistemic state. No model, agent,
API key, database server, or paid inference service is required.

```bash
python warden.py serve
```

Open **http://127.0.0.1:8765**. Drop files or paste URLs, DOIs, arXiv IDs, or a
whole source list. The local worker acquires public sources, preserves originals,
indexes text, detects typed structures, challenges proposed links, and maintains
the research queue. On Windows, `OPEN_ARIADNE.bat` starts this interface.

Headless continuous operation:

```bash
python warden.py watch
```

`WATCH_ARIADNE.bat` provides the Windows equivalent. Startup/restart templates are
in `ops/`; they are not installed automatically. The computer must remain running.
The worker waits when idle and resumes persisted jobs on restart.

The [small-dashboard guide](docs/RESEARCH_INBOX.md) explains browser collection,
progress counts, supported inputs, and the separate musical/TOL experiment.

The [pipeline design](docs/PIPELINE_DESIGN.md) contains the six-stack comparison,
prison flowchart, algorithm placement, Neurite investigation, extension register,
and limitations. [Simulation results](docs/validation/SIMULATION.md) distinguish
measured component behavior from reasoned predictions.

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

PDF text extraction uses `pdftotext` if Poppler is already installed. Without it,
PDFs remain in custody with an extraction gap. Scanned PDFs/images need an OCR
adapter; binary originals are preserved even when text cannot be extracted.
The Python runtime itself remains standard-library only. Python 3.10+ and SQLite
with FTS5/JSON support are required. No package installation is needed.

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

## Commands and recovery

```bash
python warden.py run                       # ingest inbox, acquire, explore, report, snapshot
python warden.py run file.txt --budget 20   # bounded processing batch
python warden.py acquire sources.txt       # queue a messy URL/DOI manifest
python warden.py search "70 languages"      # local hybrid retrieval
python warden.py trace F-...                # typed evidence/return paths
python warden.py report
python warden.py verify                    # custody, event/history chains, SQLite, FKs
python warden.py snapshot
python warden.py history --at 100           # reconstruct logical table state
python warden.py recover artifacts/snapshots/state-....sqlite recovered.sqlite
python -m unittest discover -s tests -v
python tests/simulate.py
```

Recovery always creates a new database; it refuses to overwrite existing state.
Back up `custody/`, `db/`, `config/`, and `artifacts/snapshots/` together. SQLite
snapshots contain the ledger, history and stored implementation source, but the
original corpus bytes remain in `custody/`.

Every managed database row transition is versioned. Current and superseded parser
outputs remain distinguishable. History verification/replay and recovery are
tested; this is not a guarantee of infallible historical interpretation.

## Guidance and evidence firewall

Recognized conversation exports and checkpoints enter **G0 guidance**. Their
questions can generate searches, but they are excluded from evidence matching and
support relationships. Other inputs enter **E0 candidate sources**. The runtime
does not automatically confer E1 verification or E2 corroboration.

The local server accepts `POST /api/messages` with `message_id`, `stream`, and
`content`, using the current local session's `X-ARIADNE-Token`. Each 20 distinct
messages in a stream creates an idempotent G0 checkpoint. A sender must be
connected; this repository cannot automatically receive messages from ChatGPT.

## Structured inputs and tuning

Ordinary text requires no manual classification. Optional `ariadne_schema: 1`
JSON records allow precise supplied metadata and partition/claim fields; see
`examples/`. Examples are synthetic controls, not research evidence. Claims must
declare `exclusive: true` to create a conditional exclusive-predicate conflict;
otherwise different values remain variants.

`config/pipeline.json` controls query budgets, candidate/display limits, depth,
priority weights, aliases and protected torches. Limits constrain active work,
not permanent retention. `artifacts/latest_report.html` shows K and N explicitly,
with full exports and all breadcrumbs. `artifacts/neurite_notes.md` can be pasted
into Neurite's default Zettelkasten format.

## Optional attention lenses

Musical/TOL and fractal patterns are provisional ways to choose where to look.
They are not global truth gates. The local scalar arithmetic check does not
validate or invalidate the full research framework.

The installed Neurite-inspired pass can be disabled with
`"multiscale_enabled": false` in `config/pipeline.json`. Lens runs are immutable,
versioned records; a failed pass rolls back its partial output while ordinary
acquisition, findings, and connection checks continue. Past results remain
available. Musical/TOL and SBEB execution remain future adapters.

See [published progress](docs/PROGRESS.md) for implementation and validation scope.

## Boundaries of this build

- Current retrieval is local to acquired/ingested material. Public URL acquisition
  expands explicit pointers with robots checks, retry states and a depth bound.
- DOI resolution can stop at a landing page/paywall; GitHub pointers expand to
  metadata, README and tree resources. No authenticated acquisition, ISBN resolver,
  OCR, browser extension, or repository execution is claimed.
- Typed extraction recognizes explicit patterns; it cannot invent morphology,
  decode unknown languages, or certify historical source independence.
- Controls without an adequate test remain UNKNOWN. All machine links remain
  MACHINE_PREDICTION, including multiscale/Neurite-inspired recurrence.
- Snapshot storage, pair matching and Pareto sorting need profiling before large
  deployments. No billion-token or zero-resource-cost guarantee is made.
