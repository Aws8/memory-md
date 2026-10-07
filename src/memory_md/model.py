"""Data model for Agent Memory Repo files.

An Agent Memory Repo is a git repo of Markdown notes. Agents load
MEMORY.md at session start, then follow [[path]] cross-links to other
files. Entries are one-line bullets with optional trailing metadata in
``[key: value; key: value]`` form.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class Link:
    """A ``[[path]]`` or ``[[path#anchor]]`` cross-link inside a file."""

    raw: str  # full text inside [[ ]]
    path: str  # path part before '#'
    anchor: str | None
    line: int  # 1-based line number in the source file


@dataclass(frozen=True)
class Entry:
    """A one-line bullet entry with optional trailing metadata."""

    file: Path  # repo-relative path of the containing file
    line: int  # 1-based line number
    text: str  # entry text with metadata stripped
    metadata: dict[str, str] = field(default_factory=dict)
    indent: int = 0  # leading whitespace columns (sub-bullets are answers)


@dataclass
class NoteFile:
    """A file inside the memory repo with its parsed content."""

    relpath: Path  # path relative to repo root
    abspath: Path
    links: list[Link] = field(default_factory=list)
    entries: list[Entry] = field(default_factory=list)
    headings: set[str] = field(default_factory=set)  # anchor slugs
    text: str = ""
    is_markdown: bool = True

    @property
    def link_target(self) -> str:
        """The canonical [[link]] spelling for this file (md suffix dropped)."""
        p = self.relpath.as_posix()
        if p.lower().endswith(".md"):
            return p[:-3]
        return p
