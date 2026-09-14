# ARIADNE Conversation Checkpoints

This directory stores the rolling continuity checkpoints required by `GPR-001`.

Every **10 completed exchanges** — 10 user inputs + 10 assistant outputs = 20 conversation-visible messages — the assistant pushes a checkpoint containing all project progress since the previous checkpoint.

These files are **G0 — DISCOVERY_GUIDANCE**. They preserve research history and navigation state. They are not evidence for the underlying research-object claims and cannot count as independent corroboration.

## Naming

```text
checkpoints/YYYY-MM-DD/CP-YYYYMMDD-NNNN.md
```

Each checkpoint identifies its predecessor and the conversation window it covers as precisely as the platform permits.

## Required behavior

- Preserve corrections, failures, residuals, and outliers.
- Record new or changed torches and return triggers.
- Link new findings back to older threads when recontextualized.
- Record repository/artifact changes.
- Record unresolved forward, sideways, orthogonal, and global-return paths.
- Never convert chat repetition into evidentiary multiplicity.

See:

- `docs/GLOBAL_PROJECT_RULES.md`
- `docs/EPISTEMIC_FIREWALL.md`
- `config/project_rules.json`
- `config/epistemic_policy.json`
