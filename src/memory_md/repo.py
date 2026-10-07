"""Load and parse an Agent Memory Repo.

Implements the layout rules from https://cognition.com/agent-memory-repo:

- ``MEMORY.md`` at the repo root is the entry point; keep it short and
  link everything else from an ``## Index`` section.
- Entries are one-line bullets: ``- text [key: value; key: value]``.
- Cross-links are ``[[path]]`` rooted at the repo root. ``.md`` is omitted
  for Markdown files; other extensions are kept.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

from .model import Entry, Link, NoteFile

LINK_RE = re.compile(r"\[\[([^\[\]]+)\]\]")
HEADING_RE = re.compile(r"^#{1,6}\s+(.+?)\s*$")
BULLET_RE = re.compile(r"^(?P<indent>[ \t]*)(?:[-*+]|\d+[.)])\s+(?P<body>.*)$")
FENCE_RE = re.compile(r"^\s*(```+|~~~+)")
INDEX_HEADING_RE = re.compile(r"^#{1,6}\s+index\s*$", re.IGNORECASE)
SECTION_HEADING_RE = re.compile(r"^#{1,6}\s+")

# A trailing [key: value; key: value] block. The body must look like
# key/value pairs, so a plain [note] at line end is left in the text.
TRAILING_META_RE = re.compile(r"\[([^\[\]]+)\]\s*$")
META_KEY_RE = re.compile(r"(?:^|;)\s*([A-Za-z_][\w-]*)\s*:")

ENTRYPOINT = "MEMORY.md"
INDEX_HEADING = "index"

# Files that are normal to find unlinked inside a memory repo.
IGNORED_FILES = {
    ".gitignore",
    ".gitattributes",
    "license",
    "license.md",
    "license.txt",
}
IGNORED_DIRS = {".git", "node_modules", ".venv", "__pycache__", ".devin-plugin"}


def slugify(heading: str) -> str:
    """GitHub-style anchor slug for a Markdown heading."""
    s = heading.strip().lower()
    s = re.sub(r"[^\w\s-]", "", s)
    return re.sub(r"[\s_]+", "-", s).strip("-")


def _iter_files(root: Path) -> list[Path]:
    out = []
    for p in sorted(root.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(root)
        if any(part in IGNORED_DIRS or part.startswith(".git") for part in rel.parts):
            continue
        out.append(rel)
    return out


def parse_metadata(body: str) -> dict[str, str] | None:
    """Parse a ``key: value; key: value`` body. None if it isn't metadata."""
    matches = list(META_KEY_RE.finditer(body))
    if not matches:
        return None
    meta: dict[str, str] = {}
    for i, m in enumerate(matches):
        key = m.group(1).lower()
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
        value = body[start:end].strip().rstrip(";").strip()
        # Reject if a chunk before the first key isn't just separators
        meta[key] = value
    prefix = body[: matches[0].start()].strip()
    if prefix and prefix != ";":
        return None
    return meta


def _strip_code(line: str) -> str:
    """Remove inline `code` spans so links inside them don't count."""
    return re.sub(r"`[^`]*`", "", line)


def parse_file(root: Path, relpath: Path) -> NoteFile:
    abspath = root / relpath
    try:
        text = abspath.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        text = abspath.read_text(encoding="utf-8", errors="replace")
    note = NoteFile(
        relpath=relpath,
        abspath=abspath,
        text=text,
        is_markdown=relpath.suffix.lower() in {".md", ".markdown"},
    )
    if not note.is_markdown:
        return note

    in_fence = False
    fence_marker = ""
    for lineno, line in enumerate(text.splitlines(), start=1):
        fence = FENCE_RE.match(line)
        if fence:
            marker = fence.group(1)[0] * 3
            if not in_fence:
                in_fence = True
                fence_marker = marker
            elif marker == fence_marker:
                in_fence = False
            continue
        if in_fence:
            continue

        heading = HEADING_RE.match(line)
        if heading:
            note.headings.add(slugify(heading.group(1)))

        clean = _strip_code(line)
        for m in LINK_RE.finditer(clean):
            raw = m.group(1).strip()
            path, sep, anchor = raw.partition("#")
            note.links.append(
                Link(
                    raw=raw,
                    path=path.strip(),
                    anchor=anchor.strip() if sep else None,
                    line=lineno,
                )
            )

        bullet = BULLET_RE.match(line)
        if bullet:
            body = bullet.group("body").strip()
            meta: dict[str, str] = {}
            tm = TRAILING_META_RE.search(body)
            if tm and not body.endswith("]]"):
                parsed = parse_metadata(tm.group(1))
                if parsed is not None:
                    meta = parsed
                    body = body[: tm.start()].rstrip()
            if body or meta:
                note.entries.append(
                    Entry(
                        file=relpath,
                        line=lineno,
                        text=body,
                        metadata=meta,
                        indent=len(bullet.group("indent").expandtabs(4)),
                    )
                )
    return note


