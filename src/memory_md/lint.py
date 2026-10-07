"""Lint rules for Agent Memory Repo.

Each rule emits Finding objects with a severity:

- ``error``   — breaks the spec (missing MEMORY.md, broken [[links]])
- ``warning`` — hurts agent usability (orphan files, bloated MEMORY.md,
  malformed metadata, duplicate index entries)
- ``info``    — hygiene suggestions (missing ``added``/``source``,
  unpushed commits, no remote)
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from .repo import MemoryRepo

ERROR = "error"
WARNING = "warning"
INFO = "info"

DEFAULT_MAX_MEMORY_LINES = 100


@dataclass(frozen=True)
class Finding:
    rule: str
    severity: str
    message: str
    file: Path | None = None
    line: int | None = None

    def render(self) -> str:
        loc = ""
        if self.file is not None:
            loc = str(self.file.as_posix())
            if self.line is not None:
                loc += f":{self.line}"
            loc += ": "
        return f"[{self.severity}] {loc}{self.rule}: {self.message}"


def _is_date(value: str) -> bool:
    try:
        date.fromisoformat(value.strip())
        return True
    except ValueError:
        return False


def lint(repo: MemoryRepo, max_memory_lines: int = DEFAULT_MAX_MEMORY_LINES) -> list[Finding]:
    findings: list[Finding] = []

    ep = repo.entrypoint
    if ep is None:
        findings.append(
            Finding(
                "no-memory-md",
                ERROR,
                "MEMORY.md missing at repo root — agents have no entry point",
            )
        )
    else:
        if not repo.index_links():
            findings.append(
                Finding(
                    "index-missing",
                    WARNING,
                    "MEMORY.md has no '## Index' section with [[links]] to other files",
                    ep.relpath,
                )
            )
        nonempty = [l for l in ep.text.splitlines() if l.strip()]
        if len(nonempty) > max_memory_lines:
            findings.append(
                Finding(
                    "memory-md-bloat",
                    WARNING,
                    f"MEMORY.md is {len(nonempty)} non-empty lines (max {max_memory_lines}) — "
                    "keep it short; move detail into linked notes",
                    ep.relpath,
                )
            )

    # [[link]] resolution + dead anchors
    broken = 0
    for note in repo.files.values():
        for link in note.links:
            target = repo.resolve(link.path)
            if target is None:
                broken += 1
                findings.append(
                    Finding(
                        "broken-link",
                        ERROR,
                        f"[[{link.raw}]] does not resolve to a file",
                        note.relpath,
                        link.line,
                    )
                )
            elif link.anchor and target.is_markdown:
                if link.anchor.lower() not in target.headings:
                    findings.append(
                        Finding(
                            "dead-anchor",
                            WARNING,
                            f"[[{link.raw}]] resolves but anchor '#{link.anchor}' "
                            "matches no heading in the target file",
                            note.relpath,
                            link.line,
                        )
                    )

    # Orphan files: unreachable from MEMORY.md
    if ep is not None:
        for rel, note in repo.files.items():
            if rel not in repo.reachable():
                findings.append(
                    Finding(
                        "orphan-file",
                        WARNING,
                        "unreachable from MEMORY.md — index it or link it from a note",
                        rel,
                    )
                )

    # Index hygiene
    seen_targets: dict[str, int] = {}
    for link in repo.index_links():
        key = link.path
        if key in seen_targets:
            findings.append(
                Finding(
                    "duplicate-index-entry",
                    WARNING,
                    f"index links [[{link.raw}]] again (first on line {seen_targets[key]})",
                    Path("MEMORY.md"),
                    link.line,
                    )
            )
        else:
            seen_targets[key] = link.line

    # Entry metadata hygiene. A bullet that is only a [[link]] (index lines)
    # is navigation, not a memory entry — it needs no metadata.
    link_only_re = re.compile(r"^\[\[[^\]]+\]\]\s*$")
    for note in repo.files.values():
        if not note.is_markdown:
            continue
        for entry in note.entries:
            if link_only_re.match(entry.text):
                continue
            if not entry.metadata:
                findings.append(
                    Finding(
                        "missing-metadata",
                        INFO,
                        "entry has no [key: value] metadata — recommended keys: source, added",
                        note.relpath,
                        entry.line,
                    )
                )
                continue
            if "added" not in entry.metadata:
                findings.append(
                    Finding(
                        "missing-added",
                        INFO,
                        "no 'added' date — stale entries get hard to spot",
                        note.relpath,
                        entry.line,
                    )
                )
            elif not _is_date(entry.metadata["added"]):
                findings.append(
                    Finding(
                        "bad-added-date",
                        WARNING,
                        f"added: '{entry.metadata['added']}' is not YYYY-MM-DD",
                        note.relpath,
                        entry.line,
                    )
                )
            if "source" not in entry.metadata:
                findings.append(
                    Finding(
                        "missing-source",
                        INFO,
                        "no 'source' link — Dreaming can't check it later",
                        note.relpath,
                        entry.line,
                    )
                )

    # Memory loop hygiene: push after every edit
    git = repo.git_status()
    if git["is_repo"]:
        if git["dirty"]:
            findings.append(
                Finding(
                    "uncommitted-changes",
                    INFO,
                    f"{len(git['dirty'])} uncommitted change(s) — the memory loop pushes after every edit",
                )
            )
        if not git["has_remote"]:
            findings.append(
                Finding(
                    "no-remote",
                    INFO,
                    "no git remote — memory won't survive this machine",
                )
            )
        elif git["unpushed"]:
            findings.append(
                Finding(
                    "unpushed-commits",
                    INFO,
                    f"{git['unpushed']} commit(s) not pushed",
                )
            )
    return findings


def summarize(findings: list[Finding]) -> dict[str, int]:
    out = {ERROR: 0, WARNING: 0, INFO: 0}
    for f in findings:
        out[f.severity] = out.get(f.severity, 0) + 1
    return out
