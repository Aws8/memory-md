"""mem — the memory-md CLI.

    mem lint [path]          validate a memory repo against the spec
    mem graph [path]         render the [[link]] graph (mermaid|dot|json|list)
    mem stats [path]         counts, coverage, most-linked files
    mem dream [path]         dry-run Dreaming: duplicates, stale, contradictions
    mem init DIR --name N    scaffold a spec-compliant memory repo
    mem add FILE "text"      append a properly formatted entry
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .commands import add_entry, ensure_indexed, init_repo, stats
from .dream import dream
from .graph import RENDERERS
from .lint import ERROR, INFO, WARNING, lint, summarize
from .repo import find_repo


def _print_findings(findings, severities) -> None:
    order = {ERROR: 0, WARNING: 1, INFO: 2}
    for f in sorted(findings, key=lambda x: (order.get(x.severity, 9), str(x.file), x.line or 0)):
        if f.severity in severities:
            print(f.render())


def cmd_lint(args) -> int:
    repo = find_repo(Path(args.path))
    findings = lint(repo, max_memory_lines=args.max_memory_lines)
    sev = {ERROR, WARNING} if not args.verbose else {ERROR, WARNING, INFO}
    _print_findings(findings, sev)
    s = summarize(findings)
    print(f"\n{s[ERROR]} error(s), {s[WARNING]} warning(s), {s[INFO]} info")
    return 1 if s[ERROR] or (s[WARNING] and args.strict) else 0


def cmd_graph(args) -> int:
    repo = find_repo(Path(args.path))
    print(RENDERERS[args.format](repo))
    return 0


def cmd_stats(args) -> int:
    repo = find_repo(Path(args.path))
    print(stats(repo))
    return 0


def cmd_dream(args) -> int:
    repo = find_repo(Path(args.path))
    suggestions = dream(repo, stale_days=args.stale_days, dup_ratio=args.dup_ratio)
    if not suggestions:
        print("nothing to clean up — memory looks fresh")
        return 0
    for s in suggestions:
        print(s.render())
    print(f"\n{len(suggestions)} suggestion(s). Advisory only — nothing was changed.")
    return 0


def cmd_init(args) -> int:
    try:
        actions = init_repo(Path(args.dir), args.name, git=not args.no_git)
    except FileExistsError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    for a in actions:
        print(a)
    print(f"\nmemory repo ready at {Path(args.dir).resolve()}")
    return 0


def cmd_add(args) -> int:
    repo = find_repo(Path(args.path))
    try:
        rel = add_entry(repo.root, Path(args.file), args.text, source=args.source)
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    print(f"added to {rel.as_posix()}")
    if args.index:
        print("indexed in MEMORY.md" if ensure_indexed(repo.root, rel) else "already indexed")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="mem",
        description="Toolkit for Agent Memory Repo — lint, graph and dry-run Dreaming "
        "for the open agent-memory standard (cognition.com/agent-memory-repo).",
    )
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = p.add_subparsers(dest="command", required=True)

    def common(sp):
        sp.add_argument("path", nargs="?", default=".", help="memory repo dir (default: .)")

    sp = sub.add_parser("lint", help="validate a repo against the spec")
    common(sp)
    sp.add_argument("-v", "--verbose", action="store_true", help="also show info findings")
    sp.add_argument("--strict", action="store_true", help="exit 1 on warnings too")
    sp.add_argument("--max-memory-lines", type=int, default=100)
    sp.set_defaults(func=cmd_lint)

    sp = sub.add_parser("graph", help="render the [[link]] graph")
    common(sp)
    sp.add_argument("-f", "--format", choices=sorted(RENDERERS), default="mermaid")
    sp.set_defaults(func=cmd_graph)

    sp = sub.add_parser("stats", help="counts and coverage")
    common(sp)
    sp.set_defaults(func=cmd_stats)

    sp = sub.add_parser("dream", help="dry-run Dreaming cleanup suggestions")
    common(sp)
    sp.add_argument("--stale-days", type=int, default=90)
    sp.add_argument("--dup-ratio", type=float, default=0.82)
    sp.set_defaults(func=cmd_dream)

    sp = sub.add_parser("init", help="scaffold a compliant memory repo")
    sp.add_argument("dir", help="directory to create")
    sp.add_argument("--name", required=True, help="memory owner name, e.g. Aws")
    sp.add_argument("--no-git", action="store_true", help="skip git init")
    sp.set_defaults(func=cmd_init)

    sp = sub.add_parser("add", help="append a formatted entry to a note")
    sp.add_argument("file", help="note path inside the repo, e.g. projects/payments")
    sp.add_argument("text", help="entry text")
    sp.add_argument("--source", help="source URL (session link)")
    sp.add_argument("--index", action="store_true", help="also add to MEMORY.md index")
    sp.add_argument("path", nargs="?", default=".", help=argparse.SUPPRESS)
    sp.set_defaults(func=cmd_add)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
