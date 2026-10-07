"""Write-side helpers: init a compliant repo, add spec-formatted entries."""

from __future__ import annotations

import subprocess
from datetime import date
from pathlib import Path

MEMORY_TEMPLATE = """# Memory: {name}

- {name} uses this memory repo across agent sessions [added: {today}]

## Index
- [[{first_note}]]
"""

FIRST_NOTE_TEMPLATE = """# {title}

- Replace this with your first real memory [added: {today}]
"""


def init_repo(path: Path, name: str, git: bool = True) -> list[str]:
    """Create a spec-compliant memory repo. Returns actions taken."""
    path = path.resolve()
    actions: list[str] = []
    path.mkdir(parents=True, exist_ok=True)

    memory_md = path / "MEMORY.md"
    if memory_md.exists():
        raise FileExistsError(f"{memory_md} already exists")
    memory_md.write_text(
        MEMORY_TEMPLATE.format(name=name, today=date.today().isoformat(), first_note="notes/first"),
        encoding="utf-8",
    )
    actions.append(f"created {memory_md}")

    notes = path / "notes"
    notes.mkdir(exist_ok=True)
    first = notes / "first.md"
    first.write_text(
        FIRST_NOTE_TEMPLATE.format(title="First note", today=date.today().isoformat()),
        encoding="utf-8",
    )
    actions.append(f"created {first}")

    if git:
        subprocess.run(["git", "init"], cwd=path, capture_output=True, timeout=30)
        subprocess.run(["git", "add", "-A"], cwd=path, capture_output=True, timeout=30)
        subprocess.run(
            ["git", "-c", "user.email=memory-md@local", "-c", "user.name=memory-md",
             "commit", "-m", "init memory repo"],
            cwd=path,
            capture_output=True,
            timeout=30,
        )
        actions.append("git init + initial commit")
    return actions


def format_entry(text: str, source: str | None = None, added: str | None = None) -> str:
    """Format one spec-compliant entry line."""
    text = " ".join(text.strip().split())
    if not text:
        raise ValueError("entry text is empty")
    meta_parts = []
    if source:
        meta_parts.append(f"source: {source.strip()}")
    meta_parts.append(f"added: {(added or date.today().isoformat()).strip()}")
    return f"- {text} [{'; '.join(meta_parts)}]"


def add_entry(repo_root: Path, file: Path, text: str, source: str | None = None) -> Path:
    """Append a formatted entry to a note file (created if missing)."""
    rel = file
    if rel.suffix.lower() != ".md":
        rel = Path(str(rel) + ".md")
    target = repo_root / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    line = format_entry(text, source=source)
    existing = target.read_text(encoding="utf-8") if target.exists() else f"# {rel.stem}\n"
    if existing and not existing.endswith("\n"):
        existing += "\n"
    target.write_text(existing + line + "\n", encoding="utf-8")
    return rel


def ensure_indexed(repo_root: Path, rel: Path) -> bool:
    """Add [[rel]] to the ## Index of MEMORY.md if missing. True if added."""
    memory_md = repo_root / "MEMORY.md"
    if not memory_md.exists():
        return False
    link_target = rel.as_posix()[:-3] if rel.as_posix().endswith(".md") else rel.as_posix()
    text = memory_md.read_text(encoding="utf-8")
    if f"[[{link_target}]]" in text:
        return False
    lines = text.splitlines()
    idx = None
    for i, l in enumerate(lines):
        if l.strip().lower().startswith("#") and "index" in l.lower():
            idx = i
            break
    if idx is None:
        lines += ["", "## Index"]
        idx = len(lines) - 1
    # insert right after the index heading, before next heading
    insert_at = len(lines)
    for j in range(idx + 1, len(lines)):
        if lines[j].lstrip().startswith("#"):
            insert_at = j
            break
    lines.insert(insert_at, f"- [[{link_target}]]")
    memory_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return True


def stats(repo) -> str:
    """Human-readable stats table for a loaded MemoryRepo."""
    md_files = [n for n in repo.files.values() if n.is_markdown]
    other = [n for n in repo.files.values() if not n.is_markdown]
    entries = [e for n in md_files for e in n.entries]
    links = [l for n in md_files for l in n.links]
    broken = sum(1 for n in md_files for l in n.links if repo.resolve(l.path) is None)
    with_source = sum(1 for e in entries if "source" in e.metadata)
    with_added = sum(1 for e in entries if "added" in e.metadata)
    dates = sorted(e.metadata["added"] for e in entries if "added" in e.metadata)

    indeg: dict[str, int] = {}
    for n in md_files:
        for l in n.links:
            t = repo.resolve(l.path)
            if t:
                indeg[t.relpath.as_posix()] = indeg.get(t.relpath.as_posix(), 0) + 1
    top = sorted(indeg.items(), key=lambda kv: -kv[1])[:5]

    lines = [
        f"root:            {repo.root}",
        f"files:           {len(repo.files)} ({len(md_files)} markdown, {len(other)} other)",
        f"entries:         {len(entries)}",
        f"links:           {len(links)} ({broken} broken)",
        f"with source:     {with_source}/{len(entries)} entries",
        f"with added date: {with_added}/{len(entries)} entries",
    ]
    if dates:
        lines.append(f"added range:     {dates[0]} -> {dates[-1]}")
    if repo.entrypoint is not None:
        reach = repo.reachable()
        lines.append(f"reachable:       {len(reach)}/{len(repo.files)} files from MEMORY.md")
    if top:
        lines.append("most linked-to:")
        for path, n in top:
            lines.append(f"  {path} ({n})")
    return "\n".join(lines)
