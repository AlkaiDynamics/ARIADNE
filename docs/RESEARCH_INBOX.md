# Research inbox: small interface, persistent work

## Everyday use

Run the following command, then open http://127.0.0.1:8765.

~~~bash
python warden.py serve
~~~

Windows users can run OPEN_ARIADNE.bat. These commands require the
codex/algorithm-warden branch until its draft PR is merged.

Do your research in whichever browser tools you prefer. Then:

- Drop downloaded PDFs, text, Markdown, CSV, JSON, or HTML into ARIADNE.
- Paste a mixed resource list containing HTTP(S) links, DOI identifiers, and
  explicit arXiv identifiers; select **Fetch resources**.
- Drop a text/Markdown bibliography or an exported browser-bookmarks HTML file.
  Explicit pointers are queued automatically; originals are preserved.
- Drag a browser link onto the drop area to put it in the resource box, then
  select **Fetch resources**.

The page shows queued links, sources saved, sources indexed, and current candidate
findings. Acquisition totals and graph-linked resource totals appear underneath.
**Needs attention** shows blocked/exhausted links, extraction gaps, and recent
retry reasons. **Recent sources** shows the last eight saved originals.
**View findings** opens the existing detailed report.

There are no graph-editing chores or model controls on the inbox page.
Closing the browser tab leaves the local worker running. Stopping the process
pauses work; restarting resumes persisted jobs. Startup templates in ops/
remain optional and must be installed on the user's computer.

## Flow

~~~mermaid
flowchart TD
    A["Drop files or resource lists"] --> C["Preserve originals"]
    B["Paste links"] --> D["Queue acquisition"]
    C --> E["Extract explicit pointers"]
    E --> D
    D --> F{"Public resource available?"}
    F -->|Yes| C
    F -->|No| G["Keep reason and retry state"]
    C --> H["Extract and index"]
    H --> I["Create candidate graph connections"]
    I --> J["Version state and update progress"]
    G --> J
    J --> K["Wait for new material or due work"]
    K --> D
~~~

This diagram includes bounded pointer discovery; it does not imply unrestricted
crawling. Existing retry and depth limits remain in effect.

## What the numbers mean

| Display | Meaning |
|---|---|
| Queued links | QUEUED jobs plus failed jobs with retry attempts remaining |
| Sources saved | Unique originals in custody, including binary files and guidance |
| Sources indexed | Sources with at least one indexed passage |
| Candidate findings | Current E0 machine detections; excludes G0 guidance |
| Links acquired | Jobs whose originals reached custody, including extraction gaps |
| Links linked | Jobs compiled to LINKED; does not imply verified claims |
| Needs attention | Problem link counts and extraction-gap source counts, shown separately |
| Saved state | Latest managed-row revision in the ledger |

No indicator claims a percentage of all possible research. Link counts can grow
as new pointers are discovered. A source may have multiple incoming links.
Saved, indexed, and verified are different states. A source can be indexed
without producing any typed finding. The status endpoint is a read-only
projection and does not generate a new history version merely because it is polled.

## Limits that affect feeding

- 25 MiB per file/download.
- Text PDFs need installed Poppler pdftotext; scans need a future OCR adapter.
  Unsupported originals remain preserved and visible as extraction gaps.
- A bare book title or ISBN stays in the preserved manifest; it is not silently
  resolved to an invented resource.
- Public HTTP(S) acquisition uses existing robots checks, redirects, backoff,
  and depth limits. Login walls and paywalls are retained as outcomes.
- Bibliography links are pointers, not automatically verified citation relations.
- Browser research sessions do not automatically synchronize with ARIADNE.
  Drop/export/paste is the current handoff.
- No agents, model inference, API keys, or neural packages are used.

## Decision: musical equation and TOL as an optional grammar

The supplied scalar operations are R(x)=2x/3 and L(x)=3x/4. They commute:
R(L(x))=L(R(x))=x/2. This makes an exact operator-algebra test possible.

