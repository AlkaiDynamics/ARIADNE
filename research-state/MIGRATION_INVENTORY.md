# Initial Great Work Migration Inventory

Base fork state is pinned to upstream commit:

```text
709f8e7d38a98761c6442cce83663ecaa35b3285
```

The GitHub fork already preserved the complete inherited tree at that commit. This file classifies Great Work-specific state that should remain downstream-owned when canonical upstream is later purified.

## Active research state already present

### `config/research_questions.json`

Contains the live Completed Harmony / MI–FA boundary prior-art question. This is a project research instance, not a canonical ARIADNE default.

### `config/torches.json`

Contains live Great Work torches including:

- 70 target languages;
- sorcery targets/operators;
- House of Judah / Aristeas fourth group;
- 36 cells/pairs/nomes/decans;
- Moses–Hermes interpretation layer;
- angel entity/function distinction;
- Seth/Valentinus complementary projections;
- music/harmony reintegration;
- Gnostic transit operators;
- Gog/Magog translation stack;
- quail/salwā stack;
- Rosetta 6×12 architecture.

The generic Torch mechanism belongs upstream. These instances belong downstream.

### `checkpoints/`

Contains Great Work conversation/research continuity artifacts. The checkpoint mechanism belongs upstream; checkpoint contents and cadence policy instance belong downstream.

### `seed/AYLI_to_ARIADNE_Research_Timeline_v0.1.md`

AYLI/Great Work continuity history. Downstream state.

### `docs/GLOBAL_PROJECT_RULES.md`

Currently contains Great Work policy instances and explicitly names connected projects. Generic rule mechanisms/contracts can live upstream; Great Work-specific policy instances belong downstream.

### Domain-specific provenance vocabulary

Current provenance classes include Great Work-specific concepts such as `TOL_PREDICTION` and `CHECKSUM_PREDICTION`. These should be reviewed under the mechanism-vs-policy split rather than silently deleted or generalized.

## Verification status

- GitHub repository is an actual fork of `zhenrez/ARIADNE`.
- Downstream `main` and upstream `main` both pointed to `709f8e7d38a98761c6442cce83663ecaa35b3285` at bootstrap time.
- Downstream connection has admin/maintain/push permission.
- No project-state file has been moved or deleted during bootstrap.
- Runtime-sensitive paths remain unchanged.

## Next migration gates

1. Add generic downstream profile/path resolution before relocating `config/` instances.
2. Add durable ARIADNE epistemic/project `FORK` type distinct from navigation `branches`.
3. Add project/focus-scoped P0 keys and dependency-scoped blocking.
4. Add validation-regime and handoff-envelope primitives.
5. Move Great Work policy/state only after the runtime can consume downstream-owned locations.
6. Verify byte/record equivalence after each move.
7. Purify canonical upstream only after downstream preservation is independently verified.

Nothing in this inventory is evidentiary support for the research claims it mentions. It is migration/continuity metadata.
