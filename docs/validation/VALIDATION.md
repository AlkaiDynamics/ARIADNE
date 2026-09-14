# Validation record

Validation uses synthetic controls and isolated temporary databases. No real
historical claim is certified by these checks.

## Commands

```bash
python -m unittest discover -s tests -v
python tests/simulate.py
python -m compileall -q ariadne.py warden.py ariadne_core
python warden.py run examples/partition-a.json examples/partition-b.json --budget 8
python warden.py verify
```

The 42-test regression suite passes. It covers:

- immutable source custody, changed-inbox replay, checksum failure and duplicate ingestion;
- additive migration of v0 evidence;
- distinct partition/factor operators at the same numerical address;
- unknown residual functions, scoped variants, conditional nogoods and no machine promotion;
- shared-source-family controls and unrun controls staying unknown;
- four directional queries, protected torches, local-loop stopping, budget retention and reopening;
- Unicode normalization, word boundaries, fuzzy transposition and SQL metacharacters;
- retrieval bounds without false saturation claims;
- row-history/event integrity, exact logical replay, transactional rollback and snapshot recovery;
- superseded extraction versions excluded from current evidence;
- G0 excluded from evidence support, idempotent 20-message checkpoints;
- acquisition custody, recursive pointers, failure residuals and private-network rejection;
- continuous watch cycles, a second writer rejected by the OS lock;
- multiscale membership preservation and escaped report markup.

Cross-platform CI initially exposed an open SQLite backup handle that prevented
renaming a snapshot on Windows. Snapshot/recovery connections now close explicitly
before rename or return. The continuous-worker test also fails on ERROR_RETRY,
rather than accepting a query run when snapshot creation failed.

The local HTTP interface was exercised through a spawned server process: feed
page, operational status, generated report, unauthenticated-write rejection and
graceful SIGTERM shutdown. External acquisition behavior is covered with injected
HTTP fixtures. A live GitHub raw-source fetch was attempted and failed at DNS
resolution in this execution environment (`Temporary failure in name resolution`).
Live acquisition therefore remains unverified here; publisher access policies also
vary. Windows startup/locking and user-systemd activation need validation on
the target machine; startup templates were not installed here.

## What the simulation measures

See [SIMULATION.md](SIMULATION.md) and [simulation.json](simulation.json).
The six executable ablations compare implemented retrieval-channel combinations
and structural/arithmetic screening on a controlled corpus. They do not pretend
to benchmark full e-graph, MCTS, BALD, ILP, topology or knowledge-compilation stacks.

All valid fixture matches were retained by both guarded configurations. The
unfiltered retrieval configurations returned additional wrong-type/invalid
candidates. This supports placing guards after broad retrieval in this fixture;
it does not establish universal accuracy or superiority of hybrid retrieval.