However, iterating these two maps alone on a bounded scalar starting set has
the trivial limiting attractor {0}: after n operations the absolute magnitude
is at most (3/4)^n times its initial bound. For nonzero x and fixed depth n,
the endpoints are x(2/3)^a(3/4)^(n-a), a=0,...,n. Thus there are n+1 distinct
values but 2^n path histories. Multiplicity is not independent corroboration.

An exact rational enumeration performed during this change gave:

| Depth | Path histories | Distinct values |
|---|---:|---:|
| 1 | 2 | 2 |
| 2 | 4 | 3 |
| 4 | 16 | 5 |
| 8 | 256 | 9 |

These are arithmetic results, not measurements of research quality or
multifractality. The regression suite includes a reproducible depth-eight
enumeration.

A meaningful extension can treat the equation as a **graph rewrite grammar**:
expand into typed R/L branches, retain both orders of operations, compare
observable outputs, preserve residual differences, and create the next
generation without erasing either derivation. TOL could provide a configurable
typed topology for this grammar. Its specific node/edge map still needs an
explicit research specification; none is invented here.

For a research implementation, "expand" and "challenge" are operations on
evidence states, not scalar multiplication. Their commutation must be tested,
not assumed from the musical arithmetic. A geometrical fractal would additionally
require an explicit space, metric, maps/embedding, and scaling interpretation.
Adding translations or normalization changes the mathematical model and must
be recorded as such.

The proposal preserves three separate roles:

| Component | Role | Current status |
|---|---|---|
| Neurite-inspired multiscale module | Detect repeated typed structures and neighborhoods | Implemented exploratory detector |
| Musical/TOL grammar | Generate and compare recursive operator paths | Proposed experiment |
| Template search | Compare depth, width, and operation order at equal budgets | Proposed experiment |
| SBEB | Measure scale-dependent edge organization in chosen graph projections | Not implemented |

The [linked arXiv v4 paper](https://arxiv.org/html/2511.07329v4) evaluates
template-generated CNN architectures on CIFAR-10. Its generator/template/runner
separation inspires a benchmark design; it does not establish improved
historical reasoning. The supplied earlier attachment's DeepSeek-7B claim was
not found in the retrieved v4 HTML, and no neural runtime is added.

[SBEB, Zhao, Liu and Zhou (2023)](https://doi.org/10.1016/j.chaos.2023.113719)
is a separate multifractal-analysis method. Its bibliographic identity and
abstract-level description were located; full method access was unavailable
in this session. A faithful implementation needs the full algorithm and its
ordering/scaling conventions. No improvised estimator is labeled SBEB here.

Before either proposal affects research ranking:

1. Separate source-evidence, guidance, and execution-trace graph projections.
2. Compare ordinary branching, musical grammar, generic typed roles, and explicit
   TOL roles at equal search and CPU budgets.
3. Measure verified retrieval, residual preservation, false links, duplicates,
   and work consumed. Keep topology metrics separate from quality metrics.
4. Test node relabelings, degree-preserving nulls, and graphs generated by the
   same pipeline with shuffled research inputs.
5. Record snapshot hash, projection, grammar version, seeds, scale range,
   estimator configuration, and uncertainty. Insufficient scale range yields
   UNKNOWN, not a forced fractal claim.
6. Keep the core acquisition loop unchanged if the extra method adds no useful
   discrimination.

Any later SBEB work should run on immutable snapshots as a bounded background
analysis, rather than on every upload. The small dashboard need not expose these
experimental controls.

## Validation scope

Seven inbox regressions cover repeated manifests, HTML bookmark pointers, DOI
punctuation, progress-state distinctions, read-only status, binary preservation,
a fixture acquisition-to-graph path, and dashboard JavaScript syntax. An eighth
regression independently checks musical path/value multiplicities.
The original regression suite remains in place. Acquisition tests use injected
HTTP fixtures and do not establish access to arbitrary live sites.

This change was authored through GitHub while the local execution environment
was unavailable. CI results belong to the commit/workflow record; local visual
preview and real-browser interactions were not executed in this session.
