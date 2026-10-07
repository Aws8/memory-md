"""Dry-run Dreaming: local heuristics for the cleanup a Dreaming agent
would do — merge duplicates, flag stale entries, spot contradictions —
without an LLM and without writing anything.

Every suggestion is advisory. Nothing here edits the repo.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from difflib import SequenceMatcher
from pathlib import Path

from .model import Entry
from .repo import MemoryRepo

WORD_RE = re.compile(r"[a-z0-9]+")
DATE_RE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
NUM_RE = re.compile(r"\b\d+(?:\.\d+)?%?\b")

DEFAULT_STALE_DAYS = 90
DEFAULT_DUP_RATIO = 0.82
MAX_ENTRIES_FOR_PAIRWISE = 4000


@dataclass(frozen=True)
class Suggestion:
    kind: str  # duplicate | stale | contradiction | undated | unindexed
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
        return f"[{self.kind}] {loc}{self.message}"


def _norm(text: str) -> str:
    """Normalize entry text for duplicate comparison."""
    t = text.lower()
    t = re.sub(r"\[\[[^\]]*\]\]", " ", t)
    t = re.sub(r"https?://\S+", " ", t)
    words = WORD_RE.findall(t)
    return " ".join(sorted(set(words)))


def _fingerprint(text: str) -> frozenset[str]:
    return frozenset(WORD_RE.findall(text.lower()))


def _ratio(a: Entry, b: Entry) -> float:
    return SequenceMatcher(None, _norm(a.text), _norm(b.text)).ratio()


def _same_facts_different_numbers(a: Entry, b: Entry) -> bool:
    """Heuristic contradiction: same subject words, different numbers."""
    wa, wb = _fingerprint(a.text), _fingerprint(b.text)
    if not wa or not wb:
        return False
    shared = len(wa & wb) / max(len(wa | wb), 1)
    if shared < 0.55:
        return False
    na, nb = NUM_RE.findall(a.text), NUM_RE.findall(b.text)
    if not na or not nb:
        return False
    return sorted(na) != sorted(nb)


def dream(
    repo: MemoryRepo,
    stale_days: int = DEFAULT_STALE_DAYS,
    dup_ratio: float = DEFAULT_DUP_RATIO,
    today: date | None = None,
) -> list[Suggestion]:
    """Return advisory cleanup suggestions for the repo."""
    today = today or date.today()
    suggestions: list[Suggestion] = []

    entries: list[Entry] = []
    for note in repo.files.values():
        if note.is_markdown:
            entries.extend(note.entries)

    # Undated + stale entries
    for e in entries:
        added = e.metadata.get("added")
        if not e.metadata or "added" not in e.metadata:
            continue
        try:
            d = date.fromisoformat(added.strip())
        except ValueError:
            continue
        age = (today - d).days
        if age > stale_days:
            suggestions.append(
                Suggestion(
                    "stale",
                    f"added {age} days ago ({added}) — verify or remove",
                    e.file,
                    e.line,
                )
            )

    # Duplicates (exact-normalized fast path, then near-dups) — O(n²) capped
    if len(entries) <= MAX_ENTRIES_FOR_PAIRWISE:
        reported: set[tuple[int, int]] = set()
        groups: dict[str, list[Entry]] = {}
        for e in entries:
            groups.setdefault(_norm(e.text), []).append(e)
        for key, group in groups.items():
            if key and len(group) > 1:
                for e in group[1:]:
                    suggestions.append(
                        Suggestion(
                            "duplicate",
                            f"same as {group[0].file.as_posix()}:{group[0].line} — merge",
                            e.file,
                            e.line,
                        )
                    )
                    reported.add((id(group[0]), id(e)))
        # Candidate pairs via inverted index: only compare entries sharing a
        # sufficiently rare word. Words in >20% of entries carry no signal.
        from itertools import combinations

        common_cutoff = max(3, len(entries) // 5)
        inverted: dict[str, list[int]] = {}
        fingerprints = [_fingerprint(e.text) for e in entries]
        for i, fp in enumerate(fingerprints):
            for w in fp:
                inverted.setdefault(w, []).append(i)
        candidates: set[tuple[int, int]] = set()
        for ids in inverted.values():
            if 1 < len(ids) <= common_cutoff:
                candidates.update(combinations(sorted(ids), 2))

        def _jaccard(i: int, j: int) -> float:
            a, b = fingerprints[i], fingerprints[j]
            if not a or not b:
                return 0.0
            return len(a & b) / len(a | b)

        for i, j in candidates:
            a, b = entries[i], entries[j]
            if (id(a), id(b)) in reported or _norm(a.text) == _norm(b.text):
                continue
            if a.file == b.file and _same_facts_different_numbers(a, b):
                suggestions.append(
                    Suggestion(
                        "contradiction",
                        f"same subject, different numbers vs line {b.line} — check sources",
                        a.file,
                        a.line,
                    )
                )
                reported.add((id(a), id(b)))
            elif _jaccard(i, j) >= 0.35 and _ratio(a, b) >= dup_ratio:
                suggestions.append(
                    Suggestion(
                        "duplicate",
                        f"~{int(_ratio(a, b) * 100)}% similar to {b.file.as_posix()}:{b.line} — merge?",
                        a.file,
                        a.line,
                    )
                )
                reported.add((id(a), id(b)))

    # Unindexed markdown files (reachable but not in the index)
    if repo.entrypoint is not None:
        indexed = {repo.resolve(l.path).relpath for l in repo.index_links() if repo.resolve(l.path)}
        reachable = repo.reachable()
        for rel, note in sorted(repo.files.items(), key=lambda kv: kv[0].as_posix()):
            if not note.is_markdown or rel == Path("MEMORY.md"):
                continue
            if rel in reachable and rel not in indexed:
                suggestions.append(
                    Suggestion(
                        "unindexed",
                        "reachable via links but missing from MEMORY.md ## Index",
                        rel,
                    )
                )
    return suggestions