class MemoryRepo:
    """A loaded Agent Memory Repo rooted at ``root``."""

    def __init__(self, root: Path):
        self.root = root.resolve()
        if not self.root.is_dir():
            raise NotADirectoryError(f"not a directory: {root}")
        self.files: dict[Path, NoteFile] = {}
        for rel in _iter_files(self.root):
            if rel.name in IGNORED_FILES or rel.name.lower() in IGNORED_FILES:
                continue
            self.files[rel] = parse_file(self.root, rel)

    @property
    def entrypoint(self) -> NoteFile | None:
        return self.files.get(Path(ENTRYPOINT))

    def resolve(self, link_path: str) -> NoteFile | None:
        """Resolve a [[path]] to a file. .md is optional for Markdown."""
        p = link_path.strip().strip("/")
        if not p:
            return None
        cand = Path(p)
        if cand in self.files:
            return self.files[cand]
        if cand.suffix.lower() != ".md":
            with_md = Path(p + ".md")
            if with_md in self.files:
                return self.files[with_md]
        return None

    def index_links(self) -> list[Link]:
        """Links listed under the ``## Index`` section of MEMORY.md."""
        ep = self.entrypoint
        if ep is None:
            return []
        in_index = False
        out: list[Link] = []
        in_fence = False
        for lineno, line in enumerate(ep.text.splitlines(), start=1):
            if FENCE_RE.match(line):
                in_fence = not in_fence
                continue
            if in_fence:
                continue
            if SECTION_HEADING_RE.match(line):
                in_index = bool(INDEX_HEADING_RE.match(line))
                continue
            if in_index:
                for m in LINK_RE.finditer(_strip_code(line)):
                    raw = m.group(1).strip()
                    path, sep, anchor = raw.partition("#")
                    out.append(
                        Link(
                            raw=raw,
                            path=path.strip(),
                            anchor=anchor.strip() if sep else None,
                            line=lineno,
                        )
                    )
        return out

    def reachable(self) -> set[Path]:
        """Files reachable from MEMORY.md by following links (BFS)."""
        ep = self.entrypoint
        if ep is None:
            return set()
        seen = {ep.relpath}
        stack = [ep]
        while stack:
            note = stack.pop()
            for link in note.links:
                target = self.resolve(link.path)
                if target and target.relpath not in seen:
                    seen.add(target.relpath)
                    stack.append(target)
        return seen

    def git_status(self) -> dict[str, object]:
        """Git state of the repo: dirty files, remote, unpushed commits."""
        info: dict[str, object] = {
            "is_repo": False,
            "dirty": [],
            "has_remote": False,
            "unpushed": 0,
        }
        try:
            inside = subprocess.run(
                ["git", "rev-parse", "--is-inside-work-tree"],
                cwd=self.root,
                capture_output=True,
                text=True,
                timeout=15,
            )
        except (OSError, subprocess.TimeoutExpired):
            return info
        if inside.returncode != 0 or "true" not in inside.stdout:
            return info
        info["is_repo"] = True

        dirty = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=self.root,
            capture_output=True,
            text=True,
            timeout=15,
        )
        if dirty.returncode == 0:
            info["dirty"] = [l for l in dirty.stdout.splitlines() if l.strip()]

        remote = subprocess.run(
            ["git", "remote"],
            cwd=self.root,
            capture_output=True,
            text=True,
            timeout=15,
        )
        info["has_remote"] = bool(remote.stdout.strip())
        if info["has_remote"]:
            ahead = subprocess.run(
                ["git", "rev-list", "--count", "@{upstream}..HEAD"],
                cwd=self.root,
                capture_output=True,
                text=True,
                timeout=15,
            )
            if ahead.returncode == 0 and ahead.stdout.strip().isdigit():
                info["unpushed"] = int(ahead.stdout.strip())
        return info


def find_repo(start: Path) -> MemoryRepo:
    """Open the memory repo at ``start`` or nearest parent containing MEMORY.md."""
    start = start.resolve()
    for cand in [start, *start.parents]:
        if (cand / ENTRYPOINT).is_file():
            return MemoryRepo(cand)
    return MemoryRepo(start)
