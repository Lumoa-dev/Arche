# Project Standards

Project-wide conventions and policies that ensure consistency across Arche development.

## Issue Label System

Labels use a `type:*` / `area:*` / `priority:*` prefix scheme:

| Category | Examples |
|----------|----------|
| `type:*` | `type: bug`, `type: feature`, `type: refactor`, `type: ui`, `type: chore`, `type: docs` |
| `area:*` | `area: core`, `area: auth`, `area: blog`, `area: admin`, `area: frontend`, `area: ci` |
| `priority:*` | `priority: high`, `priority: medium`, `priority: low` |

Labels are defined in `.github/labels.json` and synced via `.github/workflows/label-sync.yml` — the JSON file is the single source of truth.

### Policy

- Use `type:*` prefixes to avoid conflicts with GitHub's default labels (`bug`, `enhancement`, etc.)
- Do not create ad-hoc labels outside `labels.json`
- The sync workflow creates/updates from `labels.json` but does **not** auto-delete unused ones (safety measure)

## Epic Format

### Title

```
[Epic] <Category Name>
```

No emoji. No decorative prefixes.

### Body

Pure markdown — no emoji, no decorative elements. Use a hierarchical checklist:

```markdown
## Goals

- Concise description of what this Epic achieves

## Checklist

- [ ] Task 1 (#issue-number)
- [ ] Task 2 (#issue-number)
```

## Issue Template Policy

Four templates cover all scenarios:

| Template | When to Use |
|----------|------------|
| Bug | Defect report — unexpected behavior, crash, visual glitch |
| Feature | New capability — new API, new component, new plugin |
| Task | Everything else — refactor, chore, docs, UI tweaks, dependency update |
| Epic | Meta-issue grouping multiple sub-issues |

Do not create per-label templates (e.g., no separate "UI Bug" or "Refactor Task" templates). Templates solve **how to write** — labels solve **what it is**.

## Label Sync Policy

The `label-sync.yml` workflow:

- **Creates** labels defined in `labels.json` if missing
- **Updates** labels whose description or color differ from `labels.json`
- **Does NOT delete** labels not in `labels.json`

Rationale: Deletion is destructive and could affect historical issues. Manual review is preferred when pruning unused labels.

## PR Template Policy

Use a single PR template. GitHub supports multiple templates (via `PULL_REQUEST_TEMPLATE/` directory), but Arche doesn't need it — different PR types (fix, feature, release) share enough structure that one template plus labels is sufficient.
