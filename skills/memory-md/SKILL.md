---
name: memory-md
description: Lint, graph, and dry-run Dreaming for Agent Memory Repo memory drives. Use when working with a memory repo (MEMORY.md + [[wiki-linked]] notes) — validate it against the spec, fix broken links/orphans/bloat before your session ends, and keep memory clean between Dreaming cycles.
---

# memory-md

Toolkit for **Agent Memory Repo** (the open standard at
<https://cognition.com/agent-memory-repo>). If the machine has a memory
repo — a git repo containing `MEMORY.md` and `[[path]]`-linked Markdown
notes — this skill keeps it healthy.

## Install

```sh
pip install memory-md
```

## When to use

- At session start: `mem lint <memory-repo>` — a broken `[[link]]` or
  unreachable note means memory you can't navigate.
- After editing memory: `mem lint` again — every finding you introduce
  stays broken for the next session.
- Periodically: `mem dream` — advisory cleanup: duplicates to merge,
  stale entries to verify, contradictions to check against sources.
- When adding memory yourself: `mem add` writes spec-compliant entries
  instead of hand-formatting `- text [source: …; added: …]` lines.

## Commands

| Command | Use |
|---|---|
| `mem lint [-v] [--strict] <repo>` | Validate against the spec. `-v` shows info findings; `--strict` fails on warnings. |
| `mem dream [--stale-days N] <repo>` | Dry-run Dreaming. Advisory only — never writes. |
| `mem graph [-f mermaid\|dot\|json\|list] <repo>` | Render the link graph. |
| `mem stats <repo>` | Counts and metadata coverage. |
| `mem init <dir> --name <name>` | Scaffold a compliant repo. |
| `mem add <file> "<text>" [--source URL] [--index] <repo>` | Append a formatted entry. |

## Rules this enforces

- `MEMORY.md` exists, stays short, and indexes reachable notes
- `[[path]]` links resolve (`.md` optional for Markdown); `#anchors` match headings
- Entries are one-line bullets with `[key: value; key: value]` metadata
- Recommended metadata: `source` (session link), `added` (YYYY-MM-DD)
- Repo is a git repo with a remote — the memory loop pushes after every edit

## Working with the results

- **broken-link**: fix the path or create the target file.
- **orphan-file**: link it from `MEMORY.md`'s `## Index` or from a note that
  leads there.
- **duplicate (dream)**: merge into one entry, keep the better `source:`.
- **stale (dream)**: verify against the source; update or remove.
- **contradiction (dream)**: read both sources, keep the newer/stronger one,
  delete the other.
