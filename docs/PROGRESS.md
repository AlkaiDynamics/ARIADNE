# ARIADNE progress — 2026-09-14

This release consolidates the algorithm-only Warden, small research inbox,
continuous acquisition/discovery, and versioned evidence ledger in PR #3.

## Available

- Small browser page: drop raw resources, bookmark exports, or resource lists;
  paste URLs, DOIs, or arXiv IDs. See queued/saved/indexed/finding counts and gaps.
- Persistent, agentless public-resource acquisition with retries and backoff.
- Typed candidate graph connections, hybrid retrieval, four-direction search,
  protected research threads, bounded work, and idle waiting.
- Source custody, competing interpretations, immutable event/row history,
  superseded extraction retention, snapshots, replay, and recovery to a new DB.
- Optional Neurite-inspired multiscale attention pass with a disable setting,
  immutable run records, and transaction-level failure isolation.
- Revised connection-check settings create new assessments while retaining old
  ones. Criteria and implementation identifiers appear in each new assessment.
- Guidance sources remain separate from evidentiary support.

## Research clarification

The musical equation and TOL may be useful as provisional search lenses or as a
recursive grammar. Neither their completeness nor their validation is assumed.
The two-scalar-map check concerns only that chosen mathematical projection;
it has no global veto over the user's framework or unrelated connections.

The FractalNet paper and SBEB are separate candidate techniques. Their apparent
relevance does not establish fit or privilege them over competing algorithms.
No musical/TOL or SBEB runtime has been installed. A future lens must report its
scope, assumptions, input/version lineage, uncertainty, and suggested searches.
Priority is an investigation decision, not a truth judgment.

Optional computation can still consume resources and affect the order of work.
Failure isolation and baseline-preservation regressions do not prove that every
future algorithm will have zero effect on performance or research quality.

## Validation record

The preceding inbox commit, 8e351b8d91eca93858e5961222fe1383fd01505d, passed
50 tests on both Linux and Windows:
[CI run](https://github.com/zhenrez/ARIADNE/actions/runs/34858776384).

This update adds five regressions for:
- lens-on/off preservation of baseline findings, connections, and lexical hits;
- rollback of partial lens output while baseline search continues;
- immutable/idempotent lens records and reconstruction of earlier state;
- changed connection criteria retaining both old and new assessments;
- continuous-worker restart followed by processing new material.

It also strengthens the extraction-gap progress check so diagnostic error
passages do not count as indexed source content. The resulting suite contains
55 tests; the linked PR checks provide the authoritative result for its head:
[PR #3 checks](https://github.com/zhenrez/ARIADNE/pull/3/checks).

Earlier 12-seed simulations compare six implemented retrieval/constraint
ablations, not six fully implemented frameworks. The exact musical enumeration
checks path/value multiplicities, not theory validity or research effectiveness.

## Running

~~~bash
python warden.py serve
~~~

Open http://127.0.0.1:8765, or use OPEN_ARIADNE.bat on Windows.
The computer and worker must stay running; closing the tab is fine.
The process waits when idle and resumes persisted work after restart.
OS startup/restart templates are provided but have not been installed on the
user's computer. Stop/restart the process after upgrading code.

## Remaining limits

Live acquisition tests here use fixtures; access to arbitrary websites is not
guaranteed. PDF text requires Poppler; scans need OCR. Authentication/paywall
adapters are absent. No model, paid inference, or agent service is required.
The latest dashboard was not visually previewed in the unavailable workspace.
Publishing the repository does not install or host a running service.
